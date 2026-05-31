(function () {
  const DEFAULTS = Object.freeze({
    aguada: {
      label: 'Aguada',
      navUrl: 'http://localhost:8001',
      appUrl: 'http://localhost:8001',
      title: 'Abrir módulo externo Aguada',
    },
    seguranca: {
      label: 'Segurança',
      navUrl: 'http://127.0.0.1:8000/ui',
      appUrl: 'http://127.0.0.1:8000/ui',
      title: 'Abrir interface ativa do xSeguranca',
    },
    cftv: {
      label: 'CFTV',
      navUrl: 'cftv.html',
      appUrl: '../xCFTV/src/main/webapp/index.xhtml',
      title: 'Abrir ponte do módulo CFTV',
    },
    paiol: {
      label: 'Paiol',
      navUrl: 'http://127.0.0.1:3003/paiois.html',
      appUrl: 'http://127.0.0.1:3003/paiois.html',
      title: 'Abrir interface ativa do xPaiol',
    },
  });

  function loadOverrides() {
    try {
      const raw = localStorage.getItem('xcmasm_module_links');
      return raw ? JSON.parse(raw) : {};
    } catch {
      return {};
    }
  }

  function getConfig(key) {
    const base = DEFAULTS[key] || {};
    const override = loadOverrides()[key] || {};
    return { ...base, ...override };
  }

  function resolveUrl(key, field = 'navUrl') {
    const cfg = getConfig(key);
    return cfg[field] || cfg.navUrl || '#';
  }

  function applyAnchor(anchor, key, field = 'navUrl') {
    if (!anchor) return;
    const cfg = getConfig(key);
    anchor.href = resolveUrl(key, field);
    if (cfg.title) anchor.title = cfg.title;
  }

  window.XCMASM_MODULE_LINK_DEFAULTS = DEFAULTS;
  window.getXCMASMModuleLink = getConfig;
  window.resolveXCMASMModuleUrl = resolveUrl;
  window.applyXCMASMModuleAnchor = applyAnchor;
})();