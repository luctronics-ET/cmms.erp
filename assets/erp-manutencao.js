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
    cache: { ativos: null, os: null, estoque: null, planos: null, catalogo: null },
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

  // ── helpers de manutenção preventiva (semáforo) ─────────────────────────

  /** Converte duração ISO 8601 (P1M, P3M, P1Y, P14D) em dias aproximados. */
  function parseDurationDays(val) {
    if (!val || typeof val !== 'string') return 30;
    const m = val.match(/^P(?:(\d+)Y)?(?:(\d+)M)?(?:(\d+)D)?/);
    if (!m) return 30;
    return (parseInt(m[1] || 0) * 365) + (parseInt(m[2] || 0) * 30) + (parseInt(m[3] || 0));
  }

  /** Retorna { color: 'green'|'amber'|'red', label, daysUntil } para um plano. */
  function planStatus(plan) {
    if (!plan.proxima_execucao) return { color: 'green', label: '—', daysUntil: Infinity };
    const today = new Date(); today.setHours(0, 0, 0, 0);
    const next  = new Date(plan.proxima_execucao); next.setHours(0, 0, 0, 0);
    const daysUntil = Math.round((next - today) / 86400000);
    const freq = plan.frequencia || {};
    let intervalDays = 30;
    if (freq.tipo === 'periodica') {
      const raw = typeof freq.valor === 'string' ? freq.valor
        : typeof freq.valor === 'object' ? (freq.valor.operacional || freq.valor.critico_24x7 || 'P3M')
        : 'P3M';
      intervalDays = parseDurationDays(raw);
    } else if (freq.tipo === 'por_uso') {
      intervalDays = 90;  // fallback para planos por uso (sem limiar de data)
    }
    if (daysUntil < 0)                   return { color: 'red',   label: `${Math.abs(daysUntil)}d vencida`, daysUntil };
    if (daysUntil <= intervalDays * 0.2) return { color: 'amber', label: `${daysUntil}d`,                  daysUntil };
    return { color: 'green', label: `${daysUntil}d`, daysUntil };
  }

  function _allPlanos() {
    const cached = state.cache.planos?.data;
    return (cached && cached.length) ? cached : (window.ERP_MANUT_MOCKS?.planos_manutencao || []);
  }
  function _allCatalogo() {
    const cached = state.cache.catalogo?.data;
    return (cached && cached.length) ? cached : (window.ERP_MANUT_MOCKS?.catalogo_servicos || []);
  }

  /** Todos os planos activos para um ativo (por ativo_id ou por tipo). */
  function planosDoAtivo(ativo) {
    return _allPlanos().filter(p =>
      (p.ativo !== 0) &&
      (p.ativo_id === ativo.id || (p.tipo_codigo && p.tipo_codigo === ativo.tipo)));
  }

  /** Pior status semáforo entre os planos do ativo (para badge na tabela). */
  function ativoWorstStatus(ativo) {
    const mine = planosDoAtivo(ativo);
    if (!mine.length) return null;
    const ss = mine.map(planStatus);
    if (ss.some(s => s.color === 'red'))   return { color: 'red',   label: `${ss.filter(s => s.color === 'red').length} vencida(s)` };
    if (ss.some(s => s.color === 'amber')) return { color: 'amber', label: `${ss.filter(s => s.color === 'amber').length} próx.` };
    return { color: 'green', label: 'Em dia' };
  }

  function servicoNome(id) {
    return (_allCatalogo().find(s => s.id === id) || {}).nome || id;
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
      const rows = filteredAtivos().map(a => ({ ...a, _status: ativoWorstStatus(a) }));
      const wrap = el('div');
      cont.replaceChildren(wrap);
      window.engine.table(wrap, {
        cols: [
          { key: '_status', label: '⬤', format: s => {
            if (!s) return window.engine.badge('—', 'default');
            return window.engine.badge(s.label, s.color === 'red' ? 'red' : s.color === 'amber' ? 'amber' : 'green');
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

  // ── novos renderers: Planos, Catálogo, Estoque ──────────────────────────

  Object.assign(RENDERERS, {
    planos(cont) {
      const { el, fmt } = window.engine.utils;
      const allPlanos = _allPlanos();
      const visibles = state.cats.size === 0 ? allPlanos : allPlanos.filter(p => {
        if (p.ativo_id) {
          const at = (state.cache.ativos?.data || []).find(a => a.id === p.ativo_id);
          return at && state.cats.has(at.categoria);
        }
        return (state.cache.ativos?.data || []).some(a =>
          state.cats.has(a.categoria) && a.tipo === p.tipo_codigo);
      });
      const rows = visibles.map(p => ({
        ...p,
        _status:       planStatus(p),
        _servico_nome: servicoNome(p.servico_id),
      }));
      const wrap = el('div');
      cont.replaceChildren(wrap);
      window.engine.table(wrap, {
        cols: [
          { key: '_status', label: '⬤', format: s =>
            window.engine.badge(s.label, s.color === 'red' ? 'red' : s.color === 'amber' ? 'amber' : 'green') },
          { key: '_servico_nome',    label: 'Serviço' },
          { key: 'tipo_codigo',      label: 'Tipo',    format: v => v || '—' },
          { key: 'proxima_execucao', label: 'Próxima', format: v => v ? fmt.date(v) : '—' },
          { key: 'ultima_execucao',  label: 'Última',  format: v => v ? fmt.date(v) : '—' },
          { key: 'responsavel_pmoc', label: 'PMOC', filter: true },
        ],
        rows,
        onRowClick: p => {
          const at = p.ativo_id
            ? (state.cache.ativos?.data || []).find(a => a.id === p.ativo_id)
            : null;
          if (at) openAtivoDrawer(at);
        },
      });
    },

    catalogo(cont) {
      const { el } = window.engine.utils;
      const wrap = el('div');
      cont.replaceChildren(wrap);
      window.engine.table(wrap, {
        cols: [
          { key: 'codigo',             label: 'Código' },
          { key: 'nome',               label: 'Serviço' },
          { key: 'escopo',             label: 'Escopo', filter: true,
            format: v => window.engine.badge(v, v === 'central' ? 'blue' : 'amber') },
          { key: 'versao',             label: 'v.' },
          { key: 'tempo_estimado_min', label: 'Tempo (min)', format: v => v || '—' },
          { key: 'ativo',              label: 'Status',
            format: v => window.engine.badge(v ? 'ativo' : 'arquivado', v ? 'green' : 'default') },
        ],
        rows: _allCatalogo(),
        onRowClick: svc => {
          const { el } = window.engine.utils;
          const aplic = typeof svc.aplicavel_a === 'object' ? (svc.aplicavel_a || {}) : {};
          const cats  = (aplic.categorias || []).join(', ') || '—';
          const body  = el('div', {},
            ...[
              ['Código', svc.codigo], ['Escopo', svc.escopo], ['Versão', svc.versao],
              ['Tempo (min)', svc.tempo_estimado_min || '—'], ['Categorias', cats],
              ['Descrição', svc.descricao || '—'],
            ].map(([k, v]) => el('div', {
              style: { display: 'flex', gap: '8px', padding: '4px 0', borderBottom: '1px solid var(--line)' },
            },
              el('div', { style: { color: 'var(--ink-3)', minWidth: '140px' } }, k),
              el('div', {}, String(v)))),
          );
          const m = window.engine.modal({
            title: svc.nome,
            body,
            footer: [el('button', { class: 'pe-btn pe-btn--primary', onclick: () => m.close() }, 'Fechar')],
          });
          m.open();
        },
      });
    },

    estoque(cont) {
      const { el, fmt } = window.engine.utils;
      const itens = (state.cache.estoque?.data || []).map(i => ({
        ...i, _abaixo: (i.qtd_atual ?? 0) < (i.qtd_minima ?? 0),
      }));
      const wrap = el('div');
      cont.replaceChildren(wrap);
      window.engine.table(wrap, {
        cols: [
          { key: 'codigo',    label: 'Código' },
          { key: 'nome',      label: 'Item' },
          { key: 'unidade',   label: 'Un' },
          { key: 'qtd_atual', label: 'Saldo', format: v => fmt.num(v, 2) },
          { key: 'qtd_minima',label: 'Mín',   format: v => fmt.num(v, 2) },
          { key: '_abaixo',   label: 'Status',
            format: v => window.engine.badge(v ? 'Baixo' : 'OK', v ? 'red' : 'green') },
        ],
        rows: itens,
      });
    },
  });

  // ── Cal+Gantt e Config ───────────────────────────────────────────────────

  Object.assign(RENDERERS, {

    calgantt(cont) {
      const { el, fmt } = window.engine.utils;
      const view = state._calView || (state._calView = 'calendar');

      const toggleWrap = el('div', { style: { marginBottom: '10px', display: 'flex', gap: '4px', alignItems: 'center' } },
        el('button', {
          class: 'pe-btn ' + (view === 'calendar' ? 'pe-btn--primary' : 'pe-btn--ghost'),
          onclick: () => { state._calView = 'calendar'; RENDERERS.calgantt(cont); },
        }, '📅 Calendário'),
        el('button', {
          class: 'pe-btn ' + (view === 'gantt' ? 'pe-btn--primary' : 'pe-btn--ghost'),
          onclick: () => { state._calView = 'gantt'; RENDERERS.calgantt(cont); },
        }, '📊 Gantt'),
        el('div', { style: { flex: 1 } }),
        el('span', { style: { fontSize: '12px', color: 'var(--ink-3)' } }, '60 dias'),
      );

      const body = el('div');
      cont.replaceChildren(toggleWrap, body);

      // Filtra planos com proxima_execucao nos próximos 60 dias (+ vencidos)
      const allPlanos = _allPlanos();
      const today = new Date(); today.setHours(0, 0, 0, 0);
      const horizon = new Date(today.getTime() + 60 * 86400000);

      const visibles = (state.cats.size === 0 ? allPlanos : allPlanos.filter(p => {
        if (p.ativo_id) {
          const at = (state.cache.ativos?.data || []).find(a => a.id === p.ativo_id);
          return at && state.cats.has(at.categoria);
        }
        return (state.cache.ativos?.data || []).some(a =>
          state.cats.has(a.categoria) && a.tipo === p.tipo_codigo);
      })).filter(p => {
        if (!p.proxima_execucao) return false;
        const d = new Date(p.proxima_execucao);
        return d <= horizon;   // inclui vencidos (d < today também)
      });

      if (!visibles.length) {
        body.replaceChildren(el('div', { style: { padding: '24px', color: 'var(--ink-3)' } },
          'Nenhuma manutenção agendada nos próximos 60 dias.'));
        return;
      }

      if (view === 'calendar') {
        const events = visibles.map(p => {
          const st = planStatus(p);
          const svNome = servicoNome(p.servico_id);
          const ativoNome = p.ativo_id
            ? ((state.cache.ativos?.data || []).find(a => a.id === p.ativo_id)?.nome || p.ativo_id)
            : (p.tipo_codigo || '—');
          return {
            id: p.id,
            date: p.proxima_execucao,
            title: `${svNome} · ${ativoNome}`,
            color: st.color === 'red' ? 'var(--red)' : st.color === 'amber' ? 'var(--amber)' : 'var(--green)',
            _plano: p,
          };
        });
        window.engine.calendar(body, {
          events,
          onEventClick: ev => {
            const at = ev._plano?.ativo_id
              ? (state.cache.ativos?.data || []).find(a => a.id === ev._plano.ativo_id)
              : null;
            if (at) openAtivoDrawer(at);
          },
        });

      } else {
        // Gantt: range hoje até hoje+60d; cada plano é uma tarefa de 1 dia (proxima_execucao)
        const startIso = fmt.iso ? fmt.iso(today) : today.toISOString().slice(0, 10);
        const endIso   = fmt.iso ? fmt.iso(horizon) : horizon.toISOString().slice(0, 10);

        const tasks = visibles.map(p => {
          const st = planStatus(p);
          const svNome = servicoNome(p.servico_id);
          const ativoNome = p.ativo_id
            ? ((state.cache.ativos?.data || []).find(a => a.id === p.ativo_id)?.nome || p.ativo_id)
            : (p.tipo_codigo || '—');
          // Duração estimada: 1 dia para periodica, duração do serviço se disponível
          const svc = _allCatalogo().find(s => s.id === p.servico_id);
          const durDays = svc?.tempo_estimado_min ? Math.max(1, Math.ceil(svc.tempo_estimado_min / 480)) : 1;
          const taskStart = new Date(p.proxima_execucao); taskStart.setHours(0, 0, 0, 0);
          const taskEnd   = new Date(taskStart.getTime() + durDays * 86400000);
          return {
            id: p.id,
            label: `${svNome} · ${ativoNome}`,
            start: taskStart.toISOString().slice(0, 10),
            end:   taskEnd.toISOString().slice(0, 10),
            color: st.color === 'red' ? 'var(--red)' : st.color === 'amber' ? 'var(--amber)' : 'var(--green)',
            _plano: p,
          };
        }).sort((a, b) => a.start.localeCompare(b.start));

        window.engine.gantt(body, {
          range: { start: startIso, end: endIso },
          tasks,
          onTaskMove: (id, s, e) => {
            const p = visibles.find(x => x.id === id);
            if (!p) return;
            p.proxima_execucao = s;
            toast(`Plano reagendado para ${s} (apenas local — salve via API)`, 'amber');
          },
        });
      }
    },

    config(cont) {
      const { el } = window.engine.utils;

      // ── Seção: Limiar do semáforo ─────────────────────────────────────
      const LS_THRESHOLD = 'xerp_manut_threshold';
      const currentThreshold = parseFloat(localStorage.getItem(LS_THRESHOLD) || '0.2');
      const fThreshold = el('input', {
        type: 'range', min: '0.05', max: '0.50', step: '0.05',
        value: String(currentThreshold),
        style: { width: '180px', accentColor: 'var(--acc)' },
      });
      const thresholdLabel = el('span', {
        style: { fontFamily: 'var(--font-mono)', fontSize: '13px', minWidth: '36px', display: 'inline-block' },
      }, `${Math.round(currentThreshold * 100)}%`);
      fThreshold.addEventListener('input', () => {
        const v = parseFloat(fThreshold.value);
        thresholdLabel.textContent = `${Math.round(v * 100)}%`;
      });
      const btnSaveThreshold = el('button', { class: 'pe-btn pe-btn--primary', onclick: () => {
        localStorage.setItem(LS_THRESHOLD, fThreshold.value);
        toast('Limiar salvo. Recarregue para aplicar.', 'green');
      } }, 'Salvar');

      const secThreshold = _configSection('Limiar do semáforo (amber)',
        el('div', { style: { display: 'flex', alignItems: 'center', gap: '10px', marginTop: '8px' } },
          el('span', { style: { fontSize: '13px', color: 'var(--ink-2)' } }, 'Âmbar quando faltam ≤'),
          fThreshold,
          thresholdLabel,
          el('span', { style: { fontSize: '13px', color: 'var(--ink-2)' } }, 'do intervalo'),
          btnSaveThreshold,
        ),
        'Percentual do intervalo antes do vencimento em que o plano passa para âmbar (padrão: 20%).',
      );

      // ── Seção: Resumo de dados ─────────────────────────────────────────
      const ativos   = state.cache.ativos?.data   || [];
      const os       = state.cache.os?.data       || [];
      const planos   = _allPlanos();
      const catalogo = _allCatalogo();
      const estoque  = state.cache.estoque?.data  || [];
      const ts = state.cache.ativos?.ts ? new Date(state.cache.ativos.ts).toLocaleTimeString('pt-BR') : '—';

      const rows = [
        ['Ativos carregados', ativos.length],
        ['OS carregadas',     os.length],
        ['Planos de manutenção', planos.length],
        ['Serviços no catálogo', catalogo.length],
        ['Itens de estoque',     estoque.length],
        ['Última sincronização', ts],
        ['Categorias disponíveis', state.catsAvailable.join(', ') || '—'],
      ];
      const secDados = _configSection('Resumo de dados',
        el('div', { style: { marginTop: '8px' } },
          ...rows.map(([k, v]) => el('div', {
            style: { display: 'flex', gap: '12px', padding: '4px 0', borderBottom: '1px solid var(--line)', fontSize: '13px' },
          },
            el('div', { style: { color: 'var(--ink-3)', minWidth: '220px' } }, k),
            el('div', { style: { fontFamily: 'var(--font-mono)' } }, String(v)),
          )),
        ),
      );

      // ── Seção: Ações de cache ──────────────────────────────────────────
      const secCache = _configSection('Cache e sincronização',
        el('div', { style: { display: 'flex', gap: '8px', marginTop: '8px', flexWrap: 'wrap' } },
          el('button', { class: 'pe-btn', onclick: () => {
            fetchAll().then(() => { markAllDirty(); renderActiveTab(); toast('Dados recarregados.', 'green'); });
          } }, '↻ Recarregar tudo'),
          el('button', { class: 'pe-btn pe-btn--ghost', onclick: () => {
            state.cache = { ativos: null, os: null, estoque: null, planos: null, catalogo: null };
            markAllDirty();
            toast('Cache limpo. Recarregue para buscar do núcleo.', 'amber');
          } }, '🗑 Limpar cache'),
        ),
      );

      cont.replaceChildren(
        el('div', { style: { maxWidth: '720px', display: 'flex', flexDirection: 'column', gap: '16px', paddingTop: '4px' } },
          secThreshold, secDados, secCache,
        ),
      );

      function _configSection(title, ...children) {
        return el('div', {
          style: { background: 'var(--panel)', border: '1px solid var(--line)', borderRadius: '8px', padding: '14px 16px' },
        },
          el('div', { style: { fontWeight: '600', marginBottom: '2px' } }, title),
          ...children,
        );
      }
    },
  });

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
    const planos = planosDoAtivo(ativo);
    const osDoAtivo = (state.cache.os?.data || []).filter(o => o.ativo_id === ativo.id);

    function dadosView() {
      return el('div', {},
        ...Object.entries(ativo)
          .filter(([k]) => !k.startsWith('_'))
          .map(([k, v]) =>
          el('div', { style: { display: 'flex', gap: '8px', padding: '6px 0', borderBottom: '1px solid var(--line)' } },
            el('div', { style: { color: 'var(--ink-3)', minWidth: '160px' } }, k),
            el('div', {}, v == null ? '—' : String(v)),
          )),
      );
    }
    function planosView() {
      if (!planos.length) return el('div', { style: { color: 'var(--ink-3)' } }, 'Sem planos vinculados.');
      return el('div', {},
        ...planos.map(p => {
          const st    = planStatus(p);
          const svNome = servicoNome(p.servico_id);
          const badge = window.engine.badge(
            st.label, st.color === 'red' ? 'red' : st.color === 'amber' ? 'amber' : 'green');
          const btOS = (st.color !== 'green')
            ? el('button', {
                class: 'pe-btn pe-btn--primary',
                style: { padding: '2px 8px', fontSize: '11px' },
                onclick: () => openCriarOSModal(ativo, p),
              }, '+ OS preventiva')
            : null;
          return el('div', {
            style: { display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 0', borderBottom: '1px solid var(--line)' },
          },
            badge,
            el('span', { style: { flex: 1, fontSize: '13px' } }, svNome),
            el('span', { style: { fontSize: '12px', color: 'var(--ink-3)' } },
              p.proxima_execucao ? `próx: ${fmt.date(p.proxima_execucao)}` : '—'),
            btOS,
          );
        }),
      );
    }
    function osView() {
      if (!osDoAtivo.length) return el('div', { style: { color: 'var(--ink-3)' } }, 'Sem OS para este ativo.');
      return el('div', {},
        ...osDoAtivo.map(o => el('div', {
          style: { display: 'flex', gap: '8px', padding: '4px 0', borderBottom: '1px solid var(--line)', cursor: 'pointer' },
          onclick: () => openOsDrawer(o),
        },
          window.engine.badge(o.status, o.status === 'concluida' ? 'green' : o.status === 'cancelada' ? 'red' : 'amber'),
          el('span', { style: { flex: 1, fontSize: '13px' } }, o.titulo || o.codigo || o.id),
          el('span', { style: { fontSize: '12px', color: 'var(--ink-3)' } }, fmt.date(o.data_abertura)),
        )));
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
    const subTabs = el('div', {}, tabBtn('dados', 'Dados'), tabBtn('planos', `Planos (${planos.length})`), tabBtn('os', `OS (${osDoAtivo.length})`));
    function refreshSubTabs() {
      subTabs.replaceChildren(tabBtn('dados', 'Dados'), tabBtn('planos', `Planos (${planos.length})`), tabBtn('os', `OS (${osDoAtivo.length})`));
    }

    const worstSt = ativoWorstStatus(ativo);
    const titleBadge = worstSt
      ? window.engine.badge(worstSt.label, worstSt.color === 'red' ? 'red' : worstSt.color === 'amber' ? 'amber' : 'green')
      : null;
    const titleEl = el('span', {}, ativo.nome, ' ', titleBadge || '');

    const m = window.engine.modal({
      title: ativo.nome,
      body: el('div', {}, subTabs, subBody),
      footer: [el('button', { class: 'pe-btn pe-btn--primary', onclick: () => m.close() }, 'Fechar')],
    });
    m.open();
    renderSub();
  }

  function openCriarOSModal(ativo, plano) {
    const { el } = window.engine.utils;
    const svNome = servicoNome(plano.servico_id);
    const titulo = `Manutenção preventiva: ${svNome}`;
    const fTitulo = el('input', { type: 'text', value: titulo, class: 'pe-input', style: { width: '100%' } });
    const fTipo   = el('select', { class: 'pe-input', style: { width: '100%' } },
      el('option', { value: 'preventiva', selected: true }, 'preventiva'),
      el('option', { value: 'corretiva' }, 'corretiva'),
    );
    const fPrior  = el('select', { class: 'pe-input', style: { width: '100%' } },
      el('option', { value: 'normal' }, 'normal'),
      el('option', { value: 'alta' }, 'alta'),
      el('option', { value: 'urgente' }, 'urgente'),
    );
    const fObs = el('textarea', { rows: 3, class: 'pe-input', style: { width: '100%' } },
      `Gerada via painel Manutenção. Plano: ${plano.id}`);

    const body = el('div', { style: { display: 'flex', flexDirection: 'column', gap: '10px' } },
      el('div', {}, el('label', {}, 'Título'), fTitulo),
      el('div', { style: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' } },
        el('div', {}, el('label', {}, 'Tipo'), fTipo),
        el('div', {}, el('label', {}, 'Prioridade'), fPrior),
      ),
      el('div', {}, el('label', {}, 'Observações'), fObs),
      el('div', { style: { fontSize: '12px', color: 'var(--ink-3)' } },
        `Ativo: ${ativo.nome} · Serviço: ${svNome}`),
    );

    const m = window.engine.modal({
      title: 'Criar OS Preventiva',
      body,
      footer: [
        el('button', { class: 'pe-btn pe-btn--ghost', onclick: () => m.close() }, 'Cancelar'),
        el('button', { class: 'pe-btn pe-btn--primary', onclick: async () => {
          const payload = {
            titulo: fTitulo.value.trim() || titulo,
            tipo: fTipo.value,
            prioridade: fPrior.value,
            ativo_id: ativo.id,
            servico_id: plano.servico_id,
            servico_versao_snapshot: plano.servico_versao_pin || null,
            obs: fObs.value,
          };
          try {
            const r = await fetch('/api/os', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(payload),
            });
            if (!r.ok) throw new Error(`HTTP ${r.status}`);
            toast('OS preventiva criada!', 'green');
            m.close();
            state.tabDirty.os = true;
            fetchAll().then(() => {
              if (state.activeTab === 'os') RENDERERS.os(document.getElementById('manut-tab-content'));
            });
          } catch (e) {
            toast(`Falha ao criar OS: ${e.message}`, 'red');
          }
        }}, 'Criar OS'),
      ],
    });
    m.open();
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
      // Catálogo e planos: GET não requer auth — falha silenciosa com fallback para mocks
      const [planos, catalogo] = await Promise.all([
        fetch('/api/catalogo/planos').then(r => r.ok ? r.json() : []).catch(() => []),
        fetch('/api/catalogo/servicos').then(r => r.ok ? r.json() : []).catch(() => []),
      ]);
      state.cache.planos   = { data: planos.length   ? planos   : (window.ERP_MANUT_MOCKS?.planos_manutencao || []),   ts: Date.now() };
      state.cache.catalogo = { data: catalogo.length ? catalogo : (window.ERP_MANUT_MOCKS?.catalogo_servicos  || []), ts: Date.now() };
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
