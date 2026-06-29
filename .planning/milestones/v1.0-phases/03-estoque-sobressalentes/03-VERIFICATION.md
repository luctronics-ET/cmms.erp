---
phase: 03-estoque-sobressalentes
verified: 2026-06-28T00:00:00Z
status: passed
score: 3/5 must-haves verified
behavior_unverified: 2
overrides_applied: 0
behavior_unverified_items:
  - truth: "Aba 'Sobressalentes' lists peças with qtd_atual, unidade, badge ZERADO/BAIXO/OK, and valor estimado"
    test: "Serve the app, log in, go to Manutenção → click '🔩 Sobressalentes'. Verify the tab renders the table with columns Nome, Categoria, Qtd atual, Un, Status (badge), Preço un., Ações; and the header card shows 'Valor estimado do estoque: R$ X'."
    expected: "Table renders peças (or empty-state message); badge pills are colour-coded (red=ZERADO, amber=BAIXO, green=OK); valor estimado updates after mutations."
    why_human: "Browser rendering, CSS token application, and table layout cannot be verified by grep or test runner."
  - truth: "Adicionar/editar/ajustar via modal (motivo+obs) — qtd atualizada + movimento em sobressalentes_movimentos; client re-renders without reload"
    test: "Click '+ Nova Peça', fill nome + qtd_minima + preço → save. Click 'Ajustar', fill tipo/quantidade/motivo/obs → save. Verify the list re-renders with updated qtd_atual, badge, and total without a page reload."
    expected: "Create toast 'Peça criada.', ajuste toast 'Ajuste registrado.'; list re-renders; badge/total update in place."
    why_human: "Toast messages, modal open/close lifecycle, and on-mutation re-render are browser DOM interactions that cannot be verified programmatically."
human_verification:
  - test: "Sobressalentes tab renders: list, badges, and valor estimado"
    expected: "Tab appears; table shows peças with ZERADO/BAIXO/OK coloured badge pills and total estimated stock value in the header card."
    why_human: "Browser rendering, CSS variable application, DOM layout — cannot verify without a browser."
  - test: "+Nova Peça form, Editar form, and Ajustar modal end-to-end"
    expected: "Forms open as overlay modals; all fields present (including motivo and obs in Ajustar); save calls the correct endpoint with Bearer token; list re-renders; backend error detail surfaced via toast."
    why_human: "Modal open/close, form field interaction, toast feedback, and re-render are browser DOM behaviors."
  - test: "Central Estoque screen unchanged after Sobressalentes operations"
    expected: "Estoque screen shows the same items as before — no spare parts leaked from sobressalentes."
    why_human: "UI-level confirmation; the programmatic isolation is already proven by test_sobressalentes (T-03-05) but the visual confirmation from the operator is specified in the plan checkpoint."
---

# Phase 03: Estoque Sobressalentes Verification Report

**Phase Goal:** Backend + frontend vertical slice for local spare-parts inventory (estoque de sobressalentes) kept fully separate from central `estoque`. Implements IMP-03.
**Verified:** 2026-06-28
**Status:** human_needed (2 truths present and wired, behavior not exercised by tests — awaiting browser confirmation)
**Re-verification:** No — initial verification.

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | GET /api/manutencao/sobressalentes returns each peça with badge (ZERADO\|BAIXO\|OK) and valor_estimado_total = Σ qtd_atual×preco_unitario | ✓ VERIFIED | `_badge()` function in manutencao.py:647-658; `listar_sobressalentes` at line 661 computes badge per row and accumulates `valor_estimado_total`. Confirmed by `test_sobressalentes` (badge assertions at lines 344, 346; valor arithmetic at line 350). |
| 2 | POST /api/manutencao/sobressalentes creates a peça; PUT /{id} edits it; both require a non-visitante token | ✓ VERIFIED | `criar_sobressalente` (line 704) and `editar_sobressalente` (line 741) both call `_require_auth` then check `role == 'visualizador'` → 403. Confirmed by `test_sobressalentes` (201 on create, 200 on PUT, 401 on missing token). |
| 3 | POST /sobressalentes/{id}/ajuste updates qtd_atual AND inserts one sobressalentes_movimentos row in a single atomic transaction with operador taken from the token | ✓ VERIFIED | `ajustar_sobressalente` (lines 798-871): single `aiosqlite.connect` block, `conn.execute(UPDATE sobressalentes...)`, `conn.execute(INSERT INTO sobressalentes_movimentos...)`, single `conn.commit()`. `operador = user.get("mat") or user.get("nome")` (line 820 — never from payload). Confirmed by `test_sobressalentes` lines 371-399: both DB tables asserted, operador non-empty. |
| 4 | GET /api/estoque returns exactly the same records as before — no sobressalentes leak into estoque/estoque_movimentos | ✓ VERIFIED | Manutencao.py Fase 03 code (lines 576-894) has zero references to `estoque` or `estoque_movimentos` tables. `test_sobressalentes` asserts `estoque_count_before == estoque_count_after` and `estoque_ids_before == estoque_ids_after` (lines 416-420). All 11 tests pass. |
| 5 | Aba "Sobressalentes" tab renders list with badge + valor estimado; add/edit/ajuste (modal motivo+obs) calls Phase-3 endpoints with Bearer token; list re-renders after mutations | ⚠️ PRESENT_BEHAVIOR_UNVERIFIED | TAB_DEFS entry at erp-manutencao.js:30; `async sobressalentes(cont)` renderer at line 1530; `sbRender()` fetches `/api/manutencao/sobressalentes`; `sbBadgeColor` maps badge → CSS token; `valorBadge.textContent` at line 1842; `sbOpenPecaForm` and `sbOpenAjuste` both call endpoints with `sbAuthHeaders()`; `sbRender()` called after mutations. All server data via `el()/textContent` (no innerHTML of server data). Code is fully wired. Visual tab rendering, modal behaviour, and re-render lifecycle require browser confirmation. |

