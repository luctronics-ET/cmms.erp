<!-- GSD:project-start source:PROJECT.md -->

## Project

**xCMASM ERP**

Plataforma modular de gestão de ativos e serviços do CMASM (Centro de Mísseis e Armas Submarinas), instalação naval brasileira. Núcleo = backend FastAPI + ERP web single-file (`cmasm_erp.html`) com Manutenção categorizada por tipo de ativo, integrado a um PMOC único offline-first (`pmoc/`) que sincroniza via API. Uso interno por técnicos e gestores da Divisão de Manutenção.

**Core Value:** A gestão de manutenção (ativos → planos → OS → estoque) tem que funcionar de ponta a ponta com os dados reais já cadastrados; nada deste milestone pode quebrar o que já roda em produção.

### Constraints

- **Tech stack**: manter FastAPI + aiosqlite + SQLite + ERP vanilla JS single-file + PMOC offline-first. Sem novo framework.
- **Compatibilidade**: PMOC app de campo e módulos externos consomem `GET /api/usuarios` e `POST /api/os` — não quebrar contratos de API existentes.
- **Dados**: produção-first — preservar dados existentes; imports idempotentes e não-destrutivos.
- **Arquitetura**: refatorar só onde dói (cirúrgico por padrão; modularizar pontos críticos quando justificar).
- **Design**: tema dark obrigatório, JetBrains Mono + DM Sans (tokens em CLAUDE.md); reaproveitar layout legado já aprovado.
- **Segurança**: somente o mínimo barato neste milestone (bcrypt + sem senha default).

<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->

## Technology Stack

## Languages

- Python 3.7+ - Backend (FastAPI core, database migrations, seed scripts)
- JavaScript (vanilla) - Frontend (no build step, single-file HTML apps + SDK)
- SQL (SQLite) - Database schema definitions in `data/*.sql`
- HTML5 - Static templates for ERP and PMOC field app
- CSS3 - Styling (dark theme, self-hosted fonts)

## Runtime

- Python 3.7+ (development and production)
- Node.js / npm (optional, for ESLint only — no build pipeline required)
- pip (Python dependencies from `requirements.txt`)
- npm (dev dependencies for ESLint — see `package.json`)
- Lockfile: `requirements.txt` present; no `package-lock.json` (minimal npm usage)

## Frameworks

- FastAPI 0.115.0 - REST API framework (async, production-grade)
- Uvicorn 0.30.6 (with [standard] extras) - ASGI server for FastAPI
- Vanilla JavaScript (no React, Vue, or build framework on core ERP)
- Leaflet 1.9.4 - Map library (loaded via CDN from unpkg.com)
- SQLite (aiosqlite 0.20.0) - Embedded relational database
- No ORM — raw SQL with parameter binding via aiosqlite
- ESLint 10.2.1 - JavaScript linting (dev dependency in `package.json`)
- No pytest or test runner configured — tests are manual or integration-based
- No build step for core ERP — files served as-is
- Uvicorn with `--reload` flag for hot-reload during development
- Python tools in `tools/` for seeding and migrations (not build-time)

## Key Dependencies

- fastapi==0.115.0 - Web framework, request routing, validation, OpenAPI docs
- aiosqlite==0.20.0 - Async SQLite driver (enables non-blocking DB operations)
- uvicorn[standard]==0.30.6 - ASGI server (includes uvloop for performance)
- pydantic==2.7.4 - Data validation, serialization (request bodies, responses)
- python-multipart==0.0.9 - Multipart form parsing (file uploads in POST requests)
- aiofiles - Async file I/O (not directly used, but listed; may support future uploads)
- httpx==0.27.2 - Async HTTP client (used for proxying xPredial requests, health checks on satellites)

## Configuration

- `.env` file (not committed — see `.env.example` for template)
- Key variables: `DB_PATH`, `TOKEN_TTL_HOURS`, `CORS_ORIGINS`, `XPREDIAL_URL`, `XAGUADA_URL`, `XPAIOL_URL`, `XCALIBRACAO_URL`
- `TELEGRAM_BOT_TOKEN` loaded via `tools/telegram_spike.py` (optional integration)
- Defaults in code ensure app runs offline: e.g., `DB_PATH` defaults to `./data/core.db`
- `backend/main.py` - No compilation; FastAPI serves HTML + API routes directly
- Static files mounted from `assets/` and `pmoc/` directories
- Cache-control middleware prevents serving stale HTML/JS (line 344–346 in `backend/main.py`)

