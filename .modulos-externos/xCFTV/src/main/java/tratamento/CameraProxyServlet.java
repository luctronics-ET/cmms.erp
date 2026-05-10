package tratamento;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.net.Authenticator;
import java.net.HttpURLConnection;
import java.net.PasswordAuthentication;
import java.net.URL;
import java.net.URLEncoder;

import javax.servlet.ServletConfig;
import javax.servlet.ServletContext;
import javax.servlet.ServletException;
import javax.servlet.annotation.WebServlet;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

/**
 * Proxy direto para a API CGI das câmeras/DVRs/NVRs Intelbras (HTTP API V3.59+).
 *
 * As câmeras Intelbras expõem uma API CGI em:
 *   http://{ip}/cgi-bin/{endpoint}.cgi?action={action}&{params}
 * Autenticação: HTTP Digest Auth (user:password por câmera ou padrão global).
 *
 * Endpoints expostos por este proxy (sem CORS, acessível pelo browser):
 *
 *   GET /cam/status?ip=192.168.10.X
 *       → verifica se a câmera responde (magicBox.cgi?action=getSystemInfo)
 *       → retorna JSON: {online, ip, info:{version,deviceType,...}}
 *
 *   GET /cam/snapshot?ip=192.168.10.X[&channel=1]
 *       → retorna imagem JPEG diretamente da câmera (snapshot.cgi?channel=1&type=0)
 *       → útil para <img src="/cam/snapshot?ip=..."> no browser
 *
 *   GET /cam/channels?ip=192.168.10.X
 *       → lista títulos dos canais (configManager.cgi?action=getConfig&name=ChannelTitle)
 *       → retorna JSON: {ip, channels:[{name},...]}
 *
 *   GET /cam/cgi?ip=192.168.10.X&path=magicBox&action=getSystemInfo[&key=val...]
 *       → proxy genérico: encaminha qualquer chamada CGI à câmera
 *       → retorna o body bruto da resposta (text/plain no formato chave=valor)
 *
 * Configuração (web.xml init-param):
 *   cam.user     usuário padrão das câmeras (ex: admin)
 *   cam.password senha padrão das câmeras
 */
@WebServlet(name = "CameraProxy", urlPatterns = {"/cam/*"})
public class CameraProxyServlet extends HttpServlet {

    private static final int TIMEOUT_MS = 5000;
    private static final int SNAP_TIMEOUT_MS = 8000;

    private String defaultUser;
    private String defaultPassword;

    @Override
    public void init(ServletConfig config) throws ServletException {
        super.init(config);
        ServletContext ctx = config.getServletContext();
        defaultUser     = getParam(config, ctx, "cam.user",     "admin");
        defaultPassword = getParam(config, ctx, "cam.password", "admin");
    }

    private String getParam(ServletConfig cfg, ServletContext ctx, String name, String def) {
        String v = cfg.getInitParameter(name);
        if (v == null) v = ctx.getInitParameter(name);
        return (v != null && !v.isEmpty()) ? v : def;
    }

    @Override
    protected void doGet(HttpServletRequest req, HttpServletResponse resp) throws IOException {
        resp.setHeader("Access-Control-Allow-Origin", "*");

        String pathInfo = req.getPathInfo(); // /status, /snapshot, /channels, /cgi

        // Validar IP obrigatório
        String ip = req.getParameter("ip");
        if (ip == null || ip.isEmpty()) {
            resp.setStatus(400);
            resp.setContentType("application/json;charset=UTF-8");
            resp.getWriter().write("{\"error\":\"parametro ip obrigatorio\"}");
            return;
        }
        // Validar formato IP (apenas IPv4 simples, sem path traversal)
        if (!ip.matches("\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}")) {
            resp.setStatus(400);
            resp.setContentType("application/json;charset=UTF-8");
            resp.getWriter().write("{\"error\":\"ip invalido\"}");
            return;
        }

        String user = coalesce(req.getParameter("user"), defaultUser);
        String pass = coalesce(req.getParameter("pass"), defaultPassword);

        try {
            if ("/status".equals(pathInfo)) {
                handleStatus(ip, user, pass, resp);
            } else if ("/snapshot".equals(pathInfo)) {
                handleSnapshot(ip, user, pass, req, resp);
            } else if ("/channels".equals(pathInfo)) {
                handleChannels(ip, user, pass, resp);
            } else if ("/cgi".equals(pathInfo)) {
                handleGenericCgi(ip, user, pass, req, resp);
            } else {
                resp.setStatus(404);
                resp.setContentType("application/json;charset=UTF-8");
                resp.getWriter().write("{\"error\":\"endpoint nao reconhecido\"}");
            }
        } catch (Exception e) {
            resp.setStatus(502);
            resp.setContentType("application/json;charset=UTF-8");
            resp.getWriter().write("{\"error\":\"" + escapeJson(e.getMessage()) + "\"}");
        }
    }

