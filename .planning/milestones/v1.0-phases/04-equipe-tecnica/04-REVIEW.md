---
phase: 04-equipe-tecnica
reviewed: 2026-06-28T22:55:00-03:00
depth: deep
files_reviewed: 4
files_reviewed_list:
  - data/schema_manutencao.sql
  - backend/manutencao.py
  - tests/test_manutencao.py
  - assets/erp-manutencao.js
findings:
  critical: 0
  warning: 3
  info: 0
  total: 3
status: findings
---

# Phase 04: Code Review Report — Equipe Técnica

**Reviewed:** 2026-06-28T22:55:00-03:00
**Depth:** deep (cross-file call-chain analysis)
**Files Reviewed:** 4
**Status:** issues_found

## Summary

Reviewed the four files added/modified in commits 2e2b983, bea7308, cbc4646, f6c3c1a covering the Equipe Técnica feature: schema DDL, backend CRUD + capacity helper, test suite, and frontend renderer.

The `_capacidade` formula is correct (Σhoras × num_equipes × len(dias_semana) × 52; config-only, no member multiply). SQL is fully parameterized. Auth and role checks are present on all write endpoints. Soft-delete invariant is enforced. The `el()` utility uses `document.createTextNode` for string children — no XSS path exists in the Equipe Técnica renderer. The singleton upsert (INSERT OR REPLACE id=1) is idempotent and correct.

Three issues found, all WARNING-level. No critical/security bugs.

## Warnings

### WR-01: `MembroUpdate.ativo` accepts out-of-range integers — member can become unrecoverable

**File:** `backend/manutencao.py:953`
**Issue:** `MembroUpdate.ativo` is `Optional[int]` with no `field_validator` constraining values to `{0, 1}`. A caller (or future integration) can PUT `{ativo: 2}` or `{ativo: -1}`, which writes the arbitrary value directly to the DB. The row is preserved (soft-delete invariant holds), but the member will not appear in `GET /equipe/membros` (which filters `WHERE ativo = 1`) nor in `?incluir_inativos=1` (which returns `SELECT *` with no filter). The member effectively becomes unrecoverable via normal API until the DB is edited directly. This also means `ativo` can be used as a silent "hidden" flag with no mechanism to detect it.

**Fix:**
```python
@field_validator("ativo")
@classmethod
def ativo_valido(cls, v: Optional[int]) -> Optional[int]:
    if v is not None and v not in (0, 1):
        raise ValueError("ativo deve ser 0 (inativo) ou 1 (ativo)")
    return v
```

---

### WR-02: `get_config` — `json.loads` on DB fields is unguarded; corrupt row crashes endpoint with 500

**File:** `backend/manutencao.py:1190-1191`
**Issue:** When a row exists in `equipe_config`, `get_config` calls `json.loads(config["dias_semana"])` and `json.loads(config["turnos"])` with no `try/except`. If the DB row contains invalid JSON in either column (e.g., from a direct SQL INSERT, a failed write, or schema migration artifact), the call raises `json.JSONDecodeError`, which FastAPI converts to an unhandled 500 response. The `PUT /equipe/config` path is safe (Pydantic validates before write), but `get_config` trusts whatever is in the DB.

Note: `_capacidade`'s internal `json.loads` branches (lines 1040, 1045) are dead code in the current call graph — `get_config` and `put_config` both pass Python lists into `_capacidade`, never raw strings. The unsafe lines are the two in `get_config` itself.

**Fix:**
```python
if row:
    config = dict(row)
    try:
        config["dias_semana"] = json.loads(config["dias_semana"])
        config["turnos"] = json.loads(config["turnos"])
    except (json.JSONDecodeError, TypeError):
        # Corrupt DB row — fall back to defaults rather than crashing
        config["dias_semana"] = _DEFAULT_CONFIG["dias_semana"]
        config["turnos"] = _DEFAULT_CONFIG["turnos"]
```

---

### WR-03: Frontend — no "Reativar" path; deactivated members are permanently unreachable via UI

**File:** `assets/erp-manutencao.js:2205-2220`
**Issue:** The `eqRender` function fetches only `ativo=1` members (default GET). Inactive members are not shown anywhere in the Equipe Técnica tab — neither the default roster nor via an "incluir inativos" toggle. The `eqDesativar` soft-delete path works correctly, but there is no button, modal, or view that exposes the `?incluir_inativos=1` listing or a `PUT {ativo: 1}` reactivation call. The backend fully supports reactivation (no `WHERE ativo = 1` guard on `editar_membro`), but the frontend exposes no path to it. A deactivated member requires a direct API call or DB edit to restore.

**Fix:** Add an "incluir inativos" toggle and a "Reativar" button for inactive rows. Minimal implementation:

```js
// In eqRender, add a toggle state (e.g., eqShowAll) and checkbox above the table:
const showAllCb = el('input', { type: 'checkbox', id: 'eq-show-all' });
showAllCb.addEventListener('change', () => { eqShowAll = showAllCb.checked; eqRender(); });

// Fetch roster with toggle:
fetch(apiUrl('/api/manutencao/equipe/membros' + (eqShowAll ? '?incluir_inativos=1' : '')), ...)

// For inactive rows, replace "Desativar" (disabled) with "Reativar":
if (!ativo) {
  const btnReativar = el('button', { class: 'pe-btn', ... }, 'Reativar');
  btnReativar.addEventListener('click', async () => {
    await fetch(apiUrl('/api/manutencao/equipe/membros/' + m.id), {
      method: 'PUT', headers: eqAuthHeaders(), body: JSON.stringify({ ativo: 1 }),
    });
    eqRender();
  });
}
```

---

_Reviewed: 2026-06-28T22:55:00-03:00_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_
