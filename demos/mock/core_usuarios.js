const MOCK = (() => ({
  modulo: 'core_usuarios', titulo: 'Núcleo · Usuários', icon: '👥',
  user: { nome: 'TC Freitas' },
  sync: { online: true, pending: 0, lastSync: new Date().toISOString() },
  kpis: [
    { label: 'Usuários',         value: 78 },
    { label: 'Ativos',           value: 72 },
    { label: 'Lotações',         value: 14 },
    { label: 'Qualif. vencendo', value: 6, sub: '< 60 dias' },
  ],
  donut: { title: 'Por categoria', data: [
    { label: 'Militares', value: 58, color: 'var(--acc)' },
    { label: 'Civis',     value: 14, color: 'var(--green)' },
  ]},
  ativos: {
    cols: [
      { key: 'mat',  label: 'Mat./NIP' },
      { key: 'nome', label: 'Nome' },
      { key: 'posto', label: 'Posto/Grad.', filter: true },
      { key: 'lotacao', label: 'Lotação', filter: true },
      { key: 'qualificacoes', label: 'Qualificações' },
    ],
    rows: [
      { mat: '04.1234.56', nome: 'TC Freitas',   posto: 'TC',  lotacao: 'CMASM-13', qualificacoes: 'eletricista_nr10' },
      { mat: '04.2233.11', nome: 'Cb Silva',     posto: 'Cb',  lotacao: 'CMASM-13', qualificacoes: 'tec_refrig' },
      { mat: '04.3344.22', nome: '2T Soares',    posto: '2T',  lotacao: 'CMASM-13', qualificacoes: '—' },
      { mat: '04.4455.33', nome: 'Sub Costa',    posto: 'SUB', lotacao: 'CMASM-13', qualificacoes: 'eletricista_nr10, soldador' },
      { mat: '04.5566.44', nome: '1T Marques',   posto: '1T',  lotacao: 'CMASM-20', qualificacoes: '—' },
      { mat: '04.6677.55', nome: 'CF Almeida',   posto: 'CF',  lotacao: 'CMASM-13', qualificacoes: 'motorista_d' },
      { mat: '04.7788.66', nome: 'TC Ribeiro',   posto: 'TC',  lotacao: 'CMASM-13', qualificacoes: 'tec_refrig' },
      { mat: '04.8899.77', nome: 'Cabo Vieira',  posto: 'Cb',  lotacao: 'CMASM-13', qualificacoes: 'operador_corte' },
    ],
  },
}))();
