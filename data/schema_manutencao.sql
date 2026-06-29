-- xCMASM · Schema de Manutenção — uso_registros
-- Fase 01: Registrar Uso. Aditivo — CREATE TABLE IF NOT EXISTS obrigatório.
-- Ref: Rules.md §15, CONTEXT.md Phase 1, REQUISITOS.md §3.7 (IMP-01).

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS uso_registros (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  ativo_id       TEXT    NOT NULL REFERENCES ativos(id),
  delta          REAL    NOT NULL,                        -- incremento aplicado (positivo)
  valor_anterior REAL    NOT NULL,                        -- uso_atual antes do registro (snapshot)
  valor_novo     REAL    NOT NULL,                        -- uso_atual após o registro (= valor_anterior + delta)
  data           TEXT    NOT NULL,                        -- data da operação (ISO 8601: YYYY-MM-DD)
  operador       TEXT,                                    -- nome/mat do usuário logado (snapshot)
  observacao     TEXT,                                    -- campo livre opcional
  created_at     TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_uso_registros_ativo ON uso_registros(ativo_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_uso_registros_data  ON uso_registros(data);

-- ============================================================
-- Fase 02: Plano no Ativo — IMP-02 (CONTEXT.md Phase 2).
-- Tabelas de estado por item por ativo + trilha de execução.
-- Aditivo: CREATE TABLE IF NOT EXISTS, nunca DROP/ALTER.
-- ============================================================

-- Estado persistido por (ativo, item-do-plano): substitui o dict ulm do legado.
-- proximo_uso e ultimo_uso DEVEM ser REAL para comparação numérica com uso_atual
-- (TEXT causaria comparação lexicográfica — Pitfall 3 do RESEARCH.md).
CREATE TABLE IF NOT EXISTS ativo_plano_estado (
  ativo_id               TEXT    NOT NULL REFERENCES ativos(id),
  catalogo_plano_item_id INTEGER NOT NULL REFERENCES catalogo_plano_itens(id),
  ultimo_uso             REAL    NOT NULL DEFAULT 0,  -- uso_no_momento no último registro
  proximo_uso            REAL    NOT NULL,             -- ultimo_uso + intervalo
  updated_at             TEXT    NOT NULL DEFAULT (datetime('now')),
  PRIMARY KEY (ativo_id, catalogo_plano_item_id)
);
CREATE INDEX IF NOT EXISTS idx_ape_ativo ON ativo_plano_estado(ativo_id);

-- Trilha de execução de manutenção: um row por POST /registro bem-sucedido.
-- uso_no_momento lido de ativos.uso_atual DENTRO da transação (anti-double-count).
CREATE TABLE IF NOT EXISTS manut_registros (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  ativo_id        TEXT    NOT NULL REFERENCES ativos(id),
  responsavel     TEXT    NOT NULL,
  operador        TEXT,                                -- snapshot do usuário do token
  data            TEXT    NOT NULL,                    -- ISO YYYY-MM-DD
  uso_no_momento  REAL    NOT NULL,                    -- uso_atual lido dentro da txn
  itens_json      TEXT    NOT NULL,                    -- JSON array de catalogo_plano_item_id
  observacao      TEXT,
  created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_mr_ativo ON manut_registros(ativo_id, created_at DESC);

-- ============================================================
-- Fase 03: Estoque de Sobressalentes — IMP-03 (CONTEXT.md Phase 3).
-- Tabelas SEPARADAS de estoque/estoque_movimentos (SC: sem mistura).
-- Aditivo: CREATE TABLE IF NOT EXISTS, nunca DROP/ALTER.
-- ============================================================

-- Peças do estoque local dos técnicos (SEPARADO do estoque central).
-- categoria alinhada com refrigeração: consumivel | sobressalente | ferramenta.
-- qtd_atual e qtd_minima como REAL para compatibilidade numérica com uso_atual.
CREATE TABLE IF NOT EXISTS sobressalentes (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  codigo          TEXT UNIQUE,                                      -- código opcional (único se informado)
  nome            TEXT    NOT NULL,                                  -- nome da peça (obrigatório)
  categoria       TEXT    NOT NULL DEFAULT 'sobressalente',         -- consumivel | sobressalente | ferramenta
  unidade         TEXT    NOT NULL DEFAULT 'un',                    -- un | kg | L | m | m2
  qtd_atual       REAL    NOT NULL DEFAULT 0,                       -- estoque atual
  qtd_minima      REAL    NOT NULL DEFAULT 0,                       -- limiar BAIXO/OK
  preco_unitario  REAL             DEFAULT 0,                       -- para cálculo do valor estimado
  obs             TEXT,                                             -- campo livre opcional
  ativo           INTEGER          DEFAULT 1,                       -- soft-delete: 0 = inativo
  criado_em       TEXT    NOT NULL DEFAULT (datetime('now'))        -- timestamp de criação
);

-- Histórico de movimentos de ajuste do estoque de sobressalentes.
-- operador = snapshot do usuário do token (nunca do payload — T-03-02).
CREATE TABLE IF NOT EXISTS sobressalentes_movimentos (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  item_id     INTEGER NOT NULL REFERENCES sobressalentes(id),       -- FK para a peça
  tipo        TEXT    NOT NULL,                                      -- entrada | saida | ajuste
  quantidade  REAL    NOT NULL,                                      -- quantidade do movimento
  motivo      TEXT,                                                  -- motivo do ajuste (livre)
  obs         TEXT,                                                  -- campo livre opcional
  operador    TEXT,                                                  -- snapshot do usuário do token
  created_at  TEXT    NOT NULL DEFAULT (datetime('now'))            -- timestamp do movimento
);

-- Índice composto para histórico newest-first por item (ORDER BY created_at DESC).
CREATE INDEX IF NOT EXISTS idx_sob_mov_item ON sobressalentes_movimentos(item_id, created_at DESC);
