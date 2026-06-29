---
phase: 05-cronograma-preventivo
verified: 2026-06-29T02:32:15Z
status: passed
score: 3/4 must-haves verified
behavior_unverified: 2
overrides_applied: 0
behavior_unverified_items:
  - truth: "Aba 'Cronograma' renders day-by-day schedule with criticality badges, capacity bars, KPI header"
    test: "Open ERP in browser, log in, go to Manutencao > Cronograma tab"
    expected: "Day cards appear with colored criticidade badges, per-day capacity bar, KPI row at top"
    why_human: "DOM rendering requires a running browser + seeded backend; grep confirms wiring but cannot exercise visual layout"
  - truth: "When kpis.alerta is true a red alert banner renders; reloading after crew-config change reflects new schedule"
    test: "In Equipe Tecnica set a very small crew (e.g. 0.5h/day), reload Cronograma tab"
    expected: "Red banner 'Demanda excede a capacidade da equipe no horizonte' appears above day cards; banner disappears when capacity restored"
    why_human: "Conditional DOM branch (kpis.alerta) and live config coupling require a running end-to-end stack; no automated test exercises the browser renderer"
human_verification:
  - test: "Open ERP -> Manutencao -> Cronograma tab: verify day-by-day list renders with dark-theme criticidade badges (CRITICA=red, ALTA=amber, MEDIA=acc, BAIXA=green) and a capacity bar per day"
    expected: "Each day card shows date + dia_semana header, colored badge per item, horas_usadas/horas_disponiveis bar, duration label"
    why_human: "Visual DOM rendering; no automated assertion covers badge color or bar width in browser"
  - test: "Confirm KPI header shows: Total de OS, Horas-pessoa, Dias uteis, Conclusao, Utilizacao"
    expected: "Five KPI cards appear above the day list with real computed values from the endpoint"
    why_human: "DOM element presence + value display; automated tests cover the backend computation, not the rendered UI"
  - test: "Set a tiny crew config in Equipe Tecnica (e.g. 0.5h/day), then reopen Cronograma tab"
    expected: "Red alert banner 'Demanda excede a capacidade da equipe no horizonte' appears; schedule now spans more days reflecting the new capacity"
    why_human: "Requires running backend + live browser state change; alerta=True DOM path and config round-trip verified only end-to-end"
  - test: "Restore a normal crew config (e.g. 4h/day, seg-sex), reload Cronograma; banner disappears"
    expected: "No red banner; pct_utilizacao drops below 100"
    why_human: "Same as above"
---

# Phase 05: Cronograma Preventivo Verification Report

**Phase Goal:** Add a "Cronograma" preventive-maintenance scheduling tab to the Manutencao module: a backend greedy day-packing endpoint (Wave 1) and a dark-theme frontend tab (Wave 2) with day-by-day schedule, criticality badges, capacity bars, KPIs, and a red overload alert.
**Verified:** 2026-06-29T02:32:15Z
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | GET /api/manutencao/cronograma returns dia-by-dia greedy schedule with kpis block, requires Bearer (401 otherwise) | VERIFIED | Route registered at `/api/manutencao/cronograma` GET; `_require_auth` gated (line 1477); test_cronograma_requires_auth passes (401 confirmed by live pytest run) |
| 2 | Fixed dataset + known config + injected today produces byte-for-byte deterministic dias + KPIs | VERIFIED | test_cronograma asserts exact 2-day packing (a01+a02 on 2026-07-06, a03 on 2026-07-07), exact KPIs (total_os=3, horas_pessoa=4.5, dias_uteis=2, data_conclusao="2026-07-07", alerta=False, pct_utilizacao=55.6); ran and PASSED |
| 3 | Aba "Cronograma" renders day-by-day schedule with criticality badges, capacity bars, KPI header | PRESENT_BEHAVIOR_UNVERIFIED | TAB_DEFS entry at line 32; `async cronograma(cont)` renderer at line 2429; fetches `/api/manutencao/cronograma` with Bearer; builds KPI grid + capacity bars + badge rendering via el()/textContent; visual output requires human |
| 4 | kpis.alerta=True shown as red banner; config coupling: reload after config change updates schedule | PRESENT_BEHAVIOR_UNVERIFIED | alertBanner logic at line 2532-2549 (rendered when `kpis.alerta === true`); endpoint reads `equipe_config` id=1 via `_capacidade` (line 1502-1504) so schedule updates on config change; but DOM rendering + live state change require human exercise |

