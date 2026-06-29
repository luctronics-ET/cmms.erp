# Phase 2: Plano no Ativo — Research

**Researched:** 2026-06-28
**Domain:** CMMS — Maintenance Plan per Asset (plano↔ativo, checkboxes, proximo_uso, manut_registros)
**Confidence:** HIGH (all conclusions drawn from direct file inspection; no external sources needed)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Modelo de dados**
- Nova tabela `ativo_plano_estado` em `schema_manutencao.sql`: `(ativo_id, catalogo_plano_item_id)` chave; `ultimo_uso` (REAL), `proximo_uso` (REAL), `updated_at`. É o `ulm` do legado persistido (estado por item por ativo).
- Nova tabela `manut_registros`: `id`, `ativo_id`, `responsavel`, `data`, `itens` (JSON dos catalogo_plano_item_id marcados ou linhas separadas), `uso_no_momento`, `observacao`, `created_at`. Trilha do que foi executado.
- Não dropar/alterar tabelas existentes; aditivo via `CREATE TABLE IF NOT EXISTS`.

**Cálculo de status e proximo_uso**
- Status por item derivado de `uso_atual` do ativo vs `proximo_uso` do item: VENCIDA (uso_atual >= proximo_uso), URGENTE/PROXIMA por janelas (reusar limiar existente, ex. iv*0.15), EM DIA caso contrário.
- Ao registrar item marcado: `proximo_uso = uso_no_momento + intervalo` (intervalo = frequência do item no `catalogo_plano_itens`, com default do plano). Idempotente por registro — dois registros consecutivos dão `uso + 2×intervalo`, sem double-count.
- "faltam X" = `proximo_uso - uso_atual`. Barra de progresso = fração do intervalo consumida.
- Primeiro registro de um item sem estado prévio: cria a linha em `ativo_plano_estado` com `ultimo_uso=uso_no_momento`, `proximo_uso=uso_no_momento+intervalo`.

**Contrato de endpoint**
- `GET /api/manutencao/plano-ativo?ativo_id=` retorna itens do plano aplicável ao tipo do ativo (via `catalogo_planos.aplicavel_tipos`) com estado (ultimo_uso/proximo_uso/status/falta) mesclado de `ativo_plano_estado`.
- `POST /api/manutencao/registro` payload `{ativo_id, responsavel, itens:[catalogo_plano_item_id...], observacao?}`: insere `manut_registros` + upsert `ativo_plano_estado.proximo_uso` por item marcado, tudo em UMA transação atômica. Responsável obrigatório.
- Operador/responsável: responsável vem do payload; operador (quem registrou) do token.

**Frontend (UX)**
- Na aba de manutenção do ativo (reusar/estender o que já existe), renderizar lista de itens do plano com checkbox, badge de status colorido (tokens dark), barra de progresso, texto "faltam X".
- Campo responsável + botão "Registrar Manutenção". Após registrar: feedback, recarregar a lista (status atualizam, VENCIDA some para item recém-executado).
- Bearer token de `localStorage('xcmasm_token')`. Inserção segura no DOM (sem innerHTML de dados do servidor — usar el()/textContent, como corrigido na Fase 1).

**Testes**
- `tests/test_manutencao.py::test_plano_no_ativo` (ou arquivo dedicado): registrar duas vezes → `proximo_uso = uso_no_momento + 2×intervalo`; status reflete proximo_uso atualizado; transação atômica.
- Sem nova regressão vs baseline (14 falhas pré-existentes não contam).

### Claude's Discretion
- Nomes exatos de endpoint/colunas e shape fino do JSON.
- Reuso vs nova seção na aba de manutenção (onde encaixa melhor no `erp-manutencao.js`).
- Limiares exatos de URGENTE/PROXIMA (seguir o padrão já usado em vencimentos).

### Deferred Ideas (OUT OF SCOPE)
- Cronograma por equipe → Fase 5 (consome este estado).
- Gerar OS preventiva a partir do registro (já existe fluxo separado) — não ampliar aqui.
</user_constraints>

---

## Summary

Phase 2 implements the "plano no ativo" feature: a technician selects an asset, sees the maintenance plan items applicable to that asset type (resolved via `catalogo_planos.aplicavel_tipos`), checks off which items were performed, and submits the form. The backend writes a `manut_registros` row and upserts `ativo_plano_estado.proximo_uso` for each checked item in a single atomic transaction.

The dominant implementation complexity is correctness: the `proximo_uso` must be computed from the **current `uso_atual` at POST time** (read inside the transaction from the DB), not from a stale client value — otherwise the anti-double-count invariant breaks. The legacy HTML `CMASM_Gestao_v2.html` (line 1135: `ulm[pid] = h.hor`) already demonstrates the correct pattern: record the meter reading at registration time, not a pre-fetched value.

The frontend inserts into the existing `openAtivoDrawer` modal (`erp-manutencao.js:1721`), specifically the `subManut()` sub-tab (`line 1891`). Phase 1 already implemented this UI in localStorage-only mode; Phase 2 wires it to the backend endpoints. The insertion point is inside the existing `regManut:` handler closure (line 1755), which is replaced by an async API call.

