# Phase 1: Registrar Uso — Pattern Map

**Mapped:** 2026-06-28
**Files analyzed:** 6 (new/modified artifacts)
**Analogs found:** 6 / 6

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `backend/manutencao.py` | router/controller | request-response (CRUD + atomic write) | `backend/catalogo.py` | exact |
| `data/schema_manutencao.sql` | migration/schema | — | `data/schema_catalogo.sql` | exact |
| `backend/db_core.py` | config (add to `_SCHEMAS`) | — | `backend/db_core.py` lines 7–11 | self-referential |
| `backend/main.py` | config (add router + startup) | — | `backend/main.py` lines 20–22, 325–327, 793–811 | self-referential |
| `cmasm_erp.html` + `assets/erp-manutencao.js` | component/view (new tab) | request-response | `assets/erp-manutencao.js` TAB_DEFS + renderTabBar | exact |
| `tests/conftest.py` + `tests/test_migracoes_idempotencia.py` | test + fixture | — | `tests/conftest.py` + `tests/test_catalogo.py` | exact |

---

## Pattern Assignments

### `backend/manutencao.py` (router, request-response + atomic write)

**Analog:** `backend/catalogo.py`

**Imports pattern** (`backend/catalogo.py` lines 10–21):
```python
from __future__ import annotations

import uuid as _uuid_mod
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Header, Query
from pydantic import BaseModel, field_validator

router = APIRouter(prefix="/api/manutencao", tags=["manutencao"])

def _db():
    return sys.modules["backend.main"].db
```
Convention: `_db()` via `sys.modules["backend.main"].db` — never import `db` directly, avoids circular import.

**Auth pattern** (`backend/catalogo.py` lines 36–48):
```python
async def _require_auth(authorization: str | None) -> dict:
    from fastapi import HTTPException as _HTTPException
    if not authorization or not authorization.startswith("Bearer "):
        raise _HTTPException(401, "Token ausente")
    token = authorization[7:]
    row = await _db().fetch_one(
        "SELECT s.usuario_id, u.nome, u.role FROM sessoes s JOIN usuarios u ON u.id = s.usuario_id "
        "WHERE s.token = ? AND s.expira_em > datetime('now')",
        (token,),
    )
    if not row:
        raise _HTTPException(401, "Token inválido ou expirado")
    return row
```
Convention: copy this helper verbatim into `manutencao.py`. The returned `dict` has `usuario_id`, `nome`, `role` — use `row["nome"]` as `operador` in the INSERT.

**Core POST pattern — atomic write** (`backend/catalogo.py` lines 210–230, adapted):
`db_core.CoreDB.execute()` is a single-statement helper. For the two-statement transaction (UPDATE ativos + INSERT uso_registros), use a raw `aiosqlite.connect` block:
```python
async def _atomic_uso(db_path: str, ativo_id: str, delta: float, ...) -> dict:
    import aiosqlite
    async with aiosqlite.connect(db_path) as conn:
        conn.row_factory = aiosqlite.Row
        await conn.execute("UPDATE ativos SET uso_atual = uso_atual + ? WHERE id = ?", (delta, ativo_id))
        await conn.execute(
            "INSERT INTO uso_registros (ativo_id, delta, valor_anterior, valor_novo, data, operador, observacao, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (...),
        )
        await conn.commit()   # single commit — rollback on exception
```
Convention: access `db_path` via `_db().db_path`. Both statements in one `async with` block so failure rolls back both.

**GET list pattern** (`backend/catalogo.py` lines 122–135):
```python
@router.get("/uso")
async def list_uso(ativo_id: str | None = None, limit: int = 20):
    db = _db()
    clauses, params = [], []
    if ativo_id:
        clauses.append("ativo_id = ?"); params.append(ativo_id)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    return await db.fetch_all(
        f"SELECT * FROM uso_registros {where} ORDER BY created_at DESC LIMIT ?",
        (*params, limit),
    )
```

