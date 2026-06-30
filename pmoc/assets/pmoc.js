/* CMASM PMOC — single-file app (vanilla, no build step)
 * - IndexedDB store (pmoc_v1)
 * - Boot híbrido: pull do núcleo; fallback para seeds locais
 * - 4 categorias: refrigeracao, maq_corte, viaturas, embarcacoes
 * - Eventos pendentes + sync push
 */
'use strict';

// ─────────── CONFIG ───────────
const NUCLEO = (window.PMOC_NUCLEO || `${location.protocol}//${location.hostname}:8010`);
const DB_NAME = 'pmoc_v1';
const DB_VERSION = 1;
const SEEDS_PATH = 'seeds';

const CATEGORIAS = {
  refrigeracao: {
    label: 'Refrigeração', emoji: '❄️', cor: '#00b4d8',
    categoria_db: 'climatizacao',
    unidade_uso: 'meses',
    colunas: [
      { k: 'nome',  label: 'Nome' },
      { k: 'loc',   label: 'Local' },
      { k: 'btu',   label: 'BTU', detalhe: true, mono: true },
      { k: 'gas',   label: 'Gás', detalhe: true, mono: true },
      { k: 'criticidade', label: 'Crit.', detalhe: true },
      { k: 'status', label: 'Status', isStatus: true },
    ],
    modulo_sync: 'pmoc_refrigeracao',
  },
  maq_corte: {
    label: 'Máq. de corte', emoji: '🔧', cor: '#f59e0b',
    categoria_db: 'maquinas_corte',
    unidade_uso: 'h',
    colunas: [
      { k: 'nome', label: 'Nome' },
      { k: 'tipo', label: 'Tipo', mono: true },
      { k: 'loc',  label: 'Local' },
      { k: 'uso_atual', label: 'Uso', mono: true, suffix: ' h' },
      { k: 'status', label: 'Status', isStatus: true },
    ],
    modulo_sync: 'pmoc_grama',
  },
  viaturas: {
    label: 'Viaturas', emoji: '🚗', cor: '#22c55e',
    categoria_db: 'viaturas',
    unidade_uso: 'km',
    colunas: [
      { k: 'nome',  label: 'Nome' },
      { k: 'placa', label: 'Placa', mono: true },
      { k: 'subtipo', label: 'Subtipo' },
      { k: 'loc',   label: 'Local' },
      { k: 'uso_atual', label: 'Uso', mono: true, useUnidade: true },
      { k: 'status', label: 'Status', isStatus: true },
    ],
    modulo_sync: 'pmoc_transportes',
  },
  embarcacoes: {
    label: 'Embarcações', emoji: '⛵', cor: '#3b82f6',
    categoria_db: 'embarcacoes',
    unidade_uso: 'h',
    colunas: [
      { k: 'nome',  label: 'Nome' },
      { k: 'placa', label: 'Indicativo', mono: true },
      { k: 'subtipo', label: 'Subtipo' },
      { k: 'loc',   label: 'Local' },
      { k: 'uso_atual', label: 'Uso', mono: true, suffix: ' h' },
      { k: 'status', label: 'Status', isStatus: true },
    ],
    modulo_sync: 'pmoc_transportes',
  },
};

// Taxonomia canônica de serviços (espelha a do ERP). Default por categoria do PMOC.
const SERVICO_TAXONOMIA = {
  'TRANSPORTE':         ['FAINA ARMAMENTO TERRESTRE','FAINA ARMAMENTO MARITIMA','TRANSPORTE MATERIAL','TRANSPORTE PESSOAL','MANOBRA DE PESO','RECEBIMENTO MATERIAL','LIXO'],
  'MANUTENCAO':         ['EDIFICACAO','HIDRAULICA','ELETRICA','ELETRONICA','INFORMATICA','REFRIGERACAO','CARPINTARIA','PINTURA INDUSTRIAL'],
  'CONTROLE VEGETAL':   [],
  'CONTROLE BIOLOGICO': [],
};
const TAXON_DEFAULT = {
  refrigeracao: ['MANUTENCAO','REFRIGERACAO'], maq_corte: ['CONTROLE VEGETAL',''],
  viaturas: ['TRANSPORTE',''], embarcacoes: ['TRANSPORTE',''],
};
function _fillSubcat(catVal, subVal) {
  const sub = el('#m-subcat'); if (!sub) return;
  const subs = SERVICO_TAXONOMIA[catVal] || [];
  sub.innerHTML = '<option value="">—</option>' +
    subs.map(s => `<option value="${s}"${s === subVal ? ' selected' : ''}>${s}</option>`).join('');
  sub.disabled = !subs.length;
}

