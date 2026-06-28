---
phase: 01-registrar-uso
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - data/schema_manutencao.sql
  - backend/db_core.py
  - backend/manutencao.py
  - backend/main.py
autonomous: true
requirements: [IMP-01]
must_haves:
  truths:
    - "POST /api/manutencao/uso increments ativos.uso_atual and inserts a uso_registros row in one atomic transaction (rollback if either statement fails)"
    - "The POST response includes the new uso_atual and a vencimentos_disparados list for plans of that ativo where the alert window is reached"
    - "GET /api/manutencao/uso?ativo_id= returns recent registros ordered newest-first"
    - "db.init() loads schema_manutencao.sql and creates uso_registros idempotently (CREATE TABLE IF NOT EXISTS)"
  artifacts:
    - "data/schema_manutencao.sql (new) — uso_registros table"
    - "backend/manutencao.py (new) — APIRouter prefix=/api/manutencao"
  key_links:
    - "schema_manutencao.sql registered as 4th entry in CoreDB._SCHEMAS"
    - "manutencao_router included in main.py via include_router"
    - "atomic UPDATE+INSERT use a single aiosqlite.connect() block, NOT CoreDB.execute (which opens a connection per call)"
---

<objective>
Deliver the backend vertical slice of "Registrar Uso": the uso_registros schema, the new manutencao APIRouter mounted in main.py, the atomic POST /api/manutencao/uso endpoint (increment ativos.uso_atual + audit row in one transaction), the GET listing endpoint, and the triggered-vencimento calculation in the POST response. Implements IMP-01.

Purpose: This is the foundation the frontend tab and the test infra (Plan 02) build on. It establishes the manutencao skeleton reused by phases 2–7.
Output: data/schema_manutencao.sql, backend/manutencao.py, edits to backend/db_core.py and backend/main.py.
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/01-registrar-uso/01-CONTEXT.md
@.planning/phases/01-registrar-uso/01-RESEARCH.md
@.planning/phases/01-registrar-uso/01-PATTERNS.md

# Analogs to mirror exactly:
@backend/catalogo.py
@backend/db_core.py
@data/schema_catalogo.sql
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create schema_manutencao.sql and register it in CoreDB._SCHEMAS</name>
  <files>data/schema_manutencao.sql, backend/db_core.py</files>
  <read_first>
    - data/schema_catalogo.sql (lines 1–32) — header + CREATE TABLE IF NOT EXISTS + index pattern to mirror
    - backend/db_core.py (lines 7–24) — current _SCHEMAS list and how init() runs executescript over it
  </read_first>
  <action>
Create data/schema_manutencao.sql with the uso_registros table per the locked CONTEXT decision (D-modelo-de-dados). Start with `PRAGMA foreign_keys = ON;`. Use `CREATE TABLE IF NOT EXISTS uso_registros` with columns: id (INTEGER PRIMARY KEY AUTOINCREMENT), ativo_id (TEXT NOT NULL REFERENCES ativos(id)), delta (REAL NOT NULL), valor_anterior (REAL NOT NULL), valor_novo (REAL NOT NULL), data (TEXT NOT NULL), operador (TEXT), observacao (TEXT), created_at (TEXT DEFAULT (datetime('now'))). Add `CREATE INDEX IF NOT EXISTS idx_uso_registros_ativo ON uso_registros(ativo_id, created_at DESC);`. Mirror the file header comment style of schema_catalogo.sql. Additive only — no ALTER, no DROP, every statement guarded by IF NOT EXISTS so db.init() is idempotent.

