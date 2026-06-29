---
phase: 08-ajuda-e-documentacao
plan: "03"
subsystem: frontend-docs
status: complete
tags: [docs, help-drawer, safe-markdown, vanilla-js, DOC-01, DOC-02, DOC-03]

dependency_graph:
  requires: [08-01]
  provides: [frontend-documentos-page, frontend-help-drawer]
  affects: [cmasm_erp.html, assets/erp-docs.js]

tech_stack:
  added: []
  patterns:
    - IIFE 'use strict' module pattern (same as erp-manutencao.js)
    - Local el() copy (pmoc-engine.js does not export el publicly)
    - renderMdSafe DOM-only markdown renderer (textContent/createTextNode, zero innerHTML of server content)
    - authFetch with Authorization: Bearer from localStorage xcmasm_token
    - FormData multipart POST for file upload (no JSON)
    - Blob URL download trick for Bearer-authenticated file downloads
    - Lazy drawer creation (DOM element built on first openAjuda() call)

key_files:
  created:
    - assets/erp-docs.js
  modified:
    - cmasm_erp.html

decisions:
  - Use docs-root inner div (not page-documentos directly) to follow manut-root pattern; avoids the outer page container being wiped
  - Copy el() inside IIFE — pmoc-engine.js confirmed not to export el via window.engine (see RESEARCH open question #2)
  - renderMdSafe called in two places: openAjuda() content render and edit-mode save re-render; both use appendChild, never innerHTML of server data
  - Download via fetch+Blob URL (not anchor href) so the Bearer header is always sent
  - Help button derives active-page chave from document.querySelector('.ni.active').dataset.page at click time — live, not stale

metrics:
  duration: ~25 minutes
  completed: 2026-06-29
  tasks_completed: 2
  tasks_total: 3
  files_changed: 2
---

# Phase 08 Plan 03: Frontend Documentos Page + Contextual Help Drawer Summary

**One-liner:** Vanilla JS IIFE module wiring a Documentos repository page (browse/upload/history/download with tipo badges) and a contextual help "?" drawer with a DOM-only safe markdown renderer — zero innerHTML of server content.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Build assets/erp-docs.js — Documentos module + help drawer + safe renderer | `094300e` | assets/erp-docs.js (created, 835 lines) |
| 2 | Wire Documentos page, help button, and script into cmasm_erp.html | `2608af2` | cmasm_erp.html (+21 lines) |

## Task 3: Checkpoint (Deferred — Non-blocking)

The plan's third task is a `type="checkpoint:human-verify"` requiring a running browser session (server + frontend). This cannot be automated by the executor. It is documented here as a deferred verification step.

**Status:** Deferred — non-blocking. The automated checks below confirm correctness at the code level.

**How to verify (human):**
1. Serve: `python3 -m http.server 8080` + `uvicorn backend.main:app --port 8010 --reload`; open `http://localhost:8080/cmasm_erp.html`, log in.
2. Click "Documentos" in sidebar — page loads with categoria/tipo filters.
3. Create a document (+ Novo documento), categoria "geral", tipo "modelo" — it appears with a colored badge.
4. Upload a small PDF → versão 1; upload again → versão 2; open Histórico → both versions with autor/data.
5. Click Baixar on v1 — downloads the v1 file (not v2).
6. Try uploading a .exe — UI surfaces the backend 4xx rejection.
7. Click "?" while on any page — drawer opens with that page's help text safely rendered (bold/lists visible, no raw markup); as a manager, click Editar, change text, Salvar — persists on reopen.
8. Log in as visualizador — create/upload/save help all return 403.

## Automated Sanity Results

```
node --check assets/erp-docs.js  → Syntax OK
node -e "verify erp-docs.js"     → OK erp-docs.js safe + wired
node -e "verify cmasm_erp.html"  → OK cmasm_erp.html wired
python -m pytest tests/test_manutencao_smoke.py -q  → 6 passed, 0 failures
```

**renderMdSafe call sites confirmed:** 3 (definition + 2 invocations — openAjuda content render + edit-mode save re-render).

**Unsafe innerHTML lines:** 0. All `.innerHTML =` assignments are empty-string clears (`container.innerHTML = ''` or `editArea.innerHTML = ''`) — explicitly allowed.

**Bearer token:** present on all authFetch calls and on the direct `fetch()` for FormData upload.

**Endpoints confirmed present:** `/api/docs/documentos`, `/api/docs/ajuda`.

## Deviations from Plan

### Auto-adjustments (Rule 2 / Rule 3)

**1. [Rule 2 - Missing mount target] Added docs-root inner div + updated mount() fallback**
- **Found during:** Task 2 implementation
- **Issue:** The plan said to populate `#page-documentos` directly, but wiping the outer `.page` container (which showPage() activates) would remove CSS activation. The sibling pages all use inner root divs (manut-root pattern).
- **Fix:** Added `<div id="docs-root">` inside `#page-documentos`; updated `mount()` to prefer `#docs-root`, fallback to `#page-documentos`. No behavior change — content is always rendered inside the page.
- **Files modified:** cmasm_erp.html, assets/erp-docs.js
- **Commit:** 2608af2

**2. [Rule 2 - Missing showPage hook] Added documentos to showPage() renders map**
- **Found during:** Task 2 wiring
- **Issue:** Without a renders entry, navigating to Documentos would only toggle the page visibility — it would never call `erpDocs.mount()` to load the documents list.
- **Fix:** Added `documentos: ()=>{ if(window.erpDocs&&window.erpDocs.mount) window.erpDocs.mount(); }` to the renders map in showPage().
- **Files modified:** cmasm_erp.html
- **Commit:** 2608af2

## Known Stubs

None. The Documentos page fetches live data from the backend endpoints. The help drawer fetches live ajuda topics. No hardcoded placeholder data flows to the UI.

## Threat Surface Scan

No new network endpoints, auth paths, or schema changes introduced — this plan is frontend-only. The erp-docs.js module:

- Enforces Bearer token on every request (T-08F-02 mitigated)
- Never assigns innerHTML of server content (T-08F-01 mitigated — confirmed 0 unsafe lines)
- Hides write controls for visitante role client-side; backend _require_escrita enforces server-side (T-08F-03 mitigated)

## Self-Check

| Check | Result |
|-------|--------|
| `assets/erp-docs.js` exists | FOUND |
| commit 094300e exists | FOUND |
| commit 2608af2 exists | FOUND |
| `data-page="documentos"` in cmasm_erp.html | FOUND |
| `id="page-documentos"` in cmasm_erp.html | FOUND |
| `erp-docs.js` script tag in cmasm_erp.html | FOUND |
| `erpDocs.openAjuda` in cmasm_erp.html | FOUND |
| renderMdSafe called (not just defined) | FOUND (3 sites) |
| Zero non-empty innerHTML assignments | PASSED |
| Smoke tests | 6/6 passed |

## Self-Check: PASSED
