var CFTV_CATALOG = [];
var GRUPO_ATIVO = "todas";

function mudaCor(idElemento) {
    var elemento = document.getElementById(idElemento);
    if (!elemento) {
        return;
    }
    setInterval(function() {
        elemento.hidden = !elemento.hidden;
    }, 400);
}

function clica(enderecoIP) {
    window.open("http://" + enderecoIP, "_blank");
}

function camerasFiltradas(grupo) {
    if (!grupo || grupo === "todas") {
        return CFTV_CATALOG;
    }
    return CFTV_CATALOG.filter(function(c) {
        return c.group === grupo;
    });
}

function normalizarTipo(tipo) {
    if (tipo === "bi-spectral") {
        return "Bi-spectral";
    }
    if (tipo === "speed-dome") {
        return "Speed Dome";
    }
    return "Fixa IP";
}

function posicaoMapa(camera, index) {
    if (typeof camera.x === "number" && typeof camera.y === "number") {
        return { x: camera.x, y: camera.y };
    }

    var porGrupo = {
        azul: { x0: 10, y0: 12, w: 40, h: 34, cols: 5 },
        vermelha: { x0: 56, y0: 12, w: 36, h: 34, cols: 5 },
        perimetro: { x0: 10, y0: 58, w: 24, h: 30, cols: 4 },
        paiois: { x0: 36, y0: 58, w: 24, h: 30, cols: 4 },
        internas: { x0: 64, y0: 58, w: 28, h: 30, cols: 5 }
    };

    var regra = porGrupo[camera.group] || porGrupo.internas;
    var cols = regra.cols;
    var c = index % cols;
    var r = Math.floor(index / cols);
    var x = regra.x0 + c * (regra.w / Math.max(cols, 1));
    var y = regra.y0 + r * 6.6;
    return { x: x, y: y };
}

function renderMapa(grupo) {
    var mapa = document.getElementById("mapaCanvas");
    var legenda = document.getElementById("mapaLegenda");
    if (!mapa) {
        return;
    }

    var counters = { azul: 0, vermelha: 0, perimetro: 0, paiois: 0, internas: 0 };
    var html = "";

    for (var i = 0; i < CFTV_CATALOG.length; i++) {
        var cam = CFTV_CATALOG[i];
        var idx = counters[cam.group] || 0;
        counters[cam.group] = idx + 1;

        var p = posicaoMapa(cam, idx);
        var ativo = (grupo === "todas" || cam.group === grupo);

        html += "<div class='mapa-pin " + cam.group + (ativo ? "" : " off") + "' " +
            "style='left:" + p.x + "%;top:" + p.y + "%;' " +
            "data-name='" + cam.name + "' " +
            "title='" + cam.name + " | " + cam.ip + " | " + cam.group + "' " +
            "onclick=\"clica('" + cam.ip + "')\"></div>";
    }

    mapa.innerHTML = html;

    if (legenda) {
        legenda.innerHTML =
            "Legenda: " +
            "<span style='color:#2563eb'><b>Azul</b></span> " + counters.azul +
            " | <span style='color:#dc2626'><b>Vermelha</b></span> " + counters.vermelha +
            " | <span style='color:#b45309'><b>Perimetro</b></span> " + counters.perimetro +
            " | <span style='color:#15803d'><b>Paiois</b></span> " + counters.paiois +
            " | <span style='color:#6d28d9'><b>Internas</b></span> " + counters.internas;
    }
}

function renderPainel(grupo) {
    var painelBody = document.getElementById("painelBody");
    if (!painelBody) {
        return;
    }

    var cams = CFTV_CATALOG;
    var colunas = 10;
    var html = "";

    for (var i = 0; i < cams.length; i++) {
        if (i % colunas === 0) {
            html += "<tr>";
        }

        var c = cams[i];
        var ativo = (grupo === "todas" || c.group === grupo);
        var opacidade = ativo ? "1" : "0.25";

        html += "<td id='" + c.ip + "' data-grupo='" + c.group + "' data-ip='" + c.ip + "' data-name='" + c.name + "' " +
            "style='opacity:" + opacidade + "' " +
            "onclick=\"abrirSnapshot('" + c.ip + "','" + c.name + "')\" " +
            "oncontextmenu=\"clica('" + c.ip + "');return false;\" " +
            "title='" + c.name + " | " + c.ip + " | Clique: snapshot | Botão direito: WEB'>" +
            c.name + "</td>";

        if (i % colunas === colunas - 1 || i === cams.length - 1) {
            html += "</tr>";
        }
    }

    painelBody.innerHTML = html;
}

