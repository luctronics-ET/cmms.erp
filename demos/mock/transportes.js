const MOCK = (() => {
  const iso = d => new Date(d).toISOString().slice(0, 10);
  const today = new Date();
  const plusD = n => iso(new Date(today.getTime() + n * 86400000));
  const b = (t, k) => ({ text: t, kind: k });
  return {
    modulo: 'pmoc_transportes', titulo: 'PMOC · Transportes', icon: '🚐',
    user: { nome: 'CF Almeida' },
    sync: { online: true, pending: 0, lastSync: new Date(Date.now() - 8*60000).toISOString() },
    kpis: [
      { label: 'Frota',          value: 12, sub: '8 viaturas + 4 embarc.' },
      { label: 'Viagens hoje',   value: 6, sub: '2 externas' },
      { label: 'Em manutenção',  value: 2, sub: 'S-10 + Lancha Natal' },
      { label: 'Próx. licenc.',  value: '45d', sub: 'Doblô' },
    ],
    donut: { title: 'Frota por categoria', data: [
      { label: 'VTR interna',  value: 4, color: 'var(--blue)' },
      { label: 'VTR externa',  value: 4, color: 'var(--green)' },
      { label: 'Emb. rotina',  value: 2, color: 'var(--amber)' },
      { label: 'Emb. patrulha',value: 2, color: 'var(--red)' },
    ]},
    line: { title: 'KM rodado por dia (Ilha das Flores) — semana',
      series: [{ label: 'km', points: [
        { x:1, y:120 }, { x:2, y:140 }, { x:3, y:110 }, { x:4, y:160 }, { x:5, y:135 }, { x:6, y:80 }, { x:7, y:90 },
      ] }],
    },
    ativos: {
      cols: [
        { key: 'nome', label: 'Identificação' },
        { key: 'tipo', label: 'Tipo', filter: true },
        { key: 'subtipo', label: 'Subtipo', filter: true },
        { key: 'placa', label: 'Placa/Casco' },
        { key: 'uso', label: 'km/h atual', format: v => engine.utils.fmt.num(v) },
        { key: 'status', label: 'Status',
          format: v => engine.badge(v.toUpperCase(),
            v === 'disponivel' ? 'green' : v === 'em_uso' ? 'blue' : v === 'manutencao' ? 'amber' : 'red') },
      ],
      rows: [
        { nome: 'S-10 Pickup',         tipo: 'VTR_PICKUP',   subtipo: 'vtr_int', placa: 'LRZ-5099', uso: 142800, status: 'manutencao' },
        { nome: 'MUNK XCMG (guindaste)', tipo: 'VTR_GUINDASTE', subtipo: 'vtr_int', placa: 'KPJ-8385', uso: 38400, status: 'disponivel' },
        { nome: 'Doblô 1.4',           tipo: 'VTR_SEDAN',    subtipo: 'vtr_ext', placa: 'XYZ-1234', uso: 88300, status: 'em_uso' },
        { nome: 'Ambulância',          tipo: 'VTR_PICKUP',   subtipo: 'vtr_ext', placa: 'ABC-9876', uso: 51200, status: 'disponivel' },
        { nome: 'Caminhão Constellation', tipo: 'VTR_CARGA', subtipo: 'vtr_ext', placa: 'CMS-0042', uso: 198000, status: 'disponivel' },
        { nome: 'ETPM Fátima (CMASM-08)',  tipo: 'EMB_LANCHA', subtipo: 'emb_rot', placa: 'CMASM-08', uso: 4200,  status: 'em_uso' },
        { nome: 'Lancha Natal (CMASM-05)', tipo: 'EMB_LANCHA', subtipo: 'emb_pat', placa: 'CMASM-05', uso: 2800,  status: 'manutencao' },
        { nome: 'Sgt Freitas (CMASM-10)',  tipo: 'EMB_BOTE',   subtipo: 'emb_pat', placa: 'CMASM-10', uso: 1450,  status: 'disponivel' },
      ],
    },
    kanban: { columns: [
      { id: 'agendada', title: 'Agendada' },
      { id: 'em_andamento', title: 'Em andamento' },
      { id: 'concluida', title: 'Concluída' },
      { id: 'cancelada', title: 'Cancelada' },
    ], cards: [
      { id: 'ot1', columnId: 'agendada',     title: 'Doblô → DCAM 08:30',     badges: [b('VTR EXT','blue')] },
      { id: 'ot2', columnId: 'agendada',     title: 'Ambulância → HNMD',      badges: [b('URGENTE','red')] },
      { id: 'ot3', columnId: 'em_andamento', title: 'ETPM Fátima · Ilha Flores 09:00', badges: [b('ROTINA','amber')] },
      { id: 'ot4', columnId: 'concluida',    title: 'MUNK · içar gerador',    badges: [b('OK','green')] },
    ]},
    calendar: { events: [
      { id: 'ct1', date: plusD(0), title: 'Doblô · DCAM' },
      { id: 'ct2', date: plusD(0), title: 'ETPM Fátima · 12 viagens', color: 'var(--amber)' },
      { id: 'ct3', date: plusD(2), title: 'Manut. S-10 (5000km)', color: 'var(--red)' },
      { id: 'ct4', date: plusD(7), title: 'Lancha Natal · sobreaviso', color: 'var(--blue)' },
    ]},
    gantt: {
      range: { start: iso(new Date(today.getFullYear(), today.getMonth(), 1)),
               end:   iso(new Date(today.getFullYear(), today.getMonth()+1, 0)) },
      tasks: [
        { id: 'gtt1', label: 'Revisão S-10', start: plusD(2), end: plusD(3), color: 'var(--red)' },
        { id: 'gtt2', label: 'Pintura Lancha Natal', start: plusD(5), end: plusD(12), color: 'var(--amber)' },
        { id: 'gtt3', label: 'Troca pneus Doblô', start: plusD(8), end: plusD(8), color: 'var(--blue)' },
      ],
    },
    chat: { currentUser: 'CF Almeida', messages: [
      { id: 'mt1', author: 'Cabo Lopes', text: 'CF, motorista da S-10 reportou ruído na suspensão.', ts: new Date(Date.now()-7200000).toISOString() },
      { id: 'mt2', author: 'CF Almeida', text: 'Recolhe e abre OS corretiva. Doblô assume rotas externas.', ts: new Date(Date.now()-7100000).toISOString() },
    ]},
    docs: {
      cols: [
        { key: 'nome', label: 'Documento' },
        { key: 'tipo', label: 'Tipo', filter: true },
        { key: 'data', label: 'Atualizado', format: v => engine.utils.fmt.date(v) },
      ],
      rows: [
        { nome: 'Papeleta 6 (modelo oficial)',          tipo: 'formulario', data: '2026-01-10' },
        { nome: 'POP — Inspeção pré-viagem viaturas',   tipo: 'pop',        data: '2026-03-04' },
        { nome: 'POP — Manutenção 5000km',              tipo: 'pop',        data: '2025-12-20' },
        { nome: 'Cronograma sobreaviso embarcações',    tipo: 'cronograma', data: '2026-05-01' },
      ],
    },
  };
})();
