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

  const RENDERERS = {};  // populated nas tasks 6-13

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