function renderInventario(grupo) {
    var corpo = document.getElementById("inventarioBody");
    if (!corpo) {
        return;
    }

    var cams = camerasFiltradas(grupo);
    var html = "";

    for (var i = 0; i < cams.length; i++) {
        var c = cams[i];
        var info = INCOP_STATUS[c.ip];
        var statusHtml;
        if (!info) {
            statusHtml = "<span class='incop-badge incop-unknown'>—</span>";
        } else if (info.online) {
            var pingBtn = info.id ? " <button class='incop-ping-btn' onclick=\"incopPing('" + info.id + "',this)\">Ping</button>" : "";
            statusHtml = "<span class='incop-badge incop-ok'>Online</span>" + pingBtn;
        } else {
            statusHtml = "<span class='incop-badge incop-off'>Offline</span>";
        }
        html += "<tr>" +
            "<td>" + c.name + "</td>" +
            "<td>" + c.ip + "</td>" +
            "<td>" + c.group + "</td>" +
            "<td>" + c.vendor + "</td>" +
            "<td>" + normalizarTipo(c.type) + "</td>" +
            "<td><a href='http://" + c.ip + "' target='_blank'>WEB</a> | <a href='http://" + c.ip + "/onvif/device_service' target='_blank'>ONVIF</a></td>" +
            "<td>" + statusHtml + "</td>" +
            "</tr>";
    }

    corpo.innerHTML = html;
}

function atualizarSaida(msg) {
    var output = document.getElementById("output");
    if (output) {
        output.innerHTML = msg;
    }
}

function filtrarGrupo(grupo) {
    GRUPO_ATIVO = grupo || "todas";
    renderPainel(GRUPO_ATIVO);
    renderInventario(GRUPO_ATIVO);
    renderMapa(GRUPO_ATIVO);
    atualizarSaida("Filtro ativo: <b>" + GRUPO_ATIVO + "</b> | Cameras: " + camerasFiltradas(GRUPO_ATIVO).length);
}

function readTextFile(file) {
    fetch(file)
        .then(function(response) {
            return response.text();
        })
        .then(function(text) {
            var linhas = text.split(/\r?\n/).map(function(l) {
                return l.trim();
            }).filter(Boolean);

            var unicos = [];
            var seen = {};
            for (var i = 0; i < linhas.length; i++) {
                if (!seen[linhas[i]]) {
                    seen[linhas[i]] = true;
                    unicos.push(linhas[i]);
                }
            }

            atualizarSaida("IPs monitorados carregados: " + unicos.length + " | " + unicos.slice(0, 8).join(", "));
        })
        .catch(function() {
            atualizarSaida("Nao foi possivel ler a lista de IPs monitorados.");
        });
}

function copiarComando(elemento) {
    var cmdCell = elemento && elemento.parentNode ? elemento.parentNode.querySelector(".cmd") : null;
    if (!cmdCell) {
        return;
    }

    var texto = cmdCell.textContent;
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(texto);
    }

    var old = elemento.textContent;
    elemento.textContent = "Copiado";
    setTimeout(function() {
        elemento.textContent = old;
    }, 1000);
}

function abrirMapa(recurso, modulo) {
    var msg = "XMapa [" + modulo + "] -> " + recurso;
    atualizarSaida(msg);

    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(recurso);
    }
}

function carregarCatalogo() {
    return fetch("resources/cftv-cameras.json")
        .then(function(response) {
            return response.json();
        })
        .then(function(data) {
            CFTV_CATALOG = data.cameras || [];
            window.xcftvCatalog = {
                version: data.version || "1.0",
                updatedAt: data.updatedAt || "",
                cameras: CFTV_CATALOG,
                groups: ["todas", "azul", "vermelha", "perimetro", "paiois", "internas"],
                incop: data.incop || { enabled: false }
            };
        })
        .catch(function() {
            CFTV_CATALOG = [];
            atualizarSaida("Falha ao carregar catalogo local de cameras.");
        });
}

document.addEventListener("DOMContentLoaded", function() {
    carregarCatalogo().then(function() {
        filtrarGrupo("todas");
        // Inicia integração INC-OP se habilitada no catálogo
        if (window.xcftvCatalog && window.xcftvCatalog.incop && window.xcftvCatalog.incop.enabled) {
            incopInit(window.xcftvCatalog.incop);
        }
    });
});

// ═══════════════════════════════════════════════════════════════
//  INTEGRAÇÃO INTELBRAS INC-OP (Intelligent Network Center)
//  API: GET /incop/devices?ip=x.x.x.x  →  proxy → INC-OP /imcrs
// ═══════════════════════════════════════════════════════════════

var INCOP_STATUS = {};   // ip → {online, label, id, status}
var INCOP_TIMER  = null;
var INCOP_CONFIG = {};

