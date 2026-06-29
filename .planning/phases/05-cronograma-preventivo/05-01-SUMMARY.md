---
phase: 05-cronograma-preventivo
plan: 01
subsystem: backend/manutencao
tags: [scheduling, greedy-packing, preventive-maintenance, api, tests]
status: complete

dependency_graph:
  requires:
    - Phase 4 equipe_config (h_dia_total, dias_semana, turnos)
    - Phase 2 ativo_plano_estado (proximo_uso, catalogo_plano_item_id)
    - schema_core.sql: ativos, pmoc_refrigeracao, pmoc_transportes, pmoc_corte, pmoc_fonoclama
  provides:
    - GET /api/manutencao/cronograma — dias+kpis JSON for Wave 2 frontend tab
  affects:
    - backend/manutencao.py — appended ~355 lines (helpers + endpoint)
    - tests/test_manutencao.py — appended 3 new tests + seed helper

tech_stack:
  added:
    - computar_cronograma: greedy day-packing scheduler (port of pmocCronograma JS)
    - _est_duracao_min: legacy duration formula from cmasm13-govbr-v8_3.html
    - _normaliza_crit: criticidade normalization (operacional/None → MÉDIA)
    - _dias_uteis_set: pt-BR DOW string → Python weekday integer set
  patterns:
    - Parameterized UNION SQL (T-05-01 — no string interpolation)
    - today query param injection for test determinism (Pitfall 1)
    - Dedup by ativo_id keeping min-falta row (Pitfall 3)
    - MAX_JOBS=5000 / MAX_DAYS=365 guards (T-05-03)

key_files:
  modified:
    - backend/manutencao.py: _est_duracao_min, _normaliza_crit, _dias_uteis_set,
      _proximo_dia_util, computar_cronograma, get_cronograma endpoint
    - tests/test_manutencao.py: _seed_cronograma_fixture, test_cronograma,
      test_cronograma_alerta, test_cronograma_requires_auth

decisions:
  - key: "alerta test uses 2h/day crew config"
    rationale: |
      RESEARCH specifies 3 SELF CONTAINED + 4h cap → alerta=True, but mathematically
      3×207=621 packed into 3 days yields cap_total=720 > 621 → alerta=False.
      The test uses 2h/day (cap=120 min) instead: 3×207=621 > 3×120=360 → alerta=True.
      Deviation documented as Rule 1 (RESEARCH spec error — fix applied).
  - key: "categoria filter in test requests"
    rationale: |
      The test DB is pre-seeded with 10 fonoclama ativos (startup seed in main.py).
      Tests pass categoria=climatizacao to isolate the 3-asset fixture.
  - key: "SQL UNION ORDER BY removed from first branch"
    rationale: |
      SQLite rejects ORDER BY in individual UNION branches (not in a subquery).
      Ordering is not needed since Python handles dedup+sort after the query.

metrics:
  duration: "~25 min"
  completed: "2026-06-28"
  tasks_completed: 3
  tasks_total: 3
  files_modified: 2
  lines_added: ~555
---

# Phase 05 Plan 01: Cronograma Preventivo Backend Compute Slice Summary

**One-liner:** Greedy day-packing scheduler for preventive maintenance with KPIs, ported from JS legacy into `GET /api/manutencao/cronograma` with deterministic tests.

---

## What Was Built

### Scheduling helpers (backend/manutencao.py — appended after `_capacidade`)

**Constants (verbatim from legacy cmasm13-govbr-v8_3.html lines 911-917):**

| Constant | Values |
|----------|--------|
| `MIN_POR_ITEM` | 10 min/item |
| `SETUP_MIN` | 15 min |
| `FATOR_TIPO_EQUIP` | SPLIT=1.0, PISO/TETO=1.15, JANELA=0.7, SELF CONTAINED=1.6 |
| `FATOR_MANUT` | PREVENTIVA=1.0, REVISÃO=1.6, CORRETIVA=1.3, ... |
| `N_CHECKLIST` | SPLIT=9, PISO/TETO=9, SELF CONTAINED=12, JANELA=6, _DEFAULT=9 |
| `CRIT_ORDER` | CRÍTICA=0, ALTA=1, MÉDIA=2, BAIXA=3 |
| `_DOW_STR_TO_PY` | seg→0, ter→1, qua→2, qui→3, sex→4, sab→5, dom→6 |
| `MAX_JOBS` | 5000 |
| `MAX_DAYS` | 365 |

**Duration formula:**
```
_est_duracao_min(tipo, tipo_manut="PREVENTIVA") = round(n × MIN_POR_ITEM × f_eq × f_m + SETUP_MIN)
```
Examples: SPLIT→105 min, PISO/TETO→119 min, JANELA→57 min, SELF CONTAINED→207 min, fallback→105 min.

**Sort key (stable determinism contract):**
```python
fila.sort(key=lambda j: (CRIT_ORDER.get(j["criticidade"], 2), j["falta"], j["ativo_id"]))
```

**computar_cronograma algorithm:**
1. Open first working day (`novo_dia` advances cursor, records ISO date + pt-BR abbrev, then steps cursor forward).
2. For each job: if `job_min > restante AND current day has items` → overflow to next day; place job; if `restante <= 0` → open next day.
3. Pop trailing empty day.
4. KPIs: `total_os`, `horas_pessoa=round(Σmin/60,1)`, `dias_uteis=len(dias)`, `data_conclusao=dias[-1]["data"]`, `pct_utilizacao=round(Σmin/(cap_dia_min×dias_uteis)×100,1)`, `alerta=Σmin>cap_total`.

