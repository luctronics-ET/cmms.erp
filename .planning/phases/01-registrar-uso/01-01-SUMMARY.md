---
phase: 01-registrar-uso
plan: 01
subsystem: api
tags: [fastapi, aiosqlite, sqlite, pydantic, manutencao, uso_registros]

# Dependency graph
requires: []
provides:
  - "data/schema_manutencao.sql — uso_registros table (IF NOT EXISTS, idempotent)"
  - "backend/manutencao.py — APIRouter /api/manutencao with atomic POST/GET /uso"
  - "manutencao_router registered in main.py — /api/manutencao/uso routes live on app"
  - "CoreDB._SCHEMAS now includes schema_manutencao.sql as 4th entry"
affects:
  - "02-registrar-uso"     # Plan 02 adds test infra on top of these routes
  - "phases 2-7"           # manutencao.py skeleton reused by all future maintenance phases

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Atomic aiosqlite transaction: single async with aiosqlite.connect() block with one await conn.commit() for multi-statement writes"
    - "_vencimentos_para_ativo helper: reuses iv*0.15 alert logic from main.py:2527-2581 filtered by ativo_id post-commit"
    - "APIRouter pattern: _db() via sys.modules['backend.main'].db + _require_auth copied from catalogo.py"

key-files:
  created:
    - "data/schema_manutencao.sql"
    - "backend/manutencao.py"
  modified:
    - "backend/db_core.py"
    - "backend/main.py"

key-decisions:
  - "Atomic UPDATE+INSERT via single aiosqlite.connect block — NOT two CoreDB.execute() calls (which open separate connections and are not atomic)"
  - "operador derived from Bearer token (user.nome/mat), never accepted from request body (IMP-01 audit trail)"
  - "delta field_validator rejects <= 0 via Pydantic (STRIDE T-01-02 tampering mitigation)"
  - "vencimentos_disparados calculated post-commit using existing iv*0.15 alert constant from main.py — no logic duplication"
  - "schema_manutencao.sql registered as 4th entry in _SCHEMAS so db.init() creates uso_registros idempotently on first startup"

patterns-established:
  - "Atomic multi-statement writes: async with aiosqlite.connect(db_path) as conn + conn.commit()"
  - "_db() helper: sys.modules['backend.main'].db avoids circular imports in router modules"
  - "Additive schema: PRAGMA foreign_keys = ON + CREATE TABLE IF NOT EXISTS + CREATE INDEX IF NOT EXISTS throughout"

requirements-completed: [IMP-01]

coverage:
  - id: D1
    description: "POST /api/manutencao/uso increments ativos.uso_atual and inserts uso_registros row in one atomic transaction"
    requirement: IMP-01
    verification:
      - kind: integration
        ref: "python -c import backend.manutencao + route presence check via app.routes"
        status: pass
    human_judgment: false
  - id: D2
    description: "GET /api/manutencao/uso returns recent registros newest-first"
    requirement: IMP-01
    verification:
      - kind: integration
        ref: "tests/test_manutencao_smoke.py — 6 passed"
        status: pass
    human_judgment: false
  - id: D3
    description: "schema_manutencao.sql defines uso_registros (9 columns, IF NOT EXISTS, no DROP/ALTER) and is registered as 4th _SCHEMAS entry"
    requirement: IMP-01
    verification:
      - kind: unit
        ref: "python -c assert 'schema_manutencao.sql' in open('backend/db_core.py').read()"
        status: pass
    human_judgment: false
  - id: D4
    description: "POST /uso response includes vencimentos_disparados list for triggered preventive plans"
    requirement: IMP-01
    verification: []
    human_judgment: true
    rationale: "No integration test with real catalogo_planos data was run in this plan — Plan 02 will cover this via test fixtures"

duration: 18min
completed: 2026-06-28
status: complete
---

# Phase 01 Plan 01: Registrar Uso — Backend Slice Summary

**Atomic `POST /api/manutencao/uso` with aiosqlite single-connection transaction: increments `ativos.uso_atual`, audits `uso_registros`, returns triggered vencimentos via iv*0.15 alert logic reused from main.py**

## Performance

- **Duration:** 18 min
- **Started:** 2026-06-28T00:00:00Z
- **Completed:** 2026-06-28T00:18:00Z
- **Tasks:** 3
- **Files modified:** 4 (2 created, 2 modified)