    // ─────────────────────────────────────────────────────────────────
    // /cam/status?ip=x.x.x.x
    // ─────────────────────────────────────────────────────────────────
    private void handleStatus(String ip, String user, String pass, HttpServletResponse resp)
            throws IOException {
        resp.setContentType("application/json;charset=UTF-8");
        String url = "http://" + ip + "/cgi-bin/magicBox.cgi?action=getSystemInfo";
        byte[] raw = callCamera(url, user, pass, TIMEOUT_MS);
        if (raw == null) {
            resp.setStatus(200);
            resp.getWriter().write("{\"online\":false,\"ip\":\"" + ip + "\"}");
            return;
        }
        String body = new String(raw, "UTF-8");
        // resposta: serialNo=...\r\ndeviceType=...\r\nhardwareVersion=...\r\n...
        String version  = extractKV(body, "softwareVersion");
        String devType  = extractKV(body, "deviceType");
        String serial   = extractKV(body, "serialNo");
        resp.setStatus(200);
        resp.getWriter().write(
            "{\"online\":true,\"ip\":\"" + ip + "\"," +
            "\"info\":{" +
            "\"version\":" + jsonStr(version) + "," +
            "\"deviceType\":" + jsonStr(devType) + "," +
            "\"serialNo\":" + jsonStr(serial) +
            "}}"
        );
    }

    // ─────────────────────────────────────────────────────────────────
    // /cam/snapshot?ip=x.x.x.x[&channel=1]
    // ─────────────────────────────────────────────────────────────────
    private void handleSnapshot(String ip, String user, String pass,
            HttpServletRequest req, HttpServletResponse resp)
            throws IOException {
        String channel = coalesce(req.getParameter("channel"), "1");
        if (!channel.matches("\\d{1,2}")) channel = "1";
        String url = "http://" + ip + "/cgi-bin/snapshot.cgi?channel=" + channel + "&type=0";
        byte[] img = callCamera(url, user, pass, SNAP_TIMEOUT_MS);
        if (img == null) {
            resp.setStatus(502);
            resp.setContentType("application/json;charset=UTF-8");
            resp.getWriter().write("{\"error\":\"camera nao respondeu\",\"ip\":\"" + ip + "\"}");
            return;
        }
        resp.setStatus(200);
        resp.setContentType("image/jpeg");
        resp.getOutputStream().write(img);
    }

    // ─────────────────────────────────────────────────────────────────
    // /cam/channels?ip=x.x.x.x
    // ─────────────────────────────────────────────────────────────────
    private void handleChannels(String ip, String user, String pass, HttpServletResponse resp)
            throws IOException {
        resp.setContentType("application/json;charset=UTF-8");
        String url = "http://" + ip + "/cgi-bin/configManager.cgi?action=getConfig&name=ChannelTitle";
        byte[] raw = callCamera(url, user, pass, TIMEOUT_MS);
        if (raw == null) {
            resp.setStatus(503);
            resp.getWriter().write("{\"error\":\"camera offline\",\"ip\":\"" + ip + "\"}");
            return;
        }
        // Formato: table.ChannelTitle[0].Name=Lab01\r\ntable.ChannelTitle[1].Name=Lab02\r\n
        String body = new String(raw, "UTF-8");
        StringBuilder json = new StringBuilder("[");
        String[] lines = body.split("\r?\n");
        boolean first = true;
        for (String line : lines) {
            // match: table.ChannelTitle[N].Name=Valor
            if (line.contains(".Name=")) {
                String name = line.substring(line.indexOf('=') + 1).trim();
                if (!first) json.append(",");
                first = false;
                json.append(jsonStr(name));
            }
        }
        json.append("]");
        resp.setStatus(200);
        resp.getWriter().write("{\"ip\":\"" + ip + "\",\"channels\":" + json + "}");
    }

