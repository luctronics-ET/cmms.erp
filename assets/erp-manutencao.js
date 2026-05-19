/**
 * Módulo da página `manutencao` no cmasm_erp.html — refatoração V1.
 * Spec: docs/superpowers/specs/2026-05-19-manutencao-unificada-design.md
 */
(function () {
  'use strict';
  // depende de: window.engine (pmoc-engine.js) + window.ERP_MANUT_MOCKS (erp-manutencao-mocks.js)

  let initialized = false;

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
    render(root);
  }

  function render(root) {
    // populado nas Tasks 4+
    root.replaceChildren(
      window.engine.utils.el('div',
        { style: { padding: '20px', color: 'var(--ink-2)' } },
        'Manutenção · refatorando (Task 3 ok).'),
    );
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
