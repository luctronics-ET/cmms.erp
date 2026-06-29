---
phase: 03-estoque-sobressalentes
reviewed: 2026-06-28T22:30:00-03:00
depth: standard
files_reviewed: 4
files_reviewed_list:
  - data/schema_manutencao.sql
  - backend/manutencao.py
  - tests/test_manutencao.py
  - assets/erp-manutencao.js
findings:
  critical: 0
  warning: 2
  info: 1
  total: 3
status: findings
---

# Phase 03: Code Review Report — Estoque Sobressalentes

**Reviewed:** 2026-06-28T22:30:00-03:00
**Depth:** standard
**Files Reviewed:** 4
**Status:** findings

## Summary

Phase 3 implements a complete sobressalentes (spare parts) inventory slice: schema, five FastAPI
endpoints, one integration test, and a frontend tab. The core requirements are met: SQL is fully
parameterized, the ajuste transaction is genuinely atomic (single `aiosqlite.connect` block + single
`commit`), `operador` is always derived from the token, and the sobressalentes tables are isolated
from `estoque`/`estoque_movimentos`. Auth is present on all five endpoints. DOM construction in the
frontend uses `el()` / `textContent` throughout — no server data reaches `innerHTML`.

Two warnings were found. Both are in the backend and relate to missing input validation. No critical
security issues, no XSS, no SQL injection.

---

## Warnings

### WR-01: `AjusteIn.quantidade` has no positivity constraint — negative values corrupt the audit trail

**File:** `backend/manutencao.py:634`

**Issue:** `quantidade: float` accepts any float, including negative values. The endpoint docstring
states "entrada — adiciona quantidade" and "saida — subtrai quantidade", but these semantics break
when `quantidade` is negative:

- `tipo="entrada", quantidade=-5` on a stock of 10 → `nova_qtd = 5`, recorded as `tipo="entrada",
  quantidade=-5.0`. The movement log shows an "entrada" that reduced stock — a corrupted audit trail.
- `tipo="saida", quantidade=-3` → `nova_qtd = qtd_anterior + 3` — a "saida" that increases stock,
  same problem.

The `nova_qtd < 0` guard only fires if the result goes negative, so many negative-quantity calls
silently succeed and persist misleading movement records.

The frontend validates `quantidade > 0` at line 1803, but this is a UI-only constraint that any
direct API call bypasses.

Only `tipo="ajuste"` intentionally allows negative `quantidade` (bidirectional delta). The fix is a
model-level validator that enforces `quantidade > 0` for `entrada` and `saida`, or restricts all
three types to `quantidade > 0` with signed semantics left to the caller to express via type choice.

**Fix:**
```python
@field_validator("quantidade")
@classmethod
def quantidade_positiva(cls, v: float, info) -> float:
    # For "ajuste", quantity may be negative (bidirectional delta).
    # For "entrada" and "saida", quantity must be positive — sign is implied by the type.
    tipo = (info.data or {}).get("tipo")
    if tipo in ("entrada", "saida") and v <= 0:
        raise ValueError("quantidade deve ser positiva (> 0) para entrada/saida")
    return v
```

Note: Pydantic v2 validators receive `info: FieldValidationInfo`; the `tipo` field must be declared
before `quantidade` in the model for `info.data` to contain it, or use a `model_validator` instead.

---

### WR-02: `editar_sobressalente` 404 check and UPDATE are on different connections — silent no-op on concurrent soft-delete

**File:** `backend/manutencao.py:756-793`

**Issue:** The existence check (`db.fetch_one` at line 757) opens and closes its own `aiosqlite`
connection via the CoreDB singleton. The UPDATE at line 788 opens a second, independent connection.
Between these two operations a concurrent request could soft-delete the row (`ativo=0`). The UPDATE
then silently executes on 0 rows (SQLite does not error on zero-affected updates) and returns
`{"ok": True}` — a false success.

In this deployment concurrency is low, but the endpoint's own docstring says "404 se não encontrado"
and the contract is violated when soft-delete races the edit.

**Fix:** Move the existence check inside the same `aiosqlite.connect` block as the UPDATE, then
check `cursor.rowcount` after the UPDATE:

```python
db_path = _db().db_path
async with aiosqlite.connect(db_path) as conn:
    # Check existence AND update in the same connection (no TOCTOU gap)
    cur = await conn.execute(
        f"UPDATE sobressalentes SET {set_clause} WHERE id = ? AND ativo = 1",
        values,
    )
    if cur.rowcount == 0:
        raise HTTPException(404, "Peça não encontrada")
    await conn.commit()
```

This eliminates the separate `fetch_one` call and the gap entirely.

---

## Info

### IN-01: `GET /sobressalentes/{item_id}/movimentos` returns empty list for non-existent items instead of 404

**File:** `backend/manutencao.py:874-894`

**Issue:** The movimentos endpoint queries `sobressalentes_movimentos WHERE item_id = ?` without
first verifying that `item_id` references an active row in `sobressalentes`. A caller querying
movements for a deleted or non-existent item gets `[]` (HTTP 200) rather than a 404. This is
inconsistent with the other endpoints in this router.

**Fix:** Add a pre-check (can reuse the singleton since no write is involved):
```python
row = await _db().fetch_one(
    "SELECT id FROM sobressalentes WHERE id = ? AND ativo = 1", (item_id,)
)
if not row:
    raise HTTPException(404, "Peça não encontrada")
```

---

_Reviewed: 2026-06-28T22:30:00-03:00_
_Reviewer: Claude (adversarial review — Phase 03)_
_Depth: standard_