**Primary recommendation:** Add new SQL to `schema_manutencao.sql`, add two endpoints to `backend/manutencao.py`, and replace the `regManut` closure in `openAtivoDrawer` with an async `fetch` to `POST /api/manutencao/registro`. Do not create new files; wire into existing extension points.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Resolve plan for asset type | API / Backend | — | `catalogo_planos.aplicavel_tipos` JSON is in SQLite; browser has no direct DB access |
| Per-item status computation (VENCIDA/URGENTE/etc.) | API / Backend | — | Needs `ativo_plano_estado` + `uso_atual`; computed once server-side, sent as enum |
| Atomic write (manut_registros + ativo_plano_estado) | API / Backend | — | Requires a single SQLite transaction; cannot be split across requests |
| Checklist UI + progress bar | Browser / Client | — | Pure rendering; no server round-trip per checkbox toggle |
| Responsible-person picker | Browser / Client | — | Static list populated from `ativos`/`usuarios` cache already loaded |
| Bearer auth | API / Backend | Browser / Client | Token from `localStorage('xcmasm_token')` sent as Authorization header |

---

## Standard Stack

All dependencies already present in the project. No new packages required.

| Library | Version | Purpose |
|---------|---------|---------|
| `aiosqlite` | installed (Phase 1 already imports it) | Atomic transaction via raw `aiosqlite.connect` context manager |
| `fastapi` | installed | Router + Pydantic models |
| `pydantic` | installed | `RegistroIn` model with `field_validator` |

**Installation:** none required.

---

## Key Data Model: catalogo_planos → catalogo_plano_itens → ativo_plano_estado

### How plan assignment works (`data/schema_catalogo.sql`)

`catalogo_planos` (line 239–267 of `schema_catalogo.sql`) has two resolution fields:

```
catalogo_planos.tipo_codigo   TEXT       — applies to all ativos of this tipo (e.g., "AC_SPLIT")
catalogo_planos.aplicavel_tipos TEXT     — JSON list of tipo_codes that reuse this plan by name
```

Both fields are used for lookup (see `main.py:2537-2546`, mirrored in `manutencao.py:80-91`):

```python
# manutencao.py lines 80-91 (_vencimentos_para_ativo)
planos = await db.fetch_all("SELECT * FROM catalogo_planos WHERE ativo = 1")
plano_by_tipo: dict[str, list] = {}
for p in planos:
    tipos = json.loads(p["aplicavel_tipos"] or "[]")   # primary: JSON list
    if p["tipo_codigo"] and p["tipo_codigo"] not in tipos:
        tipos.append(p["tipo_codigo"])                  # secondary: scalar fallback
    for t in tipos:
        plano_by_tipo.setdefault(t, []).append(p)
```

**To find plans for a given asset:** `plano_by_tipo.get(ativo["tipo"], [])`. This is already implemented in `_vencimentos_para_ativo` and can be reused verbatim.

### How per-item interval works

`catalogo_plano_itens.frequencia` (nullable TEXT, JSON) overrides the plan-level `catalogo_planos.frequencia` (TEXT, JSON):

```python
# manutencao.py lines 103-116
raw = it["frequencia"] or p.get("frequencia")   # item override else plan default
f = json.loads(raw)                              # {"tipo": "por_uso", "valor": 250, "unidade": "h"}
iv = float(f["valor"])                           # the interval in uso units
```

The GET handler must read `it["frequencia"] or p["frequencia"]` for every item — never assume the item has its own frequency.

### New tables (to add to `data/schema_manutencao.sql`)

```sql
CREATE TABLE IF NOT EXISTS ativo_plano_estado (
  ativo_id              TEXT    NOT NULL REFERENCES ativos(id),
  catalogo_plano_item_id INTEGER NOT NULL REFERENCES catalogo_plano_itens(id),
  ultimo_uso            REAL    NOT NULL DEFAULT 0,   -- uso_no_momento when last registered
  proximo_uso           REAL    NOT NULL,              -- ultimo_uso + intervalo
  updated_at            TEXT    NOT NULL DEFAULT (datetime('now')),
  PRIMARY KEY (ativo_id, catalogo_plano_item_id)
);
CREATE INDEX IF NOT EXISTS idx_ape_ativo ON ativo_plano_estado(ativo_id);

CREATE TABLE IF NOT EXISTS manut_registros (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  ativo_id        TEXT    NOT NULL REFERENCES ativos(id),
  responsavel     TEXT    NOT NULL,
  operador        TEXT,                               -- token user snapshot
  data            TEXT    NOT NULL,                   -- ISO YYYY-MM-DD
  uso_no_momento  REAL    NOT NULL,                   -- ativos.uso_atual read inside txn
  itens_json      TEXT    NOT NULL,                   -- JSON array of catalogo_plano_item_id (integers)
  observacao      TEXT,
  created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_mr_ativo ON manut_registros(ativo_id, created_at DESC);
```

