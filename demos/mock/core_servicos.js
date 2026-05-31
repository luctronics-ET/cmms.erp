const MOCK = (() => {
  const b = (t, k) => ({ text: t, kind: k });
  return {
    modulo: 'core_servicos', titulo: 'Núcleo · Serviços', icon: '🧰',
    user: { nome: 'TC Freitas' },
    sync: { online: true, pending: 0, lastSync: new Date().toISOString() },
    kpis: [
      { label: 'OS abertas',     value: 14, sub: 'em 5 PMOCs' },
      { label: 'PS pendentes',   value: 6,  sub: 'aguardando autorização' },
      { label: 'SR pendentes',   value: 9,  sub: '4 material / 2 transp.' },
      { label: 'Concluídas (m)', value: 41, sub: 'mês atual' },
    ],
    donut: { title: 'OS por status (todos PMOCs)', data: [
      { label: 'Aberta',      value: 14, color: 'var(--blue)' },
      { label: 'Em execução', value: 8,  color: 'var(--amber)' },
      { label: 'Pronto',      value: 3,  color: 'var(--acc)' },
      { label: 'Concluída',   value: 41, color: 'var(--green)' },
      { label: 'Cancelada',   value: 2,  color: 'var(--red)' },
    ]},
    kanban: { columns: [
      { id: 'aberta', title: 'Aberta' }, { id: 'autorizada', title: 'Autorizada' },
      { id: 'iniciada', title: 'Iniciada' }, { id: 'em_execucao', title: 'Em execução' },
      { id: 'pronto', title: 'Pronto' }, { id: 'concluida', title: 'Concluída' },
    ], cards: [
      { id: 'cs1', columnId: 'aberta',      title: '[REFRIG] Limpeza AC-Sala-CIC',     badges: [b('URGENTE','red')] },
      { id: 'cs2', columnId: 'aberta',      title: '[ELET] Termografia QDG',           badges: [b('NR-10','amber')] },
      { id: 'cs3', columnId: 'autorizada',  title: '[PREDIAL] Reforma Sala 201',       badges: [b('PS-MAE','blue')] },
      { id: 'cs4', columnId: 'em_execucao', title: '[TRANSP] Manutenção S-10',         badges: [b('CORR','red')] },
      { id: 'cs5', columnId: 'em_execucao', title: '[GRAMA] Corte campo de honra',     badges: [b('ROTINA','green')] },
      { id: 'cs6', columnId: 'pronto',      title: '[REFRIG] Higienização Sala 201',   badges: [b('OK','green')] },
    ]},
  };
})();