**Error pattern** (`backend/catalogo.py` lines 191–197):
```python
row = await db.fetch_one("SELECT id, uso_atual FROM ativos WHERE id = ? AND ativo = 1", (ativo_id,))
if not row:
    raise HTTPException(404, "Ativo não encontrado")
```
Convention: always include `detail` string (FastAPI wraps it as `{"detail": "..."}`).

**Pydantic model pattern** (`backend/catalogo.py` lines 53–72):
```python
class UsoIn(BaseModel):
    ativo_id: str
    delta: float
    data: Optional[str] = None        # ISO date; default = today in endpoint
    observacao: Optional[str] = None
```
Convention: `Optional[str] = None` for nullable fields; no `field_validator` needed here unless constraining delta > 0.

---

### `data/schema_manutencao.sql` (schema)

**Analog:** `data/schema_catalogo.sql` lines 1–31

**Header + table pattern**:
```sql
-- xCMASM · Schema de Manutenção — uso_registros (Phase 1)
-- Aditivo: usa CREATE TABLE IF NOT EXISTS. Nunca DROP.
-- Ref: Rules.md §15, CONTEXT.md Phase 1.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS uso_registros (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  ativo_id       TEXT    NOT NULL REFERENCES ativos(id),
  delta          REAL    NOT NULL,
  valor_anterior REAL    NOT NULL,
  valor_novo     REAL    NOT NULL,
  data           TEXT    NOT NULL,              -- ISO date (YYYY-MM-DD)
  operador       TEXT,                          -- nome/mat do usuário logado
  observacao     TEXT,
  created_at     TEXT    DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_uso_registros_ativo ON uso_registros(ativo_id, created_at DESC);
```
Convention: `CREATE TABLE IF NOT EXISTS` throughout; `CREATE INDEX IF NOT EXISTS`; FK declared inline; no triggers; aditivo only.

---

### `backend/db_core.py` — add to `_SCHEMAS` (lines 7–11)

**Existing pattern** (`backend/db_core.py` lines 7–11):
```python
_SCHEMAS = [
    os.path.join(_DATA_DIR, "schema_core.sql"),
    os.path.join(_DATA_DIR, "schema_grama.sql"),
    os.path.join(_DATA_DIR, "schema_catalogo.sql"),
]
```
**What to add:** append `os.path.join(_DATA_DIR, "schema_manutencao.sql")` as the fourth entry. No other change to `db_core.py` — migrations for new columns (if any) go in `startup()` in `main.py`.

---

### `backend/main.py` — register router + startup hook (lines 20–22, 325–327, 793–811)

**Import pattern** (`backend/main.py` lines 20–22):
```python
from .catalogo import router as catalogo_router
from .grama   import router as grama_router, init_grama
from .sync    import router as sync_router
# ADD:
from .manutencao import router as manutencao_router
```

**Registration pattern** (`backend/main.py` lines 325–327):
```python
app.include_router(grama_router)
app.include_router(sync_router)
app.include_router(catalogo_router)
# ADD:
app.include_router(manutencao_router)
```

**Startup hook pattern** (`backend/main.py` lines 793–811):
```python
@app.on_event("startup")
async def startup():
    await db.init()
    # existing migrations ...
    init_grama(db)
    await _seed_colab_if_empty()
    # ...
    # ADD — no migration needed (schema_manutencao.sql loaded by db.init() via _SCHEMAS)
    # If future ALTER needed: same PRAGMA table_info guard as lines 797–799
```
Convention: `db.init()` already runs all `_SCHEMAS`; startup only needs explicit ALTER migrations for columns added after initial schema creation.

---

### `assets/erp-manutencao.js` — new "Registrar Uso" tab (TAB_DEFS + renderActiveTab)

**Analog:** `assets/erp-manutencao.js` lines 23–29 (TAB_DEFS) and lines 392–403 (renderTabBar loop)

