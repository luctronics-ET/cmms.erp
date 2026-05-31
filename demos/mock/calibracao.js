const MOCK = (() => {
  const iso = d => new Date(d).toISOString().slice(0, 10);
  const today = new Date();
  const plusD = n => iso(new Date(today.getTime() + n * 86400000));
  return {
    modulo: 'pmoc_calibracao', titulo: 'PMOC · Calibração', icon: '📐',
    user: { nome: 'TC Ribeiro' },
    sync: { online: true, pending: 0, lastSync: new Date(Date.now()-45*60000).toISOString() },
    kpis: [
      { label: 'Instrumentos', value: 67, sub: 'sob controle' },
      { label: 'Vencidos',     value: 3,  sub: 'recalibrar' },
      { label: 'Próx. 30d',    value: 8,  sub: 'planejar envio' },
      { label: 'Setores',      value: 3,  sub: 'GAMI / GAS / GM' },
    ],
    donut: { title: 'Status', data: [
      { label: 'Válida',        value: 56, color: 'var(--green)' },
      { label: 'Vencendo (30d)', value: 8,  color: 'var(--amber)' },
      { label: 'Vencida',       value: 3,  color: 'var(--red)' },
    ]},
    line: { title: 'Calibrações realizadas/mês (12m)', series: [{ label: 'qtd', points: [
      { x:1, y:6 }, { x:2, y:8 }, { x:3, y:5 }, { x:4, y:9 },
      { x:5, y:7 }, { x:6, y:11 }, { x:7, y:9 }, { x:8, y:6 },
      { x:9, y:7 }, { x:10, y:5 }, { x:11, y:8 }, { x:12, y:10 },
    ] }]},
    ativos: {
      cols: [
        { key: 'tag', label: 'TAG' },
        { key: 'nome', label: 'Instrumento' },
        { key: 'setor', label: 'Setor', filter: true },
        { key: 'fabricante', label: 'Fabricante' },
        { key: 'valida_ate', label: 'Validade', format: v => engine.utils.fmt.date(v) },
        { key: 'status', label: 'Status',
          format: v => engine.badge(v.toUpperCase(),
            v === 'valida' ? 'green' : v === 'vencendo' ? 'amber' : 'red') },
      ],
      rows: [
        { tag: 'GAMI-001', nome: 'Multímetro Fluke 87V',     setor: 'GAMI', fabricante: 'Fluke',  valida_ate: plusD(140), status: 'valida' },
        { tag: 'GAMI-002', nome: 'Osciloscópio Tek MDO3024', setor: 'GAMI', fabricante: 'Tektronix', valida_ate: plusD(28),  status: 'vencendo' },
        { tag: 'GAS-014',  nome: 'Manômetro digital Aleas',  setor: 'GAS',  fabricante: 'Aleas',  valida_ate: plusD(-12), status: 'vencida' },
        { tag: 'GM-007',   nome: 'Paquímetro Mitutoyo 300mm', setor: 'GM',  fabricante: 'Mitutoyo', valida_ate: plusD(60),  status: 'valida' },
        { tag: 'GM-019',   nome: 'Torquímetro Tonichi 200N·m', setor: 'GM', fabricante: 'Tohnichi', valida_ate: plusD(-3),  status: 'vencida' },
      ],
    },
    calendar: { events: [
      { id: 'ck1', date: plusD(0),  title: '2 instr. vencidos (GAS)', color: 'var(--red)' },
      { id: 'ck2', date: plusD(28), title: 'Oscilo Tek vence',         color: 'var(--amber)' },
      { id: 'ck3', date: plusD(60), title: 'Paquímetro GM vence',     color: 'var(--blue)' },
    ]},
    docs: { cols: [
      { key: 'nome', label: 'Documento' },
      { key: 'tipo', label: 'Tipo', filter: true },
    ], rows: [
      { nome: 'Certificado RBC — GAMI-001 (2026)', tipo: 'certificado' },
      { nome: 'Procedimento envio para calibração', tipo: 'pop' },
      { nome: 'ISO/IEC 17025 (resumo)',             tipo: 'norma' },
    ]},
  };
})();
