# Codebase Structure

**Analysis Date:** 2026-06-28

## Directory Layout

```
cmasm.erp/
├── cmasm_erp.html               # ★ Main ERP SPA (511 KB, single file, vanilla JS)
│
├── backend/                     # FastAPI nucleus (port 8010)
│   ├── main.py                  # FastAPI app, routes, startup, static mounts
│   ├── db_core.py               # CoreDB singleton, schema init, additive migrations
│   ├── catalogo.py              # /api/catalogo/* (services, plans, qualifications)
│   ├── grama.py                 # /api/grama/* (lawn control module)
│   ├── sync.py                  # /api/sync/* (PMOC offline sync events)
│   └── __pycache__/             # Python cache (ignore)
│
├── pmoc/                        # ★ PMOC unique offline-first field app
│   ├── index.html               # Field app (categories: refrigeração, predial, paióis, grama, etc.)
│   ├── assets/                  # pmoc.js, pmoc.css
│   ├── seeds/                   # Seed data CSVs per category
│   ├── tools/                   # Seed generation scripts
│   └── docs/                    # PMOC specifications
│
├── data/                        # Database schemas
│   ├── schema_core.sql          # Core entities (users, assets, OS, inventory, sessions)
│   ├── schema_catalogo.sql      # Catalogo + sync (services, plans, planos, sync_eventos)
│   ├── schema_grama.sql         # Grama (machines, areas, operations)
│   └── core.db                  # SQLite database file (created at runtime)
│
├── assets/                      # Static assets (served at /assets/*)
│   ├── xcmasm-sdk.js            # ★ Shared JS SDK (HTTP client + localStorage)
│   ├── pmoc-engine.js           # UI components library for PMOC
│   ├── pmoc-engine.css          # Styling for PMOC components
│   ├── erp-manutencao.js        # Maintenance module (categorized by asset type)
│   ├── erp-refrigeracao.js      # Refrigeration sub-module
│   ├── xmap.js                  # Leaflet map integration
│   ├── xmap-layers-*.js         # Map layer definitions (aguada, eletrica, grama)
│   ├── fonts.css                # Font imports (JetBrains Mono, DM Sans)
│   ├── fonts/                   # Self-hosted woff2 files
│   ├── favicon.svg              # Logo/icon
│   └── bootstrap-icons-fonts/   # Bootstrap icon set
│
├── tools/                       # Seed and utility scripts
│   ├── seed_usuarios.py         # Creates 12 default users
│   ├── seed_ativos.py           # Creates sample assets
│   ├── seed_estoque.py          # Creates sample inventory
│   ├── telegram_spike.py        # Telegram bot integration stub
│   └── import_ata2_climatizacao.py  # Import climate services from ATA2 HTML
│
├── tests/                       # Test suite (pytest)
│   ├── test_sync.py             # Sync endpoint tests
│   ├── test_auth.py             # Auth flow tests
│   └── __pycache__/
│
├── docs/                        # Internal documentation
│   ├── CMASM.ERP_leanERP.md     # Architectural vision
│   ├── propostas/               # Feature proposals
│   ├── demos/                   # Demo summaries
│   └── superpowers/             # GSD skill notes
│
├── .docs_cmasm/                 # Authoritative business documents
│   ├── Regras de Negocio e Fluxos.md  # ★ Canonical domain model (categories, OS lifecycle)
│   ├── referencias/             # Templates, reference CSVs
│   ├── *.csv                    # User rosters, asset lists, etc.
│   └── *.osm                    # OpenStreetMap facility maps
│
├── .claude/                     # Claude Code harness config
│   └── settings.json            # Permissions, hooks, env vars
│
├── .planning/                   # GSD orchestrator outputs
│   ├── codebase/                # This directory (ARCHITECTURE.md, STRUCTURE.md, etc.)
│   └── ...
│
├── .github/                     # GitHub Actions workflows
│   └── instructions/            # Decision records
│
├── demos/                       # Standalone demo HTMLs
│   ├── core_ativos.html         # Asset CRUD demo
│   ├── paiois.html              # Paiol (storage) demo
│   └── mock/                    # Mock data fixtures
│
├── .venv/                       # Python virtual environment (gitignored)
│
├── CLAUDE.md                    # ★ Architecture guide (read this first)
├── REQUISITOS.md                # Vision, principles, roadmap
├── Rules.md                     # Technical rules, schema, lifecycle
├── MODULOS_EXTERNOS.md          # External module integration contract
├── todo.md                      # Active backlog
│
├── requirements.txt             # Python deps: fastapi, uvicorn, aiosqlite
├── package.json                 # Node.js (minimal: serve, pytest CLI refs)
├── Dockerfile                   # Container build for nucleus
├── .env                         # Environment config (DB_PATH, TOKEN_TTL, URLs)
└── .gitignore                   # Ignore .venv, *.db, .env, etc.
```