**TAB_DEFS addition** (`assets/erp-manutencao.js` lines 23–29):
```js
const TAB_DEFS = [
  { id: 'dashboard',      icon: '📊', label: 'Painel' },
  { id: 'refrigeracao',   icon: '❄️', label: 'Refrigeração' },
  { id: 'transportes',    icon: '🚚', label: 'Transportes' },
  { id: 'corte',          icon: '🌿', label: 'Máq. Corte' },
  { id: 'fonoclama',      icon: '📣', label: 'Fonoclama' },
  // ADD:
  { id: 'registrar-uso',  icon: '⏱', label: 'Registrar Uso' },
];
```

**Tab panel rendering pattern** (`assets/erp-manutencao.js` lines 375–403): each tab entry in `TAB_DEFS` is rendered as a `<button data-tab="...">` by the `renderTabBar()` loop; `renderActiveTab()` switches content. Add a `case 'registrar-uso':` branch in `renderActiveTab()` that returns a `renderRegistrarUso()` function call (same pattern as `renderDashboard()`, `renderRefrigeracao()`, etc.).

**Form markup pattern** — inline HTML string inside the JS render function, following the `form-grid` / `form-group` CSS classes already in use (`cmasm_erp.html` lines 1425–1452 modal example):
```html
<div class="form-grid">
  <div class="form-group"><label>Ativo</label>
    <select id="uso-ativo-id">...</select>
  </div>
  <div class="form-group"><label>Delta (h/km)</label>
    <input type="number" id="uso-delta" min="0.1" step="0.1">
  </div>
  <div class="form-group"><label>Data</label>
    <input type="date" id="uso-data">
  </div>
  <div class="form-group form-full"><label>Observação</label>
    <input type="text" id="uso-obs" placeholder="Opcional">
  </div>
</div>
<div style="margin-top:12px">
  <button class="pe-btn pe-btn--primary" onclick="window._manut.registrarUso()">Registrar</button>
</div>
<div id="uso-feedback"></div>
<h3 style="margin-top:20px">Registros Recentes</h3>
<div id="uso-recentes"></div>
```

**API call pattern** (fetch via token from localStorage — existing convention throughout `erp-manutencao.js`):
```js
async function registrarUso() {
  const token = localStorage.getItem('xcmasm_token');
  const resp = await fetch('/api/manutencao/uso', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
    body: JSON.stringify({ ativo_id, delta, data, observacao }),
  });
  const data = await resp.json();
  if (!resp.ok) { toast(data.detail || 'Erro', 'warning'); return; }
  // show data.vencimentos_disparados if any
  toast('Uso registrado');
  await _loadRecentes();
}
```
Convention: `localStorage.getItem('xcmasm_token')` for Bearer token; `toast(msg, level?)` for feedback; `data.detail` for error string.

---

### `tests/conftest.py` — async fixture addition

**Analog:** `tests/conftest.py` lines 18–29 (existing sync fixture)

**Existing sync fixture** (lines 18–29):
```python
@pytest.fixture
def app_client(tmp_path, monkeypatch):
    """Fresh app + DB per test."""
    db_path = tmp_path / "test_core.db"
    monkeypatch.setenv("DB_PATH", str(db_path))
    for mod in ("backend.main", "backend.db_core", "backend.grama", "backend.sync"):
        sys.modules.pop(mod, None)
    main = importlib.import_module("backend.main")
    with TestClient(main.app) as client:
        yield client, main
```

