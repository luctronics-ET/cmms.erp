<!-- refreshed: 2026-06-28 -->
# Architecture

**Analysis Date:** 2026-06-28

## System Overview

xCMASM is a **two-tier integrated platform**: a central FastAPI backend nucleus + a single unified offline-first field app (PMOC). The architecture consolidates multiple domain categories into one codebase, eliminating separate `pmoc_*` repositories.

```text
┌──────────────────────────────────────────────────────────────────────┐
│           Frontend Layer (Browser)                                    │
├──────────────┬─────────────────────────────┬───────────────────────┤
│   cmasm_erp  │     PMOC Field App          │   Satellites          │
│  .html       │   (offline-first)           │   (xPredial, xAguada, │
│  (SPA)       │   pmoc/index.html           │    xPaiol, xCalibr.)  │
└──────┬───────┴────────────┬────────────────┴───────────────────────┘
       │                    │                        ▲
       │ Bearer token       │ Sync/manifest         │ Integration
       │ in localStorage    │ push/cursor events    │ via /api/
       ▼                    ▼                        │
┌──────────────────────────────────────────────────────────────────────┐
│        FastAPI Nucleus (backend/main.py:8010)                         │
├──────────────┬──────────────────┬──────────────────┬────────────────┤
│    Auth      │    Core Domains  │   Sync Layer     │   Static File  │
│  /api/auth   │  /api/usuarios   │  /api/sync/*     │   /assets/     │
│  (login,     │  /api/ativos     │  /api/sync/push  │   /pmoc/       │
│   logout,    │  /api/os         │  manifest        │   /static/     │
│   me)        │  /api/estoque    │  cursor          │                │
│              │  /api/grama      │  (offline sync)  │                │
│              │  /api/catalogo   │                  │                │
└──────────────┴──────────────────┴──────────────────┴────────────────┘
       │                    │                  │
       └────────────────────┴──────────────────┘
                     ▼
          ┌──────────────────────────────┐
          │   CoreDB Singleton (aiosqlite)
          │   data/core.db               │
          ├──────────────────────────────┤
          │ schema_core.sql              │
          │ schema_catalogo.sql          │
          │ schema_grama.sql             │
          └──────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| **FastAPI App** | Request routing, middleware (CORS, no-cache), static file mounting | `backend/main.py` (lines 316–346) |
| **Auth Layer** | Bearer token validation (djb2 hash), session management, login/logout | `backend/main.py` (lines 815–996) |
| **CoreDB** | Aiosqlite singleton, schema initialization, additive migrations via PRAGMA | `backend/db_core.py` |
| **Sync Router** | PMOC event ingestion (`/api/sync/push`), manifest generation, cursor tracking | `backend/sync.py` |
| **Catalogo Router** | Service catalog (serviços, planos, qualificações), material bindings | `backend/catalogo.py` |
| **Grama Router** | Lawn/vegetation control module (máquinas, áreas, operações, kanban) | `backend/grama.py` |
| **cmasm_erp.html** | Single-file browser SPA; uses SDK for all API calls; persists to localStorage | `cmasm_erp.html` |
| **xcmasm-sdk.js** | HTTP client wrapper; token/user storage in localStorage; handles offline gracefully | `assets/xcmasm-sdk.js` |
| **PMOC App** | Offline field app; categorized by domain (refrigeração, predial, paióis, grama, etc.); syncs via `/api/sync` | `pmoc/index.html` |

## Pattern Overview

**Overall:** Hub-and-spoke with offline-first field synchronization.

**Key Characteristics:**
- **Single nucleus:** One FastAPI app serves all `/api/*` routes for all domains
- **No separate module repos:** Categories (refrigeração, predial, etc.) are internal divisions of the ERP, not external integrations
- **Offline-first field app (PMOC):** Operates disconnected; syncs via HTTP push/pull with structured event payload
- **Bearer token auth:** All API clients authenticate with `Authorization: Bearer <token>`; token created at login, validated via `sessoes` table
- **Additive migrations only:** Schema changes via `PRAGMA table_info` checks before `ALTER TABLE` — never DROP
- **Global state managed:** `db` singleton initialized at startup; attached to `app` object for route handlers

## Layers

**API Layer (Routes):**
- Purpose: Expose REST endpoints for all domains (auth, users, assets, OS, inventory, grama, catalogo, sync)
- Location: `backend/main.py` + `backend/{catalogo,grama,sync}.py`
- Contains: FastAPI route handlers, Pydantic models, error responses
- Depends on: CoreDB singleton, aiosqlite
- Used by: Web frontends (cmasm_erp.html, PMOC app), external satellites (xPredial, xAguada, xPaiol, xCalibracao)

**Database Layer:**
- Purpose: Persist all core entities and audit trails
- Location: `backend/db_core.py` + `data/schema_*.sql`
- Contains: CoreDB class (async context manager wrapper), schema definitions (3 files: core, catalogo, grama)
- Depends on: aiosqlite, sqlite3 file at `DB_PATH`
- Used by: All route handlers via `await db.fetch_one()`, `await db.fetch_all()`, `await db.execute()`

**Frontend Layer (Browser):**
- Purpose: Render UI, manage user session, send/receive API calls
- Location: `cmasm_erp.html`, `pmoc/index.html`, `assets/*.js`
- Contains: HTML + vanilla JS (no build step), CSS with dark theme, SDK integration
- Depends on: xcmasm-sdk.js for API client; Leaflet for maps; pmoc-engine.js for components
- Used by: End users in browser tabs

**Static Assets:**
- Purpose: Shared JS, CSS, fonts, icons
- Location: `assets/`, `pmoc/assets/`
- Contains: xcmasm-sdk.js (shared HTTP client), pmoc-engine.js (UI components), fonts.css, xmap.js (map layers)
- Used by: All HTML frontends

## Data Flow

### Primary Request Path (User logs in → views ERP)

1. **Login:** User fills form in cmasm_erp.html; calls `sdk.auth.login(mat, senha)` → `POST /api/auth/login` (`backend/main.py` line 953)
2. **Password hash:** Backend hashes password with djb2 algorithm (line 816–823), compares against `usuarios.pw_hash`
3. **Token created:** On success, generates random token via `secrets.token_urlsafe(32)`, inserts into `sessoes` with TTL (line 969–974)
4. **Token stored:** Frontend receives token, saves to `localStorage` under `xcmasm_token` (xcmasm-sdk.js line 58)
5. **Subsequent requests:** Every API call includes `Authorization: Bearer <token>` header; backend validates via `_require_auth()` (line 826–837)
6. **Session expiry:** Tokens expire after `TOKEN_TTL_HOURS` (default 8 hours); check in `_require_auth` compares `expira_em > datetime('now')`

### PMOC Offline → Sync to Nucleus

1. **Field work:** PMOC app records events (os_criada, uso_atual_inc, estoque_mov, etc.) to IndexedDB offline
2. **Sync trigger:** User syncs (manual or auto); calls `POST /api/sync/push` with `PushIn` payload (`backend/sync.py` line 48–51)
3. **Event validation:** Each event routed to handler (e.g., `_h_uso_atual_inc`, `_h_estoque_mov`) which validates payload and applies state mutations (line 76–291)
4. **Atomic insert:** If handler returns `None`, event inserted into `sync_eventos` with `status='aplicado'`; if handler returns error string, `status='rejeitado'` + reason
5. **Response:** Nucleus returns list of applied/rejected events; PMOC marks as synced locally
6. **Manifest pull:** PMOC requests `GET /api/sync/manifest?modulo=<categoria>` to fetch current state snapshot (users, ativos, estoque, etc.)

### Preventive Maintenance Trigger

1. **Asset usage incremented:** PMOC or other module calls `POST /api/sync/push` with `uso_atual_inc` event (delta in payload)
2. **Asset updated:** Event handler increments `ativos.uso_atual` (sync.py line 92)
3. **Plan check:** Nucleus evaluates `catalogo_planos` against `uso_atual`; if `uso_atual >= proximo_uso`, alert generated (Rules.md §3)
4. **Auto-preventiva OS:** Confirming alert in UI creates `ps_criada` event with `servico_id` + materials list
5. **OS lifecycle:** On completion, `proximo_uso` reset to `uso_atual + intervalo`

**State Management:**
- **Session state:** Stored in `localStorage` on client; read into memory for duration of page load
- **Server-side state:** Persisted in SQLite; accessed via CoreDB singleton per request
- **No in-memory caches:** Each request queries DB fresh (no Redis, no module-level variables)
- **Global singleton:** `db = CoreDB(DB_PATH)` at module level in `backend/main.py` line 324

## Key Abstractions

**Event Handler Pattern:**
- Purpose: Decouples sync logic from HTTP routing; enables testable, side-effect-isolated handlers
- Examples: `backend/sync.py` lines 73–291 (`_h_uso_atual_inc`, `_h_estoque_mov`, `_h_os_executada`)
- Pattern: Each handler is `async (conn, payload) -> str | None`; returns error reason or None on success

**Pydantic Models:**
- Purpose: Validate and document API request/response shapes
- Examples: `LoginIn` (line 841), `OSIn` (line 897), `PushIn` (backend/sync.py line 48)
- Usage: Route handlers declare `body: ModelName` parameter; FastAPI auto-validates + parses JSON

**CoreDB Singleton:**
- Purpose: Provide single async context manager for all DB operations; ensure migrations run once at startup
- Usage: `await db.fetch_one(sql, params)`, `await db.fetch_all(sql, params)`, `await db.execute(sql, params)`
- Initialization: `await db.init()` called on startup (line 795); runs all schema files + additive migrations

**SDK Object (xcmasm-sdk.js):**
- Purpose: HTTP client wrapper with auto-bearer-token injection and localStorage persistence
- Usage: `const sdk = xcmasm({ baseURL: 'http://localhost:8010' }); await sdk.usuarios.list()`
- Offline handling: If fetch fails (network error), logs warning and returns null gracefully

## Entry Points

**HTTP Entry Point (Port 8010):**
- Location: `backend/main.py` line 316 (`app = FastAPI(...)`)
- Triggers: `uvicorn backend.main:app --port 8010 --reload`
- Responsibilities:
  - Initialize CoreDB + run migrations (startup event line 793–812)
  - Mount static directories: `/assets`, `/pmoc`, `/static`
  - Expose `/api/*` routes + `/` (serves cmasm_erp.html)
  - CORS middleware for external satellites

**Browser Entry Point (cmasm_erp.html):**
- Location: `/home/luc/DEV_ERP/cmasm.erp/cmasm_erp.html` (511 KB single file)
- Triggers: User navigates to `http://localhost:8010/cmasm_erp.html` (served by `@app.get("/")` line 694–696)
- Responsibilities:
  - Show login screen until authenticated
  - Initialize SDK with baseURL
  - Render ERP modules (tabs for Manutenção categorized by asset tipo, Estoque, Organização, etc.)
  - Persist user session to localStorage

**PMOC Field App Entry Point:**
- Location: `/home/luc/DEV_ERP/cmasm.erp/pmoc/index.html`
- Triggers: User navigates to `http://localhost:8010/pmoc/` (served by StaticFiles mount line 335–336)
- Responsibilities:
  - Initialize local IndexedDB for offline operation
  - Render field forms per category (refrigeração, predial, paióis, transportes, grama, elétrica, calibração)
  - Record events locally
  - Sync with nucleus on demand or schedule

## Architectural Constraints

- **Threading:** Single-threaded event loop (FastAPI + aiosqlite); async/await handles concurrency via coroutines
- **Global state:** `db` singleton module-level variable (line 324); initialized once at startup, reused for all requests
- **No module-level side effects:** Route handlers must be pure (side effects only in DB); allows testing via dependency injection of mock `db`
- **Circular imports:** Avoided by using `sys.modules["backend.main"].db` in sync.py line 23 (dynamic import to break cycle)
- **Database locks:** SQLite allows one writer at a time; aiosqlite serializes writes; large concurrent inserts may queue
- **Token expiry:** TTL checked on every authenticated request (line 836); expired sessions automatically rejected; client must re-login

## Anti-Patterns

### Hard-Coded Fixture Data in Startup

**What happens:** `_MANUT_TIPOS_PLANOS`, `_TRANSP_PLANOS`, `_COLAB_SEED_*` dicts at module level (lines 41–656) are seeded at startup if tables are empty.

**Why it's wrong:** Large fixtures make the code harder to maintain; updates to planos must be made in multiple places (dict + database); difficult to version or export canonical data.

**Do this instead:** Move seed data to CSV files in `references/` or `pmoc/seeds/`; import via a separate tool script (e.g., `tools/import_planos.py`); seed only on explicit admin command, not automatic startup.

### Event Handlers with Side Effects Beyond DB

**What happens:** `_h_os_executada` (line 227–291) modifies `estoque` + `ordens_servico` + `os_historico`; all mutations are tied to one event.

**Why it's wrong:** If one mutation fails midway, partial state is persisted; no automatic rollback in current code.

**Do this instead:** Wrap all handler side effects in explicit transaction; use `conn.execute("BEGIN TRANSACTION")` + `ROLLBACK` on error. Or use `await db.execute()` which already commits atomically.

### Additive Migrations Without Rollback Support

**What happens:** `db_core.py` lines 18–77 add columns via `ALTER TABLE` in startup; no DOWN migration.

**Why it's wrong:** If a migration fails halfway (e.g., disk full), database is left in partially-migrated state; no way to revert without manual SQL intervention.

**Do this instead:** Implement rollback migrations; track schema version in `schema_version` table; run migrations explicitly via CLI command, not automatic startup.

### Token Validation on Every Request (No Caching)

**What happens:** `_require_auth()` queries `sessoes` table for every authenticated request (line 830–834).

**Why it's wrong:** Under high load, auth queries dominate database I/O; no caching of valid sessions.

**Do this instead:** Cache valid sessions in memory (e.g., dict with TTL); invalidate cache on logout. Or use Redis for distributed caching.

## Error Handling

**Strategy:** Synchronous HTTP error responses with `detail` field; all handlers catch exceptions and return 4xx/5xx.

**Patterns:**
- **Validation errors:** FastAPI + Pydantic auto-return 422 with field errors
- **Auth errors:** 401 "Token absent", "Token invalid or expired", "User not found", "Incorrect password" (lines 827–967)
- **Not found:** 404 "Usuário não encontrado", "Refrigeração não encontrada" (lines 1027, 1121)
- **Business logic errors:** Sync event handlers return error string (e.g., "ativo desconhecido", "saldo negativo") → recorded in `sync_eventos.motivo_rejeicao`
- **Upstream proxy errors:** HTTPException 502 if xPredial unreachable (line 738)

## Cross-Cutting Concerns

**Logging:** None formal; Python `print()` or stderr only. To add: use `logging` module + inject logger into handlers.

**Validation:** 
- HTTP layer: Pydantic models enforce shape (type, required fields)
- Sync layer: Handlers validate payload (e.g., `if not isinstance(delta, (int, float))` line 81)
- No centralized validation framework

**Authentication:** Bearer token in `Authorization` header; token stored in `sessoes` table with expiry; validated before every protected route.

**Authorization (RBAC):** Users have `role` (admin, gestor, operador, visualizador) but routes do not enforce role checks; all authenticated users can call all endpoints. Can add role gates in route handlers as needed.

**Audit trail:** `os_historico` (status changes), `estoque_movimentos` (inventory moves), `sync_eventos` (PMOC events) record who did what when. No centralized audit table for other domains.

---

*Architecture analysis: 2026-06-28*
