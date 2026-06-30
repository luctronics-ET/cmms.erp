-- xCMASM · Schema Docs — Ajuda Contextual + Repositório de Documentos Versionado
-- Fase 08. Aditivo — CREATE TABLE IF NOT EXISTS obrigatório. Nunca DROP.
-- Ref: CONTEXT.md Phase 8, Rules.md (aditivo), REQUISITOS.md DOC-01/DOC-02/DOC-03.
--
-- NOTA: tabelas prefixadas com docs_ para evitar colisão com a tabela 'documentos'
-- já existente em schema_core.sql (tabela legada com schema diferente).

PRAGMA foreign_keys = ON;

-- ─── Ajuda Contextual (DOC-01) ───────────────────────────────────────────────
-- Um tópico por chave (ex: 'manutencao', 'estoque/lista', 'documentos').
-- UNIQUE(chave) — upsert via ON CONFLICT DO UPDATE (preserva id original).
CREATE TABLE IF NOT EXISTS ajuda_topicos (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  chave        TEXT    NOT NULL UNIQUE,          -- identificador de página/seção
  categoria    TEXT,                             -- categoria PMOC ou NULL (geral)
  titulo       TEXT    NOT NULL DEFAULT '',      -- título exibido no drawer
  conteudo_md  TEXT    NOT NULL DEFAULT '',      -- conteúdo markdown (renderizado client-side)
  updated_at   TEXT    NOT NULL DEFAULT (datetime('now')),
  updated_by   TEXT                              -- snapshot nome do usuário
);

CREATE INDEX IF NOT EXISTS idx_ajuda_chave ON ajuda_topicos(chave);

-- ─── Repositório de Documentos (DOC-02, DOC-03) ──────────────────────────────
-- Metadados do documento; arquivos físicos em data/documentos/<categoria>/.
-- categoria: whitelist geral|refrigeracao|predial|paiois|transportes|grama|eletrica|calibracao
-- tipo:      modelo | formulario | guia | norma
-- Prefixo docs_ para não colidir com a tabela 'documentos' do schema_core.sql.
CREATE TABLE IF NOT EXISTS docs_documentos (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  categoria    TEXT    NOT NULL,                 -- whitelist ALLOWED_CATS (backend/docs.py)
  tipo         TEXT    NOT NULL DEFAULT 'modelo', -- modelo | formulario | guia | norma
  titulo       TEXT    NOT NULL,
  descricao    TEXT,
  ativo        INTEGER NOT NULL DEFAULT 1,       -- soft-delete: 0 = inativo
  criado_em    TEXT    NOT NULL DEFAULT (datetime('now')),
  criado_por   TEXT                              -- snapshot nome do usuário
);

CREATE INDEX IF NOT EXISTS idx_ddoc_cat_tipo ON docs_documentos(categoria, tipo, ativo);

-- ─── Versões dos Documentos (DOC-02) ─────────────────────────────────────────
-- Um row por versão; versao = COALESCE(MAX(versao),0)+1 atômico na transação.
-- UNIQUE(documento_id, versao) — backstop de integridade contra race condition.
-- arquivo_path: relativo a data/ (ex: documentos/geral/42_v1.pdf).
-- arquivo_nome: nome original do cliente — usado somente como Content-Disposition.
CREATE TABLE IF NOT EXISTS docs_versoes (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  documento_id  INTEGER NOT NULL REFERENCES docs_documentos(id),
  versao        INTEGER NOT NULL,               -- 1, 2, 3, ... por documento
  arquivo_path  TEXT    NOT NULL,               -- relativo a data/ (server-controlled)
  arquivo_nome  TEXT    NOT NULL,               -- nome original (Content-Disposition)
  mime          TEXT,                           -- mime do cliente (metadado apenas)
  tamanho       INTEGER,                        -- bytes
  autor         TEXT,                           -- snapshot nome do usuário
  data          TEXT    NOT NULL DEFAULT (datetime('now')),
  ativo         INTEGER NOT NULL DEFAULT 1,     -- soft-delete de versão
  UNIQUE(documento_id, versao)
);

CREATE INDEX IF NOT EXISTS idx_dv_doc ON docs_versoes(documento_id, versao DESC);

-- ─── Pastas / Árvore de Documentos ───────────────────────────────────────────
-- Estrutura hierárquica de pastas. caminho (materialized path) = UNIQUE para
-- idempotência do seed e exibição; parent_id para navegação da árvore.
-- pasta_id em docs_documentos é adicionado via migração aditiva (db_core.py).
CREATE TABLE IF NOT EXISTS docs_pastas (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  nome        TEXT    NOT NULL,
  parent_id   INTEGER REFERENCES docs_pastas(id),
  caminho     TEXT    NOT NULL UNIQUE,            -- ex: "Organização/Ordens Internas"
  ativo       INTEGER NOT NULL DEFAULT 1,
  criado_em   TEXT    NOT NULL DEFAULT (datetime('now')),
  criado_por  TEXT
);

CREATE INDEX IF NOT EXISTS idx_dpasta_parent ON docs_pastas(parent_id, ativo);

-- Pastas raiz padrão (idempotente via UNIQUE(caminho)).
INSERT OR IGNORE INTO docs_pastas (nome, parent_id, caminho) VALUES
  ('Organização',     NULL, 'Organização'),
  ('Ordens Internas', NULL, 'Ordens Internas'),
  ('Normas Técnicas', NULL, 'Normas Técnicas');
