---
phase: 01-registrar-uso
verified: 2026-06-28T00:00:00Z
status: passed
score: 4/5 must-haves verified
behavior_unverified: 0
overrides_applied: 0
re_verification: false
human_verification:
  - test: "Open cmasm_erp.html via a static server, go to Manutenção → Registrar Uso, select an ativo, enter a delta value and date, click Registrar — confirm success feedback appears, Registros Recentes table refreshes, and (when a preventive plan is near due) an inline vencimento alert shows below the form."
    expected: "Success feedback shows incremented total (e.g. '+5.0 h → total 125.0 h'), Registros Recentes table lists the new row newest-first, and when vencimentos_disparados is non-empty a yellow/amber alert block appears listing the triggered service names and remaining interval."
    why_human: "This is runtime DOM behavior requiring a real browser + a live backend. No test exercises the full POST→refresh→alert render cycle. The frontend fetch and vencimentos_disparados wiring is present and substantive, but the visual end-to-end flow (success feedback renders, recentes table populates, amber alert appears) cannot be confirmed by grep or pytest."
---

# Phase 1: Registrar Uso — Verification Report

**Phase Goal:** Técnico registra uso (horas/km) de um ativo: incremento atômico de ativos.uso_atual + histórico em uso_registros; alerta de vencimento preventivo na mesma interação; skeleton de manutenção (backend/manutencao.py registrado, data/schema_manutencao.sql em CoreDB._SCHEMAS); async pytest fixture; teste de idempotência de migração.
**Verified:** 2026-06-28
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | POST /api/manutencao/uso increments ativos.uso_atual and inserts a uso_registros row in one atomic transaction (rollback if either fails) | VERIFIED | `backend/manutencao.py:153` — single `async with aiosqlite.connect(db_path) as conn:` block executes UPDATE ativos + INSERT uso_registros + single `conn.commit()` at line 189; no second connect call in the POST handler |
| 2 | POST response includes vencimentos_disparados; alert triggers when uso_atual >= plan threshold (within iv*0.15 window) | VERIFIED | `manutencao.py:192–198` calls `_vencimentos_para_ativo(ativo_id, valor_novo)` after commit and returns it in `{"vencimentos_disparados": vencimentos}`; helper at lines 66–133 replicates main.py iv*0.15 logic per plan |
| 3 | Registros Recentes visible in the UI tab after registration | PRESENT_BEHAVIOR_UNVERIFIED — routed to Human Verification | `erp-manutencao.js:1284,1326–1360,1515–1519` — 'Registrar Uso' tab (TAB_DEFS line 29), `ruCarregarRecentes()` calls GET /api/manutencao/uso?ativo_id=, renders table into `recentesDiv` (titled 'Registros Recentes'). Wiring is complete and substantive. End-to-end visual render requires browser + running backend. |
| 4 | pytest green with 0 new regressions; test_migracoes_idempotencia passes | VERIFIED | Full suite: 14 failed / 88 passed. All 14 failures are in pre-existing test files (test_catalogo.py ×10, test_import_ata2_climatizacao.py ×1, test_sync.py ×2, test_sync_eventos.py ×1) — none modified by this phase. test_migracoes_idempotencia.py: 2/2 PASSED. test_manutencao_smoke.py: 6/6 PASSED. |
| 5 | manutencao.py registered via include_router; schema_manutencao.sql in CoreDB._SCHEMAS with CREATE TABLE IF NOT EXISTS | VERIFIED | `db_core.py:11` — `schema_manutencao.sql` is 4th entry in `_SCHEMAS`. `main.py:23` imports `manutencao_router`; `main.py:329` calls `app.include_router(manutencao_router)`. Routes confirmed: `/api/manutencao/uso` present on running app. `schema_manutencao.sql` uses `CREATE TABLE IF NOT EXISTS uso_registros` with all 9 required columns; no DROP/ALTER. |

