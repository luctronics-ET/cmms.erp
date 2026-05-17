/**
 * pmoc-engine.js — PMOC Dashboard Engine v2.0 for xCMASM
 * Expects window.PMOC_CFG to be set before calling PMOC.init()
 */
(function(){
'use strict';

let S, EST, CFG;
const BASE_STYLE_ID='pmoc-base-style';
const BASE_STYLE=`
:root{--bg:#07111f;--bg2:#0d1e33;--bg3:#0a1828;--line:#1e3a5f;--tx:#e2e8f0;--tx2:#94a3b8;--tx3:#64748b;--green:#22c55e;--red:#ef4444;--amber:#f59e0b;--accent:#00b4d8;--accent-ink:#fff;--mono:'JetBrains Mono',monospace;--sans:'DM Sans',sans-serif}
*{box-sizing:border-box;margin:0;padding:0}html,body{height:100%;overflow:hidden;background:var(--bg);color:var(--tx);font-family:var(--sans)}
.pmoc-root{display:flex;flex-direction:column;height:100vh;overflow:hidden}
.pmoc-header{height:44px;background:var(--bg2);border-bottom:1px solid var(--line);display:flex;align-items:center;gap:10px;padding:0 16px;flex-shrink:0}
.pmoc-header-back{color:var(--tx2);font-size:12px;text-decoration:none;display:flex;align-items:center;gap:4px;padding:4px 8px;border-radius:5px;border:1px solid var(--line);transition:all .12s}.pmoc-header-back:hover{border-color:var(--accent);color:var(--accent)}
.pmoc-header-sep{width:1px;height:20px;background:var(--line)}.pmoc-header-icon{font-size:18px}.pmoc-header-title{font-size:14px;font-weight:700;color:var(--tx);flex:1}.pmoc-header-meta{font-size:10px;color:var(--tx3);font-family:var(--mono)}
.pmoc-btn{display:inline-flex;align-items:center;gap:5px;padding:5px 11px;border-radius:6px;border:none;cursor:pointer;font-size:11px;font-weight:600;font-family:var(--sans);transition:all .12s}
.pmoc-btn-p{background:var(--accent);color:var(--accent-ink)}.pmoc-btn-p:hover{opacity:.88}.pmoc-btn-s{background:var(--green);color:#fff}.pmoc-btn-s:hover{opacity:.88}.pmoc-btn-g{background:var(--bg3);color:var(--tx2);border:1px solid var(--line)}.pmoc-btn-g:hover{border-color:var(--accent);color:var(--tx)}
.pmoc-kpis{height:62px;background:var(--bg3);border-bottom:1px solid var(--line);display:flex;gap:1px;flex-shrink:0;overflow:hidden}
.pmoc-kpi{flex:1;padding:8px 14px;background:var(--bg2);display:flex;flex-direction:column;justify-content:center;min-width:0}.pmoc-kpi-lbl{font-size:9px;font-weight:600;color:var(--tx3);text-transform:uppercase;letter-spacing:.07em;margin-bottom:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.pmoc-kpi-val{font-size:18px;font-weight:800;letter-spacing:-.03em;font-family:var(--mono);white-space:nowrap}
.pmoc-main{flex:1;min-height:0;display:grid;grid-template-columns:minmax(0,1.9fr) minmax(0,1.15fr) minmax(0,1fr);gap:1px;background:var(--line)}
.pmoc-col{background:var(--bg);display:flex;flex-direction:column;overflow:hidden}.pmoc-col-hdr{padding:7px 12px;background:var(--bg2);border-bottom:1px solid var(--line);font-size:9px;font-weight:700;color:var(--tx3);text-transform:uppercase;letter-spacing:.08em;flex-shrink:0;display:flex;align-items:center;gap:6px}.pmoc-col-body{flex:1;overflow-y:auto;min-height:0}.pmoc-col-body::-webkit-scrollbar{width:3px}.pmoc-col-body::-webkit-scrollbar-thumb{background:var(--line);border-radius:2px}
.pmoc-right{background:var(--bg);display:flex;flex-direction:column;overflow:hidden;gap:1px}.pmoc-right-zone{background:var(--bg);display:flex;flex-direction:column;overflow:hidden;flex:1;min-height:0}
.pmoc-divider{height:1px;background:var(--line);flex-shrink:0}
.pmoc-table{width:100%;border-collapse:collapse;font-size:11px}.pmoc-table th{padding:6px 10px;text-align:left;font-size:9px;font-weight:600;letter-spacing:.07em;color:var(--tx3);text-transform:uppercase;border-bottom:1px solid var(--line);white-space:nowrap;background:var(--bg3);position:sticky;top:0;z-index:2}.pmoc-table td{padding:5px 10px;border-bottom:1px solid rgba(30,58,95,.5);vertical-align:middle}.pmoc-table tr:hover td{background:rgba(13,30,51,.6)}.pmoc-empty{text-align:center;color:var(--tx3);padding:14px;font-size:11px}
.pmoc-footer{height:100px;background:var(--line);display:grid;grid-template-columns:minmax(0,1.6fr) minmax(0,1fr);gap:1px;flex-shrink:0}.pmoc-footer-panel{background:var(--bg);display:flex;flex-direction:column;overflow:hidden}.pmoc-footer-hdr{padding:5px 12px;background:var(--bg2);border-bottom:1px solid var(--line);font-size:9px;font-weight:700;color:var(--tx3);text-transform:uppercase;letter-spacing:.08em;flex-shrink:0}.pmoc-footer-body{flex:1;overflow-y:auto;min-height:0}.pmoc-footer-body::-webkit-scrollbar{width:3px}.pmoc-footer-body::-webkit-scrollbar-thumb{background:var(--line);border-radius:2px}
.pmoc-mbg{position:fixed;inset:0;background:rgba(0,0,0,.65);z-index:100;display:none;align-items:center;justify-content:center}.pmoc-mbg.open{display:flex}.pmoc-mbox{background:var(--bg2);border:1px solid var(--line);border-radius:10px;padding:20px;width:420px;max-width:95vw;max-height:90vh;overflow-y:auto}.pmoc-mh{display:flex;align-items:center;justify-content:space-between;margin-bottom:14px}.pmoc-mh h3{font-size:14px;font-weight:700;color:var(--tx)}.pmoc-mc{background:none;border:none;color:var(--tx2);font-size:18px;cursor:pointer;padding:2px 6px;border-radius:4px}.pmoc-mc:hover{color:var(--tx);background:var(--bg3)}
.pmoc-f{margin-bottom:10px}.pmoc-f label{display:block;font-size:10px;font-weight:600;color:var(--tx2);margin-bottom:4px;text-transform:uppercase;letter-spacing:.04em}.pmoc-inp,.pmoc-sel,.pmoc-txa{width:100%;padding:7px 10px;border:1px solid var(--line);border-radius:6px;font-size:12px;background:var(--bg3);color:var(--tx);outline:none;font-family:var(--sans);transition:border-color .12s}.pmoc-inp:focus,.pmoc-sel:focus,.pmoc-txa:focus{border-color:var(--accent)}.pmoc-sel option{background:var(--bg3);color:var(--tx)}.pmoc-txa{resize:vertical;min-height:50px}.pmoc-fg{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.pmoc-donut-wrap{display:flex;align-items:center;gap:8px;padding:8px 10px;flex-shrink:0}.pmoc-donut-svg{width:80px;height:80px;flex-shrink:0}.pmoc-legend{display:flex;flex-direction:column;gap:3px}
`;
const BASE_SHELL=`
<div class="pmoc-root">
  <div class="pmoc-header">
    <a href="/" class="pmoc-header-back">← CMASM</a>
    <div class="pmoc-header-sep"></div>
    <span class="pmoc-header-icon" id="pmoc-icon">⚙️</span>
    <span class="pmoc-header-title" id="pmoc-title">PMOC</span>
    <span class="pmoc-header-meta" id="pmoc-date"></span>
    <button class="pmoc-btn pmoc-btn-p" id="btn-reg">⏱ Registrar Uso</button>
    <button class="pmoc-btn pmoc-btn-s" id="btn-manut">🔧 Nova Manut.</button>
    <button class="pmoc-btn pmoc-btn-g" id="btn-refresh">⟳</button>
  </div>
  <div class="pmoc-kpis" id="pmoc-kpis"></div>
  <div class="pmoc-main">
    <div class="pmoc-col">
      <div class="pmoc-col-hdr">⚙️ Equipamentos</div>
      <div class="pmoc-col-body">
        <table class="pmoc-table">
          <thead><tr><th>Equipamento</th><th>Tipo</th><th style="text-align:right">Horímetro</th><th>Status</th><th style="text-align:right">Manut.</th></tr></thead>
          <tbody id="pmoc-equip"></tbody>
        </table>
      </div>
    </div>
    <div class="pmoc-col" style="background:var(--bg3)">
      <div class="pmoc-col-hdr">📊 Status da Frota</div>
      <div class="pmoc-donut-wrap">
        <div class="pmoc-donut-svg" id="pmoc-donut"></div>
        <div class="pmoc-legend" id="pmoc-legend"></div>
      </div>
      <div class="pmoc-divider"></div>
      <div class="pmoc-col-hdr">📈 Horas por Tipo</div>
      <div style="padding:8px 10px;flex:1;overflow-y:auto" id="pmoc-bar"></div>
    </div>
    <div class="pmoc-right">
      <div class="pmoc-right-zone">
        <div class="pmoc-col-hdr">⚠️ Próx. Manutenções</div>
        <div class="pmoc-col-body" style="padding:6px 8px" id="pmoc-alerts"></div>
      </div>
      <div class="pmoc-divider"></div>
      <div class="pmoc-right-zone" style="background:var(--bg3)">
        <div class="pmoc-col-hdr">📅 Últimos 7 dias</div>
        <div style="padding:6px 8px;display:flex;gap:3px;align-items:stretch" id="pmoc-calendar"></div>
      </div>
    </div>
  </div>
  <div class="pmoc-footer">
    <div class="pmoc-footer-panel">
      <div class="pmoc-footer-hdr">🔧 Últimas Manutenções</div>
      <div class="pmoc-footer-body">
        <table class="pmoc-table">
          <thead><tr><th>Data</th><th>Equip.</th><th>Serviço</th><th>Resp.</th><th style="text-align:right">h</th></tr></thead>
          <tbody id="pmoc-last"></tbody>
        </table>
      </div>
    </div>
    <div class="pmoc-footer-panel">
      <div class="pmoc-footer-hdr">📦 Estoque de Peças</div>
      <div class="pmoc-footer-body">
        <table class="pmoc-table">
          <thead><tr><th>Peça</th><th style="text-align:right">Mín</th><th style="text-align:right">Atual</th><th></th></tr></thead>
          <tbody id="pmoc-stock"></tbody>
        </table>
      </div>
    </div>
  </div>
</div>
<div class="pmoc-mbg" id="pmoc-modal-reg">
  <div class="pmoc-mbox">
    <div class="pmoc-mh"><h3>⏱ Registrar Uso</h3><button class="pmoc-mc" onclick="PMOC.closeModal('pmoc-modal-reg')">✕</button></div>
    <div class="pmoc-f"><label>Equipamento *</label><select class="pmoc-sel" id="mo-uid"></select></div>
    <div class="pmoc-fg">
      <div class="pmoc-f"><label>Data *</label><input class="pmoc-inp" type="date" id="mo-data"></div>
      <div class="pmoc-f"><label>Horas *</label><input class="pmoc-inp" type="number" id="mo-horas" min="0.1" step="0.1" placeholder="0.0"></div>
    </div>
    <div class="pmoc-f"><label>Técnico</label><input class="pmoc-inp" id="mo-op" placeholder="Nome do técnico"></div>
    <div class="pmoc-f"><label>Observações</label><textarea class="pmoc-txa" id="mo-obs"></textarea></div>
    <button class="pmoc-btn pmoc-btn-p" onclick="PMOC.saveRegistro()">Salvar</button>
  </div>
</div>
<div class="pmoc-mbg" id="pmoc-modal-manut">
  <div class="pmoc-mbox">
    <div class="pmoc-mh"><h3>🔧 Registrar Manutenção</h3><button class="pmoc-mc" onclick="PMOC.closeModal('pmoc-modal-manut')">✕</button></div>
    <div class="pmoc-f"><label>Equipamento *</label><select class="pmoc-sel" id="mm-uid"></select></div>
    <div class="pmoc-fg">
      <div class="pmoc-f"><label>Data *</label><input class="pmoc-inp" type="date" id="mm-data"></div>
      <div class="pmoc-f"><label>Horas manut.</label><input class="pmoc-inp" type="number" id="mm-horas" min="0" step="0.5" placeholder="0.0"></div>
    </div>
    <div class="pmoc-f"><label>Item do plano</label><select class="pmoc-sel" id="mm-tipo"><option value="">Selecionar…</option></select></div>
    <div class="pmoc-f"><label>Descrição *</label><textarea class="pmoc-txa" id="mm-desc" placeholder="Descreva o serviço realizado…"></textarea></div>
    <div class="pmoc-f"><label>Responsável</label><input class="pmoc-inp" id="mm-resp" placeholder="Nome do técnico"></div>
    <button class="pmoc-btn pmoc-btn-s" onclick="PMOC.saveManut()">Salvar</button>
  </div>
</div>
`;

/* ─── helpers ─────────────────────────────────────────── */
const fH  = h => `${Number(h||0).toFixed(1)} h`;
const fD  = iso => iso ? new Date(iso).toLocaleDateString('pt-BR') : '–';
const fDT = iso => iso ? new Date(iso).toLocaleString('pt-BR',{day:'2-digit',month:'2-digit',year:'numeric',hour:'2-digit',minute:'2-digit'}) : '–';
const today = () => new Date().toISOString().slice(0,10);
const H = id => S.hist[id] || {hor:0, regs:[], manut:[], ulm:{}};
const T = tid => CFG.tipos[tid];

const SC = {vencida:'#ef4444', urgente:'#f59e0b', proxima:'#60a5fa', ok:'#22c55e'};
const SL = {vencida:'VENCIDA', urgente:'URGENTE', proxima:'PRÓXIMA', ok:'EM DIA'};
const SBG= {vencida:'rgba(239,68,68,.15)', urgente:'rgba(245,158,11,.15)', proxima:'rgba(96,165,250,.12)', ok:'rgba(34,197,94,.12)'};

function accentInk(hex){
  const raw=(hex||'').replace('#','');
  if(raw.length!==6)return '#fff';
  const r=parseInt(raw.slice(0,2),16);
  const g=parseInt(raw.slice(2,4),16);
  const b=parseInt(raw.slice(4,6),16);
  if([r,g,b].some(Number.isNaN))return '#fff';
  const lum=(0.299*r+0.587*g+0.114*b)/255;
  return lum>0.68 ? '#07111f' : '#fff';
}

function ensureBaseTemplate(){
  const wantsTemplate=document.body?.dataset?.pmocTemplate==='body' || !document.querySelector('.pmoc-root');
  if(!wantsTemplate)return;
  if(!document.getElementById(BASE_STYLE_ID)){
    const style=document.createElement('style');
    style.id=BASE_STYLE_ID;
    style.textContent=BASE_STYLE;
    document.head.appendChild(style);
  }
  if(document.querySelector('.pmoc-root'))return;
  const wrap=document.createElement('div');
  wrap.innerHTML=BASE_SHELL;
  document.body.prepend(...wrap.childNodes);
}

function syncPageMeta(){
  if(!CFG)return;
  document.title=`CMASM · ${CFG.title}`;
  const dateEl=document.getElementById('pmoc-date');
  if(dateEl){
    dateEl.textContent=new Date().toLocaleDateString('pt-BR',{weekday:'short',day:'2-digit',month:'short',year:'numeric'});
  }
}

function badge(st){
  return `<span style="padding:1px 7px;border-radius:9999px;font-size:9px;font-weight:700;font-family:monospace;color:${SC[st]};background:${SBG[st]};white-space:nowrap">${SL[st]}</span>`;
}

/* ─── storage ──────────────────────────────────────────── */
function loadState(){
  try{
    const r=localStorage.getItem(CFG.sk);
    if(r){const s=JSON.parse(r);s.unidades.forEach(u=>{if(!s.hist[u.id])s.hist[u.id]={hor:0,regs:[],manut:[],ulm:{}};});return s;}
  }catch(_){}
  const hist={};CFG.defaultUnits.forEach(u=>{hist[u.id]={hor:0,regs:[],manut:[],ulm:{}};});
  return{unidades:[...CFG.defaultUnits],hist};
}
function loadEst(){
  try{
    const r=localStorage.getItem(CFG.se);
    if(r){const saved=JSON.parse(r);return CFG.defaultParts.map(p=>({...p,qt:saved[p.id]?.qt||0,movs:saved[p.id]?.movs||[]}));}
  }catch(_){}
  return CFG.defaultParts.map(p=>({...p,qt:0,movs:[]}));
}
function saveState(){try{localStorage.setItem(CFG.sk,JSON.stringify(S));}catch(_){} syncToAPI();}
function saveEst(){
  const obj={};EST.forEach(p=>{obj[p.id]={qt:p.qt,movs:(p.movs||[]).slice(-30)};});
  try{localStorage.setItem(CFG.se,JSON.stringify(obj));}catch(_){} syncToAPI();
}

/* ─── API sync (backend persistence) ──────────────────── */
async function syncFromAPI(){
  if(!CFG?.pageId)return;
  try{
    const res=await fetch(`/api/pmoc/${CFG.pageId}`);
    if(!res.ok)return;
    const data=await res.json();
    let changed=false;
    if(data.state_json){
      try{
        const s=JSON.parse(data.state_json);
        if(s&&s.unidades){
          s.unidades.forEach(u=>{if(!s.hist[u.id])s.hist[u.id]={hor:0,regs:[],manut:[],ulm:{}};});
          S=s;
          localStorage.setItem(CFG.sk,data.state_json);
          changed=true;
        }
      }catch(_){}
    }
    if(data.est_json){
      try{
        const saved=JSON.parse(data.est_json);
        EST=CFG.defaultParts.map(p=>({...p,qt:saved[p.id]?.qt||0,movs:saved[p.id]?.movs||[]}));
        localStorage.setItem(CFG.se,data.est_json);
        changed=true;
      }catch(_){}
    }
    if(changed){populateUnitSelects();render();}
  }catch(_){}
}

async function syncToAPI(){
  if(!CFG?.pageId)return;
  try{
    const estObj={};EST.forEach(p=>{estObj[p.id]={qt:p.qt,movs:(p.movs||[]).slice(-30)};});
    await fetch(`/api/pmoc/${CFG.pageId}`,{
      method:'PUT',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({state_json:JSON.stringify(S),est_json:JSON.stringify(estObj)})
    });
  }catch(_){}
}

/* ─── maintenance logic ────────────────────────────────── */
function calcProx(uid){
  const u=S.unidades.find(x=>x.id===uid);if(!u)return[];
  const t=T(u.tipo);if(!t)return[];
  const h=H(uid);
  return t.plano.map(m=>{
    const ult=h.ulm[m.id]||0;
    const prox=ult===0?m.iv:(Math.floor(ult/m.iv)+1)*m.iv;
    const falt=prox-h.hor;
    const pct=falt/m.iv;
    let st;
    if(falt<=0)st='vencida';
    else if(pct<=0.10)st='urgente';
    else if(pct<=0.20)st='proxima';
    else st='ok';
    return{...m,prox,falt,ult,st};
  });
}
function unitStatus(uid){
  const pr=calcProx(uid);
  if(pr.some(p=>p.st==='vencida'))return'vencida';
  if(pr.some(p=>p.st==='urgente'))return'urgente';
  if(pr.some(p=>p.st==='proxima'))return'proxima';
  return'ok';
}
function allAlerts(){
  return S.unidades.filter(u=>u.ativo).flatMap(u=>
    calcProx(u.id).filter(p=>p.st!=='ok').map(p=>({u,p}))
  ).sort((a,b)=>a.p.falt-b.p.falt);
}

/* ─── SVG charts ───────────────────────────────────────── */
function donutSVG(data, total){
  if(!total) return `<svg viewBox="0 0 100 100" style="width:100%;height:100%">
    <circle cx="50" cy="50" r="35" fill="none" stroke="#0d1e33" stroke-width="14"/>
    <text x="50" y="48" text-anchor="middle" fill="#94a3b8" font-size="8">0</text>
    <text x="50" y="58" text-anchor="middle" fill="#475569" font-size="6">equip.</text></svg>`;
  const r=35,cx=50,cy=50; let ang=-Math.PI/2;
  const arcs=data.map(d=>{
    const sw=(d.value/total)*2*Math.PI;
    const x1=cx+r*Math.cos(ang), y1=cy+r*Math.sin(ang);
    ang+=sw;
    const x2=cx+r*Math.cos(ang), y2=cy+r*Math.sin(ang);
    const lg=sw>Math.PI?1:0;
    return `<path d="M${cx},${cy}L${x1.toFixed(2)},${y1.toFixed(2)}A${r},${r} 0 ${lg} 1 ${x2.toFixed(2)},${y2.toFixed(2)}Z" fill="${d.color}"/>`;
  });
  return `<svg viewBox="0 0 100 100" style="width:100%;height:100%">
    ${arcs.join('')}<circle cx="50" cy="50" r="25" fill="#07111f"/>
    <text x="50" y="47" text-anchor="middle" fill="#e2e8f0" font-size="14" font-weight="bold" font-family="monospace">${total}</text>
    <text x="50" y="57" text-anchor="middle" fill="#64748b" font-size="6" font-family="sans-serif">equip.</text></svg>`;
}

function barRows(bars){
  if(!bars.length) return `<div style="color:#475569;font-size:10px;text-align:center;padding:8px">Sem dados</div>`;
  const mx=Math.max(...bars.map(b=>b.value),1);
  return bars.map(b=>{
    const pct=(b.value/mx*100).toFixed(1);
    return `<div style="display:flex;align-items:center;gap:5px;margin-bottom:4px">
      <div style="width:68px;font-size:9px;color:#94a3b8;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex-shrink:0">${b.label}</div>
      <div style="flex:1;height:13px;background:#0a1828;border-radius:2px;overflow:hidden">
        <div style="width:${pct}%;height:100%;background:${b.color};border-radius:2px;display:flex;align-items:center;justify-content:flex-end;padding-right:3px;transition:width .4s">
          ${b.value>0?`<span style="font-size:8px;font-weight:700;color:rgba(255,255,255,.9);font-family:monospace">${fH(b.value)}</span>`:''}
        </div>
      </div>
    </div>`;
  }).join('');
}

/* ─── mini 7-day heatmap ───────────────────────────────── */
function calendarRow(){
  const days=['Dom','Seg','Ter','Qua','Qui','Sex','Sáb'];
  const dates=[];
  const now=new Date();
  for(let i=6;i>=0;i--){const d=new Date(now);d.setDate(d.getDate()-i);dates.push(d);}
  const uns=S.unidades.filter(u=>u.ativo);
  const allRegs=uns.flatMap(u=>H(u.id).regs.map(r=>r.dt?.slice(0,10)));
  const allManuts=uns.flatMap(u=>H(u.id).manut.map(m=>m.data?.slice(0,10)));
  return dates.map(d=>{
    const iso=d.toISOString().slice(0,10);
    const regs=allRegs.filter(x=>x===iso).length;
    const mauts=allManuts.filter(x=>x===iso).length;
    const isToday=iso===today();
    const bg=mauts>0?'#22c55e':regs>0?'#00b4d8':isToday?'rgba(0,180,216,.2)':'#0a1828';
    const brd=isToday?'1px solid #00b4d8':'1px solid #1e3a5f';
    return `<div style="flex:1;text-align:center;border-radius:4px;padding:3px 2px;background:${bg};border:${brd};cursor:default" title="${iso}: ${regs} reg, ${mauts} manut">
      <div style="font-size:8px;color:#94a3b8;font-weight:600">${days[d.getDay()]}</div>
      <div style="font-size:10px;font-weight:700;color:${isToday?'#00b4d8':'#e2e8f0'};font-family:monospace">${d.getDate()}</div>
      ${regs+mauts>0?`<div style="font-size:8px;color:rgba(255,255,255,.7)">${regs+mauts}</div>`:'<div style="font-size:8px;color:transparent">·</div>'}
    </div>`;
  }).join('');
}

/* ─── render sections ──────────────────────────────────── */
function renderKPIs(){
  const uns=S.unidades.filter(u=>u.ativo);
  const tH=uns.reduce((s,u)=>s+H(u.id).hor,0);
  const als=allAlerts();
  const tM=uns.reduce((s,u)=>s+H(u.id).manut.length,0);
  const pCrit=EST.filter(p=>p.qt===0).length;
  const pBaixo=EST.filter(p=>p.qt>0&&p.qt<=(p.min||2)).length;
  const el=document.getElementById('pmoc-kpis'); if(!el)return;
  const kpis=[
    {l:'Equipamentos',v:uns.length,    c:CFG.accent,    i:'⚙️'},
    {l:'Horas Frota',  v:fH(tH),       c:'#60a5fa',     i:'⏱️'},
    {l:'Manutenções',  v:tM,           c:'#22c55e',     i:'🔧'},
    {l:'Alertas',      v:als.length,   c:als.length?'#ef4444':'#22c55e', i:'⚠️'},
    {l:'Estoque Crit.',v:pCrit+pBaixo, c:(pCrit+pBaixo)?'#f59e0b':'#22c55e', i:'📦'},
  ];
  el.innerHTML=kpis.map(k=>`<div class="pmoc-kpi" style="border-left:3px solid ${k.c}">
    <div class="pmoc-kpi-lbl">${k.i} ${k.l}</div>
    <div class="pmoc-kpi-val" style="color:${k.c}">${k.v}</div>
  </div>`).join('');
}

function renderEquip(){
  const el=document.getElementById('pmoc-equip'); if(!el)return;
  const uns=S.unidades.filter(u=>u.ativo);
  if(!uns.length){el.innerHTML=`<tr><td colspan="5" class="pmoc-empty">Sem equipamentos</td></tr>`;return;}
  el.innerHTML=uns.map(u=>{
    const t=T(u.tipo); const st=unitStatus(u.id); const h=H(u.id);
    const alerts=calcProx(u.id).filter(p=>p.st!=='ok');
    return `<tr onclick="PMOC.selectUnit('${u.id}')" style="cursor:pointer">
      <td>
        <div style="display:flex;align-items:center;gap:5px">
          <div style="width:7px;height:7px;border-radius:50%;background:${t?.cor||'#94a3b8'};flex-shrink:0"></div>
          <span style="font-weight:600;color:#e2e8f0;font-size:11px">${u.nome}</span>
        </div>
        ${alerts.length?`<div style="font-size:9px;color:${SC[st]};margin-left:12px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">⚠ ${alerts[0].n}</div>`:''}
      </td>
      <td style="font-size:10px;color:#94a3b8;white-space:nowrap">${t?.emoji||''} ${t?.nome||u.tipo}</td>
      <td style="text-align:right;font-family:monospace;font-size:11px;color:#60a5fa;font-weight:600">${fH(h.hor)}</td>
      <td>${badge(st)}</td>
      <td style="text-align:right;font-family:monospace;font-size:10px;color:#64748b">${h.manut.length}</td>
    </tr>`;
  }).join('');
}

function renderCharts(){
  const uns=S.unidades.filter(u=>u.ativo);
  // donut
  const cnt={ok:0,proxima:0,urgente:0,vencida:0};
  uns.forEach(u=>cnt[unitStatus(u.id)]++);
  const donutData=[
    {label:'EM DIA',  value:cnt.ok,       color:'#22c55e'},
    {label:'PRÓXIMA', value:cnt.proxima,  color:'#60a5fa'},
    {label:'URGENTE', value:cnt.urgente,  color:'#f59e0b'},
    {label:'VENCIDA', value:cnt.vencida,  color:'#ef4444'},
  ].filter(d=>d.value>0);
  const elD=document.getElementById('pmoc-donut');
  if(elD)elD.innerHTML=donutSVG(donutData,uns.length);
  const elL=document.getElementById('pmoc-legend');
  if(elL)elL.innerHTML=donutData.map(d=>`<div style="display:flex;align-items:center;gap:4px;font-size:9px;color:#94a3b8">
    <div style="width:7px;height:7px;border-radius:2px;background:${d.color}"></div>${d.label}: <b style="color:#e2e8f0;font-family:monospace">${d.value}</b></div>`).join('');
  // bars
  const typeH={};
  uns.forEach(u=>{
    const t=T(u.tipo);
    if(!typeH[u.tipo])typeH[u.tipo]={label:`${t?.emoji||''} ${(t?.nome||u.tipo).substring(0,12)}`,value:0,color:t?.cor||CFG.accent};
    typeH[u.tipo].value+=H(u.id).hor;
  });
  const elB=document.getElementById('pmoc-bar');
  if(elB)elB.innerHTML=barRows(Object.values(typeH).sort((a,b)=>b.value-a.value).slice(0,6));
}

function renderAlerts(){
  const el=document.getElementById('pmoc-alerts'); if(!el)return;
  const als=allAlerts().slice(0,7);
  if(!als.length){el.innerHTML=`<div style="text-align:center;padding:10px;color:#22c55e;font-size:11px">✓ Tudo em dia!</div>`;return;}
  el.innerHTML=als.map(a=>{
    const t=T(a.u.tipo); const c=SC[a.p.st];
    const txt=a.p.falt<=0?`Vencida há ${Math.abs(a.p.falt).toFixed(0)}h`:`Faltam ${a.p.falt.toFixed(0)}h`;
    return `<div style="padding:4px 7px;background:#0d1e33;border-radius:4px;border-left:3px solid ${c};margin-bottom:3px" onclick="PMOC.selectUnit('${a.u.id}')" style="cursor:pointer">
      <div style="display:flex;align-items:center;gap:4px;font-size:10px;font-weight:600;color:#e2e8f0">
        <span style="flex-shrink:0">${t?.emoji||'⚙️'}</span>
        <span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1">${a.u.nome}</span>
        ${badge(a.p.st)}
      </div>
      <div style="font-size:9px;color:#64748b;margin-top:1px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${a.p.n}</div>
      <div style="font-size:9px;color:${c};font-family:monospace">${txt}</div>
    </div>`;
  }).join('');
}

function renderCalendar(){
  const el=document.getElementById('pmoc-calendar'); if(!el)return;
  el.innerHTML=calendarRow();
}

function renderLastMaint(){
  const el=document.getElementById('pmoc-last'); if(!el)return;
  const uns=S.unidades.filter(u=>u.ativo);
  const all=uns.flatMap(u=>H(u.id).manut.map(m=>({...m,unit:u}))).sort((a,b)=>new Date(b.data||0)-new Date(a.data||0)).slice(0,5);
  if(!all.length){el.innerHTML=`<tr><td colspan="5" class="pmoc-empty">Nenhuma manutenção registrada.</td></tr>`;return;}
  el.innerHTML=all.map(m=>{
    const t=T(m.unit.tipo);
    return `<tr>
      <td style="font-size:10px;color:#94a3b8;font-family:monospace;white-space:nowrap">${fD(m.data)}</td>
      <td><div style="display:flex;align-items:center;gap:5px">
        <div style="width:6px;height:6px;border-radius:50%;background:${t?.cor||'#94a3b8'};flex-shrink:0"></div>
        <span style="font-size:10px;font-weight:600;color:#e2e8f0">${m.unit.nome}</span>
      </div></td>
      <td style="font-size:10px;color:#94a3b8;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:160px">${m.desc||m.n||'–'}</td>
      <td style="font-size:10px;color:#64748b">${m.resp||'–'}</td>
      <td style="text-align:right;font-size:10px;font-family:monospace;color:#60a5fa">${fH(m.h||0)}</td>
    </tr>`;
  }).join('');
}

function renderStock(){
  const el=document.getElementById('pmoc-stock'); if(!el)return;
  if(!EST.length){el.innerHTML=`<tr><td colspan="4" class="pmoc-empty">Sem peças cadastradas.</td></tr>`;return;}
  el.innerHTML=EST.slice(0,12).map(p=>{
    const min=p.min||2; const crit=p.qt===0; const low=p.qt>0&&p.qt<=min;
    const col=crit?'#ef4444':low?'#f59e0b':'#22c55e';
    const pct=min>0?Math.min(100,(p.qt/min)*100):p.qt>0?100:0;
    return `<tr>
      <td style="font-size:10px;color:#e2e8f0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:140px" title="${p.d}">${p.d}</td>
      <td style="text-align:right;font-size:10px;font-family:monospace;color:#64748b">${min}</td>
      <td style="text-align:right;font-size:10px;font-family:monospace;font-weight:700;color:${col}">${p.qt}</td>
      <td style="width:55px">
        <div style="height:4px;background:#0a1828;border-radius:2px;overflow:hidden">
          <div style="width:${pct.toFixed(0)}%;height:100%;background:${col};border-radius:2px;transition:width .4s"></div>
        </div>
      </td>
    </tr>`;
  }).join('');
}

/* ─── full render ──────────────────────────────────────── */
function render(){
  renderKPIs();
  renderEquip();
  renderCharts();
  renderAlerts();
  renderCalendar();
  renderLastMaint();
  renderStock();
}

/* ─── modal helpers ────────────────────────────────────── */
function openModal(id){document.getElementById(id)?.classList.add('open');}
function closeModal(id){document.getElementById(id)?.classList.remove('open');}

/* ─── save registro de uso ─────────────────────────────── */
function saveRegistro(){
  const uid=document.getElementById('mo-uid')?.value;
  const dt=document.getElementById('mo-data')?.value;
  const h=parseFloat(document.getElementById('mo-horas')?.value)||0;
  const op=document.getElementById('mo-op')?.value||'';
  const obs=document.getElementById('mo-obs')?.value||'';
  if(!uid||!dt||h<=0){alert('Preencha data e horas.');return;}
  if(!S.hist[uid])S.hist[uid]={hor:0,regs:[],manut:[],ulm:{}};
  S.hist[uid].hor=parseFloat((S.hist[uid].hor+h).toFixed(1));
  S.hist[uid].regs.push({id:'r'+Date.now(),dt,h,op,obs});
  saveState(); closeModal('pmoc-modal-reg'); render();
}

/* ─── save manutenção ──────────────────────────────────── */
function saveManut(){
  const uid=document.getElementById('mm-uid')?.value;
  const data=document.getElementById('mm-data')?.value;
  const desc=document.getElementById('mm-desc')?.value||'';
  const resp=document.getElementById('mm-resp')?.value||'';
  const h=parseFloat(document.getElementById('mm-horas')?.value)||0;
  const tipo=document.getElementById('mm-tipo')?.value||'';
  if(!uid||!data||!desc){alert('Preencha data e descrição.');return;}
  if(!S.hist[uid])S.hist[uid]={hor:0,regs:[],manut:[],ulm:{}};
  const mid='m'+Date.now();
  S.hist[uid].manut.push({id:mid,data,desc,resp,h,tipo});
  // mark plan item done if tipo matches plano id
  if(tipo){S.hist[uid].ulm[tipo]=S.hist[uid].hor;}
  saveState(); closeModal('pmoc-modal-manut'); render();
}

/* ─── populate unit selects ────────────────────────────── */
function populateUnitSelects(){
  const uns=S.unidades.filter(u=>u.ativo);
  const opts=`<option value="">Selecionar…</option>`+uns.map(u=>`<option value="${u.id}">${u.nome} (${T(u.tipo)?.nome||u.tipo})</option>`).join('');
  ['mo-uid','mm-uid'].forEach(id=>{const el=document.getElementById(id);if(el)el.innerHTML=opts;});
}

/* ─── populate plano select ────────────────────────────── */
function onUnitChangeMM(){
  const uid=document.getElementById('mm-uid')?.value;
  const el=document.getElementById('mm-tipo'); if(!el)return;
  if(!uid){el.innerHTML='<option value="">Selecionar (opcional)</option>';return;}
  const u=S.unidades.find(x=>x.id===uid);
  const t=u?T(u.tipo):null;
  const plano=t?.plano||[];
  const pr=uid?calcProx(uid):[];
  el.innerHTML='<option value="">Selecionar (opcional)</option>'+
    plano.map(m=>{
      const ps=pr.find(p=>p.id===m.id);
      return `<option value="${m.id}">${m.n}${ps?` [${ps.falt<=0?'VENCIDA':'faltam '+ps.falt.toFixed(0)+'h'}]`:''}`;
    }).join('');
}

/* ─── public API ───────────────────────────────────────── */
window.PMOC={
  init(cfg){
    CFG=cfg; window.PMOC_CFG=cfg;
    ensureBaseTemplate();
    S=loadState(); EST=loadEst();
    document.querySelectorAll('.pmoc-mbg').forEach(el=>{
      el.addEventListener('click',e=>{if(e.target===el)el.classList.remove('open');});
    });
    populateUnitSelects();
    // update title
    const t=document.getElementById('pmoc-title');if(t)t.textContent=cfg.title;
    const ic=document.getElementById('pmoc-icon');if(ic)ic.textContent=cfg.icon;
    // apply accent color
    document.documentElement.style.setProperty('--accent', cfg.accent);
    document.documentElement.style.setProperty('--accent-ink', accentInk(cfg.accent));
    syncPageMeta();
    render();
    // open registro btn
    document.getElementById('btn-reg')?.addEventListener('click',()=>{
      populateUnitSelects();
      document.getElementById('mo-data').value=today();
      openModal('pmoc-modal-reg');
    });
    document.getElementById('btn-manut')?.addEventListener('click',()=>{
      populateUnitSelects();
      document.getElementById('mm-data').value=today();
      openModal('pmoc-modal-manut');
    });
    document.getElementById('btn-refresh')?.addEventListener('click',()=>{syncFromAPI().then(()=>{if(!S||!EST){S=loadState();EST=loadEst();render();}});});
    document.getElementById('mm-uid')?.addEventListener('change',onUnitChangeMM);
    // sync from backend (async, non-blocking — re-renders if newer data found)
    syncFromAPI();
  },
  selectUnit(uid){
    // jump to portal unit page
    const page=CFG.pageId||'dashboard';
    window.location.href=`/?page=${page}`;
  },
  saveRegistro, saveManut,
  closeModal,
  refresh(){syncFromAPI().then(()=>{if(!S||!EST){S=loadState();EST=loadEst();render();}});}
};

})();
