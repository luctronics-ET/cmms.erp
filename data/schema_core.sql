-- xCore — Schema central do xCMASM
-- Migrado do localStorage do ERP_core (cmasm-erp.html)

CREATE TABLE IF NOT EXISTS usuarios (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  nome       TEXT NOT NULL,
  posto      TEXT,
  mat        TEXT UNIQUE,
  email      TEXT,
  tel        TEXT,
  tipo       TEXT DEFAULT 'militar' CHECK (tipo IN ('militar','civil')),
  role       TEXT DEFAULT 'operador' CHECK (role IN ('admin','gestor','operador','visualizador')),
  pw_hash    TEXT,
  ativo      INTEGER DEFAULT 1,
  telegram_chat_id TEXT,
  criado_em  DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Organograma (hardcoded no ERP → persistido aqui)
CREATE TABLE IF NOT EXISTS estrutura (
  id     TEXT PRIMARY KEY,   -- ex: CMASM-11.2
  tipo   TEXT NOT NULL,      -- departamento | divisao | secao | grupo | assessoria | servico | ...
  nome   TEXT NOT NULL,
  pai    TEXT,               -- FK para id desta tabela
  cargo  TEXT,               -- título do cargo
  ct     TEXT                -- chave de tipo de cargo (encarregado_secao etc.)
);

-- Quem ocupa cada posição
CREATE TABLE IF NOT EXISTS cargos (
  unidade_id TEXT PRIMARY KEY,
  usuario_id INTEGER,
  obs        TEXT,
  FOREIGN KEY (unidade_id) REFERENCES estrutura(id),
  FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);

-- Ativos (migrado de gestao-ativos.html)
CREATE TABLE IF NOT EXISTS ativos (
  id           TEXT PRIMARY KEY,   -- u01, u20 …
  tipo         TEXT NOT NULL,      -- FS220 | VTR_PICKUP | AC_SPLIT | GERADOR …
  categoria    TEXT NOT NULL,      -- maquinas_corte | viaturas | embarcacoes | climatizacao | eletrica | predial | outros
  nome         TEXT NOT NULL,
  pat          TEXT,               -- patrimônio / nº série
  loc          TEXT,               -- localização no CMASM
  obs          TEXT,
  ativo        INTEGER DEFAULT 1,
  uso_atual    REAL DEFAULT 0,     -- horímetro (h), odômetro (km) ou meses
  unidade_uso  TEXT DEFAULT 'h' CHECK (unidade_uso IN ('h','km','meses')),
  criado_em    DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Tokens de sessão (expiráveis)
CREATE TABLE IF NOT EXISTS sessoes (
  token      TEXT PRIMARY KEY,
  usuario_id INTEGER NOT NULL,
  criado_em  DATETIME DEFAULT CURRENT_TIMESTAMP,
  expira_em  DATETIME NOT NULL,
  FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);

-- Locais (prédios, salas, áreas externas, paiois)
CREATE TABLE IF NOT EXISTS locais (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  codigo      TEXT UNIQUE,          -- CMASM-10.2.1, G5, D5
  neo         TEXT,
  nome        TEXT NOT NULL,
  tipo        TEXT NOT NULL DEFAULT 'sala',  -- predio | sala | area_externa | paiol | instalacao
  area        TEXT DEFAULT 'OPE',   -- ADM | OPE | APA
  restricao   TEXT DEFAULT '',      -- civil | militar | reservado | secreto | proibido
  parent_id   INTEGER REFERENCES locais(id),
  estrutura_id TEXT REFERENCES estrutura(id),
  descricao   TEXT,
  area_m2     REAL,
  ativo       INTEGER DEFAULT 1,
  criado_em   DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Ordens de Serviço
CREATE TABLE IF NOT EXISTS ordens_servico (
  id             TEXT PRIMARY KEY,
  codigo         TEXT UNIQUE NOT NULL,
  titulo         TEXT NOT NULL,
  descricao      TEXT,
  tipo           TEXT NOT NULL DEFAULT 'corretiva',   -- corretiva | preventiva | preditiva | inspecao
  status         TEXT NOT NULL DEFAULT 'aberta',      -- aberta | em_andamento | aguardando | concluida | cancelada
  prioridade     TEXT NOT NULL DEFAULT 'media',       -- critica | alta | media | baixa
  categoria      TEXT,                                -- taxonomia de serviço (TRANSPORTE|MANUTENCAO|CONTROLE VEGETAL|CONTROLE BIOLOGICO)
  subcategoria   TEXT,                                -- subcategoria da taxonomia
  servicos       TEXT,                                -- JSON: [{nome, catalogo_id, origem}] passos da OS
  veiculos       TEXT,                                -- JSON: [{ativo_id, nome}] viaturas/embarcações
  modulo_origem  TEXT,                                -- xPredial | xGrama | xHVAC | xEletrica | xPaiol | manual
  solicitante_id INTEGER REFERENCES usuarios(id),
  responsavel_id INTEGER REFERENCES usuarios(id),
  local_id       INTEGER REFERENCES locais(id),
  data_abertura  TEXT NOT NULL DEFAULT (date('now')),
  data_prevista  TEXT,
  data_conclusao TEXT,
  custo_estimado REAL,
  custo_real     REAL,
  observacoes    TEXT,
  criado_em      DATETIME DEFAULT CURRENT_TIMESTAMP,
  atualizado_em  DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS os_historico (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  os_id       TEXT NOT NULL REFERENCES ordens_servico(id) ON DELETE CASCADE,
  status_de   TEXT,
  status_para TEXT NOT NULL,
  obs         TEXT,
  usuario_id  INTEGER REFERENCES usuarios(id),
  criado_em   DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS os_etapas (
  id        INTEGER PRIMARY KEY AUTOINCREMENT,
  os_id     TEXT NOT NULL REFERENCES ordens_servico(id) ON DELETE CASCADE,
  titulo    TEXT NOT NULL,
  concluida INTEGER NOT NULL DEFAULT 0,
  ordem     INTEGER NOT NULL DEFAULT 0,
  criado_em DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Estoque (materiais e consumíveis)
CREATE TABLE IF NOT EXISTS estoque (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  codigo      TEXT UNIQUE,
  nome        TEXT NOT NULL,
  categoria   TEXT NOT NULL DEFAULT 'material',  -- material | ferramenta | consumivel | epi | combustivel
  unidade     TEXT NOT NULL DEFAULT 'un',        -- un | kg | L | m | m2
  qtd_atual   REAL NOT NULL DEFAULT 0,
  qtd_minima  REAL NOT NULL DEFAULT 0,
  local_id       INTEGER REFERENCES locais(id),
  preco_unitario REAL DEFAULT 0,
  obs            TEXT,
  ativo       INTEGER DEFAULT 1,
  criado_em   DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS estoque_movimentos (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  item_id     INTEGER NOT NULL REFERENCES estoque(id),
  tipo        TEXT NOT NULL,   -- entrada | saida | ajuste
  quantidade  REAL NOT NULL,
  os_id       TEXT REFERENCES ordens_servico(id),
  usuario_id  INTEGER REFERENCES usuarios(id),
  obs         TEXT,
  criado_em   DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Portal do Colaborador (CompanyHub incorporado)
CREATE TABLE IF NOT EXISTS colab_events (
  id           TEXT PRIMARY KEY,
  title        TEXT NOT NULL,
  type         TEXT NOT NULL DEFAULT 'event',
  event_date   TEXT NOT NULL,
  location     TEXT,
  attendees    INTEGER DEFAULT 0,
  description  TEXT,
  created_em   DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_em   DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS colab_policies (
  id            TEXT PRIMARY KEY,
  title         TEXT NOT NULL,
  category      TEXT NOT NULL DEFAULT 'general',
  version       TEXT,
  description   TEXT,
  owner         TEXT,
  created_date  TEXT,
  updated_date  TEXT,
  created_em    DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_em    DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS colab_executives (
  id                  TEXT PRIMARY KEY,
  full_name           TEXT NOT NULL,
  position            TEXT NOT NULL,
  department          TEXT,
  email               TEXT,
  phone               TEXT,
  office_location     TEXT,
  years_with_company  INTEGER DEFAULT 0,
  bio                 TEXT,
  linkedin_url        TEXT,
  photo_url           TEXT,
  created_em          DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_em          DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS colab_announcements (
  id            TEXT PRIMARY KEY,
  title         TEXT NOT NULL,
  content       TEXT NOT NULL,
  priority      TEXT NOT NULL DEFAULT 'medium',
  author        TEXT,
  created_date  TEXT,
  created_em    DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_em    DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS colab_tickets (
  id               TEXT PRIMARY KEY,
  subject          TEXT NOT NULL,
  description      TEXT NOT NULL,
  category         TEXT NOT NULL DEFAULT 'other',
  priority         TEXT NOT NULL DEFAULT 'medium',
  status           TEXT NOT NULL DEFAULT 'open',
  requester_name   TEXT,
  requester_email  TEXT,
  department       TEXT,
  assigned_to      TEXT,
  resolution_notes TEXT,
  due_date         TEXT,
  created_date     TEXT,
  created_em       DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_em       DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS colab_timeoff (
  id              TEXT PRIMARY KEY,
  type            TEXT NOT NULL DEFAULT 'vacation',
  start_date      TEXT NOT NULL,
  end_date        TEXT NOT NULL,
  reason          TEXT,
  total_days      INTEGER DEFAULT 0,
  status          TEXT NOT NULL DEFAULT 'pending',
  employee_name   TEXT,
  employee_email  TEXT,
  department      TEXT,
  manager_email   TEXT,
  manager_notes   TEXT,
  approval_date   TEXT,
  created_date    TEXT,
  created_em      DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_em      DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Migração aditiva: campos extras em ativos
-- (ALTER TABLE só roda se a coluna não existir — verificado em db_core.py)

-- PMOC de Refrigeração / Climatização
CREATE TABLE IF NOT EXISTS pmoc_refrigeracao (
  id                  INTEGER PRIMARY KEY AUTOINCREMENT,
  ativo_id            TEXT REFERENCES ativos(id),
  local_id            INTEGER REFERENCES locais(id),
  -- Estado
  estado_operacional  TEXT DEFAULT 'OP',   -- OP | INOP
  est_idade           TEXT,                -- NOVA | SEMI | VELHA
  obs                 TEXT,
  -- Operação PMOC
  permanencia         INTEGER DEFAULT 0,   -- 1=permanente (X no CSV)
  criticidade         TEXT DEFAULT 'MÉDIA',-- CRÍTICA | ALTA | MÉDIA | BAIXA
  horas_dia           REAL,
  dias_semana         INTEGER,
  -- Elétrico
  tensao_nominal      REAL,
  tensao_medida       REAL,
  corrente_nominal    REAL,
  corrente_medida     REAL,
  potencia_kw         REAL,
  quadro              TEXT,
  disjuntor           TEXT,
  cabo                TEXT,
  -- Refrigerante
  gas_tipo            TEXT,                -- R-22 | R-410A | R-32 …
  carga_g             REAL,               -- carga estimada em gramas
  pressao_padrao      TEXT,
  pressao_medida      TEXT,
  pressao_data        TEXT,
  -- Temperaturas (padrão / medida)
  temp_evaporadora    TEXT,
  temp_evaporadora_m  TEXT,
  temp_centro         TEXT,
  temp_longe          TEXT,
  -- Inventário
  patrimonio          TEXT,
  data_instalacao     TEXT,
  ultima_manutencao   TEXT,
  -- Metadados
  pmoc_csv_id         INTEGER,            -- ID original do CSV para rastreabilidade
  criado_em           DATETIME DEFAULT CURRENT_TIMESTAMP,
  atualizado_em       DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_pmoc_refrig_ativo  ON pmoc_refrigeracao(ativo_id);
CREATE INDEX IF NOT EXISTS idx_pmoc_refrig_local  ON pmoc_refrigeracao(local_id);
CREATE INDEX IF NOT EXISTS idx_pmoc_refrig_estado ON pmoc_refrigeracao(estado_operacional);
CREATE INDEX IF NOT EXISTS idx_pmoc_refrig_crit   ON pmoc_refrigeracao(criticidade);

-- PMOC de Transportes (viaturas e embarcações)
CREATE TABLE IF NOT EXISTS pmoc_transportes (
  id                  INTEGER PRIMARY KEY AUTOINCREMENT,
  ativo_id            TEXT REFERENCES ativos(id),
  local_id            INTEGER REFERENCES locais(id),
  estado_operacional  TEXT DEFAULT 'OP',
  est_idade           TEXT,
  criticidade         TEXT DEFAULT 'operacional',
  obs                 TEXT,
  renavam             TEXT,
  licenciamento_ate   TEXT,
  seguro_ate          TEXT,
  registro_naval      TEXT,
  combustivel         TEXT,
  tanque_l            REAL,
  oleo_ultima_uso     REAL,
  pneus_estado        TEXT,
  bateria_estado      TEXT,
  casco_estado        TEXT,
  motor_obs           TEXT,
  data_aquisicao      TEXT,
  ultima_manutencao   TEXT,
  criado_em           DATETIME DEFAULT CURRENT_TIMESTAMP,
  atualizado_em       DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_pmoc_transp_ativo  ON pmoc_transportes(ativo_id);

-- PMOC de Corte (máquinas de corte de grama)
CREATE TABLE IF NOT EXISTS pmoc_corte (
  id                  INTEGER PRIMARY KEY AUTOINCREMENT,
  ativo_id            TEXT REFERENCES ativos(id),
  local_id            INTEGER REFERENCES locais(id),
  estado_operacional  TEXT DEFAULT 'OP',
  est_idade           TEXT,
  criticidade         TEXT DEFAULT 'operacional',
  obs                 TEXT,
  motor_tempos        INTEGER,
  combustivel         TEXT,
  oleo_tipo           TEXT,
  oleo_ultima_uso     REAL,
  ferramenta_corte    TEXT,
  data_aquisicao      TEXT,
  ultima_manutencao   TEXT,
  criado_em           DATETIME DEFAULT CURRENT_TIMESTAMP,
  atualizado_em       DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_pmoc_corte_ativo   ON pmoc_corte(ativo_id);

-- PMOC de Fonoclama (alto-falantes / ramais)
CREATE TABLE IF NOT EXISTS pmoc_fonoclama (
  id                  INTEGER PRIMARY KEY AUTOINCREMENT,
  ativo_id            TEXT REFERENCES ativos(id),
  local_id            INTEGER REFERENCES locais(id),
  estado_operacional  TEXT DEFAULT 'OP',
  est_idade           TEXT,
  criticidade         TEXT DEFAULT 'operacional',
  obs                 TEXT,
  potencia_w          REAL,
  impedancia          REAL,
  tensao_linha        REAL,
  data_instalacao     TEXT,
  ultima_manutencao   TEXT,
  criado_em           DATETIME DEFAULT CURRENT_TIMESTAMP,
  atualizado_em       DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_pmoc_fono_ativo    ON pmoc_fonoclama(ativo_id);

-- Índices
CREATE INDEX IF NOT EXISTS idx_usuarios_mat    ON usuarios(mat);
CREATE INDEX IF NOT EXISTS idx_usuarios_ativo  ON usuarios(ativo);
CREATE INDEX IF NOT EXISTS idx_ativos_cat      ON ativos(categoria);
CREATE INDEX IF NOT EXISTS idx_ativos_ativo    ON ativos(ativo);
CREATE INDEX IF NOT EXISTS idx_sessoes_expira  ON sessoes(expira_em);
CREATE INDEX IF NOT EXISTS idx_locais_pai      ON locais(parent_id);
CREATE INDEX IF NOT EXISTS idx_locais_ativo    ON locais(ativo);
CREATE INDEX IF NOT EXISTS idx_os_status       ON ordens_servico(status);
CREATE INDEX IF NOT EXISTS idx_os_modulo       ON ordens_servico(modulo_origem);
CREATE INDEX IF NOT EXISTS idx_os_local        ON ordens_servico(local_id);
CREATE INDEX IF NOT EXISTS idx_estoque_cat     ON estoque(categoria);
CREATE INDEX IF NOT EXISTS idx_estmov_item     ON estoque_movimentos(item_id);
CREATE INDEX IF NOT EXISTS idx_colab_events_date       ON colab_events(event_date);
CREATE INDEX IF NOT EXISTS idx_colab_policies_cat      ON colab_policies(category);
CREATE INDEX IF NOT EXISTS idx_colab_executives_dept   ON colab_executives(department);
CREATE INDEX IF NOT EXISTS idx_colab_announcements_dt  ON colab_announcements(created_date);
CREATE INDEX IF NOT EXISTS idx_colab_tickets_email     ON colab_tickets(requester_email);
CREATE INDEX IF NOT EXISTS idx_colab_tickets_status    ON colab_tickets(status);
CREATE INDEX IF NOT EXISTS idx_colab_timeoff_email     ON colab_timeoff(employee_email);
CREATE INDEX IF NOT EXISTS idx_colab_timeoff_status    ON colab_timeoff(status);

-- ════════════════════════════════════════════════════════════════════════════
-- PMOC Transportes (frota_terrestre=viaturas/km + frota_naval=embarcações/h)
-- Mesmo molde de pmoc_refrigeracao: ficha de detalhe 1:1 com ativos.
-- ════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS pmoc_transportes (
  id                  INTEGER PRIMARY KEY AUTOINCREMENT,
  ativo_id            TEXT REFERENCES ativos(id),
  local_id            INTEGER REFERENCES locais(id),
  -- Estado
  estado_operacional  TEXT DEFAULT 'OP',    -- OP | INOP
  est_idade           TEXT,                 -- NOVA | SEMI | VELHA
  criticidade         TEXT DEFAULT 'MÉDIA', -- CRÍTICA | ALTA | MÉDIA | BAIXA
  obs                 TEXT,
  -- Documentação (viatura) / registro (embarcação)
  renavam             TEXT,
  licenciamento_ate   TEXT,                 -- vencimento licenciamento (vtr)
  seguro_ate          TEXT,
  registro_naval      TEXT,                 -- TIE / Cap. Portos (emb)
  -- Propulsão
  combustivel         TEXT,                 -- diesel | gasolina | flex
  tanque_l            REAL,
  -- Manutenção mecânica
  oleo_ultima_uso     REAL,                 -- uso_atual (km/h) na última troca de óleo
  pneus_estado        TEXT,                 -- BOM | REGULAR | RUIM (vtr)
  bateria_estado      TEXT,
  casco_estado        TEXT,                 -- (emb)
  motor_obs           TEXT,
  data_aquisicao      TEXT,
  ultima_manutencao   TEXT,
  -- Metadados
  criado_em           DATETIME DEFAULT CURRENT_TIMESTAMP,
  atualizado_em       DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_pmoc_transp_ativo  ON pmoc_transportes(ativo_id);
CREATE INDEX IF NOT EXISTS idx_pmoc_transp_estado ON pmoc_transportes(estado_operacional);

-- ════════════════════════════════════════════════════════════════════════════
-- PMOC Corte (maquinas_corte: roçadeiras, cortadores, motosserras, trator) por hora
-- ════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS pmoc_corte (
  id                  INTEGER PRIMARY KEY AUTOINCREMENT,
  ativo_id            TEXT REFERENCES ativos(id),
  local_id            INTEGER REFERENCES locais(id),
  -- Estado
  estado_operacional  TEXT DEFAULT 'OP',    -- OP | INOP
  est_idade           TEXT,                 -- NOVA | SEMI | VELHA
  criticidade         TEXT DEFAULT 'MÉDIA',
  obs                 TEXT,
  -- Motor
  motor_tempos        TEXT,                 -- 2T | 4T | diesel
  combustivel         TEXT,                 -- gasolina | mistura_2t | diesel
  oleo_tipo           TEXT,                 -- SAE30 | 10W-30 | 15W-40
  oleo_ultima_uso     REAL,                 -- horas na última troca de óleo
  -- Corte
  ferramenta_corte    TEXT,                 -- nylon | lamina | corrente | deck
  -- Manutenção
  data_aquisicao      TEXT,
  ultima_manutencao   TEXT,
  -- Metadados
  criado_em           DATETIME DEFAULT CURRENT_TIMESTAMP,
  atualizado_em       DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_pmoc_corte_ativo  ON pmoc_corte(ativo_id);
CREATE INDEX IF NOT EXISTS idx_pmoc_corte_estado ON pmoc_corte(estado_operacional);

-- ════════════════════════════════════════════════════════════════════════════
-- PMOC Fonoclama (sistema de aviso sonoro: amplificadores, consoles, cornetas,
-- linhas 70V, sirenes). Legado migrado de xFonoclama/fonoclama.html.
-- ════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS pmoc_fonoclama (
  id                  INTEGER PRIMARY KEY AUTOINCREMENT,
  ativo_id            TEXT REFERENCES ativos(id),
  local_id            INTEGER REFERENCES locais(id),
  -- Estado
  estado_operacional  TEXT DEFAULT 'OP',    -- OP | INOP
  est_idade           TEXT,
  criticidade         TEXT DEFAULT 'ALTA',  -- aviso sonoro tende a ser crítico
  obs                 TEXT,
  -- Áudio / elétrico
  potencia_w          REAL,
  impedancia          TEXT,                 -- 8Ω | 70V | 100V
  tensao_linha        TEXT,
  -- Manutenção
  data_instalacao     TEXT,
  ultima_manutencao   TEXT,
  -- Metadados
  criado_em           DATETIME DEFAULT CURRENT_TIMESTAMP,
  atualizado_em       DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_pmoc_fono_ativo  ON pmoc_fonoclama(ativo_id);
CREATE INDEX IF NOT EXISTS idx_pmoc_fono_estado ON pmoc_fonoclama(estado_operacional);