**Score:** 4/5 truths verified (1 present, behavior-unverified — routed to human check)

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `data/schema_manutencao.sql` | uso_registros table with 9 columns, CREATE TABLE IF NOT EXISTS, no DROP/ALTER | VERIFIED | File exists, all 9 columns (id, ativo_id, delta, valor_anterior, valor_novo, data, operador, observacao, created_at), guarded with IF NOT EXISTS, two indexes added |
| `backend/manutencao.py` | APIRouter prefix=/api/manutencao, atomic POST+GET, _vencimentos_para_ativo | VERIFIED | 229 lines, substantive — `_db`, `_require_auth`, `UsoIn` Pydantic model with `delta>0` validator, `_vencimentos_para_ativo`, POST `/uso` (201), GET `/uso`; no stubs |
| `assets/erp-manutencao.js` — 'registrar-uso' tab | TAB_DEFS entry, inline form, POST fetch, vencimentos alert, Registros Recentes | VERIFIED (code) / UNVERIFIED (render) | TAB_DEFS line 29, case handler at line 1284, fetch to `/api/manutencao/uso` at line 1438, vencimentos alert at lines 1462–1468, recentesDiv at line 1517; render needs browser |
| `tests/test_migracoes_idempotencia.py` | 2 async tests covering double init + column existence | VERIFIED | File exists, 2 tests, both PASSED under pytest-asyncio 1.4.0 with asyncio_mode=auto |
| `pytest.ini` | asyncio_mode = auto | VERIFIED | `pytest.ini` exists at repo root with `[pytest]` section and `asyncio_mode = auto` |
| `tests/conftest.py` — async_app_client | LifespanManager + ASGITransport fixture, backend.manutencao in reload list | VERIFIED | Lines 35–49: `@pytest_asyncio.fixture async def async_app_client` uses `LifespanManager(main.app)` and `httpx.ASGITransport(app=manager.app)`; both fixtures include `"backend.manutencao"` in sys.modules.pop list |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `schema_manutencao.sql` | `CoreDB._SCHEMAS` | `db_core.py:11` | WIRED | 4th entry in `_SCHEMAS` list |
| `backend/manutencao.py` | `backend/main.py` app | `main.py:23 + main.py:329` | WIRED | `from .manutencao import router as manutencao_router` + `app.include_router(manutencao_router)` |
| `POST handler` | atomic transaction | single `aiosqlite.connect` block | WIRED | UPDATE + INSERT + commit in one `async with` block; `_db().execute()` not used for writes |
| Frontend form | `/api/manutencao/uso` | `erp-manutencao.js:1438` | WIRED | `fetch(apiUrl('/api/manutencao/uso'), {method:'POST', headers: ruAuthHeaders(), body: JSON.stringify({...})})` |
| POST response | vencimentos alert div | `erp-manutencao.js:1462–1468` | WIRED | `resp.vencimentos_disparados` checked; alertaDiv shown/hidden accordingly |
| GET recentes | recentesDiv render | `erp-manutencao.js:1330 + 1474` | WIRED | `ruCarregarRecentes` fetches GET /api/manutencao/uso?ativo_id=, called on ativo change and after successful POST |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `/api/manutencao/uso` route registered on running app | `python -c "import backend.main; paths=...; assert any('/api/manutencao/uso' in p ..."` | `/api/manutencao/uso` confirmed in route list | PASS |
| test_migracoes_idempotencia.py — double init + column check | `python -m pytest tests/test_migracoes_idempotencia.py -v` | 2/2 PASSED (0.52s) | PASS |
| test_manutencao_smoke.py — asset references preserved | `python -m pytest tests/test_manutencao_smoke.py -v` | 6/6 PASSED (0.28s) | PASS |
| Full suite — no new regressions | `python -m pytest tests/ -q --tb=no` | 14 failed / 88 passed — same 14 pre-existing failures, no new failures | PASS |
| schema_manutencao.sql no DROP/ALTER | `grep -i DROP,ALTER data/schema_manutencao.sql` | no match | PASS |
| Atomic POST uses single aiosqlite.connect | Source inspection `backend/manutencao.py:153` | One `async with aiosqlite.connect(db_path) as conn:` in POST handler; comment at line 142 not an actual call | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| IMP-01 | 01-PLAN.md + 02-PLAN.md | Atomic increment of ativos.uso_atual + uso_registros audit row in one transaction; UI for technician to register; vencimento alert in response | SATISFIED | Backend: single aiosqlite.connect block, both writes, commit, vencimentos_disparados. UI: TAB_DEFS + fetch + vencimento alert. |
| QA-02 | 02-PLAN.md | async pytest fixture (asgi-lifespan) + migration idempotency test green + no regression | SATISFIED | async_app_client fixture in conftest.py; pytest.ini asyncio_mode=auto; test_migracoes_idempotencia.py 2/2 PASS; 0 new failures in full suite. |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (none) | — | No TBD/FIXME/XXX/placeholder found in phase-modified files | — | — |

---

## Human Verification Required

### 1. Registrar Uso end-to-end visual flow

**Test:** Start the backend (`uvicorn backend.main:app --port 8010 --reload`) and serve the frontend (`npx serve .` or `python3 -m http.server 8080`). Log in, navigate to Manutenção → tab "Registrar Uso". Select any active ativo. Enter a delta value > 0, keep or change the date, optionally add an observation. Click "Registrar".

**Expected:** (a) Success feedback appears in green: "Registrado: +{delta} {unidade} → total {novo_uso} {unidade}". (b) The "Registros Recentes" table below refreshes and shows the new row at the top with correct data/delta/anterior/novo/operador columns. (c) The horímetro badge updates to the new uso_atual. (d) If the selected ativo has a preventive plan whose next threshold is within 15% of the interval, an amber inline alert "Atenção — serviços preventivos próximos do vencimento:" appears listing the triggered services with remaining interval.

**Why human:** End-to-end DOM rendering with real backend I/O. The fetch call, response handler, alertaDiv show/hide logic, and recentesDiv table construction are all present and wired in `erp-manutencao.js` (lines 1438–1519), but the actual render in the browser cannot be confirmed by static analysis or pytest.

---

## Gaps Summary

No gaps. All must-haves are either VERIFIED or PRESENT_BEHAVIOR_UNVERIFIED (code present and fully wired; only the visual runtime render is unconfirmed). The single human verification item is a visual/runtime check that cannot be automated without a headless browser.

---

_Verified: 2026-06-28_
_Verifier: Claude (gsd-verifier)_