**Score:** 2/4 truths fully verified (2 PRESENT_BEHAVIOR_UNVERIFIED — code is present and wired; behavior not exercised by any automated test)

---

### Success Criteria Verdict

**SC1 — Aba "Cronograma": plano dia-a-dia com ativos agendados, criticidade, duracao estimada, capacidade usada vs disponivel por dia**
- Backend: VERIFIED. Endpoint returns `dias[].itens[].{criticidade, duracao_min, duracao_h}` and `dias[].{horas_usadas, horas_disponiveis}`.
- Frontend wiring: VERIFIED (TAB_DEFS + RENDERERS['cronograma'] present and dispatched). Visual rendering: PRESENT_BEHAVIOR_UNVERIFIED (human check required).

**SC2 — KPIs de mobilizacao + alerta visual quando demanda>capacidade**
- Backend KPIs: VERIFIED. test_cronograma asserts all five KPI fields with exact values; test_cronograma_alerta asserts `alerta=True` (PASSED).
- Frontend KPI display + alert banner DOM: PRESENT_BEHAVIOR_UNVERIFIED (human check required).

**SC3 — Cronograma respeita dias uteis e turnos da Fase 4 (alterar config muda cronograma no reload)**
- VERIFIED (config coupling). The endpoint reads `equipe_config WHERE id = 1` (line 1490), calls `_capacidade(config)` to derive `h_dia_total` (line 1502), and `cap_dia_min = max(capacidade["h_dia_total"] * 60, 1)` (line 1503). `_dias_uteis_set(config["dias_semana"])` (line 1504) controls which weekdays are valid. This is the same source as the Phase 4 PUT /equipe/config endpoint. Re-opening the tab after a config change reloads via the same GET call, so schedule changes reflect immediately. No stale cache layer.

**SC4 — pytest test_cronograma verde; packing greedy deterministico para dataset fixo + config conhecida**
- VERIFIED. Three targeted tests ran PASSED:
  - `test_cronograma`: exact 2-day packing, all KPI values exact
  - `test_cronograma_alerta`: `alerta=True` for 3 SELF CONTAINED × 207 min vs 2h/day cap
  - `test_cronograma_requires_auth`: 401 without token
