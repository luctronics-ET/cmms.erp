# Technology Stack

**Analysis Date:** 2026-06-28

## Languages

**Primary:**
- Python 3.7+ - Backend (FastAPI core, database migrations, seed scripts)
- JavaScript (vanilla) - Frontend (no build step, single-file HTML apps + SDK)
- SQL (SQLite) - Database schema definitions in `data/*.sql`

**Secondary:**
- HTML5 - Static templates for ERP and PMOC field app
- CSS3 - Styling (dark theme, self-hosted fonts)

## Runtime

**Environment:**
- Python 3.7+ (development and production)
- Node.js / npm (optional, for ESLint only — no build pipeline required)

**Package Manager:**
- pip (Python dependencies from `requirements.txt`)
- npm (dev dependencies for ESLint — see `package.json`)
- Lockfile: `requirements.txt` present; no `package-lock.json` (minimal npm usage)

## Frameworks

**Core:**
- FastAPI 0.115.0 - REST API framework (async, production-grade)
- Uvicorn 0.30.6 (with [standard] extras) - ASGI server for FastAPI

**Frontend:**
- Vanilla JavaScript (no React, Vue, or build framework on core ERP)
- Leaflet 1.9.4 - Map library (loaded via CDN from unpkg.com)

**Database:**
- SQLite (aiosqlite 0.20.0) - Embedded relational database
- No ORM — raw SQL with parameter binding via aiosqlite

**Testing & Linting:**
- ESLint 10.2.1 - JavaScript linting (dev dependency in `package.json`)
- No pytest or test runner configured — tests are manual or integration-based

**Build/Dev:**
- No build step for core ERP — files served as-is
- Uvicorn with `--reload` flag for hot-reload during development
- Python tools in `tools/` for seeding and migrations (not build-time)

## Key Dependencies

**Critical:**
- fastapi==0.115.0 - Web framework, request routing, validation, OpenAPI docs
- aiosqlite==0.20.0 - Async SQLite driver (enables non-blocking DB operations)
- uvicorn[standard]==0.30.6 - ASGI server (includes uvloop for performance)
- pydantic==2.7.4 - Data validation, serialization (request bodies, responses)

**Infrastructure:**
- python-multipart==0.0.9 - Multipart form parsing (file uploads in POST requests)
- aiofiles - Async file I/O (not directly used, but listed; may support future uploads)
- httpx==0.27.2 - Async HTTP client (used for proxying xPredial requests, health checks on satellites)

## Configuration

**Environment:**
- `.env` file (not committed — see `.env.example` for template)
- Key variables: `DB_PATH`, `TOKEN_TTL_HOURS`, `CORS_ORIGINS`, `XPREDIAL_URL`, `XAGUADA_URL`, `XPAIOL_URL`, `XCALIBRACAO_URL`
- `TELEGRAM_BOT_TOKEN` loaded via `tools/telegram_spike.py` (optional integration)
- Defaults in code ensure app runs offline: e.g., `DB_PATH` defaults to `./data/core.db`

**Build:**
- `backend/main.py` - No compilation; FastAPI serves HTML + API routes directly
- Static files mounted from `assets/` and `pmoc/` directories
- Cache-control middleware prevents serving stale HTML/JS (line 344–346 in `backend/main.py`)

## Platform Requirements

**Development:**
- Python 3.7+, pip
- Git (for version control)
- Text editor or IDE (any; no build config required)
- HTTP server for static files (e.g., `npx serve .`, `python -m http.server`)
- Optional: Node.js 18+ (if running ESLint)

**Production:**
- Python 3.7+ runtime
- Uvicorn server (via pip install)
- SQLite (embedded; no separate database installation)
- Reverse proxy (e.g., nginx) recommended for SSL/TLS
- Environment variables set at deployment (DB_PATH, CORS_ORIGINS, satellite URLs)

## Frontend Assets

**Static Files (`assets/` directory):**
- `xcmasm-sdk.js` - Shared REST client SDK (used by all HTML modules)
- `pmoc-engine.js` - UI components library for PMOC field app
- `erp-module-shell.css` - Shared layout/theme CSS
- `fonts/` - Self-hosted woff2 files: JetBrains Mono (data/code), DM Sans (UI)
- `fonts.css` - Font face declarations (fallback to Google Fonts CDN if offline)
- Leaflet CSS served via CDN (unpkg.com)

**HTML Entry Points:**
- `cmasm_erp.html` - Main ERP single-file app (root `/`)
- `pmoc/index.html` - PMOC field app (mounted at `/pmoc/`)

## Database

**Engine:** SQLite (aiosqlite wrapper)
- File-based: `./data/core.db` (created on first init)
- Schemas in `data/schema_*.sql`:
  - `schema_core.sql` - Users, organization, assets, locations, work orders, inventory, sessions
  - `schema_catalogo.sql` - Service catalog, plans, materials, conditionality rules
  - `schema_grama.sql` - Vegetation control (Grama) module: machines, areas, operations

**Migrations:**
- Additive only — uses `PRAGMA table_info()` to check before `ALTER TABLE`
- Never drops columns/tables (Rule in Rules.md §9)
- Executed at startup in `backend/main.py` `startup()` event

## API

**Base URL:** `http://localhost:8010` (default; configurable via env)
- `/` - Serves `cmasm_erp.html` (main ERP)
- `/pmoc/` - Serves PMOC field app (static files)
- `/assets/*` - Static assets (SDK, CSS, fonts)
- `/api/*` - REST endpoints (auth, users, assets, inventory, work orders, sync, etc.)
- `/docs` - FastAPI OpenAPI documentation

**Authentication:**
- Bearer token scheme (JWT-style tokens stored in `sessoes` table)
- Password hash: djb2 algorithm (hexadecimal format, backward-compatible with legacy ERP_core)
- Token TTL: configured via `TOKEN_TTL_HOURS` env var (default 8 hours)

---

*Stack analysis: 2026-06-28*
