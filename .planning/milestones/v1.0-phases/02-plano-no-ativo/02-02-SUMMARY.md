---
phase: 02-plano-no-ativo
plan: 02
subsystem: frontend
tags: [manutencao, plano-ativo, fetch, el-safe-dom, async-renderer, xss-prevention]
status: complete

dependency_graph:
  requires: [02-01-SUMMARY]
  provides: [renderSubManutAPI, regManut-async-POST]
  affects: [assets/erp-manutencao.js]

tech_stack:
  added: []
  patterns:
    - async renderer with el()/textContent (no innerHTML of server data)
    - closure-scoped _mnRespEl for form state without global getElementById
    - _mn- prefix for all IDs/classes (no collision with _mc-/_md- legacy prefixes)
    - renderSub() early-return branch pattern for async sub-tabs

key_files:
  created: []
  modified:
    - assets/erp-manutencao.js

decisions:
  - renderSubManutAPI() is the sole renderer for the manut tab; subManut() left as no-op for reference
  - SUBS['manut'] key removed to prevent any stale synchronous path reaching the tab
  - _mnRespEl stored on window._manutD bridge (closure scope) to avoid getElementById with fixed IDs
  - regManut() calls renderSubManutAPI() directly on success (no full page reload)
  - operador never sent in POST body (backend derives from Bearer token per T-02-08)

metrics:
  duration: ~3 minutes
  completed: 2026-06-29
  tasks_completed: 2
  tasks_total: 3
  files_changed: 1

requirements: [IMP-02]
---

# Phase 02 Plan 02: Plano no Ativo — Frontend Vertical Slice Summary

**One-liner:** Async manut sub-tab renderer using el()/textContent fetches GET /api/manutencao/plano-ativo and renders per-item checkboxes, status badges (VENCIDA/URGENTE/PROXIMA/EM_DIA), progress bars and "faltam X h"; regManut POSTs to /api/manutencao/registro with Bearer token and reloads the checklist on success.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | API-back the Manutenção sub-tab renderer | 67377b5 | assets/erp-manutencao.js |
| 2 | Replace regManut with async POST + reload | 67377b5 | assets/erp-manutencao.js |

(Tasks 1 and 2 committed atomically — regManut calls renderSubManutAPI, making them inseparable.)

## Artifacts Produced

### assets/erp-manutencao.js

**`renderSubManutAPI(body, ativo)` (new async function inside `openAtivoDrawer`)**
- Immediately shows `'Carregando plano...'` via `el()`.
- Fetches `GET /api/manutencao/plano-ativo?ativo_id=` with `Authorization: Bearer` token.
- On error: `body.replaceChildren(el())` with error message via `.textContent` (never `innerHTML`).
- On empty `itens`: shows `'Sem plano de manutenção para o tipo deste ativo.'` via `.textContent`.
- On success: builds checklist with `el()` + `.textContent` for all server-supplied text fields (`servico_nome`, detail line).
- Per-item: checkbox (`id='_mn-{item_id}'`, `class='_mn-cb'`, `value=String(item_id)`), progress bar, `detalheEl.textContent`, status badge via `window.engine.badge(statusLabel, kind)`.
- Status → badge kind: `VENCIDA→danger`, `URGENTE→warn`, `PROXIMA→proximo`, `EM_DIA→ok`.
- Appends responsável select (`id='_mn-resp'`) + Registrar button below the list.
- Stores the select element in `window._manutD._mnRespEl` for closure access by `regManut`.

**`renderSub()` (modified)**
- Added explicit early-return branch: `if (activeSub === 'manut') { renderSubManutAPI(subBody, ativo); return; }`
- The synchronous `subBody.innerHTML = SUBS[activeSub]?.()` line now only runs for the other tabs.

**`SUBS` map (modified)**
- Removed `manut` key — `SUBS = { status, uso, hist, comb }` only.
- No double-render possible; no stale `subManut()` handler reachable.

**`subManut()` (modified)**
- Left as a no-op `return ''` for reference; no longer wired to any tab.

**`window._manutD.regManut` (replaced with async handler)**
- Reads checked items: `[...subBody.querySelectorAll('._mn-cb:checked')].map(cb => parseInt(cb.value, 10))`.
- Reads responsável from `window._manutD._mnRespEl.value` (closure-scoped select element).
- Client-side validation: amber toast if no items or no responsável.
- POSTs `{ ativo_id, responsavel, itens }` — operador NOT in body (T-02-08).
- On success: green toast + calls `renderSubManutAPI(subBody, ativo)` to reload the checklist.
- On HTTP error: red toast with `e.detail` or HTTP status.
- On network error: red toast with error message.

