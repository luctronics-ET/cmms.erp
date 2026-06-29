# Phase 2: Plano no Ativo — Pattern Map

**Mapped:** 2026-06-28
**Files analyzed:** 5 (2 backend, 1 schema, 1 frontend, 1 test)
**Analogs found:** 5 / 5

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `data/schema_manutencao.sql` (add tables) | migration | CRUD | `data/schema_manutencao.sql` lines 1-20 (existing) | exact |
| `backend/manutencao.py` — `GET /plano-ativo` | controller | request-response | `backend/manutencao.py` `_vencimentos_para_ativo` lines 65-134 | exact |
| `backend/manutencao.py` — `POST /registro` | controller | CRUD + atomic txn | `backend/manutencao.py` `registrar_uso` lines 139-200 | exact |
| `assets/erp-manutencao.js` — plano checklist section | component | request-response | `erp-manutencao.js` registrar-uso section lines 1362-1485 | exact |
| `tests/test_manutencao.py` (new file) | test | — | `tests/test_catalogo.py` lines 1-80 | exact |

---

## Pattern Assignments

### `data/schema_manutencao.sql` — new tables `ativo_plano_estado` + `manut_registros`

**Analog:** `data/schema_manutencao.sql` lines 1-20 (existing `uso_registros`)

**Convention:** `CREATE TABLE IF NOT EXISTS` only. No DROP. PRAGMA foreign_keys ON at file top. One `CREATE INDEX IF NOT EXISTS` per FK/query-path column.

**Copy pattern** (lines 6-19 of existing schema_manutencao.sql):
```sql
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS uso_registros (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  ativo_id       TEXT    NOT NULL REFERENCES ativos(id),
  ...
  created_at     TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_uso_registros_ativo ON uso_registros(ativo_id, created_at DESC);
```

**Adapt for `ativo_plano_estado`:**
- PK: composite `(ativo_id, catalogo_plano_item_id)` — use `PRIMARY KEY (ativo_id, catalogo_plano_item_id)` (no AUTOINCREMENT)
- Columns: `ativo_id TEXT NOT NULL REFERENCES ativos(id)`, `catalogo_plano_item_id TEXT NOT NULL`, `ultimo_uso REAL`, `proximo_uso REAL`, `updated_at TEXT NOT NULL DEFAULT (datetime('now'))`
- Index on `(ativo_id)` to allow lookups by ativo

**Adapt for `manut_registros`:**
- Same shape as `uso_registros` but with `responsavel TEXT NOT NULL`, `itens TEXT` (JSON array of catalogo_plano_item_id), `uso_no_momento REAL`, `observacao TEXT`

---

### `backend/manutencao.py` — `GET /api/manutencao/plano-ativo?ativo_id=`

**Analog:** `backend/manutencao.py` `_vencimentos_para_ativo` lines 65-134

**Imports pattern** (lines 10-20 of manutencao.py — already present, no new imports needed):
```python
import json
import math
import sys
from typing import Optional
import aiosqlite
from fastapi import APIRouter, HTTPException, Header, Query
from pydantic import BaseModel, field_validator
```

**Auth pattern** (lines 32-44):
```python
async def _require_auth(authorization: str | None) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Token ausente")
    token = authorization[7:]
    row = await _db().fetch_one(
        "SELECT s.usuario_id, u.nome, u.mat, u.role "
        "FROM sessoes s JOIN usuarios u ON u.id = s.usuario_id "
        "WHERE s.token = ? AND s.expira_em > datetime('now')",
        (token,),
    )
    if not row:
        raise HTTPException(401, "Token inválido ou expirado")
    return row
```

**Core pattern — tipo lookup + plano matching** (lines 80-101 of manutencao.py):
```python
planos = await db.fetch_all("SELECT * FROM catalogo_planos WHERE ativo = 1")
plano_by_tipo: dict[str, list] = {}
for p in planos:
    tipos: list = []
    try:
        tipos = json.loads(p["aplicavel_tipos"] or "[]")
    except Exception:
        tipos = []
    if p["tipo_codigo"] and p["tipo_codigo"] not in tipos:
        tipos.append(p["tipo_codigo"])
    for t in tipos:
        plano_by_tipo.setdefault(t, []).append(p)
```