## Platform Requirements

- Python 3.7+, pip
- Git (for version control)
- Text editor or IDE (any; no build config required)
- HTTP server for static files (e.g., `npx serve .`, `python -m http.server`)
- Optional: Node.js 18+ (if running ESLint)
- Python 3.7+ runtime
- Uvicorn server (via pip install)
- SQLite (embedded; no separate database installation)
- Reverse proxy (e.g., nginx) recommended for SSL/TLS
- Environment variables set at deployment (DB_PATH, CORS_ORIGINS, satellite URLs)

## Frontend Assets

- `xcmasm-sdk.js` - Shared REST client SDK (used by all HTML modules)
- `pmoc-engine.js` - UI components library for PMOC field app
- `erp-module-shell.css` - Shared layout/theme CSS
- `fonts/` - Self-hosted woff2 files: JetBrains Mono (data/code), DM Sans (UI)
- `fonts.css` - Font face declarations (fallback to Google Fonts CDN if offline)
- Leaflet CSS served via CDN (unpkg.com)
- `cmasm_erp.html` - Main ERP single-file app (root `/`)
- `pmoc/index.html` - PMOC field app (mounted at `/pmoc/`)

## Database

- File-based: `./data/core.db` (created on first init)
- Schemas in `data/schema_*.sql`:
- Additive only — uses `PRAGMA table_info()` to check before `ALTER TABLE`
- Never drops columns/tables (Rule in Rules.md §9)
- Executed at startup in `backend/main.py` `startup()` event

## API

- `/` - Serves `cmasm_erp.html` (main ERP)
- `/pmoc/` - Serves PMOC field app (static files)
- `/assets/*` - Static assets (SDK, CSS, fonts)
- `/api/*` - REST endpoints (auth, users, assets, inventory, work orders, sync, etc.)
- `/docs` - FastAPI OpenAPI documentation
- Bearer token scheme (JWT-style tokens stored in `sessoes` table)
- Password hash: djb2 algorithm (hexadecimal format, backward-compatible with legacy ERP_core)
- Token TTL: configured via `TOKEN_TTL_HOURS` env var (default 8 hours)

<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->

## Conventions

## Naming Patterns

- Python files (backend): snake_case — `db_core.py`, `catalogo.py`, `sync.py`, `grama.py`
- JavaScript files (frontend/assets): kebab-case or snake_case — `xcmasm-sdk.js`, `pmoc-engine.js`, `erp-manutencao.js`, `tbl-enhance.js`, `xmap-layers-grama.js`
- HTML files: lowercase, descriptive — `cmasm_erp.html` (main ERP), `index.html` (PMOC), `CLAUDE.md` (developer guidance)
- SQL schema files: snake_case with `schema_` prefix — `schema_core.sql`, `schema_catalogo.sql`, `schema_grama.sql`
- Python: snake_case for all functions and methods — `_require_auth()`, `_db()`, `_new_uuid()`, `_utc_now()`, `fetch_one()`, `fetch_all()`
- JavaScript: camelCase for functions and methods — `getAtivos()`, `criarUsuario()`, `atualizarLocal()`, `resolveTipoCodigo()`, `getMH()` (get/set/create/update prefixes common)
- Private functions prefixed with `_` in both Python and JavaScript — `_req()` in `xcmasm-sdk.js`, `_seed_user()` in tests
- Python: snake_case — `db_path`, `user_id`, `last_sync`, `estado_operacional`
- JavaScript: camelCase — `state`, `cache`, `activeTab`, `tabDirty`, `catsAvailable`, `isInitialized`
- Constants (JavaScript): UPPER_SNAKE_CASE — `TOKEN_KEY`, `USER_KEY`, `LS_KEY`, `VERSION`, `TAB_DEFS`, `CAT_DBCATS`
- State objects use descriptive lowercase keys — `{ hor: 0, regs: [], manut: [], ulm: {} }` in localStorage structures
- PascalCase for all Pydantic models — `ServicoIn`, `PlanoIn`, `QualificacaoIn`, `UsuarioQualificacaoIn`
- Model suffixes: `In` for input validation models, no suffix for output/response models
- Enum-like constants: descriptive strings — `escopo` accepts `"central"` or `"local"`, `status` accepts `"valida"` | `"vencida"` | `"suspensa"`

