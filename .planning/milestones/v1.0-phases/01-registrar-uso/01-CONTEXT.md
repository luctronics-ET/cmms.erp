# Phase 1: Registrar Uso - Context

**Gathered:** 2026-06-28
**Status:** Ready for planning
**Mode:** Smart discuss (autonomous, recommendations auto-accepted)

<domain>
## Phase Boundary

Entrega o primeiro slice vertical (frontend + backend + migração aditiva) **e** o esqueleto de manutenção reutilizado pelas fases 2–7:
- Aba "Registrar Uso" no ERP (visual portado de `.docs_cmasm/referencias/CMASM_Gestao_v2.html`): seleciona ativo, informa delta de uso (horas/km) + data, registra.
- Incremento atômico de `ativos.uso_atual` + histórico auditável em `uso_registros`.
- Alerta de vencimento preventivo na mesma interação quando `uso_atual >= proximo_uso`.
- Skeleton: `backend/manutencao.py` (APIRouter incluído em `main.py`) + `data/schema_manutencao.sql` (em `CoreDB._SCHEMAS`).
- Infra de teste: fixture async (pytest-asyncio + httpx + asgi-lifespan) + teste de idempotência de migração.

Fora desta fase: plano-no-ativo com checkboxes (Fase 2), demais imports.
</domain>

<decisions>
## Implementation Decisions

### Modelo de dados (uso_registros)
- Nova tabela `uso_registros` em `schema_manutencao.sql`: `id` (PK), `ativo_id` (FK ativos), `delta` (REAL), `valor_anterior` (REAL), `valor_novo` (REAL), `data` (DATE/TEXT), `operador` (mat/nome do usuário logado), `observacao` (TEXT opcional), `created_at` (TEXT default timestamp).
- Snapshot do horímetro = grava `valor_anterior` e `valor_novo` para trilha auditável (não só o delta).
- Não dropar nem alterar `ativos.uso_atual` (coluna já existe) — só incrementar.

### Contrato do endpoint
- `POST /api/manutencao/uso` (no router `manutencao.py`), payload `{ativo_id, delta, data?, observacao?}`. Operador derivado do token (usuário logado).
- Incremento atômico: `UPDATE ativos SET uso_atual = uso_atual + ? WHERE id=?` + `INSERT INTO uso_registros (...)` na MESMA transação (rollback se qualquer passo falhar).
- Resposta inclui `uso_atual` novo e lista de vencimentos disparados (planos do ativo onde `uso_atual >= proximo_uso`) para o alerta no front.
- `GET /api/manutencao/uso?ativo_id=` retorna registros recentes (ordenados desc, limit razoável).
- Reaproveitar lógica de vencimento existente onde possível; PMOC `_h_uso_atual_inc` (sync) deve, quando viável, gravar também em `uso_registros` p/ trilha unificada (se barato; senão registrar como deferred).

### Frontend (UX)
- Nova aba/seção "Registrar Uso" no `cmasm_erp.html`, visual portado do legado (layout aprovado), tema dark + tokens existentes.
- Substituir qualquer persistência localStorage do legado por chamada à API via SDK (`window.xcmasm`/fetch padrão do projeto).
- Form: seletor de ativo, campo delta numérico, data (default hoje), observação opcional, botão "Registrar".
- Após registrar: feedback de sucesso, atualizar "Registros Recentes", e se houver vencimento disparado exibir alerta inline.

### Schema, migração e testes
- `schema_manutencao.sql` com todas as tabelas em `CREATE TABLE IF NOT EXISTS`; adicionado a `CoreDB._SCHEMAS`.
- Migração aditiva apenas; `PRAGMA table_info` antes de qualquer `ALTER`; nunca `DROP`.
- `tests/test_migracoes_idempotencia.py`: roda `db.init()` duas vezes no mesmo banco → sem erro "duplicate column name".
- Estabelecer fixture async (`async_app_client` com `asgi-lifespan.LifespanManager` p/ rodar `db.init()` no startup) em `conftest.py`, SEM tocar no fixture sync `TestClient` existente. Adicionar `pytest-asyncio`, `asgi-lifespan` ao `requirements.txt` (httpx já está pinado).
- Não regredir a suíte pytest existente (`tests/` — 7 arquivos).

### Claude's Discretion
- Nome exato do endpoint/sub-rotas e shape fino do JSON, desde que respeite contratos existentes.
- Estrutura interna do `manutencao.py` (helpers, models Pydantic).
- Detalhes de markup/CSS do port, mantendo o visual aprovado.
</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/db_core.py` — `CoreDB` singleton, `_SCHEMAS` list, migração via `PRAGMA table_info` (aditiva).
- `backend/main.py` — registro de routers via `include_router` (ver `catalogo`, `grama`, `sync`); auth bearer token (usuário logado p/ operador).
- `ativos.uso_atual` — coluna já existente, incrementada hoje por Transportes/Grama/manual.
- Lógica de vencimento existente: `GET /api/manutencao/vencimentos` + `catalogo_planos`/`aplicavel_tipos` (uso_atual → próximo/falta).
- Padrões de tabela no ERP: `assets/tbl-enhance.js`, `pmoc-engine.js` (export/sort/filter).
- Legado fonte: `.docs_cmasm/referencias/CMASM_Gestao_v2.html` (aba "Registrar Uso", visual aprovado).
- Testes: `tests/conftest.py` (TestClient sync), `tests/test_manutencao_smoke.py`, etc.

### Established Patterns
- Backend: FastAPI + Pydantic + async/await + aiosqlite, raw SQL, erro com `detail`.
- Frontend: vanilla JS, sem build, API objects em `window`, inline `<script>`.
- Migrações: aditivas, `PRAGMA table_info`, nunca `DROP`.

### Integration Points
- `main.py` `include_router(manutencao.router)`.
- `CoreDB._SCHEMAS` += `schema_manutencao.sql`.
- Nova aba na navegação do `cmasm_erp.html` (Manutenção ou topo).
- `conftest.py` ganha fixture async.
</code_context>

<specifics>
## Specific Ideas

- Visual da aba deve seguir o legado `CMASM_Gestao_v2.html` (aprovado pelo usuário). Não reinventar layout.
- Trilha auditável é requisito (operador + data + snapshot), não só incrementar número.
</specifics>

<deferred>
## Deferred Ideas

- Unificar trilha do PMOC `_h_uso_atual_inc` em `uso_registros` se não for barato nesta fase.
- Paginação/cache de vencimentos → v2 (PERF-*).
</deferred>