**Core pattern — item frequencia parse + status calc** (lines 103-131):
```python
for it in itens:
    try:
        raw = it["frequencia"] or p.get("frequencia")
        if not raw:
            continue
        f = json.loads(raw)
        if not isinstance(f, dict):
            continue
        if f.get("tipo") != "por_uso" or not f.get("valor"):
            continue
        iv = float(f["valor"])
        if iv <= 0:
            continue
        prox = (math.floor(uso / iv) + 1) * iv
        falta = prox - uso
        if falta <= iv * 0.15:   # janela URGENTE/PROXIMA — mesma constante
            ...
    except Exception:
        continue   # skip malformed — never crash
```

**Status derivation to copy** (new logic, extends the analog):
```python
# Status tiers (extend _vencimentos_para_ativo thresholds):
# VENCIDA  → falta <= 0
# URGENTE  → 0 < falta <= iv * 0.15
# PROXIMA  → iv * 0.15 < falta <= iv * 0.30
# EM_DIA   → falta > iv * 0.30
```

**State merge pattern:** After computing `prox`/`falta` from catalogplano, LEFT JOIN `ativo_plano_estado` on `(ativo_id, catalogo_plano_item_id)`. If row exists, use `estado.proximo_uso` as the authoritative `prox` value (overrides computed). Emit `ultimo_uso`, `proximo_uso`, `status`, `falta`, `pct` per item.

**plano_item_id field:** `catalogo_plano_itens` has no explicit `id` column — query must include `rowid AS id` or add an `id` column when inserting. Check `PRAGMA table_info(catalogo_plano_itens)` first. If no `id`, use `(plano_id || '::' || servico_id)` as the stable composite key for `catalogo_plano_item_id` in `ativo_plano_estado`.

---

### `backend/manutencao.py` — `POST /api/manutencao/registro`

**Analog:** `backend/manutencao.py` `registrar_uso` lines 139-200 — this is the canonical atomic transaction pattern.

**Pydantic model pattern** (lines 49-60):
```python
class RegistroIn(BaseModel):
    ativo_id: str
    responsavel: str           # obrigatório
    itens: list[str]           # catalogo_plano_item_ids marcados
    observacao: Optional[str] = None

    @field_validator("responsavel")
    @classmethod
    def resp_nao_vazio(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("responsavel é obrigatório")
        return v.strip()
```

**Atomic transaction pattern** (lines 154-190 — copy verbatim, adapt inserts):
```python
db_path = _db().db_path

async with aiosqlite.connect(db_path) as conn:
    conn.row_factory = aiosqlite.Row

    # 1. Read ativo snapshot inside transaction
    async with conn.execute(
        "SELECT uso_atual, tipo FROM ativos WHERE id = ? AND ativo = 1",
        (body.ativo_id,),
    ) as cur:
        row = await cur.fetchone()
    if not row:
        raise HTTPException(404, "Ativo não encontrado")

    uso_atual = float(row["uso_atual"] or 0.0)

    # 2. INSERT manut_registros
    await conn.execute(
        "INSERT INTO manut_registros (ativo_id, responsavel, itens, uso_no_momento, observacao) "
        "VALUES (?, ?, ?, ?, ?)",
        (body.ativo_id, body.responsavel,
         json.dumps(body.itens), uso_atual, body.observacao),
    )

    # 3. UPSERT ativo_plano_estado per checked item
    for item_id in body.itens:
        # fetch intervalo from catalogo_plano_itens ...
        await conn.execute(
            "INSERT INTO ativo_plano_estado (ativo_id, catalogo_plano_item_id, ultimo_uso, proximo_uso, updated_at) "
            "VALUES (?, ?, ?, ?, datetime('now')) "
            "ON CONFLICT(ativo_id, catalogo_plano_item_id) DO UPDATE SET "
            "ultimo_uso=excluded.ultimo_uso, proximo_uso=excluded.proximo_uso, updated_at=excluded.updated_at",
            (body.ativo_id, item_id, uso_atual, proximo_uso),
        )

    # 4. Single commit — atomicity (T-01-04)
    await conn.commit()
```

**Key:** `ON CONFLICT ... DO UPDATE SET` syntax from `backend/sync.py` lines 451-455 is the upsert analog for `ativo_plano_estado`. Copy that exact clause shape.

**Post-commit read** (lines 192-200 pattern): after commit, return summary using `_db().fetch_one` (singleton, separate connection), not the closed `conn`.

---

### `assets/erp-manutencao.js` — plano checklist section

