---
phase: 02-plano-no-ativo
plan: 01
subsystem: backend
tags: [manutencao, plano-ativo, sqlite, fastapi, atomic-txn, anti-double-count]
status: complete

dependency_graph:
  requires: [01-01-SUMMARY]
  provides: [ativo_plano_estado, manut_registros, GET /plano-ativo, POST /registro]
  affects: [backend/manutencao.py, data/schema_manutencao.sql, tests/test_manutencao.py]

tech_stack:
  added: []
  patterns:
    - aiosqlite single-connect atomic transaction (ON CONFLICT upsert)
    - por_uso guard before float() coercion (avoids KeyError/TypeError on por_tempo items)
    - anti-double-count: uso_no_momento read from DB inside txn, never from payload

key_files:
  created:
    - tests/test_manutencao.py
  modified:
    - data/schema_manutencao.sql
    - backend/manutencao.py

decisions:
  - proximo_uso = uso_no_momento + iv (always resets to current usage + interval, never accumulates)
  - por_tempo items appear in GET /plano-ativo with status=POR_TEMPO, por_tempo=true, null numerics
  - itens_validos filtered to por_uso items only for ativo_plano_estado upsert; por_tempo items still recorded in manut_registros audit JSON
  - operador derived from Bearer token, never from payload (T-02-03)

metrics:
  duration: ~20 minutes
  completed: 2026-06-28
  tasks_completed: 3
  tasks_total: 3
  files_changed: 3

requirements: [IMP-02]
---

# Phase 02 Plan 01: Plano no Ativo — Backend Vertical Slice Summary

**One-liner:** Atomic SQLite backend for maintenance plan execution — GET /plano-ativo computes VENCIDA/URGENTE/PROXIMA/EM_DIA per item, POST /registro upserts ativo_plano_estado with anti-double-count proximo_uso inside a single aiosqlite transaction.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add ativo_plano_estado + manut_registros tables | fd39d8d | data/schema_manutencao.sql |
| 2 | Add GET /plano-ativo and POST /registro endpoints | 3730794 | backend/manutencao.py |
| 3 | Add tests/test_manutencao.py (4 tests) | 7725c75 | tests/test_manutencao.py |

## Artifacts Produced

### data/schema_manutencao.sql
- `ativo_plano_estado(ativo_id, catalogo_plano_item_id, ultimo_uso REAL, proximo_uso REAL, updated_at)` — composite PK; idx_ape_ativo index
- `manut_registros(id, ativo_id, responsavel, operador, data, uso_no_momento REAL, itens_json, observacao, created_at)` — idx_mr_ativo index
- Both tables: CREATE TABLE IF NOT EXISTS (additive; idempotent)

### backend/manutencao.py
- `RegistroIn` Pydantic model: `responsavel` (required, non-blank validator), `itens` (non-empty list[int]), `observacao` (optional)
- `GET /api/manutencao/plano-ativo?ativo_id=` — resolves plans by ativo.tipo, merges ativo_plano_estado, computes status with thresholds: VENCIDA (falta≤0), URGENTE (≤15% interval), PROXIMA (≤30%), EM_DIA; por_tempo guard before float() coercion
- `POST /api/manutencao/registro` — single aiosqlite.connect block: reads uso_atual inside txn, builds itens_validos (por_uso only), inserts manut_registros, upserts ativo_plano_estado via ON CONFLICT DO UPDATE, single commit

### tests/test_manutencao.py (4/4 passed)
- `test_plano_no_ativo`: GET returns status/falta/pct; POST at uso=1000 → proximo_uso=1250; explicit UPDATE to uso=1100; POST again → proximo_uso=1350 (anti-double-count proven, not 1500)
- `test_registro_exige_responsavel`: 422 on blank/whitespace/missing responsavel; zero audit rows
- `test_registro_atomico`: 422 on nonexistent item_id; zero rows in BOTH manut_registros AND ativo_plano_estado (proves cross-table atomic rollback)
- `test_plano_ativo_requires_auth`: 401 without Bearer token

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as written.

Minor adjustment: the RESEARCH.md example code for POST raised HTTPException on malformed JSON frequencies (`raise HTTPException(422, ...)`). The plan's task description said "skip" for malformed/por_tempo items (itens_validos filtering). The implementation follows the plan task description (skip non-por_uso items silently in itens_validos), which is the correct behavior: por_tempo items are a legitimate configuration, not an error. This is consistent with the GET handler behavior and the constraint doc.

## Test Results

```
python -c "import backend.manutencao"  → OK (module imports without error)
pytest tests/test_manutencao_smoke.py tests/test_manutencao.py -q → 10 passed, 9 warnings
```

No new failures beyond the 14-failure pre-existing baseline (test_catalogo auth, test_sync, test_sync_eventos).

## Threat Model Coverage

All T-02-XX mitigations implemented:
- T-02-01: All SQL uses tuple params, no f-string interpolation
- T-02-02: uso_no_momento read from ativos.uso_atual inside txn, never from payload
- T-02-03: operador derived from _require_auth token, never from payload
- T-02-04: manut_registros records responsavel, operador, data, uso_no_momento, itens_json per event
- T-02-05: Single aiosqlite.connect + one commit; HTTPException before commit forces rollback
- T-02-06: GET /plano-ativo calls _require_auth (401 without valid token)

## Known Stubs

None — all data flows are wired to the database.

## Threat Flags

None — no new network endpoints, auth paths, or schema changes beyond the plan's declared scope.

## Self-Check: PASSED

- data/schema_manutencao.sql: ativo_plano_estado and manut_registros tables present, REAL columns verified
- backend/manutencao.py: GET /plano-ativo and POST /registro registered on router, ON CONFLICT upsert present
- tests/test_manutencao.py: 4/4 tests pass, no payload uso_atual token in test file
- Commits fd39d8d, 3730794, 7725c75 all present in git log
