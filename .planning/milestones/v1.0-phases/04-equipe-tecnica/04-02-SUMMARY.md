---
phase: 04-equipe-tecnica
plan: "02"
subsystem: assets/erp-manutencao.js
tags: [equipe-tecnica, roster, capacity, crud, soft-delete, frontend, vanilla-js, IMP-04]
dependency_graph:
  requires: [backend/manutencao.py equipe endpoints (04-01), assets/erp-manutencao.js TAB_DEFS+RENDERERS]
  provides: [Equipe Técnica tab UI, roster CRUD, soft-deactivate, capacity config panel]
  affects: [Phase 5 cronograma (consumes equipe_config via UI)]
tech_stack:
  added: []
  patterns: [vanilla JS renderer, el()/textContent XSS-safe DOM, Bearer token fetch, modal overlay pattern, Promise.all parallel fetch]
key_files:
  created: []
  modified:
    - assets/erp-manutencao.js
decisions:
  - Capacity display reads h_dia_total/h_semana/h_ano directly from PUT /equipe/config response — frontend never recomputes (T-04-08 accept)
  - Soft-deactivate via PUT {ativo:0} matching Wave-1 backend; no DELETE call (T-04-05)
  - All member-supplied text (nome, posto_grad, especialidade) rendered via textContent exclusively (T-04-06 mitigate)
  - Task 1 and Task 2 committed together as one atomic feat commit since the renderer is a single function
  - Task 3 (human-verify) deferred as non-blocking per plan constraints
metrics:
  duration: "~3 minutes"
  completed: "2026-06-29"
  tasks_completed: 2
  tasks_total: 3
  files_changed: 1
status: complete
---

# Phase 04 Plan 02: Equipe Técnica Frontend Summary

**One-liner:** Equipe Técnica tab with roster CRUD (add/edit/soft-deactivate) and capacity-config panel showing backend-recomputed h/dia, h/semana, h/ano on save.

## What Was Built

Frontend vertical slice for IMP-04 (Equipe Técnica), completing the end-to-end:

1. **TAB_DEFS entry** (`assets/erp-manutencao.js` ~line 31):
   ```js
   { id: 'equipe-tecnica', icon: '👥', label: 'Equipe Técnica' }
   ```
   Added after `sobressalentes`. `renderActiveTab()` dispatches via `RENDERERS[id]` automatically — no other file needed to change.

2. **RENDERERS['equipe-tecnica'] async renderer** — two stacked sections:

   **Roster section:**
   - `GET /api/manutencao/equipe/membros` → table with columns: Nome, Posto/Grad, Especialidade, Status badge (Ativo=green / Inativo=red), Ações (Editar | Desativar).
   - All member-supplied strings rendered via `textContent` only (XSS safe, T-04-06).
   - **+ Membro** button → modal overlay (mirrors `sbOpenModal` pattern): inputs nome*, posto_grad, especialidade, tem_login checkbox, usuario_mat → `POST /api/manutencao/equipe/membros`.
   - **Editar** per row → same modal pre-filled → `PUT /api/manutencao/equipe/membros/{id}`.
   - **Desativar** per row → `confirm()` → `PUT /api/manutencao/equipe/membros/{id}` `{ativo: 0}` (soft-delete, never DELETE).
   - On success: `eqRender()` re-fetches and rebuilds the entire tab.

   **Config section:**
   - `GET /api/manutencao/equipe/config` fetched in parallel with roster (`Promise.all`).
   - Controls: `num_equipes` number input, 7 weekday checkboxes (seg–dom tokens), dynamic turnos list (nome text + horas number per row, add/remove).
   - **Salvar configuração** → `PUT /api/manutencao/equipe/config` with `{num_equipes, dias_semana, turnos}` → on success reads `response.capacidade.h_dia_total`, `.h_semana`, `.h_ano` and updates the capacity panel — frontend does not recompute (T-04-08 accept / single source of truth).
   - Capacity panel shows three badges: `{value} h/dia`, `{value} h/semana`, `{value} h/ano` in monospace accent color.
   - Brief success message fades after 3 s.

3. **Security (threat model)**:
   - T-04-06 (XSS): all member text via `textContent` — no `innerHTML` with user data. ✓
   - T-04-07 (Spoofing): every fetch includes `Authorization: Bearer <xcmasm_token>`. ✓
   - T-04-08 (Repudiation): capacity numbers come from backend response only. ✓

## Commits

| Hash | Type | Description |
|------|------|-------------|
| f6c3c1a | feat | Add Equipe Técnica tab — roster CRUD + capacity config panel |

## Sanity Results

```
node --check assets/erp-manutencao.js  → Syntax OK
python -m pytest tests/test_manutencao_smoke.py -q  → 6 passed, 1 warning
```

No regressions on existing tabs.

## Deviations from Plan

**1. [Task merge] Tasks 1 and 2 implemented as one commit**
- **Reason:** The renderer is a single `async 'equipe-tecnica'(cont)` function — splitting into two partial commits would have left the file in an intermediate state (renderer with roster but no config). Both tasks were implemented together in a single edit, then committed atomically.
- **Impact:** None — both verification checks pass.

## Deferred Items

**Task 3: Human verification (browser end-to-end)**

This is a `checkpoint:human-verify` gate. Per the execution constraints this is recorded as non-blocking deferred.

To verify manually:
1. `uvicorn backend.main:app --port 8010 --reload` (seed first if needed: `python tools/seed_usuarios.py`)
2. `python3 -m http.server 8080` → http://localhost:8080/cmasm_erp.html → login (mat 000001 / senha 1234)
3. Open Manutenção → "Equipe Técnica" tab — should render without console errors.
4. Click "+ Membro", add a member → appears as Ativo in roster.
5. Editar the member, then Desativar → disappears from default roster (backend: ativo=0).
6. Config panel: set num_equipes=2, keep seg–sex, two turnos of 4h → Salvar → expect 16 h/dia · 80 h/semana · 4160 h/ano.
7. Reload → config persists.

**Resume signal:** "approved" to close IMP-04.

## Known Stubs

None — all data is wired to live API endpoints (Wave-1 backend, plan 04-01).

## Threat Surface Scan

No new network surface introduced. The renderer calls only the six existing Wave-1 routes registered under `/api/manutencao` in `main.py`. No new auth paths, file access, or schema changes.

## Self-Check: PASSED

- `assets/erp-manutencao.js`: TAB_DEFS entry present, renderer present, equipe/membros fetch present, equipe/config fetch present ✓
- `node --check assets/erp-manutencao.js` → Syntax OK ✓
- `pytest tests/test_manutencao_smoke.py -q` → 6 passed ✓
- Commit f6c3c1a present ✓
