function navHTML(activePage) {
  const links = [
    ["index.html", "Painel"],
    ["locais.html", "Locais"],
    ["planejamento.html", "Planejamento"],
    ["inspecoes.html", "Inspeções"],
    ["aprovacoes.html", "Aprovações"],
    ["laudos.html", "Laudos"],
    ["normas.html", "Normas"],
    ["historico-relatorios.html", "Histórico"],
  ];
  return links
    .map(([href, label]) => `<a class="${activePage === href ? "active" : ""}" href="${href}">${label}</a>`)
    .join("");
}

function setHeader(activePage, subtitle) {
  const root = document.getElementById("top");
  if (!root) return;
  root.innerHTML = `
    <div style="display:flex;align-items:center;gap:12px">
      <div style="width:32px;height:32px;background:linear-gradient(135deg,var(--acc),var(--cyan));border-radius:8px;display:flex;align-items:center;justify-content:center;color:#fff;font-family:var(--mono);font-weight:700;font-size:11px">xP</div>
      <div style="display:flex;flex-direction:column">
        <h1>xPredial</h1>
        <span class="sub">${subtitle}</span>
      </div>
    </div>
    <nav>${navHTML(activePage)}</nav>
    <div style="margin-left:20px;display:flex;gap:10px">
      <a href="../cmasm-erp.html" class="btn btn-s btn-sm" style="padding:4px 10px;font-size:10px">⇚ xCMASM</a>
    </div>
  `;
}

function optionHtml(items, valueField, labelField) {
  return items.map((item) => `<option value="${item[valueField]}">${item[labelField]}</option>`).join("");
}

async function loadLocaisSelect(selectId) {
  const locais = await predialAPI.listLocais();
  const select = document.getElementById(selectId);
  if (!select) return locais;
  select.innerHTML = `<option value="">Selecione...</option>${optionHtml(locais, "id", "nome")}`;
  return locais;
}

function badge(status) {
  let cls = "info";
  if (["ok", "concluida", "aprovada"].includes(status)) cls = "ok";
  if (["atencao", "aguardando_aprovacao", "planejada"].includes(status)) cls = "warn";
  if (["critico", "reprovada"].includes(status)) cls = "crit";
  return `<span class="badge ${cls}">${status.replace("_", " ")}</span>`;
}

function toast(msg, type = "success") {
  const area = document.getElementById("toast-area") || (() => {
    const d = document.createElement("div");
    d.id = "toast-area";
    d.style = "position:fixed;bottom:20px;right:20px;z-index:9999;display:flex;flex-direction:column;gap:8px";
    document.body.appendChild(d);
    return d;
  })();
  const t = document.createElement("div");
  t.className = `card ${type === "error" ? "red" : "green"}`;
  t.style = "padding:10px 20px;margin:0;min-width:200px;animation:tIn .3s ease;border-left:4px solid " + (type === "error" ? "var(--red)" : "var(--green)");
  t.innerHTML = `<div style="font-size:12px;font-weight:600">${msg}</div>`;
  area.appendChild(t);
  setTimeout(() => { t.style.opacity = "0"; setTimeout(() => t.remove(), 300); }, 3000);
}

window.xPredialUI = {
  setHeader,
  loadLocaisSelect,
  badge,
  toast,
};