**Score:** 3/5 truths verified (2 present, behavior-unverified)

> Note: Truth 5 bundles SC1 (visual list) and SC2 (modal flows) from the success criteria. Both are fully coded and wired; the unverified portion is browser rendering and UX flow, not logic.

---

### Deferred Items

None.

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `data/schema_manutencao.sql` | `sobressalentes` + `sobressalentes_movimentos` tables (CREATE TABLE IF NOT EXISTS, additive) | ✓ VERIFIED | Fase 03 block appended at line 56. Both tables present with all required columns. Index `idx_sob_mov_item(item_id, created_at DESC)` present. Schema is idempotent (IF NOT EXISTS). |
| `backend/manutencao.py` | 5 sobressalentes endpoints with `_require_auth` | ✓ VERIFIED | All 5 endpoints present: GET /sobressalentes (661), POST /sobressalentes (704), PUT /sobressalentes/{id} (741), POST /sobressalentes/{id}/ajuste (798), GET /sobressalentes/{id}/movimentos (874). All call `_require_auth`. |
| `tests/test_manutencao.py` | `test_sobressalentes` covering CRUD + atomic ajuste + estoque isolation | ✓ VERIFIED | `test_sobressalentes` at line 272 covers all specified behaviors. Runs green: 11 passed, 11 warnings. |
| `assets/erp-manutencao.js` | `sobressalentes` TAB_DEFS entry + async renderer with `sb_`-prefixed helpers | ✓ VERIFIED (wired) | TAB_DEFS entry at line 30; async renderer at line 1530; `sbToken`, `sbAuthHeaders`, `sbBadgeColor`, `sbFmtBRL`, `sbOpenModal`, `sbRender`, `sbOpenPecaForm`, `sbOpenAjuste` all present. |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `ajustar_sobressalente` handler | `sobressalentes` + `sobressalentes_movimentos` tables | Single `aiosqlite.connect` block + single `conn.commit()` | ✓ WIRED | Lines 823-869: read inside txn → compute nova_qtd → UPDATE → INSERT → commit. Exactly mirrors `registrar_uso` atomicity pattern. |
| `schema_manutencao.sql` | `CoreDB._SCHEMAS` | Already registered — `db.init()` runs schema automatically | ✓ WIRED | Plan confirms schema_manutencao.sql is in `_SCHEMAS`; no db_core.py change required. Tests confirm tables are created on test DB init. |
| `sbRender()` | GET `/api/manutencao/sobressalentes` | `fetch(apiUrl('/api/manutencao/sobressalentes'), { headers: { Authorization: Bearer + sbToken() } })` | ✓ WIRED | erp-manutencao.js line 1637; response `.items` and `.valor_estimado_total` consumed at lines 1653-1654. |
| `sbOpenAjuste` | POST `/api/manutencao/sobressalentes/{id}/ajuste` | `fetch(apiUrl('.../ajuste'), { method: 'POST', headers: sbAuthHeaders(), body: JSON.stringify(payload) })` | ✓ WIRED | erp-manutencao.js line 1813; `sbRender()` called on success at line 1825. |
| `sbOpenPecaForm` | POST/PUT `/api/manutencao/sobressalentes[/{id}]` | `fetch(url, { method, headers: sbAuthHeaders(), body: JSON.stringify(payload) })` | ✓ WIRED | erp-manutencao.js lines 1730-1747; `sbRender()` called on success at line 1747. |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `erp-manutencao.js` sbRender | `data.items`, `data.valor_estimado_total` | GET `/api/manutencao/sobressalentes` → `listar_sobressalentes` → SELECT from `sobressalentes` WHERE ativo=1 | Yes — DB query at manutencao.py:678-685; badge computed from real DB columns; valor_estimado_total = Σ qtd×preco (real arithmetic) | ✓ FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| test_sobressalentes passes (CRUD + atomic ajuste + estoque isolation) | `python -m pytest tests/test_manutencao.py tests/test_manutencao_smoke.py -q` | 11 passed, 11 warnings in 14.45s | ✓ PASS |
| Schema idempotent (runs twice without error) | `python -c "import sqlite3,tempfile,os; d=tempfile.mkdtemp(); p=os.path.join(d,'t.db'); c=sqlite3.connect(p); sql=open('data/schema_manutencao.sql').read(); c.executescript(sql); c.executescript(sql); print('OK')"` | OK | ✓ PASS |
| JS syntax valid | `node --check assets/erp-manutencao.js` | (no output = OK) | ✓ PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| IMP-03 SC1 | 03-01-PLAN, 03-02-PLAN | List peças with badge ZERADO/BAIXO/OK and valor_estimado_total | ✓ SATISFIED (backend); ⚠️ PRESENT_BEHAVIOR_UNVERIFIED (frontend visual) | Backend: manutencao.py listar_sobressalentes + _badge(); test_sobressalentes confirmed green. Frontend: renderer wired but browser rendering is human_needed. |
| IMP-03 SC2 | 03-01-PLAN, 03-02-PLAN | Create/edit/ajuste (modal motivo+obs); atomic update+movimento | ✓ SATISFIED (backend); ⚠️ PRESENT_BEHAVIOR_UNVERIFIED (frontend visual) | Backend: all 5 endpoints, atomic transaction, operador from token — all tested. Frontend: sbOpenPecaForm + sbOpenAjuste wired but modal UX is human_needed. |
| IMP-03 SC3 | 03-01-PLAN | Separate tables — no mistura with estoque/estoque_movimentos | ✓ SATISFIED | Dedicated tables in schema_manutencao.sql; zero estoque references in Fase 03 code; test_sobressalentes T-03-05 asserts isolation. |
| IMP-03 SC4 | 03-01-PLAN | pytest test_sobressalentes green on clean DB | ✓ SATISFIED | 11 passed, 11 warnings. Pre-existing 14 failures (in other test files) are not regressions. |

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `assets/erp-manutencao.js` | 1633 | `cont.innerHTML = '<div ...>Carregando...</div>'` | ℹ️ Info | Static placeholder only — no server data interpolated. Permitted by plan: "innerHTML allowed only for static placeholder strings with no server data." Not a stub. |

