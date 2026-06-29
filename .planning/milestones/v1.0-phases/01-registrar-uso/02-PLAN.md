---
phase: 01-registrar-uso
plan: 02
type: execute
wave: 2
depends_on: ["01-01"]
files_modified:
  - assets/erp-manutencao.js
  - cmasm_erp.html
  - tests/conftest.py
  - tests/test_migracoes_idempotencia.py
  - requirements.txt
  - pytest.ini
autonomous: true
requirements: [IMP-01, QA-02]
must_haves:
  truths:
    - "A 'Registrar Uso' tab exists in the manutencao UI: select ativo, enter delta + date + optional observação, click Registrar → POST /api/manutencao/uso via fetch with Bearer token"
    - "After a successful register, the user sees success feedback, the 'Registros Recentes' list refreshes, and a vencimento alert shows inline when vencimentos_disparados is non-empty"
    - "An async pytest fixture (async_app_client via asgi-lifespan LifespanManager) runs db.init() before requests, without modifying the existing sync app_client fixture"
    - "test_migracoes_idempotencia passes: db.init() called twice on the same DB raises no error; uso_registros table exists with expected columns"
    - "The full existing pytest suite still passes (no regression)"
  artifacts:
    - "Registrar Uso tab in assets/erp-manutencao.js (TAB_DEFS id 'registrar-uso')"
    - "tests/test_migracoes_idempotencia.py (new)"
    - "pytest.ini (new) with asyncio_mode = auto"
  key_links:
    - "frontend POSTs to /api/manutencao/uso (the endpoint from Plan 01) with localStorage 'xcmasm_token'"
    - "async_app_client added to conftest.py WITHOUT touching the sync app_client fixture"
    - "'backend.manutencao' added to the sys.modules.pop reload list in BOTH fixtures"
---

<objective>
Deliver the frontend tab and the async test infrastructure for "Registrar Uso". Adds the 'Registrar Uso' tab to the manutencao UI (visual ported from the approved legacy, API-backed not localStorage), the async pytest fixture (pytest-asyncio + asgi-lifespan), the migration idempotency test, and pytest config. Completes IMP-01 (UI) and satisfies QA-02.

Purpose: Closes the vertical slice (user can register usage end-to-end) and establishes the async test fixture reused by phases 2–7.
Output: edits to assets/erp-manutencao.js, cmasm_erp.html, tests/conftest.py, requirements.txt; new tests/test_migracoes_idempotencia.py and pytest.ini.
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/01-registrar-uso/01-CONTEXT.md
@.planning/phases/01-registrar-uso/01-RESEARCH.md
@.planning/phases/01-registrar-uso/01-PATTERNS.md
@.planning/phases/01-registrar-uso/01-01-SUMMARY.md

# Analogs to mirror exactly:
@tests/conftest.py
@tests/test_catalogo.py
@.docs_cmasm/referencias/CMASM_Gestao_v2.html
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add async test fixture, pytest config, and migration idempotency test</name>
  <files>tests/conftest.py, tests/test_migracoes_idempotencia.py, requirements.txt, pytest.ini</files>
  <read_first>
    - tests/conftest.py (lines 18–32) — existing sync app_client fixture; the new fixture must NOT modify it
    - tests/test_catalogo.py (lines 1–54) — sqlite3-direct query helper + app_client usage pattern
    - .planning/phases/01-registrar-uso/01-RESEARCH.md (Pattern 8, Pattern 9, Pitfalls C/D) — LifespanManager + ASGITransport correct wiring, asyncio_mode requirement
  </read_first>
  <action>
Add `pytest-asyncio>=0.23` and `asgi-lifespan>=2.1` to requirements.txt (both verified legitimate in RESEARCH Package Legitimacy Audit — disposition Aprovado). Do not pin httpx differently; it is already 0.27.2.

Create pytest.ini at the repo root with a `[pytest]` section containing `asyncio_mode = auto` (required so `async def test_*` actually execute under pytest-asyncio 0.23+ — Pitfall D).

Edit tests/conftest.py: (a) add `"backend.manutencao"` to the sys.modules.pop reload list inside the EXISTING sync app_client fixture so its db reference is not stale now that manutencao.py exists; do not otherwise change that fixture. (b) Add a NEW `async_app_client` fixture (pytest_asyncio.fixture) that sets DB_PATH to a tmp file, pops the same module list (including backend.manutencao), imports backend.main, then `async with LifespanManager(main.app) as manager:` and `async with AsyncClient(transport=ASGITransport(app=manager.app), base_url="http://test") as client: yield client, main`. Use exactly `transport=ASGITransport(app=manager.app)` — never `app=main.app` directly (Pitfall C). Import pytest_asyncio, asgi_lifespan.LifespanManager, and httpx AsyncClient/ASGITransport at the top of conftest.py.

