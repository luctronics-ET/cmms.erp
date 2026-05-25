const MOCK = (() => {
  const iso = d => new Date(d).toISOString().slice(0, 10);
  const today = new Date();
  const plusD = n => iso(new Date(today.getTime() + n * 86400000));
  const b = (t, k) => ({ text: t, kind: k });
  return {
    modulo: 'pmoc_predial', titulo: 'PMOC · Predial', icon: '🏛️',
    user: { nome: '2T Soares' },
    sync: { online: true, pending: 0, lastSync: new Date(Date.now()-3600000).toISOString() },
    kpis: [
      { label: 'Edificações', value: 8, sub: '5 ADM / 3 OPE' },
      { label: 'Locais',      value: 64, sub: 'salas, áreas, paiois' },
      { label: 'Ocorrências', value: 7, sub: '3 abertas' },
      { label: 'Inspeções',   value: '12/m', sub: 'meta cumprida' },
    ],
    donut: { title: 'Ocorrências por tipo', data: [
      { label: 'Infiltração', value: 3, color: 'var(--blue)' },
      { label: 'Elétrica',    value: 2, color: 'var(--amber)' },
      { label: 'Hidráulica',  value: 1, color: 'var(--red)' },
      { label: 'Outras',      value: 1, color: 'var(--green)' },
    ]},
    line: { title: 'Ocorrências/mês', series: [{ label: 'qtd', points: [
      { x:1, y:5 }, { x:2, y:7 }, { x:3, y:3 }, { x:4, y:6 }, { x:5, y:7 }, { x:6, y:4 },
    ] }]},
    ativos: {
      cols: [
        { key: 'nome', label: 'Local' },
        { key: 'tipo', label: 'Tipo', filter: true },
        { key: 'edif', label: 'Edificação', filter: true },
        { key: 'area', label: 'Área (m²)', format: v => engine.utils.fmt.num(v) },
        { key: 'restricao', label: 'Restrição', filter: true },
      ],
      rows: [
        { nome: 'Sala 201',    tipo: 'sala',          edif: 'Bloco A', area: 24,  restricao: 'civil' },
        { nome: 'Auditório',   tipo: 'sala',          edif: 'Aud. CMASM', area: 180, restricao: 'civil' },
        { nome: 'Paiol 3',     tipo: 'paiol',         edif: 'Paiois',  area: 60,  restricao: 'reservado' },
        { nome: 'Cais Norte',  tipo: 'area_externa',  edif: 'Cais',    area: 400, restricao: 'militar' },
        { nome: 'CIC',         tipo: 'sala',          edif: 'Operações', area: 80, restricao: 'reservado' },
        { nome: 'Refeitório',  tipo: 'sala',          edif: 'Bloco B', area: 120, restricao: 'civil' },
      ],
    },
    kanban: { columns: [
      { id: 'aberta', title: 'Aberta' }, { id: 'iniciada', title: 'Iniciada' },
      { id: 'em_execucao', title: 'Em execução' }, { id: 'concluida', title: 'Concluída' },
    ], cards: [
      { id: 'op1', columnId: 'aberta',      title: 'Infiltração teto Sala 201',  badges: [b('OCO','red'), b('CHUVA','blue')] },
      { id: 'op2', columnId: 'iniciada',    title: 'Pintura Sala 202',           badges: [b('PREVENT','green')] },
      { id: 'op3', columnId: 'em_execucao', title: 'Inspeção mensal predial',    badges: [b('INSP','blue')] },
    ]},
    calendar: { events: [
      { id: 'cp1', date: plusD(1), title: 'Inspeção Bloco A' },
      { id: 'cp2', date: plusD(3), title: 'Reparo Sala 201', color: 'var(--red)' },
      { id: 'cp3', date: plusD(7), title: 'Pintura Sala 202', color: 'var(--green)' },
    ]},
    chat: { currentUser: '2T Soares', messages: [
      { id: 'mp1', author: 'Solicitante (Adm)', text: 'Infiltração no teto da Sala 201 piorou com a chuva.', ts: new Date(Date.now()-86400000).toISOString() },
      { id: 'mp2', author: '2T Soares', text: 'Abri OS corretiva. Inspeção visual amanhã.', ts: new Date(Date.now()-82800000).toISOString() },
    ]},
    docs: { cols: [
      { key: 'nome', label: 'Documento' },
      { key: 'tipo', label: 'Tipo', filter: true },
    ], rows: [
      { nome: 'Checklist inspeção predial mensal', tipo: 'checklist' },
      { nome: 'POP — Reparo de infiltrações',      tipo: 'pop' },
      { nome: 'Planta baixa CMASM (PDF)',           tipo: 'planta' },
    ]},
  };
})();
