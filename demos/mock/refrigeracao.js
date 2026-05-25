const MOCK = (() => {
  const today = new Date();
  const iso = d => new Date(d).toISOString().slice(0, 10);
  const plusD = n => iso(new Date(today.getTime() + n * 86400000));
  const b = (t, k) => ({ text: t, kind: k });
  return {
    modulo: 'pmoc_refrigeracao', titulo: 'PMOC · Refrigeração', icon: '❄️',
    user: { nome: 'Cb Silva' },
    sync: { online: true, pending: 0, lastSync: new Date(Date.now() - 12 * 60000).toISOString() },
    kpis: [
      { label: 'Ativos',          value: 28, sub: '24 ativos / 4 arquivados' },
      { label: 'OS abertas',      value: 4,  sub: '1 urgente' },
      { label: 'Manut. vencidas', value: 3,  sub: 'precisa intervenção' },
      { label: 'Estoque baixo',   value: 2,  sub: 'gás R-410A, filtros' },
    ],
    donut: {
      title: 'OS por status',
      data: [
        { label: 'Aberta',      value: 4, color: 'var(--blue)' },
        { label: 'Em execução', value: 2, color: 'var(--amber)' },
        { label: 'Concluída',   value: 9, color: 'var(--green)' },
      ],
      totalLabel: 'OS · mês',
    },
    line: {
      title: 'Manutenções/mês — últimos 6 meses',
      series: [{ label: 'Concluídas', points: [
        { x: 1, y: 6 }, { x: 2, y: 8 }, { x: 3, y: 5 },
        { x: 4, y: 9 }, { x: 5, y: 7 }, { x: 6, y: 11 },
      ] }],
    },
    ativos: {
      cols: [
        { key: 'nome', label: 'Equipamento' },
        { key: 'tipo', label: 'Tipo', filter: true },
        { key: 'local', label: 'Local', filter: true },
        { key: 'criticidade', label: 'Criticidade', filter: true,
          format: v => engine.badge(v, v === 'critico_24x7' ? 'red' : v === 'operacional' ? 'amber' : 'green') },
        { key: 'btu', label: 'BTU' },
        { key: 'prox', label: 'Próx. serviço', format: v => engine.utils.fmt.date(v) },
        { key: 'status', label: 'Status',
          format: v => engine.badge(v.toUpperCase(),
            v === 'vencida' ? 'red' : v === 'proxima' ? 'amber' : 'green') },
      ],
      rows: [
        { nome: 'AC-Sala-201',    tipo: 'AC_SPLIT',   local: 'Adm Bloco A', criticidade: 'operacional',   btu: 12000, prox: plusD(8),   status: 'ok' },
        { nome: 'AC-Sala-CIC',    tipo: 'AC_SPLIT',   local: 'CIC',         criticidade: 'critico_24x7', btu: 18000, prox: plusD(-2),  status: 'vencida' },
        { nome: 'AC-Auditório',   tipo: 'AC_CENTRAL', local: 'Aud. CMASM',  criticidade: 'admin',        btu: 60000, prox: plusD(40),  status: 'ok' },
        { nome: 'AC-Sala-202',    tipo: 'AC_SPLIT',   local: 'Adm Bloco A', criticidade: 'operacional',   btu: 9000,  prox: plusD(3),   status: 'proxima' },
        { nome: 'AC-Refeitório',  tipo: 'AC_SPLIT',   local: 'Refeitório',  criticidade: 'operacional',   btu: 30000, prox: plusD(15),  status: 'ok' },
        { nome: 'AC-Paiol-3',     tipo: 'AC_SPLIT',   local: 'Paiol 3',     criticidade: 'critico_24x7', btu: 12000, prox: plusD(0),   status: 'vencida' },
        { nome: 'AC-CCM',         tipo: 'AC_CENTRAL', local: 'CCM',         criticidade: 'critico_24x7', btu: 90000, prox: plusD(22),  status: 'ok' },
        { nome: 'AC-Vest-Mas',    tipo: 'AC_SPLIT',   local: 'Vestiários',  criticidade: 'admin',        btu: 9000,  prox: plusD(60),  status: 'ok' },
      ],
    },
    kanban: {
      columns: [
        { id: 'aberta', title: 'Aberta' },
        { id: 'iniciada', title: 'Iniciada' },
        { id: 'em_execucao', title: 'Em execução' },
        { id: 'pronto', title: 'Pronto' },
        { id: 'concluida', title: 'Concluída' },
      ],
      cards: [
        { id: 'os-r1', columnId: 'aberta',      title: 'Limpeza AC-Sala-CIC',     badges: [b('URGENTE','red'), b('SPLIT','blue')] },
        { id: 'os-r2', columnId: 'aberta',      title: 'Troca gás AC-Sala-202',   badges: [b('PREV','green')] },
        { id: 'os-r3', columnId: 'iniciada',    title: 'Inspeção AC-Auditório',   badges: [b('INSP','blue')] },
        { id: 'os-r4', columnId: 'em_execucao', title: 'Limpeza filtros refeit.', badges: [b('ROTINA','amber')] },
        { id: 'os-r5', columnId: 'pronto',      title: 'Higienização AC-Sala-201',badges: [b('OK','green')] },
        { id: 'os-r6', columnId: 'concluida',   title: 'Recarga gás AC-CCM',      badges: [b('FECHADA','green')] },
      ],
    },
    calendar: {
      events: [
        { id: 'cr1', date: plusD(0),  title: 'AC-Sala-CIC (vencida)', color: 'var(--red)' },
        { id: 'cr2', date: plusD(0),  title: 'AC-Paiol-3 (vencida)',  color: 'var(--red)' },
        { id: 'cr3', date: plusD(3),  title: 'AC-Sala-202' },
        { id: 'cr4', date: plusD(8),  title: 'AC-Sala-201', color: 'var(--green)' },
        { id: 'cr5', date: plusD(15), title: 'AC-Refeitório', color: 'var(--blue)' },
      ],
    },
    gantt: {
      range: { start: iso(new Date(today.getFullYear(), today.getMonth(), 1)),
               end:   iso(new Date(today.getFullYear(), today.getMonth()+1, 0)) },
      tasks: [
        { id: 'gr1', label: 'Limpeza splits andar 2', start: plusD(0), end: plusD(4), color: 'var(--acc)' },
        { id: 'gr2', label: 'Inspeção AC central',    start: plusD(5), end: plusD(6), color: 'var(--green)' },
        { id: 'gr3', label: 'Troca gás (CIC)',        start: plusD(8), end: plusD(10), color: 'var(--amber)' },
        { id: 'gr4', label: 'Higienização vestiários',start: plusD(12),end: plusD(13), color: 'var(--blue)' },
      ],
    },
    chat: {
      currentUser: 'Cb Silva',
      messages: [
        { id: 'm1', author: 'TC Freitas', text: 'Cb Silva, prioriza o AC do CIC — está vencido há 2 dias.', ts: new Date(Date.now() - 30*60000).toISOString() },
        { id: 'm2', author: 'Cb Silva',   text: 'Beleza, vou agora. Peço o hidrojateamento no paiol?',         ts: new Date(Date.now() - 28*60000).toISOString() },
        { id: 'm3', author: 'TC Freitas', text: 'Sim. Foto do filtro antes/depois pelo app.',                  ts: new Date(Date.now() - 25*60000).toISOString() },
        { id: 'm4', author: 'Cb Silva',   text: 'A caminho.',                                                 ts: new Date(Date.now() - 60000).toISOString() },
      ],
    },
    docs: {
      cols: [
        { key: 'nome', label: 'Documento' },
        { key: 'tipo', label: 'Tipo', filter: true },
        { key: 'versao', label: 'Versão' },
        { key: 'data', label: 'Atualizado', format: v => engine.utils.fmt.date(v) },
      ],
      rows: [
        { nome: 'POP — Limpeza padrão split 9k–18k BTU', tipo: 'pop', versao: 'v2.1', data: '2026-04-12' },
        { nome: 'POP — Recarga R-410A',                  tipo: 'pop', versao: 'v1.3', data: '2026-02-28' },
        { nome: 'NR-34 — Trabalho em altura (resumo)',   tipo: 'norma', versao: 'v1.0', data: '2025-11-04' },
        { nome: 'Checklist mensal — Inspeção AC',        tipo: 'checklist', versao: 'v3.0', data: '2026-05-01' },
      ],
    },
  };
})();