Create tests/test_migracoes_idempotencia.py mirroring test_catalogo.py style. Include: (1) a test that calls db.init() a second time via the running app (the TestClient already triggered the first init) and asserts no exception — use the sync app_client fixture and run main.db.init() on the event loop; (2) a test that opens main.db.db_path with sqlite3 and asserts PRAGMA table_info(uso_registros) contains the columns id, ativo_id, delta, valor_anterior, valor_novo, data, operador. This proves QA-02: schema loads from scratch and is idempotent (no "duplicate column name").
  </action>
  <verify>
    <automated>cd /home/luc/DEV_ERP/cmasm.erp && grep -q 'pytest-asyncio' requirements.txt && grep -q 'asgi-lifespan' requirements.txt && grep -q 'asyncio_mode' pytest.ini && python -m pytest tests/test_migracoes_idempotencia.py -q</automated>
  </verify>
  <acceptance_criteria>
    - requirements.txt lists pytest-asyncio>=0.23 and asgi-lifespan>=2.1; pytest.ini has asyncio_mode = auto.
    - conftest.py has a new async_app_client fixture using LifespanManager + ASGITransport(app=manager.app); the existing sync app_client fixture is unchanged except for adding "backend.manutencao" to its reload list.
    - tests/test_migracoes_idempotencia.py passes: second db.init() raises nothing; uso_registros columns present.
  </acceptance_criteria>
  <done>Async fixture + pytest.ini + idempotency test added; test_migracoes_idempotencia.py green; sync fixture preserved.</done>
</task>

<task type="auto">
  <name>Task 2: Add 'Registrar Uso' tab to the manutencao UI (API-backed)</name>
  <files>assets/erp-manutencao.js, cmasm_erp.html</files>
  <read_first>
    - assets/erp-manutencao.js (lines 20–32) — TAB_DEFS array; (lines 375–403) — renderTabBar / renderActiveTab switch pattern
    - .docs_cmasm/referencias/CMASM_Gestao_v2.html (lines 193–225) — approved legacy modal layout to port as an inline section
    - .planning/phases/01-registrar-uso/01-RESEARCH.md (Pattern 10) — frontend fetch + alert + recentes pattern; Pitfall B (global name collisions → prefix new functions)
    - cmasm_erp.html (lines 376–381) — dark-theme tab/tab-panel CSS tokens to reuse
  </read_first>
  <action>
