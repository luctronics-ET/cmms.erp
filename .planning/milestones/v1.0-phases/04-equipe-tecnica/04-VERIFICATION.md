---
phase: 04-equipe-tecnica
verified: 2026-06-28T18:00:00Z
status: passed
score: 4/5 must-haves verified
behavior_unverified: 1
overrides_applied: 0
behavior_unverified_items:
  - truth: "Tab 'Equipe Tecnica' renders roster and config panel correctly in the browser; CRUD, soft-deactivate, config-save, capacity display, and persistence-across-reload work end-to-end"
    test: "Start backend + static server, log in, open Manutencao -> Equipe Tecnica, exercise roster CRUD and config panel"
    expected: "Tab renders without console errors; roster shows members with status badges; soft-deactivate removes member from default list; config save shows 16 h/dia, 80 h/semana, 4160 h/ano for 2 equipes/4h+4h; config persists across reload"
    why_human: "Browser DOM rendering, modal overlays, and visual state transitions cannot be verified by grep or test runner; Task 3 of plan 04-02 is explicitly a checkpoint:human-verify gate"
human_verification:
  - test: "Open Manutencao -> Equipe Tecnica tab end-to-end"
    expected: |
      1. Tab renders without console errors.
      2. Click '+ Membro', add a member (nome + posto/grad + especialidade) -> appears in roster as Ativo (green badge).
      3. Editar the member -> changes reflected; Desativar -> disappears from default list.
      4. Config panel: set num_equipes=2, keep seg-sex, two turnos of 4h, click 'Salvar configuracao' -> shows exactly 16 h/dia, 80 h/semana, 4160 h/ano.
      5. Reload page -> config persists (still 2 equipes / 4h+4h / same capacity numbers).
    why_human: "Visual rendering, modal behavior, and browser state cannot be verified programmatically"
---

# Phase 04: Equipe Tecnica Verification Report

**Phase Goal:** IMP-04 — Equipe Tecnica tab: roster of members (nome, posto/grad, especialidade, status) with CRUD + soft-deactivate; capacity config (num_equipes, dias, turnos) saved to singleton equipe_config with backend-derived capacity summary; test_equipe_tecnica green.
**Verified:** 2026-06-28
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Roster endpoints (GET/POST/PUT /equipe/membros) are implemented with auth and soft-delete | VERIFIED | `backend/manutencao.py` lines 1064-1172; `_require_auth` on all three; `ativo=0` PUT path confirmed; no DELETE route; test_equipe_tecnica sub-scenarios 1-4 pass |
| 2 | GET/PUT /equipe/config returns singleton + derived capacity; `_capacidade()` reproduces legacy formula exactly | VERIFIED | `_capacidade()` at line 1017; exact formula confirmed; GET reads defaults when table empty; PUT does INSERT OR REPLACE id=1; test sub-scenarios 5-7 assert exact integers h_dia_equipe=4/8, h_dia_total=4/16, h_semana=20/80, h_ano=1040/4160 |
| 3 | pytest test_equipe_tecnica passes with exact capacity assertions; no new failures vs baseline | VERIFIED | `python -m pytest tests/test_manutencao.py tests/test_manutencao_smoke.py -q` -> **12 passed, 13 warnings** (was 6 before plan 01; +1 new test; smoke suite unchanged at 6); zero regressions |
| 4 | Schema equipe_membros + equipe_config are additive (CREATE TABLE IF NOT EXISTS), idempotent, with all required columns | VERIFIED | `data/schema_manutencao.sql` lines 96-130 confirmed; idempotency check run: `schema OK + idempotent`; columns match plan spec exactly |
| 5 | "Equipe Tecnica" tab renders roster CRUD and config panel in the browser with Bearer auth and textContent-safe DOM | PRESENT_BEHAVIOR_UNVERIFIED | `assets/erp-manutencao.js`: TAB_DEFS entry at line 31 confirmed; async `'equipe-tecnica'` renderer at line 1943; membros + config fetches wired; `eqAuthHeaders()` uses Bearer; 13 `.textContent` assignments, 0 `.innerHTML` in renderer; capacity read from `saved.capacidade` (not recomputed); JS syntax OK. Visual behavior not exercised by a test. |

