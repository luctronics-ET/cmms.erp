/**
 * xMap — Componente de Mapa xCMASM (multi-instância)
 * Singleton de API global: window.xMap
 *
 * Uso:
 *   const inst = xMap.create('container-id', { modules: ['grama'], zoom: 15 })
 *   inst.setModules(['grama','aguada'])
 *   inst.toggleBasemap('satellite' | 'map')
 *   inst.hideLayer('grama','areas')      // oculta uma camada nesta instância
 *   inst.getLeafletMap()                 // L.Map para uso avançado (editor, etc)
 *   xMap.registerLayer(moduleName, layerDefs)   // defs compartilhadas entre instâncias
 *
 * Compat: xMap.init(...) cria/retorna a instância padrão.
 */

(function (global) {
  'use strict';

  /* ── Tile URLs ── */
  const TILES = {
    map: {
      url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
      attribution: '© <a href="https://www.openstreetmap.org/copyright">OSM</a>',
      maxZoom: 19,
    },
    satellite: {
      url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
      attribution: '© Esri',
      maxZoom: 19,
    },
  };

  /* ── Registro global de definições de camada (compartilhado entre instâncias) ── */
  const _layerDefs = {};   // { moduleName: { layerKey: def } }
  const _instances = [];   // instâncias vivas (p/ re-build ao registrar camada nova)

  /* ── Utilitários ── */
  function createSVGIcon(svgContent, size = [28, 28], anchor = [14, 14]) {
    return L.divIcon({
      html: svgContent,
      className: '',
      iconSize: size,
      iconAnchor: anchor,
      popupAnchor: [0, -anchor[1]],
    });
  }

  function popupHTML(icon, title, sub, rows) {
    const rowsHTML = rows.map(([k, v, cls = '']) =>
      `<div class="xmap-popup-row">
        <span class="xmap-popup-key">${k}</span>
        <span class="xmap-popup-val ${cls}">${v}</span>
      </div>`
    ).join('');
    return `
      <div class="xmap-popup">
        <div class="xmap-popup-header">
          <span class="xmap-popup-icon">${icon}</span>
          <div>
            <div class="xmap-popup-title">${title}</div>
            ${sub ? `<div class="xmap-popup-sub">${sub}</div>` : ''}
          </div>
        </div>
        <div class="xmap-popup-rows">${rowsHTML}</div>
      </div>`;
  }

  /* ───────────────────────── Instância ───────────────────────── */
  function makeInstance(containerId, options) {
    const parent = document.getElementById(containerId);
    if (!parent) { console.error(`xMap: elemento #${containerId} não encontrado`); return null; }

    const opts = Object.assign({
      modules: [],
      basemap: 'map',
      center: [-22.8395, -43.106],
      zoom: 15,
      minZoom: 13,
      maxZoom: 19,
      showFilters: true,
      showBadge: true,
      hidden: [],          // ['grama:areas', ...] camadas ocultas por padrão
    }, options);

    let _map = null;
    let _basemapMode = opts.basemap;
    const _baseLayers = {};
    let _activeModules = [];
    const _built = {};        // { module: { key: { group, def } } }
    const _filterState = {};   // { module: { key: bool } }
    const _hidden = {};        // { module: { key: true } } — forçado oculto
    let _wrapperEl = null, _filtersEl = null, _badgeEl = null;

    (opts.hidden || []).forEach(h => {
      const [m, k] = String(h).split(':');
      if (m && k) { (_hidden[m] = _hidden[m] || {})[k] = true; }
    });

    /* DOM */
    _wrapperEl = document.createElement('div');
    _wrapperEl.className = 'xmap-wrapper';
    _wrapperEl.style.cssText = 'position:relative;width:100%;height:100%;';
    parent.appendChild(_wrapperEl);
    const container = document.createElement('div');
    container.className = 'xmap-container';
    container.style.cssText = 'width:100%;height:100%;';
    _wrapperEl.appendChild(container);

    _map = L.map(container, {
      center: opts.center, zoom: opts.zoom,
      minZoom: opts.minZoom, maxZoom: opts.maxZoom,
      zoomControl: true, attributionControl: true,
    });
    _map.zoomControl.setPosition('bottomright');

    _baseLayers.map = L.tileLayer(TILES.map.url, { attribution: TILES.map.attribution, maxZoom: TILES.map.maxZoom });
    _baseLayers.satellite = L.tileLayer(TILES.satellite.url, { attribution: TILES.satellite.attribution, maxZoom: TILES.satellite.maxZoom });
    _baseLayers[_basemapMode].addTo(_map);

    /* Toolbar basemap */
    function _buildToolbar() {
      const tb = document.createElement('div');
      tb.className = 'xmap-toolbar';
      tb.innerHTML =
        `<button class="xmap-basemap-btn ${_basemapMode==='map'?'active':''}" data-mode="map">Mapa</button>
         <div class="xmap-toolbar-sep"></div>
         <button class="xmap-basemap-btn ${_basemapMode==='satellite'?'active':''}" data-mode="satellite">Satélite</button>`;
      _wrapperEl.appendChild(tb);
      tb.querySelectorAll('.xmap-basemap-btn').forEach(btn => {
        btn.addEventListener('click', () => {
          inst.toggleBasemap(btn.dataset.mode);
          tb.querySelectorAll('.xmap-basemap-btn').forEach(b => b.classList.remove('active'));
          btn.classList.add('active');
        });
      });
    }

    /* Painel de filtros */
    function _buildFiltersPanel() {
      const panel = document.createElement('div');
      panel.className = 'xmap-filters';
      _wrapperEl.appendChild(panel);
      _filtersEl = panel;
      _renderFilters();
    }
    function _renderFilters() {
      if (!_filtersEl) return;
      _filtersEl.innerHTML = `<div class="xmap-filters-title">Layers</div>`;
      _activeModules.forEach(mod => {
        const layers = _built[mod]; if (!layers) return;
        Object.entries(layers).forEach(([key, { def }]) => {
          if (_hidden[mod] && _hidden[mod][key]) return;
          const isOn = _filterState[mod] && _filterState[mod][key] !== false;
          const item = document.createElement('div');
          item.className = `xmap-filter-item ${isOn ? 'on' : ''}`;
          item.innerHTML =
            `<span class="xmap-filter-dot" style="background:${def.color || '#8fa8c8'}"></span>
             <span class="xmap-filter-label">${def.label || key}</span>
             <span class="xmap-filter-toggle"></span>`;
          item.addEventListener('click', () => {
            if (!_filterState[mod]) _filterState[mod] = {};
            _filterState[mod][key] = !isOn;
            _applyVisibility(mod, key);
            _renderFilters();
          });
          _filtersEl.appendChild(item);
        });
      });
    }
    function _applyVisibility(mod, key) {
      const entry = _built[mod] && _built[mod][key]; if (!entry) return;
      const visible = _filterState[mod] && _filterState[mod][key] !== false
        && !(_hidden[mod] && _hidden[mod][key]);
      if (visible) { if (!_map.hasLayer(entry.group)) _map.addLayer(entry.group); }
      else { if (_map.hasLayer(entry.group)) _map.removeLayer(entry.group); }
    }

    function _buildBadge() {
      _badgeEl = document.createElement('div');
      _badgeEl.className = 'xmap-module-badge';
      _wrapperEl.appendChild(_badgeEl);
    }
    function _renderBadge() {
      if (!_badgeEl) return;
      _badgeEl.innerHTML = _activeModules.map(m => `<span class="xmap-mod-chip" data-mod="${m}">${m.toUpperCase()}</span>`).join('');
    }

    /* Constrói grupos de um módulo a partir das defs registradas */
    function _buildModule(mod) {
      const defs = _layerDefs[mod]; if (!defs) return;
      if (!_built[mod]) _built[mod] = {};
      Object.entries(defs).forEach(([key, def]) => {
        if (_built[mod][key]) return;     // já construído
        const group = L.layerGroup();
        try { def.render(group); } catch (e) { console.warn('xMap render falhou', mod, key, e); }
        _built[mod][key] = { group, def };
      });
    }

    if (opts.showToolbar !== false) _buildToolbar();
    if (opts.showFilters) _buildFiltersPanel();
    if (opts.showBadge) _buildBadge();

    const inst = {
      getLeafletMap() { return _map; },
      setModules(moduleNames) {
        _activeModules = moduleNames.slice();
        /* oculta tudo */
        Object.values(_built).forEach(layers => Object.values(layers).forEach(({ group }) => { if (_map.hasLayer(group)) _map.removeLayer(group); }));
        /* constrói + mostra ativos */
        _activeModules.forEach(mod => {
          _buildModule(mod);
          if (!_filterState[mod]) _filterState[mod] = {};
          const layers = _built[mod]; if (!layers) return;
          Object.entries(layers).forEach(([key, { group }]) => {
            if (_filterState[mod][key] === undefined) _filterState[mod][key] = true;
            if (_filterState[mod][key] && !(_hidden[mod] && _hidden[mod][key])) _map.addLayer(group);
          });
        });
        _renderFilters(); _renderBadge();
        return inst;
      },
      hideLayer(mod, key) { (_hidden[mod] = _hidden[mod] || {})[key] = true; _applyVisibility(mod, key); _renderFilters(); return inst; },
      showLayer(mod, key) { if (_hidden[mod]) delete _hidden[mod][key]; _applyVisibility(mod, key); _renderFilters(); return inst; },
      toggleBasemap(mode) {
        const next = mode || (_basemapMode === 'map' ? 'satellite' : 'map');
        if (next === _basemapMode) return;
        _map.removeLayer(_baseLayers[_basemapMode]);
        _basemapMode = next;
        _baseLayers[_basemapMode].addTo(_map);
        if (_baseLayers[_basemapMode].bringToBack) _baseLayers[_basemapMode].bringToBack();
      },
      /* chamado quando uma camada nova é registrada após a instância existir */
      _onLayerRegistered(mod) {
        if (_activeModules.includes(mod)) this.setModules(_activeModules);
      },
      invalidateSize() { if (_map) setTimeout(() => _map.invalidateSize(), 60); },
    };

    if (opts.modules && opts.modules.length) inst.setModules(opts.modules);
    _instances.push(inst);
    return inst;
  }

  /* ───────────────────────── API global ───────────────────────── */
  let _default = null;
  const xMap = {
    create(containerId, options = {}) { return makeInstance(containerId, options); },
    init(containerId, options = {}) { _default = makeInstance(containerId, options); return _default; },
    getLeafletMap() { return _default && _default.getLeafletMap(); },
    setModules(m) { return _default && _default.setModules(m); },
    toggleBasemap(m) { return _default && _default.toggleBasemap(m); },
    registerLayer(moduleName, layerDefs) {
      if (!_layerDefs[moduleName]) _layerDefs[moduleName] = {};
      Object.assign(_layerDefs[moduleName], layerDefs);
      _instances.forEach(i => i._onLayerRegistered(moduleName));
    },
    utils: { createSVGIcon, popupHTML },
  };

  global.xMap = xMap;
})(window);
