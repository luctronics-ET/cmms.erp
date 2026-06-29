/**
 * Módulo da página `manutencao` no cmasm_erp.html — refatoração V1.
 * Spec: docs/superpowers/specs/2026-05-19-manutencao-unificada-design.md
 */
(function () {
  'use strict';
  // depende de: window.engine (pmoc-engine.js) + window.ERP_MANUT_MOCKS (erp-manutencao-mocks.js)

  let initialized = false;

  // ── estado global do módulo ──────────────────────────────────────────────
  const state = {
    cats: new Set(),            // categorias selecionadas
    catsAvailable: [],          // derivado dos ativos carregados
    cache: { ativos: null, os: null, estoque: null, catalogo_servicos: null, planos_manutencao: null },
    activeTab: 'dashboard',
    tabDirty: { dashboard: true, os: true, planos: true, catalogo: true },
    _fetchError: null,          // { msg, hasCache } — consumido por _showPendingBanner()
  };

  // Navegação: Painel global + uma aba por categoria. Controle/Planos/Catálogo
  // viraram sub-abas DENTRO de cada categoria (escopadas), não mais globais.
  const TAB_DEFS = [
    { id: 'dashboard', icon: '📊', label: 'Painel' },
    { id: 'refrigeracao', icon: '❄️', label: 'Refrigeração' },
    { id: 'transportes',  icon: '🚚', label: 'Transportes' },
    { id: 'corte',        icon: '🌿', label: 'Máq. Corte' },
    { id: 'fonoclama',    icon: '📣', label: 'Fonoclama' },
    { id: 'registrar-uso', icon: '⏱', label: 'Registrar Uso' },
    { id: 'sobressalentes', icon: '🔩', label: 'Sobressalentes' },
  ];

  // categoria de navegação → categoria(s) de ativos no DB
  const CAT_DBCATS = {
    refrigeracao: ['climatizacao'],
    transportes:  ['viaturas', 'embarcacoes', 'frota_terrestre', 'frota_naval'],
    corte:        ['maquinas_corte'],
    fonoclama:    ['fonoclama'],
  };
  const CAT_FICHA_LABEL = {
    refrigeracao: 'Inventário', transportes: 'Frota', corte: 'Máquinas', fonoclama: 'Dispositivos',
  };

  // Configuração das fichas PMOC genéricas (mesmo molde de refrigeração, enxuto).
  const FICHA_CFG = {
    transportes: {
      endpoint: '/api/pmoc/transportes',
      cols: [
        { key: 'ativo_nome', label: 'Ativo' },
        { key: 'ativo_tipo', label: 'Tipo', filter: true },
        { key: 'ativo_categoria', label: 'Frota', filter: true },
        { key: 'ativo_subtipo', label: 'Lotação', filter: true },
        { key: 'combustivel', label: 'Combustível', filter: true, format: v => v || '—' },
      ],
      edit: [
        { key: 'estado_operacional', label: 'Estado', opts: ['OP', 'INOP'] },
        { key: 'criticidade', label: 'Criticidade', opts: ['CRÍTICA', 'ALTA', 'MÉDIA', 'BAIXA'] },
        { key: 'combustivel', label: 'Combustível', opts: ['', 'diesel', 'gasolina', 'flex'] },
        { key: 'tanque_l', label: 'Tanque (L)', type: 'number' },
        { key: 'oleo_ultima_uso', label: 'Óleo: uso na última troca', type: 'number' },
        { key: 'pneus_estado', label: 'Pneus', opts: ['', 'BOM', 'REGULAR', 'RUIM'] },
        { key: 'bateria_estado', label: 'Bateria', opts: ['', 'BOM', 'REGULAR', 'RUIM'] },
        { key: 'casco_estado', label: 'Casco (emb.)', opts: ['', 'BOM', 'REGULAR', 'RUIM'] },
        { key: 'renavam', label: 'RENAVAM' },
        { key: 'licenciamento_ate', label: 'Licenciamento até', type: 'date' },
        { key: 'seguro_ate', label: 'Seguro até', type: 'date' },
        { key: 'registro_naval', label: 'Registro naval (emb.)' },
        { key: 'ultima_manutencao', label: 'Última manutenção', type: 'date' },
        { key: 'obs', label: 'Observações', type: 'textarea' },
      ],
    },
    corte: {
      endpoint: '/api/pmoc/corte',
      cols: [
        { key: 'ativo_nome', label: 'Ativo' },
        { key: 'ativo_tipo', label: 'Tipo', filter: true },
        { key: 'motor_tempos', label: 'Motor', filter: true, format: v => v || '—' },
        { key: 'ferramenta_corte', label: 'Ferramenta', filter: true, format: v => v || '—' },
      ],
      edit: [
        { key: 'estado_operacional', label: 'Estado', opts: ['OP', 'INOP'] },
        { key: 'criticidade', label: 'Criticidade', opts: ['CRÍTICA', 'ALTA', 'MÉDIA', 'BAIXA'] },
        { key: 'motor_tempos', label: 'Motor', opts: ['', '2T', '4T', 'diesel'] },
        { key: 'combustivel', label: 'Combustível', opts: ['', 'gasolina', 'mistura_2t', 'diesel'] },
        { key: 'oleo_tipo', label: 'Óleo', opts: ['', 'SAE30', '10W-30', '15W-40'] },
        { key: 'oleo_ultima_uso', label: 'Óleo: horas na última troca', type: 'number' },
        { key: 'ferramenta_corte', label: 'Ferramenta', opts: ['', 'nylon', 'lamina', 'corrente', 'deck'] },
        { key: 'ultima_manutencao', label: 'Última manutenção', type: 'date' },
        { key: 'obs', label: 'Observações', type: 'textarea' },
      ],
    },
    fonoclama: {
      endpoint: '/api/pmoc/fonoclama',
      cols: [
        { key: 'ativo_nome', label: 'Dispositivo' },
        { key: 'ativo_tipo', label: 'Tipo', filter: true },
        { key: 'impedancia', label: 'Impedância', filter: true, format: v => v || '—' },
        { key: 'potencia_w', label: 'Potência (W)', format: v => v || '—' },
      ],
      edit: [
        { key: 'estado_operacional', label: 'Estado', opts: ['OP', 'INOP'] },
        { key: 'criticidade', label: 'Criticidade', opts: ['CRÍTICA', 'ALTA', 'MÉDIA', 'BAIXA'] },
        { key: 'potencia_w', label: 'Potência (W)', type: 'number' },
        { key: 'impedancia', label: 'Impedância', opts: ['', '8Ω', '70V', '100V'] },
        { key: 'tensao_linha', label: 'Tensão de linha' },
        { key: 'data_instalacao', label: 'Instalação', type: 'date' },
        { key: 'ultima_manutencao', label: 'Última manutenção', type: 'date' },
        { key: 'obs', label: 'Observações', type: 'textarea' },
      ],
    },
  };

  // ── persistência filtros ─────────────────────────────────────────────────
  const LS_KEY = 'xerp_manut_cats';

  // ── persistência histórico por unidade ───────────────────────────────────
  // Estrutura: { uid: { hor: number, regs: [...], manut: [...], ulm: {pid: hor} } }
  function getMH() {
    try { return JSON.parse(localStorage.getItem('xcmasm_manut_hist') || '{}'); }
    catch (_) { return {}; }
  }
  function saveMH(d) { try { localStorage.setItem('xcmasm_manut_hist', JSON.stringify(d)); } catch (_) {} }
  function getHistUnit(uid) {
    const mh = getMH(); return mh[uid] || { hor: 0, regs: [], manut: [], ulm: {} };
  }
  function saveHistUnit(uid, hist) {
    const mh = getMH(); mh[uid] = hist; saveMH(mh);
  }

  function resolveTipoCodigo(ativo) {
    const tipos = window.ERP_MANUT_MOCKS?.TIPOS || {};
    const byKey = Object.keys(tipos);
    const raw = [
      ativo?.tipo_codigo,
      ativo?.tipo,
      ativo?.cod,
      ativo?.codigo,
      ativo?.nome,
      ativo?.modelo,
      ativo?.fabricante,
    ]
      .filter(Boolean)
      .map(v => String(v).trim());

    for (const value of raw) {
      const upper = value.toUpperCase();
      if (tipos[upper]) return upper;
    }

    const clue = raw.join(' ').toLowerCase();
    if (/\bfs\s*[- ]?220\b|stihl\s*fs\s*220/.test(clue)) return 'FS220';
    if (/garthen|pro\s*[- ]?3500s|\bgar\b/.test(clue)) return 'GAR';
    if (/\bms\s*[- ]?650\b|motosserra/.test(clue)) return 'MS650';
    if (/coyote|\bct\s*[- ]?151\b|\bcoy\b/.test(clue)) return 'COY';
    if (/\blgt\s*[- ]?2654\b/.test(clue)) return 'LGT';
    if (/\bts\s*[- ]?114\b/.test(clue)) return 'TS114';
    if (/solis\s*90|\bsol\b/.test(clue)) return 'SOL';

    const fuzzy = byKey.find(k => clue.includes(k.toLowerCase()));
    return fuzzy || null;
  }

  // ── engine de planos preventivos (horímetro-based) ───────────────────────
  function calcProxManut(ativo) {
    const tipos = window.ERP_MANUT_MOCKS?.TIPOS || {};
    const tipoCodigo = resolveTipoCodigo(ativo);
    const tipo = tipoCodigo ? tipos[tipoCodigo] : null;
    if (!tipo) return [];
    const hist = getHistUnit(ativo.id);
    const hor = hist.hor || (ativo.horimetro || 0);
    return tipo.plano.map(m => {
      const ult = hist.ulm?.[m.id] || 0;
      const prox = ult === 0 ? m.iv : (Math.floor(ult / m.iv) + 1) * m.iv;
      const falt = prox - hor;
      const pct = Math.min(100, Math.max(0, ((hor - ult) / m.iv) * 100));
      const st = falt <= 0 ? 'danger' : falt <= m.iv * 0.15 ? 'warn' : falt <= m.iv * 0.30 ? 'proximo' : 'ok';
      return { ...m, ult, prox, falt, pct, st, hor, tipoCodigo };
    });
  }

  function derivePlanoServico(tipoCodigo, planoItem) {
    if (!tipoCodigo || !planoItem) return null;
    const tipo = window.ERP_MANUT_MOCKS?.TIPOS?.[tipoCodigo];
    const materiais = (planoItem.its || []).map(nome => ({
      nome_livre: nome,
      qtd: 1,
      unidade: 'un',
      obrigatorio: 1,
    }));
    return {
      id: `svc-plano-${String(tipoCodigo).toLowerCase()}-${planoItem.id}`,
      codigo: `${String(tipoCodigo).toUpperCase()}_${String(planoItem.id).toUpperCase()}`,
      nome: planoItem.n,
      descricao: `Plano preventivo por horímetro para ${tipo?.nome || tipoCodigo}.`,
      escopo: 'central',
      versao: 1,
      tempo_estimado_min: Math.max(30, 20 + (materiais.length * 15)),
      aplicavel_a: {
        categorias: tipo?.categoria ? [tipo.categoria] : [],
        tipos: [tipoCodigo],
      },
      criado_por_modulo: 'manutencao',
      ativo: 1,
      materiais,
      ferramentas: [],
      pessoal: [{ qualificacao_codigo: 'operador_corte', qtd: 1, opcional: 0 }],
    };
  }

  function resolvePlanoServico(plano) {
    if (!plano) return null;
    if (plano._svc) return plano._svc;
    const fromCache = (state.cache.catalogo_servicos?.data || []).find(s => s.id === plano.servico_id);
    if (fromCache) return fromCache;
    const fromCatalog = (window.ERP_MANUT_MOCKS?.catalogo_servicos || []).find(s => s.id === plano.servico_id);
    if (fromCatalog) return fromCatalog;
    return derivePlanoServico(plano.tipo_codigo, plano._planoItem || plano);
  }

  function getManutServicos(record) {
    if (Array.isArray(record?.servicos) && record.servicos.length) return record.servicos;
    return (record?.itens || []).map((nome, idx) => ({
      id: `${record?.id || 'm'}-svc-${idx}`,
      nome,
      materiais: [],
    }));
  }

  function getManutMateriais(record) {
    if (Array.isArray(record?.materiais) && record.materiais.length) return record.materiais;
    return getManutServicos(record)
      .flatMap(servico => servico.materiais || [])
      .filter(Boolean);
  }

  function getManutServicoLabels(record) {
    return getManutServicos(record).map(servico => servico.nome).filter(Boolean);
  }

  function getManutMaterialLabels(record) {
    const seen = new Set();
    return getManutMateriais(record)
      .map(material => material?.nome_livre || material?.nome)
      .filter(nome => {
        if (!nome || seen.has(nome)) return false;
        seen.add(nome);
        return true;
      });
  }

  function getDerivedPlanRows() {
    const cachedPlanos = state.cache.planos_manutencao?.data || [];
    const byServicoTipo = new Map(
      cachedPlanos
        .filter(plano => plano?.servico_id && plano?.tipo_codigo)
        .map(plano => [`${plano.tipo_codigo}::${plano.servico_id}`, plano])
    );
    return filteredAtivos().flatMap(ativo => calcProxManut(ativo).map(planoItem => {
      const tipoCodigo = planoItem.tipoCodigo || resolveTipoCodigo(ativo);
      if (!tipoCodigo) return null;
      const svcId = `svc-plano-${String(tipoCodigo).toLowerCase()}-${planoItem.id}`;
      const cacheKey = `${tipoCodigo}::${svcId}`;
      return {
      ...(byServicoTipo.get(cacheKey) || {}),
      id: (byServicoTipo.get(cacheKey) || {}).id || `plano-${ativo.id}-${planoItem.id}`,
      ativo_id: ativo.id,
      tipo_codigo: tipoCodigo,
      servico_id: svcId,
      frequencia: { tipo: 'por_uso', valor: planoItem.iv, unidade: 'h' },
      ultima_execucao: planoItem.ult > 0 ? fH(planoItem.ult) : 'Nunca',
      proxima_execucao: fH(planoItem.prox),
      responsavel_pmoc: (byServicoTipo.get(cacheKey) || {}).responsavel_pmoc || '',
      _status: planoItem.st,
      _planoItem: planoItem,
      _ativo: ativo,
      _svc: resolvePlanoServico({
        ...(byServicoTipo.get(cacheKey) || {}),
        tipo_codigo: tipoCodigo,
        servico_id: svcId,
        _planoItem: planoItem,
      }),
    };
    }).filter(Boolean));
  }

  function getCatalogoServicos() {
    const staticServices = window.ERP_MANUT_MOCKS?.catalogo_servicos || [];
    const cachedServices = state.cache.catalogo_servicos?.data || [];
    const derivedServices = getDerivedPlanRows().map(row => row._svc).filter(Boolean);
    const byId = new Map();
    [...staticServices, ...cachedServices, ...derivedServices].forEach(servico => {
      if (servico?.id && !byId.has(servico.id)) byId.set(servico.id, servico);
    });
    return [...byId.values()];
  }

  function loadFilter() {
    const url = new URLSearchParams(location.search).get('cats');
    if (url) return url.split(',').filter(Boolean);
    try { return JSON.parse(localStorage.getItem(LS_KEY) || '[]'); }
    catch (_) { return []; }
  }

  function saveFilter() {
    const arr = [...state.cats];
    localStorage.setItem(LS_KEY, JSON.stringify(arr));
    const url = new URL(location.href);
    if (arr.length) url.searchParams.set('cats', arr.join(','));
    else url.searchParams.delete('cats');
    history.replaceState(null, '', url.toString());
  }

  function markAllDirty() { for (const k of Object.keys(state.tabDirty)) state.tabDirty[k] = true; }

  function resolveApiBase() {
    if (window.XCMASM_API_BASE && typeof window.XCMASM_API_BASE === 'string') {
      return window.XCMASM_API_BASE.replace(/\/$/, '');
    }
    if (location.protocol === 'file:') {
      return 'http://localhost:8010';
    }
    return '';
  }

  function apiUrl(path) {
    const base = resolveApiBase();
    return `${base}${path}`;
  }

  function boot() {
    if (initialized) return;
    const root = document.getElementById('manut-root');
    if (!root) { console.warn('[manut] #manut-root não encontrado'); return; }
    if (!window.engine) {
      console.warn('[manut] pmoc-engine.js não carregado');
      return; // não seta initialized → permite nova tentativa
    }
    initialized = true;
    // Migra dados de PMOCs legados (maq-corte, refrigeracao) na primeira execução
    try { migrarDadosLegados(); } catch (e) { console.warn('[manut] migração legada falhou:', e); }
    fetchAll().finally(() => { render(root); _showPendingBanner(); });
  }

  // ── render principal ─────────────────────────────────────────────────────
  function render(root) {
    state.cats = new Set(loadFilter());
    root.replaceChildren(
      renderTopBar(),
      renderTabBar(),
      renderTabContainer(),
    );
    renderActiveTab();
  }

  function renderTopBar() {
    const { el } = window.engine.utils;
    return el('div', { style: {
      position: 'sticky', top: '0', zIndex: '5',
      background: 'var(--bg)', padding: '12px 0', marginBottom: '12px',
      borderBottom: '1px solid var(--line)',
    } },
      el('div', { style: { display: 'flex', alignItems: 'center', gap: '12px' } },
        el('h2', { style: { margin: 0, fontSize: '18px' } }, 'Manutenção'),
        el('div', { style: { flex: 1 } }),
        el('button', { class: 'pe-btn pe-btn--ghost', title: 'Recarregar do núcleo',
          onclick: () => fetchAll().finally(() => { markAllDirty(); renderActiveTab(); _showPendingBanner(); }),
        }, '↻'),
        el('button', { class: 'pe-btn', onclick: () => openPlanoCreate() }, '+ Plano'),
        el('button', { class: 'pe-btn pe-btn--primary', onclick: () => {
          if (typeof window.novaOSManut === 'function') window.novaOSManut('');
          else toast('Abra Serviços → Nova OS', 'amber');
        } }, '+ OS'),
      ),
    );
  }

  function renderTabBar() {
    const { el } = window.engine.utils;
    const bar = el('div', { id: 'manut-tabbar', style: {
      display: 'flex', gap: '4px', padding: '4px',
      background: 'var(--bg2)', borderRadius: '8px',
      marginBottom: '14px', overflowX: 'auto',
    } });
    function updateStyles() {
      bar.querySelectorAll('[data-tab]').forEach(b => {
        const on = b.dataset.tab === state.activeTab;
        Object.assign(b.style, {
          background: on ? 'var(--panel)' : 'transparent',
          color: on ? 'var(--ink)' : 'var(--ink-2)',
          boxShadow: on ? 'inset 0 -2px 0 var(--acc)' : 'none',
        });
      });
    }
    TAB_DEFS.forEach(t => {
      bar.appendChild(el('button', {
        class: 'pe-btn pe-btn--ghost',
        dataset: { tab: t.id },
        style: { borderRadius: '6px', minHeight: '32px', whiteSpace: 'nowrap' },
        onclick: () => {
          state.activeTab = t.id;
          updateStyles();
          renderActiveTab();
        },
      }, `${t.icon} ${t.label}`));
    });
    state._updateTabStyles = updateStyles;
    updateStyles();
    return bar;
  }

  function renderTabContainer() {
    const { el } = window.engine.utils;
    return el('div', { id: 'manut-tab-content' });
  }

  function renderActiveTab() {
    const cont = document.getElementById('manut-tab-content');
    if (!cont) return;
    const id = state.activeTab;
    // tasks 6-13 substituem este placeholder por renderers reais
    if (!RENDERERS[id]) {
      cont.replaceChildren(window.engine.utils.el('div',
        { style: { padding: '24px', color: 'var(--ink-3)' } },
        `Tab "${id}" — pendente (Tasks 6-13).`));
      return;
    }
    RENDERERS[id](cont);
    state.tabDirty[id] = false;
  }

  // ── helpers de derivação (filtrados pela categoria ativa) ────────────────
  // _scopeCats = escopo forçado por uma aba de categoria (Refrigeração, etc).
  // Quando nulo (ex.: Painel), usa o filtro de chips global (state.cats).
  function activeCats() {
    if (state._scopeCats && state._scopeCats.length) return new Set(state._scopeCats);
    return state.cats;
  }
  function filteredAtivos() {
    const all = state.cache.ativos?.data || [];
    const cats = activeCats();
    if (cats.size === 0) return all;
    return all.filter(a => cats.has(a.categoria));
  }
  /** OS filtradas por categoria. OS sem ativo_id (manuais, sem vínculo)
   *  passam por todos os filtros — são consideradas globais. */
  function filteredOS() {
    const all = state.cache.os?.data || [];
    const cats = activeCats();
    if (cats.size === 0) return all;
    const ativosIds = new Set(filteredAtivos().map(a => a.id));
    return all.filter(o => !o.ativo_id || ativosIds.has(o.ativo_id));
  }
  function estoqueBaixo() {
    const all = state.cache.estoque?.data || [];
    return all.filter(i => (i.qtd_atual ?? 0) < (i.qtd_minima ?? 0));
  }

  // ── categoria com sub-abas (Ficha · Controle · Planos · Catálogo) ────────
  function renderCategory(cont, key) {
    const { el } = window.engine.utils;
    state._scopeCats = CAT_DBCATS[key] || null;

    // Refrigeração: funde as views do app refrig (Inventário/Alertas/… ) com as
    // sub-abas genéricas numa ÚNICA linha — evita 3ª fila de abas. As demais
    // categorias mantêm Ficha/Controle/Vencimentos/Planos/Catálogo.
    const refrigSubs = (key === 'refrigeracao' && window.erpRefrig && window.erpRefrig.subs) || [];
    const refrigIds = new Set(refrigSubs.map(s => s.id));
    const SUBS = key === 'refrigeracao'
      ? [...refrigSubs,
         { id: 'os',          label: '🗂️ Controle' },
         { id: 'vencimentos', label: '⏰ Vencimentos' },
         { id: 'planos',      label: '📋 Planos' }]
      : [{ id: 'ficha',       label: CAT_FICHA_LABEL[key] || 'Ficha' },
         { id: 'os',          label: 'Controle' },
         { id: 'vencimentos', label: 'Vencimentos' },
         { id: 'planos',      label: 'Planos' },
         { id: 'catalogo',    label: 'Catálogo' }];

    // _catSub é global; valida contra as subs desta categoria.
    let sub = state._catSub;
    if (!SUBS.some(s => s.id === sub)) sub = state._catSub = SUBS[0].id;

    const bar = el('div', { style: {
      display: 'flex', gap: '4px', marginBottom: '12px',
      borderBottom: '1px solid var(--line)', paddingBottom: '8px', flexWrap: 'wrap',
    } }, ...SUBS.map(s => el('button', {
      class: 'pe-btn ' + (s.id === sub ? 'pe-btn--primary' : 'pe-btn--ghost'),
      style: { borderRadius: '6px' },
      onclick: () => { state._catSub = s.id; renderCategory(cont, key); },
    }, s.label)));
    const body = el('div');
    cont.replaceChildren(bar, body);

    if (refrigIds.has(sub)) {
      window.erpRefrig.showSub(body, sub);
    } else if (sub === 'ficha') {
      renderFichaTab(body, key);
    } else if (sub === 'os')          RENDERERS.os(body);
    else if (sub === 'vencimentos')   renderVencimentos(body);
    else if (sub === 'planos')        RENDERERS.planos(body);
    else if (sub === 'catalogo')      RENDERERS.catalogo(body);
  }

  // ── Vencimentos (o que está por vencer, por categoria) ───────────────────
  async function renderVencimentos(body) {
    const { el, fmt } = window.engine.utils;
    body.replaceChildren(el('div', { style: { padding: '16px', color: 'var(--ink-3)' } }, 'Calculando vencimentos...'));
    const cats = [...activeCats()];
    let rows = [];
    try {
      const reqs = (cats.length ? cats : ['']).map(c =>
        fetch(apiUrl('/api/manutencao/vencimentos' + (c ? `?categoria=${encodeURIComponent(c)}` : '')))
          .then(r => r.ok ? r.json() : []));
      rows = (await Promise.all(reqs)).flat();
    } catch (e) {
      body.replaceChildren(el('div', { style: { padding: '16px', color: 'var(--red)' } }, 'Falha: ' + e.message));
      return;
    }
    const wrap = el('div');
    body.replaceChildren(wrap);
    if (!rows.length) {
      wrap.appendChild(el('div', { style: { padding: '24px', color: 'var(--ink-3)', textAlign: 'center' } },
        'Sem planos aplicáveis aos ativos desta categoria (disparo por tempo não é listado).'));
      return;
    }
    window.engine.table(wrap, {
      cols: [
        { key: 'status', label: '', format: v => v === 'warn' ? '🟡' : '🟢' },
        { key: 'ativo_nome', label: 'Ativo', filter: true },
        { key: 'servico', label: 'Serviço' },
        { key: 'intervalo', label: 'Intervalo', format: (v, r) => `${v} ${r.unidade || ''}` },
        { key: 'uso_atual', label: 'Uso', format: (v, r) => `${fmt.num(v || 0, 0)} ${r.unidade || ''}` },
        { key: 'proximo', label: 'Próximo', format: (v, r) => `${fmt.num(v, 0)} ${r.unidade || ''}` },
        { key: 'falta', label: 'Falta', format: (v, r) => el('span',
          { style: { color: r.status === 'warn' ? 'var(--amber)' : 'var(--ink)', fontWeight: r.status === 'warn' ? '700' : '400', fontFamily: 'var(--font-mono)' } },
          `${fmt.num(v, 0)} ${r.unidade || ''}`) },
        { key: '_acao', label: '', format: (v, r) => el('div', { style: { display: 'flex', gap: '4px' } },
          el('button', {
            class: 'pe-btn pe-btn--primary', style: { padding: '2px 8px', fontSize: '11px' }, title: 'Cria OS direto (liga serviço p/ baixa de estoque)',
            onclick: async (e) => { e.stopPropagation(); await gerarOsVencimento(r); },
          }, 'Gerar OS'),
          el('button', {
            class: 'pe-btn', style: { padding: '2px 8px', fontSize: '11px' }, title: 'Abre Nova OS preenchida (revisar antes)',
            onclick: (e) => { e.stopPropagation();
              if (window.novaOSComContexto) window.novaOSComContexto({
                ativoId: r.ativo_id, assunto: `${r.servico} · ${r.ativo_nome}`,
                descricao: `Preventiva do plano "${r.plano_nome}" — a cada ${r.intervalo} ${r.unidade || ''}.`,
              });
            },
          }, 'Nova OS…')) },
      ],
      rows,
      pageSize: Math.max(rows.length, 30),
    });
  }

  async function gerarOsVencimento(r) {
    try {
      const resp = await fetch(apiUrl('/api/manutencao/os-preventiva'), {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ativo_id: r.ativo_id, servico_id: r.servico_id }),
      });
      if (!resp.ok) throw new Error('HTTP ' + resp.status);
      const os = await resp.json();
      toast('OS gerada: ' + (os.codigo || ''), 'green');
      state.tabDirty.os = true;
    } catch (e) { toast('Falha ao gerar OS: ' + e.message, 'red'); }
  }

  // ── renderers de cada tab ────────────────────────────────────────────────
  const RENDERERS = {
    refrigeracao(cont) { renderCategory(cont, 'refrigeracao'); },
    transportes(cont)  { renderCategory(cont, 'transportes'); },
    corte(cont)        { renderCategory(cont, 'corte'); },
    fonoclama(cont)    { renderCategory(cont, 'fonoclama'); },
    dashboard(cont) {
      state._scopeCats = null;  // Painel = global (respeita chips)
      const { el, fmt } = window.engine.utils;
      const ativos = filteredAtivos();
      const os = filteredOS();
      const baixo = estoqueBaixo();
      const osPorStatus = {};
      for (const o of os) osPorStatus[o.status] = (osPorStatus[o.status] || 0) + 1;

      const KPIS = [
        { label: 'Ativos no filtro', value: ativos.length, sub: `${ativos.filter(a => a.ativo).length} em serviço` },
        { label: 'OS abertas',       value: os.filter(o => o.status !== 'concluida' && o.status !== 'cancelada').length },
        { label: 'OS concluídas',    value: os.filter(o => o.status === 'concluida').length },
        { label: 'Estoque baixo',    value: baixo.length, sub: 'itens < min' },
      ];

      const kpiGrid = el('div', { style: {
        display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(160px,1fr))',
        gap: '12px', marginBottom: '14px',
      } }, ...KPIS.map(k => el('div', { style: {
        background: 'var(--panel)', border: '1px solid var(--line)',
        borderRadius: '8px', padding: '12px',
      } },
        el('div', { style: { fontSize: '11px', color: 'var(--ink-3)', textTransform: 'uppercase', letterSpacing: '.5px' } }, k.label),
        el('div', { style: { fontFamily: 'var(--font-mono)', fontSize: '24px', color: 'var(--acc)', fontWeight: '700', marginTop: '4px' } }, String(k.value)),
        k.sub ? el('div', { style: { fontSize: '11px', color: 'var(--ink-2)' } }, k.sub) : null,
      )));

      const charts = el('div', { style: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px', marginBottom: '14px' } });
      const donutEl = el('div'); const lineEl = el('div');
      charts.appendChild(donutEl); charts.appendChild(lineEl);

      window.engine.chartDonut(donutEl, {
        title: 'OS por status',
        data: Object.entries(osPorStatus).map(([label, value]) => ({
          label, value,
          color: ({
            aberta: 'var(--blue)', em_execucao: 'var(--amber)',
            concluida: 'var(--green)', cancelada: 'var(--red)',
          })[label] || 'var(--ink-3)',
        })),
        totalLabel: 'OS',
      });
      // Line chart: mês x OS concluídas naquele mês
      const byMonth = {};
      for (const o of os.filter(x => x.status === 'concluida' && x.data_conclusao)) {
        const m = (o.data_conclusao || '').slice(0, 7);
        byMonth[m] = (byMonth[m] || 0) + 1;
      }
      const months = Object.keys(byMonth).sort().slice(-12);
      window.engine.chartLine(lineEl, {
        title: 'OS concluídas/mês (12m)',
        series: [{ label: 'Concluídas', points: months.map((m, i) => ({ x: i + 1, y: byMonth[m] })) }],
      });

      const alertas = el('div', {
        style: { background: 'var(--panel)', border: '1px solid var(--line)', borderRadius: '8px', padding: '12px' },
      },
        el('div', { style: { fontWeight: '600', marginBottom: '8px' } }, 'Alertas críticos'),
        baixo.length === 0 ? el('div', { style: { color: 'var(--ink-3)', fontSize: '13px' } }, 'Nenhum alerta de estoque') :
        el('ul', { style: { margin: 0, paddingLeft: '18px', fontSize: '13px' } },
          ...baixo.slice(0, 10).map(i => el('li', {}, `${i.nome} · saldo ${fmt.num(i.qtd_atual)} < min ${fmt.num(i.qtd_minima)}`))),
      );

      // Frota vinculada — status resumo
      const frota = window.getFrota?.() || [];
      const frotaCard = frota.length > 0 ? el('div', {
        style: { background: 'var(--panel)', border: '1px solid var(--line)', borderRadius: '8px', padding: '12px', marginTop: '12px' },
      },
        el('div', { style: { fontWeight: '600', marginBottom: '10px' } }, 'Frota vinculada aos ativos'),
        el('div', { style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(200px,1fr))', gap: '8px' } },
          ...frota.filter(f => f.ativoId).map(f => {
            const ativo = ativos.find(a => a.id === f.ativoId);
            const osA = os.filter(o => o.ativo_id === f.ativoId && o.status !== 'concluida' && o.status !== 'cancelada').length;
            const badgeKind = { P: 'green', OR: 'blue', INOP: 'red', MANUT: 'amber' }[f.status] || 'gray';
            return el('div', { style: { padding: '8px 10px', background: 'var(--bg3)', borderRadius: '6px', fontSize: '12px' } },
              el('div', { style: { fontWeight: '600', marginBottom: '3px' } }, f.nome),
              el('div', { style: { color: 'var(--ink-3)' } }, ativo ? ativo.nome : f.ativoId),
              el('div', { style: { display: 'flex', gap: '6px', marginTop: '4px', alignItems: 'center' } },
                window.engine.badge(f.status, badgeKind),
                osA > 0 ? window.engine.badge(`${osA} OS`, 'amber') : null,
              ),
            );
          }),
        ),
      ) : null;

      cont.replaceChildren(kpiGrid, charts, alertas, ...(frotaCard ? [frotaCard] : []));
    },

    ativos(cont) {
      const { el, fmt } = window.engine.utils;
      const rows = filteredAtivos();
      const wrap = el('div');
      cont.replaceChildren(wrap);
      window.engine.table(wrap, {
        cols: [
          { key: 'id', label: '', format: v => {
            const st = statusManutAtivo(v);
            return st === 'danger' ? '🔴' : st === 'warn' ? '🟡' : st === 'ok' ? '🟢' : '';
          }},
          { key: 'nome', label: 'Nome' },
          { key: 'tipo', label: 'Tipo', filter: true },
          { key: 'categoria', label: 'Categoria', filter: true },
          { key: 'criticidade', label: 'Criticidade', filter: true,
            format: v => v ? window.engine.badge(v,
              v === 'critico_24x7' ? 'red' : v === 'operacional' ? 'amber' : 'green') : '—' },
          { key: 'uso_atual', label: 'Uso atual', format: v => fmt.num(v, 1) },
          { key: 'unidade_uso', label: 'Un' },
          { key: 'responsavel_pmoc', label: 'PMOC dono', filter: true },
        ],
        rows,
        pageSize: Math.max(rows.length, 25),
        onRowClick: openAtivoDrawer,
      });
    },

    os(cont) {
      const { el } = window.engine.utils;
      const view = state._osView || (state._osView = 'kanban');
      const toggleWrap = el('div', { style: { marginBottom: '10px', display: 'flex', gap: '4px' } },
        el('button', {
          class: 'pe-btn ' + (view === 'kanban' ? 'pe-btn--primary' : 'pe-btn--ghost'),
          onclick: () => { state._osView = 'kanban'; RENDERERS.os(cont); },
        }, 'Kanban'),
        el('button', {
          class: 'pe-btn ' + (view === 'lista' ? 'pe-btn--primary' : 'pe-btn--ghost'),
          onclick: () => { state._osView = 'lista'; RENDERERS.os(cont); },
        }, 'Lista'),
        el('button', {
          class: 'pe-btn ' + (view === 'calendario' ? 'pe-btn--primary' : 'pe-btn--ghost'),
          onclick: () => { state._osView = 'calendario'; RENDERERS.os(cont); },
        }, 'Calendário'),
      );
      const body = el('div');
      cont.replaceChildren(toggleWrap, body);

      if (view === 'kanban') renderOsKanban(body);
      else if (view === 'calendario') renderOsCalendar(body);
      else renderOsLista(body);
    },

    async planos(cont) {
      const { el } = window.engine.utils;
      cont.replaceChildren(el('div', { style: { padding: '16px', color: 'var(--ink-3)' } }, 'Carregando planos...'));
      const cats = [...activeCats()];
      let planos = [];
      try {
        const reqs = (cats.length ? cats : ['']).map(c =>
          fetch(apiUrl('/api/catalogo/planos-catalogo' + (c ? `?categoria=${encodeURIComponent(c)}` : '')))
            .then(r => r.ok ? r.json() : []));
        planos = (await Promise.all(reqs)).flat();
      } catch (e) {
        cont.replaceChildren(el('div', { style: { padding: '16px', color: 'var(--red)' } }, 'Falha ao carregar planos: ' + e.message));
        return;
      }
      const wrap = el('div');
      cont.replaceChildren(wrap);
      if (!planos.length) {
        wrap.appendChild(el('div', { style: { padding: '24px', color: 'var(--ink-3)', textAlign: 'center' } },
          'Nenhum plano cadastrado para esta categoria. (Plano = pacote nomeado de serviços + disparo por h/km/tempo.)'));
        return;
      }
      window.engine.table(wrap, {
        cols: [
          { key: 'codigo', label: 'Código' },
          { key: 'nome', label: 'Plano' },
          { key: 'aplicavel_tipos', label: 'Tipos', format: v => {
            try { return JSON.parse(v || '[]').join(', ') || '—'; } catch (_) { return v || '—'; }
          } },
          { key: 'n_servicos', label: 'Serviços', format: (v, r) => `${v || 0} (${r.n_preventivos || 0} prev)` },
          { key: 'frequencia', label: 'Disparo', format: v => fmtFreq(v) },
        ],
        rows: planos,
        pageSize: Math.max(planos.length, 25),
        onRowClick: row => openPlanoCatalogoDrawer(row),
      });
    },

    catalogo(cont) {
      const { el } = window.engine.utils;
      const cats = activeCats();
      let servicos = getCatalogoServicos();
      if (cats.size > 0) {
        servicos = servicos.filter(s => {
          const aplic = s.aplicavel_a?.categorias || [];
          return aplic.length === 0 ? false : aplic.some(c => cats.has(c));
        });
      }
      const wrap = el('div');
      cont.replaceChildren(wrap);
      window.engine.table(wrap, {
        cols: [
          { key: 'codigo', label: 'Código' },
          { key: 'nome', label: 'Nome' },
          { key: 'aplicavel_a', label: 'Categorias', format: v =>
            (v?.categorias || []).join(', ') || '—' },
          { key: 'tempo_estimado_min', label: 'Tempo (min)',
            format: v => v ? `${v} min` : '—' },
          { key: 'versao', label: 'Versão',
            format: v => window.engine.badge(`v${v}`, 'blue') },
          { key: 'materiais', label: 'Materiais',
            format: v => `${(v || []).length} itens` },
        ],
        rows: servicos,
        onRowClick: row => openCatalogoDrawer(row),
      });
    },

    estoque(cont) {
      const { el, fmt } = window.engine.utils;
      const all = state.cache.estoque?.data || [];
      const relevancia = window.ERP_MANUT_MOCKS?.estoque_relevancia || {};
      const cats = [...state.cats];
      let rows = all;
      if (cats.length > 0) {
        const rel = new Set(cats.flatMap(c => relevancia[c] || []));
        if (rel.size > 0) rows = all.filter(i => rel.has(i.codigo) || rel.has(i.id) || (i.qtd_atual ?? 0) < (i.qtd_minima ?? 0));
      }
      const wrap = el('div');
      cont.replaceChildren(wrap);
      if (!rows.length) {
        wrap.appendChild(el('div', { style: { padding: '24px', color: 'var(--ink-3)', textAlign: 'center' } },
          cats.length > 0 ? 'Nenhum item relevante para as categorias selecionadas.' : 'Estoque vazio ou API indisponível.'));
        return;
      }
      window.engine.table(wrap, {
        cols: [
          { key: 'nome', label: 'Item' },
          { key: 'codigo', label: 'Código' },
          { key: 'unidade', label: 'Un' },
          { key: 'qtd_atual', label: 'Atual', format: (v, row) => {
            const low = (v ?? 0) < (row.qtd_minima ?? 0);
            return el('span', { style: { color: low ? 'var(--red)' : 'var(--ink)', fontFamily: 'var(--font-mono)', fontWeight: low ? '700' : '400' } }, fmt.num(v ?? 0, 0));
          }},
          { key: 'qtd_minima', label: 'Mínimo', format: v => fmt.num(v ?? 0, 0) },
          { key: 'qtd_atual', label: 'Status', format: (v, row) =>
            (v ?? 0) < (row.qtd_minima ?? 0) ?
              window.engine.badge('Baixo', 'red') :
              window.engine.badge('OK', 'green') },
        ],
        rows,
      });
    },

    calgantt(cont) {
      const { el } = window.engine.utils;
      const upcoming = getDerivedPlanRows()
        .map(p => ({ ...p, _diff: p._planoItem?.falt ?? null, _svc: p._svc }))
        .sort((a, b) => (a._diff ?? Number.POSITIVE_INFINITY) - (b._diff ?? Number.POSITIVE_INFINITY));

      cont.replaceChildren(
        el('div', { style: { padding: '4px 0 12px', fontWeight: '600', fontSize: '15px' } }, 'Próximas manutenções por horímetro'),
        el('div', { style: { display: 'flex', flexDirection: 'column', gap: '6px' } },
          ...upcoming.slice(0, 20).map(p => {
            const color = p._diff < 0 ? 'var(--red)' : p._diff <= (p._planoItem?.iv || 0) * 0.15 ? 'var(--amber)' : p._diff <= (p._planoItem?.iv || 0) * 0.30 ? 'var(--acc)' : 'var(--green)';
            const label = p._diff < 0 ? `Vencida há ${Math.abs(p._diff).toFixed(0)} h` : `Em ${Math.max(0, p._diff).toFixed(0)} h`;
            return el('div', { style: {
              display: 'flex', gap: '12px', alignItems: 'center',
              padding: '8px 12px', background: 'var(--panel)',
              border: `1px solid ${color}30`, borderLeft: `3px solid ${color}`,
              borderRadius: '6px', fontSize: '13px',
            } },
              el('div', { style: { minWidth: '120px', fontFamily: 'var(--font-mono)', fontSize: '11px', color } }, label),
              el('div', { style: { flex: 1 } }, p._svc?.nome || p.servico_id),
              el('div', { style: { fontSize: '11px', color: 'var(--ink-3)' } }, p._ativo?.nome || '—'),
            );
          }),
          ...(upcoming.length === 0 ? [el('div', { style: { color: 'var(--ink-3)', padding: '12px' } }, 'Nenhum plano preventivo disponível no filtro atual.')] : []),
        ),
      );
    },

    eam(cont) {
      const mocks = window.ERP_MANUT_MOCKS || {};
      const ITENS = mocks.ITENS_EAM || [];
      const VALS  = mocks.VALORES_EAM || {};

      // Persistent state across re-renders
      const es = state._eamSt || (state._eamSt = { tipo: 'TS114', nivel: 'O', perIdx: 2, sub: 'matriz' });

      // Dynamic periods from today
      const hoje = new Date();
      const yr   = hoje.getFullYear();
      const jun  = new Date(yr, 5, 30);
      const dez  = new Date(yr, 11, 31);
      const diff = d => Math.max(7, Math.round((d - hoje) / 86400000));
      const H_SEM = 40; // 8h/dia × 5 dias
      const hMaq  = d => Math.round((d / 7) * H_SEM * 10) / 10;
      const PERS  = [
        { id: '1sem', label: '1 Semana', dias: 7 },
        { id: '1mes', label: '1 Mês',    dias: 30 },
        { id: 'jun',  label: '→ Jun',    dias: diff(jun) },
        { id: 'dez',  label: '→ Dez',    dias: diff(dez) },
      ];

      const per   = PERS[es.perIdx];
      const H     = hMaq(per.dias);
      const ativos = filteredAtivos();
      const nMaq  = Math.max(1, ativos.filter(a => a.tipo === es.tipo).length);
      const hasEAM = ITENS.length > 0;

      const TIPOS_LIST = Object.keys(mocks.TIPOS || {});

      const fR = v => 'R$ ' + Number(v).toFixed(2).replace('.', ',').replace(/\B(?=(\d{3})+(?!\d))/g, '.');
      const fH2 = h => Number(h).toFixed(1) + ' h';
      const CAT_C = { corte: '#f59e0b', motor: '#3b82f6', rodagem: '#ef4444', eletrico: '#14b8a6', fixador: '#6b7280' };

      function calcQtd(it, h) {
        if (it.iv >= 9999) return nMaq;
        return Math.max(1, Math.ceil((h / it.iv) * (it.qe || 1))) * nMaq;
      }
      function calcNivel(niv, h) {
        const fn = { E: i => i.E, R: i => i.R, O: i => i.O }[niv];
        const items = ITENS.filter(fn);
        let total = 0;
        const itens = items.map(it => {
          const q = calcQtd(it, h); const c = Math.round(q * it.p * 100) / 100;
          total += c; return { ...it, q, c };
        });
        return { total: Math.round(total * 100) / 100, itens };
      }

      // ── sub-tab renderers ─────────────────────────────────────────────────
      function subMatriz() {
        if (!hasEAM) return `<div style="padding:20px;color:var(--ink-3)">Dados EAM disponíveis apenas para TS114.</div>`;
        const rows = PERS.map((p, i) => {
          const h = hMaq(p.dias);
          const E = calcNivel('E', h), R = calcNivel('R', h), O = calcNivel('O', h);
          return { p, i, h, E, R, O };
        });
        const NL = { E: 'Essencial', R: 'Regular', O: 'Ótimo' };
        const NC = { E: 'var(--amber)', R: 'var(--acc)', O: 'var(--green)' };
        const cur = rows[es.perIdx];
        let kpis = `<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:14px">
          ${['E','R','O'].map(n => `<div style="background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:12px;border-left:3px solid ${NC[n]}">
            <div style="font-size:10px;color:var(--ink-3);text-transform:uppercase;margin-bottom:4px">${NL[n]} · ${per.label}</div>
            <div style="font-family:var(--font-mono);font-size:20px;color:${NC[n]};font-weight:700">${fR(cur[n].total)}</div>
            <div style="font-size:11px;color:var(--ink-3)">${cur[n].itens.length} itens · ${nMaq} máq</div>
          </div>`).join('')}
        </div>`;

        let matTable = `<div style="overflow-x:auto;margin-bottom:14px"><table style="width:100%;border-collapse:collapse;font-size:12px">
          <thead><tr style="background:var(--panel)">
            <th style="padding:7px 10px;text-align:left;font-size:10px;color:var(--ink-3);text-transform:uppercase;border-bottom:1px solid var(--line)">Período</th>
            <th style="padding:7px 10px;text-align:right;font-size:10px;color:var(--ink-3);text-transform:uppercase;border-bottom:1px solid var(--line)">h/máq</th>
            <th style="padding:7px 10px;text-align:right;color:var(--amber);font-size:10px;text-transform:uppercase;border-bottom:1px solid var(--line)">Essencial</th>
            <th style="padding:7px 10px;text-align:right;color:var(--acc);font-size:10px;text-transform:uppercase;border-bottom:1px solid var(--line)">Regular</th>
            <th style="padding:7px 10px;text-align:right;color:var(--green);font-size:10px;text-transform:uppercase;border-bottom:1px solid var(--line)">Ótimo</th>
            <th style="padding:7px 10px;text-align:right;font-size:10px;color:var(--ink-3);text-transform:uppercase;border-bottom:1px solid var(--line)">R$/h frota</th>
          </tr></thead><tbody>`;
        rows.forEach(({ p, i, h, E, R, O }) => {
          const sel = i === es.perIdx;
          const bg = sel ? 'background:var(--bg2)' : '';
          const cph = O.total / (h * nMaq);
          matTable += `<tr style="${bg}" onclick="_eam.setPer(${i})" style="cursor:pointer">
            <td style="padding:7px 10px;border-bottom:1px solid var(--line);font-weight:${sel?'700':'400'};cursor:pointer" onclick="_eam.setPer(${i})">${p.label} <span style="font-size:10px;color:var(--ink-3)">(${p.dias}d)</span></td>
            <td style="padding:7px 10px;border-bottom:1px solid var(--line);text-align:right;font-family:var(--font-mono)">${fH2(h)}</td>
            <td style="padding:7px 10px;border-bottom:1px solid var(--line);text-align:right;font-family:var(--font-mono);color:var(--amber)">${fR(E.total)}</td>
            <td style="padding:7px 10px;border-bottom:1px solid var(--line);text-align:right;font-family:var(--font-mono);color:var(--acc)">${fR(R.total)}</td>
            <td style="padding:7px 10px;border-bottom:1px solid var(--line);text-align:right;font-family:var(--font-mono);color:var(--green);font-weight:${sel?'700':'400'}">${fR(O.total)}</td>
            <td style="padding:7px 10px;border-bottom:1px solid var(--line);text-align:right;font-family:var(--font-mono);color:var(--ink-3)">R$ ${cph.toFixed(2).replace('.',',')}</td>
          </tr>`;
        });
        matTable += `</tbody></table></div>`;

        const detNiv = es.nivel;
        const det = calcNivel(detNiv, H);
        const detTable = `<div style="font-size:13px;font-weight:600;margin-bottom:8px">Detalhamento · ${NL[detNiv]} · ${per.label}</div>
          <div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;font-size:12px">
          <thead><tr style="background:var(--panel)">
            ${['Item','Cat.','UN','Intervalo','Qtd.','Pr.Unit.','Subtotal','% total'].map(h =>
              `<th style="padding:6px 9px;text-align:${h==='Item'?'left':'right'};font-size:9px;color:var(--ink-3);text-transform:uppercase;border-bottom:1px solid var(--line)">${h}</th>`).join('')}
          </tr></thead><tbody>
          ${det.itens.sort((a,b)=>b.c-a.c).map(it => {
            const pct = det.total > 0 ? Math.round(it.c / det.total * 100) : 0;
            const cc = CAT_C[it.cat] || 'var(--ink-3)';
            return `<tr>
              <td style="padding:6px 9px;border-bottom:1px solid var(--line)">${it.d}</td>
              <td style="padding:6px 9px;border-bottom:1px solid var(--line);text-align:right"><span style="font-size:9px;padding:1px 5px;border-radius:4px;background:${cc}20;color:${cc}">${it.cat}</span></td>
              <td style="padding:6px 9px;border-bottom:1px solid var(--line);text-align:right;font-family:var(--font-mono)">${it.un}</td>
              <td style="padding:6px 9px;border-bottom:1px solid var(--line);text-align:right;font-family:var(--font-mono);color:var(--ink-3)">${it.iv >= 9999 ? 'fixo' : it.iv + 'h'}</td>
              <td style="padding:6px 9px;border-bottom:1px solid var(--line);text-align:right;font-family:var(--font-mono);font-weight:700">${it.q}</td>
              <td style="padding:6px 9px;border-bottom:1px solid var(--line);text-align:right;font-family:var(--font-mono);color:var(--ink-2)">${fR(it.p)}</td>
              <td style="padding:6px 9px;border-bottom:1px solid var(--line);text-align:right;font-family:var(--font-mono);font-weight:700">${fR(it.c)}</td>
              <td style="padding:6px 9px;border-bottom:1px solid var(--line);text-align:right"><div style="height:4px;background:var(--bg3);border-radius:2px;min-width:40px"><div style="height:100%;width:${pct}%;background:${NC[detNiv]};border-radius:2px"></div></div><span style="font-size:9px;color:var(--ink-3)">${pct}%</span></td>
            </tr>`;
          }).join('')}
          <tr style="border-top:2px solid var(--line)">
            <td colspan="6" style="padding:7px 9px;font-weight:700">TOTAL</td>
            <td style="padding:7px 9px;text-align:right;font-family:var(--font-mono);font-weight:700;color:${NC[detNiv]}">${fR(det.total)}</td>
            <td></td>
          </tr></tbody></table></div>`;

        return kpis + matTable + detTable;
      }

      function subDepreciacao() {
        const tipo = es.tipo;
        const vEAM = VALS[tipo];
        if (!vEAM) return `<div style="padding:20px;color:var(--ink-3)">Sem dados de aquisição para ${tipo}.</div>`;
        const { vAcq, vRes, vidaH } = vEAM;
        const depH = (vAcq - vRes) / vidaH;
        const H_ANO = H_SEM * 52;
        const anosVida = Math.round(vidaH / H_ANO * 10) / 10;
        const kpis = `<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:14px">
          ${[
            ['Valor aquisição', fR(vAcq * nMaq), `${nMaq} × ${fR(vAcq)}`, 'var(--amber)'],
            ['Dep./hora/máq',   `R$ ${depH.toFixed(2).replace('.',',')}`, 'por hora operada', 'var(--acc)'],
            ['Vida útil',       `${vidaH} h`,  `≈ ${anosVida} anos`, 'var(--ink-2)'],
            ['Valor residual',  fR(vRes * nMaq), `${nMaq} × ${fR(vRes)}`, 'var(--green)'],
          ].map(([l,v,s,c]) => `<div style="background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:12px;border-left:3px solid ${c}">
            <div style="font-size:10px;color:var(--ink-3);text-transform:uppercase;margin-bottom:4px">${l}</div>
            <div style="font-family:var(--font-mono);font-size:18px;font-weight:700;color:${c}">${v}</div>
            <div style="font-size:11px;color:var(--ink-3)">${s}</div>
          </div>`).join('')}
        </div>`;

        const rows = PERS.map((p, i) => {
          const h = hMaq(p.dias);
          const dep = depH * h;
          const vResAtual = Math.max(0, vAcq - dep);
          const pct = Math.min(100, Math.round(h / vidaH * 100));
          const depFrota = dep * nMaq;
          const manut = hasEAM ? calcNivel('O', h).total : 0;
          return { p, h, dep, vResAtual, pct, depFrota, manut, total: depFrota + manut };
        });

        const table = `<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;font-size:12px">
          <thead><tr style="background:var(--panel)">
            ${['Período','h/máq','% Vida','Dep./máq','Val.Residual','Dep. frota','Manutenção (Ótimo)','Total c/Dep'].map(h =>
              `<th style="padding:7px 9px;text-align:${h==='Período'?'left':'right'};font-size:9px;color:var(--ink-3);text-transform:uppercase;border-bottom:1px solid var(--line)">${h}</th>`).join('')}
          </tr></thead><tbody>
          ${rows.map(({ p, h, dep, vResAtual, pct, depFrota, manut, total }) => {
            const c = pct > 50 ? 'var(--red)' : pct > 25 ? 'var(--amber)' : 'var(--green)';
            return `<tr>
              <td style="padding:7px 9px;border-bottom:1px solid var(--line);font-weight:600;color:var(--acc)">${p.label}</td>
              <td style="padding:7px 9px;border-bottom:1px solid var(--line);text-align:right;font-family:var(--font-mono)">${fH2(h)}</td>
              <td style="padding:7px 9px;border-bottom:1px solid var(--line);text-align:right"><div style="height:4px;background:var(--bg3);border-radius:2px;min-width:40px"><div style="height:100%;width:${pct}%;background:${c};border-radius:2px"></div></div><span style="font-size:9px;color:${c}">${pct}%</span></td>
              <td style="padding:7px 9px;border-bottom:1px solid var(--line);text-align:right;font-family:var(--font-mono);color:var(--amber)">${fR(dep)}</td>
              <td style="padding:7px 9px;border-bottom:1px solid var(--line);text-align:right;font-family:var(--font-mono)">${fR(vResAtual)}</td>
              <td style="padding:7px 9px;border-bottom:1px solid var(--line);text-align:right;font-family:var(--font-mono);color:var(--red)">${fR(depFrota)}</td>
              <td style="padding:7px 9px;border-bottom:1px solid var(--line);text-align:right;font-family:var(--font-mono);color:var(--green)">${manut > 0 ? fR(manut) : '—'}</td>
              <td style="padding:7px 9px;border-bottom:1px solid var(--line);text-align:right;font-family:var(--font-mono);font-weight:700;color:var(--purple)">${fR(total)}</td>
            </tr>`;
          }).join('')}
          </tbody></table></div>`;
        return kpis + table;
      }

      function subEstoque() {
        if (!hasEAM) return `<div style="padding:20px;color:var(--ink-3)">Dados EAM disponíveis apenas para TS114.</div>`;
        const det = calcNivel(es.nivel, H);
        const NL = { E: 'Essencial', R: 'Regular', O: 'Ótimo' };
        const NC = { E: 'var(--amber)', R: 'var(--acc)', O: 'var(--green)' };

        const kpis = `<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:14px">
          ${[
            ['Total necessário', fR(det.total), `${det.itens.length} itens`, NC[es.nivel]],
            ['Item mais caro',   det.itens.sort((a,b)=>b.c-a.c)[0]?.d || '—', fR(det.itens[0]?.c || 0), 'var(--amber)'],
            ['Custo/h frota',   `R$ ${(det.total / (H * nMaq)).toFixed(2).replace('.',',')}`, `${fH2(H)} × ${nMaq} máq`, 'var(--acc)'],
          ].map(([l,v,s,c]) => `<div style="background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:12px;border-left:3px solid ${c}">
            <div style="font-size:10px;color:var(--ink-3);text-transform:uppercase;margin-bottom:4px">${l}</div>
            <div style="font-family:var(--font-mono);font-size:16px;font-weight:700;color:${c};overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${v}</div>
            <div style="font-size:11px;color:var(--ink-3)">${s}</div>
          </div>`).join('')}
        </div>`;

        const table = `<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;font-size:12px">
          <thead><tr style="background:var(--panel)">
            ${['Item','UN','Qtd.Nec.','Est.Seg.20%','Pto.Repos.','Pr.Unit.','Total','Urgência'].map(h =>
              `<th style="padding:6px 9px;text-align:${h==='Item'?'left':'right'};font-size:9px;color:var(--ink-3);text-transform:uppercase;border-bottom:1px solid var(--line)">${h}</th>`).join('')}
          </tr></thead><tbody>
          ${det.itens.sort((a,b)=>b.c-a.c).map(it => {
            const seg = Math.ceil(it.q * 0.2);
            const pr = it.q + seg;
            const pct = det.total > 0 ? Math.round(it.c / det.total * 100) : 0;
            const urg = pct >= 15 ? `<span style="font-size:9px;padding:1px 5px;border-radius:4px;background:var(--red)20;color:var(--red)">ALTO ${pct}%</span>`
                       : pct >= 5  ? `<span style="font-size:9px;padding:1px 5px;border-radius:4px;background:var(--amber)20;color:var(--amber)">MED ${pct}%</span>`
                       :             `<span style="font-size:9px;padding:1px 5px;border-radius:4px;background:var(--acc)20;color:var(--acc)">BAIXO ${pct}%</span>`;
            return `<tr>
              <td style="padding:6px 9px;border-bottom:1px solid var(--line)">${it.d}</td>
              <td style="padding:6px 9px;border-bottom:1px solid var(--line);text-align:right;font-family:var(--font-mono)">${it.un}</td>
              <td style="padding:6px 9px;border-bottom:1px solid var(--line);text-align:right;font-family:var(--font-mono);font-weight:700;color:${NC[es.nivel]}">${it.q}</td>
              <td style="padding:6px 9px;border-bottom:1px solid var(--line);text-align:right;font-family:var(--font-mono);color:var(--amber)">${seg}</td>
              <td style="padding:6px 9px;border-bottom:1px solid var(--line);text-align:right;font-family:var(--font-mono);color:var(--acc)">${pr}</td>
              <td style="padding:6px 9px;border-bottom:1px solid var(--line);text-align:right;font-family:var(--font-mono);color:var(--ink-2)">${fR(it.p)}</td>
              <td style="padding:6px 9px;border-bottom:1px solid var(--line);text-align:right;font-family:var(--font-mono);font-weight:700">${fR(it.c)}</td>
              <td style="padding:6px 9px;border-bottom:1px solid var(--line);text-align:right">${urg}</td>
            </tr>`;
          }).join('')}
          </tbody></table></div>`;
        return kpis + table;
      }

      function subCronograma() {
        const tipo = es.tipo;
        const tipoObj = (mocks.TIPOS || {})[tipo];
        if (!tipoObj) return `<div style="padding:20px;color:var(--ink-3)">Tipo não encontrado.</div>`;
        const hoje2 = new Date();
        const H_TOT = hMaq(PERS[3].dias); // até Dez
        const eventos = [];
        (tipoObj.plano || []).forEach(m => {
          let h = m.iv;
          while (h <= H_TOT) {
            const diasOffset = Math.round((h / H_SEM) * 7);
            const dt = new Date(hoje2.getTime() + diasOffset * 86400000);
            eventos.push({ m, h, dt, sem: Math.ceil(h / H_SEM) });
            h += m.iv;
          }
        });
        eventos.sort((a, b) => a.h - b.h);
        const bySem = {};
        eventos.forEach(e => { if (!bySem[e.sem]) bySem[e.sem] = []; bySem[e.sem].push(e); });

        const ST_C = { 'danger':'var(--red)', 'warn':'var(--amber)', 'proximo':'var(--acc)', 'ok':'var(--green)' };
        const allAtivos = ativos.filter(a => a.tipo === tipo);

        // Frota status summary
        let frotaHtml = '';
        if (allAtivos.length > 0) {
          frotaHtml = `<div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:14px">` +
            allAtivos.map(a => {
              const pr = calcProxManut(a);
              const danger = pr.filter(p => p.st === 'danger').length;
              const warn   = pr.filter(p => p.st === 'warn').length;
              const hist   = getHistUnit(a.id);
              return `<div style="background:var(--panel);border:1px solid var(--line);border-radius:7px;padding:8px 12px;font-size:12px;min-width:140px">
                <div style="font-weight:600">${a.nome || a.cod}</div>
                <div style="font-family:var(--font-mono);font-size:11px;color:var(--acc)">${fH2(hist.hor)}</div>
                ${danger > 0 ? `<span style="font-size:9px;background:var(--red)20;color:var(--red);padding:1px 5px;border-radius:3px">${danger} vencida</span>` : ''}
                ${warn   > 0 ? `<span style="font-size:9px;background:var(--amber)20;color:var(--amber);padding:1px 5px;border-radius:3px;margin-left:3px">${warn} urgente</span>` : ''}
              </div>`;
            }).join('') + `</div>`;
        }

        const cronTable = `<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;font-size:12px">
          <thead><tr style="background:var(--panel)">
            ${['Horímetro','Data aprox.','Semana','Manutenção','Intervalo'].map(h =>
              `<th style="padding:6px 9px;text-align:left;font-size:9px;color:var(--ink-3);text-transform:uppercase;border-bottom:1px solid var(--line)">${h}</th>`).join('')}
          </tr></thead><tbody>
          ${eventos.slice(0, 60).map(e => {
            const dtStr = e.dt.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' });
            const hEAM = hasEAM ? ITENS.find(it => e.m.its?.some(s => it.d.includes(s.split(' ')[0]))) : null;
            return `<tr>
              <td style="padding:6px 9px;border-bottom:1px solid var(--line);font-family:var(--font-mono);color:var(--amber)">${e.h} h</td>
              <td style="padding:6px 9px;border-bottom:1px solid var(--line);font-family:var(--font-mono)">${dtStr}/${yr}</td>
              <td style="padding:6px 9px;border-bottom:1px solid var(--line);color:var(--ink-3)">S${e.sem}</td>
              <td style="padding:6px 9px;border-bottom:1px solid var(--line);font-weight:500">${e.m.n}</td>
              <td style="padding:6px 9px;border-bottom:1px solid var(--line);font-family:var(--font-mono);color:var(--ink-3)">${e.m.iv} h</td>
            </tr>`;
          }).join('')}
          ${eventos.length > 60 ? `<tr><td colspan="5" style="padding:6px 9px;color:var(--ink-3);font-size:11px">... e mais ${eventos.length - 60} eventos</td></tr>` : ''}
          </tbody></table></div>`;

        const semBars = Object.entries(bySem).sort((a,b)=>Number(a[0])-Number(b[0])).slice(0,16);
        const maxSem = Math.max(1, ...semBars.map(([,v])=>v.length));
        const barChart = `<div style="margin-bottom:14px">
          <div style="font-size:12px;font-weight:600;margin-bottom:8px">Eventos por semana (1 máquina)</div>
          ${semBars.map(([s, evs]) => {
            const pct = Math.round(evs.length / maxSem * 100);
            return `<div style="display:flex;align-items:center;gap:8px;margin-bottom:5px">
              <div style="font-size:10px;color:var(--ink-2);width:60px;flex-shrink:0">Sem.${s}</div>
              <div style="flex:1;height:12px;background:var(--panel);border-radius:3px;overflow:hidden">
                <div style="width:${pct}%;height:100%;background:var(--acc)66;border-radius:3px;display:flex;align-items:center;padding-left:4px">
                  <span style="font-size:9px;color:var(--acc);font-weight:700">${evs.length}</span>
                </div>
              </div>
              <div style="font-size:9px;color:var(--ink-3);width:100px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${evs.map(e=>e.m.n.split(' ')[0]).join(', ')}</div>
            </div>`;
          }).join('')}
        </div>`;

        return frotaHtml + barChart + cronTable;
      }

      function subMetricas() {
        const MTBF = 150, MTTR = 2.5;
        const disp = (MTBF / (MTBF + MTTR) * 100).toFixed(1);
        const kpis = `<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:14px">
          ${[
            ['MTBF estimado','~150 h','Entre falhas não programadas','var(--green)'],
            ['MTTR estimado','~2,5 h','Tempo médio de reparo','var(--amber)'],
            ['Disponibilidade',disp+'%','MTBF/(MTBF+MTTR)×100','var(--acc)'],
            ['OEE estimado','≥ 85%','Com manutenção preventiva ótima','var(--ink-2)'],
          ].map(([l,v,s,c]) => `<div style="background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:12px;border-left:3px solid ${c}">
            <div style="font-size:10px;color:var(--ink-3);text-transform:uppercase;margin-bottom:4px">${l}</div>
            <div style="font-family:var(--font-mono);font-size:20px;font-weight:700;color:${c}">${v}</div>
            <div style="font-size:11px;color:var(--ink-3)">${s}</div>
          </div>`).join('')}
        </div>`;

        // Cost per hour by period and level
        if (!hasEAM) return kpis + `<div style="color:var(--ink-3);font-size:13px">Adicione ITENS_EAM para análise de custo por hora.</div>`;
        const catTotals = {};
        const detO = calcNivel('O', H);
        detO.itens.forEach(it => { catTotals[it.cat] = (catTotals[it.cat] || 0) + it.c; });
        const grandTotal = Object.values(catTotals).reduce((a,b)=>a+b, 0);
        const cats = Object.entries(catTotals).sort((a,b)=>b[1]-a[1]);
        const maxCat = cats.length ? cats[0][1] : 1;

        const distBar = `<div style="background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:12px;margin-bottom:14px">
          <div style="font-weight:600;margin-bottom:10px;font-size:13px">Distribuição de custo por categoria · ${per.label} · Ótimo</div>
          ${cats.map(([cat, v]) => {
            const pct = Math.round(v / maxCat * 100);
            const ptot = grandTotal > 0 ? Math.round(v / grandTotal * 100) : 0;
            const cc = CAT_C[cat] || 'var(--ink-3)';
            return `<div style="display:flex;align-items:center;gap:8px;margin-bottom:7px">
              <div style="font-size:11px;color:var(--ink-2);width:80px;text-transform:capitalize;flex-shrink:0">${cat}</div>
              <div style="flex:1;height:14px;background:var(--bg3);border-radius:3px;overflow:hidden">
                <div style="width:${pct}%;height:100%;background:${cc}88;border-radius:3px;display:flex;align-items:center;justify-content:flex-end;padding-right:4px">
                  <span style="font-size:9px;color:#fff;font-weight:700">${ptot}%</span>
                </div>
              </div>
              <div style="font-size:10px;font-family:var(--font-mono);color:var(--ink-3);width:90px;text-align:right;flex-shrink:0">${fR(v)}</div>
            </div>`;
          }).join('')}
        </div>`;

        const cphTable = `<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;font-size:12px">
          <thead><tr style="background:var(--panel)">
            ${['Período','Dias','h/máq','Essencial','Regular','Ótimo','R$/h (frota,Ótimo)'].map(h =>
              `<th style="padding:7px 9px;text-align:${h==='Período'?'left':'right'};font-size:9px;color:var(--ink-3);text-transform:uppercase;border-bottom:1px solid var(--line)">${h}</th>`).join('')}
          </tr></thead><tbody>
          ${PERS.map(p => {
            const h = hMaq(p.dias);
            const E = calcNivel('E',h), R = calcNivel('R',h), O = calcNivel('O',h);
            const cph = (O.total / (h * nMaq)).toFixed(2).replace('.',',');
            return `<tr>
              <td style="padding:7px 9px;border-bottom:1px solid var(--line);font-weight:600;color:var(--acc)">${p.label}</td>
              <td style="padding:7px 9px;border-bottom:1px solid var(--line);text-align:right;color:var(--ink-3)">${p.dias}d</td>
              <td style="padding:7px 9px;border-bottom:1px solid var(--line);text-align:right;font-family:var(--font-mono)">${fH2(h)}</td>
              <td style="padding:7px 9px;border-bottom:1px solid var(--line);text-align:right;font-family:var(--font-mono);color:var(--amber)">${fR(E.total)}</td>
              <td style="padding:7px 9px;border-bottom:1px solid var(--line);text-align:right;font-family:var(--font-mono);color:var(--acc)">${fR(R.total)}</td>
              <td style="padding:7px 9px;border-bottom:1px solid var(--line);text-align:right;font-family:var(--font-mono);color:var(--green)">${fR(O.total)}</td>
              <td style="padding:7px 9px;border-bottom:1px solid var(--line);text-align:right;font-family:var(--font-mono);color:var(--ink-2)">R$ ${cph}/h</td>
            </tr>`;
          }).join('')}
          </tbody></table></div>`;

        return kpis + distBar + cphTable;
      }

      const SUBS_EAM = {
        matriz: subMatriz, depreciacao: subDepreciacao, estoque: subEstoque, cronograma: subCronograma, metricas: subMetricas,
      };
      const SUB_TABS = [
        { id: 'matriz',      label: '🗂 Matriz' },
        { id: 'depreciacao', label: '📉 Depreciação' },
        { id: 'estoque',     label: '📦 Estoque' },
        { id: 'cronograma',  label: '📅 Cronograma' },
        { id: 'metricas',    label: '📊 Métricas' },
      ];

      // Bridge for onclick in innerHTML
      window._eam = {
        setPer:    i  => { es.perIdx = i;  RENDERERS.eam(cont); },
        setNivel:  n  => { es.nivel = n;   RENDERERS.eam(cont); },
        setTipo:   t  => { es.tipo = t;    RENDERERS.eam(cont); },
        setSub:    s  => { es.sub = s;     RENDERERS.eam(cont); },
      };

      const NL = { E: 'Essencial', R: 'Regular', O: 'Ótimo' };
      const NC = { E: 'var(--amber)', R: 'var(--acc)', O: 'var(--green)' };

      const ctrl = `
        <div style="display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:12px">
          <select onchange="_eam.setTipo(this.value)" style="padding:5px 9px;border:1px solid var(--line);border-radius:6px;background:var(--panel);color:var(--ink);font-size:12px">
            ${TIPOS_LIST.map(t => `<option value="${t}" ${t===es.tipo?'selected':''}>${t}${VALS[t]?' ★':''}</option>`).join('')}
          </select>
          <span style="font-size:11px;color:var(--ink-3)">${nMaq} máquina(s) no filtro</span>
          <div style="display:flex;gap:3px;flex-shrink:0">
            ${PERS.map((p,i) => `<button onclick="_eam.setPer(${i})" style="padding:4px 10px;border-radius:6px;border:1px solid var(--line);background:${i===es.perIdx?'var(--acc)':'var(--panel)'};color:${i===es.perIdx?'#fff':'var(--ink-2)'};cursor:pointer;font-size:11px">${p.label}</button>`).join('')}
          </div>
          <div style="display:flex;gap:3px;flex-shrink:0">
            ${['E','R','O'].map(n => `<button onclick="_eam.setNivel('${n}')" style="padding:4px 10px;border-radius:6px;border:1px solid var(--line);background:${n===es.nivel?NC[n]:'var(--panel)'};color:${n===es.nivel?'#fff':'var(--ink-2)'};cursor:pointer;font-size:11px">${NL[n]}</button>`).join('')}
          </div>
        </div>
        <div style="display:flex;gap:3px;margin-bottom:14px">
          ${SUB_TABS.map(t => `<button onclick="_eam.setSub('${t.id}')" style="padding:5px 12px;border-radius:6px;border:none;background:${t.id===es.sub?'var(--panel)':'transparent'};color:${t.id===es.sub?'var(--ink)':'var(--ink-2)'};box-shadow:${t.id===es.sub?'inset 0 -2px 0 var(--acc)':'none'};cursor:pointer;font-size:12px">${t.label}</button>`).join('')}
        </div>`;

      const subContent = SUBS_EAM[es.sub]?.() || '';
      const { el } = window.engine.utils;
      const wrap = el('div');
      wrap.innerHTML = ctrl + subContent;
      cont.replaceChildren(wrap);
    },

    config(cont) {
      const { el } = window.engine.utils;
      const quals = window.ERP_MANUT_MOCKS?.qualificacoes_catalogo || [];
      cont.replaceChildren(
        el('div', { style: { fontWeight: '600', fontSize: '15px', marginBottom: '12px' } }, 'Qualificações requeridas'),
        el('div', { style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(240px,1fr))', gap: '10px' } },
          ...quals.map(q => el('div', { style: {
            padding: '10px 14px', background: 'var(--panel)',
            border: '1px solid var(--line)', borderRadius: '8px', fontSize: '13px',
          } },
            el('div', { style: { fontWeight: '600', marginBottom: '4px' } }, q.nome),
            el('div', { style: { color: 'var(--ink-3)', fontSize: '11px' } }, `Código: ${q.codigo}`),
            el('div', { style: { fontSize: '11px', marginTop: '4px', display: 'flex', gap: '4px', flexWrap: 'wrap' } },
              window.engine.badge(`${q.usuarios} usuário(s)`, 'blue'),
              ...(q.requer_validade ? [window.engine.badge('validade', 'amber')] : []),
            ),
          ))),
      );
    },

    async 'registrar-uso'(cont) {
      state._scopeCats = null;
      const { el } = window.engine.utils;

      // ── helpers locais (prefixo ru_ para evitar colisão com globals legados) ──

      function ruToken() {
        return localStorage.getItem('xcmasm_token') || '';
      }

      function ruAuthHeaders() {
        return { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + ruToken() };
      }

      // Popula o selector de ativos com os dados já carregados pelo módulo
      function ruBuildAtivoOpts(select) {
        const ativos = (state.cache.ativos?.data || []).filter(a => a.ativo);
        select.innerHTML = '<option value="">— selecione um ativo —</option>';
        ativos.forEach(a => {
          const opt = document.createElement('option');
          opt.value = a.id;
          opt.textContent = `${a.nome} (${a.categoria || '—'})`;
          opt.dataset.uso = a.uso_atual || '0';
          opt.dataset.unidade = a.unidade_uso || 'h';
          select.appendChild(opt);
        });
      }

      // Atualiza badge de horímetro quando ativo muda
      function ruOnAtivoChange(select, badge) {
        const opt = select.options[select.selectedIndex];
        if (opt && opt.value) {
          const uso = parseFloat(opt.dataset.uso || 0);
          const unidade = opt.dataset.unidade || 'h';
          badge.textContent = `Horímetro atual: ${uso.toFixed(1)} ${unidade}`;
          badge.style.display = 'inline-block';
        } else {
          badge.style.display = 'none';
        }
      }

      // Carrega e exibe registros recentes para o ativo selecionado
      async function ruCarregarRecentes(ativoId, recDiv) {
        if (!ativoId) { recDiv.innerHTML = ''; return; }
        recDiv.innerHTML = '<span style="color:var(--ink-3);font-size:12px">Carregando...</span>';
        try {
          const r = await fetch(apiUrl('/api/manutencao/uso?ativo_id=' + encodeURIComponent(ativoId) + '&limit=10'), {
            headers: { 'Authorization': 'Bearer ' + ruToken() },
          });
          if (!r.ok) { recDiv.innerHTML = '<span style="color:var(--red);font-size:12px">Falha ao carregar recentes</span>'; return; }
          const rows = await r.json();
          if (!rows.length) { recDiv.innerHTML = '<span style="color:var(--ink-3);font-size:12px">Nenhum registro para este ativo.</span>'; return; }
          const tbl = el('table', { style: { width: '100%', borderCollapse: 'collapse', fontSize: '12px' } },
            el('thead', {},
              el('tr', { style: { color: 'var(--ink-3)', textAlign: 'left' } },
                el('th', { style: { padding: '4px 8px', borderBottom: '1px solid var(--line)' } }, 'Data'),
                el('th', { style: { padding: '4px 8px', borderBottom: '1px solid var(--line)' } }, 'Delta'),
                el('th', { style: { padding: '4px 8px', borderBottom: '1px solid var(--line)' } }, 'Anterior'),
                el('th', { style: { padding: '4px 8px', borderBottom: '1px solid var(--line)' } }, 'Novo'),
                el('th', { style: { padding: '4px 8px', borderBottom: '1px solid var(--line)' } }, 'Operador'),
              ),
            ),
            el('tbody', {},
              ...rows.map(row => el('tr', { style: { borderBottom: '1px solid var(--line)' } },
                el('td', { style: { padding: '4px 8px', fontFamily: 'var(--font-mono)' } }, row.data || '—'),
                el('td', { style: { padding: '4px 8px', fontFamily: 'var(--font-mono)', color: 'var(--acc)' } }, `+${Number(row.delta || 0).toFixed(1)} ${row.unidade_uso || 'h'}`),
                el('td', { style: { padding: '4px 8px', fontFamily: 'var(--font-mono)', color: 'var(--ink-2)' } }, Number(row.valor_anterior || 0).toFixed(1)),
                el('td', { style: { padding: '4px 8px', fontFamily: 'var(--font-mono)' } }, Number(row.valor_novo || 0).toFixed(1)),
                el('td', { style: { padding: '4px 8px', color: 'var(--ink-2)' } }, row.operador || '—'),
              )),
            ),
          );
          recDiv.replaceChildren(tbl);
        } catch (e) {
          recDiv.innerHTML = '<span style="color:var(--red);font-size:12px">Erro de rede: ' + e.message + '</span>';
        }
      }

      // Layout da seção Registrar Uso portado do legado (CMASM_Gestao_v2.html #m-uso)
      const cardStyle = {
        background: 'var(--panel)', border: '1px solid var(--line)',
        borderRadius: '8px', padding: '20px', marginBottom: '14px',
      };
      const labelStyle = { fontSize: '12px', color: 'var(--ink-2)', marginBottom: '4px', display: 'block' };
      const inputStyle = {
        width: '100%', boxSizing: 'border-box', padding: '7px 10px',
        background: 'var(--bg2)', border: '1px solid var(--line)',
        borderRadius: '6px', color: 'var(--ink)', fontSize: '13px',
      };

      // Ativo selector + badge
      const ativoSel = el('select', { style: { ...inputStyle } });
      ruBuildAtivoOpts(ativoSel);

      const horimBadge = el('span', {
        style: {
          display: 'none', marginLeft: '10px', fontFamily: 'var(--font-mono)',
          fontSize: '12px', color: 'var(--acc)', padding: '2px 8px',
          background: 'var(--bg3)', borderRadius: '4px',
        },
      }, '');

      // Inputs
      const today = new Date().toISOString().slice(0, 10);
      const deltaInput = el('input', { type: 'number', min: '0.1', step: '0.1', placeholder: '0.0', style: { ...inputStyle } });
      const dataInput = el('input', { type: 'date', value: today, style: { ...inputStyle } });
      const obsInput = el('input', { type: 'text', placeholder: 'Observação (opcional)', style: { ...inputStyle } });

      // Feedback + alerta
      const feedbackDiv = el('div', { style: { marginTop: '8px', fontSize: '13px', color: 'var(--green)', minHeight: '20px' } });
      const alertaDiv = el('div', {
        style: {
          display: 'none', marginTop: '10px', padding: '10px 14px',
          background: 'var(--bg2)', border: '1px solid var(--amber)',
          borderRadius: '6px', color: 'var(--amber)', fontSize: '13px',
        },
      });

      // Registros recentes
      const recentesDiv = el('div', { style: { marginTop: '8px' } });

      // Ativo change handler
      ativoSel.addEventListener('change', () => {
        ruOnAtivoChange(ativoSel, horimBadge);
        // Atualiza placeholder do delta com unidade do ativo
        const opt = ativoSel.options[ativoSel.selectedIndex];
        if (opt && opt.value) {
          const un = opt.dataset.unidade || 'h';
          deltaInput.placeholder = `Incremento em ${un}`;
        } else {
          deltaInput.placeholder = '0.0';
        }
        feedbackDiv.textContent = '';
        alertaDiv.style.display = 'none';
        ruCarregarRecentes(ativoSel.value, recentesDiv);
      });

      // Botão Registrar
      const btnRegistrar = el('button', { class: 'pe-btn pe-btn--primary', style: { marginTop: '12px' } }, '⏱ Registrar');
      btnRegistrar.addEventListener('click', async () => {
        const ativoId = ativoSel.value;
        const delta = parseFloat(deltaInput.value);
        const dataVal = dataInput.value || today;
        const obs = obsInput.value.trim() || null;

        // Validação client-side (advisory — server valida definitivamente)
        if (!ativoId) { toast('Selecione um ativo.', 'amber'); return; }
        if (!delta || delta <= 0) { toast('Informe o incremento de uso (> 0).', 'amber'); return; }

        btnRegistrar.disabled = true;
        feedbackDiv.textContent = 'Registrando...';
        alertaDiv.style.display = 'none';

        try {
          const res = await fetch(apiUrl('/api/manutencao/uso'), {
            method: 'POST',
            headers: ruAuthHeaders(),
            body: JSON.stringify({ ativo_id: ativoId, delta, data: dataVal, observacao: obs }),
          });

          if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            toast(err.detail || 'Erro ao registrar uso (HTTP ' + res.status + ')', 'red');
            feedbackDiv.textContent = '';
            return;
          }

          const resp = await res.json();
          const opt = ativoSel.options[ativoSel.selectedIndex];
          const unidade = (opt && opt.dataset.unidade) || 'h';

          // Atualiza badge de horímetro
          horimBadge.textContent = `Horímetro atual: ${Number(resp.uso_atual || 0).toFixed(1)} ${unidade}`;
          if (opt) opt.dataset.uso = resp.uso_atual || 0;

          feedbackDiv.textContent = `Registrado: +${delta.toFixed(1)} ${unidade} → total ${Number(resp.uso_atual || 0).toFixed(1)} ${unidade}`;

          // Alerta de vencimento inline
          const venc = resp.vencimentos_disparados || [];
          if (venc.length) {
            alertaDiv.style.display = 'block';
            alertaDiv.replaceChildren(
              el('strong', {}, 'Atenção — serviços preventivos próximos do vencimento:'),
              ...venc.map(v =>
                el('div', {}, `• ${v.servico} (falta ${Number(v.falta || 0).toFixed(1)} ${v.unidade || unidade})`)
              ),
            );
          } else {
            alertaDiv.style.display = 'none';
          }

          // Limpa inputs e atualiza recentes
          deltaInput.value = '';
          obsInput.value = '';
          await ruCarregarRecentes(ativoId, recentesDiv);
        } catch (e) {
          toast('Erro de rede: ' + e.message, 'red');
          feedbackDiv.textContent = '';
        } finally {
          btnRegistrar.disabled = false;
        }
      });

      // Monta layout
      cont.replaceChildren(
        el('div', { style: { maxWidth: '640px' } },
          el('h3', { style: { marginTop: '0', marginBottom: '16px', fontWeight: '600' } }, '⏱ Registrar Uso'),

          // Formulário
          el('div', { style: cardStyle },
            el('div', { style: { marginBottom: '14px' } },
              el('label', { style: labelStyle }, 'Ativo *'),
              el('div', { style: { display: 'flex', alignItems: 'center', gap: '8px' } },
                ativoSel, horimBadge,
              ),
            ),
            el('div', { style: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '14px' } },
              el('div', {},
                el('label', { style: labelStyle }, 'Data *'),
                dataInput,
              ),
              el('div', {},
                el('label', { style: labelStyle }, 'Horas / km *'),
                deltaInput,
              ),
            ),
            el('div', { style: { marginBottom: '14px' } },
              el('label', { style: labelStyle }, 'Observações'),
              obsInput,
            ),
            btnRegistrar,
            feedbackDiv,
            alertaDiv,
          ),

          // Registros recentes
          el('div', { style: cardStyle },
            el('div', { style: { fontWeight: '600', marginBottom: '10px' } }, 'Registros Recentes'),
            recentesDiv,
          ),
        ),
      );
    },

    // ── Sobressalentes ─────────────────────────────────────────────────────
    async sobressalentes(cont) {
      state._scopeCats = null;
      const { el } = window.engine.utils;

      // ── helpers locais (prefixo sb_ para evitar colisão com globals) ──

      function sbToken() {
        return localStorage.getItem('xcmasm_token') || '';
      }

      function sbAuthHeaders() {
        return { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + sbToken() };
      }

      const cardStyle = {
        background: 'var(--panel)', border: '1px solid var(--line)',
        borderRadius: '8px', padding: '20px', marginBottom: '14px',
      };
      const labelStyle = { fontSize: '12px', color: 'var(--ink-2)', marginBottom: '4px', display: 'block' };
      const inputStyle = {
        width: '100%', boxSizing: 'border-box', padding: '7px 10px',
        background: 'var(--bg2)', border: '1px solid var(--line)',
        borderRadius: '6px', color: 'var(--ink)', fontSize: '13px',
      };

      // badge ZERADO/BAIXO/OK → CSS color token
      function sbBadgeColor(badge) {
        if (badge === 'ZERADO') return 'var(--red)';
        if (badge === 'BAIXO')  return 'var(--amber)';
        return 'var(--green)'; // OK
      }

      // Formata número como moeda BRL
      function sbFmtBRL(v) {
        return Number(v || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
      }

      // ── overlay modal helper ──────────────────────────────────────────

      function sbOpenModal(title, bodyBuilder, onSave) {
        // remove overlay anterior se existir
        const existingOverlay = document.getElementById('sb-modal-overlay');
        if (existingOverlay) existingOverlay.remove();

        const overlay = el('div', {
          id: 'sb-modal-overlay',
          style: {
            position: 'fixed', inset: '0', zIndex: '9000',
            background: 'rgba(0,0,0,0.65)', display: 'flex',
            alignItems: 'center', justifyContent: 'center',
          },
        });

        const modal = el('div', {
          style: {
            background: 'var(--bg)', border: '1px solid var(--line)',
            borderRadius: '10px', padding: '24px', minWidth: '360px',
            maxWidth: '520px', width: '90%', boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
          },
        });

        const closeBtn = el('button', {
          class: 'pe-btn pe-btn--ghost',
          style: { float: 'right', marginTop: '-4px' },
        }, '✕');
        closeBtn.addEventListener('click', () => overlay.remove());

        const titleEl = el('h3', { style: { margin: '0 0 18px 0', fontWeight: '600', fontSize: '15px' } }, title);

        const bodyEl = el('div');
        const fields = bodyBuilder(bodyEl, inputStyle, labelStyle);

        const saveBtn = el('button', {
          class: 'pe-btn pe-btn--primary',
          style: { marginTop: '16px', width: '100%' },
        }, 'Salvar');
        const cancelBtn = el('button', {
          class: 'pe-btn pe-btn--ghost',
          style: { marginTop: '8px', width: '100%' },
        }, 'Cancelar');

        saveBtn.addEventListener('click', async () => {
          saveBtn.disabled = true;
          saveBtn.textContent = 'Salvando...';
          try {
            await onSave(fields, overlay);
          } finally {
            saveBtn.disabled = false;
            saveBtn.textContent = 'Salvar';
          }
        });
        cancelBtn.addEventListener('click', () => overlay.remove());

        overlay.addEventListener('click', e => { if (e.target === overlay) overlay.remove(); });

        modal.append(closeBtn, titleEl, bodyEl, saveBtn, cancelBtn);
        overlay.appendChild(modal);
        document.body.appendChild(overlay);
      }

      // ── carregar e renderizar lista ───────────────────────────────────

      async function sbRender() {
        cont.innerHTML = '<div style="padding:24px;color:var(--ink-3);font-size:13px">Carregando...</div>';

        let data;
        try {
          const r = await fetch(apiUrl('/api/manutencao/sobressalentes'), {
            headers: { 'Authorization': 'Bearer ' + sbToken() },
          });
          if (!r.ok) {
            const err = await r.json().catch(() => ({}));
            toast(err.detail || 'Erro ao carregar sobressalentes (HTTP ' + r.status + ')', 'red');
            cont.innerHTML = '';
            return;
          }
          data = await r.json();
        } catch (e) {
          toast('Erro de rede: ' + e.message, 'red');
          cont.innerHTML = '';
          return;
        }

        const pecas = data.items || [];
        const valorTotal = data.valor_estimado_total || 0;

        // ── Botão + Nova Peça ─────────────────────────────────────────

        function sbOpenPecaForm(peca) {
          const isEdit = !!peca;
          sbOpenModal(
            isEdit ? 'Editar Peça' : '+ Nova Peça',
            (bodyEl, iStyle, lStyle) => {
              const fields = {};

              const rows = [
                { key: 'nome',          label: 'Nome *',        type: 'text',   placeholder: 'Nome da peça' },
                { key: 'codigo',        label: 'Código',        type: 'text',   placeholder: 'Código (opcional)' },
                { key: 'unidade',       label: 'Unidade',       type: 'text',   placeholder: 'un' },
                { key: 'qtd_minima',    label: 'Qtd mínima',    type: 'number', placeholder: '0' },
                { key: 'preco_unitario', label: 'Preço unitário (R$)', type: 'number', placeholder: '0.00' },
                { key: 'obs',           label: 'Observações',   type: 'text',   placeholder: '' },
              ];

              rows.forEach(row => {
                const wrap = el('div', { style: { marginBottom: '12px' } });
                const lbl = el('label', { style: lStyle }, row.label);
                let input;
                if (row.key === 'obs') {
                  input = el('textarea', {
                    placeholder: row.placeholder,
                    rows: '2',
                    style: { ...iStyle, resize: 'vertical' },
                  });
                } else {
                  input = el('input', {
                    type: row.type,
                    placeholder: row.placeholder,
                    style: { ...iStyle },
                  });
                }
                if (isEdit && peca[row.key] != null) {
                  input.value = peca[row.key];
                }
                fields[row.key] = input;
                wrap.append(lbl, input);
                bodyEl.appendChild(wrap);
              });

              // Categoria select
              const catWrap = el('div', { style: { marginBottom: '12px' } });
              const catLbl = el('label', { style: lStyle }, 'Categoria');
              const catSel = el('select', { style: iStyle });
              ['consumivel', 'sobressalente', 'ferramenta'].forEach(opt => {
                const o = document.createElement('option');
                o.value = opt;
                o.textContent = opt;
                if (isEdit && peca.categoria === opt) o.selected = true;
                catSel.appendChild(o);
              });
              fields.categoria = catSel;
              catWrap.append(catLbl, catSel);
              bodyEl.appendChild(catWrap);

              return fields;
            },
            async (fields, overlay) => {
              const nome = fields.nome.value.trim();
              if (!nome) { toast('Nome é obrigatório.', 'amber'); return; }

              const payload = {
                nome,
                codigo:        fields.codigo.value.trim() || null,
                categoria:     fields.categoria.value || 'sobressalente',
                unidade:       fields.unidade.value.trim() || 'un',
                qtd_minima:    parseFloat(fields.qtd_minima.value) || 0,
                preco_unitario: parseFloat(fields.preco_unitario.value) || 0,
                obs:           fields.obs.value.trim() || null,
              };

              const url    = isEdit
                ? apiUrl('/api/manutencao/sobressalentes/' + peca.id)
                : apiUrl('/api/manutencao/sobressalentes');
              const method = isEdit ? 'PUT' : 'POST';

              const res = await fetch(url, {
                method,
                headers: sbAuthHeaders(),
                body: JSON.stringify(payload),
              });
              if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                toast(err.detail || 'Erro ao salvar (HTTP ' + res.status + ')', 'red');
                return;
              }
              toast(isEdit ? 'Peça atualizada.' : 'Peça criada.', 'green');
              overlay.remove();
              sbRender();
            },
          );
        }

        // ── Ajustar modal ─────────────────────────────────────────────

        function sbOpenAjuste(peca) {
          sbOpenModal(
            'Ajustar Quantidade — ' + peca.nome,
            (bodyEl, iStyle, lStyle) => {
              const fields = {};

              // Tipo
              const tipoWrap = el('div', { style: { marginBottom: '12px' } });
              const tipoLbl = el('label', { style: lStyle }, 'Tipo *');
              const tipoSel = el('select', { style: iStyle });
              ['entrada', 'saida', 'ajuste'].forEach(opt => {
                const o = document.createElement('option');
                o.value = opt;
                o.textContent = opt.charAt(0).toUpperCase() + opt.slice(1);
                tipoSel.appendChild(o);
              });
              fields.tipo = tipoSel;
              tipoWrap.append(tipoLbl, tipoSel);
              bodyEl.appendChild(tipoWrap);

              // Quantidade
              const qtdWrap = el('div', { style: { marginBottom: '12px' } });
              const qtdLbl = el('label', { style: lStyle }, 'Quantidade *');
              const qtdInput = el('input', { type: 'number', min: '0.001', step: '0.001', placeholder: '0', style: iStyle });
              fields.quantidade = qtdInput;
              qtdWrap.append(qtdLbl, qtdInput);
              bodyEl.appendChild(qtdWrap);

              // Motivo
              const motWrap = el('div', { style: { marginBottom: '12px' } });
              const motLbl = el('label', { style: lStyle }, 'Motivo *');
              const motInput = el('input', { type: 'text', placeholder: 'Motivo do ajuste', style: iStyle });
              fields.motivo = motInput;
              motWrap.append(motLbl, motInput);
              bodyEl.appendChild(motWrap);

              // Obs
              const obsWrap = el('div', { style: { marginBottom: '12px' } });
              const obsLbl = el('label', { style: lStyle }, 'Observações');
              const obsInput = el('textarea', { placeholder: 'Observações (opcional)', rows: '2', style: { ...iStyle, resize: 'vertical' } });
              fields.obs = obsInput;
              obsWrap.append(obsLbl, obsInput);
              bodyEl.appendChild(obsWrap);

              return fields;
            },
            async (fields, overlay) => {
              const quantidade = parseFloat(fields.quantidade.value);
              const motivo    = fields.motivo.value.trim();
              if (!quantidade || quantidade <= 0) { toast('Informe uma quantidade > 0.', 'amber'); return; }
              if (!motivo) { toast('Motivo é obrigatório.', 'amber'); return; }

              const payload = {
                tipo:      fields.tipo.value,
                quantidade,
                motivo,
                obs: fields.obs.value.trim() || null,
              };

              const res = await fetch(apiUrl('/api/manutencao/sobressalentes/' + peca.id + '/ajuste'), {
                method: 'POST',
                headers: sbAuthHeaders(),
                body: JSON.stringify(payload),
              });
              if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                toast(err.detail || 'Erro ao ajustar (HTTP ' + res.status + ')', 'red');
                return;
              }
              toast('Ajuste registrado.', 'green');
              overlay.remove();
              sbRender();
            },
          );
        }

        // ── Cabeçalho com valor total + botão Nova Peça ───────────────

        const btnNova = el('button', { class: 'pe-btn pe-btn--primary' }, '+ Nova Peça');
        btnNova.addEventListener('click', () => sbOpenPecaForm(null));

        const valorBadge = el('span', {
          style: {
            fontFamily: 'var(--font-mono)', fontSize: '15px', fontWeight: '600',
            color: 'var(--acc)', padding: '4px 12px',
            background: 'var(--bg3)', borderRadius: '6px',
          },
        });
        valorBadge.textContent = 'R$ ' + sbFmtBRL(valorTotal);

        const headerCard = el('div', {
          style: {
            ...cardStyle,
            display: 'flex', alignItems: 'center', gap: '14px', flexWrap: 'wrap',
          },
        },
          el('div', { style: { fontWeight: '600', fontSize: '14px' } }, 'Valor estimado do estoque:'),
          valorBadge,
          el('div', { style: { flex: '1' } }),
          btnNova,
        );

        // ── Tabela de peças ───────────────────────────────────────────

        let tableNode;
        if (!pecas.length) {
          tableNode = el('div', {
            style: { padding: '24px', color: 'var(--ink-3)', textAlign: 'center', fontSize: '13px' },
          }, 'Nenhuma peça cadastrada. Clique em "+ Nova Peça" para começar.');
        } else {
          const thead = el('thead', {},
            el('tr', { style: { color: 'var(--ink-3)', textAlign: 'left', fontSize: '12px' } },
              el('th', { style: { padding: '8px 10px', borderBottom: '1px solid var(--line)' } }, 'Nome'),
              el('th', { style: { padding: '8px 10px', borderBottom: '1px solid var(--line)' } }, 'Categoria'),
              el('th', { style: { padding: '8px 10px', borderBottom: '1px solid var(--line)', textAlign: 'right' } }, 'Qtd atual'),
              el('th', { style: { padding: '8px 10px', borderBottom: '1px solid var(--line)' } }, 'Un'),
              el('th', { style: { padding: '8px 10px', borderBottom: '1px solid var(--line)' } }, 'Status'),
              el('th', { style: { padding: '8px 10px', borderBottom: '1px solid var(--line)', textAlign: 'right' } }, 'Preço un.'),
              el('th', { style: { padding: '8px 10px', borderBottom: '1px solid var(--line)' } }, 'Ações'),
            ),
          );

          const tbody = el('tbody', {},
            ...pecas.map(p => {
              const badgeEl = el('span', {
                style: {
                  display: 'inline-block', padding: '2px 8px', borderRadius: '4px',
                  fontSize: '11px', fontWeight: '600',
                  background: sbBadgeColor(p.badge) + '22',
                  color: sbBadgeColor(p.badge),
                  border: '1px solid ' + sbBadgeColor(p.badge) + '55',
                },
              });
              badgeEl.textContent = p.badge || 'OK';

              const nomeEl = el('td', { style: { padding: '8px 10px', fontWeight: '500' } });
              nomeEl.textContent = p.nome || '—';

              const catEl = el('td', { style: { padding: '8px 10px', color: 'var(--ink-2)', fontSize: '12px' } });
              catEl.textContent = p.categoria || '—';

              const qtdEl = el('td', { style: { padding: '8px 10px', fontFamily: 'var(--font-mono)', textAlign: 'right' } });
              qtdEl.textContent = Number(p.qtd_atual || 0).toFixed(2);

              const unEl = el('td', { style: { padding: '8px 10px', color: 'var(--ink-2)', fontSize: '12px' } });
              unEl.textContent = p.unidade || 'un';

              const badgeTd = el('td', { style: { padding: '8px 10px' } }, badgeEl);

              const precoEl = el('td', { style: { padding: '8px 10px', fontFamily: 'var(--font-mono)', textAlign: 'right', color: 'var(--ink-2)' } });
              precoEl.textContent = 'R$ ' + sbFmtBRL(p.preco_unitario);

              const btnEditar = el('button', { class: 'pe-btn pe-btn--ghost', style: { fontSize: '12px', padding: '3px 10px' } }, 'Editar');
              btnEditar.addEventListener('click', () => sbOpenPecaForm(p));

              const btnAjustar = el('button', { class: 'pe-btn', style: { fontSize: '12px', padding: '3px 10px', marginLeft: '6px' } }, 'Ajustar');
              btnAjustar.addEventListener('click', () => sbOpenAjuste(p));

              const acoesTd = el('td', { style: { padding: '8px 10px', whiteSpace: 'nowrap' } }, btnEditar, btnAjustar);

              return el('tr', { style: { borderBottom: '1px solid var(--line)' } },
                nomeEl, catEl, qtdEl, unEl, badgeTd, precoEl, acoesTd,
              );
            }),
          );

          tableNode = el('table', { style: { width: '100%', borderCollapse: 'collapse', fontSize: '13px' } },
            thead, tbody,
          );
        }

        const listCard = el('div', { style: { ...cardStyle, padding: '0', overflow: 'hidden' } });
        listCard.appendChild(tableNode);

        cont.replaceChildren(
          el('div', {},
            el('h3', { style: { marginTop: '0', marginBottom: '16px', fontWeight: '600' } }, '🔩 Sobressalentes'),
            headerCard,
            listCard,
          ),
        );
      }

      // Renderiza imediatamente
      await sbRender();
    },
  };

  const OS_STATUS_ORDEM = ['aberta', 'autorizada', 'iniciada', 'em_execucao', 'espera', 'pronto', 'concluida', 'cancelada'];

  // Transições permitidas (espelha Rules.md §4)
  const OS_TRANSICOES = {
    aberta:      ['autorizada', 'cancelada'],
    autorizada:  ['iniciada', 'cancelada'],
    iniciada:    ['em_execucao', 'espera', 'cancelada'],
    em_execucao: ['espera', 'pronto', 'cancelada'],
    espera:      ['em_execucao', 'cancelada'],
    pronto:      ['concluida', 'em_execucao', 'cancelada'],
    concluida:   [],
    cancelada:   [],
  };

  function transitionAllowed(de, para) {
    return (OS_TRANSICOES[de] || []).includes(para);
  }

  function renderOsKanban(body) {
    const os = filteredOS();
    const cards = os.map(o => ({
      id: o.id, columnId: o.status, title: o.titulo || o.codigo || o.id,
      badges: [
        o.tipo ? { text: o.tipo, kind: 'blue' } : null,
        o.prioridade ? { text: o.prioridade, kind: o.prioridade === 'urgente' || o.prioridade === 'alta' ? 'red' : 'amber' } : null,
      ].filter(Boolean),
      _raw: o,
    }));
    const k = window.engine.kanban(body, {
      columns: OS_STATUS_ORDEM.map(s => ({ id: s, title: s })),
      cards,
      onCardClick: c => openOsDrawer(c._raw),
      onMove: async (id, from, to) => {
        if (!transitionAllowed(from, to)) {
          toast(`Transição inválida: ${from} → ${to}`, 'red');
          // reverte client-side
          const card = k._cards?.find(c => c.id === id);
          if (card) card.columnId = from;
          state.tabDirty.os = true; renderActiveTab();
          return;
        }
        try {
          const r = await fetch(`/api/os/${id}/status`, {
            method: 'PUT', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: to, obs: 'movido via painel manutenção' }),
          });
          if (!r.ok) throw new Error('HTTP ' + r.status);
          const o = (state.cache.os?.data || []).find(x => x.id === id);
          if (o) o.status = to;
          toast(`OS movida: ${from} → ${to}`, 'green');
        } catch (e) {
          toast(`Falha ao mover OS: ${e.message}`, 'red');
          state.tabDirty.os = true; renderActiveTab();
        }
      },
    });
    k._cards = cards;
  }

  function renderOsLista(body) {
    const { el, fmt } = window.engine.utils;
    const os = filteredOS();
    const wrap = el('div');
    body.replaceChildren(wrap);
    window.engine.table(wrap, {
      cols: [
        { key: 'codigo', label: 'Código' },
        { key: 'titulo', label: 'Título' },
        { key: 'tipo', label: 'Tipo', filter: true },
        { key: 'status', label: 'Status', filter: true,
          format: v => window.engine.badge(v, v === 'concluida' ? 'green' : v === 'cancelada' ? 'red' : 'amber') },
        { key: 'prioridade', label: 'Prioridade', filter: true },
        { key: 'data_abertura', label: 'Aberta', format: v => fmt.date(v) },
      ],
      rows: os,
      onRowClick: openOsDrawer,
    });
  }

  function renderOsCalendar(body) {
    const { el } = window.engine.utils;
    const os = filteredOS();
    const colorByStatus = s => s === 'concluida' ? 'var(--green)'
      : s === 'cancelada' ? 'var(--red)'
      : (s === 'em_execucao' || s === 'pronto') ? 'var(--blue)' : 'var(--amber)';
    // data da OS: prevista > conclusão > abertura
    const events = os.map(o => {
      const d = o.data_prevista || o.data_conclusao || o.data_abertura;
      if (!d) return null;
      return { id: o.id, date: String(d).slice(0, 10), title: o.codigo || o.titulo || o.id,
               color: colorByStatus(o.status), _raw: o };
    }).filter(Boolean);
    const wrap = el('div');
    body.replaceChildren(wrap);
    if (!events.length) {
      wrap.appendChild(el('div', { style: { padding: '24px', color: 'var(--ink-3)', textAlign: 'center' } },
        'Nenhuma OS com data nesta categoria.'));
      return;
    }
    // ponytail: read-only (não há PUT geral de OS p/ reagendar via drag). Clique abre a OS.
    window.engine.calendar(wrap, {
      events,
      draggable: false,
      onEventClick: ev => openOsDrawer(ev._raw),
    });
  }

  function openOsDrawer(os) {
    const { el } = window.engine.utils;
    const statusColor = { concluida: 'green', cancelada: 'red', em_execucao: 'blue', pronto: 'blue' };
    const campos = [
      ['Código', os.codigo || os.id],
      ['Tipo', os.tipo || '—'],
      ['Status', os.status],
      ['Prioridade', os.prioridade || 'normal'],
      ['Ativo vinculado', os.ativo_id || os.ativoId || '—'],
      ['Responsável', os.responsavel || '—'],
      ['Abertura', os.data_abertura || os.abertura || '—'],
      ['Conclusão', os.data_conclusao || os.dataConclusao || '—'],
      ['Origem', os.origem || os.modulo_origem || 'manual'],
      ['Plano vinculado', os.planoId || os.plano_id || '—'],
      ['Materiais/Peças', os.pecas || os.materiais || '—'],
    ];
    const trans = (OS_TRANSICOES[os.status] || []);
    const m = window.engine.modal({
      title: `${os.codigo || os.id} — ${os.titulo || os.descricao?.slice(0, 50) || ''}`,
      body: el('div', {},
        el('div', { style: { marginBottom: '10px' } },
          window.engine.badge(os.status, statusColor[os.status] || 'amber'),
          os.prioridade === 'urgente' || os.prioridade === 'alta' ? el('span', { style: { marginLeft: '6px' } }, window.engine.badge(os.prioridade, 'red')) : null,
        ),
        os.titulo || os.descricao ? el('div', { style: { padding: '8px 10px', background: 'var(--bg3)', borderRadius: '6px', fontSize: '13px', marginBottom: '12px' } }, os.titulo || os.descricao) : null,
        el('div', { style: { fontSize: '13px' } },
          ...campos.filter(([, v]) => v && v !== '—').map(([k, v]) => el('div', {
            style: { display: 'flex', gap: '8px', padding: '5px 0', borderBottom: '1px solid var(--line)' },
          }, el('div', { style: { color: 'var(--ink-3)', minWidth: '160px', flexShrink: 0 } }, k),
             el('div', {}, String(v))))),
      ),
      footer: [
        ...trans.map(t => el('button', { class: 'pe-btn pe-btn--primary', onclick: async () => {
          try {
            const r = await fetch(`/api/os/${os.id}/status`, {
              method: 'PUT', headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ status: t }),
            });
            if (!r.ok) throw new Error('HTTP ' + r.status);
            os.status = t;
            const cached = state.cache.os?.data;
            if (cached) { const idx = cached.findIndex(x => x.id === os.id); if (idx >= 0) cached[idx].status = t; }
            toast(`OS → ${t}`, 'green');
            m.close();
            state.tabDirty.os = true;
            renderActiveTab();
          } catch (e) { toast(`Falha: ${e.message}`, 'red'); }
        } }, `→ ${t}`)),
        el('button', { class: 'pe-btn', onclick: () => m.close() }, 'Fechar'),
      ],
    });
    m.open();
  }

  // Toast simples (5s)
  function toast(text, kind) {
    const { el } = window.engine.utils;
    const t = el('div', { style: {
      position: 'fixed', bottom: '20px', right: '20px', zIndex: '999',
      background: 'var(--panel)', border: `1px solid var(--${kind || 'acc'})`,
      color: `var(--${kind || 'acc'})`,
      padding: '10px 14px', borderRadius: '6px', boxShadow: '0 4px 12px rgba(0,0,0,.4)',
      maxWidth: '420px',
    } }, text);
    document.body.appendChild(t);
    setTimeout(() => t.remove(), 5000);
  }

  // ── helpers de formatação local ─────────────────────────────────────────
  const fH = h => `${Number(h || 0).toFixed(1)} h`;
  const fD = iso => iso ? new Date(iso).toLocaleDateString('pt-BR') : '–';
  const fDT = iso => iso ? new Date(iso).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' }) : '–';
  const todayISO = () => new Date().toISOString().slice(0, 10);

  const SC = { danger: 'var(--red)', warn: 'var(--amber)', proximo: 'var(--acc)', ok: 'var(--green)' };
  const SC2 = { danger: 'rd', warn: 'am', proximo: 'bl', ok: 'gn' };
  const SL = { danger: 'VENCIDA', warn: 'URGENTE', proximo: 'PRÓXIMA', ok: 'EM DIA' };

  function badgeHtml(st, txt) {
    const colors = { danger: '#ef4444', warn: '#f59e0b', proximo: '#00b4d8', ok: '#22c55e' };
    const c = colors[st] || colors.ok;
    return `<span style="display:inline-flex;align-items:center;padding:2px 7px;border-radius:9999px;font-size:9px;font-weight:700;font-family:var(--font-mono);background:${c}22;color:${c};border:1px solid ${c}55">${txt || SL[st] || st}</span>`;
  }

  // ── Drawer de ativo: 5 abas (Status / Uso / Manutenção / Histórico / Combustível) ──
  function openAtivoDrawer(ativo) {
    const { el } = window.engine.utils;
    const tipo = window.ERP_MANUT_MOCKS?.TIPOS?.[ativo.tipo];
    let pr = calcProxManut(ativo);
    let activeSub = 'status';
    const subBody = el('div', { style: { marginTop: '10px', maxHeight: '60vh', overflowY: 'auto' } });

    // ── Bridge global para os onclick handlers no innerHTML ─────────────────
    window._manutD = {
      uid: ativo.id,
      getHist: () => getHistUnit(ativo.id),
      saveHist: h => { saveHistUnit(ativo.id, h); pr = calcProxManut(ativo); },
      refresh: () => { refreshTabBar(); renderSub(); state.tabDirty.ativos = state.tabDirty.dashboard = true; },
      regUso: () => {
        const h_in = parseFloat(document.getElementById('_md-h')?.value);
        const op = document.getElementById('_md-op')?.value;
        const c = parseFloat(document.getElementById('_md-c')?.value) || 0;
        const obs = document.getElementById('_md-obs')?.value || '';
        const data = document.getElementById('_md-data')?.value || todayISO();
        if (!h_in || h_in <= 0) { toast('Informe as horas trabalhadas', 'amber'); return; }
        if (!op) { toast('Selecione o operador', 'amber'); return; }
        const hist = window._manutD.getHist();
        hist.regs.push({ id: 'r' + Date.now(), dt: new Date().toISOString(), h: h_in, c, op, obs, data });
        hist.hor = Math.round((hist.hor + h_in) * 10) / 10;
        // Sync horimetro ao ativo no ERP
        if (typeof window.getAtivos === 'function' && typeof window.saveAtivos === 'function') {
          const ativos = window.getAtivos();
          const idx = ativos.findIndex(a => a.id === ativo.id);
          if (idx >= 0) { ativos[idx].horimetro = hist.hor; window.saveAtivos(ativos); }
        }
        window._manutD.saveHist(hist);
        window._manutD.refresh();
        toast(`Uso registrado: +${h_in}h | Horímetro: ${fH(hist.hor)}`, 'green');
      },
      regManut: async () => {
        // Reads resp from closure-scoped _mnRespEl set by renderSubManutAPI
        const resp = (window._manutD._mnRespEl?.value || '').trim();
        const sels = [...subBody.querySelectorAll('._mn-cb:checked')].map(cb => parseInt(cb.value, 10));
        if (!sels.length) { toast('Selecione ao menos um serviço', 'amber'); return; }
        if (!resp) { toast('Informe o responsável', 'amber'); return; }
        const token = localStorage.getItem('xcmasm_token') || '';
        try {
          const r = await fetch(apiUrl('/api/manutencao/registro'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
            body: JSON.stringify({ ativo_id: ativo.id, responsavel: resp, itens: sels }),
          });
          if (!r.ok) {
            const e = await r.json().catch(() => ({}));
            toast('Erro: ' + (e.detail || ('HTTP ' + r.status)), 'red');
            return;
          }
          toast('Manutenção registrada', 'green');
          // Reload the manut sub-tab so statuses refresh (VENCIDA disappears for executed items)
          activeSub = 'manut';
          renderSubManutAPI(subBody, ativo);
        } catch (e) {
          toast('Falha de rede: ' + e.message, 'red');
        }
      },
      delReg: (rid) => {
        if (!confirm('Remover este registro de uso?')) return;
        const hist = window._manutD.getHist();
        const r = hist.regs.find(x => x.id === rid);
        if (r) { hist.hor = Math.round((hist.hor - r.h) * 10) / 10; hist.regs = hist.regs.filter(x => x.id !== rid); }
        window._manutD.saveHist(hist);
        window._manutD.refresh();
      },
      delManut: (mid) => {
        if (!confirm('Remover este registro de manutenção?')) return;
        const hist = window._manutD.getHist();
        hist.manut = hist.manut.filter(x => x.id !== mid);
        window._manutD.saveHist(hist);
        window._manutD.refresh();
      },
    };

    function subStatus() {
      const hist = getHistUnit(ativo.id);
      const vc = pr.filter(p => p.st === 'danger').length;
      const ur = pr.filter(p => p.st === 'warn' || p.st === 'proximo').length;
      const cT = (hist.regs || []).reduce((s, r) => s + (r.c || 0), 0);
      return `
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:12px">
          <div style="background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:10px">
            <div style="font-size:10px;color:var(--ink-3);text-transform:uppercase;letter-spacing:.05em;margin-bottom:4px">Horímetro</div>
            <div style="font-family:var(--font-mono);font-size:22px;color:var(--acc);font-weight:700">${fH(hist.hor)}</div>
          </div>
          <div style="background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:10px">
            <div style="font-size:10px;color:var(--ink-3);text-transform:uppercase;letter-spacing:.05em;margin-bottom:4px">Alertas</div>
            <div style="font-family:var(--font-mono);font-size:22px;font-weight:700;color:${vc > 0 ? 'var(--red)' : ur > 0 ? 'var(--amber)' : 'var(--green)'}">${vc + ur}</div>
          </div>
        </div>
        ${pr.length === 0 ? `<div style="color:var(--ink-3);font-size:13px;padding:12px">Sem plano de manutenção para tipo "${ativo.tipo || '—'}".<br>Cadastre o tipo do ativo para ativar o plano preventivo.</div>` : pr.map(p => {
          const barC = SC[p.st] || 'var(--green)';
          return `<div style="padding:9px 11px;border-radius:7px;border:1px solid ${barC}33;background:${p.st === 'danger' ? 'rgba(239,68,68,.08)' : p.st === 'warn' ? 'rgba(245,158,11,.08)' : 'var(--panel)'};margin-bottom:7px">
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:4px">
              <span style="font-size:12px;font-weight:600">${p.n}</span>
              ${badgeHtml(p.st)}
            </div>
            <div style="height:5px;background:var(--bg3);border-radius:3px;overflow:hidden;margin-bottom:4px">
              <div style="width:${p.pct}%;height:100%;background:${barC};border-radius:3px;transition:width .4s"></div>
            </div>
            <div style="display:flex;justify-content:space-between;font-size:10px;color:var(--ink-3);font-family:var(--font-mono)">
              <span>Última: ${p.ult > 0 ? fH(p.ult) : 'Nunca'} · A cada ${p.iv} h</span>
              <span style="color:${barC};font-weight:600">${p.st === 'danger' ? `⚠ Vencida há ${Math.abs(p.falt).toFixed(0)} h` : `Próx. ${p.prox.toFixed(0)} h (faltam ${p.falt.toFixed(0)} h)`}</span>
            </div>
          </div>`;
        }).join('')}
        ${hist.manut.length > 0 ? `<div style="margin-top:12px;font-size:12px;font-weight:600;margin-bottom:6px;color:var(--ink-3)">Últimas manutenções</div>
        ${[...hist.manut].reverse().slice(0, 3).map(m => `
          <div style="padding:6px 0;border-bottom:1px solid var(--line);font-size:12px">
            <div style="font-weight:600">${fD(m.data)} — ${m.resp}</div>
            <div style="color:var(--ink-3);margin-top:1px">${getManutServicoLabels(m).slice(0, 3).join(', ')}${getManutServicoLabels(m).length > 3 ? '…' : ''}</div>
            ${getManutMaterialLabels(m).length ? `<div style="color:var(--ink-3);margin-top:2px;font-size:11px">Materiais: ${getManutMaterialLabels(m).slice(0, 3).join(', ')}${getManutMaterialLabels(m).length > 3 ? '…' : ''}</div>` : ''}
          </div>`).join('')}` : ''}`;
    }

    function subUso() {
      const hist = getHistUnit(ativo.id);
      const recent = [...(hist.regs || [])].reverse().slice(0, 8);
      const vc = pr.filter(p => p.st === 'danger' || p.st === 'warn').length;
      return `
        <div style="margin-bottom:13px">
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:9px;margin-bottom:9px">
            <div><label style="display:block;font-size:10px;font-weight:600;color:var(--ink-3);margin-bottom:3px;text-transform:uppercase">Data *</label>
              <input class="form-inp" id="_md-data" type="date" value="${todayISO()}" style="width:100%;padding:7px 9px;border:1px solid var(--line);border-radius:6px;font-size:12px;background:var(--bg2);color:var(--ink)"></div>
            <div><label style="display:block;font-size:10px;font-weight:600;color:var(--ink-3);margin-bottom:3px;text-transform:uppercase">Horas trabalhadas *</label>
              <input class="form-inp" id="_md-h" type="number" min="0.1" step="0.1" placeholder="0.0" style="width:100%;padding:7px 9px;border:1px solid var(--line);border-radius:6px;font-size:12px;background:var(--bg2);color:var(--ink)"></div>
          </div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:9px;margin-bottom:9px">
            <div><label style="display:block;font-size:10px;font-weight:600;color:var(--ink-3);margin-bottom:3px;text-transform:uppercase">Combustível (L)</label>
              <input class="form-inp" id="_md-c" type="number" min="0" step="0.5" placeholder="0.0" style="width:100%;padding:7px 9px;border:1px solid var(--line);border-radius:6px;font-size:12px;background:var(--bg2);color:var(--ink)"></div>
            <div><label style="display:block;font-size:10px;font-weight:600;color:var(--ink-3);margin-bottom:3px;text-transform:uppercase">Operador *</label>
              <select id="_md-op" style="width:100%;padding:7px 9px;border:1px solid var(--line);border-radius:6px;font-size:12px;background:var(--bg2);color:var(--ink)">
                <option value="">Selecionar…</option>
                <option>Luciano Ferreira</option><option>Carlos Silva</option>
                <option>João Mendes</option><option>Pedro Santos</option><option>Maria Oliveira</option><option>[Outro]</option>
              </select></div>
          </div>
          <div style="margin-bottom:9px"><label style="display:block;font-size:10px;font-weight:600;color:var(--ink-3);margin-bottom:3px;text-transform:uppercase">Observações / Área trabalhada</label>
            <textarea id="_md-obs" rows="2" style="width:100%;padding:7px 9px;border:1px solid var(--line);border-radius:6px;font-size:12px;background:var(--bg2);color:var(--ink);resize:vertical"></textarea></div>
          ${vc > 0 ? `<div style="padding:8px 12px;border-radius:6px;background:rgba(245,158,11,.12);border:1px solid var(--amber);color:var(--amber);font-size:11px;margin-bottom:9px">⚠️ Esta unidade tem ${vc} manutenção(ões) vencida(s)/urgente(s). Verifique antes de operar.</div>` : ''}
          <button class="btn btn-primary" onclick="_manutD.regUso()" style="padding:7px 16px;font-size:12px">➕ Registrar Uso</button>
        </div>
        ${recent.length > 0 ? `<div style="font-size:12px;font-weight:600;color:var(--ink-3);margin-bottom:6px">Registros recentes</div>
        ${recent.map(r => `<div style="display:flex;justify-content:space-between;align-items:center;padding:7px 0;border-bottom:1px solid var(--line);font-size:12px">
          <div><span style="font-weight:600">${fD(r.data || r.dt?.slice(0,10))}</span><span style="color:var(--ink-3);margin-left:7px">${r.op}</span></div>
          <div style="display:flex;gap:12px;align-items:center">
            <span style="color:var(--acc);font-family:var(--font-mono);font-weight:700">${fH(r.h)}</span>
            ${r.c ? `<span style="color:var(--amber);font-family:var(--font-mono)">${r.c} L</span>` : ''}
            <button onclick="_manutD.delReg('${r.id}')" style="background:none;border:none;cursor:pointer;color:var(--ink-3);font-size:12px;padding:2px 6px" title="Remover">✕</button>
          </div>
        </div>`).join('')}` : ''}`;
    }

    // Legacy subManut() kept for reference but no longer drives the manut tab.
    // The SUBS map no longer has a 'manut' key; renderSubManutAPI() is the sole renderer.
    function subManut() {
      // Intentionally unused — renderSubManutAPI() replaced this path.
      return '';
    }

    // ── API-backed Manutenção sub-tab renderer (Phase 02-02) ─────────────────
    // Safe DOM only: all server-supplied text via el()/textContent, never innerHTML.
    // Status color map: VENCIDA→red, URGENTE→amber, PROXIMA→blue(acc), EM_DIA→green, other→neutral
    async function renderSubManutAPI(body, a) {
      // Step 1: loading state
      body.replaceChildren(
        el('div', { style: { padding: '16px', color: 'var(--ink-3)', fontSize: '13px' } },
          'Carregando plano...')
      );

      const token = localStorage.getItem('xcmasm_token') || '';
      let data;
      try {
        const res = await fetch(
          apiUrl('/api/manutencao/plano-ativo?ativo_id=' + encodeURIComponent(a.id)),
          { headers: { 'Authorization': 'Bearer ' + token } }
        );
        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          const msg = err.detail || ('HTTP ' + res.status);
          const errNode = el('div', { style: { padding: '14px', color: 'var(--red)', fontSize: '13px' } });
          errNode.textContent = 'Erro ao carregar plano: ' + msg;
          body.replaceChildren(errNode);
          return;
        }
        data = await res.json();
      } catch (e) {
        const errNode = el('div', { style: { padding: '14px', color: 'var(--red)', fontSize: '13px' } });
        errNode.textContent = 'Falha de rede: ' + e.message;
        body.replaceChildren(errNode);
        return;
      }

      const { itens = [], uso_atual = 0, unidade_uso = 'h' } = data;

      // Step 3: empty state
      if (!itens.length) {
        const empty = el('div', { style: { padding: '14px', color: 'var(--ink-3)', fontSize: '13px' } });
        empty.textContent = 'Sem plano de manutenção para o tipo deste ativo.';
        body.replaceChildren(empty);
        return;
      }

      // Status → badge kind + bar color
      const STATUS_KIND = { VENCIDA: 'danger', URGENTE: 'warn', PROXIMA: 'proximo', EM_DIA: 'ok' };
      const STATUS_LABEL = { VENCIDA: 'VENCIDA', URGENTE: 'URGENTE', PROXIMA: 'PRÓXIMA', EM_DIA: 'EM DIA', POR_TEMPO: 'POR TEMPO', SEM_FREQ: 'SEM FREQ' };
      const BAR_COLOR = {
        VENCIDA: 'var(--red)', URGENTE: 'var(--amber)', PROXIMA: 'var(--acc)', EM_DIA: 'var(--green)',
      };

      // Step 4: build checklist with el() + textContent only
      const list = el('div', {});
      itens.forEach(item => {
        const kind = STATUS_KIND[item.status] || '';
        const statusLabel = STATUS_LABEL[item.status] || item.status;
        const barColor = BAR_COLOR[item.status] || 'var(--acc)';
        const unidade = item.unidade || unidade_uso || 'h';
        const falta = typeof item.falta === 'number' ? item.falta : 0;
        const pct = typeof item.pct === 'number' ? Math.min(100, Math.max(0, item.pct)) : 0;

        const cb = el('input', {
          type: 'checkbox',
          id: '_mn-' + item.item_id,
          class: '_mn-cb',
          value: String(item.item_id),
          style: { width: '14px', height: '14px', accentColor: 'var(--acc)', flexShrink: '0', marginTop: '2px' },
        });

        // servico_nome via textContent — never innerHTML (T-02-07)
        const nomeEl = el('div', { style: { fontSize: '12px', fontWeight: '600', marginBottom: '2px' } });
        nomeEl.textContent = item.servico_nome;

        // progress bar
        const bar = el('div',
          { style: { height: '4px', background: 'var(--bg3)', borderRadius: '3px', overflow: 'hidden', margin: '4px 0' } },
          el('div', { style: { width: pct + '%', height: '100%', background: barColor, borderRadius: '3px' } })
        );

        // detail line via textContent
        const detalheEl = el('div', { style: { fontSize: '10px', color: 'var(--ink-3)', fontFamily: 'var(--font-mono)' } });
        if (item.por_tempo || item.intervalo === null) {
          detalheEl.textContent = 'Frequência por tempo — verificar calendário';
        } else {
          detalheEl.textContent = 'A cada ' + item.intervalo + ' ' + unidade + ' · faltam ' + Math.max(0, falta).toFixed(0) + ' ' + unidade;
        }

        const badgeEl = window.engine.badge(statusLabel, kind);

        const lbl = el('label', {
          id: '_mnl-' + item.item_id,
          style: {
            display: 'flex', gap: '9px', alignItems: 'flex-start', padding: '8px 11px',
            borderRadius: '7px', cursor: 'pointer', border: '2px solid var(--line)',
            background: 'var(--panel)', marginBottom: '6px', transition: 'all .1s',
          },
          onclick: () => {
            // cb.checked is pre-toggle at label onclick time — negate to get post-toggle state
            const willBeChecked = !cb.checked;
            lbl.style.borderColor = willBeChecked ? 'var(--acc)' : 'var(--line)';
            lbl.style.background  = willBeChecked ? 'rgba(0,180,216,.08)' : 'var(--panel)';
          },
        }, cb, el('div', { style: { flex: '1', minWidth: '0' } }, nomeEl, bar, detalheEl), badgeEl);

        list.appendChild(lbl);
      });

      // Step 5: responsável select + Registrar button
      const respLabel = el('label', { style: { display: 'block', fontSize: '10px', fontWeight: '600', color: 'var(--ink-3)', marginBottom: '3px', textTransform: 'uppercase' } });
      respLabel.textContent = 'Responsável *';

      const respSel = el('select', {
        id: '_mn-resp',
        style: { width: '100%', padding: '7px 9px', border: '1px solid var(--line)', borderRadius: '6px', fontSize: '12px', background: 'var(--bg2)', color: 'var(--ink)' },
      });
      ['', 'Luciano Ferreira', 'Carlos Silva', 'João Mendes', 'Pedro Santos', 'Maria Oliveira'].forEach((name, i) => {
        const opt = document.createElement('option');
        opt.value = name;
        opt.textContent = i === 0 ? 'Selecionar…' : name;
        respSel.appendChild(opt);
      });

      // Store resp select in closure for regManut to read without global getElementById
      window._manutD._mnRespEl = respSel;

      const infoBar = el('div', {
        style: { padding: '8px 12px', borderRadius: '6px', background: 'rgba(0,180,216,.12)', border: '1px solid var(--acc)', fontSize: '12px', marginBottom: '11px' },
      });
      const usoLabel = el('span');
      usoLabel.textContent = 'Uso atual: ' + Number(uso_atual || 0).toFixed(1) + ' ' + (unidade_uso || 'h') + ' — Marque os serviços executados';
      infoBar.appendChild(usoLabel);

      const btnReg = el('button', {
        class: 'btn btn-primary',
        style: { background: 'var(--green)', padding: '7px 16px', fontSize: '12px', marginTop: '10px' },
        onclick: () => window._manutD.regManut(),
      }, '✓ Registrar Manutencao');

      const footer = el('div', { style: { marginTop: '12px' } },
        el('div', { style: { marginBottom: '9px' } }, respLabel, respSel),
        btnReg
      );

      body.replaceChildren(infoBar, list, footer);
    }

    function subHist() {
      const hist = getHistUnit(ativo.id);
      const manut = [...(hist.manut || [])].reverse();
      if (!manut.length) return `<div style="color:var(--ink-3);font-size:13px;padding:12px">Nenhuma manutenção registrada para este ativo.</div>`;
      return `<table style="width:100%;border-collapse:collapse;font-size:12px">
        <thead><tr style="background:var(--panel)">
          <th style="padding:7px 9px;text-align:left;font-size:10px;font-weight:600;color:var(--ink-3);border-bottom:1px solid var(--line)">Data</th>
          <th style="padding:7px 9px;text-align:right;font-size:10px;font-weight:600;color:var(--ink-3);border-bottom:1px solid var(--line)">Horímetro</th>
          <th style="padding:7px 9px;text-align:left;font-size:10px;font-weight:600;color:var(--ink-3);border-bottom:1px solid var(--line)">Responsável</th>
          <th style="padding:7px 9px;text-align:left;font-size:10px;font-weight:600;color:var(--ink-3);border-bottom:1px solid var(--line)">Serviços realizados</th>
          <th style="padding:7px 9px;text-align:left;font-size:10px;font-weight:600;color:var(--ink-3);border-bottom:1px solid var(--line)">Materiais</th>
          <th style="padding:7px 9px;border-bottom:1px solid var(--line)"></th>
        </tr></thead><tbody>
        ${manut.map(m => `<tr>
          <td style="padding:6px 9px;border-bottom:1px solid var(--line);font-weight:600">${fD(m.data)}</td>
          <td style="padding:6px 9px;border-bottom:1px solid var(--line);text-align:right;font-family:var(--font-mono);color:var(--acc)">${fH(m.h)}</td>
          <td style="padding:6px 9px;border-bottom:1px solid var(--line)">${m.resp}</td>
          <td style="padding:6px 9px;border-bottom:1px solid var(--line);max-width:220px">${getManutServicoLabels(m).map(i => `<span style="display:inline-flex;align-items:center;padding:1px 5px;border-radius:4px;font-size:9px;background:var(--panel);border:1px solid var(--line);margin:1px">${i}</span>`).join(' ')}</td>
          <td style="padding:6px 9px;border-bottom:1px solid var(--line);max-width:220px">${getManutMaterialLabels(m).length ? getManutMaterialLabels(m).map(i => `<span style="display:inline-flex;align-items:center;padding:1px 5px;border-radius:4px;font-size:9px;background:rgba(0,180,216,.08);border:1px solid var(--line);margin:1px">${i}</span>`).join(' ') : '<span style="color:var(--ink-3)">—</span>'}</td>
          <td style="padding:6px 9px;border-bottom:1px solid var(--line)">
            <button onclick="_manutD.delManut('${m.id}')" style="background:none;border:1px solid var(--line);cursor:pointer;color:var(--ink-3);font-size:10px;padding:2px 7px;border-radius:4px" title="Remover">🗑</button>
          </td>
        </tr>`).join('')}
        </tbody></table>`;
    }

    function subComb() {
      const hist = getHistUnit(ativo.id);
      const regs = (hist.regs || []).filter(r => r.c > 0);
      const tC = regs.reduce((s, r) => s + r.c, 0);
      const tH = regs.reduce((s, r) => s + r.h, 0);
      const byOp = {};
      regs.forEach(r => { if (!byOp[r.op]) byOp[r.op] = { c: 0, h: 0 }; byOp[r.op].c += r.c; byOp[r.op].h += r.h; });
      const ops = Object.entries(byOp).sort((a, b) => b[1].c - a[1].c);
      const mx = ops.length ? Math.max(...ops.map(o => o[1].c)) : 1;
      return `
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:13px">
          <div style="background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:10px">
            <div style="font-size:10px;color:var(--ink-3);text-transform:uppercase;margin-bottom:4px">Total consumido</div>
            <div style="font-family:var(--font-mono);font-size:20px;color:var(--amber);font-weight:700">${tC.toFixed(1)} L</div>
          </div>
          <div style="background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:10px">
            <div style="font-size:10px;color:var(--ink-3);text-transform:uppercase;margin-bottom:4px">Média L/hora</div>
            <div style="font-family:var(--font-mono);font-size:20px;color:var(--acc);font-weight:700">${tH > 0 ? (tC / tH).toFixed(2) : '–'} L/h</div>
          </div>
        </div>
        ${regs.length === 0 ? '<div style="color:var(--ink-3);font-size:13px">Nenhum registro com combustível.</div>' : ''}
        ${ops.length > 0 ? `<div style="font-size:12px;font-weight:600;color:var(--ink-3);margin-bottom:8px">Por operador</div>
        ${ops.map(([op, d], i) => `<div style="display:flex;align-items:center;gap:8px;margin-bottom:9px">
          <div style="font-size:11px;color:var(--ink-2);width:130px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex-shrink:0">${op}</div>
          <div style="flex:1;height:12px;background:var(--panel);border-radius:3px;overflow:hidden">
            <div style="width:${Math.round(d.c / mx * 100)}%;height:100%;background:hsl(${40 + i * 40},74%,55%);border-radius:3px;display:flex;align-items:center;justify-content:flex-end;padding-right:4px">
              <span style="font-size:9px;font-weight:700;color:#fff">${d.c.toFixed(1)}L</span>
            </div>
          </div>
          <div style="font-size:10px;font-family:var(--font-mono);color:var(--ink-3);width:60px;text-align:right;flex-shrink:0">${d.h.toFixed(1)}h</div>
        </div>`).join('')}` : ''}`;
    }

    // NOTE: 'manut' is intentionally absent — renderSubManutAPI() is the sole async renderer for that tab.
    const SUBS = { status: subStatus, uso: subUso, hist: subHist, comb: subComb };
    const TABS = [
      { id: 'status', label: '📊 Status' },
      { id: 'uso',    label: '⏱ Uso' },
      { id: 'manut',  label: '🔧 Manutenção' },
      { id: 'hist',   label: '📋 Histórico' },
      { id: 'comb',   label: '⛽ Combustível' },
    ];

    function renderSub() {
      // manut tab: async API path — must return before the synchronous innerHTML path below
      if (activeSub === 'manut') { renderSubManutAPI(subBody, ativo); return; }
      subBody.innerHTML = SUBS[activeSub]?.() || '';
    }

    const tabBar = el('div', { style: { display: 'flex', gap: '3px', padding: '4px', background: 'var(--panel)', borderRadius: '8px', flexWrap: 'wrap' } });
    function refreshTabBar() {
      tabBar.replaceChildren(...TABS.map(t => el('button', {
        class: 'pe-btn ' + (activeSub === t.id ? 'pe-btn--primary' : 'pe-btn--ghost'),
        style: { fontSize: '11px', padding: '4px 10px', minHeight: '28px' },
        onclick: () => { activeSub = t.id; refreshTabBar(); renderSub(); },
      }, t.label)));
    }

    const tipo_info = tipo ? `${tipo.emoji} ${tipo.nome}` : (ativo.tipo || '');
    const m = window.engine.modal({
      title: `${tipo_info ? tipo_info + ' · ' : ''}${ativo.nome}`,
      body: el('div', {}, tabBar, subBody),
      footer: [el('button', { class: 'pe-btn pe-btn--primary', onclick: () => m.close() }, 'Fechar')],
    });
    m.open();
    refreshTabBar();
    renderSub();
  }

  // ── helpers de manutenção ───────────────────────────────────────────────

  function statusManutAtivo(ativoId) {
    const ativo = (state.cache.ativos?.data || []).find(a => a.id === ativoId);
    if (!ativo) return null;
    const pr = calcProxManut(ativo);
    if (!pr.length) return null;
    if (pr.some(p => p.st === 'danger')) return 'danger';
    if (pr.some(p => p.st === 'warn')) return 'warn';
    return 'ok';
  }

  // ── Planos nomeados (catalogo_planos) ────────────────────────────────────
  function fmtFreq(v) {
    if (!v) return '—';
    let f; try { f = typeof v === 'string' ? JSON.parse(v) : v; } catch (_) { return String(v); }
    if (!f || f.valor == null) return '—';
    const un = f.tipo === 'por_tempo' ? (f.unidade || 'meses') : (f.unidade || 'h');
    return `a cada ${f.valor} ${un}`;
  }

  function _field(label, inp) {
    const { el } = window.engine.utils;
    return el('div', {}, el('label', { style: { display: 'block', fontSize: '11px', color: 'var(--ink-3)', marginBottom: '3px' } }, label), inp);
  }

  async function openPlanoCatalogoDrawer(plano) {
    const { el } = window.engine.utils;
    let d;
    try {
      d = await fetch(apiUrl(`/api/catalogo/planos-catalogo/${plano.id}`)).then(r => {
        if (!r.ok) throw new Error('HTTP ' + r.status); return r.json();
      });
    } catch (e) { toast('Falha ao carregar plano: ' + e.message, 'red'); return; }
    let tipos = '—';
    try { tipos = JSON.parse(d.aplicavel_tipos || '[]').join(', ') || d.tipo_codigo || '—'; }
    catch (_) { tipos = d.tipo_codigo || '—'; }
    const itens = d.itens || [];
    const reabrir = () => { m.close(); openPlanoCatalogoDrawer(plano); };
    const body = el('div', { style: { fontSize: '13px' } },
      el('div', { style: { marginBottom: '10px', color: 'var(--ink-2)' } },
        `Categoria: ${d.categoria} · Tipos: ${tipos} · Disparo default: ${fmtFreq(d.frequencia)}`),
      el('div', { style: { fontWeight: '600', marginBottom: '6px' } }, `Serviços do plano (${itens.length})`),
      ...itens.map(it => el('div', { style: { padding: '8px 10px', background: 'var(--bg3)', borderRadius: '6px', marginBottom: '6px' } },
        el('div', { style: { display: 'flex', justifyContent: 'space-between', gap: '8px', alignItems: 'baseline' } },
          el('div', { style: { fontWeight: '600' } }, `${it.classe === 'corr' ? '🔧 ' : ''}${it.nome}`),
          el('div', { style: { display: 'flex', gap: '8px', alignItems: 'center' } },
            el('span', { style: { color: 'var(--acc)', fontFamily: 'var(--font-mono)', fontSize: '12px', whiteSpace: 'nowrap' } }, fmtFreq(it.frequencia)),
            el('button', { class: 'pe-btn', style: { padding: '0 6px', fontSize: '11px' }, title: 'Remover serviço',
              onclick: async () => {
                if (!confirm(`Remover "${it.nome}" do plano?`)) return;
                await fetch(apiUrl(`/api/catalogo/planos-catalogo/${d.id}/itens/${encodeURIComponent(it.servico_id)}`), { method: 'DELETE' });
                reabrir();
              } }, '✕'))),
        (it.materiais && it.materiais.length)
          ? el('div', { style: { fontSize: '11px', color: 'var(--ink-3)', marginTop: '4px' } },
              'Materiais: ' + it.materiais.map(m => `${m.material_nome || m.nome_livre} (${m.qtd} ${m.unidade || 'un'})`).join(', '))
          : null,
      )),
    );
    const m = window.engine.modal({
      title: `${d.codigo} — ${d.nome}`,
      body,
      footer: [
        el('button', { class: 'pe-btn pe-btn--primary', onclick: () => openAddServicoToPlano(d, reabrir) }, '+ Serviço'),
        el('button', { class: 'pe-btn', onclick: async () => {
          if (!confirm(`Excluir o plano "${d.nome}"? (desativa)`)) return;
          await fetch(apiUrl(`/api/catalogo/planos-catalogo/${d.id}`), { method: 'DELETE' });
          toast('Plano excluído', 'green'); m.close(); renderActiveTab();
        } }, '🗑 Excluir'),
        el('button', { class: 'pe-btn', onclick: () => m.close() }, 'Fechar'),
      ],
    });
    m.open();
  }

  async function openAddServicoToPlano(plano, onDone) {
    const { el } = window.engine.utils;
    let servicos = [];
    try {
      servicos = await fetch(apiUrl('/api/catalogo/servicos')).then(r => r.ok ? r.json() : []);
    } catch (_) {}
    // filtra por categoria do plano (via aplicavel_a)
    servicos = servicos.filter(s => {
      try { return (s.aplicavel_a?.categorias || JSON.parse(s.aplicavel_a || '{}').categorias || []).includes(plano.categoria); }
      catch (_) { return true; }
    });
    const sel = el('select', { class: 'pe-input pe-select' },
      ...servicos.map(s => el('option', { value: s.id }, `${s.codigo || ''} — ${s.nome}`)));
    const fval = el('input', { class: 'pe-input', type: 'number', placeholder: 'ex: 50' });
    const fun = el('select', { class: 'pe-input pe-select' }, ...['h', 'km', 'meses'].map(u => el('option', { value: u }, u)));
    const body = el('div', { style: { display: 'grid', gap: '10px', fontSize: '13px' } },
      _field('Serviço', sel),
      el('div', { style: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' } },
        _field('Disparo: a cada', fval), _field('Unidade', fun)));
    const m = window.engine.modal({
      title: 'Adicionar serviço ao plano',
      body,
      footer: [
        el('button', { class: 'pe-btn pe-btn--primary', onclick: async () => {
          if (!sel.value) { toast('Selecione um serviço', 'amber'); return; }
          const freq = fval.value ? { tipo: fun.value === 'meses' ? 'por_tempo' : 'por_uso', valor: parseFloat(fval.value), unidade: fun.value } : null;
          await fetch(apiUrl(`/api/catalogo/planos-catalogo/${plano.id}/itens`), {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ servico_id: sel.value, frequencia: freq }),
          });
          m.close(); onDone && onDone();
        } }, 'Adicionar'),
        el('button', { class: 'pe-btn', onclick: () => m.close() }, 'Cancelar'),
      ],
    });
    m.open();
  }

  function openPlanoCreate() {
    const { el } = window.engine.utils;
    const catDefault = (state._scopeCats && state._scopeCats[0]) || 'climatizacao';
    const nome = el('input', { class: 'pe-input' });
    const cat = el('input', { class: 'pe-input' }); cat.value = catDefault;
    const tipos = el('input', { class: 'pe-input', placeholder: 'VTR_PICKUP, GAR (vírgula)' });
    const ftipo = el('select', { class: 'pe-input pe-select' },
      el('option', { value: 'por_uso' }, 'por uso (h/km)'), el('option', { value: 'por_tempo' }, 'por tempo'));
    const fval = el('input', { class: 'pe-input', type: 'number', placeholder: 'opcional' });
    const fun = el('select', { class: 'pe-input pe-select' }, ...['h', 'km', 'meses'].map(u => el('option', { value: u }, u)));
    const body = el('div', { style: { display: 'grid', gap: '10px', fontSize: '13px' } },
      _field('Nome do plano', nome),
      _field('Categoria', cat),
      _field('Tipos aplicáveis', tipos),
      el('div', { style: { display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '8px' } },
        _field('Disparo default', ftipo), _field('A cada', fval), _field('Unidade', fun)));
    const m = window.engine.modal({
      title: 'Novo plano',
      body,
      footer: [
        el('button', { class: 'pe-btn pe-btn--primary', onclick: async () => {
          if (!nome.value.trim()) { toast('Informe o nome', 'amber'); return; }
          const tiposArr = tipos.value.split(',').map(s => s.trim()).filter(Boolean);
          const freq = fval.value ? { tipo: ftipo.value, valor: parseFloat(fval.value), unidade: fun.value } : null;
          let novo;
          try {
            novo = await fetch(apiUrl('/api/catalogo/planos-catalogo'), {
              method: 'POST', headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ nome: nome.value.trim(), categoria: cat.value.trim(), aplicavel_tipos: tiposArr, frequencia: freq }),
            }).then(r => { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); });
          } catch (e) { toast('Falha ao criar: ' + e.message, 'red'); return; }
          toast('Plano criado', 'green');
          m.close();
          renderActiveTab();
          openPlanoCatalogoDrawer(novo);  // abre p/ adicionar serviços
        } }, 'Criar'),
        el('button', { class: 'pe-btn', onclick: () => m.close() }, 'Cancelar'),
      ],
    });
    m.open();
  }

  function openPlanoDrawer(plano) {
    const { el } = window.engine.utils;
    const svc = resolvePlanoServico(plano);
    const ativo = (state.cache.ativos?.data || []).find(a => a.id === plano.ativo_id);
    const planoItem = plano._planoItem || null;
    const campos = [
      ['Ativo', ativo?.nome || plano.ativo_id || '—'],
      ['Tipo aplicável', plano.tipo_codigo || '—'],
      ['Frequência', plano.frequencia?.tipo === 'por_uso' ? `A cada ${plano.frequencia.valor} ${plano.frequencia.unidade}` : 'Periódica'],
      ['Última execução', planoItem ? (planoItem.ult > 0 ? `${fH(planoItem.ult)} no horímetro` : 'Nunca') : (plano.ultima_execucao || '—')],
      ['Próxima execução', planoItem
        ? (planoItem.st === 'danger'
          ? `Vencida há ${Math.abs(planoItem.falt).toFixed(0)} h`
          : `${fH(planoItem.prox)} (${Math.max(0, planoItem.falt).toFixed(0)} h restantes)`)
        : (plano.proxima_execucao || '—')],
      ['Responsável PMOC', plano.responsavel_pmoc || '—'],
    ];
    const m = window.engine.modal({
      title: svc?.nome || plano.servico_id,
      body: el('div', {},
        el('div', { style: { fontSize: '13px', marginBottom: '12px' } },
          ...campos.map(([k, v]) => el('div', {
            style: { display: 'flex', gap: '8px', padding: '5px 0', borderBottom: '1px solid var(--line)' },
          }, el('div', { style: { color: 'var(--ink-3)', minWidth: '160px', flexShrink: 0 } }, k),
             el('div', {}, String(v))))),
        svc?.materiais?.length ? el('div', { style: { marginTop: '10px' } },
          el('div', { style: { fontWeight: '600', marginBottom: '6px', fontSize: '13px' } }, 'Materiais'),
          el('ul', { style: { paddingLeft: '18px', fontSize: '12px', lineHeight: '1.8' } },
            ...svc.materiais.map(mat => el('li', {}, `${mat.nome_livre} — ${mat.qtd} ${mat.unidade}${mat.obrigatorio ? ' (obrigatório)' : ''}`)))) : null,
      ),
      footer: [
        el('button', { class: 'pe-btn pe-btn--primary', onclick: () => { abrirOSPreventiva(plano, plano.ativo_id); m.close(); } },
          plano._status === 'danger' ? '🔴 Abrir OS (vencida)' : '+ Abrir OS Preventiva'),
        el('button', { class: 'pe-btn', onclick: () => m.close() }, 'Fechar'),
      ],
    });
    m.open();
  }

  // ── Fichas PMOC genéricas (transportes, corte) ───────────────────────────
  const _fichaCache = {};
  async function renderFichaTab(cont, kind) {
    const { el, fmt } = window.engine.utils;
    const cfg = FICHA_CFG[kind];
    cont.replaceChildren(el('div', { style: { padding: '16px', color: 'var(--ink-3)' } }, 'Carregando...'));
    let rows;
    try {
      rows = await fetch(apiUrl(cfg.endpoint)).then(r => {
        if (!r.ok) throw new Error(cfg.endpoint + ' ' + r.status); return r.json();
      });
    } catch (e) {
      cont.replaceChildren(el('div', { style: { padding: '16px', color: 'var(--red)' } },
        'Falha ao carregar: ' + e.message)); return;
    }
    _fichaCache[kind] = rows;
    const critColor = v => ({ 'CRÍTICA': 'red', 'ALTA': 'amber', 'MÉDIA': 'blue', 'BAIXA': 'green' })[v] || 'gray';
    const inop = rows.filter(r => r.estado_operacional === 'INOP').length;
    const crit = rows.filter(r => r.criticidade === 'CRÍTICA').length;
    const kpis = el('div', { style: { display: 'flex', gap: '12px', marginBottom: '12px', flexWrap: 'wrap' } },
      ...[['Ativos', rows.length], ['INOP', inop], ['Críticos', crit]].map(([l, v]) =>
        el('div', { style: { background: 'var(--panel)', border: '1px solid var(--line)', borderRadius: '8px', padding: '10px 14px' } },
          el('div', { style: { fontSize: '11px', color: 'var(--ink-3)', textTransform: 'uppercase' } }, l),
          el('div', { style: { fontFamily: 'var(--font-mono)', fontSize: '22px', color: 'var(--acc)', fontWeight: '700' } }, String(v)))));
    const wrap = el('div'); const tableWrap = el('div');
    wrap.appendChild(kpis); wrap.appendChild(tableWrap);
    cont.replaceChildren(wrap);
    window.engine.table(tableWrap, {
      cols: [
        { key: 'estado_operacional', label: '', format: v => v === 'INOP' ? '🔴' : '🟢' },
        ...cfg.cols,
        { key: 'uso_atual', label: 'Uso', format: (v, row) => `${fmt.num(v || 0, 0)} ${row.unidade_uso || ''}` },
        { key: 'criticidade', label: 'Criticidade', filter: true, format: v => v ? window.engine.badge(v, critColor(v)) : '—' },
        { key: '_os', label: '', format: (v, row) => el('button', {
          class: 'pe-btn pe-btn--primary', style: { padding: '2px 8px', fontSize: '11px' }, title: 'Nova OS para este ativo',
          onclick: (e) => { e.stopPropagation();
            if (window.novaOSComContexto) window.novaOSComContexto({ ativoId: row.ativo_id, assunto: `Manutenção — ${row.ativo_nome}` });
          },
        }, 'Nova OS') },
      ],
      rows,
      pageSize: Math.max(rows.length, 25),
      onRowClick: row => openFichaEdit(kind, row, cont),
    });
  }

  function openFichaEdit(kind, row, cont) {
    const { el } = window.engine.utils;
    const cfg = FICHA_CFG[kind];
    const inputs = {};
    const fields = cfg.edit.map(f => {
      let inp;
      if (f.opts) {
        inp = el('select', { class: 'pe-input pe-select' }, ...f.opts.map(o => el('option', { value: o }, o || '—')));
      } else if (f.type === 'textarea') {
        inp = el('textarea', { class: 'pe-input', rows: '2' });
      } else {
        inp = el('input', { class: 'pe-input', type: f.type || 'text' });
      }
      inp.value = row[f.key] == null ? '' : String(row[f.key]);
      inputs[f.key] = { inp, type: f.type };
      return el('div', { style: f.type === 'textarea' ? { gridColumn: '1 / -1' } : {} },
        el('label', { style: { display: 'block', fontSize: '11px', color: 'var(--ink-3)', marginBottom: '3px' } }, f.label),
        inp);
    });
    const body = el('div', { style: { fontSize: '13px' } },
      el('div', { style: { marginBottom: '10px', color: 'var(--ink-2)' } },
        `${row.ativo_nome} · ${row.ativo_tipo || ''} · uso ${Math.round(row.uso_atual || 0)} ${row.unidade_uso || ''}`),
      el('div', { style: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' } }, ...fields));
    const m = window.engine.modal({
      title: `Editar ficha — ${row.ativo_nome}`,
      body,
      footer: [
        el('button', {
          class: 'pe-btn pe-btn--primary', onclick: async () => {
            const payload = {};
            for (const [k, { inp, type }] of Object.entries(inputs)) {
              let v = inp.value;
              if (v === '') v = null;
              else if (type === 'number') v = parseFloat(v);
              payload[k] = v;
            }
            try {
              const r = await fetch(apiUrl(`${cfg.endpoint}/${row.ativo_id}`), {
                method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
              });
              if (!r.ok) throw new Error('PUT ' + r.status);
              m.close();
              renderFichaTab(cont, kind);
            } catch (e) { alert('Falha ao salvar: ' + e.message); }
          },
        }, 'Salvar'),
        el('button', { class: 'pe-btn', onclick: () => m.close() }, 'Fechar'),
      ],
    });
    m.open();
  }

  function openCatalogoDrawer(svc) {
    const { el } = window.engine.utils;
    const m = window.engine.modal({
      title: `${svc.codigo} — ${svc.nome}`,
      body: el('div', { style: { fontSize: '13px' } },
        svc.descricao ? el('div', { style: { marginBottom: '10px', color: 'var(--ink-2)' } }, svc.descricao) : null,
        el('div', { style: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '12px' } },
          el('div', {}, el('span', { style: { color: 'var(--ink-3)', fontSize: '11px' } }, 'Tempo estimado'),
            el('div', { style: { fontFamily: 'var(--font-mono)', fontSize: '18px', color: 'var(--acc)', marginTop: '2px' } }, `${svc.tempo_estimado_min || '—'} min`)),
          el('div', {}, el('span', { style: { color: 'var(--ink-3)', fontSize: '11px' } }, 'Versão'),
            el('div', { style: { fontFamily: 'var(--font-mono)', fontSize: '18px', color: 'var(--acc)', marginTop: '2px' } }, `v${svc.versao || 1}`))),
        svc.materiais?.length ? el('div', { style: { marginBottom: '10px' } },
          el('div', { style: { fontWeight: '600', marginBottom: '4px' } }, 'Materiais'),
          el('ul', { style: { paddingLeft: '18px', lineHeight: '1.8' } },
            ...svc.materiais.map(mat => el('li', {}, `${mat.nome_livre} — ${mat.qtd} ${mat.unidade}${mat.obrigatorio ? ' *' : ''}`)))) : null,
        svc.ferramentas?.length ? el('div', { style: { marginBottom: '10px' } },
          el('div', { style: { fontWeight: '600', marginBottom: '4px' } }, 'Ferramentas'),
          el('ul', { style: { paddingLeft: '18px', lineHeight: '1.8' } },
            ...svc.ferramentas.map(f => el('li', {}, f.nome)))) : null,
        svc.pessoal?.length ? el('div', { style: { marginBottom: '10px' } },
          el('div', { style: { fontWeight: '600', marginBottom: '4px' } }, 'Pessoal qualificado'),
          el('ul', { style: { paddingLeft: '18px', lineHeight: '1.8' } },
            ...svc.pessoal.map(p => {
              const q = (window.ERP_MANUT_MOCKS?.qualificacoes_catalogo || []).find(q => q.codigo === p.qualificacao_codigo);
              return el('li', {}, `${q?.nome || p.qualificacao_codigo} ×${p.qtd}${p.opcional ? ' (opcional)' : ''}`);
            }))) : null,
      ),
      footer: [
        el('button', { class: 'pe-btn pe-btn--primary', onclick: () => {
          m.close();
          if (window.novaOSComContexto) window.novaOSComContexto({
            servicoId: svc.id, assunto: svc.nome, descricao: svc.descricao || '',
          });
        } }, 'Nova OS com este serviço'),
        el('button', { class: 'pe-btn', onclick: () => m.close() }, 'Fechar'),
      ],
    });
    m.open();
  }

  function abrirOSPreventiva(plano, ativoId) {
    const ativo = (state.cache.ativos?.data || []).find(a => a.id === (ativoId || plano.ativo_id));
    const svc = resolvePlanoServico(plano);
    const osId = 'OSM-' + Date.now().toString(36).toUpperCase();
    const abertura = new Date().toISOString();

    // 1. Salva em os_manut (store legado — mantém retrocompatibilidade)
    if (typeof window.getOSManut === 'function' && typeof window.saveOSManut === 'function') {
      const osManutData = window.getOSManut();
      osManutData.push({
        id: osId,
        ativoId: ativoId || plano.ativo_id || '',
        ativoNome: ativo?.nome || plano.tipo_codigo || '—',
        tipo: 'preventiva',
        descricao: svc?.nome || plano.servico_id,
        responsavel: plano.responsavel_pmoc || '',
        abertura: abertura.slice(0, 10),
        prazo: '',
        pecas: (svc?.materiais || []).map(m => m.nome_livre).join(', '),
        status: 'aberta',
        planoId: plano.id,
        servicoId: plano.servico_id,
        criadoPor: 'sistema (PMOC)',
        dataCriacao: abertura,
      });
      window.saveOSManut(osManutData);
    }

    const requisitosMateriais = (svc?.materiais || []).filter(mat => mat.obrigatorio).map(mat => ({
      id: 'r-' + Math.random().toString(36).slice(2, 8),
      descricao: `${mat.nome_livre} — ${mat.qtd} ${mat.unidade}`,
      obrigatorio: true,
      atendido: false,
      tipo: 'material',
    }));
    const requisitosEquipe = (svc?.pessoal || []).filter(p => !p.opcional).map(p => ({
      id: 'r-' + Math.random().toString(36).slice(2, 8),
      descricao: `Equipe: ${p.qualificacao_codigo} (qtd ${p.qtd || 1})`,
      obrigatorio: true,
      atendido: false,
      tipo: 'pessoal',
    }));
    const requisitosFerramentas = (svc?.ferramentas || []).filter(f => f.obrigatorio).map(f => ({
      id: 'r-' + Math.random().toString(36).slice(2, 8),
      descricao: `Ferramenta: ${f.nome} (${f.qtd || 1})`,
      obrigatorio: true,
      atendido: false,
      tipo: 'ferramenta',
    }));
    const requisitos = [...requisitosMateriais, ...requisitosEquipe, ...requisitosFerramentas];

    // 2. Salva também em PS (Serviços — visibilidade cross-módulo, Fase 1)
    if (typeof window.getPS === 'function' && typeof window.savePS === 'function') {
      const psId = 'PS-' + Date.now().toString(36).toUpperCase();
      const ps = window.getPS();
      ps.push({
        id: psId,
        assunto: svc?.nome || plano.servico_id,
        descricao: `Preventiva automática — ${ativo?.nome || ativoId || 'ativo não especificado'}\nOS Manutenção: ${osId} | Plano: ${plano.id}`,
        prioridade: 'normal',
        status: 'autorizada',
        abertura,
        executor: plano.responsavel_pmoc || '',
        executorOrg: '',
        modulo_origem: 'manutencao',
        ativo_id: ativoId || plano.ativo_id || '',
        plano_id: plano.id,
        servico_id: plano.servico_id,
        osPai: null,
        osFilhos: [],
        requisitos,
        materiaisPrevistos: (svc?.materiais || []).map(m => ({ ...m })),
        servico_catalogo_id: plano.servico_id,
        custoPlanejado: 0,
        custoReal: 0,
        origem: 'manutencao',
      });
      window.savePS(ps);
    }

    // Atualiza cache local para refletir na UI sem reload
    if (state.cache.os?.data) {
      state.cache.os.data.push({
        id: osId, codigo: osId, titulo: svc?.nome || plano.servico_id,
        tipo: 'preventiva', status: 'aberta', prioridade: 'normal',
        ativo_id: ativoId || plano.ativo_id,
        data_abertura: abertura.slice(0, 10), modulo_origem: 'manutencao',
      });
    }

    // 3. Espelha em OS (Serviços) para visibilidade imediata no módulo Serviços
    const servicosPayload = {
      id: osId,
      assunto: svc?.nome || plano.servico_id,
      descricao: `Preventiva automática — ${ativo?.nome || ativoId || 'ativo não especificado'}\nOS Manutenção: ${osId} | Plano: ${plano.id}`,
      status: 'aberta',
      prioridade: 'normal',
      prazo: '',
      executor: plano.responsavel_pmoc || '',
      ativo_id: ativoId || plano.ativo_id || '',
      plano_id: plano.id,
      servico_id: plano.servico_id,
      servico_catalogo_id: plano.servico_id,
      materiaisPrevistos: (svc?.materiais || []).map(m => ({ ...m })),
      requisitos,
      dataAbertura: abertura,
      criadoPor: 'sistema (PMOC)',
      origem: 'manutencao',
      modulo_origem: 'manutencao',
    };
    let syncOk = false;
    try {
      if (typeof window.syncManutOSIntoServicos === 'function') {
        window.syncManutOSIntoServicos(servicosPayload);
        syncOk = true;
      }
    } catch (_err) {
      syncOk = false;
    }
    // Fallback defensivo: grava direto no store de OS caso a ponte de sincronização falhe.
    if (!syncOk && typeof window.getOS === 'function' && typeof window.saveOS === 'function') {
      const osData = window.getOS();
      const exists = osData.some(o => o.id === osId);
      if (!exists) {
        osData.push({
          id: osId,
          solicitante: 'Sistema',
          solicitanteId: '',
          executorOrg: 'CMASM-10',
          destino: 'CMASM-10',
          assunto: servicosPayload.assunto,
          descricao: servicosPayload.descricao,
          prioridade: servicosPayload.prioridade,
          prazo: servicosPayload.prazo,
          dataAbertura: servicosPayload.dataAbertura,
          status: 'autorizada',
          criadoPor: servicosPayload.criadoPor,
          autorizadoPor: servicosPayload.criadoPor,
          dataAutorizacao: new Date().toISOString(),
          avaliacaoAutorizador: null,
          avaliacaoSolicitante: null,
          executor: servicosPayload.executor,
          osPai: null,
          osFilhos: [],
          requisitos: servicosPayload.requisitos || [],
          materiaisPrevistos: servicosPayload.materiaisPrevistos || [],
          servico_catalogo_id: servicosPayload.servico_catalogo_id || '',
          custoPlanejado: 0,
          custoReal: 0,
          origem: 'manutencao',
          modulo_origem: 'manutencao',
          ativo_id: servicosPayload.ativo_id,
          plano_id: servicosPayload.plano_id,
          servico_id: servicosPayload.servico_id,
        });
        window.saveOS(osData);
      }
    }
    if (typeof window.renderKpiServicos === 'function') window.renderKpiServicos();
    if (typeof window.renderOS === 'function') window.renderOS();
    if (typeof window.renderKanban === 'function') window.renderKanban();
    if (typeof window.criarSRMateriaisDaOS === 'function' && Array.isArray(svc?.materiais) && svc.materiais.length) {
      window.criarSRMateriaisDaOS(osId, svc.materiais, { origem: 'plano_manutencao', solicitante: 'Sistema' });
    }

    toast(`OS preventiva ${osId} criada (Manutenção + Serviços)`, 'green');
    state.tabDirty.os = true;
    state.tabDirty.planos = true;
    if (state.activeTab === 'os' || state.activeTab === 'planos') {
      const cont = document.getElementById('manut-tab-content');
      if (cont) RENDERERS[state.activeTab](cont);
    }
  }

  function migrarDadosLegados() {
    const LS_FLAG = 'xcmasm_manut_migrado_v1';
    if (localStorage.getItem(LS_FLAG)) return;

    const corteRaw = localStorage.getItem('cmasm_v2_state');
    const refrigRaw = localStorage.getItem('refrigeracao_state');
    if (!corteRaw && !refrigRaw) { localStorage.setItem(LS_FLAG, '1'); return; }

    if (typeof window.getAtivos !== 'function' || typeof window.saveAtivos !== 'function') return;
    if (typeof window.getOSManut !== 'function' || typeof window.saveOSManut !== 'function') return;

    let ativos = window.getAtivos();
    let osManut = window.getOSManut();
    let changed = false;

    function mergeAtivo(novo) {
      const idx = ativos.findIndex(a => a.id === novo.id);
      if (idx < 0) { ativos.push(novo); changed = true; }
      else if ((novo.horimetro || 0) > (ativos[idx].horimetro || 0)) {
        ativos[idx].horimetro = novo.horimetro; changed = true;
      }
    }
    function mergeOS(novo) {
      if (!osManut.find(o => o.id === novo.id)) { osManut.push(novo); changed = true; }
    }

    if (corteRaw) {
      try {
        const st = JSON.parse(corteRaw);
        for (const u of (st.units || st.equips || [])) {
          mergeAtivo({
            id: `leg-corte-${u.id}`, cod: String(u.id).toUpperCase(),
            nome: u.nome || u.id, categoria: 'maquinas_corte', tipo: u.tipo || '',
            horimetro: u.horimetro || 0, status: u.ativo !== false ? 'P' : 'INOP', obs: u.obs || '',
          });
        }
        for (const m of (st.manutList || [])) {
          mergeOS({
            id: `LEG-CRT-${m.id || m.ts || Math.random().toString(36).slice(2)}`,
            ativoId: `leg-corte-${m.uid}`, ativoNome: m.uid || '—', tipo: 'preventiva',
            descricao: m.desc || m.n || 'Manutenção legada (corte vegetal)',
            responsavel: m.resp || m.op || '', abertura: m.data || '',
            status: 'concluida', dataConclusao: m.data || '', origem: 'legado_corte',
          });
        }
      } catch (e) { console.warn('[manut] Migração corte falhou:', e); }
    }

    if (refrigRaw) {
      try {
        const st = JSON.parse(refrigRaw);
        for (const u of (st.units || st.equips || [])) {
          mergeAtivo({
            id: `leg-refrig-${u.id}`, cod: String(u.id).toUpperCase(),
            nome: u.nome || u.id, categoria: 'climatizacao', tipo: u.tipo || 'AC_SPLIT',
            horimetro: u.horimetro || 0, status: u.ativo !== false ? 'P' : 'INOP',
            local: u.local || '', marca: u.marca || '', obs: u.obs || '',
          });
        }
        for (const m of (st.manutList || [])) {
          mergeOS({
            id: `LEG-REF-${m.id || m.ts || Math.random().toString(36).slice(2)}`,
            ativoId: `leg-refrig-${m.uid}`, ativoNome: m.uid || '—', tipo: 'preventiva',
            descricao: m.desc || m.n || 'Manutenção legada (refrigeração)',
            responsavel: m.resp || m.op || '', abertura: m.data || '',
            status: 'concluida', dataConclusao: m.data || '', origem: 'legado_refrigeracao',
          });
        }
      } catch (e) { console.warn('[manut] Migração refrigeração falhou:', e); }
    }

    // Migrar historico de horímetro / manutenções do cmasm_v2_state para xcmasm_manut_hist
    if (corteRaw) {
      try {
        const st = JSON.parse(corteRaw);
        const mhAll = getMH();
        let mhChanged = false;
        for (const u of (st.unidades || st.units || [])) {
          const hSrc = st.hist?.[u.id];
          if (!hSrc) continue;
          const targetId = u.id; // IDs iguais: u01, u02...
          if (!mhAll[targetId] || mhAll[targetId].hor < hSrc.hor) {
            mhAll[targetId] = {
              hor: hSrc.hor || 0,
              regs: (hSrc.regs || []).map(r => ({ ...r })),
              manut: (hSrc.manut || []).map(m => ({ ...m })),
              ulm: { ...(hSrc.ulm || {}) },
            };
            mhChanged = true;
          }
        }
        if (mhChanged) { saveMH(mhAll); }
      } catch (e) { console.warn('[manut] Migração hist corte falhou:', e); }
    }

    if (changed) {
      window.saveAtivos(ativos);
      window.saveOSManut(osManut);
      const nAtivos = ativos.filter(a => a.id.startsWith('leg-')).length;
      const nOS = osManut.filter(o => o.origem?.startsWith('legado')).length;
      toast(`Dados legados importados: ${nAtivos} ativos + ${nOS} OS históricas`, 'green');
    }
    localStorage.setItem(LS_FLAG, '1');

    // ── Migração adicional: cmasm_manut_v3 (app React TS114) ─────────────────
    const LS_FLAG_TS3 = 'xcmasm_manut_migrado_ts114v3';
    if (!localStorage.getItem(LS_FLAG_TS3)) {
      const ts3Raw = localStorage.getItem('cmasm_manut_v3');
      if (ts3Raw) {
        try {
          const ts3 = JSON.parse(ts3Raw);
          // IDs React: M1→u24, M2→u25, M3→u26, M4→u27
          const idMap = { M1: 'u24', M2: 'u25', M3: 'u26', M4: 'u27' };
          // Plan IDs: m01-m14 → p01-p14 (direto após atualização TS114 plano 14 itens)
          const pidMap = id => id.replace(/^m(\d+)$/, (_, n) => 'p' + String(parseInt(n, 10)).padStart(2, '0'));
          const mhAll = getMH();
          let mhTs3Changed = false;
          for (const maq of (ts3.maquinas || [])) {
            const targetId = idMap[maq.id];
            if (!targetId) continue;
            const existing = mhAll[targetId] || { hor: 0, regs: [], manut: [], ulm: {} };
            if ((maq.horasTotais || 0) > (existing.hor || 0)) {
              mhAll[targetId] = {
                hor: maq.horasTotais || 0,
                regs: (maq.registros || []).map(r => ({
                  id: r.id || ('r' + Date.now()), dt: r.dt || new Date().toISOString(),
                  h: r.h || 0, c: r.comb || 0, op: r.usr || '', obs: r.obs || '', data: r.data || '',
                })),
                manut: (maq.manutencoes || []).map(m => ({
                  id: m.id || ('m' + Date.now()), data: m.data || '',
                  h: m.h || 0, resp: m.tec || '', itens: m.itens || [], obs: m.obs || '',
                })),
                ulm: Object.fromEntries(
                  Object.entries(maq.ultimasManut || {}).map(([k, v]) => [pidMap(k), v])
                ),
              };
              mhTs3Changed = true;
            }
          }
          if (mhTs3Changed) {
            saveMH(mhAll);
            toast('TS114 v3: histórico de horímetros importado', 'green');
          }
        } catch (e) { console.warn('[manut] Migração TS114 v3 falhou:', e); }
      }
      localStorage.setItem(LS_FLAG_TS3, '1');
    }
  }

  // ── data fetch ──────────────────────────────────────────────────────────
  async function fetchAll() {
    if (state._fetching) return state._fetching;  // dedup chamadas concorrentes
    const banner = document.getElementById('manut-banner');
    if (banner) banner.remove();
    const work = (async () => {
      try {
        // planos_manutencao APOSENTADO — planos vêm de catalogo_planos (sub-aba Planos/Vencimentos).
        const [ativos, os, estoque, servicosBase] = await Promise.all([
          fetch(apiUrl('/api/ativos')).then(r => { if (!r.ok) throw new Error('ativos ' + r.status); return r.json(); }),
          fetch(apiUrl('/api/os')).then(r => { if (!r.ok) throw new Error('os ' + r.status); return r.json(); }),
          fetch(apiUrl('/api/estoque')).then(r => { if (!r.ok) throw new Error('estoque ' + r.status); return r.json(); }),
          fetch(apiUrl('/api/catalogo/servicos')).then(r => { if (!r.ok) throw new Error('catalogo/servicos ' + r.status); return r.json(); }),
        ]);
        const servicos = await Promise.all((servicosBase || []).map(servico =>
          fetch(apiUrl(`/api/catalogo/servicos/${encodeURIComponent(servico.id)}`))
            .then(r => (r.ok ? r.json() : servico))
            .catch(() => servico)
        ));
        state.cache.ativos   = { data: ativos,   ts: Date.now() };
        state.cache.os       = { data: os,       ts: Date.now() };
        state.cache.estoque  = { data: estoque,  ts: Date.now() };
        state.cache.catalogo_servicos = { data: servicos, ts: Date.now() };
        state.cache.planos_manutencao = { data: [], ts: Date.now() };  // aposentado
        state.catsAvailable = [...new Set(ativos.map(a => a.categoria).filter(Boolean))].sort();
        if (state._renderChips) state._renderChips();
      } catch (e) {
        console.warn('[manut] fetchAll API falhou, tentando localStorage:', e);
        // Fallback: usa dados do localStorage (getAtivos/getOSManut/getEstoque do ERP)
        const lsAtivos   = (window.getAtivos?.()  || []).map(a => ({
          id: a.id, nome: a.nome, codigo: a.cod, tipo: a.categoria, categoria: a.categoria,
          fabricante: a.fabricante, modelo: a.modelo, serie: a.serie, ano: a.ano,
          ativo: a.status !== 'INOP' ? 1 : 0, uso_atual: a.horimetro || 0, unidade_uso: 'h',
          criticidade: 'operacional', responsavel_pmoc: a.local || '—', status: a.status,
          observacoes: a.obs,
        })).map(a => ({ ...a, tipo: resolveTipoCodigo(a) || a.tipo }));
        const lsOS = (window.getOSManut?.() || []).map(o => ({
          id: o.id, codigo: o.id, titulo: o.descricao?.substring(0, 60) || o.id,
          tipo: o.tipo, status: o.status, prioridade: 'normal', ativo_id: o.ativoId,
          data_abertura: o.abertura, data_conclusao: o.dataConclusao,
          responsavel: o.responsavel,
        }));
        const lsEstoque = (window.getEstoque?.() || []).map(i => ({
          id: i.id, nome: i.nome, unidade: i.unidade, qtd_atual: i.qtd, qtd_minima: i.qtdMin,
        }));
        if (lsAtivos.length > 0) {
          state.cache.ativos  = { data: lsAtivos,  ts: Date.now(), fromLS: true };
          state.cache.os      = { data: lsOS,      ts: Date.now(), fromLS: true };
          state.cache.estoque = { data: lsEstoque, ts: Date.now(), fromLS: true };
          state.cache.catalogo_servicos = { data: window.ERP_MANUT_MOCKS?.catalogo_servicos || [], ts: Date.now(), fromLS: true };
          state.cache.planos_manutencao = { data: window.ERP_MANUT_MOCKS?.planos_manutencao || [], ts: Date.now(), fromLS: true };
          state.catsAvailable = [...new Set(lsAtivos.map(a => a.categoria).filter(Boolean))].sort();
          if (state._renderChips) state._renderChips();
        }
        const hasCache = lsAtivos.length > 0 || !!state.cache.ativos;
        state._fetchError = { msg: e.message, hasCache };
        // Se root já tem conteúdo (cenário de refresh), mostrar banner imediatamente
        const r = document.getElementById('manut-root');
        if (r?.firstChild) { showErrorBanner(e.message, hasCache); state._fetchError = null; }
      }
    })();
    state._fetching = work;
    try { return await work; }
    finally { state._fetching = null; }
  }

  function normalizeFetchErrorMessage(msg) {
    const raw = String(msg || '').trim();
    if (!raw) return 'falha de conexão';
    if (/failed to fetch/i.test(raw)) return 'falha de conexão';
    return raw;
  }

  function showErrorBanner(msg, hasCache) {
    const { el } = window.engine.utils;
    const root = document.getElementById('manut-root');
    if (!root) return;
    const isLight = document.documentElement.getAttribute('data-theme') === 'light';
    const tone = hasCache
      ? {
          bg: isLight ? 'rgba(245,158,11,.20)' : 'rgba(245,158,11,.15)',
          border: 'var(--amber)',
          text: isLight ? '#92400e' : 'var(--amber)',
        }
      : {
          bg: isLight ? 'rgba(239,68,68,.16)' : 'rgba(239,68,68,.15)',
          border: 'var(--red)',
          text: isLight ? '#991b1b' : 'var(--red)',
        };
    const safeMsg = normalizeFetchErrorMessage(msg);
    const banner = el('div', {
      id: 'manut-banner',
      style: {
        background: tone.bg,
        border: '1px solid ' + tone.border,
        color: tone.text,
        padding: '8px 12px', borderRadius: '6px',
        margin: '0 0 12px', display: 'flex', gap: '12px', alignItems: 'center',
      },
    },
      el('span', {}, hasCache ? `⚠ Dados desatualizados (${safeMsg}).` : `⛔ Sem conexão com o núcleo (${safeMsg}).`),
      el('div', { style: { flex: 1 } }),
      el('button', { class: 'pe-btn', onclick: () => fetchAll() }, 'Tentar novamente'),
    );
    root.insertBefore(banner, root.firstChild);
  }

  function isManutActive() {
    const p = document.getElementById('page-manutencao');
    return !!(p && p.classList.contains('active'));
  }

  function _showPendingBanner() {
    if (!state._fetchError) return;
    const { msg, hasCache } = state._fetchError;
    state._fetchError = null;
    showErrorBanner(msg, hasCache);
  }

  window.manutRefresh = function () {
    if (!initialized) return;
    fetchAll().finally(() => { markAllDirty(); renderActiveTab(); _showPendingBanner(); });
  };

  // Abre uma tab específica por código (ex.: link Ativos → Refrigeração).
  // Se ainda não inicializou, o boot renderiza esta activeTab quando a página abrir.
  window.manutOpenTab = function (id) {
    state.activeTab = id;
    const root = document.getElementById('manut-root');
    if (initialized && root) render(root);
  };

  // 1) Se a página já está visível na carga (caso DOMContentLoaded em deeplink),
  //    boot imediato. 2) Caso contrário, observa mudanças de classe na page.
  function setup() {
    if (isManutActive()) { boot(); return; }
    const p = document.getElementById('page-manutencao');
    if (!p) return;
    const obs = new MutationObserver(() => {
      if (isManutActive()) { boot(); obs.disconnect(); }
    });
    obs.observe(p, { attributes: true, attributeFilter: ['class'] });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', setup);
  } else {
    setup();
  }
})();