**Key design decisions:**
- `itens_json` is a JSON array of `catalogo_plano_item_id` integers (not UUIDs — the table uses `INTEGER PRIMARY KEY AUTOINCREMENT`). This matches `catalogo_plano_itens.id` type.
- `uso_no_momento` is read from `ativos.uso_atual` inside the transaction (never from the request payload) to prevent off-by-one.
- `proximo_uso` in `ativo_plano_estado` is a `REAL` column — never TEXT — to enable numeric comparison with `uso_atual` (see PITFALLS §8 in `PITFALLS.md`).

---

## GET Endpoint: `GET /api/manutencao/plano-ativo`

**Location:** `backend/manutencao.py` (append after line 234)

**Query param:** `ativo_id` (required)

**Algorithm:**

1. Fetch asset: `SELECT id, nome, tipo, uso_atual, unidade_uso FROM ativos WHERE id = ? AND ativo = 1`
2. Resolve plans by tipo using the existing pattern from `_vencimentos_para_ativo` (lines 80-91).
3. For each plan, fetch items: `SELECT i.id, i.seq, i.classe, i.frequencia, s.nome, s.tempo_estimado_min FROM catalogo_plano_itens i JOIN catalogo_servicos s ON s.id = i.servico_id WHERE i.plano_id = ? ORDER BY i.seq`
4. For each item, compute interval: `iv = float(json.loads(it["frequencia"] or p["frequencia"])["valor"])`
5. Fetch state from `ativo_plano_estado`: single query for all items of this ativo: `SELECT catalogo_plano_item_id, ultimo_uso, proximo_uso FROM ativo_plano_estado WHERE ativo_id = ?` → build dict `estado_by_item_id`.
6. For each item, merge state and compute status:

```python
uso = ativo["uso_atual"] or 0.0
estado = estado_by_item[item_id]
if estado:
    proximo_uso = estado["proximo_uso"]
    ultimo_uso  = estado["ultimo_uso"]
else:
    # No history: extrapolate first proximo from current usage
    proximo_uso = (math.floor(uso / iv) + 1) * iv
    ultimo_uso  = None

falta = proximo_uso - uso
pct   = round(min(100, max(0, (uso - (proximo_uso - iv)) / iv * 100)))

# Status thresholds (same constants as main.py:2571 and manutencao.py:117)
if falta <= 0:
    status = "VENCIDA"
elif falta <= iv * 0.15:
    status = "URGENTE"
elif falta <= iv * 0.30:
    status = "PROXIMA"
else:
    status = "EM_DIA"
```

**Response shape (per item):**

```json
{
  "plano_id": "uuid",
  "plano_nome": "Split 18kBTU",
  "item_id": 42,
  "servico_nome": "Limpeza filtro evaporadora",
  "intervalo": 250.0,
  "unidade": "h",
  "ultimo_uso": 1500.0,
  "proximo_uso": 1750.0,
  "uso_atual": 1620.0,
  "falta": 130.0,
  "pct": 48,
  "status": "EM_DIA"
}
```

Outer wrapper:

```json
{
  "ativo_id": "...",
  "ativo_nome": "Split Sala 101",
  "uso_atual": 1620.0,
  "unidade_uso": "h",
  "itens": [...]
}
```

---

## POST Endpoint: `POST /api/manutencao/registro`

**Location:** `backend/manutencao.py` (append after GET)

**Pydantic model:**

```python
class RegistroIn(BaseModel):
    ativo_id:    str
    responsavel: str
    itens:       list[int]   # catalogo_plano_item_id values (non-empty)
    observacao:  Optional[str] = None

    @field_validator("itens")
    @classmethod
    def itens_nao_vazios(cls, v):
        if not v:
            raise ValueError("Selecione ao menos um item")
        return v

    @field_validator("responsavel")
    @classmethod
    def resp_nao_vazio(cls, v):
        if not v or not v.strip():
            raise ValueError("Responsável é obrigatório")
        return v.strip()
```

**Atomic transaction pattern (same as `registrar_uso`, `manutencao.py:154`):**

