/**
 * xMap Layers — xAguada (Monitoramento Hídrico)
 * Elementos: reservatórios, bombas, válvulas, hidrômetros, tubulações, ETE
 *
 * Dados baseados em infra.json do aguada-web.
 * Em produção, buscar via fetch('/api/...') e chamar xMap.updateElement().
 */

(function () {
  /* ── Dados de infraestrutura (mock baseado em infra.json real) ── */
  const INFRA = {
    reservoirs: [
      { id: 'CON',   name: 'CON',   lat: -22.8382228, lon: -43.1080717, capacity: 80, pct: 72, online: true,  volume_l: 57600 },
      { id: 'CB03',  name: 'CB03',  lat: -22.8384676, lon: -43.1083677, capacity: 80, pct: 58, online: true,  volume_l: 46400 },
      { id: 'CIE',   name: 'CIE',   lat: -22.838998,  lon: -43.1080397, capacity: 80, pct: 85, online: true,  volume_l: 68000 },
      { id: 'CAV',   name: 'CAV',   lat: -22.8370714, lon: -43.1093764, capacity: 80, pct: 33, online: false, volume_l: 26400 },
      { id: 'CBIF',  name: 'CBIF',  lat: -22.8453673, lon: -43.1004556, capacity: 80, pct: 91, online: true,  volume_l: 72800 },
    ],
    pumps: [
      { id: 'CB01', name: 'CB01', lat: -22.8398413, lon: -43.1075282, state: 'ligada',    mode: 'auto' },
      { id: 'CB02', name: 'CB02', lat: -22.8379227, lon: -43.1090019, state: 'desligada', mode: 'manual' },
    ],
    valves: [
      { id: 'V-CON-IN',   name: 'V-CON-IN',   lat: -22.8382981, lon: -43.1081786, state: 'aberta'  },
      { id: 'V-CON-OUT',  name: 'V-CON-OUT',  lat: -22.8382645, lon: -43.1081691, state: 'fechada' },
      { id: 'V-CAV-IN',   name: 'V-CAV-IN',   lat: -22.837102,  lon: -43.1092269, state: 'aberta'  },
      { id: 'V-CAV-OUT',  name: 'V-CAV-OUT',  lat: -22.8372611, lon: -43.1092268, state: 'aberta'  },
      { id: 'V-CIE-IN',   name: 'V-CIE-IN',   lat: -22.8390359, lon: -43.1079857, state: 'aberta'  },
      { id: 'V-CIE-OUT',  name: 'V-CIE-OUT',  lat: -22.8389134, lon: -43.1080688, state: 'falha'   },
      { id: 'V-CB03-IN',  name: 'V-CB03-IN',  lat: -22.83851,   lon: -43.1083444, state: 'fechada' },
      { id: 'V-CB03-OUT', name: 'V-CB03-OUT', lat: -22.8384262, lon: -43.1083955, state: 'aberta'  },
      { id: 'V-IE-IN',    name: 'V-IE-IN',    lat: -22.8387801, lon: -43.1062243, state: 'aberta'  },
    ],
    hydrometers: [
      { id: 'HID-AV',    name: 'HID-AV',    lat: -22.8382061, lon: -43.1079094, reading: 14823.5, unit: 'm³' },
      { id: 'HID-AZ',    name: 'HID-AZ',    lat: -22.8382524, lon: -43.1079085, reading: 9241.2,  unit: 'm³' },
      { id: 'HID-PRAIA', name: 'HID-PRAIA', lat: -22.8387264, lon: -43.1062263, reading: 3102.8,  unit: 'm³' },
      { id: 'HID-IF',    name: 'HID-IF',    lat: -22.8453336, lon: -43.1004551, reading: 5670.1,  unit: 'm³' },
    ],
    sanitation: [
      { id: 'ETE-01',  name: 'ETE',            lat: -22.8402,    lon: -43.1021,    type: 'ete',   state: 'operacional' },
      { id: 'FS-01',   name: 'Fossa Séptica',   lat: -22.8395,    lon: -43.1035,    type: 'fossa', state: 'operacional' },
      { id: 'CG-01',   name: 'Cx. de Gordura',  lat: -22.8388,    lon: -43.1048,    type: 'caixa', state: 'manutencao'  },
    ],
    pipelines: [
      {
        id: 'main-1', submarine: true, diameter: 500, substance: 'water',
        coords: [[-22.8429112,-43.0995975],[-22.8405209,-43.1036951],[-22.8387801,-43.1062243]],
      },
      {
        id: 'main-2', submarine: false, diameter: 300, substance: 'water',
        coords: [[-22.8387801,-43.1062243],[-22.8384676,-43.1083677],[-22.8382228,-43.1080717]],
      },
      {
        id: 'main-3', submarine: false, diameter: 200, substance: 'water',
        coords: [[-22.8382228,-43.1080717],[-22.8370714,-43.1093764]],
      },
      {
        id: 'main-4', submarine: false, diameter: 150, substance: 'water',
        coords: [[-22.8384676,-43.1083677],[-22.838998,-43.1080397]],
      },
      {
        id: 'main-5', submarine: false, diameter: 250, substance: 'water',
        coords: [[-22.8398413,-43.1075282],[-22.8453673,-43.1004556]],
      },
    ],
  };

  /* ── Helpers visuais ── */
  function pctColor(pct) {
    if (pct >= 70) return '#22c55e';
    if (pct >= 30) return '#f59e0b';
    return '#ef4444';
  }

  function pctClass(pct) {
    if (pct >= 70) return 'ok';
    if (pct >= 30) return 'warn';
    return 'error';
  }

  function stateColor(state) {
    switch (state) {
      case 'aberta':       return '#22c55e';
      case 'fechada':      return '#8fa8c8';
      case 'parcial':      return '#f59e0b';
      case 'falha':        return '#ef4444';
      case 'ligada':       return '#22c55e';
      case 'desligada':    return '#4a6785';
      case 'manutencao':   return '#f59e0b';
      case 'operacional':  return '#22c55e';
      default:             return '#8fa8c8';
    }
  }

  function stateClass(state) {
    if (['aberta','ligada','operacional'].includes(state)) return 'ok';
    if (['falha'].includes(state))                         return 'error';
    if (['parcial','manutencao'].includes(state))          return 'warn';
    return '';
  }

  /* ── SVG Icons ── */
  function reservoirSVG(pct, online) {
    const c = online ? pctColor(pct) : '#4a6785';
    const fill = online ? pct : 0;
    return `<svg xmlns="http://www.w3.org/2000/svg" width="36" height="36" viewBox="0 0 36 36">
      <rect x="4" y="4" width="28" height="28" rx="5" fill="rgba(7,17,31,.9)" stroke="${c}" stroke-width="2"/>
      <rect x="7" y="${7 + (22 - 22*fill/100)}" width="22" height="${22*fill/100}" rx="2" fill="${c}" opacity=".55"/>
      <text x="18" y="21" text-anchor="middle" font-family="JetBrains Mono,monospace" font-size="8" font-weight="700" fill="${c}">${online ? fill+'%' : 'OFF'}</text>
      ${!online ? `<line x1="4" y1="4" x2="32" y2="32" stroke="#ef4444" stroke-width="1.5" opacity=".5"/>` : ''}
    </svg>`;
  }

  function pumpSVG(state) {
    const c = stateColor(state);
    return `<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32">
      <circle cx="16" cy="16" r="13" fill="rgba(7,17,31,.9)" stroke="${c}" stroke-width="2"/>
      <path d="M10 16 L22 16 M16 10 L16 22" stroke="${c}" stroke-width="2" stroke-linecap="round"/>
      <circle cx="16" cy="16" r="3" fill="${c}"/>
    </svg>`;
  }

  function valveSVG(state) {
    const c = stateColor(state);
    const open = state === 'aberta';
    return `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 20 20">
      <rect x="2" y="2" width="16" height="16" rx="3" fill="rgba(7,17,31,.9)" stroke="${c}" stroke-width="1.5"/>
      ${open
        ? `<rect x="5" y="9" width="10" height="2" fill="${c}" rx="1"/>`
        : `<rect x="9" y="5" width="2" height="10" fill="${c}" rx="1"/><rect x="5" y="9" width="10" height="2" fill="${c}" opacity=".3" rx="1"/>`
      }
    </svg>`;
  }

  function hydrometerSVG() {
    return `<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 22 22">
      <circle cx="11" cy="11" r="9" fill="rgba(7,17,31,.9)" stroke="#38bdf8" stroke-width="1.5"/>
      <text x="11" y="14" text-anchor="middle" font-family="JetBrains Mono,monospace" font-size="7" font-weight="700" fill="#38bdf8">㎥</text>
    </svg>`;
  }

  function sanitationSVG(type, state) {
    const c = stateColor(state);
    const icon = type === 'ete' ? '♻' : type === 'fossa' ? '⬡' : '⬤';
    return `<svg xmlns="http://www.w3.org/2000/svg" width="26" height="26" viewBox="0 0 26 26">
      <rect x="2" y="2" width="22" height="22" rx="4" fill="rgba(7,17,31,.9)" stroke="${c}" stroke-width="1.5"/>
      <text x="13" y="17" text-anchor="middle" font-size="12" fill="${c}">${icon}</text>
    </svg>`;
  }

  /* ── Criação de markers com Leaflet divIcon ── */
  function makeIcon(svgStr, size, anchor) {
    return L.divIcon({ html: svgStr, className: '', iconSize: size, iconAnchor: anchor, popupAnchor: [0, -anchor[1]] });
  }

  /* ── Definições de layers ── */
  const layerDefs = {

    pipelines: {
      label: 'Tubulações',
      color: '#38bdf8',
      render(group) {
        INFRA.pipelines.forEach(pipe => {
          const color = pipe.submarine ? '#0ea5e9' : '#38bdf8';
          const dashArray = pipe.submarine ? '8 4' : null;
          const weight = pipe.diameter >= 400 ? 4 : pipe.diameter >= 200 ? 3 : 2;
          const line = L.polyline(pipe.coords, {
            color,
            weight,
            opacity: 0.75,
            dashArray,
          });
          line.bindPopup(xMap.utils.popupHTML(
            '〜', pipe.id, pipe.submarine ? 'Tubulação Submarina' : 'Tubulação',
            [
              ['Diâmetro', pipe.diameter + ' mm'],
              ['Tipo', pipe.submarine ? 'Submarina' : 'Superfície'],
              ['Substância', pipe.substance],
            ]
          ), { maxWidth: 220 });
          group.addLayer(line);
        });
      },
    },

    reservoirs: {
      label: 'Reservatórios',
      color: '#22c55e',
      render(group) {
        INFRA.reservoirs.forEach(r => {
          const icon = makeIcon(reservoirSVG(r.pct, r.online), [36, 36], [18, 18]);
          const marker = L.marker([r.lat, r.lon], { icon });
          marker.bindPopup(xMap.utils.popupHTML(
            '🛢', r.name, 'Reservatório',
            [
              ['Nível', r.pct + '%', pctClass(r.pct)],
              ['Volume', (r.volume_l / 1000).toFixed(1) + ' m³'],
              ['Cap.', r.capacity + ' m³'],
              ['Status', r.online ? 'Online' : 'Offline', r.online ? 'ok' : 'error'],
            ]
          ), { maxWidth: 220 });
          group.addLayer(marker);
        });
      },
    },

    pumps: {
      label: 'Bombas',
      color: '#0ea5e9',
      render(group) {
        INFRA.pumps.forEach(p => {
          const icon = makeIcon(pumpSVG(p.state), [32, 32], [16, 16]);
          const marker = L.marker([p.lat, p.lon], { icon });
          marker.bindPopup(xMap.utils.popupHTML(
            '⚙', p.name, 'Casa de Bombas',
            [
              ['Estado', p.state, stateClass(p.state)],
              ['Modo', p.mode],
            ]
          ), { maxWidth: 200 });
          group.addLayer(marker);
        });
      },
    },

    valves: {
      label: 'Válvulas',
      color: '#f59e0b',
      render(group) {
        INFRA.valves.forEach(v => {
          const icon = makeIcon(valveSVG(v.state), [20, 20], [10, 10]);
          const marker = L.marker([v.lat, v.lon], { icon });
          marker.bindPopup(xMap.utils.popupHTML(
            '⊕', v.name, 'Válvula',
            [
              ['Estado', v.state, stateClass(v.state)],
            ]
          ), { maxWidth: 180 });
          group.addLayer(marker);
        });
      },
    },

    hydrometers: {
      label: 'Hidrômetros',
      color: '#38bdf8',
      render(group) {
        INFRA.hydrometers.forEach(h => {
          const icon = makeIcon(hydrometerSVG(), [22, 22], [11, 11]);
          const marker = L.marker([h.lat, h.lon], { icon });
          marker.bindPopup(xMap.utils.popupHTML(
            '💧', h.name, 'Hidrômetro',
            [
              ['Leitura', h.reading.toFixed(1) + ' ' + h.unit, 'info'],
            ]
          ), { maxWidth: 180 });
          group.addLayer(marker);
        });
      },
    },

    sanitation: {
      label: 'Saneamento',
      color: '#4ade80',
      render(group) {
        INFRA.sanitation.forEach(s => {
          const icon = makeIcon(sanitationSVG(s.type, s.state), [26, 26], [13, 13]);
          const marker = L.marker([s.lat, s.lon], { icon });
          marker.bindPopup(xMap.utils.popupHTML(
            '♻', s.name, s.type.toUpperCase(),
            [
              ['Status', s.state, stateClass(s.state)],
            ]
          ), { maxWidth: 180 });
          group.addLayer(marker);
        });
      },
    },

  };

  /* ── Registra quando xMap estiver pronto ── */
  function tryRegister() {
    if (typeof xMap !== 'undefined' && xMap.registerLayer) {
      xMap.registerLayer('aguada', layerDefs);
    } else {
      setTimeout(tryRegister, 50);
    }
  }
  tryRegister();

})();