function incopInit(cfg) {
    INCOP_CONFIG = cfg;
    incopVerificarConexao(function(ok) {
        var badge = document.getElementById("incopBadge");
        if (badge) {
            badge.textContent  = ok ? "INC-OP: online" : "INC-OP: offline";
            badge.className    = "incop-badge " + (ok ? "incop-ok" : "incop-off");
        }
        if (ok) {
            incopPollAll();
            var intervalo = (cfg.pollIntervalSec || 30) * 1000;
            INCOP_TIMER = setInterval(incopPollAll, intervalo);
        }
    });
}

function incopVerificarConexao(cb) {
    fetch(INCOP_CONFIG.proxyUrl + "/status")
        .then(function(r) { return r.json(); })
        .then(function(j) { cb(j.status === "ok"); })
        .catch(function()  { cb(false); });
}

/**
 * Busca todos os dispositivos gerenciados pelo INC-OP.
 * O INC-OP pode gerenciar switches, câmeras e outros equipamentos na rede.
 * Filtramos apenas os IPs que existem no catálogo de câmeras.
 */
function incopPollAll() {
    var size = CFTV_CATALOG.length + 50;  // margem de segurança
    fetch(INCOP_CONFIG.proxyUrl + "/devices?size=" + size)
        .then(function(r) { return r.json(); })
        .then(function(lista) {
            INCOP_STATUS = {};
            for (var i = 0; i < lista.length; i++) {
                var d = lista[i];
                if (d.ip) INCOP_STATUS[d.ip] = d;
            }
            incopAplicarStatus();
        })
        .catch(function() {
            // Silencioso: manter status anterior
        });
}

/**
 * Busca status de uma câmera específica via IP.
 * Útil para verificação pontual (botão "Verificar").
 */
function incopVerificarCamera(ip) {
    return fetch(INCOP_CONFIG.proxyUrl + "/devices?ip=" + encodeURIComponent(ip) + "&size=5")
        .then(function(r) { return r.json(); })
        .then(function(lista) {
            for (var i = 0; i < lista.length; i++) {
                if (lista[i].ip === ip) {
                    INCOP_STATUS[ip] = lista[i];
                    return lista[i];
                }
            }
            return null;
        });
}

/**
 * Aplica indicadores visuais de status INC-OP:
 *   - Células do painel (table#painel): borda verde/vermelha/cinza
 *   - Linhas do inventário: coluna "Status INC-OP"
 *   - Pins do mapa: classe css incop-online / incop-offline
 *   - Contador no painel de controle
 */
function incopAplicarStatus() {
    var online = 0, offline = 0, unknown = 0;

    for (var i = 0; i < CFTV_CATALOG.length; i++) {
        var cam = CFTV_CATALOG[i];
        var info = INCOP_STATUS[cam.ip];

        // --- Painel (cells por IP) ---
        var cell = document.getElementById(cam.ip);
        if (cell) {
            cell.classList.remove("incop-online", "incop-offline", "incop-unknown");
            if (!info) {
                cell.classList.add("incop-unknown");
                unknown++;
            } else if (info.online) {
                cell.classList.add("incop-online");
                online++;
                cell.title = cam.name + " | " + cam.ip + " | Online";
            } else {
                cell.classList.add("incop-offline");
                offline++;
                cell.title = cam.name + " | " + cam.ip + " | OFFLINE (status " + info.status + ")";
            }
        }

        // --- Mapa pins ---
        var pin = document.querySelector(".mapa-pin[data-name='" + cam.name + "']");
        if (pin) {
            pin.classList.remove("incop-online", "incop-offline", "incop-unknown");
            if (!info)         pin.classList.add("incop-unknown");
            else if (info.online) pin.classList.add("incop-online");
            else               pin.classList.add("incop-offline");
        }
    }

    // --- Inventário: atualizar coluna Status se existir ---
    var linhas = document.querySelectorAll("#inventarioBody tr");
    for (var j = 0; j < linhas.length; j++) {
        var tds = linhas[j].querySelectorAll("td");
        if (tds.length < 2) continue;
        // IP está na 2ª coluna (índice 1)
        var ipCell = tds[1] ? tds[1].textContent.trim() : "";
        var statusTd = tds[6]; // 7ª coluna = Status INC-OP
        if (!statusTd) continue;
        var inf = INCOP_STATUS[ipCell];
        if (!inf) {
            statusTd.innerHTML = "<span class='incop-badge incop-unknown'>—</span>";
        } else if (inf.online) {
            statusTd.innerHTML = "<span class='incop-badge incop-ok'>Online</span>";
        } else {
            statusTd.innerHTML = "<span class='incop-badge incop-off'>Offline</span>";
        }
    }

    // --- Contador ---
    var el = document.getElementById("incopContador");
    if (el) {
        el.textContent = "INC-OP: " + online + " online | " + offline + " offline | " + unknown + " n/gerenciado";
    }
}