const STORES = [
  'ativos', 'locais', 'catalogo_servicos', 'planos_manutencao',
  'estoque_catalogo', 'eventos_pendentes', 'eventos_aceitos', 'config',
  'refrigeracao_detalhe', 'ordens_servico',
];

// ─────────── INDEXEDDB WRAPPER ───────────
const idb = {
  db: null,
  async open() {
    return new Promise((res, rej) => {
      const req = indexedDB.open(DB_NAME, DB_VERSION);
      req.onupgradeneeded = (e) => {
        const db = e.target.result;
        for (const s of STORES) {
          if (!db.objectStoreNames.contains(s)) {
            const keyPath = (s === 'config') ? 'chave' : 'id';
            db.createObjectStore(s, { keyPath });
          }
        }
      };
      req.onsuccess = (e) => { this.db = e.target.result; res(this.db); };
      req.onerror = (e) => rej(e.target.error);
    });
  },
  _tx(store, mode = 'readonly') {
    return this.db.transaction(store, mode).objectStore(store);
  },
  get(store, key) {
    return new Promise((res, rej) => {
      const r = this._tx(store).get(key);
      r.onsuccess = () => res(r.result); r.onerror = () => rej(r.error);
    });
  },
  put(store, val) {
    return new Promise((res, rej) => {
      const r = this._tx(store, 'readwrite').put(val);
      r.onsuccess = () => res(r.result); r.onerror = () => rej(r.error);
    });
  },
  bulkPut(store, vals) {
    return new Promise((res, rej) => {
      const tx = this.db.transaction(store, 'readwrite');
      const os = tx.objectStore(store);
      for (const v of vals) os.put(v);
      tx.oncomplete = () => res(vals.length);
      tx.onerror = (e) => rej(e.target.error);
    });
  },
  getAll(store) {
    return new Promise((res, rej) => {
      const r = this._tx(store).getAll();
      r.onsuccess = () => res(r.result); r.onerror = () => rej(r.error);
    });
  },
  count(store) {
    return new Promise((res, rej) => {
      const r = this._tx(store).count();
      r.onsuccess = () => res(r.result); r.onerror = () => rej(r.error);
    });
  },
  delete(store, key) {
    return new Promise((res, rej) => {
      const r = this._tx(store, 'readwrite').delete(key);
      r.onsuccess = () => res(); r.onerror = () => rej(r.error);
    });
  },
};

// Config helpers (key/value via store 'config')
const cfg = {
  async get(k, def = null) {
    const r = await idb.get('config', k);
    return r ? r.valor : def;
  },
  async set(k, v) { await idb.put('config', { chave: k, valor: v }); },
};

// ─────────── STATE ───────────
const state = {
  categoria: 'refrigeracao',
  ativos: [],
  refrigDetalhe: {},
  locais: [],
  planos: [],
  catalogo: [],
  user: null,
  token: null,
  pendentes: 0,
  ativoSelecionado: null,
  filtros: { local: '', status: '', busca: '' },
};

// ─────────── UTILS ───────────
const el = (q, ctx = document) => ctx.querySelector(q);
const els = (q, ctx = document) => Array.from(ctx.querySelectorAll(q));
const uuid = () => (crypto.randomUUID ? crypto.randomUUID() : 'x' + Date.now() + Math.random().toString(16).slice(2));
const now = () => new Date().toISOString();
const fmtDate = (iso) => iso ? new Date(iso).toLocaleString('pt-BR') : '—';

function toast(msg, kind = 'ok', ms = 2500) {
  const t = el('#toast');
  t.className = 'toast ' + kind;
  t.textContent = msg;
  t.classList.remove('hidden');
  clearTimeout(toast._t);
  toast._t = setTimeout(() => t.classList.add('hidden'), ms);
}

