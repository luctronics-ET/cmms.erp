---
phase: 06-residuais-funcionais
fixed_at: 2026-06-29T03:30:00Z
review_path: .planning/phases/06-residuais-funcionais/06-REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 06: Code Review Fix Report

**Fixed at:** 2026-06-29T03:30:00Z
**Source review:** .planning/phases/06-residuais-funcionais/06-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 4
- Fixed: 4
- Skipped: 0

## Fixed Issues

### CR-01 + CR-02: Authorization header missing in saveFicha and gerar-OS-preventiva

**Files modified:** `assets/erp-refrigeracao.js`
**Commit:** `a3b1ade`
**Applied fix:** Both `saveFicha` (PUT /api/pmoc/refrigeracao/{id}) and the OS preventiva
handler (POST .../os-preventiva) had `headers: { 'Content-Type': 'application/json' }`.
The existing `_authHeaders()` helper (line 591) already returns `{ 'Content-Type':
'application/json', Authorization: 'Bearer <token>' }`, so both inline objects were
replaced with `_authHeaders()`. This is the same pattern used by the catalogo-servico and
materiais fetch calls immediately below in the same module.

Node syntax check: PASS (`node --check assets/erp-refrigeracao.js`).

---

### WR-01: timedelta late import moved to top-level in manutencao.py

**Files modified:** `backend/manutencao.py`
**Commit:** `d7b11d1`
**Applied fix:** Added `timedelta` to the stdlib import on line 15:
`from datetime import date, timedelta  # timedelta needed by _vencimentos_para_ativo (por_tempo branch)`.
Removed the late module-level `from datetime import timedelta  # noqa: E402` at line 1289
(previously needed because timedelta was referenced 1,274 lines before the import appeared).
No behavior change — Python's sequential module execution meant the late import was always
resolved before any function call. Static analyzers will now correctly see `timedelta` in
scope at the top of the file.

Python AST parse check: PASS.

---

### IN-01: Stale docstring corrected in manutencao_vencimentos

**Files modified:** `backend/main.py`
**Commit:** `f18e1e0`
**Applied fix:** Updated the docstring from the false claim "Disparo por tempo é omitido
(sem base de data confiável)" to accurately describe the behavior added by RES-01
(commit 7257e5b): por_tempo uses MAX(data) from manut_registros; assets with no records
emit no alert.

Python AST parse check: PASS.

---

## Sanity / Test Results

| Check | Result |
|---|---|
| `node --check assets/erp-refrigeracao.js` | PASS |
| `python -c "ast.parse(open('backend/main.py').read())"` | PASS |
| `python -c "ast.parse(open('backend/manutencao.py').read())"` | PASS |
| `python -m pytest tests/test_manutencao.py -q` (main tree) | 22 passed |

Note: pytest was run from the main working tree (not the worktree) because the worktree
lacks `data/core.db` (the live sqlite DB used by integration tests). All 22 tests passed
on main — the `sqlite3.OperationalError: no such table: pmoc_transportes` errors seen
inside the isolated worktree are a test-environment issue (no seeded DB), not caused by
these changes.

---

_Fixed: 2026-06-29T03:30:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
