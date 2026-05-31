const MOCK = (() => ({
  modulo: 'core_estoque', titulo: 'Núcleo · Estoque', icon: '🗄️',
  user: { nome: 'TC Freitas' },
  sync: { online: true, pending: 0, lastSync: new Date().toISOString() },
  kpis: [
    { label: 'Itens',        value: 412 },
    { label: 'Estoque baixo', value: 7, sub: 'reposição' },
    { label: 'Vencendo 30d',  value: 5 },
    { label: 'Seções',        value: 3, sub: 'CMASM-13/11/20' },
  ],
  donut: { title: 'Por seção (saldo R$)', data: [
    { label: 'CMASM-13 (Manut.)',   value: 142000, color: 'var(--acc)' },
    { label: 'CMASM-11 (Prefeit.)', value: 78000,  color: 'var(--green)' },
    { label: 'CMASM-20 (Armas)',    value: 235000, color: 'var(--red)' },
  ]},
  ativos: {
    cols: [
      { key: 'codigo', label: 'Código' },
      { key: 'nome', label: 'Item' },
      { key: 'categoria', label: 'Categoria', filter: true },
      { key: 'secao', label: 'Seção', filter: true },
      { key: 'qtd', label: 'Qtd' },
      { key: 'min', label: 'Mín' },
      { key: 'unidade', label: 'Un' },
      { key: 'status', label: 'Status',
        format: v => engine.badge(v.toUpperCase(), v === 'ok' ? 'green' : v === 'baixo' ? 'amber' : 'red') },
    ],
    rows: [
      { codigo: 'OLE-15W40-1L', nome: 'Óleo 15W-40 1L',          categoria: 'consumivel', secao: 'CMASM-13', qtd: 12, min: 10, unidade: 'L', status: 'ok' },
      { codigo: 'GAS-R410A',    nome: 'Gás R-410A',              categoria: 'consumivel', secao: 'CMASM-13', qtd: 1,  min: 3,  unidade: 'kg', status: 'baixo' },
      { codigo: 'FIL-AR-VTR',   nome: 'Filtro de ar viaturas',   categoria: 'sobressalente', secao: 'CMASM-13', qtd: 0,  min: 5,  unidade: 'un', status: 'crítico' },
      { codigo: 'TIN-EPX-5L',   nome: 'Tinta epóxi 5L',          categoria: 'consumivel', secao: 'CMASM-11', qtd: 8,  min: 4,  unidade: 'L', status: 'ok' },
      { codigo: 'EPI-LUV-NIT',  nome: 'Luva nitrílica',          categoria: 'epi',        secao: 'CMASM-11', qtd: 120,min: 50, unidade: 'un', status: 'ok' },
    ],
  },
}))();