// ─────────── BOOT ───────────
async function boot() {
  await idb.open();

  // restaurar user/token
  state.token = await cfg.get('token');
  state.user = await cfg.get('user');
  state.categoria = await cfg.get('categoria_ativa', 'refrigeracao');

  // verificar se já populado
  const nAtivos = await idb.count('ativos');

  if (nAtivos === 0) {
    await hydrateInitial();
  } else {
    // já tem dados — tentar sync incremental em background
    syncSilent();
  }

  // se ainda não tem user, mostrar login
  if (!state.user) {
    showLogin();
  } else {
    el('#user-pill').textContent = state.user.nome || state.user.mat;
  }

  await loadAll();
  renderCatNav();
  renderUI();
  await refreshPendentes();
  updateSyncStatus();

  // listeners
  el('#btn-sync').onclick = doSync;
  el('#btn-leitura').onclick = () => openModal('leitura');
  el('#btn-os').onclick = () => openModal('os');
  el('#d-btn-leitura').onclick = () => openModal('leitura');
  el('#d-btn-os').onclick = () => openModal('os');
  el('#f-local').onchange = (e) => { state.filtros.local = e.target.value; renderLista(); };
  el('#f-status').onchange = (e) => { state.filtros.status = e.target.value; renderLista(); };
  el('#f-busca').oninput = (e) => { state.filtros.busca = e.target.value.toLowerCase(); renderLista(); };

  els('.dt').forEach(b => b.onclick = () => switchDetailTab(b.dataset.tab));
  window.addEventListener('online', updateSyncStatus);
  window.addEventListener('offline', updateSyncStatus);
}

// ─────────── HYDRATE (seed-first com tentativa de pull) ───────────
async function hydrateInitial() {
  // tenta núcleo primeiro (apenas se token e online)
  if (navigator.onLine && state.token) {
    try {
      await pullFromNucleo();
      await cfg.set('seed_source', 'nucleo');
      return;
    } catch (e) {
      console.warn('Pull do núcleo falhou:', e);
    }
  }
  await hydrateFromLocalSeeds();
  await cfg.set('seed_source', 'local');
}

async function hydrateFromLocalSeeds() {
  const files = {
    'ativos': 'ativos.json',
    'locais': 'locais.json',
    'planos_manutencao': 'planos.json',
    'estoque_catalogo': 'estoque-catalogo.json',
    'refrigeracao_detalhe': 'refrigeracao-detalhe.json',
  };
  for (const [store, file] of Object.entries(files)) {
    try {
      const resp = await fetch(`${SEEDS_PATH}/${file}`);
      if (!resp.ok) continue;
      const data = await resp.json();
      if (Array.isArray(data) && data.length) {
        await idb.bulkPut(store, data);
      }
    } catch (e) {
      console.warn(`Seed ${file} falhou:`, e);
    }
  }
  await cfg.set('last_sync', null);
}

async function pullFromNucleo() {
  for (const cat of Object.values(CATEGORIAS)) {
    const url = `${NUCLEO}/api/sync/manifest?modulo=${cat.modulo_sync}`;
    const resp = await fetch(url, {
      headers: state.token ? { Authorization: `Bearer ${state.token}` } : {},
    });
    if (!resp.ok) throw new Error(`manifest ${cat.modulo_sync}: ${resp.status}`);
    const m = await resp.json();
    if (m.ativos?.length) await idb.bulkPut('ativos', m.ativos);
    if (m.locais?.length) await idb.bulkPut('locais', m.locais);
    if (m.catalogo_servicos?.length) await idb.bulkPut('catalogo_servicos', m.catalogo_servicos);
    if (m.planos_manutencao?.length) await idb.bulkPut('planos_manutencao', m.planos_manutencao);
    if (m.estoque_catalogo?.length) await idb.bulkPut('estoque_catalogo', m.estoque_catalogo);
  }
  await cfg.set('last_sync', now());
}

async function loadAll() {
  state.ativos = await idb.getAll('ativos');
  state.locais = await idb.getAll('locais');
  state.planos = await idb.getAll('planos_manutencao');
  state.catalogo = await idb.getAll('catalogo_servicos');
  const det = await idb.getAll('refrigeracao_detalhe');
  state.refrigDetalhe = {};
  // tenta casar pelo nome do ativo com ambiente do CSV (matching imperfeito; melhor que nada)
  for (const d of det) {
    state.refrigDetalhe[d.id] = d;
  }
}

// ─────────── LOGIN ───────────
function showLogin() {
  el('#login-modal').classList.remove('hidden');
  el('#lg-go').onclick = doLogin;
  el('#lg-dev').onclick = doLoginDev;
}

