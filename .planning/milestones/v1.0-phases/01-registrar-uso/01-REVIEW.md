---
phase: 01-registrar-uso
reviewed: 2026-06-28T23:45:00-03:00
depth: deep
files_reviewed: 7
files_reviewed_list:
  - data/schema_manutencao.sql
  - backend/manutencao.py
  - backend/db_core.py
  - backend/main.py
  - assets/erp-manutencao.js
  - tests/conftest.py
  - tests/test_migracoes_idempotencia.py
findings:
  critical: 1
  warning: 3
  info: 2
  total: 6
status: findings
---

# Phase 01: Code Review Report — Registrar Uso

**Reviewed:** 2026-06-28T23:45:00-03:00
**Depth:** deep (cross-file, call-chain tracing)
**Files Reviewed:** 7
**Status:** findings

## Summary

Reviewed the full Phase 1 slice: schema, router, main.py wiring, frontend tab, and tests.
The transaction atomicity design is sound (single `aiosqlite.connect` block, single commit).
All SQL is parameterized. Auth on the write path is correct. The idempotency test is valid.

Two issues require attention before production use: a crash-after-commit in the
`_vencimentos_para_ativo` helper when `frequencia` contains non-dict JSON, and an
XSS via `alertaDiv.innerHTML` that injects server-side service names without escaping.
Three lower-severity issues follow.

---

## Critical Issues

### CR-01: `_vencimentos_para_ativo` — `json.loads` result used outside try/except, crashes after commit

**File:** `backend/manutencao.py:107-131`

**Issue:** The `try/except` at line 107 catches only the `json.loads()` call. Lines 111–131
(the `f.get("tipo")` call and subsequent arithmetic) execute outside that guard. If
`frequencia` stores any valid JSON that is not a dict — a bare number (`"500"`), a string,
or an array — `json.loads` succeeds (no exception), `f` is not a dict, and `f.get("tipo")`
raises `AttributeError`. Similarly, if `f["valor"]` is a string instead of a number,
`iv <= 0` raises `TypeError`.

This call happens at line 192, **after `conn.commit()` has already persisted the usage
record**. The uncaught exception propagates to FastAPI and returns HTTP 500. The frontend
treats a non-2xx response as failure (line 1444–1448) and does not update the UI, while the
DB already has the new `uso_atual`. The data is saved but the client is told it failed —
a silent partial-failure.

**Fix:** Expand the try/except to cover the entire per-item block:

```python
# backend/manutencao.py — _vencimentos_para_ativo, inner loop
for it in itens:
    try:
        raw = it["frequencia"] or p.get("frequencia")
        if not raw:
            continue
        f = json.loads(raw)
        if not isinstance(f, dict):
            continue                          # guard against bare number/array
        if f.get("tipo") != "por_uso" or not f.get("valor"):
            continue
        iv = float(f["valor"])                # coerce string to float defensively
        if iv <= 0:
            continue
        prox = (math.floor(uso / iv) + 1) * iv
        falta = prox - uso
        if falta <= iv * 0.15:
            out.append({ ... })
    except Exception:
        continue                              # skip malformed item, never crash after commit
```

---

## Warnings

### WR-01: `alertaDiv.innerHTML` injects API-sourced `v.servico` without HTML escaping — XSS

**File:** `assets/erp-manutencao.js:1465-1466`

**Issue:** The vencimento alert is built with:

```js
alertaDiv.innerHTML = '<strong>Atenção — ...</strong><br>'
  + venc.map(v => `• ${v.servico} (falta ${Number(v.falta || 0).toFixed(1)} ${v.unidade || unidade})`).join('<br>');
```

`v.servico` comes from `catalogo_servicos.nome` (via `_vencimentos_para_ativo`), a free-text
field with no DB constraint on HTML characters. If any service name contains `<img
src=x onerror=alert(1)>` or similar, it executes in the user's browser when the alert is
displayed. All authenticated users who can insert/edit catalog services can trigger this.

**Fix:** Replace `innerHTML` with `textContent`-based DOM construction or a minimal escape:

```js
function ruEscape(s) {
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}
// Replace alertaDiv.innerHTML = ... with:
alertaDiv.replaceChildren(
  el('strong', {}, 'Atenção — serviços preventivos próximos do vencimento:'),
  el('br'),
  ...venc.map(v =>
    el('span', { style: { display: 'block' } },
      `• ${v.servico} (falta ${Number(v.falta || 0).toFixed(1)} ${v.unidade || unidade})`)
  ),
);
```
Since `el()` from `window.engine.utils` already uses `textContent` internally for string
children (no `innerHTML`), routing through `el()` is sufficient.

---

### WR-02: `GET /api/manutencao/uso` exposes PII (operador name/mat) without authentication

**File:** `backend/manutencao.py:202-228`

**Issue:** `listar_uso` requires no token. The `uso_registros` table stores `operador`
(a snapshot of the user's `mat` or `nome`) and timestamps of every usage event. An
unauthenticated caller on the internal network can enumerate `GET /api/manutencao/uso`
to obtain full operator identity-to-activity mappings.

The catalogo `GET` endpoints are also unauthenticated, but they expose only reference
data (service names, plan codes). `uso_registros` is an audit trail containing personnel
data — a different sensitivity class.

**Fix:** Add `authorization` parameter and call `_require_auth`:

```python
@router.get("/uso")
async def listar_uso(
    ativo_id: Optional[str] = None,
    limit: int = 20,
    authorization: str | None = Header(None),
):
    await _require_auth(authorization)
    db = _db()
    ...
```

---

### WR-03: `limit` query parameter in `GET /uso` has no lower bound — `limit=-1` dumps all rows

**File:** `backend/manutencao.py:203`

**Issue:** `limit: int = 20` accepts any integer. SQLite treats `LIMIT -1` as no limit
(returns all rows). A caller can send `?limit=-1` or `?limit=9999999` to retrieve the
entire `uso_registros` table in a single response.

**Fix:** Use FastAPI's `Query` with a minimum and maximum:

```python
from fastapi import Query

async def listar_uso(
    ativo_id: Optional[str] = None,
    limit: int = Query(default=20, ge=1, le=200),
    ...
):
```

---

## Info

### IN-01: Redundant `HTTPException` import inside `_require_auth` function body

**File:** `backend/manutencao.py:33`

**Issue:** `_require_auth` does `from fastapi import HTTPException as _HTTPException`
inside the function body. `HTTPException` is already imported at module level on line 19
and is used as plain `HTTPException` in `registrar_uso` at line 164. The alias serves
no purpose and adds per-call import overhead (negligible, but confusing).

**Fix:** Remove the inner import; use the module-level `HTTPException` directly:

```python
async def _require_auth(authorization: str | None) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Token ausente")
    ...
    if not row:
        raise HTTPException(401, "Token inválido ou expirado")
    return row
```

---

### IN-02: Unused `import sqlite3` in `test_migracoes_idempotencia.py`

**File:** `tests/test_migracoes_idempotencia.py:9`

**Issue:** `import sqlite3` is present but never referenced in the file. The tests use
`CoreDB` (aiosqlite-based) and `fresh_db.fetch_all()` for introspection.

**Fix:** Remove the unused import.

---

_Reviewed: 2026-06-28T23:45:00-03:00_
_Reviewer: Claude (gsd-code-reviewer / adversarial review)_
_Depth: deep_
