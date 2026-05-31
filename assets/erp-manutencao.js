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
    cache: { ativos: null, os: null, estoque: null },
    activeTab: 'dashboard',
    tabDirty: { dashboard: true, ativos: true, os: true, planos: true,
                catalogo: true, estoque: true, calgantt: true, config: true },
  };

  const TAB_DEFS = [
    { id: 'dashboard', icon: '📊', label: 'Dashboard' },
    { id: 'ativos',    icon: '📦', label: 'Ativos' },
    { id: 'os',        icon: '🧰', label: 'OS' },
    { id: 'planos',    icon: '⚙️', label: 'Planos' },
    { id: 'catalogo',  icon: '📖', label: 'Catálogo' },
    { id: 'estoque',   icon: '🗄️', label: 'Estoque' },
    { id: 'calgantt',  icon: '📅', label: 'Cal+Gantt' },
    { id: 'config',    icon: '📄', label: 'Configuração' },
  ];

  // ── persistência ─────────────────────────────────────────────────────────
  const LS_KEY = 'xerp_manut_cats';

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

  function boot() {
    if (initialized) return;
    initialized = true;
    const root = document.getElementById('manut-root');
    if (!root) {
      console.warn('[manut] #manut-root não encontrado');
      return;
    }
    if (!window.engine) {
      console.warn('[manut] pmoc-engine.js não carregado');
      root.innerHTML = '<div style="padding:24px;color:#ef4444">Erro: pmoc-engine não carregado.</div>';
      return;
    }
    fetchAll().finally(() => { render(root); });
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
    const chipBox = el('div', { id: 'manut-chips', style: {
      display: 'flex', flexWrap: 'wrap', gap: '6px', alignItems: 'center',
    } });

    function renderChips() {
      chipBox.replaceChildren(
        ...state.catsAvailable.map(cat => {
          const on = state.cats.has(cat);
          return el('button', {
            class: 'pe-btn ' + (on ? 'pe-btn--primary' : 'pe-btn--ghost'),
            style: { minHeight: '28px', padding: '4px 10px', fontSize: '12px' },
            onclick: () => {
              if (on) state.cats.delete(cat); else state.cats.add(cat);
              saveFilter(); markAllDirty(); renderChips(); renderActiveTab();
            },
          }, cat);
        }),
        el('button', {
          class: 'pe-btn pe-btn--ghost',
          style: { minHeight: '28px', padding: '4px 10px', fontSize: '12px' },
          onclick: () => { state.cats.clear(); saveFilter(); markAllDirty(); renderChips(); renderActiveTab(); },
        }, 'Tudo'),
        el('button', {
          class: 'pe-btn pe-btn--ghost', title: 'Recarregar do núcleo',
          style: { minHeight: '28px', padding: '4px 10px', fontSize: '12px' },
          onclick: () => fetchAll().then(() => { markAllDirty(); renderActiveTab(); }),
        }, '↻'),
      );
    }
    state._renderChips = renderChips;
    renderChips();

    return el('div', { style: {
      position: 'sticky', top: '0', zIndex: '5',
      background: 'var(--bg)', padding: '12px 0', marginBottom: '12px',
      borderBottom: '1px solid var(--line)',
    } },
      el('div', { style: { display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' } },
        el('h2', { style: { margin: 0, fontSize: '18px' } }, 'Manutenção'),
        el('div', { style: { flex: 1 } }),
        el('button', { class: 'pe-btn', onclick: () => alert('Em breve: criar plano') }, '+ Plano'),
        el('button', { class: 'pe-btn pe-btn--primary', onclick: () => alert('Em breve: nova OS') }, '+ OS'),
      ),
      el('div', { style: { display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' } },
        el('span', { style: { fontSize: '12px', color: 'var(--ink-3)' } }, 'Categorias:'),
        chipBox,
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

  // ── helpers de derivação (filtrados pelo state.cats) ─────────────────────
  function filteredAtivos() {
    const all = state.cache.ativos?.data || [];
    if (state.cats.size === 0) return all;
    return all.filter(a => state.cats.has(a.categoria));
  }
  /** OS filtradas por categoria. OS sem ativo_id (manuais, sem vínculo)
   *  passam por todos os filtros — são consideradas globais. */
  function filteredOS() {
    const all = state.cache.os?.data || [];
    if (state.cats.size === 0) return all;
    const ativosIds = new Set(filteredAtivos().map(a => a.id));
    return all.filter(o => !o.ativo_id || ativosIds.has(o.ativo_id));
  }
  function estoqueBaixo() {
    const all = state.cache.estoque?.data || [];
    return all.filter(i => (i.qtd_atual ?? 0) < (i.qtd_minima ?? 0));
  }

  // ── renderers de cada tab ────────────────────────────────────────────────
  const RENDERERS = {
    dashboard(cont) {
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

      cont.replaceChildren(kpiGrid, charts, alertas);
    },

    ativos(cont) {
      const { el, fmt } = window.engine.utils;
      const rows = filteredAtivos();
      const wrap = el('div');
      cont.replaceChildren(wrap);
      window.engine.table(wrap, {
        cols: [
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
      );
      const body = el('div');
      cont.replaceChildren(toggleWrap, body);

      if (view === 'kanban') renderOsKanban(body);
      else renderOsLista(body);
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
          state.tabDirty.os = true; RENDERERS.os(document.getElementById('manut-tab-content'));
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
          state.tabDirty.os = true; RENDERERS.os(document.getElementById('manut-tab-content'));
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

  function openOsDrawer(os) {
    const { el } = window.engine.utils;
    const m = window.engine.modal({
      title: `${os.codigo || os.id} · ${os.titulo || ''}`,
      body: el('div', {},
        ...Object.entries(os).map(([k, v]) =>
          el('div', { style: { display: 'flex', gap: '8px', padding: '4px 0', borderBottom: '1px solid var(--line)' } },
            el('div', { style: { color: 'var(--ink-3)', minWidth: '140px' } }, k),
            el('div', {}, v == null ? '—' : String(v)),
          )),
      ),
      footer: [el('button', { class: 'pe-btn pe-btn--primary', onclick: () => m.close() }, 'Fechar')],
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

  function openAtivoDrawer(ativo) {
    const { el, fmt } = window.engine.utils;
    const planos = (window.ERP_MANUT_MOCKS?.planos_manutencao || [])
      .filter(p => p.ativo_id === ativo.id || (p.tipo_codigo && p.tipo_codigo === ativo.tipo));
    const osDoAtivo = (state.cache.os?.data || []).filter(o => o.ativo_id === ativo.id);

    function dadosView() {
      return el('div', {},
        ...Object.entries(ativo).map(([k, v]) =>
          el('div', { style: { display: 'flex', gap: '8px', padding: '6px 0', borderBottom: '1px solid var(--line)' } },
            el('div', { style: { color: 'var(--ink-3)', minWidth: '160px' } }, k),
            el('div', {}, v == null ? '—' : String(v)),
          )),
      );
    }
    function planosView() {
      if (!planos.length) return el('div', { style: { color: 'var(--ink-3)' } }, 'Sem planos vinculados.');
      return el('ul', {}, ...planos.map(p =>
        el('li', {}, `${p.servico_id} · ${JSON.stringify(p.frequencia)} · próx ${p.proxima_execucao}`)));
    }
    function osView() {
      if (!osDoAtivo.length) return el('div', { style: { color: 'var(--ink-3)' } }, 'Sem OS para este ativo.');
      return el('ul', {}, ...osDoAtivo.map(o =>
        el('li', {}, `[${o.status}] ${o.codigo || o.id} · ${o.titulo}`)));
    }

    let activeSub = 'dados';
    const subBody = el('div', { style: { marginTop: '10px' } });
    function renderSub() {
      subBody.replaceChildren(({ dados: dadosView, planos: planosView, os: osView }[activeSub])());
    }
    function tabBtn(id, label) {
      return el('button', {
        class: 'pe-btn ' + (activeSub === id ? 'pe-btn--primary' : 'pe-btn--ghost'),
        style: { marginRight: '4px' },
        onclick: () => { activeSub = id; renderSub(); refreshSubTabs(); },
      }, label);
    }
    const subTabs = el('div', {}, tabBtn('dados', 'Dados'), tabBtn('planos', 'Planos'), tabBtn('os', 'OS'));
    function refreshSubTabs() {
      subTabs.replaceChildren(tabBtn('dados', 'Dados'), tabBtn('planos', 'Planos'), tabBtn('os', 'OS'));
    }

    const m = window.engine.modal({
      title: ativo.nome,
      body: el('div', {}, subTabs, subBody),
      footer: [el('button', { class: 'pe-btn pe-btn--primary', onclick: () => m.close() }, 'Fechar')],
    });
    m.open();
    renderSub();
  }

  // ── data fetch ──────────────────────────────────────────────────────────
  async function fetchAll() {
    if (state._fetching) return state._fetching;  // dedup chamadas concorrentes
    const banner = document.getElementById('manut-banner');
    if (banner) banner.remove();
    const work = (async () => {
      try {
        const [ativos, os, estoque] = await Promise.all([
          fetch('/api/ativos').then(r => { if (!r.ok) throw new Error('ativos ' + r.status); return r.json(); }),
          fetch('/api/os').then(r => { if (!r.ok) throw new Error('os ' + r.status); return r.json(); }),
          fetch('/api/estoque').then(r => { if (!r.ok) throw new Error('estoque ' + r.status); return r.json(); }),
        ]);
        state.cache.ativos   = { data: ativos,   ts: Date.now() };
        state.cache.os       = { data: os,       ts: Date.now() };
        state.cache.estoque  = { data: estoque,  ts: Date.now() };
        state.catsAvailable = [...new Set(ativos.map(a => a.categoria).filter(Boolean))].sort();
        if (state._renderChips) state._renderChips();
      } catch (e) {
        console.warn('[manut] fetchAll falhou:', e);
        showErrorBanner(e.message, !!state.cache.ativos);
      }
    })();
    state._fetching = work;
    try { return await work; }
    finally { state._fetching = null; }
  }

  function showErrorBanner(msg, hasCache) {
    const { el } = window.engine.utils;
    const root = document.getElementById('manut-root');
    if (!root) return;
    const banner = el('div', {
      id: 'manut-banner',
      style: {
        background: hasCache ? 'rgba(245,158,11,.15)' : 'rgba(239,68,68,.15)',
        border: '1px solid ' + (hasCache ? 'var(--amber)' : 'var(--red)'),
        color: hasCache ? 'var(--amber)' : 'var(--red)',
        padding: '8px 12px', borderRadius: '6px',
        margin: '0 0 12px', display: 'flex', gap: '12px', alignItems: 'center',
      },
    },
      el('span', {}, hasCache ? `⚠ Dados desatualizados (${msg}).` : `⛔ Sem conexão com o núcleo (${msg}).`),
      el('div', { style: { flex: 1 } }),
      el('button', { class: 'pe-btn', onclick: () => fetchAll() }, 'Tentar novamente'),
    );
    root.insertBefore(banner, root.firstChild);
  }

  function isManutActive() {
    const p = document.getElementById('page-manutencao');
    return !!(p && p.classList.contains('active'));
  }

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
