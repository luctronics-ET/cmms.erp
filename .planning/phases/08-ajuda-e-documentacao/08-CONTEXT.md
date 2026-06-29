# Phase 8: Ajuda e Documentacao - Context

**Gathered:** 2026-06-29
**Status:** Ready for planning
**Mode:** Smart discuss (autonomous, recommendations auto-accepted)

<domain>
## Phase Boundary

Módulo novo de Ajuda & Documentação para o cmasm.erp (servidor local):
- **Ajuda contextual** (DOC-01): textos de ajuda intrínsecos por página/seção, exibidos em painel/drawer no ERP; editáveis pelo gestor.
- **Repositório de documentos/formulários versionado** (DOC-02): modelos (formulários, POPs) com controle de versão, armazenados localmente pelo cmasm.erp; CRUD + histórico de versões + download/visualização.
- **Guias/normas técnicas** (DOC-03): resumos e guias de normas no mesmo repositório, organizados por categoria.
Repositórios replicados/organizados por categoria (categorias do PMOC).

Fora: editor rich-text avançado; OCR/indexação full-text; sync offline de documentos.
</domain>

<decisions>
## Implementation Decisions

### Armazenamento (servidor local)
- **Documentos/arquivos**: filesystem em `data/documentos/<categoria>/` (já criado), 1 arquivo por versão (nome com id+versão), + metadados no SQLite. Sem nuvem.
- **Ajuda contextual**: conteúdo markdown direto no SQLite (textos curtos).
- Migração aditiva: tabelas novas em `schema_manutencao.sql` (ou novo `schema_docs.sql` adicionado a `CoreDB._SCHEMAS`). CREATE TABLE IF NOT EXISTS, nunca DROP.

### Modelo de dados
- `ajuda_topicos`: `id` PK, `categoria` (nullable/geral), `chave` (página/seção, UNIQUE), `titulo`, `conteudo_md` TEXT, `updated_at`, `updated_by`.
- `documentos`: `id` PK, `categoria` TEXT, `tipo` TEXT (modelo|formulario|guia|norma), `titulo`, `descricao`, `ativo` INTEGER DEFAULT 1, `criado_em`, `criado_por`.
- `documento_versoes`: `id` PK, `documento_id` FK, `versao` INTEGER, `arquivo_path` TEXT (relativo a data/documentos), `arquivo_nome` TEXT, `mime` TEXT, `tamanho` INTEGER, `autor`, `data` (created_at), `ativo` INTEGER DEFAULT 1. UNIQUE(documento_id, versao).

### Contrato de endpoints (novo router backend/docs.py OU em manutencao.py; preferir backend/docs.py registrado em main.py)
- Ajuda: `GET /api/docs/ajuda?chave=` (retorna tópico da página) + `GET /api/docs/ajuda` (lista) + `PUT /api/docs/ajuda/{chave}` (upsert conteúdo). `_require_auth`; edição exige não-visitante (RES-05 `_require_escrita`).
- Documentos: `GET /api/docs/documentos?categoria=&tipo=` (lista + última versão), `POST /api/docs/documentos` (cria doc), `GET /api/docs/documentos/{id}` (detalhe + lista de versões), `POST /api/docs/documentos/{id}/versoes` (upload nova versão: incrementa versao, grava arquivo + linha), `GET /api/docs/documentos/{id}/versoes/{versao}/download` (stream do arquivo). Soft-delete (ativo=0).
- Upload: multipart/form-data (FastAPI UploadFile) → grava em data/documentos/<categoria>/. Versão = max(versao)+1. Autor do token.
- `_require_escrita` nas escritas (criar doc, upload versão, editar ajuda); GET livre (auth).

### Frontend (UX)
- **Ajuda contextual**: botão "?" / ajuda na shell do ERP que abre um painel/drawer com o conteúdo markdown do tópico da página atual (renderizado de forma segura); modo edição p/ gestor (textarea → PUT).
- **Aba "Documentos"** (TAB_DEFS): navegação por categoria + tipo; lista de documentos com última versão; ações: + Novo documento, Upload de versão (form file), ver histórico de versões, baixar versão. Badges por tipo.
- Categorias = as do PMOC (refrigeracao, predial, paiois, transportes, grama, eletrica, calibracao) + "geral".
- Fetch + Bearer; DOM seguro via el()/textContent; markdown da ajuda renderizado com sanitização (sem innerHTML cru de conteúdo não confiável — usar um render mínimo seguro ou textContent + formatação básica).

### Testes
- `tests/test_docs.py`: ajuda GET/PUT (upsert persiste); criar documento; upload nova versão → versao incrementa (1→2), versão anterior preservada, autor+data gravados; download retorna o arquivo certo; listagem por categoria; soft-delete; migrações aditivas idempotentes (db.init() 2x). Banco limpo. Escrita por visualizador → 403.

### Claude's Discretion
- Router em `backend/docs.py` novo vs estender `manutencao.py` (preferir docs.py).
- Limites de tamanho/extensão de upload (definir um teto razoável; validar extensão).
- Render de markdown na ajuda: lib mínima vs formatação própria segura.
- Conferir `.docs_cmasm/referencias/cmasm13-govbr-v8_3.html` (tem "Manual"/"norma"/"Help") por UI de ajuda/docs a portar — opcional.
</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/manutencao.py` — padrão de router (_db, _require_auth, transação atômica). `_require_escrita` (Fase 6, main.py) p/ guard de escrita.
- `backend/db_core.py` `_SCHEMAS` — adicionar schema novo.
- `assets/erp-manutencao.js` — padrão TAB_DEFS + el() p/ a aba Documentos. Shell do ERP (cmasm_erp.html) p/ o botão de ajuda contextual.
- Categorias do PMOC já usadas no sistema.
- `data/documentos/` — dir de storage criado.
- FastAPI `UploadFile`/`FileResponse` p/ upload/download.

### Established Patterns
- Migração aditiva, CREATE TABLE IF NOT EXISTS. aiosqlite raw SQL. Erros com detail.
- Frontend vanilla, fetch+Bearer, DOM seguro.

### Integration Points
- Novo `backend/docs.py` (ou em manutencao.py) registrado em main.py via include_router.
- Schema novo em _SCHEMAS. Aba + botão de ajuda no frontend.
</code_context>

<specifics>
## Specific Ideas

- Servidor local → armazenamento local (filesystem + SQLite), sem nuvem.
- Controle de versão é requisito (histórico preservado, versão incrementa).
- Organização/replicação por categoria (categorias PMOC).
- Ajuda "intrínseca ao sistema e páginas" → contextual por página.
</specifics>

<deferred>
## Deferred Ideas

- Busca full-text / OCR nos documentos → futuro.
- Editor WYSIWYG da ajuda → futuro (textarea markdown agora).
- Versionamento de diff/preview → futuro.
</deferred>
