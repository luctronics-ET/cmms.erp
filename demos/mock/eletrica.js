const MOCK = (() => {
  const iso = d => new Date(d).toISOString().slice(0, 10);
  const today = new Date();
  const plusD = n => iso(new Date(today.getTime() + n * 86400000));
  const b = (t, k) => ({ text: t, kind: k });
  return {
    modulo: 'pmoc_eletrica', titulo: 'PMOC · Elétrica', icon: '⚡',
    user: { nome: 'Sub Costa' },
    sync: { online: true, pending: 1, lastSync: new Date(Date.now() - 32 * 60000).toISOString() },
    kpis: [
      { label: 'Quadros',     value: 14, sub: '11 monitorados' },
      { label: 'Geradores',   value: 3,  sub: '1 em manutenção' },
      { label: 'OS abertas',  value: 2,  sub: '' },
      { label: 'Próx. NR-10', value: '60d', sub: 'inspeção anual' },
    ],
    donut: { title: 'OS por tipo', data: [
      { label: 'Preventiva', value: 7, color: 'var(--green)' },
      { label: 'Corretiva',  value: 3, color: 'var(--red)' },
      { label: 'Inspeção',   value: 4, color: 'var(--blue)' },
    ]},
    line: { title: 'Consumo (kWh/dia) — última semana',
      series: [{ label: 'kWh', points: [
        { x: 1, y: 320 }, { x: 2, y: 340 }, { x: 3, y: 295 },
        { x: 4, y: 410 }, { x: 5, y: 380 }, { x: 6, y: 240 }, { x: 7, y: 260 },
      ] }],
    },
    ativos: {
      cols: [
        { key: 'nome', label: 'Item' },
        { key: 'tipo', label: 'Tipo', filter: true },
        { key: 'local', label: 'Local', filter: true },
        { key: 'potencia', label: 'Pot. (kVA)' },
        { key: 'horas', label: 'Horas', format: v => engine.utils.fmt.num(v) },
      ],
      rows: [
        { nome: 'GMG-1 Caterpillar',  tipo: 'GERADOR', local: 'Casa de força', potencia: 150, horas: 2480 },
        { nome: 'GMG-2 Cummins',      tipo: 'GERADOR', local: 'CCM',           potencia: 200, horas: 1340 },
        { nome: 'QDG Principal',      tipo: 'QUADRO',  local: 'Casa de força', potencia: '—',  horas: '—' },
        { nome: 'No-break Sala CIC',  tipo: 'NOBREAK', local: 'CIC',           potencia: 5,   horas: 8200 },
        { nome: 'No-break TI',        tipo: 'NOBREAK', local: 'TI',            potencia: 10,  horas: 6100 },
      ],
    },
    kanban: { columns: [
      { id: 'aberta', title: 'Aberta' }, { id: 'iniciada', title: 'Iniciada' },
      { id: 'em_execucao', title: 'Em execução' }, { id: 'pronto', title: 'Pronto' }, { id: 'concluida', title: 'Concluída' },
    ], cards: [
      { id: 'oe1', columnId: 'aberta',      title: 'Troca filtro óleo GMG-1', badges: [b('250h','blue')] },
      { id: 'oe2', columnId: 'iniciada',    title: 'Termografia QDG',         badges: [b('NR-10','amber')] },
      { id: 'oe3', columnId: 'em_execucao', title: 'Inspeção semestral NO-break TI', badges: [b('INSP','blue')] },
      { id: 'oe4', columnId: 'pronto',      title: 'Aperto disjuntores Q-A2', badges: [b('OK','green')] },
    ]},
    calendar: { events: [
      { id: 'ce1', date: plusD(2),  title: 'GMG-1 troca óleo' },
      { id: 'ce2', date: plusD(7),  title: 'Termografia QDG', color: 'var(--amber)' },
      { id: 'ce3', date: plusD(14), title: 'Teste partida GMG-2', color: 'var(--green)' },
    ]},
    gantt: {
      range: { start: iso(new Date(today.getFullYear(), today.getMonth(), 1)),
               end:   iso(new Date(today.getFullYear(), today.getMonth()+1, 0)) },
      tasks: [
        { id: 'tge1', label: 'Manutenção GMG-1', start: plusD(2), end: plusD(3), color: 'var(--acc)' },
        { id: 'tge2', label: 'Termografia geral',start: plusD(7), end: plusD(10), color: 'var(--amber)' },
        { id: 'tge3', label: 'Substituir baterias no-break', start: plusD(15), end: plusD(16), color: 'var(--green)' },
      ],
    },
    chat: { currentUser: 'Sub Costa', messages: [
      { id: 'me1', author: '3SG Pereira', text: 'QDG com aquecimento no barramento.', ts: new Date(Date.now()-3600000).toISOString() },
      { id: 'me2', author: 'Sub Costa',   text: 'Confirma com termografia. Vou pedir parada da carga não-essencial.', ts: new Date(Date.now()-3300000).toISOString() },
    ]},
    docs: {
      cols: [
        { key: 'nome', label: 'Documento' },
        { key: 'tipo', label: 'Tipo', filter: true },
        { key: 'data', label: 'Atualizado', format: v => engine.utils.fmt.date(v) },
      ],
      rows: [
        { nome: 'POP — Manutenção GMG (250h)', tipo: 'pop', data: '2026-03-15' },
        { nome: 'POP — Inspeção termográfica', tipo: 'pop', data: '2026-01-22' },
        { nome: 'NR-10 — Procedimentos',       tipo: 'norma', data: '2025-09-10' },
      ],
    },
  };
})();