/** Ping manual de câmera pelo ID INC-OP (usa botão na linha do inventário) */
function incopPing(deviceId, btn) {
    if (!INCOP_CONFIG.proxyUrl) return;
    btn.disabled = true;
    btn.textContent = "...";
    fetch(INCOP_CONFIG.proxyUrl + "/ping/" + deviceId)
        .then(function(r) { return r.json(); })
        .then(function(j) {
            btn.disabled = false;
            btn.textContent = "Ping";
            var result = (j.result || "sem resposta").substring(0, 200);
            atualizarSaida("<b>Ping INC-OP → device " + deviceId + ":</b><br><pre style='font-size:11px'>" + result + "</pre>");
        })
        .catch(function() {
            btn.disabled = false;
            btn.textContent = "Ping";
            atualizarSaida("Erro ao pingar device " + deviceId + " via INC-OP.");
        });
}

// ═══════════════════════════════════════════════════════════════
//  SNAPSHOT MODAL — API CGI Intelbras (HTTP API V3.59)
//  Proxy: /cam/snapshot?ip=x.x.x.x  → /cgi-bin/snapshot.cgi
// ═══════════════════════════════════════════════════════════════

var SNAP_CURRENT_IP   = null;
var SNAP_CURRENT_NAME = null;
var CAM_PROXY_BASE    = "/cam";

function abrirSnapshot(ip, name) {
    SNAP_CURRENT_IP   = ip;
    SNAP_CURRENT_NAME = name;
    var modal = document.getElementById("snapModal");
    if (!modal) return;
    document.getElementById("snapModalTitle").textContent = name + "  (" + ip + ")";
    document.getElementById("snapInfo").textContent = "Carregando...";
    modal.style.display = "flex";
    carregarSnapshotImagem();
    carregarInfoCamera();
}

function fecharSnapshot() {
    var modal = document.getElementById("snapModal");
    if (modal) modal.style.display = "none";
    // Limpar src para parar download
    var img = document.getElementById("snapImg");
    if (img) img.src = "";
    SNAP_CURRENT_IP = null;
}

function atualizarSnapshot() {
    if (SNAP_CURRENT_IP) carregarSnapshotImagem();
}

function carregarSnapshotImagem() {
    var img = document.getElementById("snapImg");
    if (!img || !SNAP_CURRENT_IP) return;
    // Cache-bust com timestamp para forçar reload
    img.src = CAM_PROXY_BASE + "/snapshot?ip=" + encodeURIComponent(SNAP_CURRENT_IP) + "&channel=1&t=" + Date.now();
    img.onerror = function() {
        img.alt = "Snapshot indisponível — câmera offline ou credenciais incorretas";
        img.src = "";
        document.getElementById("snapInfo").textContent = "Câmera offline ou credenciais incorretas.";
    };
}

function carregarInfoCamera() {
    if (!SNAP_CURRENT_IP) return;
    fetch(CAM_PROXY_BASE + "/status?ip=" + encodeURIComponent(SNAP_CURRENT_IP))
        .then(function(r) { return r.json(); })
        .then(function(j) {
            var infoEl = document.getElementById("snapInfo");
            if (!infoEl) return;
            if (!j.online) {
                infoEl.textContent = "Câmera OFFLINE";
                return;
            }
            var i = j.info || {};
            infoEl.innerHTML =
                "<b>Online</b> | " +
                (i.deviceType  ? "Tipo: " + i.deviceType + " | "  : "") +
                (i.version     ? "FW: " + i.version + " | "       : "") +
                (i.serialNo    ? "S/N: " + i.serialNo             : "");
        })
        .catch(function() {/* silencioso */});
}

function abrirWebCam() {
    if (SNAP_CURRENT_IP) window.open("http://" + SNAP_CURRENT_IP, "_blank");
}

function copiarRtsp() {
    if (!SNAP_CURRENT_IP) return;
    // Formato RTSP padrão Intelbras (usuário/senha precisam ser ajustados no campo)
    var rtsp = "rtsp://admin:admin@" + SNAP_CURRENT_IP + ":554/cam/realmonitor?channel=1&subtype=0";
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(rtsp);
    }
    atualizarSaida("RTSP copiado: <code>" + rtsp + "</code>");
}

// Fechar modal ao clicar fora
window.addEventListener("click", function(e) {
    var modal = document.getElementById("snapModal");
    if (modal && e.target === modal) fecharSnapshot();
});