const MOCK = (() => ({
  modulo: 'core_documentos', titulo: 'Núcleo · Documentos', icon: '📄',
  user: { nome: 'TC Freitas' },
  sync: { online: true, pending: 0, lastSync: new Date().toISOString() },
  kpis: [
    { label: 'POPs',          value: 42 },
    { label: 'Certificados',  value: 67, sub: '6 vencendo' },
    { label: 'Fotos (OS)',    value: 1245 },
    { label: 'Plantas',       value: 18 },
  ],
  donut: { title: 'Por tipo', data: [
    { label: 'POP',          value: 42, color: 'var(--acc)' },
    { label: 'Certificado',  value: 67, color: 'var(--green)' },
    { label: 'Norma',        value: 24, color: 'var(--blue)' },
    { label: 'Foto (OS)',    value: 1245, color: 'var(--amber)' },
    { label: 'Planta',       value: 18,   color: 'var(--ink-2)' },
  ]},
  docs: {
    cols: [
      { key: 'nome', label: 'Documento' },
      { key: 'tipo', label: 'Tipo', filter: true },
      { key: 'vinculo_tipo', label: 'Vínculo', filter: true },
      { key: 'versao', label: 'Versão' },
      { key: 'data', label: 'Atualizado', format: v => engine.utils.fmt.date(v) },
    ],
    rows: [
      { nome: 'POP — Limpeza padrão split 9k–18k BTU',  tipo: 'pop',         vinculo_tipo: 'servico', versao: 'v2.1', data: '2026-04-12' },
      { nome: 'POP — Manutenção GMG (250h)',             tipo: 'pop',         vinculo_tipo: 'servico', versao: 'v1.0', data: '2026-03-15' },
      { nome: 'POP — Inspeção pré-viagem viaturas',       tipo: 'pop',         vinculo_tipo: 'servico', versao: 'v3.2', data: '2026-03-04' },
      { nome: 'Certificado RBC — GAMI-001 (2026)',        tipo: 'certificado', vinculo_tipo: 'ativo',   versao: 'v1',   data: '2026-01-20' },
      { nome: 'NR-10 — Procedimentos',                    tipo: 'norma',       vinculo_tipo: '',        versao: 'v1.0', data: '2025-09-10' },
      { nome: 'Planta baixa CMASM (PDF)',                 tipo: 'planta',      vinculo_tipo: 'local',   versao: 'v2.0', data: '2025-06-30' },
    ],
  },
}))();
