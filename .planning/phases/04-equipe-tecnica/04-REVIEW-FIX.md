---
phase: 04-equipe-tecnica
fixed_at: 2026-06-28T23:05:00-03:00
review_path: .planning/phases/04-equipe-tecnica/04-REVIEW.md
iteration: 1
findings_in_scope: 3
fixed: 3
skipped: 0
status: all_fixed
---

# Phase 04: Code Review Fix Report — Equipe Técnica

**Fixed at:** 2026-06-28T23:05:00-03:00
**Source review:** .planning/phases/04-equipe-tecnica/04-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 3
- Fixed: 3
- Skipped: 0

## Fixed Issues

### WR-01: `MembroUpdate.ativo` accepts out-of-range integers

**Files modified:** `backend/manutencao.py`
**Commit:** `ffeeca6`
**Applied fix:** Added `@field_validator("ativo")` / `ativo_valido` to `MembroUpdate` that raises `ValueError("ativo deve ser 0 (inativo) ou 1 (ativo)")` for any value outside `{0, 1}`. FastAPI converts this to HTTP 422. `MembroIn` (POST) has no `ativo` field (defaults to 1 at the DB level), so no change needed there.

---

### WR-02: `get_config` — unguarded `json.loads` crashes on corrupt DB row

**Files modified:** `backend/manutencao.py`
**Commit:** `09a52e5`
**Applied fix:** Wrapped the two `json.loads` calls in `get_config` inside a `try/except (json.JSONDecodeError, TypeError)` block that falls back to `_DEFAULT_CONFIG["dias_semana"]` and `_DEFAULT_CONFIG["turnos"]` on failure, preventing a 500 on corrupt rows. The `_capacidade` helper's own `isinstance(str)` branches are left untouched (they are dead code in the current call graph but harmless).

---

### WR-03: Frontend — no reactivation path for deactivated members

**Files modified:** `assets/erp-manutencao.js`
**Commit:** `512cf21`
**Applied fix:**
1. Added `let eqShowAll = false` state variable in the `'equipe-tecnica'` handler scope (above `eqRender`).
2. `eqRender` now builds `membrosUrl` with `?incluir_inativos=1` suffix when `eqShowAll` is true, using the exact query param the backend's `GET /equipe/membros` handler expects (`incluir_inativos: int = Query(...)`).
3. Added a checkbox "incluir inativos" (with matching `<label>`) in the roster header row, wired to toggle `eqShowAll` and call `eqRender()`.
4. Replaced the single disabled `btnDesativar` with an `if (ativo) … else …` branch: active rows get the red "Desativar" button (existing behavior, wired to `eqDesativar`); inactive rows (visible only when `eqShowAll` is true) get a green "Reativar" button that does `PUT {ativo: 1}` with Bearer token and calls `eqRender()` on success.
5. All DOM operations use `el()` / `textContent` — no `innerHTML` introduced.
6. `node --check assets/erp-manutencao.js` passed.

---

## Skipped Issues

None.

---

## Sanity / Test Results

- `python -c "import backend.manutencao"` — OK (both after WR-01 and WR-02)
- `node --check assets/erp-manutencao.js` — OK (after WR-03)
- `python -m pytest tests/test_manutencao.py -q` run from main repo: **6 passed, 13 warnings** — all green, including `test_equipe_tecnica`
- Note: running `test_equipe_tecnica` from within the isolated git worktree fails with `sqlite3.OperationalError: no such table: pmoc_transportes`. This is a **pre-existing infra issue** — `main.py`'s startup `_seed_pmoc_frota_corte_if_empty()` references a PMOC table not seeded in the test fixture DB, unrelated to these fixes. The test passes in the main repo working tree both before and after the fixes.

---

_Fixed: 2026-06-28T23:05:00-03:00_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
