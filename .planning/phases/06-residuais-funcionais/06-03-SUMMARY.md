---
phase: 06-residuais-funcionais
plan: "03"
subsystem: frontend-erp
tags: [RES-02, RES-03, SR-prefill, ficha-local, abrirNovaSR, erp-refrigeracao]
dependency_graph:
  requires:
    - "06-01 (backend: ordens_servico.departamento, POST /api/os aceita departamento)"
    - "06-02 (backend: ativos.local_id migration in db_core, _ATIVO_EDIT whitelist, PUT /api/pmoc/refrigeracao)"
  provides:
    - "abrirNovaSR(osId, ctx) — SR modal pre-fills item+qty from service context"
    - "Ficha de refrigeracao exposes editable local_id select for all assets (incl. refri171)"
  affects:
    - "cmasm_erp.html (SR workflow, openModal modal-nova-sr)"
    - "assets/erp-refrigeracao.js (openFicha, saveFicha)"
tech_stack:
  added: []
  patterns:
    - "_srPrefill module-level context (mirrors _osPrefill pattern)"
    - "fetch /api/locais at ficha-open time (no pre-load; locais not cached in erp-refrigeracao state)"
key_files:
  created: []
  modified:
    - "cmasm_erp.html"
    - "assets/erp-refrigeracao.js"
decisions:
  - "ativoId in SR ctx writes a non-blocking obs note (not a hidden field) — ativo association already via OS"
  - "openFicha converted from sync to Promise chain (fetch /api/locais) — no async/await for compat"
  - "local_id goes to NUMS for numeric conversion (null when empty string, not zero)"
metrics:
  duration: "4 minutes"
  completed: "2026-06-29"
  tasks_completed: 2
  tasks_deferred: 1
status: complete
---

# Phase 06 Plan 03: Frontend SR Prefill + Ficha Local Summary

**One-liner:** SR modal pre-fills stock item + qty from service context; refrigeration ficha exposes editable local selector (via PUT /api/pmoc/refrigeracao → _ATIVO_EDIT whitelist).

## Tasks Completed

| # | Name | Commit | Files |
|---|------|--------|-------|
| 1 | Extend abrirNovaSR to accept optional ctx (RES-02) | 3afe530 | cmasm_erp.html |
| 2 | Confirm refri171 / non-climatizacao local assignable via ficha (RES-03) | 378cbd6 | assets/erp-refrigeracao.js |
| 3 | Human-verify SR prefill + refri171 local assignment | DEFERRED | — |

## Task Details

### Task 1 — RES-02: abrirNovaSR ctx extension

**Changes to `cmasm_erp.html`:**

1. Added `let _srPrefill=null;` alongside `_currentOSId` (line 4197 area) — mirrors the existing `_osPrefill` pattern.

2. `abrirNovaSR(osId, ctx)` — added optional `ctx` param. When `ctx` is a non-null object, stores it in `_srPrefill` before calling `openModal`. Existing single-arg callers (lines 5011, 5131 with `'${o.id}'`) are unchanged.

3. `openModal` block for `modal-nova-sr` — after populating `sr-item-id` select, reads and clears `_srPrefill`:
   - `ctx.itemId` → pre-selects `sr-item-id` + invokes `onSRItemChange()` to update `sr-unidade`
   - `ctx.qtd` → sets `sr-qtd`
   - `ctx.ativoId` → adds `"Ref. ativo: <id>"` to `sr-obs` only when obs is empty (non-blocking)

**Regression safety:** `ctx` defaults to undefined; `_srPrefill` is set to null for all non-ctx calls so the `if(_srPrefill)` branch is skipped when opened without context.

### Task 2 — RES-03: ficha local_id select

**Changes to `assets/erp-refrigeracao.js`:**

1. `_localSelect(locais, curLocalId)` — helper that builds a `<select name="local_id">` from the `/api/locais` array, pre-selecting `curLocalId`. Safe HTML via `esc()`. Options include "— sem local —" blank.

