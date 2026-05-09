/**
 * xMap — Componente de Mapa xCMASM
 * Singleton global: window.xMap
 *
 * Uso:
 *   xMap.init('container-id', { modules: ['aguada'], zoom: 15 })
 *   xMap.setModules(['aguada', 'grama'])
 *   xMap.toggleBasemap('satellite' | 'map')
 *   xMap.updateElement('aguada', 'reservoir', 'CON', { pct: 72, online: true })
 *   xMap.registerLayer(moduleName, layerDef)
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

  /* ── Estado interno ── */
  let _map = null;
  let _basemapMode = 'map';
  let _baseLayers = {};
  let _activeModules = [];
  let _registeredLayers = {};  // { moduleName: { layerKey: { group, def } } }
  let _filterState = {};       // { moduleName: { layerKey: true/false } }
  let _wrapperEl = null;
  let _filtersEl = null;
  let _badgeEl = null;
  let _opts = {};

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

  /* ── Construção da toolbar de basemap ── */
  function _buildToolbar(wrapper) {
    const tb = document.createElement('div');
    tb.className = 'xmap-toolbar';
    tb.innerHTML = `
      <button class="xmap-basemap-btn active" data-mode="map">
        <svg viewBox="0 0 16 16" fill="currentColor">
          <path d="M8 1a7 7 0 1 0 0 14A7 7 0 0 0 8 1zM2.5 8.5h2a5.5 5.5 0 0 0 1 2.7A5.5 5.5 0 0 1 2.5 8.5zm0-1a5.5 5.5 0 0 1 3-4.7A5.5 5.5 0 0 0 4.5 7.5h-2zm4 5.4V10.5h1a4.5 4.5 0 0 1-.5 2.4zm1-6.4h-1V3.1A4.5 4.5 0 0 1 8 5.5h-.5zm1 6.4a4.5 4.5 0 0 1-.5-2.4h1v2.4zm0-6.4h-.5A4.5 4.5 0 0 1 8.5 3.1V6.5h.5zm.5 5.7a5.5 5.5 0 0 0 1-2.7h2a5.5 5.5 0 0 1-3 2.7zm1-3.7a5.5 5.5 0 0 0-1-2.5 5.5 5.5 0 0 1 3 4.7h-2z"/>
        </svg>
        Mapa
      </button>
      <div class="xmap-toolbar-sep"></div>
      <button class="xmap-basemap-btn" data-mode="satellite">
        <svg viewBox="0 0 16 16" fill="currentColor">
          <path d="M9.5 1.5a.5.5 0 0 0-.75-.43L5.5 3H3a1 1 0 0 0-1 1v4a1 1 0 0 0 1 1h2.5l3.25 1.93A.5.5 0 0 0 9.5 10.5V1.5zm1.5 3.5a.5.5 0 0 1 .5.5v3a.5.5 0 0 1-1 0v-3a.5.5 0 0 1 .5-.5zm1.5-1a.5.5 0 0 1 .5.5v5a.5.5 0 0 1-1 0v-5a.5.5 0 0 1 .5-.5z"/>
        </svg>
        Satélite
      </button>`;
    wrapper.appendChild(tb);

    tb.querySelectorAll('.xmap-basemap-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const mode = btn.dataset.mode;
        xMap.toggleBasemap(mode);
        tb.querySelectorAll('.xmap-basemap-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
      });
    });
  }

  /* ── Painel de filtros ── */
  function _buildFiltersPanel(wrapper) {
    const panel = document.createElement('div');
    panel.className = 'xmap-filters';
    panel.innerHTML = `<div class="xmap-filters-title">Layers</div>`;
    wrapper.appendChild(panel);
    _filtersEl = panel;
    _renderFilters();
  }

  function _renderFilters() {
    if (!_filtersEl) return;
    _filtersEl.innerHTML = `<div class="xmap-filters-title">Layers</div>`;

    _activeModules.forEach(mod => {
      const layers = _registeredLayers[mod];
      if (!layers) return;
      Object.entries(layers).forEach(([key, { def }]) => {
        const isOn = _filterState[mod]?.[key] !== false;
        const item = document.createElement('div');
        item.className = `xmap-filter-item ${isOn ? 'on' : ''}`;
        item.innerHTML = `
          <span class="xmap-filter-dot" style="background:${def.color || '#8fa8c8'}"></span>
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
    const entry = _registeredLayers[mod]?.[key];
    if (!entry) return;
    const visible = _filterState[mod]?.[key] !== false;
    if (visible) {
      if (!_map.hasLayer(entry.group)) _map.addLayer(entry.group);
    } else {
      if (_map.hasLayer(entry.group)) _map.removeLayer(entry.group);
    }
  }

  /* ── Badge de módulos ativos ── */
  function _buildModuleBadge(wrapper) {
    const el = document.createElement('div');
    el.className = 'xmap-module-badge';
    wrapper.appendChild(el);
    _badgeEl = el;
  }

  function _renderModuleBadge() {
    if (!_badgeEl) return;
    _badgeEl.innerHTML = _activeModules
      .map(m => `<span class="xmap-mod-chip" data-mod="${m}">${m.toUpperCase()}</span>`)
      .join('');
  }

  /* ── API pública ── */
  const xMap = {

    /**
     * Inicializa o mapa em um elemento HTML.
     * @param {string} containerId  ID do elemento pai
     * @param {object} options
     *   - modules: string[]   módulos ativos inicial (default: [])
     *   - basemap: 'map'|'satellite'
     *   - center: [lat, lon]
     *   - zoom: number
     *   - minZoom: number
     *   - maxZoom: number
     */
    init(containerId, options = {}) {
      const parent = document.getElementById(containerId);
      if (!parent) { console.error(`xMap: elemento #${containerId} não encontrado`); return; }

      _opts = Object.assign({
        modules: [],
        basemap: 'map',
        center: [-22.8395, -43.106],
        zoom: 15,
        minZoom: 13,
        maxZoom: 19,
      }, options);

      /* Wrapper */
      _wrapperEl = document.createElement('div');
      _wrapperEl.className = 'xmap-wrapper';
      _wrapperEl.style.cssText = 'position:relative;width:100%;height:100%;';
      parent.appendChild(_wrapperEl);

      /* Container do leaflet */
      const container = document.createElement('div');
      container.className = 'xmap-container';
      container.style.cssText = 'width:100%;height:100%;';
      _wrapperEl.appendChild(container);

      /* Inicializa Leaflet */
      _map = L.map(container, {
        center: _opts.center,
        zoom: _opts.zoom,
        minZoom: _opts.minZoom,
        maxZoom: _opts.maxZoom,
        zoomControl: true,
        attributionControl: true,
      });

      /* Reposiciona zoom control */
      _map.zoomControl.setPosition('bottomright');

      /* Tile layers */
      _baseLayers.map = L.tileLayer(TILES.map.url, {
        attribution: TILES.map.attribution,
        maxZoom: TILES.map.maxZoom,
      });
      _baseLayers.satellite = L.tileLayer(TILES.satellite.url, {
        attribution: TILES.satellite.attribution,
        maxZoom: TILES.satellite.maxZoom,
      });

      _basemapMode = _opts.basemap;
      _baseLayers[_basemapMode].addTo(_map);

      /* UI */
      _buildToolbar(_wrapperEl);
      _buildFiltersPanel(_wrapperEl);
      _buildModuleBadge(_wrapperEl);

      /* Módulos iniciais */
      if (_opts.modules.length) {
        this.setModules(_opts.modules);
      }

      return this;
    },

    /**
     * Define os módulos ativos (layers dos outros módulos ficam ocultos).
     * @param {string[]} moduleNames
     */
    setModules(moduleNames) {
      const prev = [..._activeModules];
      _activeModules = moduleNames;

      /* Oculta todos */
      Object.entries(_registeredLayers).forEach(([mod, layers]) => {
        Object.entries(layers).forEach(([key, { group }]) => {
          if (_map.hasLayer(group)) _map.removeLayer(group);
        });
      });

      /* Mostra apenas os ativos, respeitando filtros */
      _activeModules.forEach(mod => {
        const layers = _registeredLayers[mod];
        if (!layers) return;
        if (!_filterState[mod]) _filterState[mod] = {};
        Object.entries(layers).forEach(([key, { group }]) => {
          if (_filterState[mod][key] === undefined) _filterState[mod][key] = true;
          if (_filterState[mod][key]) _map.addLayer(group);
        });
      });

      _renderFilters();
      _renderModuleBadge();
    },

    /**
     * Alterna basemap entre mapa e satélite.
     * @param {'map'|'satellite'} mode  (opcional — alterna se omitido)
     */
    toggleBasemap(mode) {
      const next = mode || (_basemapMode === 'map' ? 'satellite' : 'map');
      if (next === _basemapMode) return;
      _map.removeLayer(_baseLayers[_basemapMode]);
      _basemapMode = next;
      _baseLayers[_basemapMode].addTo(_map);
    },

    /**
     * Registra layers de um módulo.
     * @param {string} moduleName
     * @param {object} layerDefs  { layerKey: { label, color, render(map) → LayerGroup } }
     */
    registerLayer(moduleName, layerDefs) {
      if (!_registeredLayers[moduleName]) _registeredLayers[moduleName] = {};

      Object.entries(layerDefs).forEach(([key, def]) => {
        const group = L.layerGroup();
        def.render(group);
        _registeredLayers[moduleName][key] = { group, def };

        /* Se já é módulo ativo, adiciona ao mapa */
        if (_activeModules.includes(moduleName)) {
          if (!_filterState[moduleName]) _filterState[moduleName] = {};
          if (_filterState[moduleName][key] !== false) _map.addLayer(group);
          _renderFilters();
        }
      });
    },

    /**
     * Atualiza dados de um elemento específico.
     * @param {string} moduleName
     * @param {string} layerKey
     * @param {string} elementId   identificador único do elemento
     * @param {object} data        novos dados
     */
    updateElement(moduleName, layerKey, elementId, data) {
      const entry = _registeredLayers[moduleName]?.[layerKey];
      if (!entry?.def?.update) return;
      entry.def.update(entry.group, elementId, data);
    },

    /**
     * Retorna instância do Leaflet map (para uso avançado).
     */
    getLeafletMap() { return _map; },

    /* Utilidades expostas para uso nos layer files */
    utils: { createSVGIcon, popupHTML },
  };

  global.xMap = xMap;
})(window);