### Endpoint: GET /api/manutencao/cronograma

```
GET /api/manutencao/cronograma?categoria=<str>&today=<YYYY-MM-DD>
Authorization: Bearer <token>
→ {dias:[...], kpis:{...}}
```

**Flow:**
1. `_require_auth(authorization)` — 401 if missing/invalid (T-05-02)
2. Parse `today` with `date.fromisoformat()` → 422 on bad format (T-05-04)
3. Load `equipe_config` (mirrors GET /equipe/config pattern) → `cap_dia_min`, `dias_uteis_py`
4. Parameterized UNION SQL: ativos with `ativo_plano_estado` + ativos without (falta=0) (T-05-01)
5. Dedup by `ativo_id` keeping min-falta row; normalize criticidade; compute `duracao_min`, `status`
6. Stable sort → `computar_cronograma` → return `{dias, kpis}`

**Response shape:**
```json
{
  "dias": [
    {
      "data": "2026-07-06",
      "dia_semana": "Seg",
      "itens": [
        {"ativo_id": "a01", "nome": "...", "tipo": "SPLIT", "criticidade": "CRÍTICA",
         "duracao_min": 105, "duracao_h": 1.75, "falta": -5.0, "status": "VENCIDA"}
      ],
      "horas_usadas": 3.5,
      "horas_disponiveis": 4.0
    }
  ],
  "kpis": {
    "total_os": 3,
    "horas_pessoa": 4.5,
    "dias_uteis": 2,
    "data_conclusao": "2026-07-07",
    "pct_utilizacao": 55.6,
    "alerta": false
  }
}
```

---

## Test Results

```
tests/test_manutencao.py::test_cronograma        PASSED
tests/test_manutencao.py::test_cronograma_alerta PASSED
tests/test_manutencao.py::test_cronograma_requires_auth PASSED
```

**test_cronograma exact KPI assertions (3-asset fixture, today=2026-07-06, categoria=climatizacao):**

| KPI | Expected | Formula |
|-----|---------|---------|
| total_os | 3 | len(fila) |
| horas_pessoa | 4.5 | round(267/60, 1) — IEEE 754: 4.45 rounds to 4.5 |
| dias_uteis | 2 | len(dias) |
| data_conclusao | "2026-07-07" | dias[-1]["data"] |
| pct_utilizacao | 55.6 | round(267/(240×2)×100, 1) |
| alerta | False | 267 < 480 |

**test_cronograma_alerta:** 3 SELF CONTAINED × 207 min = 621 min vs cap 2h/day=120 min → 621 > 360 → `alerta=True`.

**Full suite result:** 15 passed (9 test_manutencao.py + 6 test_manutencao_smoke.py), 0 failed, no regressions.

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] RESEARCH alerta test dataset mathematically inconsistent**
- **Found during:** Task 3
- **Issue:** RESEARCH specified `alerta=True` for 3 SELF CONTAINED + 4h cap (240 min). Math: 3×207=621, packed into 3 days → cap_total=720 > 621 → alerta=False (not True).
- **Fix:** Changed alerta test to use 2h/day crew config (cap=120 min). Then: 621 > 360 → alerta=True.
- **Files modified:** tests/test_manutencao.py
- **Commit:** 3ca10fc

**2. [Rule 1 - Bug] SQLite ORDER BY in UNION branch rejected**
- **Found during:** Task 3 test run
- **Issue:** `ORDER BY a.id` inside the first SELECT of a UNION ALL is illegal in SQLite ("ORDER BY clause should come after UNION ALL not before").
- **Fix:** Removed the ORDER BY from the first UNION branch. Python handles all ordering after the query.
- **Files modified:** backend/manutencao.py
- **Commit:** 3ca10fc

**3. [Rule 2 - Missing critical] Test needs categoria filter to isolate fixture**
- **Found during:** Task 3
- **Issue:** The test DB is pre-seeded at startup with 10 fonoclama assets. Calling `/cronograma` without a category filter returned 13 assets across 7 days instead of 3 assets across 2 days.
- **Fix:** Tests pass `categoria=climatizacao` query param to isolate the seeded test fixture.
- **Files modified:** tests/test_manutencao.py
- **Commit:** 3ca10fc

---

## Known Stubs

None. The endpoint returns live-computed data from actual DB rows.

---

## Threat Flags

No new security surface introduced. The endpoint is read-only. All threats per the plan's threat register were mitigated:
- T-05-01: categoria bound as parameter (`? IS NULL OR a.categoria = ?`)
- T-05-02: `_require_auth` gate before any data read
- T-05-03: `cap_dia_min = max(..., 1)` + MAX_JOBS/MAX_DAYS guards
- T-05-04: `date.fromisoformat()` with ValueError → 422

---

## Self-Check: PASSED

- `backend/manutencao.py` modified (helpers + endpoint): FOUND
- `tests/test_manutencao.py` modified (3 new tests): FOUND
- Commit 39a2302 (Task 1+2): FOUND
- Commit 3ca10fc (Task 3): FOUND
- `python -c "import backend.manutencao"`: PASSED
- `python -m pytest tests/test_manutencao.py tests/test_manutencao_smoke.py -q`: 15 passed, 0 failed
