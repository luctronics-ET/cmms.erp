PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS locais (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	codigo TEXT,
	neo TEXT,
	area TEXT CHECK(area IS NULL OR area IN ('ADM','OPE','APA')),
	endereco TEXT,
	restricao TEXT CHECK(restricao IS NULL OR restricao IN ('', 'civil', 'militar', 'reservado', 'secreto', 'proibido')),
	nome TEXT NOT NULL,
	tipo TEXT NOT NULL,
	parent_id INTEGER REFERENCES locais(id) ON DELETE SET NULL,
	area_m2 REAL,
	created_at TEXT NOT NULL DEFAULT (datetime('now')),
	updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_locais_parent ON locais(parent_id);
CREATE INDEX IF NOT EXISTS idx_locais_tipo ON locais(tipo);

CREATE TABLE IF NOT EXISTS normas (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	codigo TEXT UNIQUE NOT NULL,
	titulo TEXT NOT NULL,
	descricao TEXT,
	link_documento TEXT,
	created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS checklist_templates (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	nome TEXT NOT NULL,
	tipo_local TEXT NOT NULL,
	ativo INTEGER NOT NULL DEFAULT 1,
	created_at TEXT NOT NULL DEFAULT (datetime('now')),
	updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS checklist_template_items (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	template_id INTEGER NOT NULL REFERENCES checklist_templates(id) ON DELETE CASCADE,
	codigo TEXT NOT NULL,
	titulo TEXT NOT NULL,
	norma_id INTEGER REFERENCES normas(id) ON DELETE SET NULL,
	obrigatorio INTEGER NOT NULL DEFAULT 1,
	ordem INTEGER NOT NULL DEFAULT 0,
	UNIQUE(template_id, codigo)
);

CREATE INDEX IF NOT EXISTS idx_template_items_template ON checklist_template_items(template_id);

CREATE TABLE IF NOT EXISTS inspecoes (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	local_id INTEGER NOT NULL REFERENCES locais(id) ON DELETE RESTRICT,
	template_id INTEGER REFERENCES checklist_templates(id) ON DELETE SET NULL,
	servico_id TEXT, -- Referência ao xServicos (OS/PS)
	titulo TEXT NOT NULL,
	data_planejada TEXT,
	data_execucao TEXT,
	executante TEXT,
	status TEXT NOT NULL DEFAULT 'planejada',
	observacoes TEXT,
	degradacao_desc TEXT, -- NBR 5674
	perda_desempenho_estimada TEXT, -- NBR 5674
	created_at TEXT NOT NULL DEFAULT (datetime('now')),
	updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_inspecoes_local ON inspecoes(local_id);
CREATE INDEX IF NOT EXISTS idx_inspecoes_status ON inspecoes(status);

CREATE TABLE IF NOT EXISTS inspecao_itens (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	inspecao_id INTEGER NOT NULL REFERENCES inspecoes(id) ON DELETE CASCADE,
	codigo TEXT NOT NULL,
	titulo TEXT NOT NULL,
	norma_id INTEGER REFERENCES normas(id) ON DELETE SET NULL,
	condicao TEXT NOT NULL DEFAULT 'ok',
	observacao TEXT,
	prioridade_reparo TEXT,
	updated_at TEXT NOT NULL DEFAULT (datetime('now')),
	UNIQUE(inspecao_id, codigo)
);

CREATE INDEX IF NOT EXISTS idx_inspecao_itens_inspecao ON inspecao_itens(inspecao_id);

CREATE TABLE IF NOT EXISTS inspecao_anexos (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	inspecao_id INTEGER NOT NULL REFERENCES inspecoes(id) ON DELETE CASCADE,
	nome_arquivo TEXT NOT NULL,
	caminho TEXT NOT NULL,
	created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS laudos (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	local_id INTEGER NOT NULL REFERENCES locais(id) ON DELETE CASCADE,
	inspecao_id INTEGER REFERENCES inspecoes(id) ON DELETE SET NULL,
	titulo TEXT NOT NULL,
	tipo TEXT CHECK(tipo IN ('ART', 'RRT', 'Garantia', 'Tecnico', 'Outro')),
	arquivo_path TEXT,
	data_emissao TEXT,
	validade TEXT,
	created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_laudos_local ON laudos(local_id);

CREATE TABLE IF NOT EXISTS workflow_events (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	inspecao_id INTEGER NOT NULL REFERENCES inspecoes(id) ON DELETE CASCADE,
	de_status TEXT,
	para_status TEXT NOT NULL,
	usuario TEXT,
	comentario TEXT,
	created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_workflow_inspecao ON workflow_events(inspecao_id);
