---
phase: 04-equipe-tecnica
plan: "01"
subsystem: backend/manutencao
tags: [equipe-tecnica, roster, capacity, schema, crud, soft-delete, IMP-04]
dependency_graph:
  requires: [schema_manutencao.sql, backend/manutencao.py]
  provides: [equipe_membros table, equipe_config singleton, /api/manutencao/equipe/* endpoints, _capacidade() helper]
  affects: [Phase 5 cronograma (consumes equipe_config capacity)]
tech_stack:
  added: []
  patterns: [Pydantic validators, aiosqlite atomic writes, INSERT OR REPLACE singleton upsert, soft-delete ativo=0, JSON TEXT columns for arrays]
key_files:
  created: []
  modified:
    - data/schema_manutencao.sql
    - backend/manutencao.py
    - tests/test_manutencao.py
decisions:
  - Capacity is config-only (does NOT multiply by member count) — follows legacy cmasm13-govbr-v8_3.html formula exactly
  - equipe_config is a singleton (id=1) upserted via INSERT OR REPLACE, never INSERT multiple rows
  - Soft-delete only — no DELETE route; ativo=0 via PUT /{id} (T-04-05)
  - GET /equipe/config returns schema defaults without inserting when table is empty (idempotent read)
metrics:
  duration: "~10 minutes"
  completed: "2026-06-28"
  tasks_completed: 3
  tasks_total: 3
  files_changed: 3
status: complete
---

# Phase 04 Plan 01: Equipe Técnica Backend Slice Summary

**One-liner:** Roster CRUD + singleton config + derived capacity via `_capacidade()` helper using exact legacy formula (config-only, not member count).

## What Was Built

Backend vertical slice for IMP-04 (Equipe Técnica):

1. **Schema** (`data/schema_manutencao.sql`): Two new tables appended as a "Fase 04" additive block.
   - `equipe_membros`: roster with `posto_grad`, `especialidade`, `tem_login`, `usuario_mat` (optional login link), soft-delete `ativo` flag, `created_at`. Index on `ativo` for roster filter.
   - `equipe_config`: singleton (id=1), `num_equipes` INTEGER, `dias_semana` TEXT (JSON), `turnos` TEXT (JSON), `updated_at`. Capacity NOT stored.
   - Both use `CREATE TABLE IF NOT EXISTS` — idempotent (verified: runs twice without error).

2. **Endpoints** (`backend/manutencao.py`): Six new routes appended as "Fase 04" section.
   - `GET /api/manutencao/equipe/membros` — list roster; `ativo=1` default; `?incluir_inativos=1` returns all. Order by nome.
   - `POST /api/manutencao/equipe/membros` — create member, returns `{id}`, status 201.
   - `PUT /api/manutencao/equipe/membros/{id}` — partial update including `ativo=0` for soft-delete. 404 if not found. Never DELETE.
   - `GET /api/manutencao/equipe/config` — returns singleton id=1 + derived capacity. If table empty, returns schema defaults (no insert).
   - `PUT /api/manutencao/equipe/config` — UPSERT id=1 via `INSERT OR REPLACE`, serializes `dias_semana`/`turnos` as JSON, returns saved config + recomputed capacity.
   - All endpoints: `_require_auth`. Writes: reject `role=visualizador` (403).

3. **`_capacidade(config)` helper** (pure function, no DB):
   ```
   h_dia_equipe = Σ turnos[i].horas
   h_dia_total  = h_dia_equipe × num_equipes
   h_semana     = h_dia_total × len(dias_semana)
   h_mes        = h_semana × 4.345
   h_ano        = h_semana × 52
   ```
   Handles both list inputs (from ConfigIn) and JSON string inputs (from DB row). Returns exact integer results when inputs are integers.

4. **Test** (`tests/test_manutencao.py::test_equipe_tecnica`): Full coverage in 7 sub-scenarios on a clean fixture DB.

## Commits

| Hash | Type | Description |
|------|------|-------------|
| 2e2b983 | feat | Add equipe_membros + equipe_config tables to schema_manutencao.sql |
| bea7308 | feat | Add equipe membros CRUD + config GET/PUT + _capacidade() helper |
| cbc4646 | test | Add test_equipe_tecnica covering CRUD, soft-delete, config + capacity |

## Test Results

```
python -c "import backend.manutencao"  → import OK
python -m pytest tests/test_manutencao.py -q
6 passed, 13 warnings  (was 5 before; +1 new test, no regressions)
```

Capacity assertions verified exact:
- Default (1 equipe, 5 dias, 2×2h): `h_dia_equipe=4, h_dia_total=4, h_semana=20, h_ano=1040`
- Saved (2 equipes, 5 dias, 2×4h): `h_dia_equipe=8, h_dia_total=16, h_semana=80, h_ano=4160`

## Deviations from Plan

None — plan executed exactly as written.

## Threat Surface Scan

No new network surface beyond what the plan's threat model covers. All six routes are within the existing `/api/manutencao` router registered in `main.py`. No new auth paths, file access, or schema trust boundaries introduced.

## Self-Check: PASSED

- `data/schema_manutencao.sql`: table equipe_membros present, table equipe_config present, idempotent ✓
- `backend/manutencao.py`: `_capacidade` function present, routes `equipe/membros` and `equipe/config` present, `import backend.manutencao` clean ✓
- `tests/test_manutencao.py::test_equipe_tecnica`: 1 passed ✓
- Commits: 2e2b983, bea7308, cbc4646 all present ✓
- No NEW failures vs baseline (14 pre-existing failures unchanged) ✓