Add `{ id: 'registrar-uso', icon: '⏱', label: 'Registrar Uso' }` to TAB_DEFS in assets/erp-manutencao.js. Add a `case 'registrar-uso':` branch in renderActiveTab() that renders the Registrar Uso section (same dispatch pattern as the other tabs). Port the approved layout from CMASM_Gestao_v2.html lines 193–225 as an inline section (NOT a modal): an ativo selector (populated from the existing ativos data the module already loads), a numeric delta input (min 0.1 step 0.1, label shows the selected ativo's unidade_uso), a date input defaulting to today, an optional observação text input, and a Registrar button. Below the form: a feedback area, an inline vencimento alert div (hidden by default), and a "Registros Recentes" container.

Implement the handlers as new functions namespaced to avoid global collisions (Pitfall B — prefix with ru/uso, e.g. window._manut.registrarUso): on Registrar, read the inputs, validate ativo selected and delta > 0 client-side, then `fetch('/api/manutencao/uso', {method:'POST', headers:{'Content-Type':'application/json','Authorization':'Bearer '+localStorage.getItem('xcmasm_token')}, body: JSON.stringify({ativo_id, delta, data, observacao})})`. On non-ok, show data.detail via the existing toast. On success: show success feedback, refresh "Registros Recentes" via GET /api/manutencao/uso?ativo_id=, and if `vencimentos_disparados.length` show the inline alert listing the triggered serviços (else hide it). Replace any legacy localStorage persistence with these API calls (CONTEXT decision). Omit legacy fields not in the data model: Combustível, pre-use checklist, hardcoded operador selector (operador comes from the token server-side).

Do NOT remove existing references to assets/erp-manutencao.js or assets/erp-manutencao-mocks.js from cmasm_erp.html (test_manutencao_smoke.py asserts they remain — Pitfall E). Use dark-theme CSS tokens (var(--bg), var(--panel), var(--acc), var(--text2)) — no hardcoded hex in new markup. If a small amount of HTML scaffolding for the tab panel must live in cmasm_erp.html, add it inside #page-manutencao without disturbing existing markup.
  </action>
  <verify>
    <automated>cd /home/luc/DEV_ERP/cmasm.erp && grep -q "registrar-uso" assets/erp-manutencao.js && grep -q "/api/manutencao/uso" assets/erp-manutencao.js && grep -q "xcmasm_token" assets/erp-manutencao.js && python -m pytest tests/test_manutencao_smoke.py -q</automated>
    <human-check>Open cmasm_erp.html via a static server, go to Manutenção → Registrar Uso, select an ativo, enter a delta + date, click Registrar — confirm success feedback, refreshed "Registros Recentes", and (when a plan is near due) an inline vencimento alert. Visual matches the approved legacy layout.</human-check>
  </verify>
  <acceptance_criteria>
    - TAB_DEFS contains a 'registrar-uso' tab; renderActiveTab renders an inline form (ativo selector, delta, date default today, observação) plus feedback, inline vencimento alert, and Registros Recentes.
    - Register POSTs to /api/manutencao/uso with Bearer localStorage 'xcmasm_token'; success refreshes recentes via GET and shows the vencimento alert only when vencimentos_disparados is non-empty.
    - No legacy localStorage persistence remains for usage; Combustível/checklist/operador-selector omitted; existing erp-manutencao.js / erp-manutencao-mocks.js references in cmasm_erp.html preserved (smoke test passes).
    - New JS functions are namespaced (no global collision with legacy fH/regUso/salvarUso); dark-theme tokens used.
  </acceptance_criteria>
  <done>Registrar Uso tab added and API-backed; smoke test green; recentes + inline vencimento alert work end-to-end.</done>
</task>

<task type="auto">
  <name>Task 3: Full-suite regression check</name>
  <files>tests/</files>
  <read_first>
    - tests/ directory — all existing test files that must still pass
  </read_first>
  <action>
Run the entire pytest suite to confirm no regression from the new router, schema, fixture, and pytest.ini (asyncio_mode = auto must not break the existing sync tests). Fix any breakage introduced by this phase's changes only — do not weaken or skip pre-existing tests. This task gates the phase: success criterion 4 (pytest tests/ green) must hold.
  </action>
  <verify>
    <automated>cd /home/luc/DEV_ERP/cmasm.erp && python -m pytest tests/ -q</automated>
  </verify>
  <acceptance_criteria>
    - python -m pytest tests/ passes with zero failures and zero errors.
    - No pre-existing test was modified to pass (only additive fixture/reload-list changes from Plan 02 Task 1 are allowed).
  </acceptance_criteria>
  <done>Full pytest suite green; no regression introduced by the manutencao slice.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| browser → /api/manutencao/uso | Untrusted form input + Bearer token cross here (client validation is advisory; server is authoritative) |
| test runner → core.db (tmp) | Test fixtures mutate only tmp DBs, never production core.db |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-02-01 | Tampering | frontend delta input | low | mitigate | Client-side delta>0 check is advisory; server field_validator (Plan 01) is authoritative |
| T-02-02 | Spoofing | localStorage Bearer token | medium | accept | Token model unchanged; internal closed network (per RESEARCH); hardening deferred to Phase 7 |
| T-02-03 | Tampering | pip installs (pytest-asyncio, asgi-lifespan) | high | mitigate | Both audited [ASSUMED] OK in RESEARCH Package Legitimacy Audit; test-only deps |
| T-02-SC | Tampering | requirements.txt additions | high | mitigate | Only the two audited test packages added; no [SUS]/[SLOP] packages |
</threat_model>

<verification>
- pytest.ini asyncio_mode = auto does not break the existing sync TestClient tests.
- Existing test_manutencao_smoke.py still passes (asset references preserved).
- Async fixture runs db.init() before requests (uso_registros queryable in async tests).
- End-to-end: register usage in the UI → uso_atual increments, audit row persists, recentes refreshes, vencimento alert shows when applicable.
</verification>

<success_criteria>
- IMP-01 complete (UI + API end-to-end): technician registers usage and sees recentes + vencimento alert.
- QA-02 satisfied: async fixture established (asgi-lifespan) and migration idempotency test green, no regression.
- Phase 1 ROADMAP success criteria 1–5 all hold.
</success_criteria>

<output>
Create `.planning/phases/01-registrar-uso/01-02-SUMMARY.md` when done.
</output>
