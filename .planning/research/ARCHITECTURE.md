# Architecture Research

**Domain:** Brownfield legacy-import into single-file vanilla-JS ERP + FastAPI + SQLite
**Researched:** 2026-06-28
**Confidence:** HIGH

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│  BROWSER — cmasm_erp.html (single-file SPA, ~9000 lines, no build step) │
│                                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐  ┌───────────┐ │
│  │ Manutenção   │  │  Registrar   │  │  Sobressalentes│  │  Equipe   │ │
│  │ (tab exists) │  │  Uso (NEW)   │  │  (NEW)         │  │  (NEW)    │ │
│  └──────┬───────┘  └──────┬───────┘  └───────┬────────┘  └─────┬─────┘ │
│         │                 │                   │                 │       │
│  ┌──────┴─────────────────┴───────────────────┴─────────────────┴─────┐ │
│  │            xcmasm-sdk.js  (Bearer token, fetch wrapper)             │ │
│  └──────────────────────────────────┬──────────────────────────────────┘ │
└─────────────────────────────────────┼────────────────────────────────────┘
                                      │ HTTP + Bearer token
┌─────────────────────────────────────┼────────────────────────────────────┐
│  FastAPI Nucleus :8010              │                                     │
│                                     ▼                                    │
│  ┌──────────────┐  ┌──────────────────────────────────────────────────┐ │
│  │ Existing     │  │  New routers (additive, non-breaking)            │ │
│  │ /api/ativos  │  │  /api/ativos/{id}/uso    (registrar uso)         │ │
│  │ /api/os      │  │  /api/ativos/{id}/planos (plano-no-ativo)        │ │
│  │ /api/estoque │  │  /api/sobressalentes/*   (estoque local técnicos)│ │
│  │ /api/catalogo│  │  /api/equipe-tecnica/*   (equipe + turnos)       │ │
│  │ /api/sync    │  │  /api/cronograma/*       (cronograma preventiva) │ │
│  └──────┬───────┘  └──────────────────────────┬───────────────────────┘ │
│         │                                      │                         │
│  ┌──────┴──────────────────────────────────────┴──────────────────────┐ │
│  │              CoreDB singleton (aiosqlite, data/core.db)            │ │
│  └────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Location |
|-----------|----------------|----------|
| `cmasm_erp.html` — tab "Manutenção" | Existing maintenance panel, categorized by asset tipo | `cmasm_erp.html` (inline script) |
| New ERP section: "Registrar Uso" | Increment `ativos.uso_atual` (horímetro/odômetro) per asset; trigger preventive alert | Inline JS section in `cmasm_erp.html` |
| New ERP section: "Plano no Ativo" | Show `planos_manutencao` items for selected asset; checkboxes to select which plan items to apply | Inline JS section in `cmasm_erp.html` |
| New ERP section: "Sobressalentes" | Local technician stock separate from main `estoque`; CRUD of `sobressalentes` table | Inline JS section in `cmasm_erp.html` |
| New ERP section: "Equipe Técnica" | Manage technician teams and work shifts, feed capacity to cronograma | Inline JS section in `cmasm_erp.html` |
| New ERP section: "Cronograma" | Generate preventive maintenance schedule from plan + team capacity | Inline JS section in `cmasm_erp.html` |
| `backend/main.py` (or new `backend/manutencao.py`) | New API routes for imported features | `backend/` |
| `CoreDB` singleton | DB init, schema application, additive migrations via `PRAGMA table_info` | `backend/db_core.py` |
| `data/schema_manutencao.sql` | New tables for imported features (additive, no DROP) | `data/` |
| Legacy reference HTML | Visual source; read-only; deleted after verification | `.docs_cmasm/referencias/` |

## Recommended Project Structure

```
cmasm.erp/
├── cmasm_erp.html             # Receives new inline <section> blocks per feature
│
├── backend/
│   ├── main.py                # Import new router (manutencao_router)
│   └── manutencao.py          # NEW: /api/ativos/{id}/uso, /api/ativos/{id}/planos,
│                              #      /api/sobressalentes/*, /api/equipe-tecnica/*,
│                              #      /api/cronograma/*
│
├── data/
│   ├── schema_core.sql        # UNCHANGED (ativos.uso_atual already exists)
│   ├── schema_catalogo.sql    # UNCHANGED (planos_manutencao already exists)
│   └── schema_manutencao.sql  # NEW: sobressalentes, equipe_tecnica, equipe_turnos tables
│
├── tests/
│   └── test_manutencao.py     # NEW: pytest coverage for imported features
│
└── .docs_cmasm/referencias/   # SOURCE for visual copy; deleted at milestone end
    ├── CMASM_Gestao_v2.html   # Provides: Registrar Uso UI, Plano no Ativo, Sobressalentes
    └── cmasm13-govbr-v8_3.html # Provides: Equipe Técnica, Cronograma
```

### Structure Rationale

- **`backend/manutencao.py`:** New domain routes isolated in one file (follows existing `grama.py` / `catalogo.py` pattern). Keeps `main.py` readable. Included via `app.include_router(manutencao_router)`.
- **`data/schema_manutencao.sql`:** All new tables in one file, added to `CoreDB._SCHEMAS` list. Keeps additive migration isolated from stable schemas.
- **Inline JS sections in `cmasm_erp.html`:** Zero build-step cost. Each new feature is a self-contained `<section id="sec-FEATURE">` + supporting `<script>` block following existing patterns in the file. No module system needed.

## Architectural Patterns

### Pattern 1: Copy-Section-Wire (primary import pattern)

**What:** Extract the HTML/CSS/JS of a specific feature from the legacy file. Add it as a new section inside `cmasm_erp.html`. Replace all `localStorage` / hardcoded arrays with SDK calls to new API endpoints. Preserve the visual layout exactly.

**When to use:** Every feature import. One feature at a time.

**Trade-offs:** Safe — each import is independently shippable and verifiable. Slightly increases single-file size (already 511 KB). Avoids any build step.

**Example (Registrar Uso):**

```html
<!-- In cmasm_erp.html — add after existing Manutenção section -->
<section id="sec-uso" class="erp-section" style="display:none">
  <!-- Paste visual HTML from CMASM_Gestao_v2.html subManut/subUso -->
  <div class="tbar-title">Registrar Uso</div>
  <select id="uso-ativo-sel"><!-- populated by loadAtivos() --></select>
  <input id="uso-delta" type="number" min="0" step="0.1">
  <button onclick="registrarUso()">Registrar</button>
</section>

<script>
async function registrarUso() {
  const ativoId = document.getElementById('uso-ativo-sel').value;
  const delta   = parseFloat(document.getElementById('uso-delta').value);
  await sdk.fetch(`/api/ativos/${ativoId}/uso`, {
    method: 'POST',
    body: JSON.stringify({ delta })
  });
  await refreshAlertas();  // re-check preventive thresholds
}
</script>
```

### Pattern 2: Additive Migration (PRAGMA-guarded ALTER TABLE)

**What:** Add new tables via a new schema SQL file; add new columns to existing tables via `PRAGMA table_info`-guarded `ALTER TABLE` in `db_core.py`.

**When to use:** Every schema change in this milestone. Never DROP or recreate.

**Trade-offs:** Preserves 100% of production data. No rollback mechanism (acceptable: SQLite file is backed up before deploy). Cannot rename or remove columns (by policy).

**Example (adding `departamento` column to `ordens_servico`):**

```python
# In db_core.py CoreDB.init(), in the os_existing block:
for col, ddl in [
    # ... existing migrations ...
    ("departamento", "ALTER TABLE ordens_servico ADD COLUMN departamento TEXT"),
]:
    if col not in os_existing:
        await db.execute(ddl)
```

**Example (new `sobressalentes` table in `schema_manutencao.sql`):**

```sql
CREATE TABLE IF NOT EXISTS sobressalentes (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  codigo      TEXT UNIQUE,
  nome        TEXT NOT NULL,
  unidade     TEXT NOT NULL DEFAULT 'un',
  qtd_atual   REAL NOT NULL DEFAULT 0,
  qtd_minima  REAL NOT NULL DEFAULT 0,
  local_id    INTEGER REFERENCES locais(id),
  categoria   TEXT DEFAULT 'sobressalente',
  obs         TEXT,
  ativo       INTEGER DEFAULT 1,
  criado_em   DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_sobress_ativo ON sobressalentes(ativo);
```

### Pattern 3: Non-Breaking API Addition

**What:** Add new endpoints in a new router file; include it in `main.py`. Never remove or modify existing endpoint signatures (URL, HTTP method, required fields, response shape). New optional fields may be added to existing responses.

**When to use:** Every new endpoint. Verified by running existing pytest suite before merging each feature.

**Trade-offs:** Existing PMOC field app and external modules (xPredial, xAguada) keep working without changes. No versioning complexity needed at current scale.

**Example (new router registration):**

```python
# backend/main.py — after existing include_router calls
from .manutencao import router as manutencao_router
app.include_router(manutencao_router)
```

### Pattern 4: Independent-Shippable Feature Slice

**What:** Each legacy feature is a vertical slice: schema SQL + backend route + frontend section + test. Ship one slice at a time. Verify in production before starting the next.

**When to use:** Entire milestone. Enforces the "aos poucos" constraint.

**Trade-offs:** Requires discipline — resist merging multiple slices at once. Pays off by keeping production stable between each import.

## Data Flow

### Registrar Uso (incremento de uso_atual)

```
User picks asset + enters delta (h or km)
    ↓
POST /api/ativos/{id}/uso  { delta: float }
    ↓
backend: validate delta > 0
         UPDATE ativos SET uso_atual = uso_atual + delta WHERE id = ?
         SELECT planos where ativo_id=? and proxima_execucao is evaluable
         → if uso_atual >= threshold: return { alerta: true, plano_id: ... }
    ↓
Frontend: if alerta → show confirmation → POST /api/os (preventiva OS)
```

### Plano no Ativo (checkboxes)

```
User selects asset in Manutenção tab
    ↓
GET /api/ativos/{id}/planos
    ↓ returns: planos_manutencao rows joined with catalogo_servicos
Frontend renders checklist (checkbox per plano item, style from legacy)
User checks items → clicks "Registrar Manutenção"
    ↓
POST /api/os  { tipo: 'preventiva', ativo_id, servico_id, ... }
    (reuses existing OS creation endpoint — no contract change)
```

### Sobressalentes (estoque local)

```
GET /api/sobressalentes          → list all (ativo=1)
POST /api/sobressalentes         → create item
PUT /api/sobressalentes/{id}     → update (name, qty, threshold)
POST /api/sobressalentes/{id}/ajuste  { delta, tipo, obs }  → stock movement
    ↓
INSERT INTO sobressalentes_movimentos (...)
UPDATE sobressalentes SET qtd_atual = qtd_atual + delta
```

### Equipe Técnica + Cronograma

```
GET /api/equipe-tecnica          → list teams + shifts
POST /api/equipe-tecnica         → create team
PUT /api/equipe-tecnica/{id}     → update shifts / nº equipes

GET /api/cronograma              → calculated schedule
    backend: 1. fetch all planos_manutencao with proxima_execucao
             2. fetch equipe capacity (turnos, h/dia/equipe from CMASM formula)
             3. order by criticidade DESC
             4. assign slots greedily
             5. return ordered list: { ativo, servico, data_prevista, equipe_id }
```

### State Management

- All persistent state in SQLite via FastAPI. No localStorage for new features (unlike the legacy files).
- Frontend reads state fresh on tab activation (GET call), displays, user acts, POST/PUT, re-fetches.
- No in-memory cache on server (consistent with existing pattern).

### Key Data Flows

1. **Uso delta → preventive alert:** `ativos.uso_atual` is the single source of truth; `planos_manutencao.proxima_execucao` or `frequencia` JSON drives threshold comparison.
2. **Plano item selection → OS creation:** Reuses `POST /api/os` contract; no new endpoint needed for OS creation itself.
3. **Cronograma capacity:** `equipe_tecnica` provides `h_dia_equipe`; formula mirrors legacy JS (`horasPorDiaEquipe()` from `cmasm13-govbr-v8_3.html`).

## Component Boundaries for Each Imported Feature

### Feature 1: Registrar Uso

| Layer | What | Notes |
|-------|------|-------|
| Frontend | Section + form in `cmasm_erp.html`; asset selector + delta input + submit | Port visual from `CMASM_Gestao_v2.html` `subUso()` |
| Backend | `POST /api/ativos/{id}/uso` in `manutencao.py` | Validates delta, updates `ativos.uso_atual`, evaluates plan thresholds |
| DB | `ativos.uso_atual` already exists; no new table needed | New column `ativos.ultima_leitura_uso` (datetime) via PRAGMA-guarded ALTER if wanted |
| Depends on | `ativos` table, `planos_manutencao` table | Both exist; read-only from catalogo |
| Enables | Preventive OS auto-dispatch (`por_uso` trigger, Rules.md §3) | |

### Feature 2: Plano no Ativo (checkboxes)

| Layer | What | Notes |
|-------|------|-------|
| Frontend | Sub-tab "Manutenção" in unit detail; checklist of plan items | Port `subManut()` + `toggleMC()` from `CMASM_Gestao_v2.html` |
| Backend | `GET /api/ativos/{id}/planos` in `manutencao.py` | Returns `planos_manutencao JOIN catalogo_servicos` for the asset |
| DB | No new table; reads `planos_manutencao` + `catalogo_servicos` | Both exist in `schema_catalogo.sql` |
| Depends on | Feature 1 (uso_atual populated) | Plan thresholds only meaningful when uso_atual is tracked |
| Enables | OS creation prefilled with selected services | |

### Feature 3: Sobressalentes

| Layer | What | Notes |
|-------|------|-------|
| Frontend | New ERP tab "Sobressalentes"; CRUD list + adjustment modal | Port `renderEstoque()` from `CMASM_Gestao_v2.html` |
| Backend | `GET/POST /api/sobressalentes`, `PUT /api/sobressalentes/{id}`, `POST /api/sobressalentes/{id}/ajuste` in `manutencao.py` | Separate from main `estoque` — these are technician local parts |
| DB | New table `sobressalentes` + `sobressalentes_movimentos` in `schema_manutencao.sql` | Do NOT overload existing `estoque` table; keep concerns separate |
| Depends on | Nothing (standalone feature) | Can be shipped independently |
| Enables | Local parts tracking without polluting main warehouse stock | |

### Feature 4: Equipe Técnica

| Layer | What | Notes |
|-------|------|-------|
| Frontend | New ERP tab "Equipe Técnica"; team config + person list | Port team config card from `cmasm13-govbr-v8_3.html` (`renderTeam()`) |
| Backend | `GET/POST/PUT /api/equipe-tecnica` in `manutencao.py` | Stores team config (nº equipes, turnos, h/dia) |
| DB | New tables `equipe_tecnica` + `equipe_turnos` in `schema_manutencao.sql` | Mirrors legacy `TEAM` object: equipes, diasSemana, turnos array |
| Depends on | `usuarios` table (to link technicians to teams) | |
| Enables | Feature 5 (Cronograma) — capacity calculation feeds the schedule | |

### Feature 5: Cronograma Preventivo

| Layer | What | Notes |
|-------|------|-------|
| Frontend | Sub-tab "Cronograma" in Manutenção panel; table of scheduled items | Port `pmocCronograma()` from `cmasm13-govbr-v8_3.html` |
| Backend | `GET /api/cronograma` in `manutencao.py`; query param `?modulo=refrigeracao` etc. | Pure read; calculates from DB state; returns sorted schedule |
| DB | Reads `planos_manutencao`, `ativos`, `equipe_tecnica`; no new table | `proxima_execucao` in `planos_manutencao` is the scheduling anchor |
| Depends on | Features 1, 2, 4 (uso populated, plans bound, team capacity known) | Ship last in sequence |
| Enables | Full preventive maintenance visibility and capacity planning | |

## Build Order with Dependencies

Sequence is chosen so each step is independently shippable and verifiable in production:

```
Phase 1: Schema + backend skeleton
    Create schema_manutencao.sql (sobressalentes, equipe_tecnica tables)
    Add to CoreDB._SCHEMAS list → runs at next startup (additive, safe)
    Create backend/manutencao.py with stubs → include_router in main.py
    Run existing pytest suite → must still be 100% green

Phase 2: Feature A — Registrar Uso  [no new tables needed]
    Backend: POST /api/ativos/{id}/uso
    Frontend: port subUso() section from CMASM_Gestao_v2.html
    Test: test_manutencao.py::test_registrar_uso
    Verify in browser; check uso_atual increments in DB
    Ship ✓

Phase 3: Feature B — Plano no Ativo  [depends on: planos_manutencao populated]
    Backend: GET /api/ativos/{id}/planos
    Frontend: port subManut() + toggleMC() checklist
    Test: test_manutencao.py::test_plano_no_ativo
    Ship ✓

Phase 4: Feature C — Sobressalentes  [independent]
    Backend: full CRUD + ajuste endpoint
    Frontend: port renderEstoque() as new tab
    Test: test_manutencao.py::test_sobressalentes
    Ship ✓

Phase 5: Feature D — Equipe Técnica  [depends on: usuarios table]
    Backend: CRUD equipe-tecnica
    Frontend: port renderTeam() as new tab
    Test: test_manutencao.py::test_equipe_tecnica
    Ship ✓

Phase 6: Feature E — Cronograma  [depends on: A+B+D]
    Backend: GET /api/cronograma (capacity calc)
    Frontend: port pmocCronograma()
    Test: test_manutencao.py::test_cronograma
    Ship ✓

Phase 7: Residuais funcionais (after all imports verified)
    departamento column on ordens_servico
    por_tempo trigger (data/última execução)
    SR prefill ativo+item from servico context
    local_id religar ativos não-climatização

Phase 8: Segurança mínima
    Replace djb2 with bcrypt (backend/main.py auth)
    Remove default password seed (1234 → force reset on first login)

Phase 9: Legacy cleanup (see below)
```

## Additive Migration + Data-Preservation Approach

### Rules (non-negotiable)

1. **Always `PRAGMA table_info` before `ALTER TABLE`.** Never run `ALTER TABLE` unconditionally. Pattern:
   ```python
   existing = {row[1] async for row in await db.execute("PRAGMA table_info(table_name)")}
   for col, ddl in [("new_col", "ALTER TABLE t ADD COLUMN new_col TEXT")]:
       if col not in existing:
           await db.execute(ddl)
   ```

2. **New tables use `CREATE TABLE IF NOT EXISTS`.** Safe to run on every startup.

3. **New schema files added to `CoreDB._SCHEMAS` list only.** Never modify existing `.sql` files to add tables — create a new file.

4. **No `DROP`, no `CREATE OR REPLACE`, no `RENAME`.** If renaming is needed, add a new column and migrate data in a one-time script under `tools/`.

5. **Backup before first deploy.** `cp data/core.db data/core.db.bak-$(date +%Y%m%d)` before any schema-changing deploy.

6. **Idempotent seeds.** Any seed data inserted at startup checks for existing rows first (`SELECT COUNT(*)` guard), consistent with `_seed_colab_if_empty()` pattern.

### What to preserve

| Data | Table | Risk | Mitigation |
|------|-------|------|------------|
| 171 refrigeration machines | `ativos` + `pmoc_refrigeracao` | ALTER TABLE adds columns, existing rows get NULL for new cols | Safe — new cols are nullable or have defaults |
| Work orders, history | `ordens_servico`, `os_historico` | New `departamento` column | PRAGMA guard; existing rows get NULL |
| Service catalog + plans | `catalogo_servicos`, `planos_manutencao` | No changes to these tables in this milestone | Safe |
| User sessions | `sessoes` | bcrypt migration requires pw_hash column change | Do NOT alter column type; add `pw_bcrypt` column, migrate progressively |
| Inventory | `estoque`, `estoque_movimentos` | Sobressalentes is a separate new table | No risk to existing estoque data |

## End-of-Milestone Legacy Cleanup

### When to delete legacy reference files

**Precondition:** All five features are verified in production (browser test + pytest green). Delete only after explicit sign-off per feature.

### Safe deletion pattern

```bash
# 1. Create a final git tag before deletion (checkpoint)
git tag milestone-import-verified

# 2. Remove legacy reference files
git rm .docs_cmasm/referencias/CMASM_Gestao_v2.html
git rm .docs_cmasm/referencias/cmasm13-govbr-v8_3.html
# Remove any other referencias/ files confirmed no longer needed:
git rm .docs_cmasm/referencias/ativo-template.html
git rm .docs_cmasm/referencias/pmoc-equipe-tecnica.html
git rm .docs_cmasm/referencias/pmoc-2a-ficha-ambiente.html
git rm .docs_cmasm/referencias/pmoc-2b-equipamento-refrig.html
git rm .docs_cmasm/referencias/pmoc-ocupante.html

# 3. Commit with explicit rationale
git commit -m "cleanup: remove legacy reference HTMLs — features verified in production"
```

### What NOT to delete

- `ata2_carioca_solution.html` — keep if still referenced for service catalog seeding
- `cmasm_backup.json` — production data snapshot; keep in `.docs_cmasm/` as archive
- Map files (`.osm`) — used by xmap; keep

### Code hygiene after import

Once a feature section is live in `cmasm_erp.html` and wired to the API:
- Remove any vestigial `localStorage` reads/writes from the ported JS (the legacy files used localStorage; the ERP must use the API).
- Remove any inline fixture arrays copied from the legacy (those were the legacy's DB substitute).
- Run a grep for `localStorage.setItem` / `localStorage.getItem` in the new sections to confirm none remain for feature data.

## Anti-Patterns

### Anti-Pattern 1: Porting localStorage logic as-is

**What people do:** Copy the `saveState()` / `loadState()` JS from the legacy file into the ERP without replacing with API calls.

**Why it's wrong:** Data lives in the browser only; not persisted to `core.db`; invisible to PMOC, other users, and reports. Breaks the "data in production" requirement.

**Do this instead:** Identify every `localStorage.setItem(SK, ...)` → replace with `await sdk.fetch('/api/...', { method: 'POST', ... })`. Identify every `localStorage.getItem` → replace with `await sdk.fetch('/api/...')`.

### Anti-Pattern 2: Modifying existing endpoint responses without versioning

**What people do:** Add required fields to existing JSON responses (e.g., add `departamento` to `GET /api/os` response with a non-null constraint).

**Why it's wrong:** PMOC field app and external satellites consume `GET /api/os`. Required new fields without defaults break their parsers.

**Do this instead:** All new response fields must be optional (nullable). New endpoints are additive. Existing endpoint schemas are read-only.

### Anti-Pattern 3: Putting all five features in one giant PR

**What people do:** Port all features at once to "save time", ship together.

**Why it's wrong:** One regression breaks all five. Impossible to bisect. Production is broken during the entire multi-week effort instead of only a few hours per feature.

**Do this instead:** One feature slice per commit/PR. Verify in production. Proceed.

### Anti-Pattern 4: Merging sobressalentes into existing estoque table

**What people do:** Add a `tipo = 'sobressalente'` category to the existing `estoque` table to avoid a new table.

**Why it's wrong:** `estoque` rows are debited when OS is concluded (idempotent logic in `_h_os_executada`). Sobressalentes are technician local stock managed separately. Mixing them corrupts main warehouse accounting.

**Do this instead:** Separate `sobressalentes` table. If cross-referencing is needed later (e.g., restock from main warehouse), model as an explicit `estoque_movimentos` transfer, not by merging tables.

### Anti-Pattern 5: Running DROP on startup for "clean" migration

**What people do:** `DROP TABLE IF EXISTS planos_manutencao; CREATE TABLE planos_manutencao (...)` to add a column cleanly.

**Why it's wrong:** Destroys all plan data in production. SQLite does not support `ADD COLUMN` for all types, but standard column additions (TEXT, REAL, INTEGER with defaults or nullable) are always safe.

**Do this instead:** `ALTER TABLE ... ADD COLUMN` guarded by `PRAGMA table_info`. Accept that old NULL rows will exist — handle in application logic.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| PMOC field app | Reads `GET /api/sync/manifest`, posts `POST /api/sync/push` | New features do NOT add sync events in this milestone; PMOC sync contract unchanged |
| xPredial, xAguada, xPaiol | Read `GET /api/usuarios`, `GET /api/estrutura`, POST `POST /api/os` | `POST /api/os` gains optional new fields (`departamento`, `ativo_id`); backwards compatible |
| xCFTV, xFonoclama | No API contract with nucleus | Unaffected |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `erp-manutencao.js` ↔ new sections | Shared `window.sdk` object; no direct function calls across sections | Each section is self-contained |
| `manutencao.py` ↔ `db` singleton | Same `await db.fetch_*()` pattern as all other routers | Import `db` via `sys.modules["backend.main"].db` to avoid circular import (established pattern) |
| `schema_manutencao.sql` ↔ `CoreDB._SCHEMAS` | Added to list in `db_core.py`; executed at startup | File must use `CREATE TABLE IF NOT EXISTS` throughout |
| Cronograma ↔ `planos_manutencao` | Read-only join; cronograma never writes to planos | Separation maintained |

## Sources

- Codebase analysis: `backend/db_core.py`, `data/schema_core.sql`, `data/schema_catalogo.sql`, `backend/main.py` (lines 1–346)
- Legacy UI analysis: `.docs_cmasm/referencias/CMASM_Gestao_v2.html` (1495 lines), `.docs_cmasm/referencias/cmasm13-govbr-v8_3.html` (3298 lines)
- Project context: `.planning/PROJECT.md`, `.planning/codebase/ARCHITECTURE.md`, `.planning/codebase/STRUCTURE.md`
- Domain rules: `CLAUDE.md`, `Rules.md` (referenced, not re-read)
- Confidence: HIGH — based on direct codebase inspection; no external web research required for this brownfield pattern

---
*Architecture research for: xCMASM ERP legacy import milestone*
*Researched: 2026-06-28*
