---
phase: 06-residuais-funcionais
plan: "01"
subsystem: backend-manutencao
tags: [por_tempo, altura_m, vencimentos, locais, rres-01, res-04, tdd]
dependency_graph:
  requires: []
  provides: [por_tempo-alerts, locais-altura_m-migration, locais-altura_m-crud]
  affects: [backend/main.py, backend/manutencao.py, backend/db_core.py, tests/test_manutencao.py]
tech_stack:
  added: []
  patterns: [tdd-red-green, additive-migration, por_tempo-date-guard, mutual-exclusion-continue]
key_files:
  created: []
  modified:
    - backend/db_core.py
    - backend/main.py
    - backend/manutencao.py
    - tests/test_manutencao.py
decisions:
  - "MAX(data) FROM manut_registros WHERE ativo_id=? used as por_tempo last-execution source (MVP granularity: per-ativo, not per-item)"
  - "por_tempo branch ends with explicit continue to prevent fall-through into por_uso path (Pitfall 1 mitigation)"
  - "date imported at module level in main.py (was missing); timedelta was already there"
  - "timedelta already imported at manutencao.py:1256 (no duplicate needed)"
  - "altura_m migration added to locais_existing loop in db_core — PRAGMA-guarded, idempotent"
metrics:
  duration: "~65 minutes"
  completed: "2026-06-29"
  tasks_completed: 3
  files_modified: 4
status: complete
---

# Phase 06 Plan 01: RES-01 por_tempo + RES-04 altura_m Summary

**One-liner:** Additive `locais.altura_m` migration + date-based por_tempo vencimento branch in both evaluation paths, with 6 targeted tests following TDD RED/GREEN cycle.

---

## Objective Achieved

- **RES-01:** `por_tempo` plans now fire alerts in both `manutencao_vencimentos` (main.py) and `_vencimentos_para_ativo` (manutencao.py) when `today >= last_exec_date + valor_days`. Plans with no `manut_registros` rows are silently skipped. `por_tempo` is mutually exclusive with `por_uso` per plan via an explicit `continue` after the por_tempo branch.

- **RES-04:** `locais.altura_m REAL` column added to the `locais_existing` migration loop in `db_core.py`. `LocalIn.altura_m: Optional[float] = None` added to the Pydantic model. `create_local` INSERT and `update_local` UPDATE now persist the column. `list_refrigeracao` already SELECTs `l.altura_m AS local_altura_m` (unchanged). Frontend fallback `|| 2.7` handles NULL safely.

---

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add altura_m migration to locais | `5368279` | backend/db_core.py |
| 2 RED | por_tempo failing tests | `da1c3bc` | tests/test_manutencao.py |
| 2 GREEN | Implement por_tempo branch in both paths | `7257e5b` | backend/main.py, backend/manutencao.py, tests/test_manutencao.py |
| 3 RED | altura_m failing tests | `48630be` | tests/test_manutencao.py |
| 3 GREEN | Persist altura_m through LocalIn + CRUD | `d80692d` | backend/main.py |

---

## Test Results

```
python -m pytest tests/test_manutencao.py tests/test_manutencao_smoke.py -q
21 passed, 31 warnings in 40.51s
```

New tests added (6 total):
- `test_por_tempo_alerta_por_data` — alert fires when manut_registro >= 90 days ago
- `test_por_tempo_sem_registro_nao_alerta` — no crash/alert when no manut_registros
- `test_por_tempo_recente_nao_alerta` — no alert when registro is recent (5 days / 90-day interval)
- `test_por_uso_nao_afetado_por_por_tempo` — por_uso fields uncontaminated by por_tempo branch
- `test_local_altura_m_persists` — POST with altura_m=2.7 persists and round-trips via GET
- `test_local_altura_m_null_safe_listagem` — NULL area_m2/altura_m local listable without crash

Baseline: 9 passing → Final: 15 passing in test_manutencao.py (+6 new); 21 total with smoke tests.

---

## Verification

```bash
python -c "import backend.main, backend.manutencao"  # → OK
python -c "import asyncio; from backend.db_core import CoreDB; db=CoreDB('/tmp/t.db'); asyncio.run(db.init()); asyncio.run(db.init()); print('OK')"  # → OK (no duplicate column error)
```

---

## Deviations from Plan

### Minor Adjustments

**1. [Rule 1 - Bug] Test seed missing `uso_no_momento` NOT NULL column**
- **Found during:** Task 2 RED phase (first test run)
- **Issue:** `manut_registros.uso_no_momento REAL NOT NULL` — initial test seed omitted this column, causing `sqlite3.IntegrityError`
- **Fix:** Added `uso_no_momento=0` to INSERT in both `test_por_tempo_alerta_por_data` and `test_por_tempo_recente_nao_alerta` seeds
- **Files:** tests/test_manutencao.py

**2. [Rule 1 - Bug] test_por_uso_nao_afetado_por_por_tempo assertion incorrect**
- **Found during:** Task 2 GREEN phase
- **Issue:** Test assumed `GET /api/manutencao/vencimentos` returns only `warn`-status entries, but it returns all entries. Assertion `len(por_uso_entries) == 0` was wrong.
- **Fix:** Changed assertion to verify por_uso fields are correctly populated (unidade != 'dias', uso_atual is not None, pct is not None) — proving the por_tempo branch doesn't contaminate por_uso entries
- **Files:** tests/test_manutencao.py

### Known Limitations (Per Research)

- **por_tempo granularity:** `MAX(data) WHERE ativo_id = ?` returns last maintenance date for the entire ativo, not per-item. If an ativo has items with different frequencies, rarer items may have alerts deferred by more-recent executions of other items. Accepted as MVP per 06-RESEARCH.md Pitfall 5 / Open Question 2. Tracked for Phase 7 if needed.

---

## TDD Gate Compliance

| Gate | Status | Commit |
|------|--------|--------|
| RED (por_tempo) | `test(06-01): add failing por_tempo tests` | `da1c3bc` |
| GREEN (por_tempo) | `feat(06-01): implement por_tempo branch` | `7257e5b` |
| RED (altura_m) | `test(06-01): add failing altura_m tests` | `48630be` |
| GREEN (altura_m) | `feat(06-01): persist locais.altura_m` | `d80692d` |

---

## Threat Mitigations Applied

| Threat ID | Mitigation Applied |
|-----------|-------------------|
| T-06-01 | PRAGMA-guarded `ALTER TABLE locais ADD COLUMN altura_m REAL` in locais_existing loop; idempotent on repeat db.init() |
| T-06-02 | `try/except ValueError` around `date.fromisoformat()`; missing manut_registros row → `continue` (no crash, no alert) |
| T-06-03 | No change — read path unchanged; accepted per threat register |

---

## Self-Check: PASSED

- `/home/luc/DEV_ERP/cmasm.erp/backend/db_core.py` — contains `ALTER TABLE locais ADD COLUMN altura_m REAL`
- `/home/luc/DEV_ERP/cmasm.erp/backend/main.py` — contains `altura_m: Optional[float] = None` in LocalIn; por_tempo branch in manutencao_vencimentos; `date` in module imports
- `/home/luc/DEV_ERP/cmasm.erp/backend/manutencao.py` — contains por_tempo branch in _vencimentos_para_ativo
- `/home/luc/DEV_ERP/cmasm.erp/tests/test_manutencao.py` — contains 6 new tests
- Commits: 5368279, da1c3bc, 7257e5b, 48630be, d80692d — all verified in `git log`
- Test run: 21 passed, 0 failed (test_manutencao.py + test_manutencao_smoke.py)