**New async fixture to add** (do NOT change the existing sync fixture):
```python
import pytest_asyncio
from asgi_lifespan import LifespanManager
from httpx import AsyncClient, ASGITransport

@pytest_asyncio.fixture
async def async_app_client(tmp_path, monkeypatch):
    """Async fixture: runs startup lifespan (db.init()) via asgi-lifespan."""
    db_path = tmp_path / "test_async.db"
    monkeypatch.setenv("DB_PATH", str(db_path))
    for mod in ("backend.main", "backend.db_core", "backend.grama",
                "backend.sync", "backend.manutencao"):
        sys.modules.pop(mod, None)
    main = importlib.import_module("backend.main")
    async with LifespanManager(main.app) as manager:
        async with AsyncClient(
            transport=ASGITransport(app=manager.app), base_url="http://test"
        ) as client:
            yield client, main
```
Convention: module list in `sys.modules.pop` must include every router module to avoid stale `db` references. Add `"backend.manutencao"` to the list in the existing sync fixture too when `manutencao.py` is created.

---

### `tests/test_migracoes_idempotencia.py` (migration idempotency test)

**Analog:** `tests/test_catalogo.py` lines 1–54 (structure, `_query`/`_exec` helpers, `app_client` fixture usage)

**Pattern to follow**:
```python
"""Testa que db.init() pode ser chamado duas vezes sem erro (idempotência de migração)."""
import importlib, sys

def test_schema_manutencao_idempotente(app_client):
    """Roda startup (db.init já foi chamado pelo TestClient) e chama init() de novo."""
    _, main = app_client
    import asyncio
    # Segunda chamada a db.init() — não deve lançar "duplicate column name" nem DROP
    asyncio.get_event_loop().run_until_complete(main.db.init())

def test_uso_registros_table_exists(app_client):
    """uso_registros deve existir após startup."""
    import sqlite3
    _, main = app_client
    conn = sqlite3.connect(main.db.db_path)
    names = {r[1] for r in conn.execute("PRAGMA table_info(uso_registros)").fetchall()}
    conn.close()
    assert {"id","ativo_id","delta","valor_anterior","valor_novo","data","operador"} <= names
```
Convention: use `app_client` (sync TestClient) for migration tests — no async needed. SQLite direct query via `sqlite3.connect(main.db.db_path)` (same pattern as `_query()` in `test_catalogo.py` lines 7–14).

---

## Shared Patterns

### Auth (`_require_auth`)
**Source:** `backend/catalogo.py` lines 36–48  
**Apply to:** `backend/manutencao.py` — POST endpoint requires auth; GET may be open.  
Copy the function verbatim; it uses `_db()` not the module-level `db`.

### DB access (`_db()`)
**Source:** `backend/catalogo.py` lines 24–26  
**Apply to:** `backend/manutencao.py`  
```python
def _db():
    return sys.modules["backend.main"].db
```
Never import `db` at module top-level — would capture the pre-startup instance.

### Error responses
**Source:** `backend/catalogo.py` lines 191–197, `backend/main.py` lines 957–967  
**Apply to:** all endpoints  
Always `raise HTTPException(status_code, "detail string")`. Never return error dicts.

### Dark theme CSS tokens
**Source:** `cmasm_erp.html` line 377–381 (`.tab`, `.tab.active`, `.tab-panel`)  
**Apply to:** any new HTML markup in the tab  
Use `var(--bg)`, `var(--bg2)`, `var(--panel)`, `var(--acc)`, `var(--text2)` — never hardcoded hex in new markup.

### `CREATE TABLE IF NOT EXISTS` + index guard
**Source:** `data/schema_catalogo.sql` lines 12–32  
**Apply to:** `data/schema_manutencao.sql`  
Every table and index uses `IF NOT EXISTS`; run `PRAGMA foreign_keys = ON` at top.

---

## No Analog Found

None — all six artifacts have direct analogs in the codebase.

---

## Metadata

**Analog search scope:** `backend/`, `data/`, `assets/`, `tests/`, `cmasm_erp.html`  
**Files read:** `db_core.py`, `catalogo.py`, `main.py` (lines 1–837), `schema_catalogo.sql`, `conftest.py`, `test_catalogo.py`, `erp-manutencao.js`, `cmasm_erp.html` (targeted grep + reads)  
**Pattern extraction date:** 2026-06-28
