---
phase: 01-registrar-uso
plan: 02
subsystem: frontend+testing
tags: [vanilla-js, pytest-asyncio, asgi-lifespan, manutencao, registrar-uso, idempotencia]

# Dependency graph
requires:
  - "01-01 — backend POST/GET /api/manutencao/uso routes + uso_registros schema"
provides:
  - "assets/erp-manutencao.js — TAB_DEFS entry 'registrar-uso' + RENDERERS['registrar-uso'] async renderer"
  - "tests/conftest.py — async_app_client fixture (LifespanManager + ASGITransport); backend.manutencao added to both fixture reload lists"
  - "tests/test_migracoes_idempotencia.py — two async tests: init_twice_sem_erro + uso_registros_criada_apos_init"
  - "pytest.ini — asyncio_mode = auto"
  - "requirements.txt — pytest-asyncio>=0.23, asgi-lifespan>=2.1"
affects:
  - "phases 2-7 — async_app_client fixture reusable by all future maintenance plans"
  - "cmasm_erp.html — no changes needed (tab rendering is fully JS-driven)"

# Tech tracking
tech-stack:
  added:
    - "pytest-asyncio==1.4.0 (installed; satisfies >=0.23)"
    - "asgi-lifespan==2.1.0 (installed)"
    - "sniffio==1.3.1 (transitive dep of asgi-lifespan)"
  patterns:
    - "async_app_client: LifespanManager(main.app) + httpx.AsyncClient(transport=ASGITransport(app=manager.app)) — triggers db.init() via ASGI lifespan before any request"
    - "asyncio_mode = auto in pytest.ini — all async def test_* automatically run under pytest-asyncio without @pytest.mark.asyncio decorator"
    - "RENDERERS async method pattern: 'registrar-uso'(cont) uses await fetch() for POST and GET inside the renderer"
    - "ru_ prefix convention for functions inside the 'registrar-uso' renderer to avoid global collisions (Pitfall B)"
    - "ruToken() reads localStorage('xcmasm_token'); ruAuthHeaders() builds Authorization header — consistent with erp-refrigeracao.js pattern"

key-files:
  created:
    - "tests/test_migracoes_idempotencia.py"
    - "pytest.ini"
  modified:
    - "assets/erp-manutencao.js"
    - "tests/conftest.py"
    - "requirements.txt"

key-decisions:
  - "Renderer implemented entirely in JS (RENDERERS object) — no HTML changes to cmasm_erp.html required, preserving smoke-test assertions"
  - "ru_ function prefix chosen (ruToken, ruAuthHeaders, ruCarregarRecentes, ruBuildAtivoOpts, ruOnAtivoChange) to namespace cleanly inside the IIFE scope without polluting window"
  - "async_app_client uses ASGITransport(app=manager.app) not ASGITransport(app=main.app) — critical: routes all requests through the lifespan-managed app instance (Pitfall C)"
  - "asyncio_mode = auto applied globally — avoids per-test @pytest.mark.asyncio; existing sync TestClient tests are unaffected"
  - "backend.manutencao added to sys.modules.pop list in BOTH fixtures (sync app_client and async async_app_client) — prevents stale db references across test isolation"
  - "Ativo dropdown populated from state.cache.ativos (already loaded by the module) — no extra API call on tab render"
  - "Delta input uses min=0.1 step=0.1; client-side validation is advisory (server Pydantic validator is authoritative, as per STRIDE T-02-01)"

metrics:
  duration: 25min
  completed: 2026-06-28
  tasks: 3
  files: 5 (2 created, 3 modified)

status: complete
---

# Phase 01 Plan 02: Registrar Uso — Frontend + Test Infrastructure Summary

**Async pytest fixture (LifespanManager + ASGITransport) and Registrar Uso tab (API-backed, dark-theme, namespaced) completing IMP-01 vertical slice end-to-end**

## Performance

- **Duration:** 25 min
- **Started:** 2026-06-28T00:25:00Z
- **Completed:** 2026-06-28T00:50:00Z
- **Tasks:** 3
- **Files created:** 2 (pytest.ini, tests/test_migracoes_idempotencia.py)
- **Files modified:** 3 (requirements.txt, tests/conftest.py, assets/erp-manutencao.js)

## Accomplishments

### Task 1: Async fixture + pytest config + migration idempotency test

- Added `pytest-asyncio>=0.23` and `asgi-lifespan>=2.1` to `requirements.txt` (installed: 1.4.0 and 2.1.0)
- Created `pytest.ini` with `asyncio_mode = auto` — enables `async def test_*` without decorator boilerplate
- Updated `tests/conftest.py`: added `backend.manutencao` to sys.modules.pop reload list in the existing sync `app_client` fixture; added new `async_app_client` fixture using `LifespanManager` + `ASGITransport(app=manager.app)` (Pitfall C avoided)
- Created `tests/test_migracoes_idempotencia.py` with two async tests: `test_init_twice_sem_erro` (calls `db.init()` twice — no exception) and `test_uso_registros_criada_apos_init` (confirms 7 expected columns present)
- Both tests green: 2/2 passed

### Task 2: Registrar Uso tab (API-backed)