async function doLogin() {
  const mat = el('#lg-mat').value.trim();
  const pwd = el('#lg-pwd').value;
  el('#lg-err').classList.add('hidden');
  if (!mat || !pwd) { showLgErr('Preencha matrícula e senha.'); return; }
  try {
    const resp = await fetch(`${NUCLEO}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mat, senha: pwd }),
    });
    if (!resp.ok) throw new Error(`login ${resp.status}`);
    const data = await resp.json();
    state.token = data.token;
    state.user = data.usuario || { mat, nome: mat };
    await cfg.set('token', state.token);
    await cfg.set('user', state.user);
    el('#login-modal').classList.add('hidden');
    el('#user-pill').textContent = state.user.nome || mat;
    // se ainda não populamos do núcleo, tenta agora
    const src = await cfg.get('seed_source');
    if (src !== 'nucleo') {
      try { await pullFromNucleo(); await cfg.set('seed_source', 'nucleo'); await loadAll(); renderUI(); }
      catch (e) { console.warn(e); }
    }
    updateSyncStatus();
  } catch (e) {
    showLgErr('Falha ao autenticar com o núcleo. Use modo dev se estiver offline.');
  }
}

async function doLoginDev() {
  state.user = { id: 'dev', nome: 'operador.dev', mat: 'dev', lotacao: 'dev' };
  state.token = null;
  await cfg.set('user', state.user);
  await cfg.set('token', null);
  el('#login-modal').classList.add('hidden');
  el('#user-pill').textContent = state.user.nome;
  el('#dev-banner').classList.remove('hidden');
  updateSyncStatus();
}

function showLgErr(msg) {
  const e = el('#lg-err');
  e.textContent = msg;
  e.classList.remove('hidden');
}

// ─────────── RENDER ───────────
function renderCatNav() {
  const nav = el('#cat-nav');
  nav.innerHTML = '';
  for (const [key, cat] of Object.entries(CATEGORIAS)) {
    const count = state.ativos.filter(a => a.categoria === cat.categoria_db).length;
    const btn = document.createElement('button');
    btn.className = 'cat-btn' + (key === state.categoria ? ' active' : '');
    btn.innerHTML = `<span class="emoji">${cat.emoji}</span><span class="label">${cat.label}</span><span class="count">${count}</span>`;
    btn.onclick = () => selectCategoria(key);
    nav.appendChild(btn);
  }
}

async function selectCategoria(key) {
  state.categoria = key;
  await cfg.set('categoria_ativa', key);
  closeDetail();
  renderCatNav();
  renderUI();
}

function renderUI() {
  const cat = CATEGORIAS[state.categoria];
  renderCatNav();   // atualiza contadores das categorias (após sync/pull)
  el('#cat-title').textContent = `${cat.emoji} ${cat.label}`;
  renderThead();
  populateFiltroLocal();
  renderLista();
}

function renderThead() {
  const cat = CATEGORIAS[state.categoria];
  el('#thead-row').innerHTML = cat.colunas.map(c => `<th>${c.label}</th>`).join('');
}

function populateFiltroLocal() {
  const cat = CATEGORIAS[state.categoria];
  const ativosCat = state.ativos.filter(a => a.categoria === cat.categoria_db);
  const locais = [...new Set(ativosCat.map(a => a.loc).filter(Boolean))].sort();
  el('#f-local').innerHTML = '<option value="">Todos</option>' +
    locais.map(l => `<option value="${l}">${l}</option>`).join('');
  el('#f-local').value = state.filtros.local;
}

function calcStatus(ativo) {
  // mínima: usa planos para inferir proximo_uso
  const planos = state.planos.filter(p => p.tipo_codigo === ativo.tipo);
  if (!planos.length) return 'ok';
  // pega o menor intervalo
  const intv = planos.reduce((m, p) => Math.min(m, p.intervalo || Infinity), Infinity);
  if (!isFinite(intv) || ativo.uso_atual == null) return 'ok';
  const restante = intv - (ativo.uso_atual % intv);
  if (restante <= 0) return 'vencido';
  if (restante < intv * 0.2) return 'proximo';
  return 'ok';
}

function renderLista() {
  const cat = CATEGORIAS[state.categoria];
  let ativos = state.ativos.filter(a => a.categoria === cat.categoria_db);

  // filtros
  if (state.filtros.local) ativos = ativos.filter(a => a.loc === state.filtros.local);
  if (state.filtros.busca) {
    const q = state.filtros.busca;
    ativos = ativos.filter(a =>
      (a.nome || '').toLowerCase().includes(q) ||
      (a.placa || '').toLowerCase().includes(q) ||
      (a.pat || '').toLowerCase().includes(q));
  }

  // enriquece com detalhe refrigeração (se aplicável)
  const enriched = ativos.map(a => {
    const status = calcStatus(a);
    if (state.categoria === 'refrigeracao') {
      // heurística: tenta casar pelo nome com algum ambiente do CSV
      const det = Object.values(state.refrigDetalhe).find(d =>
        (d.ambiente || '').toUpperCase().includes((a.nome || '').toUpperCase().split(' ').slice(-1)[0] || '')
      );
      return { ...a, ...(det || {}), status };
    }
    return { ...a, status };
  });

  if (state.filtros.status) {
    const filt = enriched.filter(a => a.status === state.filtros.status);
    return renderRows(filt, cat);
  }
  renderRows(enriched, cat);
}

function renderRows(ativos, cat) {
  el('#count-info').textContent = `${ativos.length} ativos`;
  const empty = el('#empty-state');
  const tbody = el('#tbody');
  tbody.innerHTML = '';
  if (!ativos.length) { empty.classList.remove('hidden'); return; }
  empty.classList.add('hidden');

  for (const a of ativos) {
    const tr = document.createElement('tr');
    tr.dataset.id = a.id;
    tr.innerHTML = cat.colunas.map(c => renderCell(a, c)).join('');
    tr.onclick = () => openDetail(a);
    tbody.appendChild(tr);
  }
}

function renderCell(ativo, col) {
  if (col.isStatus) {
    const s = ativo.status || 'ok';
    const labels = { ok: 'Em dia', proximo: 'Próximo', vencido: 'Vencido' };
    return `<td><span class="status-dot status-${s}"></span>${labels[s]}</td>`;
  }
  let v = ativo[col.k];
  if (v == null || v === '') return '<td>—</td>';
  if (col.useUnidade && ativo.unidade_uso) v = `${v} ${ativo.unidade_uso}`;
  else if (col.suffix) v = `${v}${col.suffix}`;
  return `<td${col.mono ? ' class="mono"' : ''}>${v}</td>`;
}

// ─────────── DETAIL ───────────
function openDetail(ativo) {
  state.ativoSelecionado = ativo;
  el('#detail').classList.add('open');
  els('#tbody tr').forEach(tr => tr.classList.toggle('selected', tr.dataset.id === ativo.id));
  el('#d-title').textContent = ativo.nome;
  el('#btn-leitura').disabled = false;
  el('#btn-os').disabled = false;
  switchDetailTab('geral');
  renderTabGeral(ativo);
  renderTabHist(ativo);
  renderTabManut(ativo);
  renderTabDocs(ativo);
}

function closeDetail() {
  el('#detail').classList.remove('open');
  state.ativoSelecionado = null;
  els('#tbody tr').forEach(tr => tr.classList.remove('selected'));
  el('#btn-leitura').disabled = true;
  el('#btn-os').disabled = true;
}
window.closeDetail = closeDetail;

function switchDetailTab(tab) {
  els('.dt').forEach(b => b.classList.toggle('active', b.dataset.tab === tab));
  els('.tab-pane').forEach(p => p.classList.toggle('active', p.id === `tab-${tab}`));
}

function renderTabGeral(a) {
  const pairs = [
    ['ID', a.id, true],
    ['Tipo', a.tipo, true],
    ['Categoria', a.categoria],
    ['Local', a.loc],
    ['Patrimônio', a.pat],
    ['Placa', a.placa, true],
    ['Subtipo', a.subtipo],
    ['Uso atual', a.uso_atual != null ? `${a.uso_atual} ${a.unidade_uso || ''}` : null, true],
    ['Criticidade', a.criticidade],
    ['Obs', a.obs],
  ];
  // detalhe refrigeração
  if (state.categoria === 'refrigeracao' && a.btu) {
    pairs.push(['BTU', a.btu, true], ['Gás', a.gas, true], ['Carga (g)', a.carga_g, true],
      ['Marca', a.marca], ['Modelo', a.modelo], ['Potência (kW)', a.potencia_kw, true]);
  }
  el('#tab-geral').innerHTML = '<dl class="kv-list">' +
    pairs.filter(p => p[1] != null && p[1] !== '')
         .map(([k, v, mono]) => `<dt>${k}</dt><dd${mono ? ' class="mono"' : ''}>${v}</dd>`)
         .join('') + '</dl>';
}

async function renderTabHist(a) {
  const oss = (await idb.getAll('ordens_servico')).filter(o => o.ativo_id === a.id);
  if (!oss.length) {
    el('#tab-hist').innerHTML = '<p style="color:var(--text-dim)">Nenhuma OS registrada.</p>';
    return;
  }
  el('#tab-hist').innerHTML = oss.map(o => `
    <div class="os-item">
      <div class="head"><span>${fmtDate(o.criada_em)}</span><span class="badge b-${o.status}">${o.status}</span></div>
      <div class="title">${o.titulo}</div>
      ${o.categoria ? `<div style="font-size:11px;color:var(--acc,#00b4d8);margin-top:2px">${o.categoria}${o.subcategoria ? ' · ' + o.subcategoria : ''}</div>` : ''}
      ${(o.servicos || []).length ? `<small style="color:var(--text-dim)">Serviços: ${o.servicos.map(s => s.nome).join(', ')}</small>` : ''}
      ${(o.veiculos || []).length ? `<small style="color:var(--text-dim);display:block">Veículos: ${o.veiculos.map(v => v.nome).join(', ')}</small>` : ''}
    </div>`).join('');
}

function renderTabManut(a) {
  const planos = state.planos.filter(p => p.tipo_codigo === a.tipo);
  if (!planos.length) {
    el('#tab-manut').innerHTML = '<p style="color:var(--text-dim)">Sem planos cadastrados para este tipo.</p>';
    return;
  }
  el('#tab-manut').innerHTML = planos.map(p => `
    <div class="os-item">
      <div class="head"><span>${p.intervalo} ${p.unidade}</span></div>
      <div class="title">${p.nome}</div>
      ${(p.materiais || []).length ? '<small style="color:var(--text-dim)">Materiais: ' +
        p.materiais.map(m => `${m.descricao}${m.qtd ? ' (' + m.qtd + ')' : ''}`).join(', ') + '</small>' : ''}
    </div>`).join('');
}

function renderTabDocs(a) {
  el('#tab-docs').innerHTML = '<p style="color:var(--text-dim)">Em breve.</p>';
}

// ─────────── MODAIS (leitura / OS) ───────────
function openModal(kind) {
  if (!state.ativoSelecionado) { toast('Selecione um ativo primeiro', 'err'); return; }
  const a = state.ativoSelecionado;
  const m = el('#modal');
  const title = el('#modal-title');
  const body = el('#modal-content');
  const foot = el('#modal-foot');

  if (kind === 'leitura') {
    title.textContent = `Registrar leitura — ${a.nome}`;
    body.innerHTML = `
      <label class="f-block">
        <span>Leitura atual (${a.unidade_uso || '—'})</span>
        <input id="m-leitura" type="number" min="0" step="any" placeholder="ex: 1240">
      </label>
      <label class="f-block">
        <span>Observação (opcional)</span>
        <input id="m-obs" type="text">
      </label>`;
    foot.innerHTML = `<button class="btn" onclick="closeModal()">Cancelar</button>
                     <button class="btn btn-acc" id="m-save">Salvar</button>`;
    el('#m-save').onclick = () => salvarLeitura(a);
  } else if (kind === 'os') {
    title.textContent = `Nova OS — ${a.nome}`;
    body.innerHTML = `
      <label class="f-block">
        <span>Título</span>
        <input id="m-titulo" type="text" placeholder="ex: Vazamento na serpentina">
      </label>
      <label class="f-block">
        <span>Tipo</span>
        <select id="m-tipo">
          <option value="corretiva">Corretiva</option>
          <option value="preventiva">Preventiva</option>
          <option value="inspecao">Inspeção</option>
        </select>
      </label>
      <label class="f-block">
        <span>Prioridade</span>
        <select id="m-prio">
          <option value="baixa">Baixa</option>
          <option value="media" selected>Média</option>
          <option value="alta">Alta</option>
          <option value="urgente">Urgente</option>
        </select>
      </label>
      <label class="f-block">
        <span>Categoria</span>
        <select id="m-cat">${Object.keys(SERVICO_TAXONOMIA).map(c => `<option value="${c}">${c}</option>`).join('')}</select>
      </label>
      <label class="f-block">
        <span>Subcategoria</span>
        <select id="m-subcat"></select>
      </label>
      <label class="f-block">
        <span>Serviços (um ou vários)</span>
        <div style="display:flex;gap:6px">
          <select id="m-svc-sel" style="flex:1"><option value="">— catálogo —</option>${(state.catalogo || []).map(s => `<option value="${s.id}">${s.nome || s.titulo || s.id}</option>`).join('')}</select>
          <button type="button" class="btn" id="m-svc-add">+</button>
        </div>
        <div style="display:flex;gap:6px;margin-top:4px">
          <input id="m-svc-livre" type="text" placeholder="serviço livre..." style="flex:1">
          <button type="button" class="btn" id="m-svc-add-livre">+</button>
        </div>
        <div id="m-svc-list" style="margin-top:6px"></div>
      </label>
      <label class="f-block">
        <span>Viaturas / Embarcações</span>
        <div id="m-veic-list" style="display:grid;gap:4px"></div>
      </label>`;
    foot.innerHTML = `<button class="btn" onclick="closeModal()">Cancelar</button>
                     <button class="btn btn-acc" id="m-save">Criar</button>`;
    const def = TAXON_DEFAULT[state.categoria] || ['', ''];
    if (def[0]) el('#m-cat').value = def[0];
    _fillSubcat(el('#m-cat').value, def[1]);
    el('#m-cat').onchange = () => _fillSubcat(el('#m-cat').value, '');
    _osServicos = [];
    _renderOsServicos();
    _renderOsVeiculos();
    el('#m-svc-add').onclick = () => {
      const sel = el('#m-svc-sel'); const id = sel.value; if (!id) return;
      const svc = (state.catalogo || []).find(s => s.id === id); if (!svc) return;
      if (_osServicos.some(s => s.catalogo_id === id)) { toast('Já adicionado', 'err'); return; }
      _osServicos.push({ nome: svc.nome || svc.titulo || id, catalogo_id: id, origem: 'catalogo' });
      sel.value = ''; _renderOsServicos();
    };
    el('#m-svc-add-livre').onclick = () => {
      const inp = el('#m-svc-livre'); const nome = inp.value.trim(); if (!nome) return;
      _osServicos.push({ nome, catalogo_id: '', origem: 'livre' });
      inp.value = ''; _renderOsServicos();
    };
    el('#m-save').onclick = () => salvarOS(a);
  }
  m.classList.remove('hidden');
}

function closeModal() { el('#modal').classList.add('hidden'); }
window.closeModal = closeModal;

async function salvarLeitura(a) {
  const v = parseFloat(el('#m-leitura').value);
  if (!isFinite(v) || v < 0) { toast('Leitura inválida', 'err'); return; }
  if (v < (a.uso_atual || 0)) { toast('Leitura menor que atual; rejeitada', 'err'); return; }
  const delta = v - (a.uso_atual || 0);
  const obs = el('#m-obs').value || null;
  await enqueueEvento({
    tipo: 'uso_atual_inc',
    payload: { ativo_id: a.id, delta, fonte: 'manutencao_periodica', obs },
  });
  // atualiza o ativo localmente
  a.uso_atual = v;
  await idb.put('ativos', a);
  await loadAll();
  closeModal();
  closeDetail();
  renderUI();
  toast(`Leitura registrada: +${delta} ${a.unidade_uso || ''}`);
}

// ─────────── OS: serviços + veículos (multi) ───────────
let _osServicos = [];

function _renderOsServicos() {
  const box = el('#m-svc-list'); if (!box) return;
  box.innerHTML = _osServicos.length
    ? _osServicos.map((s, i) => `<div style="display:flex;align-items:center;gap:6px;padding:4px 6px;border:1px solid var(--border,#234);border-radius:6px;margin-bottom:4px"><span style="flex:1;font-size:12px">${i + 1}. ${(s.nome || '').replace(/</g, '&lt;')}</span><small style="color:var(--text-dim)">${s.origem}</small><button type="button" class="btn" onclick="removeOsServico(${i})">✕</button></div>`).join('')
    : '<small style="color:var(--text-dim)">Nenhum serviço.</small>';
}
function removeOsServico(i) { _osServicos.splice(i, 1); _renderOsServicos(); }
window.removeOsServico = removeOsServico;

function _renderOsVeiculos() {
  const box = el('#m-veic-list'); if (!box) return;
  const veics = (state.ativos || []).filter(a => a.categoria === 'viaturas' || a.categoria === 'embarcacoes');
  box.innerHTML = veics.length
    ? veics.map(a => `<label style="display:flex;align-items:center;gap:6px;font-size:12px"><input type="checkbox" class="m-veic-ck" value="${a.id}" data-nome="${(a.nome || '').replace(/"/g, '&quot;')}"> ${a.nome || a.id}</label>`).join('')
    : '<small style="color:var(--text-dim)">Nenhuma viatura/embarcação.</small>';
}
function _coletarOsVeiculos() {
  return els('#m-veic-list .m-veic-ck').filter(c => c.checked).map(c => ({ ativo_id: c.value, nome: c.dataset.nome || c.value }));
}

