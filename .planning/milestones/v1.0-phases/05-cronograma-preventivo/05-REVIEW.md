---
phase: 05-cronograma-preventivo
reviewed: 2026-06-28T23:55:00-03:00
depth: deep
files_reviewed: 3
files_reviewed_list:
  - backend/manutencao.py
  - tests/test_manutencao.py
  - assets/erp-manutencao.js
findings:
  critical: 0
  warning: 1
  info: 0
  total: 1
status: findings
---

# Phase 05: Code Review Report — Cronograma Preventivo

**Reviewed:** 2026-06-28T23:55:00-03:00
**Depth:** deep (cross-file, algorithm tracing)
**Files Reviewed:** 3
**Status:** findings (1 warning)

## Summary

Phase 5 introduces `computar_cronograma` (greedy packing), `_est_duracao_min`, `_normaliza_crit`, `_dias_uteis_set`, and `GET /api/manutencao/cronograma`. The implementation is largely correct:

- Auth (`_require_auth`) is present on the endpoint.
- SQL is fully parameterized (4 placeholders, 4 args); UNION ALL is correct; `ORDER BY` removed from the first branch per SQLite constraint (commit 3ca10fc).
- Dedup by `ativo_id` handles `None` item_id and negative `falta` correctly via `or 0` coercion before tuple comparison.
- Duration formula is an exact port of `estTempoServico()` from the legacy JS (verified against all four equipment types).
- DOW mapping uses an explicit pt-BR → Python `weekday()` dict; no off-by-one.
- Empty demand (zero assets): `novo_dia()` opens one day, the trailing-empty-day pop removes it, `dias=[]`, `cap_total=0`, `pct_utilizacao=0.0` — no division by zero.
- Zero-capacity guard: `max(cap_dia_min, 1)` in both `get_cronograma` and `computar_cronograma` (double guard, harmless).
- `_dias_uteis_set` falls back to Mon–Fri on empty/corrupt input, preventing an infinite loop in `_proximo_dia_util`.
- `_normaliza_crit` maps `'operacional'` / `None` / unrecognized → `'MÉDIA'` correctly (Unicode-exact match required).
- Sort is stable (Python Timsort) with three-key tuple `(CRIT_ORDER[crit], falta, ativo_id)`.
- Frontend (`cronograma` renderer): all server data rendered via `textContent`; no `innerHTML` of server strings; Bearer token sent correctly; capacity bars computed arithmetically from numeric fields only.
- `today` query param is injectable by authenticated users (intentional for deterministic testing; internal network per scope).

One latent logic bug was found in the guard/KPI computation path.

---

## Warnings

### WR-01: Off-by-one in KPI counters when MAX_JOBS or MAX_DAYS (overflow path) guard fires

**File:** `backend/manutencao.py:1408–1437`

**Issue:** `guard` is incremented at the top of the loop body — before the `if guard > MAX_JOBS: break` check. When that break fires, `guard = MAX_JOBS + 1` but only `MAX_JOBS` jobs were actually appended to the schedule. The KPI slice uses `processed = min(guard, len(fila))`, which equals `MAX_JOBS + 1`, so `total_os` is overcounted by 1 and `total_min` (and therefore `horas_pessoa`, `pct_utilizacao`, `alerta`) includes the duration of one job that was never packed.

The same off-by-one occurs on the MAX_DAYS overflow path (line 1417–1418): `guard` was already incremented for the current iteration but `dia_atual['itens'].append(job)` had not yet executed when `break` fires, so again the job is counted in `processed` but is absent from the schedule.

The same pattern does NOT affect the "fill" MAX_DAYS path (line 1427–1429) because the job was already appended before that break; that path is correct.

**Practical scope:** Triggers only when the total number of assets in scope exceeds 5 000 (MAX_JOBS) or when more than 365 working days of backlog exist (MAX_DAYS via overflow). Neither threshold is reachable in the current dataset. The bug is dormant but produces silent wrong KPIs when hit.

**Fix:**

```python
# Option A — increment guard AFTER the break check (simplest):
for job in fila:
    if guard >= MAX_JOBS:   # >= instead of post-increment >
        break
    guard += 1

# Option B — use loop index (enumerate) to avoid manual guard:
for guard, job in enumerate(fila):
    if guard >= MAX_JOBS:
        break
    # ... rest of loop unchanged ...

# KPI slice stays the same:
processed = min(guard, len(fila))   # now correct for all break paths
```

For the MAX_DAYS overflow path specifically, replace:

```python
# Current (line 1416-1419):
if job_min > restante and len(dia_atual["itens"]) > 0:
    if len(dias) >= MAX_DAYS:
        break

# Fixed — decrement guard before breaking since job was not scheduled:
if job_min > restante and len(dia_atual["itens"]) > 0:
    if len(dias) >= MAX_DAYS:
        guard -= 1   # undo the increment for the unscheduled job
        break
```

Either approach is acceptable; Option A (move increment after break check) is cleanest as it fixes both break sites simultaneously.

---

_Reviewed: 2026-06-28T23:55:00-03:00_
_Reviewer: Claude (gsd-code-reviewer — adversarial)_
_Depth: deep_