Then edit backend/db_core.py: append `os.path.join(_DATA_DIR, "schema_manutencao.sql")` as the fourth entry of the _SCHEMAS list. Make no other change to db_core.py — no new migration logic is needed because db.init() already runs executescript over every _SCHEMAS entry and IF NOT EXISTS makes it idempotent.
  </action>
  <verify>
    <automated>cd /home/luc/DEV_ERP/cmasm.erp && python -c "import ast,re; s=open('backend/db_core.py').read(); assert 'schema_manutencao.sql' in s, 'not registered in _SCHEMAS'; sql=open('data/schema_manutencao.sql').read(); assert 'CREATE TABLE IF NOT EXISTS uso_registros' in sql; assert 'DROP' not in sql.upper(); print('OK')"</automated>
  </verify>
  <acceptance_criteria>
    - data/schema_manutencao.sql exists, defines uso_registros with all 9 columns (id, ativo_id, delta, valor_anterior, valor_novo, data, operador, observacao, created_at), uses CREATE TABLE IF NOT EXISTS, contains no DROP/ALTER.
    - backend/db_core.py _SCHEMAS list has schema_manutencao.sql as the 4th entry.
  </acceptance_criteria>
  <done>schema_manutencao.sql created with uso_registros (IF NOT EXISTS) and registered as 4th entry in CoreDB._SCHEMAS; no DROP/ALTER present.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Create backend/manutencao.py router with atomic POST + GET + vencimentos helper</name>
  <files>backend/manutencao.py</files>
  <read_first>
    - backend/catalogo.py (lines 1–48) — _db(), _require_auth, APIRouter prefix pattern to copy verbatim
    - backend/catalogo.py (lines 53–135, 191–230) — Pydantic model, GET list, error/404 patterns
    - backend/main.py (lines 2527–2581) — manutencao_vencimentos logic to reuse, filtered by ativo (por_uso frequency, alert window iv*0.15)
    - backend/db_core.py (lines 79–97) — proof that CoreDB.execute opens a connection per call (why a raw aiosqlite.connect block is required for atomicity)
  </read_first>
  <behavior>
    - POST /api/manutencao/uso with valid token + body {ativo_id, delta>0}: reads current uso_atual inside the transaction, sets valor_anterior=current, valor_novo=current+delta, runs UPDATE ativos + INSERT uso_registros in one aiosqlite.connect block, commits once; returns {uso_atual, valor_anterior, delta, vencimentos_disparados}.
    - POST with unknown/inactive ativo_id: 404 with detail "Ativo não encontrado", no row written.
    - POST with delta <= 0: 422 (Pydantic field_validator rejects).
    - POST with missing/invalid Bearer token: 401.
    - GET /api/manutencao/uso?ativo_id=X: returns rows for that ativo, newest first, limited.
    - GET /api/manutencao/uso (no ativo_id): returns recent rows across all ativos, newest first, limited.
  </behavior>
  <action>
Create backend/manutencao.py mirroring backend/catalogo.py exactly. Copy `_db()` (returns `sys.modules["backend.main"].db` — never import db at module top) and `_require_auth(authorization)` verbatim from catalogo.py lines 24–48. Declare `router = APIRouter(prefix="/api/manutencao", tags=["manutencao"])`.

Define Pydantic `UsoIn(BaseModel)` with ativo_id: str, delta: float, data: Optional[str]=None, observacao: Optional[str]=None. Add a field_validator on delta that rejects values <= 0 (per the Tampering threat T-01: reject negative/zero deltas). Operador is derived from the token (use row["nome"] from _require_auth) — never accepted from the body.

Implement POST /uso (status_code=201): call _require_auth; resolve db_path via `_db().db_path`. Open `async with aiosqlite.connect(db_path) as conn:` with `conn.row_factory = aiosqlite.Row`. Inside the block, in order: (1) SELECT uso_atual FROM ativos WHERE id=? AND ativo=1 (parameterized, never f-string interpolated) — raise HTTPException(404, "Ativo não encontrado") if no row; (2) compute valor_anterior = current or 0.0, valor_novo = round(valor_anterior + delta, 2); (3) UPDATE ativos SET uso_atual=? WHERE id=?; (4) INSERT INTO uso_registros (ativo_id, delta, valor_anterior, valor_novo, data, operador, observacao) VALUES (...) with data defaulting to date.today().isoformat() when body.data is falsy; (5) await conn.commit(). Both writes live in the same connection block so an exception before commit rolls back both (IMP-01 atomicity). Do NOT use _db().execute() twice — that opens two separate connections and is not atomic.

Implement a helper `_vencimentos_para_ativo(ativo_id, uso_atual_novo)` that reuses the vencimento logic from main.py:2527–2581 filtered to one ativo: load the ativo's tipo, find catalogo_planos applicable to that tipo (via aplicavel_tipos JSON + tipo_codigo), iterate catalogo_plano_itens of classe 'prev', parse the por_uso frequency, compute prox = (floor(uso/iv)+1)*iv and falta = prox-uso, and include the item when falta <= iv*0.15 (same alert constant as main.py). Return the list of triggered items (servico, plano, intervalo, falta, etc.). Call this after commit and return it as vencimentos_disparados in the POST response.

Implement GET /uso (query params ativo_id: Optional[str]=None, limit: int=20): use _db().fetch_all with a parameterized WHERE on ativo_id when provided, JOIN ativos for ativo_nome/unidade_uso, ORDER BY created_at DESC LIMIT ?. All queries parameterized.