**Analog 1 (DOM construction):** `erp-manutencao.js` registrar-uso section lines 1362-1485 — `el()` builder, cardStyle/labelStyle/inputStyle tokens, fetch with `ruAuthHeaders()`, `btnRegistrar.disabled = true` guard, `try/catch/finally`, `toast()`, `cont.replaceChildren(...)`.

**Analog 2 (checklist visual):** `erp-manutencao.js` `subManut()` lines 1891-1922 — the legacy innerHTML checklist with checkboxes, `badgeHtml(p.st)`, responsável selector, "Registrar Manutenção" button. The Phase 2 implementation ports this to `el()` + safe DOM (no innerHTML of server data).

**Status badge pattern** (lines 1714-1718):
```javascript
function badgeHtml(st, txt) {
  const colors = { danger: '#ef4444', warn: '#f59e0b', proximo: '#00b4d8', ok: '#22c55e' };
  const c = colors[st] || colors.ok;
  return `<span style="...background:${c}22;color:${c};border:1px solid ${c}55">${txt || SL[st] || st}</span>`;
}
```
Phase 2 maps API status strings to these `st` keys:
- `VENCIDA` → `'danger'`
- `URGENTE` → `'warn'`
- `PROXIMA` → `'proximo'`
- `EM_DIA`  → `'ok'`

Use `window.engine.badge(label, kind)` (pmoc-engine.js line 108) as the `el()`-based equivalent — `kind` maps to same color set via CSS class `pe-badge--{kind}`. Either approach is acceptable; `engine.badge` avoids raw HTML injection.

**Fetch + auth pattern** (lines 1437-1483):
```javascript
const res = await fetch(apiUrl('/api/manutencao/plano-ativo?ativo_id=' + ativoId), {
  headers: ruAuthHeaders(),   // { Authorization: 'Bearer ' + localStorage.getItem('xcmasm_token') }
});
if (!res.ok) {
  const err = await res.json().catch(() => ({}));
  toast(err.detail || 'Erro HTTP ' + res.status, 'red');
  return;
}
const data = await res.json();
```

**Checkbox item render pattern** (lines 1899-1906 — port to `el()`):
```javascript
// Each plan item row: checkbox + name + interval text + status badge
el('label', { style: { display:'flex', alignItems:'center', gap:'9px',
    padding:'8px 11px', borderRadius:'7px', cursor:'pointer',
    border:'2px solid var(--line)', background:'var(--panel)', marginBottom:'6px' }},
  el('input', { type: 'checkbox', value: item.catalogo_plano_item_id,
    style: { width:'14px', height:'14px', accentColor:'var(--acc)' } }),
  el('div', { style: { flex: 1 } },
    el('div', { style: { fontSize:'12px', fontWeight:'600' } }, item.servico_nome),
    el('div', { style: { fontSize:'10px', color:'var(--ink-3)' } },
      `A cada ${item.intervalo} ${item.unidade} · faltam ${item.falta.toFixed(1)}`),
  ),
  window.engine.badge(statusLabel(item.status), statusKind(item.status)),
)
```

**Progress bar pattern** (derive from `pct` field returned by GET):
```javascript
el('div', { style: { height:'4px', background:'var(--line)', borderRadius:'2px', marginTop:'4px' } },
  el('div', { style: { width: item.pct + '%', height:'100%',
      background: item.pct >= 85 ? 'var(--red)' : item.pct >= 70 ? 'var(--amber)' : 'var(--green)',
      borderRadius:'2px' } })
)
```

**DOM safety rule** (CONTEXT.md line 39): Never set `innerHTML` to server-provided string data. Use `el()` + `.textContent`. The legacy `subManut()` template-literal approach is the OLD pattern — DO NOT replicate it. The registrar-uso section (lines 1362-1485) is the approved current pattern.

---

### `tests/test_manutencao.py` (new file)

**Analog:** `tests/test_catalogo.py` lines 1-54 (fixtures, helpers, seeding pattern)

**Fixture pattern** — copy verbatim:
```python
def _query(main, sql, params=()):
    conn = sqlite3.connect(main.db.db_path)
    conn.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()

def _exec(main, sql, params=()):
    conn = sqlite3.connect(main.db.db_path)
    try:
        conn.execute(sql, params); conn.commit()
    finally:
        conn.close()

def _seed_user(main) -> int:
    _exec(main,
        "INSERT OR IGNORE INTO usuarios (id, nome, mat, pw_hash, role, ativo) "
        "VALUES (1, 'Admin', '000001', 'hash', 'admin', 1)")
    return 1

def _seed_sessao(main, uid=1) -> str:
    token = "test-token-manut-02"
    _exec(main,
        "INSERT OR IGNORE INTO sessoes (token, usuario_id, expira_em) "
        "VALUES (?, ?, datetime('now', '+8 hours'))", (token, uid))
    return token

def _auth(main) -> dict:
    uid = _seed_user(main)
    token = _seed_sessao(main, uid)
    return {"Authorization": f"Bearer {token}"}
```