```python
db_path = _db().db_path
async with aiosqlite.connect(db_path) as conn:
    conn.row_factory = aiosqlite.Row

    # 1. Read uso_atual inside the transaction (snapshot; never trust payload)
    async with conn.execute(
        "SELECT uso_atual FROM ativos WHERE id = ? AND ativo = 1",
        (body.ativo_id,)
    ) as cur:
        row = await cur.fetchone()
    if not row:
        raise HTTPException(404, "Ativo não encontrado")
    uso_no_momento = float(row["uso_atual"] or 0.0)

    # 2. Validate and resolve intervals for each checked item
    itens_validos = []
    for item_id in body.itens:
        async with conn.execute(
            "SELECT i.id, i.frequencia, p.frequencia AS plano_freq "
            "FROM catalogo_plano_itens i "
            "JOIN catalogo_planos p ON p.id = i.plano_id "
            "WHERE i.id = ?",
            (item_id,)
        ) as cur:
            it = await cur.fetchone()
        if not it:
            raise HTTPException(422, f"Item {item_id} não encontrado")
        raw = it["frequencia"] or it["plano_freq"]
        if not raw:
            raise HTTPException(422, f"Item {item_id} sem frequência definida")
        try:
            f = json.loads(raw)
            iv = float(f["valor"])
        except Exception:
            raise HTTPException(422, f"Frequência inválida no item {item_id}")
        itens_validos.append({"item_id": item_id, "iv": iv})

    # 3. Insert manut_registros
    await conn.execute(
        "INSERT INTO manut_registros "
        "(ativo_id, responsavel, operador, data, uso_no_momento, itens_json, observacao) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            body.ativo_id,
            body.responsavel,
            operador,                          # from _require_auth token snapshot
            date.today().isoformat(),
            uso_no_momento,
            json.dumps(body.itens),
            body.observacao,
        )
    )

    # 4. Upsert ativo_plano_estado per checked item
    for item in itens_validos:
        novo_proximo = uso_no_momento + item["iv"]  # anti-double-count: always uso_no_momento + iv
        await conn.execute(
            """INSERT INTO ativo_plano_estado
               (ativo_id, catalogo_plano_item_id, ultimo_uso, proximo_uso, updated_at)
               VALUES (?, ?, ?, ?, datetime('now'))
               ON CONFLICT (ativo_id, catalogo_plano_item_id)
               DO UPDATE SET
                 ultimo_uso  = excluded.ultimo_uso,
                 proximo_uso = excluded.proximo_uso,
                 updated_at  = excluded.updated_at""",
            (body.ativo_id, item["item_id"], uso_no_momento, novo_proximo)
        )

    # 5. Single commit — atomicity guaranteed (same pattern as Phase 1)
    await conn.commit()

return {"ok": True, "uso_no_momento": uso_no_momento, "itens_registrados": len(itens_validos)}
```

**Anti-double-count proof:**
- First registration at `uso=1000`, `iv=250`: `proximo_uso = 1000 + 250 = 1250`.
- Second registration immediately (usage unchanged, still `uso=1000`): `proximo_uso = 1000 + 250 = 1250` — same value, idempotent.
- Second registration after additional usage `uso=1100`: `proximo_uso = 1100 + 250 = 1350`. Two separate registrations at different uso readings → `proximo_uso = uso_at_second_registration + iv`. No accumulation.
- This satisfies the test: `registrar duas vezes → proximo_uso = uso_no_momento + 2×intervalo` when `uso` advances by `iv` between the two calls.

---

## Status Computation Detail

The **three threshold constants** are used consistently throughout the codebase:

| Threshold | Expression | Status | Color token |
|-----------|-----------|--------|-------------|
| `falta <= 0` | `uso_atual >= proximo_uso` | VENCIDA | `var(--red)` |
| `0 < falta <= iv * 0.15` | 15% window remaining | URGENTE | `var(--amber)` |
| `iv * 0.15 < falta <= iv * 0.30` | 30% window remaining | PROXIMA | `var(--acc)` (cyan) |
| `falta > iv * 0.30` | beyond 30% window | EM_DIA | `var(--green)` |

Source (confirmed): `main.py:2571` (`falta <= iv * 0.15` → "warn"), `manutencao.py:117` (same). The 30% PROXIMA window is in the legacy `erp-manutencao.js:175`: `falt <= m.iv * 0.30 ? 'proximo' : 'ok'`.

**Progress bar fraction:** `pct = round(min(100, max(0, (uso_atual - (proximo_uso - iv)) / iv * 100)))`

- When `proximo_uso - iv <= uso_atual < proximo_uso`: 0–100% consumed in this cycle.
- Caps at 100 when overdue (VENCIDA).
- Guards against division by zero: `if iv <= 0: skip item`.

---

## Frontend: Where and How to Insert

### Location: `subManut()` inside `openAtivoDrawer` (erp-manutencao.js:1891)

The existing `subManut()` function (lines 1891–1921) renders checkboxes from the localStorage-based `calcProxManut(ativo)` result. Phase 2 **replaces the `regManut` closure** (lines 1755–1794) with an async backend call, and **replaces the `subManut()` content** with a version that fetches from `GET /api/manutencao/plano-ativo`.

The `SUBS` map at line 1984 routes `manut` key to `subManut`. The modal sub-tab label already says `🔧 Manutenção`.

### DOM pattern (safe — no `innerHTML` of server data)

The CONTEXT.md mandates using `el()/textContent` (already enforced in Phase 1, see `registrar-uso` tab at lines 1284–1560 for the reference pattern).

The new `subManut()` must:
1. Call `GET /api/manutencao/plano-ativo?ativo_id=X` with Bearer token.
2. Render each item using `el()` — **never** template literal strings with server-supplied `item.servico_nome` interpolated inside `innerHTML`. Use `el('div', {}, el('span', {}, item.servico_nome))` style.
3. Checkboxes: use `el('input', { type: 'checkbox', id: '_mn-' + item.item_id, class: '_mn-cb', value: String(item.item_id) })`.
4. Progress bar: `el('div', { style: { width: pct + '%', ... } })` — `pct` is a number from the API, safe in style attribute.
5. Status badge: use `window.engine.badge(item.status, colorMap[item.status])` where `colorMap` is:
   ```js
   const COLOR = { VENCIDA: 'red', URGENTE: 'amber', PROXIMA: 'blue', EM_DIA: 'green' };
   ```

### `regManut` replacement (lines 1755–1794)

