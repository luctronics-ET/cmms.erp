---
phase: 03-estoque-sobressalentes
plan: "02"
subsystem: frontend
tags: [sobressalentes, manutencao, frontend, vanilla-js, safe-dom]
requirements: [IMP-03]
status: complete

dependency_graph:
  requires:
    - "03-01: /api/manutencao/sobressalentes* endpoints (backend/manutencao.py)"
  provides:
    - "Sobressalentes tab in Manutenção module (erp-manutencao.js)"
  affects:
    - assets/erp-manutencao.js

tech_stack:
  added: []
  patterns:
    - sb_-prefixed local helpers (mirrors ru_ pattern from Phase 1)
    - async renderer via RENDERERS object (RENDERERS-driven, no HTML scaffolding change)
    - sbOpenModal overlay helper reusable for both create/edit form and ajuste modal
    - all server data via el()/textContent (safe DOM — no innerHTML of server data)
    - sbBadgeColor mapping ZERADO→red / BAIXO→amber / OK→green CSS tokens
    - on-mutation re-render: sbRender() called after every successful POST/PUT

key_files:
  modified:
    - assets/erp-manutencao.js

decisions:
  - "Renderer is async (async sobressalentes(cont)) matching the registrar-uso tab pattern"
  - "sbOpenModal is a local overlay helper, not a global — avoids collisions with other renderers"
  - "Tasks 1 and 2 committed together (single cohesive renderer function covering both list + forms + modal)"
  - "Task 3 (checkpoint:human-verify) deferred — agent cannot run browser; recorded in Known Stubs"

metrics:
  duration_seconds: 182
  tasks_completed: 2
  tasks_total: 3
  completed_date: "2026-06-29"
---

# Phase 03 Plan 02: Sobressalentes Frontend Slice Summary

**One-liner:** Sobressalentes tab in Manutenção with ZERADO/BAIXO/OK badges, valor estimado total, +Nova Peça/Editar forms, and Ajustar modal (motivo+obs) wired to Phase-3 endpoints via Bearer token.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Sobressalentes TAB_DEFS entry + API-backed list renderer | 8876623 | assets/erp-manutencao.js |
| 2 | +Nova Peça / Editar form + Ajustar modal (motivo + obs) | 8876623 | assets/erp-manutencao.js |

## What Was Built

### TAB_DEFS entry (assets/erp-manutencao.js line ~30)

Added `{ id: 'sobressalentes', icon: '🔩', label: 'Sobressalentes' }` after the `registrar-uso` entry. Tab is automatically rendered by the existing `renderTabBar()` loop — no `cmasm_erp.html` change needed.

### Renderer (async sobressalentes(cont))

Structure mirrors `registrar-uso(cont)`:

- **sb_-prefixed helpers**: `sbToken()`, `sbAuthHeaders()`, `sbBadgeColor(badge)`, `sbFmtBRL(v)`, `sbOpenModal(...)`, `sbRender()`
- **`sbRender()`**: GETs `/api/manutencao/sobressalentes`, renders header card with `valor_estimado_total` and "+ Nova Peça" button, then a table with columns: Nome, Categoria, Qtd atual, Un, Status (badge), Preço un., Ações
- **Badge rendering**: `sbBadgeColor` maps `ZERADO` → `var(--red)`, `BAIXO` → `var(--amber)`, `OK` → `var(--green)`; pill with semi-transparent background + border
- **Safe DOM**: every server value set via `textContent` or `el()` text argument; `innerHTML` used only for the static "Carregando..." placeholder (no server data)

### sbOpenModal — local overlay helper

Renders a fixed overlay with close button, title, body builder callback, Save/Cancel buttons. Used for both form flows:

- **+ Nova Peça / Editar** (`sbOpenPecaForm(peca)`): fields nome*, codigo, categoria (select: consumivel|sobressalente|ferramenta), unidade, qtd_minima, preco_unitario, obs. POST `/api/manutencao/sobressalentes` for new, PUT `.../id` for edit.
- **Ajustar** (`sbOpenAjuste(peca)`): fields tipo (select: entrada|saida|ajuste), quantidade*, motivo*, obs. POST `.../id/ajuste` with `{tipo, quantidade, motivo, obs}`.

Both flows: client-side required-field advisory, Bearer token from `localStorage('xcmasm_token')`, backend 4xx `detail` surfaced via `toast(..., 'red')`, success calls `sbRender()` to re-render list with updated qtd/total/badge.

## Deviations from Plan

### Auto-consolidation: Tasks 1 and 2 in a single commit

Tasks 1 and 2 implement a single, deeply-coupled renderer function (`sbRender` calls `sbOpenPecaForm` and `sbOpenAjuste` which are defined in the same closure). Splitting into two separate commits would require an intermediate state with broken references. Both tasks were implemented and committed together as `8876623`. All verification checks for both tasks pass.

## Automated Verification Results

```
node --check assets/erp-manutencao.js → JS syntax OK
node -e "..." (inline checks):
  - TAB_DEFS entry present: OK
  - renderer present: OK
  - /api/manutencao/sobressalentes fetch: OK
  - valor_estimado_total: OK
  - badge color logic: OK
  - ajuste endpoint call: OK
  - motivo field: OK
  - sbOpenAjuste: OK
  - sbOpenPecaForm: OK

python3 -m pytest tests/test_manutencao_smoke.py -q → 6 passed, 1 warning
```

## Human-Verify Checkpoint (Task 3 — Deferred, Non-blocking)

Task 3 is `type="checkpoint:human-verify"`. An automated executor cannot run the browser. The code is complete and syntactically correct. Human verification is required:

1. `cd /home/luc/DEV_ERP/cmasm.erp && python3 -m http.server 8080` + `uvicorn backend.main:app --port 8010 --reload`
2. Open ERP → log in → Manutenção → click "🔩 Sobressalentes"
3. Create a peça via "+ Nova Peça" → verify badge + valor estimado total updates
4. Click "Ajustar" → enter quantidade + motivo → verify qtd_atual + badge + total update
5. Click "Editar" → change preço → verify valor updates
6. Confirm central Estoque screen unchanged (no sobressalentes leaked in)

Resume signal: type "approved" after confirming all steps.

## Known Stubs

None — all fields are wired to live API endpoints. The list starts empty (zero peças) on a fresh DB; the user adds peças via "+ Nova Peça".

## Threat Surface Scan

No new network endpoints, auth paths, or schema changes. The frontend renderer calls the five endpoints already established in Plan 03-01 under `/api/manutencao/sobressalentes*`. All auth is Bearer token from `localStorage('xcmasm_token')` — same pattern as all other tabs. No new surface introduced.

## Self-Check

### Files created/modified
- [x] `/home/luc/DEV_ERP/cmasm.erp/assets/erp-manutencao.js` — FOUND (413 lines inserted)

### Commits exist
- [x] 8876623 — Tasks 1+2: sobressalentes renderer

## Self-Check: PASSED
