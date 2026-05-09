# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**xCMASM** (Centro de Mísseis e Armas Submarinas) is a **modular integrated platform** for facility management, security surveillance, equipment control, and asset management across a Brazilian naval facility.

---

## Repository Structure

This git repo (`/home/luciano/DEV/cmasm.erp`) is the consolidated **xCMASM workspace**. The former xCore nucleus remains under `xCore/`, and satellite modules are now mirrored locally in this repository even if canonical copies still exist elsewhere under `/home/luciano/DEV/`.

```
cmasm.erp/                       ← this repo (consolidated workspace)
├── cmasm_erp.html               # ★ MAIN ERP — single-file app, localStorage, no build step
├── index.html                   # Portal de acesso rápido (links para todos os módulos)
│
├── xCore/                       # Central FastAPI backend + HTML portals (port 8010)
│   ├── backend/
│   │   ├── main.py              # FastAPI app — serves HTML + all /api/* routes
│   │   ├── db_core.py           # aiosqlite singleton (schema_core + schema_grama)
│   │   └── grama.py             # /api/grama/* routes (vegetation control)
│   ├── data/
│   │   ├── schema_core.sql      # Core tables: usuarios, ativos, locais, os, estoque, sessoes
│   │   └── schema_grama.sql     # Grama tables: areas, maquinas, operacoes, kanban, calendario
│   ├── frontend/
│   │   ├── servicos/            # Vue 3 redirect launcher (→ cmasm_erp.html?page=srv-dashboard)
│   │   └── mapa/                # Leaflet installation map
│   ├── predial/                 # xPredial frontend (HTML/JS, served at /predial/*)
│   ├── paiol/                   # xPaiol frontend (HTML/JS, served at /paiol/*)
│   ├── cmasm-erp.html           # Older separate ERP portal (legacy, served by xCore FastAPI)
│   └── tools/
│       ├── seed_usuarios.py     # Seeds 12 real users (run once after init)
│       ├── seed_ativos.py       # Seeds fleet assets
│       ├── seed_estoque.py      # Seeds inventory items
│       └── migrate_from_backup.py  # Imports ERP_core JSON backup
│
├── cmasm-api/                   # Node.js/Express API (MySQL, alternative backend)
│   ├── src/
│   │   ├── server.js            # Express entry point (port 3001)
│   │   └── routes/index.js      # All /api/v1/* routes
│   ├── database/migrations/
│   │   ├── 001_schema.sql
│   │   └── 002_seeds.sql
│   └── .env.example
│
├── assets/                      # Shared static assets (served at /assets/*)
│   ├── xcmasm-sdk.js            # Shared JS SDK for all HTML modules
│   ├── xcmasm-module-links.js   # Module navigation links
│   ├── erp-module-shell.css     # Shared shell CSS
│   └── fonts/                   # Self-hosted DM Sans + JetBrains Mono woff2
│
├── Rules.md                     # Business rules, entity flows, data relationships
├── AGENTS.md                    # Agent instructions, domain-specific rules, module guide
└── .docs_cmasm/                 # Reference documents (CSV exports, OSM maps, PDFs)
```

**Satellite mirrors** (available locally in this repo and possibly also as separate repos outside it):
```
xPredial/     # FastAPI facility inspection (port 8002/3001)
xSeguranca/   # React + FastAPI CCTV (port 8000/3000)
xPaiol/       # Arduino API ammo monitoring (port 8003)
xCalibracao/  # FastAPI stub (port 8004)
aguada-web/   # FastAPI + MQTT water systems (port 8001)
```

---

## Starting the ERP (primary dev target)

The **main application** is `cmasm_erp.html` at the repo root — a single-file vanilla JS + HTML ERP that runs entirely in the browser with localStorage persistence. No build step required.

```bash
# Serve with any static HTTP server (required — file:// breaks font loading)
cd /home/luciano/DEV/cmasm.erp
npx serve .          # serves on http://localhost:3000 by default
# Then open: http://localhost:3000/cmasm_erp.html
```

Or with Python:
```bash
python3 -m http.server 8080
# Then open: http://localhost:8080/cmasm_erp.html
```

**`xCore/cmasm-erp.html`** is an older, separate version of the portal — do not confuse with the main ERP at `cmasm_erp.html` (root).

### Starting xCore (FastAPI backend — optional)

```bash
cd xCore
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# First-time setup: seed database
python tools/seed_usuarios.py   # 12 real users; default password hash for '1234' → "170842" (djb2 hex)
python tools/seed_ativos.py
python tools/seed_estoque.py

# Run
uvicorn backend.main:app --port 8010 --reload
# Portal: http://localhost:8010
# API docs: http://localhost:8010/docs
```

**xCore `.env`** (copy from `.env.example`):
```
PORT=8010
DB_PATH=./data/core.db
TOKEN_TTL_HOURS=8
CORS_ORIGINS=http://localhost:3001,http://localhost:8002,...
```

**cmasm-api (Node.js alternative)**:
```bash
cd cmasm-api
cp .env.example .env   # configure MYSQL_* vars
npm install
node src/server.js     # port 3001; GET http://localhost:3001/api/v1/health
```

**xPredial** (satellite):
```bash
cd xPredial
source .venv/bin/activate
uvicorn backend.main:app --reload --port 8002
# Frontend: cd frontend && python3 -m http.server 3001
pytest tests -q
```

---

## Architecture

### How xCore serves everything