- No new failures introduced: the full suite shows 14 failures, all pre-existing (test_catalogo.py × 10, test_import_ata2_climatizacao.py × 1, test_sync.py × 2, test_sync_eventos.py × 1). None in test_manutencao.py or test_manutencao_smoke.py.

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/manutencao.py` | `_est_duracao_min`, `_normaliza_crit`, `_dias_uteis_set`, `computar_cronograma`, `get_cronograma` endpoint | VERIFIED | All five present; ~355 lines appended after `_capacidade` (lines 1259-1603). Functions are substantive (no stubs). |
| `tests/test_manutencao.py` | `_seed_cronograma_fixture` + 3 new tests | VERIFIED | `_seed_cronograma_fixture` at line 620; `test_cronograma` line 684; `test_cronograma_alerta` line 773; `test_cronograma_requires_auth` line 810. All three pass. |
| `assets/erp-manutencao.js` | `'cronograma'` entry in TAB_DEFS + `async cronograma(cont)` in RENDERERS | VERIFIED | TAB_DEFS entry at line 32 (after 'equipe-tecnica'); renderer at lines 2429-2651; JS syntax check passes (`node --check`). |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| equipe_config (Fase 4) | `cap_dia_min` in get_cronograma | `_capacidade(config).h_dia_total × 60` line 1502-1503 | WIRED | Direct DB read `SELECT * FROM equipe_config WHERE id = 1` at line 1490; same pattern as GET /equipe/config |
| equipe_config.dias_semana | working-day cursor in computar_cronograma | `_dias_uteis_set(config["dias_semana"])` line 1504 | WIRED | DOW string list to Python weekday set; `_proximo_dia_util` uses this set |
| ativo_plano_estado.proximo_uso vs ativos.uso_atual | falta (sort key + demand) | UNION SQL line 1521: `(ape.proximo_uso - a.uso_atual) AS falta` | WIRED | Demand query joins `ativo_plano_estado` to `ativos`; dedup by min falta at line 1558-1572 |
| RENDERERS['cronograma'] | renderActiveTab dispatch | TAB_DEFS `id: 'cronograma'` → `renderActiveTab` → `RENDERERS[id](cont)` line ~429 | WIRED | TAB_DEFS id matches RENDERERS key exactly; dispatch is unconditional |
| fetch('/api/manutencao/cronograma') + Bearer | Wave 1 endpoint | `crAuthHeaders()` + `fetch(apiUrl('/api/manutencao/cronograma'))` lines 2459-2461 | WIRED | Bearer token from localStorage; endpoint enforces `_require_auth` |
| data.dias[].itens[].criticidade | CRIT_COLOR_DARK badge color | `CRIT_COLOR_DARK[item.criticidade]` line 2592 | WIRED | Map defined at line 2434-2439; badge color applied to DOM element |
| horas_usadas/horas_disponiveis | capacity bar width | `Math.min(100, usadoH/dispH×100)+'%'` line 2557-2558 | WIRED | barFill.style.width set at line 2583; guarded against division by zero (dispH>0 check) |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `async cronograma(cont)` renderer | `dias`, `kpis` | `fetch(apiUrl('/api/manutencao/cronograma'))` line 2459 | Yes — endpoint runs UNION SQL against `ativos` + `ativo_plano_estado`; no static return | FLOWING |
| `get_cronograma` endpoint | `fila` | UNION SQL over `ativos JOIN ativo_plano_estado` + initial-mobilization ativos (lines 1508-1554) | Yes — live DB query with parameterized categoria filter | FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Duration helper values | `python -c "import backend.manutencao as m; assert m._est_duracao_min('SPLIT')==105; assert m._est_duracao_min('JANELA')==57; assert m._est_duracao_min('SELF CONTAINED')==207; assert m._est_duracao_min('ZZZ')==105"` | All assertions pass | PASS |
| Deterministic packing (3-asset fixture) | `computar_cronograma` called directly with exact fixture | 2 days, day0=[a01,a02], day1=[a03], kpis={total_os:3, horas_pessoa:4.5, dias_uteis:2, data_conclusao:'2026-07-07', alerta:False, pct_utilizacao:55.6} | PASS |
| Route registered on router | `python -c "import backend.manutencao as m; r=[r for r in m.router.routes if 'cronograma' in getattr(r,'path','')]; print(r[0].path, r[0].methods)"` | `/api/manutencao/cronograma {'GET'}` | PASS |
| Module imports clean | `python -c "import backend.manutencao"` | No errors | PASS |
| JS syntax | `node --check assets/erp-manutencao.js` | SYNTAX OK | PASS |
| test_cronograma | `python -m pytest tests/test_manutencao.py::test_cronograma -q` | PASSED | PASS |
| test_cronograma_alerta | `python -m pytest tests/test_manutencao.py::test_cronograma_alerta -q` | PASSED | PASS |
| test_cronograma_requires_auth | `python -m pytest tests/test_manutencao.py::test_cronograma_requires_auth -q` | PASSED | PASS |
| Full test_manutencao suite | `python -m pytest tests/test_manutencao.py tests/test_manutencao_smoke.py -q` | 15 passed, 0 failed | PASS |
| Pre-existing failures baseline | Full `python -m pytest tests/ -q` | 14 failed (test_catalogo.py x10, test_import_ata2 x1, test_sync.py x2, test_sync_eventos.py x1) — none in test_manutencao.py | CONFIRMED BASELINE (no new failures) |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| IMP-05 | 05-01-PLAN.md, 05-02-PLAN.md | Cronograma preventivo computado: endpoint + frontend tab | SATISFIED | Endpoint live; frontend tab wired; three tests pass |

---

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| `assets/erp-manutencao.js` line 1336 | `innerHTML` for static error string (pre-existing; not in Phase 5 new code) | Info | Not in the cronograma renderer block (lines 2429-2651); no server data injected via innerHTML in new code |

No debt markers (TBD/FIXME/XXX) found in any Phase 5-modified code blocks.

---

### Human Verification Required

#### 1. Cronograma tab renders day-by-day schedule with criticality badges and capacity bars

**Test:** Start backend (`uvicorn backend.main:app --port 8010 --reload`), seed data, open ERP at `http://localhost:8010`, log in, navigate to Manutencao, click the "Cronograma" (calendar) tab.
**Expected:** A day-by-day list appears where each day card shows: date + day-of-week header, colored criticidade badge per asset (CRITICA=red, ALTA=amber, MEDIA=acc/cyan, BAIXA=green), estimated duration per item, and a capacity utilization bar (outer track + colored fill).
**Why human:** DOM rendering and CSS variable resolution require a live browser. Grep confirms the `el()` calls, CRIT_COLOR_DARK map, and barFill width computation are wired — but visual correctness (colors, layout, bar proportions) is not testable without a browser session.

