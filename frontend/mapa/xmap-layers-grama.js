/**
 * xMap Layers — xGrama (Controle Vegetal)
 * Elementos: áreas de serviço (polígonos), máquinas (marcadores com posição GPS)
 *
 * Busca dados da API xCore em :8010/api/grama/*.
 * Fallback para dados mock se a API estiver offline.
 */

(function () {

  const API = 'http://localhost:8010/api/grama';

  /* ── Dados mock de fallback ── */
  const MOCK_AREAS = [
    {
      id: 'mock-1', nome: 'Área Principal — Frente', tipo: 'jardim', area_m2: 3200, ativa: true,
      flora: 'gramado', inclinacao: 'plano', limpeza: 'limpa',
      maquinas_compativeis: '["cortador_grama"]',
      coords_json: JSON.stringify([
        [-22.8375,-43.1090],[-22.8372,-43.1060],[-22.8368,-43.1060],[-22.8371,-43.1090],
      ]),
    },
    {
      id: 'mock-2', nome: 'Bosque Norte', tipo: 'bosque', area_m2: 8500, ativa: true,
      flora: 'mata_fechada', inclinacao: 'moderado', limpeza: 'densa',
      maquinas_compativeis: '["motosserra","roçadeira"]',
      coords_json: JSON.stringify([
        [-22.8364,-43.1095],[-22.8360,-43.1065],[-22.8355,-43.1065],[-22.8359,-43.1095],
      ]),
    },
    {
      id: 'mock-3', nome: 'Canteiro Leste', tipo: 'canteiro', area_m2: 450, ativa: true,
      flora: 'gramado', inclinacao: 'plano', limpeza: 'media',
      maquinas_compativeis: '["cortador_grama","roçadeira"]',
      coords_json: JSON.stringify([
        [-22.8392,-43.1072],[-22.8390,-43.1068],[-22.8388,-43.1069],[-22.8390,-43.1073],
      ]),
    },
    {
      id: 'mock-4', nome: 'Área Recreativa Sul', tipo: 'area_recreativa', area_m2: 1800, ativa: true,
      flora: 'gramado', inclinacao: 'moderado', limpeza: 'limpa',
      maquinas_compativeis: '["roçadeira"]',
      coords_json: JSON.stringify([
        [-22.8410,-43.1085],[-22.8406,-43.1070],[-22.8402,-43.1072],[-22.8406,-43.1087],
      ]),
    },
  ];

  const MOCK_MAQUINAS = [
    { id: 'maq-1', nome: 'CG-01', tipo: 'cortador_grama', status: 'operacional',    lat: -22.8376, lon: -43.1075, horas_uso: 342, combustivel_atual: 75 },
    { id: 'maq-2', nome: 'RO-01', tipo: 'roçadeira',      status: 'operacional',    lat: -22.8388, lon: -43.1071, horas_uso: 128, combustivel_atual: 40 },
    { id: 'maq-3', nome: 'MS-01', tipo: 'motosserra',     status: 'em_manutencao', lat: -22.8362, lon: -43.1080, horas_uso: 87,  combustivel_atual: 0  },
    { id: 'maq-4', nome: 'SP-01', tipo: 'soprador',       status: 'inativo',        lat: -22.8404, lon: -43.1078, horas_uso: 56,  combustivel_atual: 90 },
  ];

  /* ── Estilos por tipo de área ── */
  function areaStyle(tipo) {
    const s = {
      jardim:          { color: '#4ade80', fill: '#4ade80' },
      bosque:          { color: '#166534', fill: '#16a34a' },
      canteiro:        { color: '#86efac', fill: '#86efac' },
      area_recreativa: { color: '#22d3ee', fill: '#22d3ee' },
      horta:           { color: '#a3e635', fill: '#a3e635' },
    };
    return s[tipo] || { color: '#4ade80', fill: '#4ade80' };
  }

  function tipoLabel(t) {
    return { jardim:'Jardim', bosque:'Bosque', canteiro:'Canteiro', area_recreativa:'Área Recreativa', horta:'Horta' }[t] || t;
  }

  function statusClass(s) {
    return { operacional: 'ok', em_manutencao: 'warn', inativo: '' }[s] || '';
  }

  function maqLabel(t) {
    return { cortador_grama:'Cortador', roçadeira:'Roçadeira', motosserra:'Motosserra', soprador:'Soprador' }[t] || t;
  }

  /* ── SVG máquina ── */
  function maquinaSVG(tipo, status) {
    const c = { operacional: '#4ade80', em_manutencao: '#f59e0b', inativo: '#4a6785' }[status] || '#8fa8c8';
    const ico = { cortador_grama:'✂', roçadeira:'⚡', motosserra:'⚙', soprador:'〜' }[tipo] || '⚙';
    return `<svg xmlns="http://www.w3.org/2000/svg" width="30" height="30" viewBox="0 0 30 30">
      <rect x="2" y="2" width="26" height="26" rx="6" fill="rgba(7,17,31,.92)" stroke="${c}" stroke-width="2"/>
      <text x="15" y="20" text-anchor="middle" font-size="14" fill="${c}">${ico}</text>
      ${status === 'em_manutencao' ? '<circle cx="24" cy="6" r="4" fill="#f59e0b"/>' : ''}
    </svg>`;
  }

  function makeIcon(svg, size, anchor) {
    return L.divIcon({ html: svg, className: '', iconSize: size, iconAnchor: anchor, popupAnchor: [0, -anchor[1]] });
  }

  /* ── Renderiza áreas num LayerGroup ── */
  function renderAreas(group, areas) {
    areas.forEach(area => {
      if (!area.coords_json) return;
      let coords;
      try { coords = JSON.parse(area.coords_json); } catch { return; }
      if (!coords || !coords.length) return;

      const s = areaStyle(area.tipo);
      const poly = L.polygon(coords, {
        color: s.color, fillColor: s.fill, fillOpacity: 0.13, weight: 2,
      });

      /* Popup com atributos de vegetação */
      const maqJson = area.maquinas_compativeis ? JSON.parse(area.maquinas_compativeis) : [];
      const maqStr = maqJson.map(m => maqLabel(m)).join(', ') || '—';

      const floraLabels = { gramado:'Gramado', capim_colonial:'Cap. Colonial', mata_fechada:'Mata Fechada' };
      const inclLabels  = { plano:'Plano', moderado:'Moderado', acentuado:'Acentuado' };
      const limpLabels  = { limpa:'Limpa', media:'Média', densa:'Densa' };

      const rows = [
        ['Tipo',       tipoLabel(area.tipo)],
        ['Área',       (area.area_m2 || 0).toLocaleString('pt-BR') + ' m²'],
      ];
      if (area.flora)      rows.push(['Flora',      floraLabels[area.flora] || area.flora]);
      if (area.inclinacao) rows.push(['Inclinação', inclLabels[area.inclinacao] || area.inclinacao]);
      if (area.limpeza)    rows.push(['Limpeza',    limpLabels[area.limpeza] || area.limpeza]);
      if (maqJson.length)  rows.push(['Máquinas',   maqStr, 'info']);

      poly.bindPopup(
        xMap.utils.popupHTML('🌿', area.nome, tipoLabel(area.tipo), rows),
        { maxWidth: 240 }
      );

      poly.bindTooltip(area.nome, {
        permanent: false, direction: 'center',
        className: 'xmap-area-tooltip',
      });

      group.addLayer(poly);
    });
  }

  /* ── Renderiza máquinas com posição GPS ── */
  function renderMaquinas(group, maquinas) {
    maquinas.forEach(m => {
      /* Parseia posição GPS (pode ser "lat,lon" ou JSON) */
      let lat, lon;
      if (m.lat !== undefined) {
        lat = m.lat; lon = m.lon;
      } else if (m.localizacao_gps) {
        try {
          const parsed = JSON.parse(m.localizacao_gps);
          lat = parsed.lat || parsed[0]; lon = parsed.lon || parsed[1];
        } catch {
          const parts = m.localizacao_gps.split(',');
          if (parts.length === 2) { lat = parseFloat(parts[0]); lon = parseFloat(parts[1]); }
        }
      }
      if (!lat || !lon) return;

      const icon = makeIcon(maquinaSVG(m.tipo, m.status), [30, 30], [15, 15]);
      const marker = L.marker([lat, lon], { icon });
      marker.bindPopup(
        xMap.utils.popupHTML('🚜', m.nome, maqLabel(m.tipo), [
          ['Status',      m.status,                           statusClass(m.status)],
          ['Horas',       (m.horas_uso || 0) + ' h'],
          ['Combustível', (m.combustivel_atual || 0) + '%',   m.combustivel_atual < 20 ? 'warn' : 'ok'],
        ]),
        { maxWidth: 210 }
      );
      group.addLayer(marker);
    });
  }

  /* ── Definições de layers (com fetch real) ── */
  const layerDefs = {

    areas: {
      label: 'Áreas',
      color: '#4ade80',
      render(group) {
        fetch(`${API}/areas?ativa=1`)
          .then(r => r.ok ? r.json() : Promise.reject(r.status))
          .then(data => {
            renderAreas(group, data.filter(a => a.coords_json));
          })
          .catch(() => {
            /* Fallback para mock quando API offline */
            console.info('[xMap] xGrama offline — usando dados mock de áreas');
            renderAreas(group, MOCK_AREAS);
          });
      },
    },

    maquinas: {
      label: 'Máquinas',
      color: '#4ade80',
      render(group) {
        fetch(`${API}/maquinas?status=operacional`)
          .then(r => r.ok ? r.json() : Promise.reject(r.status))
          .then(data => {
            renderMaquinas(group, data.filter(m => m.localizacao_gps));
          })
          .catch(() => {
            console.info('[xMap] xGrama offline — usando dados mock de máquinas');
            renderMaquinas(group, MOCK_MAQUINAS);
          });
      },
    },

  };

  function tryRegister() {
    if (typeof xMap !== 'undefined' && xMap.registerLayer) {
      xMap.registerLayer('grama', layerDefs);
    } else {
      setTimeout(tryRegister, 50);
    }
  }
  tryRegister();

})();