`xCore/backend/main.py` is the single FastAPI app that:
1. Exposes all `/api/*` REST endpoints (auth, users, assets, locations, OS, inventory, grama)
2. Serves `xCore/*.html` pages directly (e.g., GET `/cmasm-erp.html` → `cmasm-erp.html`)
3. Mounts static directories: `/assets` → `../assets/`, `/predial` → `xCore/predial/`, `/paiol` → `xCore/paiol/`

So `http://localhost:8010/predial/inspecoes.html` serves the xPredial frontend without a separate server during development inside xCore.

### Auth

Bearer token with password verification using djb2 hash in hexadecimal form:
- Password `1234` hashes to `"170842"` in the backend seed and auth flow
- `POST /api/auth/login` accepts `{mat, senha}` and resolves `mat` by matrícula or nome for ERP compatibility

### Shared SDK (`assets/xcmasm-sdk.js`)

All HTML modules import this file. Usage:
```js
const sdk = xcmasm({ baseURL: 'http://localhost:8010' });
// sdk.usuarios.list(), sdk.ativos.list(), sdk.os.create({...}), etc.
// Token stored in localStorage under 'xcmasm_token'
```

### Module template (`xCore/ativo-template.html`)

Starting point for new asset-management HTML modules (no build step, localStorage-based). See `AGENTS.md §10` for the 10-step guide to create a new module from this template. Key config points: `TIPOS`, `UNIDADES_DEFAULT`, `PECAS_DEFAULT`, `SK`/`SE` (unique localStorage keys).

### Satellite integration

All satellites set `XCORE_URL = os.getenv("XCORE_URL", "http://localhost:8010")` and call xCore for shared data (users, org structure). xSeguranca is fully independent (own PostgreSQL + Redis).

---

## Key API Endpoints (xCore :8010)

| Domain | Endpoints |
|--------|-----------|
| Auth | `POST /api/auth/login` |
| Users / Org | `GET/POST /api/usuarios`, `GET /api/estrutura` |
| Assets | `GET/POST/PUT /api/ativos` |
| Locations | `GET/POST/PUT /api/locais` |
| Work Orders | `GET/POST /api/os`, `PUT /api/os/{id}/status`, `GET /api/os/kanban` |
| Inventory | `GET /api/estoque`, `POST /api/estoque/{id}/movimentos` |
| Grama | `GET/POST /api/grama/maquinas|areas|manutencao|operacoes` |
| Grama board | `GET /api/grama/kanban`, `GET /api/grama/calendario` |
| Compat | `GET /api/shared` (returns `cmasm_shared` format for localStorage compat) |
| Import | `POST /api/sync/erp` (imports ERP_core JSON backup) |

---

## Business Rules (summary — full detail in `Rules.md`)

- **Assets** (`uso_atual`): incremented by Transportes (km/h), Grama (hours), or manual entry. Never delete — set `ativo=0`.
- **OS lifecycle**: `aberta → em_execucao → concluida | cancelada`. On `concluida`: auto-debit materials from Estoque, update asset `uso_atual`.
- **Preventive maintenance**: when `uso_atual ≥ proximo_uso` on a plan step → alert. Confirming opens a `preventiva` OS automatically. On completion: `proximo_uso = uso_atual + intervalo`.
- **Inventory**: `qtd_atual < qtd_minima` shows "Baixo" badge. Materials in OS go `reservado → utilizado` (or `devolvido` if cancelled).
- **Migrations**: additive only — use `PRAGMA table_info` checks, never DROP.

---

## Design System

**Dark theme — required on all pages.**

```css
--bg: #07111f;   --bg2: #0d1e33;  --bg3: #0a1828;
--panel: #0f2035; --acc: #00b4d8; --green: #22c55e;
--red: #ef4444;  --amber: #f59e0b;
```

Fonts: **JetBrains Mono** (data/code) + **DM Sans** (UI). Self-hosted woff2 files are in `assets/fonts/` — use `assets/fonts.css` import, or Google Fonts CDN as fallback. Every HTML `<head>` must include one of these.

Reference CSS: `assets/erp-module-shell.css` (module shell layout).

---

## Code Patterns

**Frontend (HTML + vanilla JS — no build step)**:
- Module API objects attached to `window` (e.g., `window.predialAPI`, `window.xcmasm`)
- Inline `<script>` in `<body>` for page logic; shared utilities in external `.js` files
- No React/Vue ativo no núcleo; `xCore/frontend/servicos/` permanece apenas como entrada legada redirecionada para o ERP consolidado. xSeguranca segue React/TS.

**Backend (FastAPI)**:
- Pydantic `BaseModel` for validation; `async/await` + `aiosqlite`; raw SQL (no ORM)
- DB singleton: `db = CoreDB(path); await db.init()`; then `await db.fetch_one(sql, params)`
- All error responses include a `detail` field

**xPredial inspection workflow**: `planejada → em_execucao → aguardando_aprovacao → aprovada → concluida`. Check current status before triggering transitions (see `.github/instructions/xpredial-melhorias.instructions.md` for mandatory fixes).

---

## Reference Files

| File | Purpose |
|------|---------|
| `Rules.md` | Business rules: entity relationships, asset categories, OS types, fleet data |
| `AGENTS.md` | Module-by-module agent guide, ativo-template walkthrough, integration keys |
| `MODULOS_EXTERNOS.md` | Satellite module status and integration notes |
| `PLANO_IMPLEMENTACAO.md` | Implementation roadmap |
| `.github/instructions/xpredial-melhorias.instructions.md` | xPredial mandatory bug fixes |
| `.docs_cmasm/` | Authoritative org data (CSV user/cargo lists, OSM facility maps) |
