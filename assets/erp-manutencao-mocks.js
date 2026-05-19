/**
 * Mocks fiéis ao schema para Planos / Catálogo / Estoque-filtro / Cal+Gantt / Configuração.
 * Shape espelha data/schema_catalogo.sql para facilitar substituição por API real.
 *
 * Quando /api/catalogo/* e /api/planos/* existirem, esses consts são removidos e
 * `erp-manutencao.js` faz fetch direto.
 */
(function () {
  'use strict';

  const today = new Date();
  const iso = d => new Date(d).toISOString().slice(0, 10);
  const plusD = n => iso(new Date(today.getTime() + n * 86400000));

  window.ERP_MANUT_MOCKS = {

    // shape: catalogo_servicos + sub-tables agrupadas em arrays
    catalogo_servicos: [
      {
        id: 'svc-limp-split-padrao',
        codigo: 'LIMP_SPLIT_PADRAO',
        nome: 'Limpeza padrão split 9k–18k BTU',
        descricao: 'Limpeza completa: filtro, evaporadora, condensadora.',
        escopo: 'central', versao: 2,
        pop_doc_id: 'doc-pop-limp-split-v2',
        tempo_estimado_min: 90,
        servico_pai_id: null,
        aplicavel_a: { categorias: ['climatizacao'], tipos: ['AC_SPLIT'] },
        criado_por_modulo: 'manutencao', ativo: 1,
        materiais: [
          { material_id: null, nome_livre: 'Detergente neutro', qtd: 1, unidade: 'L', obrigatorio: 1 },
          { material_id: null, nome_livre: 'Spray bactericida', qtd: 0.3, unidade: 'L', obrigatorio: 0 },
        ],
        ferramentas: [
          { nome: 'Hidrojateamento de baixa pressão', qtd: 1, obrigatorio: 1 },
          { nome: 'Bomba bag', qtd: 1, obrigatorio: 1 },
        ],
        pessoal: [{ qualificacao_codigo: 'tec_refrig', qtd: 1, opcional: 0 }],
        condicionais: [{ expressao: 'energia.ativa == true', bloqueante: 1 }],
      },
      {
        id: 'svc-recarga-r410a',
        codigo: 'RECARGA_R410A',
        nome: 'Recarga de gás R-410A',
        escopo: 'central', versao: 1, tempo_estimado_min: 60,
        aplicavel_a: { categorias: ['climatizacao'] },
        criado_por_modulo: 'manutencao', ativo: 1,
        materiais: [{ material_id: null, nome_livre: 'Gás R-410A', qtd: 1, unidade: 'kg', obrigatorio: 1 }],
        ferramentas: [{ nome: 'Manifold', qtd: 1, obrigatorio: 1 }],
        pessoal: [{ qualificacao_codigo: 'tec_refrig', qtd: 1, opcional: 0 }],
        condicionais: [],
      },
      {
        id: 'svc-gmg-250h',
        codigo: 'GMG_TROCA_OLEO_250H',
        nome: 'Troca óleo + filtro gerador (250h)',
        escopo: 'central', versao: 1, tempo_estimado_min: 120,
        aplicavel_a: { categorias: ['eletrica'], tipos: ['GERADOR'] },
        criado_por_modulo: 'manutencao', ativo: 1,
        materiais: [
          { material_id: null, nome_livre: 'Óleo 15W-40 lubrificante', qtd: 8, unidade: 'L', obrigatorio: 1 },
          { material_id: null, nome_livre: 'Filtro de óleo gerador', qtd: 1, unidade: 'un', obrigatorio: 1 },
        ],
        ferramentas: [],
        pessoal: [{ qualificacao_codigo: 'eletricista_nr10', qtd: 1, opcional: 0 }],
        condicionais: [{ expressao: 'ativo.disponivel == true', bloqueante: 1 }],
      },
      {
        id: 'svc-vtr-5000km',
        codigo: 'VTR_REVISAO_5000KM',
        nome: 'Revisão de viatura a cada 5.000 km',
        escopo: 'central', versao: 1, tempo_estimado_min: 180,
        aplicavel_a: { categorias: ['frota_terrestre'] },
        criado_por_modulo: 'manutencao', ativo: 1,
        materiais: [
          { material_id: null, nome_livre: 'Óleo 5W-30 sintético 4L', qtd: 1, unidade: 'un', obrigatorio: 1 },
          { material_id: null, nome_livre: 'Filtro de óleo', qtd: 1, unidade: 'un', obrigatorio: 1 },
        ],
        ferramentas: [],
        pessoal: [{ qualificacao_codigo: 'motorista_b', qtd: 1, opcional: 1 }],
        condicionais: [],
      },
    ],

    // shape: planos_manutencao
    planos_manutencao: [
      {
        id: 'plan-ac-cic', servico_id: 'svc-limp-split-padrao', servico_versao_pin: null,
        ativo_id: 'a-clim-cic', tipo_codigo: null,
        frequencia: { tipo: 'periodica', valor: { critico_24x7: 'P1M', operacional: 'P3M', admin: 'P1Y' } },
        criticidade_override: null,
        janela_permitida: { hora_inicio: '02:00', hora_fim: '05:00' },
        proxima_execucao: plusD(-2),  // vencida
        ultima_execucao: plusD(-35),
        responsavel_pmoc: 'pmoc_refrigeracao',
        ativo: 1, criado_por_modulo: 'manutencao',
      },
      {
        id: 'plan-ac-sala-202', servico_id: 'svc-limp-split-padrao', servico_versao_pin: null,
        ativo_id: null, tipo_codigo: 'AC_SPLIT',
        frequencia: { tipo: 'periodica', valor: 'P3M' },
        criticidade_override: 'operacional',
        proxima_execucao: plusD(3),
        ultima_execucao: plusD(-90),
        responsavel_pmoc: 'pmoc_refrigeracao',
        ativo: 1, criado_por_modulo: 'manutencao',
      },
      {
        id: 'plan-gmg1-250h', servico_id: 'svc-gmg-250h', servico_versao_pin: 1,
        ativo_id: 'a-gmg-1', tipo_codigo: null,
        frequencia: { tipo: 'por_uso', valor: 250, unidade: 'h' },
        proxima_execucao: plusD(8),
        ultima_execucao: plusD(-180),
        responsavel_pmoc: 'pmoc_eletrica',
        ativo: 1, criado_por_modulo: 'manutencao',
      },
      {
        id: 'plan-s10-5000', servico_id: 'svc-vtr-5000km', servico_versao_pin: null,
        ativo_id: 'a-vtr-s10', tipo_codigo: null,
        frequencia: { tipo: 'por_uso', valor: 5000, unidade: 'km' },
        proxima_execucao: plusD(15),
        ultima_execucao: plusD(-60),
        responsavel_pmoc: 'pmoc_transportes',
        ativo: 1, criado_por_modulo: 'manutencao',
      },
    ],

    // mapeamento mock de relevância: categoria → códigos de estoque relevantes
    estoque_relevancia: {
      climatizacao:     ['GAS-R410A', 'OLE-15W40-1L', 'FIL-AR-VTR'],
      eletrica:         ['OLE-15W40-1L', 'FIL-AR-VTR'],
      frota_terrestre:  ['OLE-15W40-1L', 'FIL-AR-VTR'],
      frota_naval:      ['OLE-15W40-1L'],
      maquinas_corte:   ['OLE-15W40-1L'],
      predial:          ['TIN-EPX-5L'],
      instrumentos:     [],
    },

    // shape: { codigo, nome, descricao, requer_validade } + lista de usuarios qualificados
    qualificacoes_catalogo: [
      { codigo: 'tec_refrig',       nome: 'Técnico em Refrigeração', requer_validade: 1, usuarios: 3 },
      { codigo: 'eletricista_nr10', nome: 'Eletricista NR-10',        requer_validade: 1, usuarios: 5 },
      { codigo: 'soldador',         nome: 'Soldador qualificado',     requer_validade: 1, usuarios: 2 },
      { codigo: 'operador_munk',    nome: 'Operador de Munk',         requer_validade: 1, usuarios: 1 },
      { codigo: 'motorista_b',      nome: 'Motorista categoria B',    requer_validade: 1, usuarios: 12 },
      { codigo: 'motorista_d',      nome: 'Motorista categoria D',    requer_validade: 1, usuarios: 3 },
      { codigo: 'arrais',           nome: 'Arrais Amador',             requer_validade: 1, usuarios: 2 },
      { codigo: 'operador_corte',   nome: 'Operador de máquina de corte', requer_validade: 1, usuarios: 4 },
    ],

    // shape: documento (apenas POPs vinculados a serviços)
    documentos_pop: [
      { id: 'doc-pop-limp-split-v2', nome: 'POP — Limpeza padrão split (v2)', tipo: 'pop', versao: 2, sha256: 'a1b2c3' },
      { id: 'doc-pop-gmg-v1',        nome: 'POP — Manutenção GMG (250h)',     tipo: 'pop', versao: 1, sha256: 'd4e5f6' },
    ],
  };
})();