The existing `regManut` closure writes to localStorage only. Replace with:

```js
regManut: async () => {
  const resp = paNoResp?.value?.trim();          // paNoResp = select element scoped to this modal
  const sels = [...subBody.querySelectorAll('._mn-cb:checked')].map(cb => parseInt(cb.value, 10));
  if (!sels.length)  { toast('Selecione ao menos um serviço', 'amber'); return; }
  if (!resp)         { toast('Informe o responsável', 'amber'); return; }
  const token = localStorage.getItem('xcmasm_token') || '';
  try {
    const r = await fetch(apiUrl('/api/manutencao/registro'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
      body: JSON.stringify({ ativo_id: ativo.id, responsavel: resp, itens: sels }),
    });
    if (!r.ok) { const e = await r.json(); toast('Erro: ' + (e.detail || r.status), 'red'); return; }
    toast('Manutenção registrada', 'green');
    activeSub = 'manut';                         // stay on manut sub-tab
    renderSub();                                  // reload — statuses refresh from GET
  } catch (e) { toast('Falha de rede: ' + e.message, 'red'); }
},
```

Key: `renderSub()` re-runs `subManut()` which re-fetches `GET /api/manutencao/plano-ativo` — statuses update on screen without a full page reload.

### Variable scoping

The new `subManut()` must be `async function subManut()` and store the `paNoResp` select element in a closure-level variable so `regManut` can read it. This avoids relying on a global `getElementById` with a fixed ID (which risks the Pitfall 6 global-scope collision).

Prefix all IDs in this sub-tab with `_mn-` to avoid collision with the existing `_mc-` (checkbox) and `_md-` (general modal) prefixes already in use.

---

## Architecture Patterns

### Pattern 1: Atomic Two-Table Write (reuse from Phase 1)

Already established in `registrar_uso` (manutencao.py:154):

```python
async with aiosqlite.connect(db_path) as conn:
    # READ uso_atual inside same connection
    # INSERT manut_registros
    # UPSERT ativo_plano_estado (multiple rows in one transaction)
    await conn.commit()
# vencimentos check runs AFTER commit, on singleton (read-only)
```

The `ON CONFLICT ... DO UPDATE` SQLite upsert (available since SQLite 3.24, 2018) is the right tool for `ativo_plano_estado` — the `PRIMARY KEY (ativo_id, catalogo_plano_item_id)` is the conflict target.

### Pattern 2: Plan Resolution (reuse _vencimentos_para_ativo)

`_vencimentos_para_ativo` (manutencao.py:65-134) already implements:
- Load all `catalogo_planos`
- Build `plano_by_tipo` dict
- Match by `aplicavel_tipos` JSON + `tipo_codigo` scalar fallback
- Parse item `frequencia` with guard against malformed JSON

The GET handler reuses this same resolution logic. The difference: instead of returning only items within the 15% alert window, it returns **all items** (so the technician sees the full plan, including EM_DIA items with their progress bars).

### Pattern 3: CoreDB _SCHEMAS Already Includes schema_manutencao.sql

`db_core.py:11`: `os.path.join(_DATA_DIR, "schema_manutencao.sql")` is already in `_SCHEMAS`. The new `CREATE TABLE IF NOT EXISTS` statements go at the end of the existing file — no change to `db_core.py` required.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---------|-------------|-------------|
| SQLite upsert | Custom SELECT + INSERT/UPDATE branches | `INSERT ... ON CONFLICT (pk) DO UPDATE SET ...` (SQLite 3.24+) |
| Atomic multi-table write | Per-statement `_db().execute()` calls | Single `aiosqlite.connect` context manager with one `commit()` |
| JSON validation of payload | Manual isinstance checks | Pydantic `field_validator` on `RegistroIn` |
| Plan-type resolution | Duplicate the lookup logic | Reuse `_vencimentos_para_ativo` pattern (already tested, handles edge cases) |
| Status computation | Custom string comparison | Numeric comparison: `falta <= 0`, `falta <= iv * 0.15`, `falta <= iv * 0.30` |

---

## Common Pitfalls

### Pitfall 1: proximo_uso computed from stale request value (Pitfall 8 in PITFALLS.md)

**What goes wrong:** If the POST handler computes `proximo_uso = body.uso_atual + iv` (using a value sent by the client), and the client's cached `uso_atual` is stale (another session registered use in between), `proximo_uso` is too low and the next trigger fires early.

**How to avoid:** Always `SELECT uso_atual FROM ativos WHERE id = ? AND ativo = 1` inside the atomic transaction, after all other reads. Never accept `uso_atual` from the request body.

**Verification test:** Two concurrent sessions posting use increment + registro simultaneously. Only the value read inside the transaction's own `SELECT` counts.

### Pitfall 2: catalogo_plano_itens.frequencia vs catalogo_planos.frequencia null handling

**What goes wrong:** Some items have `frequencia = NULL` (uses plan default). If the handler reads `it["frequencia"]` without falling back, `json.loads(None)` raises `TypeError`.

**How to avoid:** Always `raw = it["frequencia"] or p["frequencia"]`. Guard: `if not raw: continue` (skip items with no frequency defined at either level — they are non-schedulable).

