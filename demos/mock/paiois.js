const MOCK = (() => {
  const iso = d => new Date(d).toISOString().slice(0, 10);
  const today = new Date();
  const plusD = n => iso(new Date(today.getTime() + n * 86400000));
  const b = (t, k) => ({ text: t, kind: k });
  return {
    modulo: 'pmoc_paiois', titulo: 'PMOC · Paiois', icon: '🛡️',
    user: { nome: '1T Marques' },
    sync: { online: false, pending: 4, lastSync: new Date(Date.now()-2*3600000).toISOString() },
    kpis: [
      { label: 'Paiois',          value: 4 },
      { label: 'Itens',           value: 1248, sub: 'sob controle' },
      { label: 'Valid. < 30d',    value: 6,    sub: 'atenção' },
      { label: 'Acessos hoje',    value: 12 },
    ],
    donut: { title: 'Itens por categoria', data: [
      { label: 'Munição',     value: 540, color: 'var(--red)' },
      { label: 'Sobressalente', value: 360, color: 'var(--blue)' },
      { label: 'EPI',         value: 220, color: 'var(--green)' },
      { label: 'Outros',      value: 128, color: 'var(--amber)' },
    ]},
    line: { title: 'Movimentações/dia (semana)', series: [{ label: 'qtd', points: [
      { x:1, y:18 }, { x:2, y:22 }, { x:3, y:14 }, { x:4, y:30 }, { x:5, y:26 }, { x:6, y:8 }, { x:7, y:6 },
    ] }]},
    ativos: {
      cols: [
        { key: 'codigo', label: 'Código' },
        { key: 'nome', label: 'Item' },
        { key: 'paiol', label: 'Paiol', filter: true },
        { key: 'qtd', label: 'Qtd' },
        { key: 'min', label: 'Mín' },
        { key: 'validade', label: 'Validade', format: v => v ? engine.utils.fmt.date(v) : '—' },
        { key: 'alerta', label: 'Alerta',
          format: v => v ? engine.badge(v.toUpperCase(), v === 'baixo' ? 'amber' : v === 'vencendo' ? 'red' : 'green') : '' },
      ],
      rows: [
        { codigo: 'MUN-9MM-S',  nome: '9mm Subsônico',         paiol: 'Paiol 3',  qtd: 800, min: 200, validade: plusD(180), alerta: 'ok' },
        { codigo: 'MUN-12-CAL', nome: '12 calibre',            paiol: 'Paiol 3',  qtd: 120, min: 100, validade: plusD(20),  alerta: 'vencendo' },
        { codigo: 'SOB-IMP-LN', nome: 'Impeller Lancha Natal', paiol: 'Paiol 1',  qtd: 1,   min: 2,   validade: null, alerta: 'baixo' },
        { codigo: 'EPI-COL-NB', nome: 'Colete balístico NB',   paiol: 'Paiol 2',  qtd: 24,  min: 10,  validade: plusD(740), alerta: 'ok' },
      ],
    },
    kanban: { columns: [
      { id: 'pendente', title: 'Pendente sync' },
      { id: 'em_andamento', title: 'Em andamento' },
      { id: 'concluida', title: 'Concluída' },
    ], cards: [
      { id: 'opa1', columnId: 'pendente',     title: 'Saída 50× 9mm para treinamento',     badges: [b('PUSH','amber')] },
      { id: 'opa2', columnId: 'pendente',     title: 'Acesso Paiol 3 (2T Soares)',         badges: [b('LOG','blue')] },
      { id: 'opa3', columnId: 'em_andamento', title: 'Recontagem impeller (inventário)',   badges: [b('AJUSTE','blue')] },
      { id: 'opa4', columnId: 'concluida',    title: 'Entrada 120× cartucho 12 calibre',   badges: [b('NF-2241','green')] },
    ]},
    calendar: { events: [
      { id: 'cpa1', date: plusD(0), title: '6× itens vencem (12 calibre)', color: 'var(--red)' },
      { id: 'cpa2', date: plusD(5), title: 'Inventário mensal Paiol 3', color: 'var(--blue)' },
    ]},
    chat: { currentUser: '1T Marques', messages: [
      { id: 'mpa1', author: 'Aspirante Reis', text: 'Pegando colete NB para treinamento de hoje.', ts: new Date(Date.now()-7200000).toISOString() },
      { id: 'mpa2', author: '1T Marques',     text: 'OK, registrei. Devolve até 18h.', ts: new Date(Date.now()-7000000).toISOString() },
    ]},
    docs: { cols: [
      { key: 'nome', label: 'Documento' },
      { key: 'tipo', label: 'Tipo', filter: true },
    ], rows: [
      { nome: 'Norma de Controle de Acesso (paiois)', tipo: 'norma' },
      { nome: 'Procedimento de inventário mensal',    tipo: 'pop' },
      { nome: 'Checklist saída/retorno de material',  tipo: 'checklist' },
    ]},
  };
})();