## Deviations from Plan

### Tasks 1 and 2: Committed in a single atomic commit (minor)

**Found during:** Implementation
**Issue:** `regManut` calls `renderSubManutAPI` on success. A commit of Task 1 alone (with the new `renderSubManutAPI` but old `regManut`) would leave `regManut` referencing a yet-to-exist function. Committing them separately would create a transient state where the old `regManut` writes to localStorage while the new renderer is active.
**Fix:** Both tasks committed atomically in commit `67377b5`.
**Rule:** Rule 1 (preventing a broken intermediate state).

### Legacy `subManut()` kept as no-op (minor)

**Found during:** Task 1 implementation
**Issue:** The plan said "leave the function unused or delete only its SUBS wiring." Other code paths (e.g., future search) might reference `subManut` by name. Deleting it wholesale risks a `ReferenceError` at runtime if anything calls it.
**Fix:** Replaced body with `return '';` (no-op) + explanatory comment. The SUBS wiring is the only thing that drove the tab — that was removed. The function body itself is harmless.
**Rule:** Rule 2 (preventing an unexpected ReferenceError).

## Sanity Results

```
node --check assets/erp-manutencao.js  → NODE SYNTAX OK
python3 -m pytest tests/test_manutencao_smoke.py -x -q  → 6 passed, 1 warning
grep plano-ativo                        → OK
grep _mn-cb                             → OK
grep renderSubManutAPI                  → OK
grep activeSub==='manut'               → OK
grep api/manutencao/registro            → OK
No innerHTML in renderSubManutAPI region → OK
operador not in POST body               → OK
```

## Deferred Human Verification (Task 3 — checkpoint:human-verify)

Task 3 is a browser-only visual verification that cannot be automated. The following steps are deferred for the developer to run manually:

1. Start backend: `uvicorn backend.main:app --port 8010 --reload` (seed if needed: `python tools/seed_ativos.py`)
2. Open http://localhost:8010 and log in.
3. Go to Manutenção, open an ativo whose tipo has a catalogo plano (e.g. a climatização AC_SPLIT). Click the 🔧 Manutenção sub-tab.
4. Confirm: plan items load from the server (not the old mock), each with a checkbox, a status badge, a progress bar, and a 'faltam X h' line.
5. Check one or more items, pick a responsável, click 'Registrar Manutenção'. Confirm the green toast and that the list reloads — a just-executed item's status moves away from VENCIDA toward EM_DIA, and 'faltam X' increases.
6. Re-open the same ativo: the updated statuses persist (state came from the DB, not localStorage).
7. Negative check: open an ativo whose tipo has no plano — confirm the empty-state message appears instead of an error.

**Status:** Not yet executed (requires running browser). No code changes needed; this is a pure visual/functional check.

## Threat Model Coverage

All T-02-XX mitigations for the frontend slice:
- T-02-07 (XSS via innerHTML): All server text (`servico_nome`, detail line, error messages, empty-state) inserted via `.textContent` or `el()` string children — verified by automated grep of renderSubManutAPI region.
- T-02-08 (operador spoofing): `operador` is not in the POST body; backend derives it from the Bearer token. Verified by grep of the `JSON.stringify(...)` call.
- T-02-09 (token exposure): Bearer token sent over same-origin channel, consistent with existing registrar-uso tab — no new exposure.
- T-02-SC: No new packages; vanilla JS, no build step.

## Known Stubs

**Responsável selector: static list** — The select is populated with a hardcoded list (Luciano Ferreira, Carlos Silva, João Mendes, Pedro Santos, Maria Oliveira). This is intentional per RESEARCH.md Open Question 1: "keep static for now; wire to /api/usuarios in Phase 4 (Equipe Técnica)." The stub does not prevent the plan's goal (registration works with any selected name). Phase 4 will replace this with a dynamic fetch.

## Threat Flags

None — no new network endpoints, auth paths, or schema changes beyond the plan's declared scope. The new fetch calls hit endpoints declared in Plan 02-01.

## Self-Check: PASSED

- `assets/erp-manutencao.js`: contains `renderSubManutAPI`, `_mn-cb`, `plano-ativo`, `api/manutencao/registro`, `activeSub === 'manut'` branch.
- Commit `67377b5` present in git log.
- 6/6 smoke tests pass.
- Node syntax check passes.
- No innerHTML of server data in `renderSubManutAPI` region (automated grep confirmed).