## Directory Purposes

**`backend/`:**
- Purpose: FastAPI nucleus server code
- Contains: Route handlers, database layer, sync logic
- Key files: `main.py` (router setup), `db_core.py` (persistence layer), `catalogo.py` (services catalog), `grama.py` (vegetation control), `sync.py` (PMOC sync)

**`pmoc/`:**
- Purpose: Single unified offline-first field application
- Contains: HTML entry point, local IndexedDB adapter, category-specific forms (refrigeração, predial, paióis, transportes, grama, elétrica, calibração)
- Key files: `index.html` (app shell), `assets/pmoc.js` (field logic), `seeds/` (category CSV data)

**`data/`:**
- Purpose: Database schema definitions
- Contains: Three SQL schema files (core, catalogo, grama) + runtime SQLite file
- Key files: `schema_core.sql` (entities), `schema_catalogo.sql` (services + sync), `schema_grama.sql` (vegetation module)
- Generated: `core.db` created at first run by `CoreDB.init()`

**`assets/`:**
- Purpose: Shared frontend JavaScript, CSS, fonts, icons
- Contains: SDK client, UI component library, map layers, styling
- Key files: `xcmasm-sdk.js` (HTTP client), `pmoc-engine.js` (components), `erp-manutencao.js` (maintenance UI), fonts (self-hosted woff2)
- Used by: `cmasm_erp.html`, `pmoc/index.html`, all satellite modules

**`tools/`:**
- Purpose: Database seeding, data import, utility scripts
- Contains: User creation, asset creation, inventory seeding, external data import
- Key files: `seed_usuarios.py`, `seed_ativos.py`, `import_ata2_climatizacao.py`
- Run manually via: `python tools/seed_usuarios.py`

**`tests/`:**
- Purpose: Pytest test suite
- Contains: Sync handler tests, auth tests, integration tests
- Run via: `pytest tests -q`

**`docs/`:**
- Purpose: Internal specs, proposals, meeting notes
- Contains: Architecture diagrams, feature designs, demo recordings
- Key files: `CMASM.ERP_leanERP.md` (hub vision), `propostas/` (functional specs), `superpowers/` (GSD notes)

**`.docs_cmasm/`:**
- Purpose: Canonical business documents
- Contains: Domain model CSV, asset registries, facility maps, compliance records
- Key files: `Regras de Negocio e Fluxos.md` (domain authority), CSV rosters, OSM maps

## Key File Locations

**Entry Points:**
- `cmasm_erp.html`: Main ERP web app (served by `GET /` and `GET /cmasm_erp.html`)
- `pmoc/index.html`: Field app (served by `GET /pmoc/` mount)
- `backend/main.py`: FastAPI server startup point

**Configuration:**
- `.env`: Environment variables (DB_PATH, TOKEN_TTL, satellite URLs)
- `.env.example`: Template (check this to see expected vars)
- `backend/main.py` lines 25–40: Config loading + defaults

**Core Logic:**
- `backend/db_core.py`: Database initialization, migration, query wrappers
- `backend/main.py`: Auth flow, user/asset CRUD, OS management
- `backend/sync.py`: PMOC event handlers (uso_atual_inc, estoque_mov, os_criada, etc.)
- `backend/catalogo.py`: Service catalog (serviços, planos, qualificações)
- `backend/grama.py`: Lawn/vegetation control (máquinas, áreas, operações)

**Frontend Logic:**
- `cmasm_erp.html`: Single-file SPA with tabs for Manutenção (categorized), Estoque, Organização, Grama
- `pmoc/index.html`: Single-file field app with local IndexedDB persistence
- `assets/xcmasm-sdk.js`: HTTP client (all API calls go through this)
- `assets/pmoc-engine.js`: Reusable UI components (modals, forms, tables)
- `assets/erp-manutencao.js`: Maintenance panel with category filtering

**Testing:**
- `tests/test_sync.py`: Sync event handler tests
- `tests/test_auth.py`: Authentication flow tests

## Naming Conventions

**Files:**
- Route handlers: `{domain}.py` (e.g., `sync.py`, `catalogo.py`, `grama.py`)
- Database schema: `schema_{domain}.sql` (e.g., `schema_core.sql`)
- Seed scripts: `seed_{entity}.py` (e.g., `seed_usuarios.py`)
- Frontend modules: `{feature}-{role}.js` or `{module}-engine.js` (e.g., `pmoc-engine.js`, `erp-manutencao.js`)