async function salvarOS(a) {
  let titulo = el('#m-titulo').value.trim();
  if (!titulo && _osServicos.length) titulo = _osServicos[0].nome;
  if (!titulo) { toast('Título obrigatório', 'err'); return; }
  const tipo = el('#m-tipo').value;
  const prioridade = el('#m-prio').value;
  const categoria = el('#m-cat')?.value || '';
  const subcategoria = el('#m-subcat')?.value || '';
  const servicos = _osServicos.slice();
  const veiculos = _coletarOsVeiculos();
  const servico_id = (servicos.find(s => s.origem === 'catalogo') || {}).catalogo_id || '';
  const os_id = uuid();
  const os = {
    id: os_id,
    titulo,
    tipo,
    prioridade,
    categoria,
    subcategoria,
    servicos,
    veiculos,
    servico_id,
    status: 'aberta',
    ativo_id: a.id,
    modulo_origem: `pmoc:${state.categoria}`,
    solicitante_id: state.user?.id || 'dev',
    criada_em: now(),
  };
  await idb.put('ordens_servico', os);
  await enqueueEvento({ tipo: 'os_criada', payload: os });
  closeModal();
  renderTabHist(a);
  toast('OS criada e enfileirada');
}

// ─────────── EVENTOS PENDENTES ───────────
async function enqueueEvento({ tipo, payload }) {
  const ev = {
    id: uuid(),
    tipo,
    payload,
    ts: now(),
    tentativas: 0,
  };
  await idb.put('eventos_pendentes', ev);
  await refreshPendentes();
}

