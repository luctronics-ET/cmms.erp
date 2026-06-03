/**
 * Dados de referência para o módulo Manutenção.
 *
 * TIPOS: 7 tipos de equipamento de corte vegetal, com planos preventivos baseados
 * em horímetro — idênticos ao sistema legado maq-corte.html (cmasm_v2_state).
 *
 * catalogo_servicos / planos_manutencao: derivados de TIPOS, usados pelas tabs
 * Planos e Catálogo até a API /api/catalogo estar disponível.
 */
(function () {
  'use strict';

  // ── TIPOS de equipamento (planos por horímetro) ──────────────────────────
  const TIPOS = {
    FS220: { nome: 'Roçadeira STIHL FS 220', cor: '#f97316', emoji: '🌿', categoria: 'maquinas_corte',
      plano: [
        { id: 'p01', iv: 8,   n: 'Inspeção geral + nível de óleo',          its: [] },
        { id: 'p02', iv: 25,  n: 'Limpar filtro de ar',                      its: ['Filtro de ar FS220'] },
        { id: 'p03', iv: 25,  n: 'Lubrificar caixa de transmissão',          its: ['Graxa STIHL engrenagem'] },
        { id: 'p04', iv: 25,  n: 'Inspecionar/trocar nylon ou lâmina',       its: ['Carretel nylon', 'Lâmina 2 pontas'] },
        { id: 'p05', iv: 100, n: 'Trocar vela de ignição',                   its: ['Vela NGK BPMR7A'] },
        { id: 'p06', iv: 150, n: 'Trocar filtro de combustível',             its: ['Filtro combustível'] },
        { id: 'p07', iv: 300, n: 'Verificar/trocar mangueira combustível',   its: ['Mangueira combustível'] },
        { id: 'p08', iv: 500, n: 'Revisão geral do motor',                   its: ['Kit juntas', 'Kit pistão/anéis'] },
      ],
    },
    GAR: { nome: 'Cortador Garthen PRO-3500S', cor: '#22c55e', emoji: '✂️', categoria: 'maquinas_corte',
      plano: [
        { id: 'p01', iv: 8,   n: 'Inspeção geral + nível de óleo',          its: [] },
        { id: 'p02', iv: 50,  n: 'Trocar óleo do motor 4T',                 its: ['Óleo SAE 30 / 10W-30'] },
        { id: 'p03', iv: 50,  n: 'Limpar filtro de ar',                      its: ['Filtro de ar Garthen'] },
        { id: 'p04', iv: 100, n: 'Trocar vela de ignição',                   its: ['Vela NGK Cg420'] },
        { id: 'p05', iv: 100, n: 'Trocar filtro de óleo',                   its: ['Filtro de óleo'] },
        { id: 'p06', iv: 100, n: 'Inspecionar lâminas e rodas',              its: ['Lâmina 2 pontas', 'Roda dianteira', 'Roda traseira'] },
        { id: 'p07', iv: 150, n: 'Trocar filtro de combustível',             its: ['Filtro combustível'] },
        { id: 'p08', iv: 500, n: 'Revisão geral',                            its: ['Kit juntas motor'] },
      ],
    },
    MS650: { nome: 'Motosserra STIHL MS650', cor: '#ef4444', emoji: '🪚', categoria: 'maquinas_corte',
      plano: [
        { id: 'p01', iv: 8,   n: 'Inspeção geral',                           its: [] },
        { id: 'p02', iv: 25,  n: 'Limpar filtro de ar',                      its: ['Filtro de ar MS650'] },
        { id: 'p03', iv: 25,  n: 'Lubrificar corrente (óleo corrente)',       its: ['Óleo corrente motosserra'] },
        { id: 'p04', iv: 50,  n: 'Afiar ou trocar corrente',                  its: ['Corrente 36 RM 63cm', 'Lima afiar'] },
        { id: 'p05', iv: 100, n: 'Trocar vela de ignição',                   its: ['Vela NGK MS650'] },
        { id: 'p06', iv: 150, n: 'Trocar filtro de combustível',             its: ['Filtro combustível'] },
        { id: 'p07', iv: 500, n: 'Revisão geral do motor',                   its: ['Kit juntas', 'Carburador'] },
      ],
    },
    COY: { nome: 'Tobata Coyote CT151', cor: '#a855f7', emoji: '🚜', categoria: 'maquinas_corte',
      plano: [
        { id: 'p01', iv: 8,   n: 'Inspeção geral + nível de óleo',          its: [] },
        { id: 'p02', iv: 50,  n: 'Trocar óleo do motor',                    its: ['Óleo SAE 30'] },
        { id: 'p03', iv: 50,  n: 'Limpar filtro de ar',                      its: ['Filtro de ar Coyote'] },
        { id: 'p04', iv: 100, n: 'Trocar vela + filtro de óleo',             its: ['Vela de ignição', 'Filtro de óleo'] },
        { id: 'p05', iv: 100, n: 'Inspecionar correias',                     its: ['Correia principal Tobata'] },
        { id: 'p06', iv: 150, n: 'Trocar filtro de combustível',             its: ['Filtro combustível'] },
        { id: 'p07', iv: 200, n: 'Trocar correia principal',                 its: ['Correia principal Tobata'] },
        { id: 'p08', iv: 500, n: 'Revisão geral',                            its: ['Kit carburador', 'Filtro hidráulico'] },
      ],
    },
    LGT: { nome: 'Husqvarna LGT2654', cor: '#14b8a6', emoji: '🌱', categoria: 'maquinas_corte',
      plano: [
        { id: 'p01', iv: 8,   n: 'Inspeção geral + nível de óleo',          its: [] },
        { id: 'p02', iv: 50,  n: 'Trocar óleo + filtro de óleo',            its: ['Óleo SAE 30', 'Filtro de óleo LGT'] },
        { id: 'p03', iv: 50,  n: 'Limpar filtro de ar',                      its: ['Filtro de ar LGT2654'] },
        { id: 'p04', iv: 100, n: 'Trocar velas (2 cilindros)',               its: ['Vela de ignição x2'] },
        { id: 'p05', iv: 150, n: 'Trocar correia do deck',                   its: ['Correia deck LGT2654'] },
        { id: 'p06', iv: 150, n: 'Trocar filtro de combustível',             its: ['Filtro combustível'] },
        { id: 'p07', iv: 250, n: 'Trocar correia de transmissão',            its: ['Correia transmissão LGT2654'] },
        { id: 'p08', iv: 500, n: 'Revisão geral',                            its: ['Kit carburador', 'Mola governador'] },
      ],
    },
    TS114: { nome: 'Husqvarna TS114', cor: '#f97316', emoji: '🌿', categoria: 'maquinas_corte',
      plano: [
        { id: 'p01', iv: 8,   n: 'Inspeção geral + nível de óleo',           its: [] },
        { id: 'p02', iv: 25,  n: 'Limpar filtro de ar',                       its: ['Filtro de ar LTH1738'] },
        { id: 'p03', iv: 25,  n: 'Lubrificar pontos de graxeiro (4 pts.)',    its: ['Graxa NLGI 2'] },
        { id: 'p04', iv: 25,  n: 'Inspecionar/afiar ou trocar lâmina',        its: ['Lâmina de corte Husqvarna TS114'] },
        { id: 'p05', iv: 50,  n: 'Trocar óleo do motor (~0,6 L)',             its: ['Óleo SAE 30'] },
        { id: 'p06', iv: 50,  n: 'Trocar filtro de ar',                       its: ['Filtro de ar LTH1738'] },
        { id: 'p07', iv: 100, n: 'Trocar vela de ignição',                    its: ['Vela HQT-9'] },
        { id: 'p08', iv: 100, n: 'Inspecionar correias (visual)',              its: [] },
        { id: 'p09', iv: 100, n: 'Revisão geral + aperto de torque',          its: [] },
        { id: 'p10', iv: 150, n: 'Trocar filtro de combustível',              its: ['Filtro combustível'] },
        { id: 'p11', iv: 200, n: 'Trocar correia de deck',                    its: ['Correia A-78'] },
        { id: 'p12', iv: 250, n: 'Trocar correia de transmissão',             its: ['Correia A-78'] },
        { id: 'p13', iv: 300, n: 'Kit reparo carburador (membranas)',         its: ['Kit carburador HS452AE'] },
        { id: 'p14', iv: 500, n: 'Trocar rolamentos de roda',                its: ['Rolamento 6202-2RS'] },
      ],
    },
    SOL: { nome: 'Trator Agrícola Solis 90', cor: '#3b82f6', emoji: '🌾', categoria: 'maquinas_corte',
      plano: [
        { id: 'p01', iv: 8,   n: 'Inspeção geral + nível de óleo',          its: [] },
        { id: 'p02', iv: 50,  n: 'Trocar óleo + filtro de óleo (diesel)',    its: ['Óleo 15W-40 diesel', 'Filtro óleo Solis'] },
        { id: 'p03', iv: 50,  n: 'Limpar filtro de ar primário',             its: ['Filtro ar primário Solis'] },
        { id: 'p04', iv: 150, n: 'Trocar filtro de combustível diesel',      its: ['Filtro combustível diesel'] },
        { id: 'p05', iv: 250, n: 'Trocar filtro hidráulico',                 its: ['Filtro hidráulico Solis'] },
        { id: 'p06', iv: 250, n: 'Trocar filtro de ar completo',             its: ['Filtro ar primário Solis', 'Filtro ar safety'] },
        { id: 'p07', iv: 500, n: 'Trocar correia alternador',                its: ['Correia alternador Solis'] },
        { id: 'p08', iv: 500, n: 'Trocar filtro de transmissão',             its: ['Filtro transmissão Solis'] },
        { id: 'p09', iv: 1000, n: 'Revisão geral motor diesel',              its: ['Kit juntas cabeçote', 'Glow plugs x4'] },
      ],
    },
  };

  // ── Unidades padrão (28 máquinas) ────────────────────────────────────────
  const UNIDADES_DEFAULT = [
    { id: 'u01', tipo: 'FS220', nome: 'FS220-01', pat: '', obs: '', ativo: true },
    { id: 'u02', tipo: 'FS220', nome: 'FS220-02', pat: '', obs: '', ativo: true },
    { id: 'u03', tipo: 'FS220', nome: 'FS220-03', pat: '', obs: '', ativo: true },
    { id: 'u04', tipo: 'FS220', nome: 'FS220-04', pat: '', obs: '', ativo: true },
    { id: 'u05', tipo: 'FS220', nome: 'FS220-05', pat: '', obs: '', ativo: true },
    { id: 'u06', tipo: 'FS220', nome: 'FS220-06', pat: '', obs: '', ativo: true },
    { id: 'u07', tipo: 'FS220', nome: 'FS220-07', pat: '', obs: '', ativo: true },
    { id: 'u08', tipo: 'FS220', nome: 'FS220-08', pat: '', obs: '', ativo: true },
    { id: 'u09', tipo: 'FS220', nome: 'FS220-09', pat: '', obs: '', ativo: true },
    { id: 'u10', tipo: 'FS220', nome: 'FS220-10', pat: '', obs: '', ativo: true },
    { id: 'u11', tipo: 'GAR',   nome: 'GAR-01',   pat: '', obs: '', ativo: true },
    { id: 'u12', tipo: 'GAR',   nome: 'GAR-02',   pat: '', obs: '', ativo: true },
    { id: 'u13', tipo: 'GAR',   nome: 'GAR-03',   pat: '', obs: '', ativo: true },
    { id: 'u14', tipo: 'GAR',   nome: 'GAR-04',   pat: '', obs: '', ativo: true },
    { id: 'u15', tipo: 'GAR',   nome: 'GAR-05',   pat: '', obs: '', ativo: true },
    { id: 'u16', tipo: 'GAR',   nome: 'GAR-06',   pat: '', obs: '', ativo: true },
    { id: 'u17', tipo: 'GAR',   nome: 'GAR-07',   pat: '', obs: '', ativo: true },
    { id: 'u18', tipo: 'GAR',   nome: 'GAR-08',   pat: '', obs: '', ativo: true },
    { id: 'u19', tipo: 'MS650', nome: 'MS650-01', pat: '', obs: '', ativo: true },
    { id: 'u20', tipo: 'COY',   nome: 'COY-01',   pat: '', obs: '', ativo: true },
    { id: 'u21', tipo: 'COY',   nome: 'COY-02',   pat: '', obs: '', ativo: true },
    { id: 'u22', tipo: 'COY',   nome: 'COY-03',   pat: '', obs: '', ativo: true },
    { id: 'u23', tipo: 'LGT',   nome: 'LGT-01',   pat: '', obs: '', ativo: true },
    { id: 'u24', tipo: 'TS114', nome: 'TS114-01', pat: '', obs: '', ativo: true },
    { id: 'u25', tipo: 'TS114', nome: 'TS114-02', pat: '', obs: '', ativo: true },
    { id: 'u26', tipo: 'TS114', nome: 'TS114-03', pat: '', obs: '', ativo: true },
    { id: 'u27', tipo: 'TS114', nome: 'TS114-04', pat: '', obs: '', ativo: true },
    { id: 'u28', tipo: 'SOL',   nome: 'SOL-01',   pat: '', obs: '', ativo: true },
  ];

  // ── Peças e insumos padrão (34 itens) ────────────────────────────────────
  const PECAS_DEFAULT = [
    { id: 'pe01', d: 'Óleo 2T STIHL HP Ultra 50mL',          un: 'UN', cat: 'oleo',    pr: 8.50 },
    { id: 'pe02', d: 'Óleo SAE 30 / 10W-30 – 1L',            un: 'L',  cat: 'oleo',    pr: 25.00 },
    { id: 'pe03', d: 'Óleo 15W-40 diesel – 1L',              un: 'L',  cat: 'oleo',    pr: 20.00 },
    { id: 'pe04', d: 'Óleo corrente motosserra – 1L',         un: 'L',  cat: 'oleo',    pr: 18.00 },
    { id: 'pe05', d: 'Graxa engrenagem STIHL 80g',            un: 'UN', cat: 'graxa',   pr: 35.00 },
    { id: 'pe06', d: 'Graxa NLGI 2 – cartucho 400g',          un: 'UN', cat: 'graxa',   pr: 28.00 },
    { id: 'pe07', d: 'Filtro de ar LTH 1738 (TS114)',         un: 'UN', cat: 'filtro',  pr: 55.00 },
    { id: 'pe08', d: 'Filtro de ar FS220 / MS650',            un: 'UN', cat: 'filtro',  pr: 38.00 },
    { id: 'pe09', d: 'Filtro de ar Garthen PRO-3500S',        un: 'UN', cat: 'filtro',  pr: 45.00 },
    { id: 'pe10', d: 'Filtro de ar Tobata Coyote CT151',      un: 'UN', cat: 'filtro',  pr: 42.00 },
    { id: 'pe11', d: 'Filtro de ar primário Solis 90',        un: 'UN', cat: 'filtro',  pr: 85.00 },
    { id: 'pe12', d: 'Filtro de ar safety Solis 90',          un: 'UN', cat: 'filtro',  pr: 65.00 },
    { id: 'pe13', d: 'Filtro combustível motor 4T',           un: 'UN', cat: 'filtro',  pr: 22.00 },
    { id: 'pe14', d: 'Filtro combustível diesel Solis 90',    un: 'UN', cat: 'filtro',  pr: 55.00 },
    { id: 'pe15', d: 'Filtro de óleo motor 4T',               un: 'UN', cat: 'filtro',  pr: 35.00 },
    { id: 'pe16', d: 'Filtro hidráulico Solis 90',            un: 'UN', cat: 'filtro',  pr: 120.00 },
    { id: 'pe17', d: 'Vela HQT-9 (Husqvarna TS114)',          un: 'UN', cat: 'motor',   pr: 47.40 },
    { id: 'pe18', d: 'Vela NGK BPMR7A (STIHL FS220/MS650)',   un: 'UN', cat: 'motor',   pr: 22.00 },
    { id: 'pe19', d: 'Vela NGK Cg420 (Garthen)',              un: 'UN', cat: 'motor',   pr: 18.00 },
    { id: 'pe20', d: 'Vela ignição Tobata / Solis',           un: 'UN', cat: 'motor',   pr: 30.00 },
    { id: 'pe21', d: 'Lâmina de corte Husqvarna TS114',       un: 'UN', cat: 'corte',   pr: 107.00 },
    { id: 'pe22', d: 'Lâmina 2 pontas 305mm – roçadeira',     un: 'UN', cat: 'corte',   pr: 28.00 },
    { id: 'pe23', d: 'Carretel de nylon manual FS220',        un: 'UN', cat: 'corte',   pr: 22.00 },
    { id: 'pe24', d: 'Correia A-78 (TS114 deck/transmissão)', un: 'UN', cat: 'correia', pr: 75.00 },
    { id: 'pe25', d: 'Correia deck Husqvarna LGT2654',        un: 'UN', cat: 'correia', pr: 280.00 },
    { id: 'pe26', d: 'Correia Tobata TR13/M130/M140',         un: 'UN', cat: 'correia', pr: 80.00 },
    { id: 'pe27', d: 'Corrente motosserra 36 RM 63cm',        un: 'UN', cat: 'corte',   pr: 150.00 },
    { id: 'pe28', d: 'Pneu dianteiro 15x6.00-6 TS114',        un: 'UN', cat: 'pneu',    pr: 450.00 },
    { id: 'pe29', d: 'Pneu traseiro 18x8.50-8 TS114',         un: 'UN', cat: 'pneu',    pr: 668.00 },
    { id: 'pe30', d: 'Kit reparo carburador HS452AE',          un: 'UN', cat: 'motor',   pr: 150.00 },
    { id: 'pe31', d: 'Mangueira combustível SAE J30 – 1m',    un: 'm',  cat: 'motor',   pr: 20.00 },
    { id: 'pe32', d: 'Sensor de banco / presença 12V',        un: 'UN', cat: 'eletric', pr: 120.00 },
    { id: 'pe33', d: 'Kit fusíveis automotivos sortido',       un: 'kit', cat: 'eletric', pr: 40.00 },
    { id: 'pe34', d: 'Descarbonizante CAR80 300mL',           un: 'UN', cat: 'quimico', pr: 38.00 },
  ];

  // ── EAM: itens de simulação TS114 (25 itens, fonte: CMASM_Simulacao_TS114) ─
  // flags E=Essencial R=Regular O=Ótimo · iv=intervalo h · vida=vida útil h · qe=qtd/evento
  const ITENS_EAM = [
    { id: 1,  d: 'Lâmina de corte',       un: 'un',  p: 107.00, iv: 25,   vida: 200,  cat: 'corte',    E:1, R:1, O:1, qe: 1 },
    { id: 2,  d: 'Correia A-78',          un: 'un',  p:  75.00, iv: 150,  vida: 600,  cat: 'corte',    E:1, R:1, O:1, qe: 1 },
    { id: 3,  d: 'Parafuso fix. lâmina',  un: 'un',  p:  15.00, iv: 25,   vida: 200,  cat: 'corte',    E:0, R:1, O:1, qe: 2 },
    { id: 4,  d: 'Roda suporte deck',     un: 'un',  p: 120.00, iv: 500,  vida: 2000, cat: 'corte',    E:0, R:0, O:1, qe: 1 },
    { id: 5,  d: 'Vela de ignição',       un: 'un',  p:  47.40, iv: 100,  vida: 400,  cat: 'motor',    E:1, R:1, O:1, qe: 1 },
    { id: 6,  d: 'Filtro de ar',          un: 'un',  p:  55.00, iv: 50,   vida: 150,  cat: 'motor',    E:1, R:1, O:1, qe: 1 },
    { id: 7,  d: 'Filtro combustível',    un: 'un',  p:  48.67, iv: 150,  vida: 450,  cat: 'motor',    E:0, R:1, O:1, qe: 1 },
    { id: 8,  d: 'Kit carburador',        un: 'un',  p: 150.00, iv: 300,  vida: 600,  cat: 'motor',    E:0, R:0, O:1, qe: 1 },
    { id: 9,  d: 'Mangueira combustível', un: 'm',   p:  20.00, iv: 500,  vida: 1500, cat: 'motor',    E:0, R:0, O:1, qe: 1 },
    { id: 10, d: 'Pneu dianteiro',        un: 'un',  p: 450.00, iv: 1500, vida: 4500, cat: 'rodagem',  E:1, R:1, O:1, qe: 1 },
    { id: 11, d: 'Pneu traseiro',         un: 'un',  p: 668.00, iv: 2000, vida: 6000, cat: 'rodagem',  E:0, R:1, O:1, qe: 1 },
    { id: 12, d: 'Sensor de banco',       un: 'un',  p: 120.00, iv: 2000, vida: 4000, cat: 'eletrico', E:0, R:0, O:1, qe: 1 },
    { id: 13, d: 'Kit fusíveis',          un: 'kit', p:  40.00, iv: 9999, vida: 9999, cat: 'eletrico', E:1, R:1, O:1, qe: 1 },
    { id: 14, d: 'Porca M12',             un: 'cx',  p:  70.00, iv: 9999, vida: 9999, cat: 'fixador',  E:0, R:1, O:1, qe: 1 },
    { id: 15, d: 'Arruela M3',            un: 'cx',  p:  35.00, iv: 9999, vida: 9999, cat: 'fixador',  E:0, R:0, O:1, qe: 1 },
    { id: 16, d: 'Arruela M4',            un: 'cx',  p:  35.00, iv: 9999, vida: 9999, cat: 'fixador',  E:0, R:1, O:1, qe: 1 },
    { id: 17, d: 'Arruela M5',            un: 'cx',  p:  35.00, iv: 9999, vida: 9999, cat: 'fixador',  E:0, R:1, O:1, qe: 1 },
    { id: 18, d: 'Arruela M6',            un: 'cx',  p:  35.00, iv: 9999, vida: 9999, cat: 'fixador',  E:0, R:1, O:1, qe: 1 },
    { id: 19, d: 'Arruela M8',            un: 'cx',  p:  35.00, iv: 9999, vida: 9999, cat: 'fixador',  E:0, R:1, O:1, qe: 1 },
    { id: 20, d: 'Arruela M10',           un: 'cx',  p:  35.00, iv: 9999, vida: 9999, cat: 'fixador',  E:0, R:1, O:1, qe: 1 },
    { id: 21, d: 'Rodinha deck',          un: 'un',  p:  35.00, iv: 800,  vida: 3200, cat: 'corte',    E:0, R:0, O:1, qe: 2 },
    { id: 22, d: 'Porca nylon M8',        un: 'cx',  p:  35.00, iv: 9999, vida: 9999, cat: 'fixador',  E:0, R:1, O:1, qe: 1 },
    { id: 23, d: 'Porca nylon M10',       un: 'cx',  p:  35.00, iv: 9999, vida: 9999, cat: 'fixador',  E:0, R:1, O:1, qe: 1 },
    { id: 24, d: 'Porca nylon M11',       un: 'cx',  p:  35.00, iv: 9999, vida: 9999, cat: 'fixador',  E:0, R:1, O:1, qe: 1 },
    { id: 25, d: 'Porca nylon M12',       un: 'cx',  p:  35.00, iv: 9999, vida: 9999, cat: 'fixador',  E:0, R:1, O:1, qe: 1 },
  ];

  // ── EAM: valores de aquisição por tipo (R$) ──────────────────────────────
  // vAcq=valor aquisição · vRes=residual (10%) · vidaH=vida útil em horas
  const VALORES_EAM = {
    TS114: { vAcq: 18500, vRes: 1850,  vidaH: 5000 },
    LGT:   { vAcq: 22000, vRes: 2200,  vidaH: 5000 },
    SOL:   { vAcq: 85000, vRes: 8500,  vidaH: 8000 },
    FS220: { vAcq: 2800,  vRes: 280,   vidaH: 2000 },
    GAR:   { vAcq: 3200,  vRes: 320,   vidaH: 2500 },
    MS650: { vAcq: 4500,  vRes: 450,   vidaH: 2500 },
    COY:   { vAcq: 8500,  vRes: 850,   vidaH: 4000 },
  };

  // ── Catálogo de serviços (para tabs Catálogo e integração Serviços) ───────
  const catalogo_servicos = [
    {
      id: 'svc-limp-split-padrao', codigo: 'LIMP_SPLIT_PADRAO',
      nome: 'Limpeza padrão split 9k–18k BTU',
      descricao: 'Limpeza completa: filtro, evaporadora, condensadora.',
      escopo: 'central', versao: 2, pop_doc_id: 'doc-pop-limp-split-v2',
      tempo_estimado_min: 90, servico_pai_id: null,
      aplicavel_a: { categorias: ['climatizacao'], tipos: ['AC_SPLIT'] },
      criado_por_modulo: 'manutencao', ativo: 1,
      materiais: [
        { nome_livre: 'Detergente neutro', qtd: 1, unidade: 'L', obrigatorio: 1 },
        { nome_livre: 'Spray bactericida', qtd: 0.3, unidade: 'L', obrigatorio: 0 },
      ],
      ferramentas: [
        { nome: 'Hidrojateamento de baixa pressão', qtd: 1, obrigatorio: 1 },
        { nome: 'Bomba bag', qtd: 1, obrigatorio: 1 },
      ],
      pessoal: [{ qualificacao_codigo: 'tec_refrig', qtd: 1, opcional: 0 }],
    },
    {
      id: 'svc-recarga-r410a', codigo: 'RECARGA_R410A',
      nome: 'Recarga de gás R-410A',
      escopo: 'central', versao: 1, tempo_estimado_min: 60,
      aplicavel_a: { categorias: ['climatizacao'] },
      criado_por_modulo: 'manutencao', ativo: 1,
      materiais: [{ nome_livre: 'Gás R-410A', qtd: 1, unidade: 'kg', obrigatorio: 1 }],
      ferramentas: [{ nome: 'Manifold', qtd: 1, obrigatorio: 1 }],
      pessoal: [{ qualificacao_codigo: 'tec_refrig', qtd: 1, opcional: 0 }],
    },
    {
      id: 'svc-gmg-250h', codigo: 'GMG_TROCA_OLEO_250H',
      nome: 'Troca óleo + filtro gerador (250h)',
      escopo: 'central', versao: 1, tempo_estimado_min: 120,
      aplicavel_a: { categorias: ['eletrica'], tipos: ['GERADOR'] },
      criado_por_modulo: 'manutencao', ativo: 1,
      materiais: [
        { nome_livre: 'Óleo 15W-40 lubrificante', qtd: 8, unidade: 'L', obrigatorio: 1 },
        { nome_livre: 'Filtro de óleo gerador', qtd: 1, unidade: 'un', obrigatorio: 1 },
      ],
      ferramentas: [],
      pessoal: [{ qualificacao_codigo: 'eletricista_nr10', qtd: 1, opcional: 0 }],
    },
    {
      id: 'svc-vtr-5000km', codigo: 'VTR_REVISAO_5000KM',
      nome: 'Revisão de viatura a cada 5.000 km',
      escopo: 'central', versao: 1, tempo_estimado_min: 180,
      aplicavel_a: { categorias: ['frota_terrestre'] },
      criado_por_modulo: 'manutencao', ativo: 1,
      materiais: [
        { nome_livre: 'Óleo 5W-30 sintético 4L', qtd: 1, unidade: 'un', obrigatorio: 1 },
        { nome_livre: 'Filtro de óleo', qtd: 1, unidade: 'un', obrigatorio: 1 },
      ],
      ferramentas: [],
      pessoal: [{ qualificacao_codigo: 'motorista_b', qtd: 1, opcional: 1 }],
    },
  ];

  // ── Relevância de estoque por categoria ──────────────────────────────────
  const estoque_relevancia = {
    climatizacao:    ['GAS-R410A', 'OLE-15W40-1L', 'FIL-AR-VTR'],
    eletrica:        ['OLE-15W40-1L', 'FIL-AR-VTR'],
    frota_terrestre: ['OLE-15W40-1L', 'FIL-AR-VTR'],
    frota_naval:     ['OLE-15W40-1L'],
    maquinas_corte:  ['pe02', 'pe05', 'pe08', 'pe22', 'pe23'],
    predial:         ['TIN-EPX-5L'],
    instrumentos:    [],
  };

  // ── Qualificações requeridas ──────────────────────────────────────────────
  const qualificacoes_catalogo = [
    { codigo: 'tec_refrig',       nome: 'Técnico em Refrigeração',          requer_validade: 1, usuarios: 3 },
    { codigo: 'eletricista_nr10', nome: 'Eletricista NR-10',                 requer_validade: 1, usuarios: 5 },
    { codigo: 'soldador',         nome: 'Soldador qualificado',              requer_validade: 1, usuarios: 2 },
    { codigo: 'operador_munk',    nome: 'Operador de Munk',                  requer_validade: 1, usuarios: 1 },
    { codigo: 'motorista_b',      nome: 'Motorista categoria B',             requer_validade: 1, usuarios: 12 },
    { codigo: 'motorista_d',      nome: 'Motorista categoria D',             requer_validade: 1, usuarios: 3 },
    { codigo: 'arrais',           nome: 'Arrais Amador',                      requer_validade: 1, usuarios: 2 },
    { codigo: 'operador_corte',   nome: 'Operador de máquina de corte',      requer_validade: 1, usuarios: 4 },
  ];

  const documentos_pop = [
    { id: 'doc-pop-limp-split-v2', nome: 'POP — Limpeza padrão split (v2)', tipo: 'pop', versao: 2 },
    { id: 'doc-pop-gmg-v1',        nome: 'POP — Manutenção GMG (250h)',     tipo: 'pop', versao: 1 },
  ];

  function deriveTipoPlanServices() {
    return Object.entries(TIPOS).flatMap(([tipoCodigo, tipo]) => (tipo.plano || []).map(planoItem => ({
      id: `svc-plano-${String(tipoCodigo).toLowerCase()}-${planoItem.id}`,
      codigo: `${String(tipoCodigo).toUpperCase()}_${String(planoItem.id).toUpperCase()}`,
      nome: planoItem.n,
      descricao: `Plano preventivo por horímetro para ${tipo.nome}.`,
      escopo: 'tipo',
      versao: 1,
      tempo_estimado_min: Math.max(30, 20 + ((planoItem.its || []).length * 15)),
      servico_pai_id: null,
      aplicavel_a: { categorias: tipo.categoria ? [tipo.categoria] : [], tipos: [tipoCodigo] },
      criado_por_modulo: 'manutencao',
      ativo: 1,
      materiais: (planoItem.its || []).map(nome => ({ nome_livre: nome, qtd: 1, unidade: 'un', obrigatorio: 1 })),
      ferramentas: [],
      pessoal: [{ qualificacao_codigo: 'operador_corte', qtd: 1, opcional: 0 }],
    })));
  }

  function deriveTipoPlanos() {
    return Object.entries(TIPOS).flatMap(([tipoCodigo, tipo]) => (tipo.plano || []).map(planoItem => ({
      id: `plan-${String(tipoCodigo).toLowerCase()}-${planoItem.id}`,
      servico_id: `svc-plano-${String(tipoCodigo).toLowerCase()}-${planoItem.id}`,
      servico_versao_pin: null,
      ativo_id: null,
      tipo_codigo: tipoCodigo,
      frequencia: { tipo: 'por_uso', valor: planoItem.iv, unidade: 'h' },
      criticidade_override: null,
      janela_permitida: null,
      proxima_execucao: null,
      ultima_execucao: null,
      responsavel_pmoc: 'manutencao',
      obs: `Plano derivado automaticamente de ${tipo.nome}.`,
      ativo: 1,
      criado_por_modulo: 'manutencao',
    })));
  }

  const derived_catalogo_servicos = deriveTipoPlanServices();
  const planos_manutencao = deriveTipoPlanos();

  window.ERP_MANUT_MOCKS = {
    TIPOS,
    UNIDADES_DEFAULT,
    PECAS_DEFAULT,
    ITENS_EAM,
    VALORES_EAM,
    catalogo_servicos: [...catalogo_servicos, ...derived_catalogo_servicos],
    estoque_relevancia,
    qualificacoes_catalogo,
    documentos_pop,
    planos_manutencao,
  };
})();