**Functions:**
- HTTP handlers: `@app.{method}("/api/path")` → snake_case name (e.g., `list_usuarios`, `create_ativo`)
- Sync handlers: `_h_{event_type}` (e.g., `_h_uso_atual_inc`, `_h_estoque_mov`)
- Migrations: `_migrate_{feature}` (e.g., `_migrate_catalogo_planos_cols`)
- Seeds: `_seed_{table_name}_if_empty` (e.g., `_seed_colab_if_empty`)

**Database entities:**
- Tables: `snake_case` (e.g., `usuarios`, `ativos`, `ordens_servico`, `estoque_movimentos`)
- Columns: `snake_case` (e.g., `pw_hash`, `uso_atual`, `data_abertura`)
- Foreign keys: `{table}_{column}` (e.g., `usuario_id`, `local_id`, `os_id`)

**HTML/JS:**
- CSS classes: `kebab-case` (e.g., `.login-box`, `.sidebar-collapsed`, `.topbar-alert`)
- DOM IDs: `kebab-case` (e.g., `#app`, `#login-screen`, `#sidebar-toggle`)
- JS variables: `camelCase` (e.g., `baseURL`, `tokenKey`, `sdk`)

## Where to Add New Code

**New Feature (e.g., new asset category):**
- Core functionality: Add route in `backend/main.py` or new file `backend/{feature}.py`; add Pydantic model above route; add table/columns to appropriate schema in `data/schema_*.sql`
- Tests: Add test file `tests/test_{feature}.py` with pytest cases
- Frontend (ERP): Add tab/section to `cmasm_erp.html` or separate HTML module; import SDK
- Frontend (PMOC): Add category section to `pmoc/index.html`; add seed CSV to `pmoc/seeds/{category}.csv`

**New Service Catalog Entry:**
- Define service in `catalogo_servicos` table via `/api/catalogo/servicos` POST endpoint
- Link materials via `catalogo_servico_materiais`
- Link to plan via `catalogo_plano_itens` if preventive maintenance applies

**New Sync Event Type:**
- Define event type constant in `backend/sync.py` line 27 (TIPOS_VALIDOS)
- Add handler function `_h_{event_type}` with signature `async (conn, payload) -> str | None`
- Register handler in `HANDLERS` dict (line 276 in full sync.py)
- Document event schema in `MODULOS_EXTERNOS.md` §3.4

**Utilities/Shared Functions:**
- Common JS: `assets/` (e.g., `xcmasm-sdk.js`, new `utils.js`)
- Common Python: `backend/` (e.g., new `helpers.py` for auth/validation utilities)

## Special Directories

**`.planning/`:**
- Purpose: GSD orchestrator outputs (phase plans, execution logs, codebase maps)
- Generated: Not committed by default; created by `/gsd-plan-phase`, `/gsd-execute-phase`, etc.
- Structure: `codebase/` (ARCHITECTURE.md, STRUCTURE.md, etc.), `phases/` (execution logs)

**`.docs_cmasm/`:**
- Purpose: Source of truth for business rules, organizational structure, facility maps
- Committed: Yes (part of git repo)
- Sensitive: Contains CSV rosters with email/phone; treat as internal-only

**`.venv/`:**
- Purpose: Python virtual environment
- Committed: No (in .gitignore)
- Setup: `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`

**`demos/`:**
- Purpose: Standalone demo pages for feature showcasing
- Committed: Yes (HTML + mock data)
- Usage: Open in browser to test isolated component behavior

**`.github/`:**
- Purpose: CI/CD workflows and decision records
- Committed: Yes
- Contents: Action YAML files, ADR markdown

## Integration Points

**External Satellites (xPredial, xAguada, xPaiol, xCalibracao):**
- They call `GET /api/usuarios`, `GET /api/estrutura` to read shared org data
- They call `POST /api/os` to create work orders
- Nucleus proxies `/api/predial/*` to xPredial (lines 752–759 in main.py)

**PMOC ↔ Nucleus Sync:**
- PMOC calls `GET /api/sync/manifest?modulo={category}` to fetch initial state
- PMOC records events locally, then calls `POST /api/sync/push` with event batch
- Nucleus validates + applies events; returns `{applied: [...], rejected: [...]}`
- PMOC calls `GET /api/sync/cursor` to track sync position (for incremental pulls)

**Browser Storage:**
- ERP SPA: Token + user object in `localStorage` under keys `xcmasm_token`, `xcmasm_user`
- PMOC app: Full data in `IndexedDB` (offline-first); syncs to nucleus periodically

---

*Structure analysis: 2026-06-28*