async function refreshPendentes() {
  state.pendentes = await idb.count('eventos_pendentes');
  const b = el('#pendentes');
  b.textContent = String(state.pendentes);
  b.dataset.zero = state.pendentes === 0 ? '1' : '0';
}

// ─────────── SYNC ───────────
function updateSyncStatus() {
  const s = el('#sync-status');
  const ls = el('#last-sync');
  cfg.get('last_sync').then(t => {
    ls.textContent = t ? `sincronizado em ${fmtDate(t)}` : 'nunca sincronizado';
  });
  cfg.get('seed_source').then(src => {
    el('#seed-source').textContent = `fonte: ${src || '?'}`;
  });

  if (!navigator.onLine) { s.textContent = 'offline'; s.className = 'sync-status'; return; }
  if (!state.token) { s.textContent = 'modo dev'; s.className = 'sync-status'; return; }
  s.textContent = 'pronto'; s.className = 'sync-status sync-ok';
}

async function doSync() {
  if (!navigator.onLine) { toast('Sem conexão', 'err'); return; }
  if (!state.token) { toast('Modo dev: sync desabilitado', 'err'); return; }
  const s = el('#sync-status');
  s.textContent = 'sincronizando…'; s.className = 'sync-status sync-busy';

  try {
    // push
    const pendentes = await idb.getAll('eventos_pendentes');
    if (pendentes.length) {
      const device_id = await getDeviceId();
      const resp = await fetch(`${NUCLEO}/api/sync/push`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${state.token}` },
        body: JSON.stringify({
          modulo: CATEGORIAS[state.categoria].modulo_sync,
          device_id,
          eventos: pendentes,
        }),
      });
      if (!resp.ok) throw new Error(`push ${resp.status}`);
      const data = await resp.json();
      for (const id of (data.aceitos || [])) {
        const ev = pendentes.find(p => p.id === id);
        if (ev) {
          await idb.put('eventos_aceitos', ev);
          await idb.delete('eventos_pendentes', id);
        }
      }
    }
    // pull incremental
    await pullFromNucleo();
    await loadAll();
    renderUI();
    await refreshPendentes();
    s.textContent = 'sincronizado'; s.className = 'sync-status sync-ok';
    toast('Sincronização concluída');
  } catch (e) {
    console.error(e);
    s.textContent = 'erro'; s.className = 'sync-status sync-err';
    toast('Falha na sincronização', 'err');
  }
  updateSyncStatus();
}

async function syncSilent() {
  if (!navigator.onLine || !state.token) return;
  try {
    await pullFromNucleo();
  } catch (e) { /* silent */ }
}

async function getDeviceId() {
  let id = await cfg.get('device_id');
  if (!id) { id = uuid(); await cfg.set('device_id', id); }
  return id;
}

// ─────────── START ───────────
window.addEventListener('DOMContentLoaded', boot);
