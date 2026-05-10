package tratamento;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.Base64;

import javax.servlet.ServletConfig;
import javax.servlet.ServletContext;
import javax.servlet.ServletException;
import javax.servlet.annotation.WebServlet;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

/**
 * Proxy reverso para a API REST do Intelbras INC-OP (Intelligent Network Center).
 *
 * Configuração via parâmetros de context (web.xml ou servlet init-params):
 *   incop.url      ex: http://192.168.10.5:8080
 *   incop.user     usuário do INC-OP (autenticação HTTP Basic)
 *   incop.password senha do INC-OP
 *
 * Endpoints expostos:
 *   GET /incop/devices?ip=192.168.10.X   → lista dispositivos com aquele IP
 *   GET /incop/devices?start=0&size=200  → lista todos os dispositivos
 *   GET /incop/ping/{id}                 → ping no dispositivo com esse ID
 *   GET /incop/status                    → verifica conectividade com o INC-OP
 */
@WebServlet(name = "IncopProxy", urlPatterns = {"/incop/*"})
public class IncopProxyServlet extends HttpServlet {

    private static final int TIMEOUT_MS = 5000;
    private static final String IMCRS_BASE = "/imcrs";

    private String incopUrl;
    private String authHeader;

    @Override
    public void init(ServletConfig config) throws ServletException {
        super.init(config);
        // Parâmetros podem vir do web.xml <init-param> ou de context-param
        ServletContext ctx = config.getServletContext();
        incopUrl = getParam(config, ctx, "incop.url", "http://localhost:8080");
        String user = getParam(config, ctx, "incop.user", "admin");
        String password = getParam(config, ctx, "incop.password", "admin");
        authHeader = "Basic " + Base64.getEncoder().encodeToString((user + ":" + password).getBytes());
    }

    private String getParam(ServletConfig cfg, ServletContext ctx, String name, String def) {
        String v = cfg.getInitParameter(name);
        if (v == null) v = ctx.getInitParameter(name);
        return (v != null && !v.isEmpty()) ? v : def;
    }

    @Override
    protected void doGet(HttpServletRequest req, HttpServletResponse resp)
            throws IOException {

        // Adiciona cabeçalho CORS para o frontend
        resp.setHeader("Access-Control-Allow-Origin", "*");
        resp.setContentType("application/json;charset=UTF-8");

        String pathInfo = req.getPathInfo(); // ex: /devices, /ping/42, /status

        try {
            if (pathInfo == null || pathInfo.equals("/") || pathInfo.equals("/status")) {
                handleStatus(resp);
            } else if (pathInfo.startsWith("/ping/")) {
                String deviceId = pathInfo.substring("/ping/".length());
                handlePing(deviceId, resp);
            } else if (pathInfo.startsWith("/devices")) {
                String queryStr = req.getQueryString();
                handleDevices(queryStr, resp);
            } else {
                resp.setStatus(404);
                resp.getWriter().write("{\"error\":\"endpoint nao reconhecido\"}");
            }
        } catch (Exception e) {
            resp.setStatus(502);
            resp.getWriter().write("{\"error\":\"" + escapeJson(e.getMessage()) + "\"}");
        }
    }

    /** GET /incop/status — retorna versão/health do INC-OP */
    private void handleStatus(HttpServletResponse resp) throws IOException {
        String upstream = incopUrl + IMCRS_BASE + "/plat/res/device?size=1";
        String xml = callIncop(upstream, "application/xml");
        if (xml != null) {
            resp.setStatus(200);
            resp.getWriter().write("{\"status\":\"ok\",\"incop_url\":\"" + escapeJson(incopUrl) + "\"}");
        } else {
            resp.setStatus(503);
            resp.getWriter().write("{\"status\":\"offline\",\"incop_url\":\"" + escapeJson(incopUrl) + "\"}");
        }
    }

    /** GET /incop/devices[?ip=x.x.x.x&start=0&size=200] */
    private void handleDevices(String queryStr, HttpServletResponse resp) throws IOException {
        StringBuilder sb = new StringBuilder(incopUrl).append(IMCRS_BASE).append("/plat/res/device");
        if (queryStr != null && !queryStr.isEmpty()) sb.append("?").append(queryStr);

        String xml = callIncop(sb.toString(), "application/xml");
        if (xml == null) {
            resp.setStatus(503);
            resp.getWriter().write("{\"error\":\"INC-OP indisponivel\"}");
            return;
        }
        resp.setStatus(200);
        resp.getWriter().write(xmlDeviceListToJson(xml));
    }

