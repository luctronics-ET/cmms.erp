/**
 * xMap Layers — xEletrica (Sistema Elétrico)
 * Elementos: geradores, transformadores, ramais principais, quadros de distribuição
 *
 * Módulo xEletrica ainda em desenvolvimento — dados são mock de planejamento.
 * Posições aproximadas dentro do perímetro da instalação.
 */

(function () {

  /* ── Dados mock de infraestrutura elétrica ── */
  const GERADORES = [
    { id: 'GE-01', nome: 'GE-01', lat: -22.8378, lon: -43.1088, kva: 250, estado: 'standby',     combustivel: 88, horasUso: 1240 },
    { id: 'GE-02', nome: 'GE-02', lat: -22.8385, lon: -43.1067, kva: 150, estado: 'operando',    combustivel: 62, horasUso: 876  },
    { id: 'GE-03', nome: 'GE-03', lat: -22.8455, lon: -43.1006, kva: 100, estado: 'manutencao',  combustivel: 0,  horasUso: 3200 },
  ];

  const TRANSFORMADORES = [
    { id: 'TR-01', nome: 'TR-01', lat: -22.8380, lon: -43.1082, kva: 500, tensao: '13.8kV/380V', estado: 'operando', carga_pct: 67 },
    { id: 'TR-02', nome: 'TR-02', lat: -22.8393, lon: -43.1073, kva: 300, tensao: '13.8kV/220V', estado: 'operando', carga_pct: 45 },
    { id: 'TR-03', nome: 'TR-03', lat: -22.8452, lon: -43.1005, kva: 200, tensao: '13.8kV/380V', estado: 'standby', carga_pct: 0  },
  ];

  const QUADROS = [
    { id: 'QD-01', nome: 'QD-Geral', lat: -22.8382, lon: -43.1084, tipo: 'geral',       estado: 'operando', circuitos: 24 },
    { id: 'QD-02', nome: 'QD-Adm',   lat: -22.8374, lon: -43.1086, tipo: 'distribuicao', estado: 'operando', circuitos: 12 },
    { id: 'QD-03', nome: 'QD-Ope',   lat: -22.8391, lon: -43.1069, tipo: 'distribuicao', estado: 'operando', circuitos: 16 },
    { id: 'QD-04', nome: 'QD-IF',    lat: -22.8454, lon: -43.1007, tipo: 'distribuicao', estado: 'alerta',   circuitos: 8  },
  ];

  const RAMAIS = [
    {
      id: 'RM-01', nome: 'Ramal Principal', tensao: '13.8kV', tipo: 'alta_tensao',
      coords: [[-22.8365,-43.1095],[-22.8380,-43.1082],[-22.8393,-43.1073]],
    },
    {
      id: 'RM-02', nome: 'Ramal IF', tensao: '13.8kV', tipo: 'alta_tensao',
      coords: [[-22.8393,-43.1073],[-22.8420,-43.1040],[-22.8452,-43.1005]],
    },
    {
      id: 'RM-03', nome: 'Ramal Adm', tensao: '380V', tipo: 'baixa_tensao',
      coords: [[-22.8380,-43.1082],[-22.8376,-43.1087],[-22.8374,-43.1086]],
    },
    {
      id: 'RM-04', nome: 'Ramal Ope', tensao: '220V', tipo: 'baixa_tensao',
      coords: [[-22.8393,-43.1073],[-22.8391,-43.1069]],
    },
  ];

  /* ── Helpers de cor/estilo ── */
  function estadoColor(estado) {
    switch (estado) {
      case 'operando':   return '#22c55e';
      case 'standby':    return '#38bdf8';
      case 'manutencao': return '#f59e0b';
      case 'alerta':     return '#ef4444';
      case 'inativo':    return '#4a6785';
      default:           return '#8fa8c8';
    }
  }

  function estadoClass(estado) {
    if (estado === 'operando') return 'ok';
    if (estado === 'alerta')   return 'error';
    if (estado === 'manutencao') return 'warn';
    return '';
  }

  function ramaisStyle(tipo) {
    if (tipo === 'alta_tensao') return { color: '#fbbf24', weight: 3, opacity: 0.8, dashArray: null };
    return { color: '#f97316', weight: 2, opacity: 0.65, dashArray: '6 3' };
  }

  function cargaClass(pct) {
    if (pct >= 80) return 'error';
    if (pct >= 60) return 'warn';
    return 'ok';
  }

  /* ── SVG Icons ── */
  function geradorSVG(estado, kva) {
    const c = estadoColor(estado);
    const spin = estado === 'operando';
    return `<svg xmlns="http://www.w3.org/2000/svg" width="34" height="34" viewBox="0 0 34 34">
      <rect x="2" y="2" width="30" height="30" rx="6" fill="rgba(7,17,31,.92)" stroke="${c}" stroke-width="2"/>
      <text x="17" y="14" text-anchor="middle" font-family="JetBrains Mono,monospace" font-size="7" fill="${c}" opacity=".6">GEN</text>
      <text x="17" y="24" text-anchor="middle" font-family="JetBrains Mono,monospace" font-size="8" font-weight="700" fill="${c}">${kva}kVA</text>
      ${spin ? `<circle cx="28" cy="6" r="3" fill="${c}"/>` : ''}
    </svg>`;
  }

  function trafoSVG(estado) {
    const c = estadoColor(estado);
    return `<svg xmlns="http://www.w3.org/2000/svg" width="30" height="30" viewBox="0 0 30 30">
      <rect x="2" y="2" width="26" height="26" rx="5" fill="rgba(7,17,31,.92)" stroke="${c}" stroke-width="2"/>
      <circle cx="10" cy="15" r="5" fill="none" stroke="${c}" stroke-width="1.5"/>
      <circle cx="20" cy="15" r="5" fill="none" stroke="${c}" stroke-width="1.5"/>
    </svg>`;
  }

  function quadroSVG(tipo, estado) {
    const c = estadoColor(estado);
    const isGeral = tipo === 'geral';
    return `<svg xmlns="http://www.w3.org/2000/svg" width="${isGeral ? 28 : 22}" height="${isGeral ? 28 : 22}" viewBox="0 0 28 28">
      <rect x="2" y="2" width="24" height="24" rx="3" fill="rgba(7,17,31,.92)" stroke="${c}" stroke-width="${isGeral ? 2 : 1.5}"/>
      <rect x="6" y="7"  width="6" height="3" rx="1" fill="${c}" opacity=".7"/>
      <rect x="6" y="12" width="6" height="3" rx="1" fill="${c}" opacity=".5"/>
      <rect x="16" y="7"  width="6" height="3" rx="1" fill="${c}" opacity=".7"/>
      <rect x="16" y="12" width="6" height="3" rx="1" fill="${c}" opacity=".5"/>
      <rect x="6" y="17" width="16" height="2" rx="1" fill="${c}" opacity=".3"/>
    </svg>`;
  }

  function makeIcon(svg, size, anchor) {
    return L.divIcon({ html: svg, className: '', iconSize: size, iconAnchor: anchor, popupAnchor: [0, -anchor[1]] });
  }

  /* ── Definições de layers ── */
  const layerDefs = {

    ramais: {
      label: 'Ramais',
      color: '#fbbf24',
      render(group) {
        RAMAIS.forEach(r => {
          const style = ramaisStyle(r.tipo);
          const line = L.polyline(r.coords, style);
          line.bindPopup(xMap.utils.popupHTML(
            '⚡', r.nome, r.tipo === 'alta_tensao' ? 'Alta Tensão' : 'Baixa Tensão',
            [
              ['Tensão', r.tensao, r.tipo === 'alta_tensao' ? 'warn' : 'info'],
            ]
          ), { maxWidth: 200 });
          group.addLayer(line);
        });
      },
    },

    geradores: {
      label: 'Geradores',
      color: '#22c55e',
      render(group) {
        GERADORES.forEach(g => {
          const icon = makeIcon(geradorSVG(g.estado, g.kva), [34, 34], [17, 17]);
          const marker = L.marker([g.lat, g.lon], { icon });
          marker.bindPopup(xMap.utils.popupHTML(
            '⚡', g.nome, 'Gerador',
            [
              ['Estado',      g.estado,          estadoClass(g.estado)],
              ['Potência',    g.kva + ' kVA'],
              ['Combustível', g.combustivel + '%', g.combustivel < 20 ? 'warn' : 'ok'],
              ['Horas',       g.horasUso + ' h'],
            ]
          ), { maxWidth: 220 });
          group.addLayer(marker);
        });
      },
    },

    transformadores: {
      label: 'Transformadores',
      color: '#fbbf24',
      render(group) {
        TRANSFORMADORES.forEach(t => {
          const icon = makeIcon(trafoSVG(t.estado), [30, 30], [15, 15]);
          const marker = L.marker([t.lat, t.lon], { icon });
          marker.bindPopup(xMap.utils.popupHTML(
            '🔌', t.nome, 'Transformador',
            [
              ['Estado',  t.estado,       estadoClass(t.estado)],
              ['Tensão',  t.tensao],
              ['Carga',   t.carga_pct + '%', cargaClass(t.carga_pct)],
              ['Cap.',    t.kva + ' kVA'],
            ]
          ), { maxWidth: 220 });
          group.addLayer(marker);
        });
      },
    },

    quadros: {
      label: 'Quadros',
      color: '#f97316',
      render(group) {
        QUADROS.forEach(q => {
          const sz = q.tipo === 'geral' ? 28 : 22;
          const icon = makeIcon(quadroSVG(q.tipo, q.estado), [sz, sz], [sz/2, sz/2]);
          const marker = L.marker([q.lat, q.lon], { icon });
          marker.bindPopup(xMap.utils.popupHTML(
            '🗄', q.nome, q.tipo === 'geral' ? 'Quadro Geral' : 'Quadro Distribuição',
            [
              ['Estado',    q.estado,          estadoClass(q.estado)],
              ['Circuitos', q.circuitos + ' circ.'],
            ]
          ), { maxWidth: 200 });
          group.addLayer(marker);
        });
      },
    },

  };

  function tryRegister() {
    if (typeof xMap !== 'undefined' && xMap.registerLayer) {
      xMap.registerLayer('eletrica', layerDefs);
    } else {
      setTimeout(tryRegister, 50);
    }
  }
  tryRegister();

})();
