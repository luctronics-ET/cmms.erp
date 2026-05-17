/**
 * xcmasm-shell.js — Shell de navegação unificado para módulos satélites xCMASM
 * Versão 1.0 · 2026-05
 *
 * Uso:
 *   <script src="/assets/xcmasm-shell.js"></script>
 *   xShell.init({ activePage: 'predial', pageTitle: 'xPredial', subtitle: '...', nav: [...] });
 *   // Após init, injetar conteúdo em document.getElementById('xc-content')
 */
(function (global) {
  'use strict';

  const TOKEN_KEY = 'xcmasm_token';
  const USER_KEY  = 'xcmasm_user';
  const XCORE_URL_KEY = 'xcmasm_xcore_url';

  // ── Detectar URL do xCore ──────────────────────────────────────────────────
  function resolveXcoreUrl() {
    if (window.XCORE_URL) return window.XCORE_URL.replace(/\/$/, '');
    const stored = localStorage.getItem(XCORE_URL_KEY);
    if (stored) return stored.replace(/\/$/, '');
    const { protocol, hostname } = window.location;
    if (protocol === 'file:') return 'http://127.0.0.1:8010';
    return `${protocol}//${hostname}:8010`;
  }

  // ── Módulos disponíveis ─────────────────────────────────────────────────────
  const MODULE_DEFS = {
    erp:         { label: 'xCMASM ERP',   icon: '⚙️',  href: null,                          ext: false },
    predial:     { label: 'xPredial',     icon: '🏢',  href: 'http://localhost:8002',        ext: true  },
    aguada:      { label: 'xAguada',      icon: '💧',  href: 'http://localhost:8001',        ext: true  },
    paiol:       { label: 'xPaiol',       icon: '📦',  href: 'http://localhost:8003',        ext: true  },
    calibracao:  { label: 'xCalibracao',  icon: '📏',  href: 'http://localhost:8004',        ext: true  },
    seguranca:   { label: 'xSegurança',   icon: '🔒',  href: 'http://localhost:3000',        ext: true  },
  };

  // ── Navegar de volta ao ERP ────────────────────────────────────────────────
  function erpUrl() {
    return resolveXcoreUrl() + '/cmasm_erp.html';
  }

  // ── HTML da sidebar ────────────────────────────────────────────────────────
  function buildSidebar(cfg) {
    const nav = cfg.nav || [];
    const activePage = cfg.activePage || '';
    const moduleKey  = cfg.moduleKey || '';
    const moduleDef  = MODULE_DEFS[moduleKey] || {};
    const mark       = (moduleDef.label || 'XC').replace(/^x/, '').substring(0, 2).toUpperCase();

    let navItems = nav.map(item => {
      const isActive = item.id === activePage ? 'active' : '';
      return `<a href="${item.href}" class="xc-ni ${isActive}">
        <span class="xc-ni-ico">${item.icon || '◦'}</span>
        <span class="xc-ni-label">${item.label}</span>
      </a>`;
    }).join('');

    const user = (() => { try { return JSON.parse(localStorage.getItem(USER_KEY)) || {}; } catch { return {}; } })();
    const userInitials = (user.nome || '??').split(' ').slice(0, 2).map(n => n[0]).join('').toUpperCase();
    const userName  = user.nome  || 'Visitante';
    const userRole  = user.posto || user.cargo || 'CMASM';

    return `
<aside class="xc-sb">
  <div class="xc-sb-head">
    <div class="xc-sb-mark">${mark}</div>
    <div class="xc-sb-brand">
      <strong>${moduleDef.label || cfg.pageTitle || 'xCMASM'}</strong>
      <span>CMASM · Marinha do Brasil</span>
    </div>
  </div>
  <nav class="xc-sb-nav">
    <div class="xc-sb-sec">Módulo</div>
    ${navItems}
    <div class="xc-sb-sec">Sistema</div>
    <a href="${erpUrl()}" class="xc-ni">
      <span class="xc-ni-ico">🏠</span>
      <span class="xc-ni-label">← xCMASM ERP</span>
    </a>
  </nav>
  <div class="xc-sb-foot">
    <div class="xc-sb-user">
      <div class="xc-sb-avatar">${userInitials}</div>
      <div class="xc-sb-uinfo">
        <b>${userName}</b>
        <small>${userRole}</small>
      </div>
    </div>
    <div class="xc-sb-foot-row">
      <button class="xc-sb-icon-btn" title="Alternar tema" onclick="xShell.toggleTheme()">☀</button>
      <button class="xc-sb-icon-btn" title="Voltar ao ERP" onclick="location.href='${erpUrl()}'">⌂</button>
    </div>
  </div>
</aside>`;
  }

  // ── HTML do topbar ─────────────────────────────────────────────────────────
  function buildTopbar(cfg) {
    return `
<header class="xc-topbar">
  <span class="xc-tb-title">${cfg.pageTitle || ''}</span>
  ${cfg.subtitle ? `<span class="xc-tb-sep">·</span><span class="xc-tb-sub">${cfg.subtitle}</span>` : ''}
  <div class="xc-tb-right">
    <a href="${erpUrl()}" class="xc-home-link">⌂ xCMASM</a>
  </div>
</header>`;
  }

  // ── Montar shell completo ──────────────────────────────────────────────────
  function buildShell(cfg) {
    document.body.innerHTML = `
<div class="xc-app">
  ${buildSidebar(cfg)}
  <div class="xc-main">
    ${buildTopbar(cfg)}
    <div class="xc-content" id="xc-content"></div>
  </div>
</div>`;
  }

  // ── Injetar conteúdo do template ───────────────────────────────────────────
  function injectContent() {
    const tpl = document.getElementById('page-content');
    const target = document.getElementById('xc-content');
    if (tpl && target) {
      target.appendChild(document.importNode(tpl.content, true));
    }
  }

  // ── Tema claro/escuro ──────────────────────────────────────────────────────
  function applyTheme() {
    const theme = localStorage.getItem('xcmasm_theme') || 'dark';
    document.documentElement.classList.toggle('light', theme === 'light');
  }

  function toggleTheme() {
    const current = localStorage.getItem('xcmasm_theme') || 'dark';
    const next = current === 'dark' ? 'light' : 'dark';
    localStorage.setItem('xcmasm_theme', next);
    applyTheme();
  }

  // ── API pública ────────────────────────────────────────────────────────────
  const xShell = {
    /**
     * Inicializar o shell.
     * @param {object} cfg
     * @param {string} cfg.activePage    - id da página ativa (para highlight no nav)
     * @param {string} cfg.moduleKey     - chave do módulo (predial, paiol, aguada...)
     * @param {string} cfg.pageTitle     - título exibido no topbar
     * @param {string} cfg.subtitle      - subtítulo (mono) exibido no topbar
     * @param {Array}  cfg.nav           - lista de {id, label, icon, href} para a sidebar
     * @param {boolean} cfg.autoInject   - se true (padrão), injeta #page-content automaticamente
     */
    init(cfg) {
      cfg = cfg || {};
      applyTheme();
      buildShell(cfg);
      if (cfg.autoInject !== false) {
        injectContent();
      }
    },

    toggleTheme,
    resolveXcoreUrl,

    /** Retorna o usuário logado do localStorage */
    currentUser() {
      try { return JSON.parse(localStorage.getItem(USER_KEY)) || null; } catch { return null; }
    },

    /** Retorna o token Bearer */
    token() {
      return localStorage.getItem(TOKEN_KEY) || '';
    },
  };

  global.xShell = xShell;

}(window));