    /** GET /incop/ping/{deviceId} */
    private void handlePing(String deviceId, HttpServletResponse resp) throws IOException {
        // Sanitize: apenas dígitos
        if (!deviceId.matches("\\d+")) {
            resp.setStatus(400);
            resp.getWriter().write("{\"error\":\"id invalido\"}");
            return;
        }
        String upstream = incopUrl + IMCRS_BASE + "/plat/res/device/" + deviceId + "/ping";
        String xml = callIncop(upstream, "application/xml");
        if (xml == null) {
            resp.setStatus(503);
            resp.getWriter().write("{\"error\":\"INC-OP indisponivel\"}");
            return;
        }
        resp.setStatus(200);
        resp.getWriter().write("{\"deviceId\":" + deviceId + ",\"result\":" + jsonStr(extractTag(xml, "result")) + "}");
    }

    // ─────────────────────────────────────────────────────────────────
    // Helpers
    // ─────────────────────────────────────────────────────────────────

    private String callIncop(String urlStr, String accept) {
        HttpURLConnection conn = null;
        try {
            URL url = new URL(urlStr);
            conn = (HttpURLConnection) url.openConnection();
            conn.setConnectTimeout(TIMEOUT_MS);
            conn.setReadTimeout(TIMEOUT_MS);
            conn.setRequestMethod("GET");
            conn.setRequestProperty("Authorization", authHeader);
            conn.setRequestProperty("Accept", accept);
            int code = conn.getResponseCode();
            if (code < 200 || code >= 300) return null;
            InputStream is = conn.getInputStream();
            ByteArrayOutputStream buf = new ByteArrayOutputStream();
            byte[] b = new byte[4096];
            int n;
            while ((n = is.read(b)) != -1) buf.write(b, 0, n);
            return buf.toString("UTF-8");
        } catch (Exception e) {
            return null;
        } finally {
            if (conn != null) conn.disconnect();
        }
    }

    /**
     * Converte XML de lista de dispositivos do INC-OP para JSON simplificado.
     * O INC retorna:
     * <list>
     *   <device>
     *     <id>1</id><label>sw-01</label><ip>192.168.10.5</ip>
     *     <status>1</status>  (1=Normal/Online, 2=Warning, 3=Minor, 4=Major,
     *                          5=Critical, 6=Unmanaged, 7=Unreachable, 8=Unknown)
     *   </device>
     * </list>
     */
    private String xmlDeviceListToJson(String xml) {
        StringBuilder json = new StringBuilder("[");
        String[] devices = xml.split("<device>");
        boolean first = true;
        for (int i = 1; i < devices.length; i++) {
            String block = devices[i];
            String id     = extractTag(block, "id");
            String label  = extractTag(block, "label");
            String ip     = extractTag(block, "ip");
            String status = extractTag(block, "status");
            if (ip == null || ip.isEmpty()) continue;
            if (!first) json.append(",");
            first = false;
            json.append("{")
                .append("\"id\":").append(id != null ? id : "null").append(",")
                .append("\"label\":").append(jsonStr(label)).append(",")
                .append("\"ip\":").append(jsonStr(ip)).append(",")
                .append("\"status\":").append(status != null ? status : "0").append(",")
                .append("\"online\":").append("1".equals(status))
                .append("}");
        }
        json.append("]");
        return json.toString();
    }

    /** Extrai conteúdo de uma tag XML simples: <tag>value</tag> */
    private String extractTag(String xml, String tag) {
        if (xml == null) return null;
        int start = xml.indexOf("<" + tag + ">");
        if (start < 0) return null;
        start += tag.length() + 2;
        int end = xml.indexOf("</" + tag + ">", start);
        if (end < 0) return null;
        return xml.substring(start, end).trim();
    }

    private String escapeJson(String s) {
        if (s == null) return "";
        return s.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n").replace("\r", "");
    }

    private String jsonStr(String s) {
        if (s == null) return "null";
        return "\"" + escapeJson(s) + "\"";
    }
}