- Added `{ id: 'registrar-uso', icon: '⏱', label: 'Registrar Uso' }` to `TAB_DEFS` array
- Added `async 'registrar-uso'(cont)` renderer inside `RENDERERS` object with complete layout:
  - Ativo selector populated from `state.cache.ativos` (active ativos only), no extra API call
  - Horímetro badge showing `uso_atual + unidade_uso` (updates on ativo change)
  - Date input (defaults to today), delta input (min=0.1, step=0.1, unidade label updates dynamically), observação input
  - Registrar button: POST `/api/manutencao/uso` with `Authorization: Bearer <xcmasm_token>`
  - Inline feedback on success (`+X h → total Y h`)
  - Inline vencimento alert (amber card) — shown only when `vencimentos_disparados.length > 0`
  - Registros Recentes table via GET `/api/manutencao/uso?ativo_id=&limit=10`
- All functions prefixed `ru_` to avoid collisions with legacy `fH`, `regUso`, `salvarUso`
- Dark-theme CSS tokens exclusively (`var(--bg)`, `var(--panel)`, `var(--acc)`, `var(--line)`, `var(--ink)`, `var(--amber)`, `var(--green)`)
- Legacy fields NOT ported: Combustível, checklist pré-uso, hardcoded operador selector
- Both `erp-manutencao.js` and `erp-manutencao-mocks.js` script references preserved in `cmasm_erp.html` — all 6 smoke tests pass

### Task 3: Full-suite regression check

- Baseline (pre-phase): **14 failed, 86 passed**
- Post-phase: **14 failed, 88 passed** (gained 2 new tests from Task 1)
- Exact same 14 pre-existing failures — zero regressions introduced

## Task Commits

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Async fixture + pytest.ini + idempotency test | `4de5ad9` | requirements.txt, pytest.ini, tests/conftest.py, tests/test_migracoes_idempotencia.py |
| 2 | Registrar Uso tab (API-backed) | `dc06735` | assets/erp-manutencao.js |
| 3 | Regression check (no code change) | — | (verification only) |

## Deviations from Plan

None — plan executed exactly as written.

- TAB_DEFS entry added as specified
- `async_app_client` uses `LifespanManager + ASGITransport(app=manager.app)` exactly as Pattern 8
- `asyncio_mode = auto` in `pytest.ini` as specified (Pitfall D avoided)
- `backend.manutencao` added to both fixture reload lists as specified
- No legacy localStorage persistence; Combustível/checklist/operador-selector omitted
- Legacy script references in `cmasm_erp.html` preserved (Pitfall E avoided)
- `cmasm_erp.html` unchanged — no HTML scaffolding needed since tab rendering is fully RENDERERS-driven

## Pre-existing Failures (NOT regressions — tracked per constraints)

The plan cited 3 pre-existing failures; the actual baseline has 14. All 14 pre-date this phase:

| Test | Failure Reason |
|------|---------------|
| test_catalogo.py (10 tests) | HTTP 410 vs 401 expected; KeyError 'id'; FK constraint differences |
| test_import_ata2_climatizacao.py::test_parse_ata2_estrutura | FileNotFoundError (file not in repo) |
| test_sync.py (2 tests) | OperationalError / assertion mismatch unrelated to manutencao |
| test_sync_eventos.py::test_estoque_mov_saida_decrementa_qtd | sqlite3 OperationalError |

These are logged in deferred-items.md scope and remain out of scope for this plan.

## IMP-01 Status: COMPLETE

Vertical slice end-to-end:
1. User goes to Manutenção → clicks "Registrar Uso" tab
2. Selects ativo from dropdown (populated from cache, shows horímetro atual)
3. Enters delta (hours/km), date (defaults today), optional observação
4. Clicks Registrar → POST `/api/manutencao/uso` with Bearer token
5. Sees success feedback (`+X h → total Y h`) and refreshed Registros Recentes table
6. If any plans near threshold: inline amber alert lists triggered services

## QA-02 Status: SATISFIED

- `async_app_client` fixture established (asgi-lifespan + httpx ASGITransport)
- `test_migracoes_idempotencia.py`: 2/2 tests green
  - `test_init_twice_sem_erro`: db.init() called twice — no error
  - `test_uso_registros_criada_apos_init`: 7 expected columns present in uso_registros
- No regression: 14 pre-existing failures unchanged, +2 new tests passing

## Threat Surface Scan

No new security surface introduced beyond what was in Plan 01:
- T-02-01 (Tampering, frontend delta): Client-side `delta > 0` check present (advisory); server Pydantic `field_validator` is authoritative
- T-02-02 (Spoofing, localStorage token): Accepted per plan — internal closed network; hardening deferred to Phase 7
- No new network endpoints, auth paths, or DB schema changes in this plan

## Self-Check

- `pytest.ini` exists: FOUND
- `tests/test_migracoes_idempotencia.py` exists: FOUND
- `tests/conftest.py` exists: FOUND
- `assets/erp-manutencao.js` exists: FOUND
- Commit `4de5ad9` exists: FOUND
- Commit `dc06735` exists: FOUND
- `registrar-uso` in TAB_DEFS: VERIFIED
- `/api/manutencao/uso` in JS fetch: VERIFIED
- test_migracoes_idempotencia: 2/2 PASSED
- smoke tests: 6/6 PASSED
- Full suite: 88 passed, 14 pre-existing failures, 0 new failures

## Self-Check: PASSED
