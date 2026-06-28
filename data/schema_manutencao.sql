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