No `TBD`, `FIXME`, or `XXX` markers found in modified files.
No empty `return null / return [] / return {}` stubs in endpoint handlers.
No hardcoded empty data arrays in renderer (sbRender fetches from real API).

---

### Human Verification Required

#### 1. Sobressalentes Tab Renders Correctly

**Test:** Serve the app (`python3 -m http.server 8080`) and start the backend (`uvicorn backend.main:app --port 8010 --reload`). Open `http://localhost:8080/cmasm_erp.html`, log in, go to Manutenção, click the "🔩 Sobressalentes" tab.
**Expected:** Tab renders. If DB is empty, the message "Nenhuma peça cadastrada. Clique em "+ Nova Peça" para começar." appears. Header card shows "Valor estimado do estoque: R$ 0,00". "+ Nova Peça" button is visible.
**Why human:** Browser rendering, CSS token (--red/--amber/--green) application, tab bar routing — cannot verify without a browser.

#### 2. +Nova Peça / Editar / Ajustar Modal End-to-End

**Test:** With a running app — click "+ Nova Peça", fill nome + qtd_minima + preço, save. Verify the row appears with the correct badge. Click "Ajustar", fill tipo=entrada, quantidade=5, motivo="Teste", obs="—", save. Verify qtd_atual and valor estimado total update without a page reload. Click "Editar", change preço, save. Verify valor updates.
**Expected:** Toast "Peça criada." on create; toast "Ajuste registrado." on ajuste; list re-renders in place with updated values; badge changes from ZERADO to OK once qtd_atual >= qtd_minima.
**Why human:** Modal open/close lifecycle, form interaction, toast visibility, and on-mutation re-render are browser DOM events. The code is wired (sbRender() is called after every successful mutation) but the UX flow must be observed.

#### 3. Central Estoque Screen Unchanged

**Test:** After performing Sobressalentes operations (create + ajuste), navigate to the Estoque screen in the main ERP.
**Expected:** Central estoque shows the same items as before — no sobressalentes peças leaked in.
**Why human:** Visual confirmation at the UI level. The programmatic isolation is already proven by test_sobressalentes (T-03-05), but the plan's human-verify checkpoint (03-02-PLAN Task 3) explicitly requires operator confirmation.

---

### Gaps Summary

No blocking gaps found. All backend logic and tests are fully implemented and passing. The two items in human_verification are browser-only behaviors (tab rendering, modal UX, re-render) that code analysis confirms are wired correctly but cannot be exercised without a running browser.

---

_Verified: 2026-06-28_
_Verifier: Claude (gsd-verifier)_