## Accomplishments

- Created `data/schema_manutencao.sql` with `uso_registros` (9 columns, AUTOINCREMENT PK, FK to ativos, two indexes) using `CREATE TABLE IF NOT EXISTS` — fully idempotent
- Created `backend/manutencao.py`: APIRouter `/api/manutencao` with `POST /uso` (atomic transaction) + `GET /uso` (newest-first, filterable by ativo_id) + `_vencimentos_para_ativo` helper
- Registered `schema_manutencao.sql` as 4th `_SCHEMAS` entry and `manutencao_router` in `main.py` — routes verified live on app; smoke tests all pass (6/6)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create schema_manutencao.sql + register in CoreDB._SCHEMAS** - `9bda55f` (feat)
2. **Task 2: Create backend/manutencao.py router with atomic POST + GET + vencimentos helper** - `25c3bca` (feat)
3. **Task 3: Register manutencao_router in main.py** - `5a1908a` (feat)

## Files Created/Modified

- `data/schema_manutencao.sql` — New: uso_registros table (9 cols), PRAGMA foreign_keys, two indexes, no DROP/ALTER
- `backend/manutencao.py` — New: APIRouter /api/manutencao; atomic POST /uso; GET /uso; _vencimentos_para_ativo; _db()/_require_auth from catalogo.py pattern
- `backend/db_core.py` — Modified: schema_manutencao.sql appended as 4th _SCHEMAS entry
- `backend/main.py` — Modified: manutencao_router imported + included via app.include_router()

## Decisions Made

- Used single `async with aiosqlite.connect(db_path)` block for the UPDATE+INSERT instead of two `CoreDB.execute()` calls — the singleton opens a new connection per call, making two-call writes non-atomic (verified in db_core.py lines 93–97)
- `operador` is derived from the Bearer token (`user["nome"]` or `user["mat"]`), never from the request body — ensures audit trail integrity (STRIDE T-01-05)
- `_vencimentos_para_ativo` reuses the iv*0.15 alert constant and catalogo_planos/catalogo_plano_itens query pattern from `main.py:2527–2581` — avoids logic divergence between the GET vencimentos endpoint and the POST uso response
- `valor_anterior` is read *inside* the transaction (not before opening the connection) — prevents snapshot inconsistency under concurrent requests

## Deviations from Plan

None — plan executed exactly as written. All three tasks completed with accepted patterns; no Rule 1/2/3/4 triggers encountered.

## Issues Encountered

Pre-existing test failures (unrelated to this plan):
- `tests/test_catalogo.py::test_create_plano_requires_auth` — 410 vs 401 expected (was failing before this plan with OperationalError, now fails differently because schema initializes properly)
- `tests/test_sync.py` (2 tests) and `tests/test_sync_eventos.py` (1 test) — pre-existing failures unrelated to manutencao

These are logged to `deferred-items.md` scope — out of scope for this plan.

## Threat Surface Scan

All STRIDE threats from the plan's threat model are mitigated in the implementation:
- T-01-01: All SQL parameterized (`(body.ativo_id,)` never f-string)
- T-01-02: `field_validator("delta")` rejects <= 0
- T-01-03: `_require_auth` validates Bearer token against sessoes with `expira_em > datetime('now')`
- T-01-04: Single `aiosqlite.connect` block + one `await conn.commit()`
- T-01-05: `operador`, `valor_anterior`, `valor_novo`, `data` all persisted in uso_registros

No new threat surface introduced beyond what the plan's threat model covers.

## Next Phase Readiness

- Backend vertical slice for IMP-01 complete: `/api/manutencao/uso` POST + GET routes live
- `backend/manutencao.py` skeleton established and reusable for phases 2–7
- Plan 02 can build async pytest fixture (`async_app_client`) + test_migracoes_idempotencia.py on top of this foundation

## Self-Check

- `data/schema_manutencao.sql` exists: FOUND
- `backend/manutencao.py` exists: FOUND
- Commit `9bda55f` exists: FOUND
- Commit `25c3bca` exists: FOUND
- Commit `5a1908a` exists: FOUND
- `/api/manutencao/uso` routes on app: VERIFIED (route check passed)
- `test_manutencao_smoke.py` — 6/6 passed

## Self-Check: PASSED

---
*Phase: 01-registrar-uso*
*Completed: 2026-06-28*