    // ─────────────────────────────────────────────────────────────────
    // /cam/cgi?ip=x&path=magicBox&action=getSystemInfo[&param=val...]
    // Proxy genérico — encaminha qualquer chamada CGI à câmera.
    // ─────────────────────────────────────────────────────────────────
    private void handleGenericCgi(String ip, String user, String pass,
            HttpServletRequest req, HttpServletResponse resp)
            throws IOException {
        // 'path' deve ser um identificador simples (sem slashes, sem ..)
        String path = req.getParameter("path");
        if (path == null || path.isEmpty() || !path.matches("[A-Za-z0-9_/]+")) {
            resp.setStatus(400);
            resp.setContentType("application/json;charset=UTF-8");
            resp.getWriter().write("{\"error\":\"parametro path invalido\"}");
            return;
        }

        // Construir query string excluindo 'ip', 'user', 'pass', 'path'
        StringBuilder qs = new StringBuilder();
        java.util.Enumeration<String> names = req.getParameterNames();
        while (names.hasMoreElements()) {
            String name = names.nextElement();
            if ("ip".equals(name) || "user".equals(name) || "pass".equals(name) || "path".equals(name)) continue;
            if (qs.length() > 0) qs.append("&");
            // Encode value for safety
            qs.append(urlEncode(name)).append("=").append(urlEncode(req.getParameter(name)));
        }

        String url = "http://" + ip + "/cgi-bin/" + path + ".cgi" + (qs.length() > 0 ? "?" + qs : "");
        byte[] raw = callCamera(url, user, pass, TIMEOUT_MS);
        if (raw == null) {
            resp.setStatus(502);
            resp.setContentType("application/json;charset=UTF-8");
            resp.getWriter().write("{\"error\":\"camera offline\",\"ip\":\"" + ip + "\"}");
            return;
        }
        resp.setStatus(200);
        resp.setContentType("text/plain;charset=UTF-8");
        resp.getOutputStream().write(raw);
    }

    // ─────────────────────────────────────────────────────────────────
    // HTTP Digest Auth helper (java.net.Authenticator-based)
    // ─────────────────────────────────────────────────────────────────
    private byte[] callCamera(String urlStr, final String user, final String pass, int timeoutMs) {
        HttpURLConnection conn = null;
        try {
            // java.net.HttpURLConnection suporta Digest natively via Authenticator
            Authenticator.setDefault(new Authenticator() {
                @Override
                protected PasswordAuthentication getPasswordAuthentication() {
                    return new PasswordAuthentication(user, pass.toCharArray());
                }
            });

            URL url = new URL(urlStr);
            conn = (HttpURLConnection) url.openConnection();
            conn.setConnectTimeout(timeoutMs);
            conn.setReadTimeout(timeoutMs);
            conn.setRequestMethod("GET");
            conn.setRequestProperty("User-Agent", "xCFTV/1.0");
            conn.setRequestProperty("Cache-Control", "no-cache");

            int code = conn.getResponseCode();
            if (code < 200 || code >= 300) return null;

            InputStream is = conn.getInputStream();
            ByteArrayOutputStream buf = new ByteArrayOutputStream();
            byte[] b = new byte[16384];
            int n;
            while ((n = is.read(b)) != -1) buf.write(b, 0, n);
            return buf.toByteArray();
        } catch (Exception e) {
            return null;
        } finally {
            if (conn != null) conn.disconnect();
        }
    }

    // ─────────────────────────────────────────────────────────────────
    // Helpers
    // ─────────────────────────────────────────────────────────────────

    /** Extrai valor de par "key=value" em resposta CGI (formato chave=valor por linha) */
    private String extractKV(String body, String key) {
        for (String line : body.split("\r?\n")) {
            int eq = line.indexOf('=');
            if (eq > 0) {
                String k = line.substring(0, eq).trim();
                // a chave pode ter prefixo de objeto ex: table.X.Name
                if (k.equals(key) || k.endsWith("." + key)) {
                    return line.substring(eq + 1).trim();
                }
            }
        }
        return null;
    }

    private String escapeJson(String s) {
        if (s == null) return "";
        return s.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n").replace("\r", "");
    }

    private String jsonStr(String s) {
        if (s == null) return "null";
        return "\"" + escapeJson(s) + "\"";
    }

    private String coalesce(String a, String b) {
        return (a != null && !a.isEmpty()) ? a : b;
    }

    private String urlEncode(String s) {
        try {
            return URLEncoder.encode(s, "UTF-8");
        } catch (Exception e) {
            return s;
        }
    }
}