**Source:** `manutencao.py:103-104` already does this correctly; copy verbatim.

### Pitfall 3: proximo_uso column stored as TEXT (Pitfall 8 in PITFALLS.md)

**What goes wrong:** If `ativo_plano_estado.proximo_uso` is TEXT (not REAL), the comparison `uso_atual >= proximo_uso` uses lexicographic order. `'99' > '250'` evaluates as true — a machine at 99h appears VENCIDA when its next service is at 250h.

**How to avoid:** The schema DDL above declares both `ultimo_uso REAL NOT NULL` and `proximo_uso REAL NOT NULL`. Verify with `PRAGMA table_info(ativo_plano_estado)` in the migration test.

### Pitfall 4: `ON CONFLICT` requires SQLite >= 3.24

**What goes wrong:** Older SQLite (< 3.24) does not support `INSERT ... ON CONFLICT (target) DO UPDATE SET`. It raises `OperationalError`.

**How to avoid:** Python 3.8+ ships with SQLite >= 3.31. The target server runs Linux 7.0 kernel — SQLite version check: `python3 -c "import sqlite3; print(sqlite3.sqlite_version)"`. If < 3.24, fall back to explicit SELECT + INSERT/UPDATE two-step inside the same connection.

### Pitfall 5: Off-by-one when ativo has no prior ativo_plano_estado row

**What goes wrong:** For an asset with no maintenance history, computing `proximo_uso = (math.floor(uso / iv) + 1) * iv` as the "virtual" next service (same as `_vencimentos_para_ativo`) is correct for the GET display — but the POST handler should not use this virtual value. It must use `uso_no_momento + iv` (the actual meter reading at registration time).

**How to avoid:** GET and POST use different formulas:
- GET (display only): `prox = (math.floor(uso / iv) + 1) * iv` — for assets with no state, show next multiple of interval.
- POST (write): `proximo_uso = uso_no_momento + iv` — always from actual meter at registration moment.

The two values may differ if `uso_atual` is not a clean multiple of `iv`. This is correct and expected — after the first registration, the schedule anchors to the actual service moment.

### Pitfall 6: innerHTML injection in subManut() (Pitfall 6 in PITFALLS.md)

**What goes wrong:** The legacy `subManut()` (erp-manutencao.js:1891) uses template literal strings with `${p.n}` interpolated into `innerHTML`. When wiring to the backend, server-supplied `servico_nome` could contain `<script>` or `"` characters that break the rendering.

**How to avoid:** The CONTEXT.md mandates `el()/textContent` exclusively. The `registrar-uso` tab (erp-manutencao.js:1284-1560) is the reference — it uses `el()` throughout with no `innerHTML` of server data. Follow that pattern.

### Pitfall 7: Global ID collision between _mc- (old) and _mn- (new) checkbox prefixes

**What goes wrong:** The existing `subManut()` uses checkbox IDs `_mc-${p.id}` and the collection selector `._md-mc`. If the new implementation reuses these prefixes, stale event listeners or querySelector calls from the old localStorage-based `regManut` may fire alongside the new async handler.

**How to avoid:** Use `_mn-` prefix for all element IDs in the new API-wired subManut, and `._mn-cb` as the class for checkboxes. The old `regManut` handler at line 1759 uses `._md-mc:checked` — a different class, so there is no immediate collision, but the old handler must still be replaced, not supplemented.

---

## Code Examples

### Schema addition (end of data/schema_manutencao.sql)

```sql
-- Fase 02: Plano no Ativo. Aditivo — CREATE TABLE IF NOT EXISTS obrigatório.
-- Ref: Rules.md §15, CONTEXT.md Phase 2, REQUISITOS.md §3.7 (IMP-02).

CREATE TABLE IF NOT EXISTS ativo_plano_estado (
  ativo_id               TEXT    NOT NULL REFERENCES ativos(id),
  catalogo_plano_item_id INTEGER NOT NULL REFERENCES catalogo_plano_itens(id),
  ultimo_uso             REAL    NOT NULL DEFAULT 0,
  proximo_uso            REAL    NOT NULL,
  updated_at             TEXT    NOT NULL DEFAULT (datetime('now')),
  PRIMARY KEY (ativo_id, catalogo_plano_item_id)
);
CREATE INDEX IF NOT EXISTS idx_ape_ativo ON ativo_plano_estado(ativo_id);

CREATE TABLE IF NOT EXISTS manut_registros (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  ativo_id        TEXT    NOT NULL REFERENCES ativos(id),
  responsavel     TEXT    NOT NULL,
  operador        TEXT,
  data            TEXT    NOT NULL,
  uso_no_momento  REAL    NOT NULL,
  itens_json      TEXT    NOT NULL,
  observacao      TEXT,
  created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_mr_ativo ON manut_registros(ativo_id, created_at DESC);
```

### SQLite upsert for ativo_plano_estado