**Score:** 4/5 truths verified (1 present, behavior-unverified)

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `data/schema_manutencao.sql` | equipe_membros + equipe_config tables, additive | VERIFIED | Both tables present at lines 105-130; CREATE TABLE IF NOT EXISTS; all required columns present; idempotency confirmed |
| `backend/manutencao.py` | equipe membros CRUD + config GET/PUT + `_capacidade()` | VERIFIED | `_capacidade` function at line 1017; 6 routes (GET/POST/PUT membros, GET/PUT config, listar); MembroIn, MembroUpdate, ConfigIn models; auth guards confirmed |
| `tests/test_manutencao.py` | test_equipe_tecnica with exact assertions | VERIFIED | Function at line 466; 7 sub-scenarios covering all plan requirements; exact integer assertions on capacity; soft-delete persistence check via `_query` |
| `assets/erp-manutencao.js` | 'equipe-tecnica' in TAB_DEFS and in RENDERERS | VERIFIED (wired, behavior unverified) | TAB_DEFS line 31; renderer line 1943; all API calls wired to Wave-1 endpoints; XSS-safe rendering confirmed |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `assets/erp-manutencao.js` renderer | `GET /api/manutencao/equipe/membros` | `fetch(apiUrl(...), { headers: eqAuthHeaders() })` in `eqRender()` | WIRED | Line 2129 |
| `assets/erp-manutencao.js` renderer | `GET /api/manutencao/equipe/config` | `Promise.all([rMembros, rConfig])` in `eqRender()` | WIRED | Line 2130 |
| `assets/erp-manutencao.js` save button | `PUT /api/manutencao/equipe/config` | `fetch(apiUrl('/api/manutencao/equipe/config'), { method: 'PUT', ... })` | WIRED | Line 2333; response `.capacidade` consumed by `eqRenderCap()` |
| `backend/manutencao.py` `_capacidade()` | equipe_config table defaults | Reads `equipe_config WHERE id=1`; falls back to `_DEFAULT_CONFIG` dict when empty | WIRED | Lines 1186-1196 |
| `backend/manutencao.py` PUT config | equipe_config singleton | `INSERT OR REPLACE INTO equipe_config (id, ...)` with id=1 hard-coded | WIRED | Lines 1223-1226 |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `erp-manutencao.js` roster table | `membros` | `GET /api/manutencao/equipe/membros` -> `SELECT * FROM equipe_membros WHERE ativo=1` | Yes — DB query confirmed at line 1084 | FLOWING |
| `erp-manutencao.js` capacity panel | `cap.h_dia_total`, `cap.h_semana`, `cap.h_ano` | `GET/PUT /equipe/config` response -> `_capacidade(config)` computed from DB row or defaults | Yes — derived from stored values, not static | FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| test_equipe_tecnica passes | `pytest tests/test_manutencao.py::test_equipe_tecnica -v` | 1 passed, 3 warnings | PASS |
| Full manutencao + smoke suite | `pytest tests/test_manutencao.py tests/test_manutencao_smoke.py -q` | 12 passed, 13 warnings | PASS |
| Schema idempotency | python idempotency script | `schema OK + idempotent` | PASS |
| JS syntax | `node --check assets/erp-manutencao.js` | Syntax OK | PASS |
| TAB_DEFS + renderer + fetches wired | node -e inline check | All checks pass | PASS |
| XSS safety (textContent) | node -e inline check | 13 `.textContent`, 0 `.innerHTML` in renderer | PASS |
| Capacity from backend response | node -e `saved.capacidade` check | `saved.capacidade` consumed, no frontend recompute | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|---------|
| IMP-04 | 04-01-PLAN.md, 04-02-PLAN.md | Equipe Tecnica: roster + config + capacity | SATISFIED | All backend endpoints, schema tables, test, and frontend tab implemented |

---

### Anti-Patterns Found

None. No TBD/FIXME/XXX/TODO markers found in any modified file. No innerHTML with user data. No empty stubs. No hardcoded empty returns from API routes.

---

### Human Verification Required

#### 1. Equipe Tecnica Tab — End-to-End Browser Verification

**Test:** Start `uvicorn backend.main:app --port 8010 --reload` (seed first if needed: `python tools/seed_usuarios.py`). Serve ERP: `python3 -m http.server 8080`. Open http://localhost:8080/cmasm_erp.html, log in (mat 000001 / senha 1234). Navigate to Manutencao -> "Equipe Tecnica" tab.

**Expected:**
1. Tab renders without console errors (tab label "Equipe Tecnica" with icon visible in tab bar).
2. Click "+ Membro", fill nome + posto/grad + especialidade, save -> member appears in roster table with green "Ativo" badge.
3. Click "Editar" on the member, change a field, save -> change reflected in roster.
4. Click "Desativar" -> confirmation prompt -> member disappears from roster (backend kept ativo=0 row).
5. Config panel shows current num_equipes, dia checkboxes pre-checked from config, turnos list.
6. Set num_equipes=2, keep seg-sex checked, set two turnos of 4h each, click "Salvar configuracao" -> capacity panel shows exactly **16 h/dia, 80 h/semana, 4160 h/ano** (backend-computed).
7. Reload the page -> config persists: still 2 equipes, same turnos, same capacity numbers.

**Why human:** Visual rendering, modal overlays, checkbox state, and browser persistence cannot be verified programmatically. Plan 04-02 Task 3 is an explicit `checkpoint:human-verify` blocking gate.

**Resume signal:** "approved" or describe any issues to fix.

---

### Gaps Summary

No technical gaps found. All backend artifacts exist, are substantive, and are wired correctly. The test passes with exact arithmetic assertions. The only open item is the planned human verification gate (Task 3 of plan 04-02), which is pending by design.

---

_Verified: 2026-06-28_
_Verifier: Claude (gsd-verifier)_
