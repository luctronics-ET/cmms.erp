const MOCK = (() => {
  const iso = d => new Date(d).toISOString().slice(0, 10);
  const today = new Date();
  const plusD = n => iso(new Date(today.getTime() + n * 86400000));
  const b = (t, k) => ({ text: t, kind: k });
  return {
    modulo: 'pmoc_grama', titulo: 'PMOC · Controle Vegetal', icon: '🌱',
    user: { nome: 'Cabo Vieira' },
    sync: { online: true, pending: 0, lastSync: new Date(Date.now()-18*60000).toISOString() },
    kpis: [
      { label: 'Áreas',          value: 14, sub: '38.500 m²' },
      { label: 'Máquinas',       value: 12 },
      { label: 'Corte hoje',     value: '3 áreas' },
      { label: 'Próx. revisão',  value: 'FS220 #2', sub: '50h restantes' },
    ],
    donut: { title: 'Máquinas por tipo', data: [
      { label: 'FS220 (roçadeira)', value: 5, color: 'var(--green)' },
      { label: 'GAR (cortador)',    value: 3, color: 'var(--acc)' },
      { label: 'MS650 (motoserra)', value: 1, color: 'var(--amber)' },
      { label: 'TS114 (corte conc.)', value: 2, color: 'var(--blue)' },
      { label: 'SOL (trator)',      value: 1, color: 'var(--red)' },
    ]},
    line: { title: 'Horas cortadas/semana', series: [{ label: 'h', points: [
      { x:1, y:22 }, { x:2, y:28 }, { x:3, y:18 }, { x:4, y:32 }, { x:5, y:26 }, { x:6, y:8 },
    ] }]},
    ativos: {
      cols: [
        { key: 'nome', label: 'Máquina' },
        { key: 'tipo', label: 'Tipo', filter: true },
        { key: 'horimetro', label: 'Horímetro (h)', format: v => engine.utils.fmt.num(v, 1) },
        { key: 'proxima', label: 'Próx. manut.', format: v => engine.utils.fmt.date(v) },
        { key: 'condicao', label: 'Condição',
          format: v => engine.badge(v.toUpperCase(), v === 'boa' ? 'green' : v === 'atencao' ? 'amber' : 'red') },
      ],
      rows: [
        { nome: 'FS220 #1', tipo: 'FS220', horimetro: 142.5, proxima: plusD(15), condicao: 'boa' },
        { nome: 'FS220 #2', tipo: 'FS220', horimetro: 198.2, proxima: plusD(3),  condicao: 'atencao' },
        { nome: 'GAR #1',   tipo: 'GAR',   horimetro: 85.4,  proxima: plusD(28), condicao: 'boa' },
        { nome: 'MS650',    tipo: 'MS650', horimetro: 42.0,  proxima: plusD(45), condicao: 'boa' },
        { nome: 'SOL',      tipo: 'SOL',   horimetro: 220.1, proxima: plusD(-1), condicao: 'ruim' },
      ],
    },
    kanban: { columns: [
      { id: 'agendada', title: 'Agendada' },
      { id: 'em_andamento', title: 'Em andamento' },
      { id: 'concluida', title: 'Concluída' },
    ], cards: [
      { id: 'og1', columnId: 'agendada',     title: 'Corte Cais Norte (1200m²)',  badges: [b('ROTINA','green')] },
      { id: 'og2', columnId: 'em_andamento', title: 'Corte campo de honra',        badges: [b('FS220','blue')] },
      { id: 'og3', columnId: 'concluida',    title: 'Corte entrada principal',     badges: [b('OK','green')] },
    ]},
    calendar: { events: [
      { id: 'cg1', date: plusD(0), title: 'Corte Cais Norte' },
      { id: 'cg2', date: plusD(1), title: 'Corte campo de honra', color: 'var(--green)' },
      { id: 'cg3', date: plusD(3), title: 'Manut. FS220 #2', color: 'var(--amber)' },
      { id: 'cg4', date: plusD(7), title: 'Corte estacionamentos', color: 'var(--blue)' },
    ]},
    docs: { cols: [
      { key: 'nome', label: 'Documento' },
      { key: 'tipo', label: 'Tipo', filter: true },
    ], rows: [
      { nome: 'POP — Troca óleo 4T (50h)', tipo: 'pop' },
      { nome: 'POP — Afiação de lâminas',  tipo: 'pop' },
      { nome: 'Checklist pré-uso máquinas', tipo: 'checklist' },
    ]},
  };
})();