All errors use raise HTTPException(status, "detail string") — never return error dicts.
  </action>
  <verify>
    <automated>cd /home/luc/DEV_ERP/cmasm.erp && python -c "import ast; t=ast.parse(open('backend/manutencao.py').read()); fns={n.name for n in ast.walk(t) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}; assert {'_db','_require_auth','_vencimentos_para_ativo'} <= fns, fns; src=open('backend/manutencao.py').read(); assert 'aiosqlite.connect' in src and 'conn.commit' in src, 'atomic block missing'; assert 'APIRouter(prefix=\"/api/manutencao\"' in src.replace(\"'\",'\"'); print('OK')"</automated>
  </verify>
  <acceptance_criteria>
    - backend/manutencao.py imports cleanly (no top-level `from backend.main import db`), exposes `router` with prefix /api/manutencao.
    - POST /uso performs UPDATE ativos + INSERT uso_registros inside ONE `async with aiosqlite.connect(...)` block with a single commit; uses _db().db_path for the path.
    - delta field_validator rejects <= 0; operador derived from token, not body.
    - _vencimentos_para_ativo reuses the por_uso + iv*0.15 alert logic; POST response includes vencimentos_disparados.
    - GET /uso returns parameterized, newest-first, limited rows.
  </acceptance_criteria>
  <done>backend/manutencao.py exists with atomic POST /uso (single aiosqlite.connect transaction), GET /uso, _vencimentos_para_ativo helper, copied _db/_require_auth, and delta>0 validation.</done>
</task>

<task type="auto">
  <name>Task 3: Register manutencao_router in main.py</name>
  <files>backend/main.py</files>
  <read_first>
    - backend/main.py (lines 18–24) — router import block (catalogo/grama/sync)
    - backend/main.py (lines 323–327) — include_router calls
  </read_first>
  <action>
Edit backend/main.py: add `from .manutencao import router as manutencao_router` alongside the other router imports (after the sync import, line ~22). Add `app.include_router(manutencao_router)` after the existing `app.include_router(catalogo_router)` line (~327). No startup migration is needed — db.init() already loads schema_manutencao.sql via _SCHEMAS (Plan 01 Task 1). Do not touch any existing include_router call or the startup hook beyond this addition. Preserve all existing API contracts.
  </action>
  <verify>
    <automated>cd /home/luc/DEV_ERP/cmasm.erp && python -c "import os; os.environ.setdefault('DB_PATH','./data/_plan01_check.db'); import importlib; m=importlib.import_module('backend.main'); paths={r.path for r in m.app.routes}; assert any(p.startswith('/api/manutencao/uso') for p in paths), sorted(p for p in paths if 'manutencao' in p); print('OK routes:', sorted(p for p in paths if 'manutencao' in p))" && rm -f ./data/_plan01_check.db</automated>
  </verify>
  <acceptance_criteria>
    - backend/main.py imports manutencao_router and calls app.include_router(manutencao_router) once.
    - The app exposes /api/manutencao/uso routes; no existing include_router call removed or reordered destructively.
  </acceptance_criteria>
  <done>manutencao_router imported and included in main.py; /api/manutencao/uso routes present on app; existing routers untouched.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| browser → /api/manutencao/* | Untrusted JSON payload + Bearer token cross here |
| backend → core.db | Production data (ativos.uso_atual with real values) is mutated here |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-01-01 | Tampering | POST /api/manutencao/uso (ativo_id) | high | mitigate | All SQL parameterized — `(body.ativo_id,)` never f-string interpolated |
| T-01-02 | Tampering | POST /api/manutencao/uso (delta) | medium | mitigate | Pydantic field_validator rejects delta <= 0 (no malicious negative corrections) |
| T-01-03 | Elevation | _require_auth token | high | mitigate | Bearer token validated against sessoes with `expira_em > datetime('now')` (copied from catalogo.py) |
| T-01-04 | Tampering | atomic UPDATE+INSERT | high | mitigate | Single aiosqlite.connect block + one commit — partial write impossible; rollback on exception (IMP-01) |
| T-01-05 | Repudiation | uso_registros audit row | medium | mitigate | operador (from token), data, valor_anterior/valor_novo snapshot persisted for every increment |
| T-01-06 | Info disclosure | GET /uso of other ativo | low | accept | Internal closed network; no per-ativo ownership control this phase (per RESEARCH Security Domain) |
| T-01-SC | Tampering | pip installs | high | mitigate | No runtime packages added in this plan; test packages handled in Plan 02 with audit (both [ASSUMED] OK) |
</threat_model>

<verification>
- `python -c "import backend.manutencao"` imports without error (no circular import).
- App boots and exposes POST + GET /api/manutencao/uso.
- schema_manutencao.sql contains no DROP/ALTER; all CREATE ... IF NOT EXISTS.
- Full existing pytest suite still passes (no regression) — re-checked end-to-end in Plan 02 once test infra lands.
</verification>

<success_criteria>
- IMP-01 backend satisfied: atomic increment of ativos.uso_atual + uso_registros audit row in one transaction, with triggered-vencimento list in the response.
- manutencao skeleton established (router + schema in _SCHEMAS) for reuse by phases 2–7.
</success_criteria>

<output>
Create `.planning/phases/01-registrar-uso/01-01-SUMMARY.md` when done.
</output>