## Code Style

- **Python:** 4-space indentation (PEP 8 compliant). Line length implicit soft limit ~100 chars. Imports organized: stdlib, third-party, local (no enforcement tool detected).
- **JavaScript:** 2-space indentation (vanilla JS, no build step). Single quotes preferred in code, but double quotes for HTML attributes. No semicolon rule strictly enforced (mixed style observed).
- **HTML/CSS:** 2-space indentation. CSS custom properties (design tokens) prefixed with `--` for theme values (`--bg`, `--bg2`, `--acc`, `--ok`, `--warn`, `--danger`).
- No ESLint or Prettier detected. JavaScript relies on smoke tests (`test_manutencao_smoke.py`) that verify brace balance in `.js` files.
- Python has no formal linter configured; relies on Pydantic validation and test suite for correctness.
- Python files: Module-level docstrings describing purpose and key references to domain docs (e.g., `"""API de Catálogo de Serviços...\n\nReferências: Rules.md §§10-15"""`).
- Function docstrings: Brief purpose. Example: `"""Verifica balanço de chaves/parênteses/colchetes ignorando strings e comentários."""`
- Inline comments: Explanatory for complex logic. Prefixed with `# ` on own line or inline after code.
- JavaScript: JSDoc comments rare; header comments in modules describe purpose and usage. Example: `/**\n * xcmasm-sdk.js — SDK compartilhado...\n */`
- PT-BR language used in docstrings and comments throughout both backend and frontend.

## Import Organization