**Conftest wiring** (`tests/conftest.py` line 27): `backend.manutencao` is already in the reload list — no changes to conftest needed.

**Test coverage required** (from CONTEXT.md lines 42-43):
1. `test_plano_ativo_retorna_itens` — GET with a seeded ativo + catalogo_plano: verify response contains items with `status`, `falta`, `pct`
2. `test_registro_upsert_proximo_uso` — POST registro once → `proximo_uso = uso_no_momento + intervalo`; POST again → `proximo_uso = uso_no_momento + 2 × intervalo` (anti-double-count)
3. `test_registro_transacao_atomica` — force an error mid-transaction, verify no partial row in `manut_registros`
4. `test_registro_exige_responsavel` — POST without `responsavel` returns 422

**Test uses `app_client` fixture** (sync TestClient — same as `test_catalogo.py`; async fixture available if needed via `async_app_client`).

---

## Shared Patterns

### Auth guard
**Source:** `backend/manutencao.py` lines 32-44
**Apply to:** both new endpoints
```python
user = await _require_auth(authorization)
operador = user.get("mat") or user.get("nome") or str(user.get("usuario_id", ""))
```

### Atomic transaction (aiosqlite.connect block)
**Source:** `backend/manutencao.py` `registrar_uso` lines 154-190
**Apply to:** `POST /registro`
- `async with aiosqlite.connect(db_path) as conn:` — single block, single `await conn.commit()`
- All reads inside the same `conn` for snapshot consistency
- Raise `HTTPException` before commit to trigger automatic rollback
- Post-commit reads use `_db()` singleton (different connection)

### Upsert (ON CONFLICT DO UPDATE)
**Source:** `backend/sync.py` lines 449-457
**Apply to:** `ativo_plano_estado` upsert inside `POST /registro`
```python
"INSERT INTO ativo_plano_estado (...) VALUES (?) "
"ON CONFLICT(ativo_id, catalogo_plano_item_id) DO UPDATE SET "
"ultimo_uso=excluded.ultimo_uso, proximo_uso=excluded.proximo_uso, updated_at=excluded.updated_at"
```

### DB singleton helper
**Source:** `backend/manutencao.py` lines 27-29
**Apply to:** all reads outside the atomic block
```python
def _db():
    return sys.modules["backend.main"].db
```

### Status thresholds (URGENTE/PROXIMA windows)
**Source:** `backend/manutencao.py` lines 117, 175 (JS mirror)
**Apply to:** `GET /plano-ativo` status computation, `badgeHtml`/`engine.badge` kind mapping
- `falta <= 0` → VENCIDA / `danger`
- `0 < falta <= iv * 0.15` → URGENTE / `warn`
- `iv * 0.15 < falta <= iv * 0.30` → PROXIMA / `proximo`
- else → EM_DIA / `ok`

### Frontend fetch + Bearer token
**Source:** `erp-manutencao.js` lines 1437-1483
**Apply to:** plano checklist fetch + registro submit
```javascript
headers: { 'Content-Type': 'application/json',
           'Authorization': 'Bearer ' + (localStorage.getItem('xcmasm_token') || '') }
```

### Safe DOM construction
**Source:** `erp-manutencao.js` lines 1374-1484 (registrar-uso section)
**Apply to:** entire checklist section — `el()` + `.textContent`, never `innerHTML` with server data

---

## No Analog Found

None. All five artifacts have direct analogs in the codebase.

---

## Metadata

**Analog search scope:** `backend/`, `data/`, `assets/`, `tests/`
**Files read:** manutencao.py (235 lines), catalogo.py (668 lines), schema_manutencao.sql (20 lines), schema_catalogo.sql (80 lines, partial), erp-manutencao.js (lines 1-320 + 1360-1940), test_manutencao_smoke.py (95 lines), test_catalogo.py (80 lines, partial), conftest.py (50 lines), sync.py (excerpt)
**Pattern extraction date:** 2026-06-28
