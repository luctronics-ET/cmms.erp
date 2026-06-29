---
phase: 03-estoque-sobressalentes
plan: "01"
subsystem: backend
tags: [estoque, sobressalentes, manutencao, api, sqlite, pytest]
requirements: [IMP-03]
status: complete

dependency_graph:
  requires: []
  provides:
    - sobressalentes tables (schema_manutencao.sql)
    - /api/manutencao/sobressalentes* endpoints (backend/manutencao.py)
    - test_sobressalentes (tests/test_manutencao.py)
  affects:
    - backend/manutencao.py (extended)
    - data/schema_manutencao.sql (extended)
    - tests/test_manutencao.py (extended)

tech_stack:
  added: []
  patterns:
    - atomic aiosqlite transaction (single connect block + one commit) for ajuste
    - Pydantic field_validator for nome (non-empty) and tipo (entrada|saida|ajuste enum)
    - badge computed server-side (ZERADO|BAIXO|OK) per decision D

key_files:
  modified:
    - data/schema_manutencao.sql
    - backend/manutencao.py
    - tests/test_manutencao.py

decisions:
  - SEPARATE tables sobressalentes + sobressalentes_movimentos (not a scope column on estoque — IMP-03 SC3)
  - operador always from _require_auth session, never from payload (T-03-02)
  - saida/ajuste with negative result → HTTP 422, atomic rollback (T-03-06)
  - visualizador role → HTTP 403 on all write endpoints (T-03-04)

metrics:
  duration_seconds: 271
  tasks_completed: 3
  tasks_total: 3
  completed_date: "2026-06-29"
---

# Phase 03 Plan 01: Sobressalentes Backend Slice Summary

**One-liner:** Dedicated local spare-parts inventory (sobressalentes) with badge/valor endpoints, atomic ajuste, and estoque-isolation proof via pytest.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add sobressalentes + sobressalentes_movimentos tables | 789a531 | data/schema_manutencao.sql |
| 2 | Five sobressalentes endpoints in manutencao.py | 5e248f3 | backend/manutencao.py |
| 3 | test_sobressalentes — CRUD + atomic ajuste + estoque isolation | f7336a8 | tests/test_manutencao.py |

## What Was Built

### Schema (data/schema_manutencao.sql)
Appended a "Fase 03" block with two tables (additive, `CREATE TABLE IF NOT EXISTS`):

- **`sobressalentes`**: local spare-parts store distinct from central `estoque`. Columns: `id`, `codigo` (UNIQUE nullable), `nome` (NOT NULL), `categoria` (consumivel|sobressalente|ferramenta), `unidade`, `qtd_atual` REAL, `qtd_minima` REAL, `preco_unitario` REAL, `obs`, `ativo`, `criado_em`.
- **`sobressalentes_movimentos`**: movement log for each adjustment. Columns: `id`, `item_id` FK, `tipo` (entrada|saida|ajuste), `quantidade`, `motivo`, `obs`, `operador` (token snapshot), `created_at`.
- Composite index `idx_sob_mov_item(item_id, created_at DESC)` for newest-first history queries.
- Schema runs twice without error (idempotent). No changes to `estoque`/`estoque_movimentos`.

### Endpoints (backend/manutencao.py)
Five new routes under the existing `router` (prefix `/api/manutencao`):

| Method | Path | Description |
|--------|------|-------------|
| GET | `/sobressalentes` | List active peças; badge ZERADO/BAIXO/OK computed server-side; `valor_estimado_total` = Σ qtd×preco |
| POST | `/sobressalentes` (201) | Create peça; nome required (Pydantic); 403 for visualizador |
| PUT | `/sobressalentes/{id}` | Edit editable fields (NOT qtd_atual); 404 if missing; 403 for visualizador |
| POST | `/sobressalentes/{id}/ajuste` (201) | Atomic UPDATE qtd_atual + INSERT movimento; operador from token; 422 if result < 0 |
| GET | `/sobressalentes/{id}/movimentos` | History newest-first; limit 1–200 |

All endpoints call `_require_auth(authorization)`.

### Tests (tests/test_manutencao.py)
`test_sobressalentes` covers all specified behaviors on a clean DB:
- Create + DB row verification
- List with correct badges (ZERADO for qtd=0, OK for qtd>=minima)
- `valor_estimado_total` arithmetic verified
- PUT changes only editable fields; qtd_atual remains unchanged
- Ajuste atomicity: both qtd_atual update and movimento insert verified, operador set from token
- History endpoint: newest-first order verified
- Estoque isolation: central estoque row count and id set unchanged after full test (T-03-05)
- 422 for blank nome, nonexistent peça (404), saida driving negative; atomic rollback verified
- 401 for write without Bearer token

**Test results:** `5 passed, 11 warnings` (4 pre-existing + 1 new; 11 total with smoke tests).

## Deviations from Plan

None — plan executed exactly as written.

## Threat Surface Scan

No new network endpoints, auth paths, or schema changes at unexpected trust boundaries.
All five endpoints are under the existing `/api/manutencao` prefix already mounted by `main.py`.
All STRIDE mitigations documented in the plan's threat register were implemented:

| Threat ID | Implementation |
|-----------|----------------|
| T-03-01 | All SQL parameterized (no string interpolation of user data) |
| T-03-02 | operador = `user.get("mat") or user.get("nome")` — never from payload |
| T-03-03 | Single `aiosqlite.connect` block + single `commit()` in ajuste handler |
| T-03-04 | `role == 'visualizador'` → HTTPException(403) on POST/PUT/ajuste |
| T-03-05 | test_sobressalentes asserts estoque row count and ids unchanged |
| T-03-06 | `nova_qtd < 0` → HTTPException(422) before any DB write |

## Known Stubs

None.

## Self-Check

### Files created/modified
- [x] `/home/luc/DEV_ERP/cmasm.erp/data/schema_manutencao.sql` — FOUND
- [x] `/home/luc/DEV_ERP/cmasm.erp/backend/manutencao.py` — FOUND
- [x] `/home/luc/DEV_ERP/cmasm.erp/tests/test_manutencao.py` — FOUND

### Commits exist
- [x] 789a531 — Task 1 schema
- [x] 5e248f3 — Task 2 endpoints
- [x] f7336a8 — Task 3 tests

## Self-Check: PASSED