```python
await conn.execute(
    """INSERT INTO ativo_plano_estado
         (ativo_id, catalogo_plano_item_id, ultimo_uso, proximo_uso, updated_at)
       VALUES (?, ?, ?, ?, datetime('now'))
       ON CONFLICT (ativo_id, catalogo_plano_item_id)
       DO UPDATE SET
         ultimo_uso  = excluded.ultimo_uso,
         proximo_uso = excluded.proximo_uso,
         updated_at  = excluded.updated_at""",
    (ativo_id, item_id, uso_no_momento, uso_no_momento + iv)
)
```

### Frontend: el()-safe item row (no innerHTML of server data)

```js
function renderItemRow(item) {
  const { el } = window.engine.utils;
  const COLOR = { VENCIDA: 'red', URGENTE: 'amber', PROXIMA: 'blue', EM_DIA: 'green' };
  const cb = el('input', {
    type: 'checkbox', id: '_mn-' + item.item_id,
    class: '_mn-cb', value: String(item.item_id),
    style: { width: '14px', height: '14px', accentColor: 'var(--acc)' },
  });
  const bar = el('div', {
    style: { height: '4px', background: 'var(--bg3)', borderRadius: '3px', overflow: 'hidden', margin: '4px 0' },
  }, el('div', {
    style: { width: item.pct + '%', height: '100%', background: 'var(--' + (COLOR[item.status] === 'green' ? 'green' : COLOR[item.status] === 'red' ? 'red' : COLOR[item.status] === 'amber' ? 'amber' : 'acc') + ')', borderRadius: '3px' },
  }));
  const nome = el('div', { style: { fontSize: '12px', fontWeight: '600' } });
  nome.textContent = item.servico_nome;   // textContent, not innerHTML
  const detalhe = el('div', { style: { fontSize: '10px', color: 'var(--ink-3)', fontFamily: 'var(--font-mono)' } });
  detalhe.textContent = `A cada ${item.intervalo} ${item.unidade || 'h'} · faltam ${Math.max(0, item.falta).toFixed(0)} ${item.unidade || 'h'}`;
  return el('label', {
    id: '_mnl-' + item.item_id,
    style: { display: 'flex', gap: '9px', alignItems: 'flex-start', padding: '8px 11px',
             borderRadius: '7px', cursor: 'pointer', border: '2px solid var(--line)',
             background: 'var(--panel)', marginBottom: '6px' },
    onclick: () => {
      const lbl = document.getElementById('_mnl-' + item.item_id);
      if (lbl) lbl.style.borderColor = cb.checked ? 'var(--acc)' : 'var(--line)';
    },
  }, cb, el('div', { style: { flex: 1 } }, nome, bar, detalhe),
     window.engine.badge(item.status, COLOR[item.status]));
}
```

### Test: anti-double-count

```python
# tests/test_manutencao.py (new test case)
async def test_plano_no_ativo_anti_double_count(client, db):
    """proximo_uso = uso_no_momento_at_second_registration + intervalo (not + 2*intervalo)."""
    # Setup: ativo com uso=1000, plano com item iv=250
    ativo_id = "test-ativo-1"
    item_id = 1   # catalogo_plano_item_id seeded in fixture

    # First registration at uso=1000
    await db.execute("UPDATE ativos SET uso_atual=1000 WHERE id=?", (ativo_id,))
    r1 = client.post("/api/manutencao/registro", json={
        "ativo_id": ativo_id, "responsavel": "Técnico A", "itens": [item_id]
    }, headers={"Authorization": "Bearer test-token"})
    assert r1.status_code == 201
    estado1 = await db.fetch_one(
        "SELECT proximo_uso FROM ativo_plano_estado WHERE ativo_id=? AND catalogo_plano_item_id=?",
        (ativo_id, item_id)
    )
    assert estado1["proximo_uso"] == 1000 + 250   # = 1250

    # Second registration, usage advanced to 1100
    await db.execute("UPDATE ativos SET uso_atual=1100 WHERE id=?", (ativo_id,))
    r2 = client.post("/api/manutencao/registro", json={
        "ativo_id": ativo_id, "responsavel": "Técnico A", "itens": [item_id]
    }, headers={"Authorization": "Bearer test-token"})
    assert r2.status_code == 201
    estado2 = await db.fetch_one(
        "SELECT proximo_uso FROM ativo_plano_estado WHERE ativo_id=? AND catalogo_plano_item_id=?",
        (ativo_id, item_id)
    )
    assert estado2["proximo_uso"] == 1100 + 250   # = 1350, NOT 1000+2*250=1500
```

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|-----------------|--------|
| `ulm[pid] = h.hor` in localStorage (CMASM_Gestao_v2.html:1135) | `ativo_plano_estado` in SQLite | Multi-user; PMOC sync can read state; not lost on browser clear |
| `regManut(uid)` collects DOM checkboxes → saves to JS object | `POST /api/manutencao/registro` → atomic SQLite write | Persistent; accessible to Cronograma (Phase 5) |
| `calcProxManut()` from ERP_MANUT_MOCKS TIPOS dict (in-memory) | `GET /api/manutencao/plano-ativo` joins catalogo tables | Real plans from DB; uses actual uso_atual |

---

## Integration Points

### backend/manutencao.py

- New imports: `math`, `json` already imported at line 13-14. No new imports needed.
- `_db()`, `_require_auth()`, atomic transaction pattern (lines 27-44, 154-189): copy verbatim.
- `_vencimentos_para_ativo()` (lines 65-134): reuse the plan resolution logic (steps 1-4 of the GET handler).