- No formal import system (vanilla JS, file:// breaks fonts). Scripts loaded inline in HTML `<head>/<body>` in dependency order:
- No path aliases or resolveAlias detected in TypeScript or JavaScript.
- All paths are relative or absolute URLs served by FastAPI.

## Error Handling

- Errors raised as `HTTPException(status_code, detail_message)` — always include a human-readable `detail` string.
- Pydantic validation errors trigger `ValueError` in `@field_validator` methods; FastAPI converts to 422 response automatically.
- Pattern in `catalogo.py`:
- Try-catch for type coercion in CRUD operations (parsing incoming JSON to Python types).
- Errors caught in fetch responses: `.catch(() => ({ detail: res.statusText }))` — always fall back to a `detail` field.
- Offline resilience: when xCore is unreachable, SDK logs warning and returns `null` (no throw).
- Pattern in `xcmasm-sdk.js`:
- Module-level error logging: `console.warn()` for expected conditions (offline, migrations failing), `console.error()` for assertions.

## Logging

- **JavaScript:** Prefixed log messages with module name in brackets — `[xcmasm-sdk]`, `[manut]`, `[xMap]`, `[refrig-engine]` — to identify source in browser DevTools.
- **Python:** Not observed in current codebase; tests use assertions and fixtures for visibility.
- **When to log:**

## Comments

- Complex business logic: Explain *why*, not *what*. Example: `// categoria de navegação → categoria(s) de ativos no DB` links UI tabs to database categories.
- Non-obvious conditionals: `// Visitante mode — hide write actions` explains the intent behind CSS selectors.
- Migration references: Point to authoritative docs. Example: `# núcleo magro v2 — campos exigidos pelo motor de manutenção (Rules.md §15)`.
- Do NOT comment obvious code (`// increment i` is redundant).
- Minimal usage observed. Module-level JSDoc headers document purpose, params, and return type for exported functions.
- Example from `pmoc-engine.js`:
- Pydantic models in Python use brief inline docstrings:

## Function Design

- Python: Functions range 5–50 lines typical. Complex CRUD operations split into helpers (e.g., `_seed_user()`, `_auth()` in tests).
- JavaScript: Utility functions 10–30 lines; component factories (header, modal) 30–80 lines. Event handlers inline or delegated to dispatcher.
- Python: Explicit keyword arguments for Pydantic models. Optional types marked `Optional[Type]`. Defaults specified in class definitions.
- JavaScript: Options objects passed as second parameter to component constructors.
- Python: Explicit type hints on all functions. `dict | None` for fetch operations; `int` for lastrowid; `list[dict]` for query results.
- JavaScript: Component functions return API objects with `.update()`, `.destroy()`, `.element` properties.

## Module Design

- No module.exports; functions and objects attached to `window` object or returned from IIFE.
- Pattern: `(function (global) { ... global.xcmasm = xcmasm; ... })(window);` or `window.ERP_MANUT = { init, ... };`
- Shared SDK accessible as `window.xcmasm({ baseURL: '...' })`.
- Not used in this codebase. Python imports from modules directly (`from .db_core import`, `from .catalogo import router`).

## Database Patterns

- No ORM. All queries are raw SQL strings passed to `db.execute()`, `db.fetch_one()`, `db.fetch_all()`.
- SQL parameterization required: `db.execute(sql, params)` — never string interpolation.
- Row factory: `db.row_factory = aiosqlite.Row` converts rows to dict-like objects.
- Connection management: Each operation opens its own connection; no connection pooling configured.
- Additive only. Schema changes use `PRAGMA table_info(table_name)` to check column existence before `ALTER TABLE ADD COLUMN`.
- Example from `db_core.py`:

## Design System

- All pages must declare `data-theme="light"` or `data-theme="dark"` on `<html>`.
- CSS custom properties defined per theme:
- Primary: **JetBrains Mono** (code, mono elements) — self-hosted woff2 in `assets/fonts/`
- Secondary: **DM Sans** (UI text, labels) — fallback to generic sans-serif
- Import via `assets/fonts.css` or Google Fonts CDN as fallback
- Example from `cmasm_erp.html`:
- Modular CSS classes with `pe-` prefix (pmoc-engine components) — `pe-header`, `pe-badge`, `pe-modal`.
- Module-specific prefixes: `sb-` (sidebar), `ni-` (nav item), `topbar-`.
- No Tailwind or utility CSS. Semantic class names tied to specific component purposes.

<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->

## Architecture

## System Overview

```text

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

- **Single nucleus:** One FastAPI app serves all `/api/*` routes for all domains
- **No separate module repos:** Categories (refrigeração, predial, etc.) are internal divisions of the ERP, not external integrations
- **Offline-first field app (PMOC):** Operates disconnected; syncs via HTTP push/pull with structured event payload
- **Bearer token auth:** All API clients authenticate with `Authorization: Bearer <token>`; token created at login, validated via `sessoes` table
- **Additive migrations only:** Schema changes via `PRAGMA table_info` checks before `ALTER TABLE` — never DROP
- **Global state managed:** `db` singleton initialized at startup; attached to `app` object for route handlers

## Layers

- Purpose: Expose REST endpoints for all domains (auth, users, assets, OS, inventory, grama, catalogo, sync)
- Location: `backend/main.py` + `backend/{catalogo,grama,sync}.py`
- Contains: FastAPI route handlers, Pydantic models, error responses
- Depends on: CoreDB singleton, aiosqlite
- Used by: Web frontends (cmasm_erp.html, PMOC app), external satellites (xPredial, xAguada, xPaiol, xCalibracao)
- Purpose: Persist all core entities and audit trails
- Location: `backend/db_core.py` + `data/schema_*.sql`
- Contains: CoreDB class (async context manager wrapper), schema definitions (3 files: core, catalogo, grama)
- Depends on: aiosqlite, sqlite3 file at `DB_PATH`
- Used by: All route handlers via `await db.fetch_one()`, `await db.fetch_all()`, `await db.execute()`
- Purpose: Render UI, manage user session, send/receive API calls
- Location: `cmasm_erp.html`, `pmoc/index.html`, `assets/*.js`
- Contains: HTML + vanilla JS (no build step), CSS with dark theme, SDK integration
- Depends on: xcmasm-sdk.js for API client; Leaflet for maps; pmoc-engine.js for components
- Used by: End users in browser tabs
- Purpose: Shared JS, CSS, fonts, icons
- Location: `assets/`, `pmoc/assets/`
- Contains: xcmasm-sdk.js (shared HTTP client), pmoc-engine.js (UI components), fonts.css, xmap.js (map layers)
- Used by: All HTML frontends

## Data Flow

### Primary Request Path (User logs in → views ERP)

### PMOC Offline → Sync to Nucleus

### Preventive Maintenance Trigger

- **Session state:** Stored in `localStorage` on client; read into memory for duration of page load
- **Server-side state:** Persisted in SQLite; accessed via CoreDB singleton per request
- **No in-memory caches:** Each request queries DB fresh (no Redis, no module-level variables)
- **Global singleton:** `db = CoreDB(DB_PATH)` at module level in `backend/main.py` line 324

## Key Abstractions

- Purpose: Decouples sync logic from HTTP routing; enables testable, side-effect-isolated handlers
- Examples: `backend/sync.py` lines 73–291 (`_h_uso_atual_inc`, `_h_estoque_mov`, `_h_os_executada`)
- Pattern: Each handler is `async (conn, payload) -> str | None`; returns error reason or None on success
- Purpose: Validate and document API request/response shapes
- Examples: `LoginIn` (line 841), `OSIn` (line 897), `PushIn` (backend/sync.py line 48)
- Usage: Route handlers declare `body: ModelName` parameter; FastAPI auto-validates + parses JSON
- Purpose: Provide single async context manager for all DB operations; ensure migrations run once at startup
- Usage: `await db.fetch_one(sql, params)`, `await db.fetch_all(sql, params)`, `await db.execute(sql, params)`
- Initialization: `await db.init()` called on startup (line 795); runs all schema files + additive migrations
- Purpose: HTTP client wrapper with auto-bearer-token injection and localStorage persistence
- Usage: `const sdk = xcmasm({ baseURL: 'http://localhost:8010' }); await sdk.usuarios.list()`
- Offline handling: If fetch fails (network error), logs warning and returns null gracefully

## Entry Points

- Location: `backend/main.py` line 316 (`app = FastAPI(...)`)
- Triggers: `uvicorn backend.main:app --port 8010 --reload`
- Responsibilities:
- Location: `/home/luc/DEV_ERP/cmasm.erp/cmasm_erp.html` (511 KB single file)
- Triggers: User navigates to `http://localhost:8010/cmasm_erp.html` (served by `@app.get("/")` line 694–696)
- Responsibilities:
- Location: `/home/luc/DEV_ERP/cmasm.erp/pmoc/index.html`
- Triggers: User navigates to `http://localhost:8010/pmoc/` (served by StaticFiles mount line 335–336)
- Responsibilities:

## Architectural Constraints

- **Threading:** Single-threaded event loop (FastAPI + aiosqlite); async/await handles concurrency via coroutines
- **Global state:** `db` singleton module-level variable (line 324); initialized once at startup, reused for all requests
- **No module-level side effects:** Route handlers must be pure (side effects only in DB); allows testing via dependency injection of mock `db`
- **Circular imports:** Avoided by using `sys.modules["backend.main"].db` in sync.py line 23 (dynamic import to break cycle)
- **Database locks:** SQLite allows one writer at a time; aiosqlite serializes writes; large concurrent inserts may queue
- **Token expiry:** TTL checked on every authenticated request (line 836); expired sessions automatically rejected; client must re-login

## Anti-Patterns

### Hard-Coded Fixture Data in Startup

### Event Handlers with Side Effects Beyond DB

### Additive Migrations Without Rollback Support

### Token Validation on Every Request (No Caching)

## Error Handling

- **Validation errors:** FastAPI + Pydantic auto-return 422 with field errors
- **Auth errors:** 401 "Token absent", "Token invalid or expired", "User not found", "Incorrect password" (lines 827–967)
- **Not found:** 404 "Usuário não encontrado", "Refrigeração não encontrada" (lines 1027, 1121)
- **Business logic errors:** Sync event handlers return error string (e.g., "ativo desconhecido", "saldo negativo") → recorded in `sync_eventos.motivo_rejeicao`
- **Upstream proxy errors:** HTTPException 502 if xPredial unreachable (line 738)

## Cross-Cutting Concerns

- HTTP layer: Pydantic models enforce shape (type, required fields)
- Sync layer: Handlers validate payload (e.g., `if not isinstance(delta, (int, float))` line 81)
- No centralized validation framework

<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->

## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->

## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:

- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->

## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