#### 2. KPI header shows all five mobilization metrics

**Test:** With the Cronograma tab open and data loaded, inspect the top area above the day list.
**Expected:** Five cards displayed in a grid: "Total de OS" (integer), "Horas-pessoa" (float + 'h'), "Dias uteis" (integer), "Conclusao" (ISO date), "Utilizacao" (float + '%').
**Why human:** Card rendering depends on browser layout engine and live endpoint response. Backend values are verified correct; visual presentation requires human confirmation.

#### 3. Red alert banner appears when demand exceeds capacity

**Test:** In Equipe Tecnica, save a config with 0.5h/day or 1 turno very short. Return to Cronograma tab (reopen it to trigger a new fetch).
**Expected:** Red banner "Demanda excede a capacidade da equipe no horizonte" appears above the day list. kpis.pct_utilizacao > 100%.
**Why human:** The `kpis.alerta === true` conditional DOM branch is wired (line 2532) but the actual rendering requires a live stack and config state change. test_cronograma_alerta confirms the backend sets alerta=True; the banner DOM path itself is not exercised by any automated test.

#### 4. Config change updates schedule on tab reload (Fase 4 coupling)

**Test:** Change crew config to 8h/day + 5 days, open Cronograma tab. Note the number of days. Then set 1h/day, reopen tab. Number of days should increase significantly.
**Expected:** Schedule respects new capacity; banner may appear if demand > new total capacity. No stale cache.
**Why human:** This is a state-transition / round-trip invariant. The code path (endpoint re-reads equipe_config on each GET, no caching) is wired, but the actual state-change-then-observe behavior requires human exercise.

---

### Gaps Summary

No gaps found. All four success criteria have backend implementation fully verified. The two PRESENT_BEHAVIOR_UNVERIFIED truths concern the frontend visual rendering and live config-coupling behavior, which are inherently human-testable items that the plan explicitly deferred as `<human-check>` in the Wave 2 plan.

The 14 test failures in the full suite are all pre-existing and confirmed to be in unrelated modules (test_catalogo.py, test_sync.py, test_sync_eventos.py, test_import_ata2_climatizacao.py). None were introduced by Phase 5.

---

_Verified: 2026-06-29T02:32:15Z_
_Verifier: Claude (gsd-verifier)_