### data/schema_manutencao.sql

- Append two `CREATE TABLE IF NOT EXISTS` blocks after line 19 (existing `idx_uso_registros_data` index).
- `db_core.py` already lists `schema_manutencao.sql` in `_SCHEMAS` (line 11) — no change needed.

### assets/erp-manutencao.js

- `openAtivoDrawer` (line 1721): modify `regManut` closure (lines 1755-1794) to async + API call.
- `subManut` (line 1891): replace localStorage-based rendering with async fetch + `el()` construction.
- `SUBS` map (line 1984): change `manut: subManut` to `manut: () => renderSubManut()` where `renderSubManut` is the new async wrapper that calls `subBody.replaceChildren(...)`.

### tests/

- No existing test file for Phase 2 yet. Create `tests/test_manutencao_plano_ativo.py` (or add to `test_manutencao.py` if that file exists after Phase 1 adds it).

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `catalogo_plano_itens.id` is INTEGER (AUTOINCREMENT), not UUID | Schema | `itens_json` stores wrong type; FK reference breaks |
| A2 | SQLite >= 3.24 on target system (for `ON CONFLICT ... DO UPDATE`) | POST endpoint | Need fallback SELECT+INSERT/UPDATE inside same connection |
| A3 | `window.engine.badge(label, color)` accepts `'red'|'amber'|'blue'|'green'` strings (not CSS vars) | Frontend | Badge renders without color token — cosmetic only |

A1 is verified: `schema_catalogo.sql:254`: `id INTEGER PRIMARY KEY AUTOINCREMENT`. [VERIFIED: direct file read]
A2 is probable but unverified by tool call in this session. [ASSUMED — low risk given Python 3.8+ ships 3.31+]
A3 is inferred from existing `renderVencimentos` usage at `erp-manutencao.js:527`. [VERIFIED: direct file read]

---

## Open Questions

1. **Responsável selector: static list or API-driven?**
   - Current `subManut()` (line 1910) uses a hardcoded `<option>` list.
   - The `GET /api/usuarios` endpoint exists; fetching it adds a round-trip.
   - Recommendation: keep static list for now (consistent with existing drawer), add API-driven selector in Phase 4 (Equipe Técnica).

2. **Multiple plans per asset type?**
   - If `plano_by_tipo[ativo.tipo]` returns multiple plans (e.g., two planos both applicable to `AC_SPLIT`), all their items are returned and shown in the checklist.
   - Items are grouped by plan with a section header (`plano_nome`) for clarity.
   - No decision point — this is already how `_vencimentos_para_ativo` works.

3. **Items without `por_uso` frequency?**
   - Items with `frequencia.tipo == 'por_tempo'` (date-based) are excluded from status computation (no `uso_atual` to compare against).
   - Recommendation: include them in the checklist as non-status items (show "disparo por tempo" label), allow checking and registering, but do not update `proximo_uso` for them (no numeric threshold). Add a `skip_proximo_uso` flag in `itens_validos` resolution.

---

## Sources

### Primary (HIGH confidence — direct file inspection)

- `backend/manutencao.py` (all 235 lines) — Phase 1 router; atomic pattern; `_vencimentos_para_ativo`; `_db()`, `_require_auth`
- `data/schema_manutencao.sql` (19 lines) — existing table `uso_registros`; conventions for index naming
- `data/schema_catalogo.sql` (271 lines) — `catalogo_planos`, `catalogo_plano_itens` columns and types
- `backend/db_core.py` (104 lines) — `_SCHEMAS` list (line 11); additive migration pattern; `db_path` attribute
- `backend/main.py:2527-2583` — `manutencao_vencimentos` endpoint; status computation constants
- `assets/erp-manutencao.js:1-250, 1721-2015` — `openAtivoDrawer`, `subManut`, `SUBS`, `TABS`, `regManut`
- `.docs_cmasm/referencias/CMASM_Gestao_v2.html:956-1140` — legacy `subManut()`, `regManut()`, `ulm` pattern
- `.planning/phases/02-plano-no-ativo/02-CONTEXT.md` — locked decisions
- `.planning/research/FEATURES.md` — Feature 2 analysis (`ativo_plano_estado`, `ulm` persistence)
- `.planning/research/PITFALLS.md` — Pitfalls 6, 7, 8 directly applicable
- `.planning/research/ARCHITECTURE.md` — additive migration rules; non-breaking API addition pattern

---

## Metadata

**Confidence breakdown:**
- Schema design: HIGH — types verified from existing schema files
- GET endpoint algorithm: HIGH — plan resolution logic copied from verified `_vencimentos_para_ativo`
- POST atomic transaction: HIGH — pattern is identical to Phase 1 `registrar_uso`
- Status thresholds: HIGH — constants confirmed in two separate files (main.py:2571, manutencao.py:117)
- Frontend insertion point: HIGH — `openAtivoDrawer` and `subManut` read directly

**Research date:** 2026-06-28
**Valid until:** 60 days (stable codebase, no fast-moving external dependencies)
