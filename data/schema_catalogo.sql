-- xCMASM · Schema do Catálogo de Manutenção + Sync (núcleo magro v2)
-- Adicionado em 2026-05-18. Aditivo: usa CREATE TABLE IF NOT EXISTS.
-- Referências: Rules.md §§10-15, MODULOS_EXTERNOS.md §3, REQUISITOS.md §3.7-3.9

PRAGMA foreign_keys = ON;

-- ========================================================
-- 1. DOCUMENTOS (POPs, certificados, fotos, normas)
--    Declarado antes do catálogo porque catalogo_servicos.pop_doc_id aponta para cá.
-- ========================================================

CREATE TABLE IF NOT EXISTS documentos (
  id               TEXT PRIMARY KEY,                  -- UUID
  nome             TEXT NOT NULL,
  tipo             TEXT,                              -- pop | certificado | foto | norma | relatorio | outro
  mime             TEXT,
  tamanho_bytes    INTEGER,
  sha256           TEXT,
  storage_path     TEXT,                              -- caminho relativo ou URL
  conteudo_inline  TEXT,                              -- markdown/texto curto direto no DB
  vinculo_tipo     TEXT,                              -- ativo | os | local | servico | usuario | NULL
  vinculo_id       TEXT,
  versao           INTEGER NOT NULL DEFAULT 1,
  substitui_doc_id TEXT REFERENCES documentos(id),
  restrito         INTEGER NOT NULL DEFAULT 0,        -- 1 = visível só p/ lotacao_id
  lotacao_id       TEXT REFERENCES estrutura(id),
  criado_por       INTEGER REFERENCES usuarios(id),
  criado_em        DATETIME DEFAULT CURRENT_TIMESTAMP,
  ativo            INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_docs_vinculo ON documentos(vinculo_tipo, vinculo_id);
CREATE INDEX IF NOT EXISTS idx_docs_tipo    ON documentos(tipo, ativo);

-- ========================================================
-- 2. CATÁLOGO DE SERVIÇOS (híbrido: escopo central | local)
-- ========================================================

CREATE TABLE IF NOT EXISTS catalogo_servicos (
  id                  TEXT PRIMARY KEY,              -- UUID
  codigo              TEXT NOT NULL,                 -- slug (LIMP_SPLIT_PADRAO)
  nome                TEXT NOT NULL,
  descricao           TEXT,
  escopo              TEXT NOT NULL DEFAULT 'central'
                       CHECK (escopo IN ('central','local')),
  versao              INTEGER NOT NULL DEFAULT 1,
  pop_doc_id          TEXT REFERENCES documentos(id),
  tempo_estimado_min  INTEGER,
  servico_pai_id      TEXT REFERENCES catalogo_servicos(id),
  aplicavel_a         TEXT,                          -- JSON {"categorias":[...],"tipos":[...]}
  criado_por_modulo   TEXT NOT NULL DEFAULT 'manutencao',
  criado_por          INTEGER REFERENCES usuarios(id),
  criado_em           DATETIME DEFAULT CURRENT_TIMESTAMP,
  atualizado_em       DATETIME DEFAULT CURRENT_TIMESTAMP,
  ativo               INTEGER NOT NULL DEFAULT 1,
  UNIQUE (codigo, versao)
);
CREATE INDEX IF NOT EXISTS idx_servicos_escopo ON catalogo_servicos(escopo, ativo);
CREATE INDEX IF NOT EXISTS idx_servicos_codigo ON catalogo_servicos(codigo, ativo);
CREATE INDEX IF NOT EXISTS idx_servicos_pai    ON catalogo_servicos(servico_pai_id);

CREATE TABLE IF NOT EXISTS catalogo_servico_materiais (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  servico_id   TEXT NOT NULL REFERENCES catalogo_servicos(id) ON DELETE CASCADE,
  material_id  INTEGER REFERENCES estoque(id),       -- nullable: pode ser nome livre
  nome_livre   TEXT,                                 -- usado quando material_id IS NULL
  qtd          REAL NOT NULL,
  unidade      TEXT NOT NULL,
  obrigatorio  INTEGER NOT NULL DEFAULT 1,
  obs          TEXT,
  CHECK (material_id IS NOT NULL OR nome_livre IS NOT NULL)
);
CREATE INDEX IF NOT EXISTS idx_csm_servico ON catalogo_servico_materiais(servico_id);

CREATE TABLE IF NOT EXISTS catalogo_servico_ferramentas (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  servico_id   TEXT NOT NULL REFERENCES catalogo_servicos(id) ON DELETE CASCADE,
  nome         TEXT NOT NULL,
  qtd          INTEGER NOT NULL DEFAULT 1,
  obrigatorio  INTEGER NOT NULL DEFAULT 1,
  obs          TEXT
);
CREATE INDEX IF NOT EXISTS idx_csf_servico ON catalogo_servico_ferramentas(servico_id);

CREATE TABLE IF NOT EXISTS catalogo_servico_pessoal (
  id                    INTEGER PRIMARY KEY AUTOINCREMENT,
  servico_id            TEXT NOT NULL REFERENCES catalogo_servicos(id) ON DELETE CASCADE,
  qualificacao_codigo   TEXT NOT NULL,               -- FK lógica → qualificacoes_catalogo.codigo
  qtd                   INTEGER NOT NULL DEFAULT 1,
  opcional              INTEGER NOT NULL DEFAULT 0,
  obs                   TEXT
);
CREATE INDEX IF NOT EXISTS idx_csp_servico ON catalogo_servico_pessoal(servico_id);

CREATE TABLE IF NOT EXISTS catalogo_condicionais (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  servico_id   TEXT NOT NULL REFERENCES catalogo_servicos(id) ON DELETE CASCADE,
  expressao    TEXT NOT NULL,                        -- DSL (Rules.md §14)
  descricao    TEXT,
  bloqueante   INTEGER NOT NULL DEFAULT 1            -- 0 = warning, 1 = adia geração
);
CREATE INDEX IF NOT EXISTS idx_csc_servico ON catalogo_condicionais(servico_id);

-- ========================================================
-- 3. PLANOS DE MANUTENÇÃO (liga serviço × ativo/tipo × frequência)
-- ========================================================

CREATE TABLE IF NOT EXISTS planos_manutencao (
  id                    TEXT PRIMARY KEY,            -- UUID
  servico_id            TEXT NOT NULL REFERENCES catalogo_servicos(id),
  servico_versao_pin    INTEGER,                     -- nullable = sempre versão vigente
  ativo_id              TEXT REFERENCES ativos(id),  -- 1 dos 2 (XOR via CHECK abaixo)
  tipo_codigo           TEXT,                        -- aplica a todos do tipo (ex: AC_SPLIT)
  frequencia            TEXT NOT NULL,               -- JSON
  criticidade_override  TEXT
                         CHECK (criticidade_override IS NULL OR
                                criticidade_override IN ('admin','operacional','critico_24x7')),
  janela_permitida      TEXT,                        -- JSON
  proxima_execucao      DATE,
  ultima_execucao       DATE,
  responsavel_pmoc      TEXT,                        -- override do ativo.responsavel_pmoc
  obs                   TEXT,
  ativo                 INTEGER NOT NULL DEFAULT 1,
  criado_por_modulo     TEXT NOT NULL DEFAULT 'manutencao',
  criado_em             DATETIME DEFAULT CURRENT_TIMESTAMP,
  atualizado_em         DATETIME DEFAULT CURRENT_TIMESTAMP,
  CHECK (
    (ativo_id IS NOT NULL AND tipo_codigo IS NULL) OR
    (ativo_id IS NULL AND tipo_codigo IS NOT NULL)
  )
);
CREATE INDEX IF NOT EXISTS idx_planos_ativo    ON planos_manutencao(ativo_id);
CREATE INDEX IF NOT EXISTS idx_planos_tipo     ON planos_manutencao(tipo_codigo);
CREATE INDEX IF NOT EXISTS idx_planos_servico  ON planos_manutencao(servico_id);
CREATE INDEX IF NOT EXISTS idx_planos_proxima  ON planos_manutencao(proxima_execucao);

-- ========================================================
-- 4. QUALIFICAÇÕES DE PESSOAL
-- ========================================================

CREATE TABLE IF NOT EXISTS qualificacoes_catalogo (
  codigo            TEXT PRIMARY KEY,                -- 'tec_refrig'
  nome              TEXT NOT NULL,
  descricao         TEXT,
  requer_validade   INTEGER NOT NULL DEFAULT 1,
  ativo             INTEGER NOT NULL DEFAULT 1,
  criado_em         DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS usuario_qualificacoes (
  id                    INTEGER PRIMARY KEY AUTOINCREMENT,
  usuario_id            INTEGER NOT NULL REFERENCES usuarios(id),
  qualificacao_codigo   TEXT NOT NULL REFERENCES qualificacoes_catalogo(codigo),
  obtida_em             DATE,
  valida_ate            DATE,
  doc_id                TEXT REFERENCES documentos(id),
  status                TEXT NOT NULL DEFAULT 'valida'
                         CHECK (status IN ('valida','vencida','suspensa')),
  obs                   TEXT,
  criado_em             DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (usuario_id, qualificacao_codigo)
);
CREATE INDEX IF NOT EXISTS idx_uq_usuario  ON usuario_qualificacoes(usuario_id);
CREATE INDEX IF NOT EXISTS idx_uq_validade ON usuario_qualificacoes(valida_ate, status);

-- ========================================================
-- 5. SYNC: módulos registrados, eventos, cursor
-- ========================================================

CREATE TABLE IF NOT EXISTS modulos_registrados (
  nome              TEXT PRIMARY KEY,                -- 'pmoc_refrigeracao'
  descricao         TEXT,
  url_navegacao     TEXT,
  categorias_atend  TEXT,                            -- JSON: ["climatizacao"]
  ativo             INTEGER NOT NULL DEFAULT 1,
  criado_em         DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sync_eventos (
  id               TEXT PRIMARY KEY,                 -- UUID gerado pelo PMOC (idempotência)
  modulo           TEXT NOT NULL REFERENCES modulos_registrados(nome),
  device_id        TEXT NOT NULL,
  usuario_id       INTEGER REFERENCES usuarios(id),
  tipo             TEXT NOT NULL,
                   -- ps_criada | os_criada | os_status | os_executada |
                   -- uso_atual_inc | estoque_mov | documento_anexo |
                   -- inspecao_concluida | plano_adiado | qualificacao_uso
  payload          TEXT NOT NULL,                    -- JSON
  ts_origem        DATETIME NOT NULL,                -- timestamp no device
  recebido_em      DATETIME DEFAULT CURRENT_TIMESTAMP,
  status           TEXT NOT NULL DEFAULT 'pendente'
                    CHECK (status IN ('pendente','processado','rejeitado','descartado_obsoleto')),
  motivo_rejeicao  TEXT,
  processado_em    DATETIME
);
CREATE INDEX IF NOT EXISTS idx_sync_mod_status   ON sync_eventos(modulo, status);
CREATE INDEX IF NOT EXISTS idx_sync_device       ON sync_eventos(modulo, device_id, recebido_em);
CREATE INDEX IF NOT EXISTS idx_sync_tipo         ON sync_eventos(tipo, recebido_em);

CREATE TABLE IF NOT EXISTS sync_cursor (
  modulo            TEXT NOT NULL REFERENCES modulos_registrados(nome),
  device_id         TEXT NOT NULL,
  ultimo_evento_id  TEXT,                            -- ref. lógica (não FK forte p/ permitir purge)
  ultimo_push_em    DATETIME,
  ultimo_pull_em    DATETIME,
  atualizado_em     DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (modulo, device_id)
);

-- ========================================================
-- 6. SEEDS MÍNIMOS (independentes de domínio)
-- ========================================================

INSERT OR IGNORE INTO modulos_registrados (nome, descricao, categorias_atend) VALUES
  ('pmoc_refrigeracao', 'Climatização (splits, central)',         '["climatizacao"]'),
  ('pmoc_eletrica',     'Elétrica e geradores',                   '["eletrica"]'),
  ('pmoc_predial',      'Locais e inspeção predial',              '["predial"]'),
  ('pmoc_paiois',       'Paiois e inventário militar',            '["paiois_item"]'),
  ('pmoc_transportes',  'Viaturas e embarcações',                 '["frota_terrestre","frota_naval"]'),
  ('pmoc_grama',        'Controle vegetal / máquinas de corte',   '["maquinas_corte"]'),
  ('pmoc_calibracao',   'Instrumentos calibrados',                '["instrumentos"]');

INSERT OR IGNORE INTO qualificacoes_catalogo (codigo, nome, descricao, requer_validade) VALUES
  ('tec_refrig',        'Técnico em Refrigeração',           'NR-34 + curso técnico em refrigeração',         1),
  ('eletricista_nr10',  'Eletricista NR-10',                  'Habilitação para serviços em eletricidade',    1),
  ('soldador',          'Soldador qualificado',               'Treinamento em solda elétrica/oxiacetilênica', 1),
  ('operador_munk',     'Operador de Munk',                   'NR-11 + treinamento Munk',                     1),
  ('motorista_b',       'Motorista categoria B',              'CNH B vigente',                                1),
  ('motorista_d',       'Motorista categoria D',              'CNH D vigente (transporte de pessoal)',        1),
  ('arrais',            'Arrais Amador',                      'Habilitação náutica para embarcações',         1),
  ('operador_corte',    'Operador de máquina de corte',       'NR-12 + EPI específico',                       1);

-- ========================================================
-- 6. PLANO = CONJUNTO DE SERVIÇOS (template por tipo/variante de máquina)
--    Adicionado 2026-06-23. Difere de planos_manutencao (agendamento por ativo):
--    aqui é o "cardápio" de serviços de um plano (ex: Preventiva Split 18kBTU).
-- ========================================================
CREATE TABLE IF NOT EXISTS catalogo_planos (
  id            TEXT PRIMARY KEY,
  codigo        TEXT UNIQUE NOT NULL,          -- G1..G12 (ATA2)
  nome          TEXT NOT NULL,                 -- "Split 18.000 BTU — até 3m"
  categoria     TEXT NOT NULL DEFAULT 'climatizacao',
  tipo_codigo   TEXT,                          -- AC_SPLIT | AC_JANELA | ...
  btu           INTEGER,
  inverter      INTEGER NOT NULL DEFAULT 0,
  altura_max_m  REAL,                          -- 3 | 10 (condição de execução)
  fonte         TEXT,
  ativo         INTEGER NOT NULL DEFAULT 1,
  criado_em     DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS catalogo_plano_itens (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  plano_id    TEXT NOT NULL REFERENCES catalogo_planos(id) ON DELETE CASCADE,
  servico_id  TEXT NOT NULL REFERENCES catalogo_servicos(id),
  seq         INTEGER NOT NULL DEFAULT 0,
  classe      TEXT NOT NULL DEFAULT 'prev',    -- prev (preventivo) | corr (corretivo sob demanda)
  item_arp    INTEGER,                         -- nº original do item na ATA2
  valor_unit  REAL,
  qtd_ata     REAL,
  lim_adesao  REAL,
  qtd_cmasm   REAL,
  UNIQUE (plano_id, servico_id)
);
CREATE INDEX IF NOT EXISTS idx_plano_itens_plano ON catalogo_plano_itens(plano_id);
CREATE INDEX IF NOT EXISTS idx_plano_itens_svc   ON catalogo_plano_itens(servico_id);
CREATE INDEX IF NOT EXISTS idx_catalogo_planos_cat ON catalogo_planos(categoria, ativo);
