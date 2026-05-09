-- ============================================================
-- xPredial — Schema SQLite  v1.1
-- NBR 5674:2012 · NBR 16747:2020
-- ============================================================

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- ── NORMAS ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS normas (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo      TEXT NOT NULL UNIQUE,
    titulo      TEXT NOT NULL,
    orgao       TEXT DEFAULT 'ABNT',
    ano         INTEGER,
    descricao   TEXT,
    url         TEXT,
    ativo       INTEGER DEFAULT 1,
    created_at  TEXT DEFAULT (datetime('now'))
);

-- ── LOCAIS ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS locais (
    id          INTEGER PRIMARY KEY,
    codigo      TEXT UNIQUE,
    neo         TEXT,
    nome        TEXT NOT NULL,
    tipo        TEXT,
    area        TEXT CHECK(area IN ('ADM','OPE','APA') OR area IS NULL),
    restricao   TEXT DEFAULT 'civil'
                     CHECK(restricao IN ('civil','militar','reservado','secreto','proibido')),
    parent_id   INTEGER REFERENCES locais(id),
    descricao   TEXT,
    ativo       INTEGER DEFAULT 1,
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_locais_parent ON locais(parent_id);
CREATE INDEX IF NOT EXISTS idx_locais_tipo   ON locais(tipo);
CREATE INDEX IF NOT EXISTS idx_locais_neo    ON locais(neo);

-- ── CHECKLIST TEMPLATES ─────────────────────────────────────
CREATE TABLE IF NOT EXISTS checklist_templates (
    id          INTEGER PRIMARY KEY,
    nome        TEXT NOT NULL,
    tipo_local  TEXT,
    descricao   TEXT,
    norma_ref   TEXT DEFAULT 'NBR 5674:2012',
    ativo       INTEGER DEFAULT 1,
    created_at  TEXT DEFAULT (datetime('now'))
);

-- ── CHECKLIST TEMPLATE ITEMS ─────────────────────────────────
CREATE TABLE IF NOT EXISTS checklist_template_items (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    template_id INTEGER NOT NULL REFERENCES checklist_templates(id),
    sistema     TEXT NOT NULL,
    subsistema  TEXT,
    descricao   TEXT NOT NULL,
    ordem       INTEGER DEFAULT 0,
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_cti_template ON checklist_template_items(template_id);
CREATE INDEX IF NOT EXISTS idx_cti_sistema  ON checklist_template_items(sistema);

-- ── INSPEÇÕES ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS inspecoes (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo               TEXT NOT NULL,
    local_id             INTEGER REFERENCES locais(id),
    local_ids            TEXT,
    template_id          INTEGER REFERENCES checklist_templates(id),
    responsavel_tecnico  TEXT,
    data_vistoria        TEXT,
    status               TEXT DEFAULT 'planejada'
                              CHECK(status IN (
                                'planejada','em_execucao',
                                'aguardando_aprovacao','aprovada',
                                'reprovada','concluida')),
    nivel                TEXT DEFAULT '1' CHECK(nivel IN ('1','2','3')),
    tipo_inspecao        TEXT DEFAULT 'extrínseca'
                              CHECK(tipo_inspecao IN ('intrínseca','extrínseca','ambas')),
    servico_id           INTEGER,
    observacoes          TEXT,
    created_at           TEXT DEFAULT (datetime('now')),
    updated_at           TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_insp_local  ON inspecoes(local_id);
CREATE INDEX IF NOT EXISTS idx_insp_status ON inspecoes(status);
CREATE INDEX IF NOT EXISTS idx_insp_data   ON inspecoes(data_vistoria);

-- ── INSPEÇÃO ITENS ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS inspecao_itens (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    inspecao_id INTEGER NOT NULL REFERENCES inspecoes(id) ON DELETE CASCADE,
    descricao   TEXT NOT NULL,
    categoria   TEXT,
    condicao    TEXT DEFAULT 'ok'
                     CHECK(condicao IN ('ok','atencao','critico')),
    g           INTEGER DEFAULT 0,
    u           INTEGER DEFAULT 0,
    t           INTEGER DEFAULT 0,
    gut_total   INTEGER DEFAULT 0,
    presente    INTEGER DEFAULT 0,
    local_ref   TEXT,
    foto_ref    TEXT,
    item_origem TEXT DEFAULT 'manual'
                     CHECK(item_origem IN ('template','manual')),
    observacao  TEXT,
    created_at  TEXT DEFAULT (datetime('now')),
    updated_at  TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_ii_inspecao ON inspecao_itens(inspecao_id);
CREATE INDEX IF NOT EXISTS idx_ii_condicao ON inspecao_itens(condicao);
CREATE INDEX IF NOT EXISTS idx_ii_gut      ON inspecao_itens(gut_total DESC);

-- ── LAUDOS ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS laudos (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    inspecao_id     INTEGER REFERENCES inspecoes(id),
    local_id        INTEGER REFERENCES locais(id),
    titulo          TEXT NOT NULL,
    tipo            TEXT DEFAULT 'laudo_inspecao'
                         CHECK(tipo IN (
                           'laudo_inspecao','art','rrt',
                           'relatorio_fotog','plano_manutencao','outro')),
    numero_art      TEXT,
    responsavel     TEXT,
    data_emissao    TEXT,
    data_validade   TEXT,
    conteudo        TEXT,
    arquivo_path    TEXT,
    status          TEXT DEFAULT 'rascunho'
                         CHECK(status IN ('rascunho','emitido','arquivado')),
    created_at      TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_laudos_insp  ON laudos(inspecao_id);
CREATE INDEX IF NOT EXISTS idx_laudos_local ON laudos(local_id);

-- ── WORKFLOW EVENTS (audit trail imutável) ───────────────────
CREATE TABLE IF NOT EXISTS workflow_events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    inspecao_id INTEGER NOT NULL REFERENCES inspecoes(id),
    de_status   TEXT,
    para_status TEXT NOT NULL,
    responsavel TEXT,
    motivo      TEXT,
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_wf_insp ON workflow_events(inspecao_id);

-- ── TRIGGERS ─────────────────────────────────────────────────
CREATE TRIGGER IF NOT EXISTS trg_insp_updated
    AFTER UPDATE ON inspecoes FOR EACH ROW BEGIN
        UPDATE inspecoes SET updated_at = datetime('now') WHERE id = OLD.id;
    END;

CREATE TRIGGER IF NOT EXISTS trg_ii_updated
    AFTER UPDATE ON inspecao_itens FOR EACH ROW BEGIN
        UPDATE inspecao_itens SET updated_at = datetime('now') WHERE id = OLD.id;
    END;

CREATE TRIGGER IF NOT EXISTS trg_gut_insert
    AFTER INSERT ON inspecao_itens
    FOR EACH ROW WHEN NEW.g > 0 AND NEW.u > 0 AND NEW.t > 0 BEGIN
        UPDATE inspecao_itens SET gut_total = NEW.g * NEW.u * NEW.t,
            condicao  = CASE
                WHEN (NEW.g * NEW.u * NEW.t) > 400 THEN 'critico'
                WHEN (NEW.g * NEW.u * NEW.t) > 100 THEN 'atencao'
                ELSE 'ok'
            END
        WHERE id = NEW.id;
    END;

CREATE TRIGGER IF NOT EXISTS trg_gut_update
    AFTER UPDATE OF g, u, t ON inspecao_itens FOR EACH ROW BEGIN
        UPDATE inspecao_itens
        SET gut_total = NEW.g * NEW.u * NEW.t,
            condicao  = CASE
                WHEN (NEW.g * NEW.u * NEW.t) > 400 THEN 'critico'
                WHEN (NEW.g * NEW.u * NEW.t) > 100 THEN 'atencao'
                ELSE 'ok'
            END
        WHERE id = NEW.id;
    END;