2. `openFicha` restructured as a Promise chain: `fetch('/api/locais')` → `.then(function(locais){...})`. The ficha HTML is built inside the callback so `_localSelect` receives real locais data. The overlay DOM node is appended before the fetch so the backdrop appears immediately; event handlers are wired inside the callback after `innerHTML` is set.

3. A new `grp('Localização', _localSelect(locais, r.local_id))` section is added between "Uso / PMOC" and "Observações" groups — applies to ALL assets in the refrigeracao list, including non-climatizacao assets like `refri171`.

4. `NUMS` extended with `local_id: 1` so `saveFicha` converts the select value to `Number(v)` (or `null` for empty string) — the PUT body then carries `local_id` as an integer, passing through `_ATIVO_EDIT` whitelist → `UPDATE ativos SET local_id = ? WHERE id = ?`.

**Confirmed editable/bound:** The `name="local_id"` select is in the live `<form id="ficha-form">` captured by `new FormData(form)` in `saveFicha`. The field is not hidden, not disabled, and is included in the FormData iteration loop.

## Deferred Tasks

### Task 3 — Human-verify SR prefill + refri171 local assignment (non-blocking)

**Type:** checkpoint:human-verify  
**Status:** Deferred — requires interactive browser session

**Verification steps for a human verifier:**

```
1. cd /home/luc/DEV_ERP/cmasm.erp && python3 -m http.server 8080
   Open: http://localhost:8080/cmasm_erp.html

2. SR prefill test (RES-02):
   - Open an OS that came from a service/maintenance context
   - Click "+ SR"
   - Confirm: sr-item-id select is pre-selected, sr-qtd is filled, sr-obs has asset ref
   - Expected: modal opens with item pre-selected

3. Regression test (RES-02 no-ctx path):
   - Open a plain OS not from service context
   - Click "SR"
   - Confirm: sr-item-id shows blank "— Selecionar item —", sr-qtd = 1, sr-obs empty

4. refri171 local assignment test (RES-03):
   - Navigate to Manutenção → Refrigeração → Inventário
   - Click on asset refri171 (ELETRONICA/BIBLIOTECA)
   - Confirm: ficha overlay shows "Localização" group with a local select
   - Select a local and save
   - Close ficha, reopen — confirm selected local persists
   (requires backend running: uvicorn backend.main:app --port 8010 --reload)

Resume signal: Type "approved" or describe what did not pre-fill / persist.
```

## Sanity Results

```
Task 1 automated check:
  abrirNovaSR signature: osId, ctx          OK
  _srPrefill declared                        OK
  _srPrefill applied in openModal            OK
  Single-arg callers found: 1               OK (onclick="abrirNovaSR('${o.id}')")

Task 2 automated checks:
  _localSelect helper                        OK
  name="local_id" select present             OK
  local_id in NUMS (numeric)                 OK
  /api/locais fetch in openFicha             OK
  Localização group in ficha                 OK

Smoke tests (test_manutencao_smoke.py):
  6 passed, 1 warning in 0.28s              PASS
```

## Deviations from Plan

None - plan executed exactly as written.

The plan noted "confirm the ficha edit actually has a bound input/select for local_id (not just the string appearing somewhere)" — confirmed: the `<select name="local_id">` is inside `<form id="ficha-form">` and captured by `new FormData(form)` in `saveFicha`.

## Threat Surface Scan

No new network endpoints added. The `PUT /api/pmoc/refrigeracao/{id}` endpoint already existed and is already guarded by `_require_auth` + `_require_escrita`. The `local_id` field was already in `_ATIVO_EDIT` whitelist. No new threat surface introduced.

## Known Stubs

None. Both features wire to real data sources:
- SR prefill: reads from `getEstoque()` (localStorage) — same source as the existing unprefilled flow
- Ficha local: reads from `/api/locais` (backend) — same API used by the Edificações page

## Self-Check: PASSED

- `/home/luc/DEV_ERP/cmasm.erp/cmasm_erp.html` — modified, committed at 3afe530
- `/home/luc/DEV_ERP/cmasm.erp/assets/erp-refrigeracao.js` — modified, committed at 378cbd6
- Both commits present in git log
- Smoke tests: 6 passed
