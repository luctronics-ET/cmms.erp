# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**cmasm.erp** is a **integrated management platform** for assets, service and manintenance at a Brazilian naval facility, **Centro de Mísseis e Armas Submarinas da Marinha (CMASM)**.

**Arquitetura: núcleo + PMOC único categorizado.** O sistema é composto por (1) o **núcleo** (`cmasm.erp`) — backend FastAPI + ERP web (`cmasm_erp.html`) com módulo Manutenção categorizado por `tipo` de ativo; e (2) um **PMOC único offline-first** (`cmasm.erp/pmoc/`), app HTML de campo com categorias internas (refrigeração, predial, paióis, transportes, grama, elétrica, calibração) que sincroniza com o núcleo via API.

Ver `REQUISITOS.md` para a visão; `Regras de Negocio e Fluxos.md` para o **modelo de domínio canônico** (categorias, planos, OS, NECs, transportes, estoque); `Rules.md` para regras técnicas/operacionais do núcleo; `MODULOS_EXTERNOS.md` para o contrato com módulos *realmente* externos (hardware/Postgres próprio — `aguada-web`, `xSeguranca`, `xCFTV`, `xFonoclama`).

O núcleo cobre: **usuários, organização, ativos, estoque, OS/serviços, manutenção (painel categorizado), documentos**. **PMOCs não são módulos externos** — são categorias internas do app único de campo.

---

## Repository Structure

Este repo (`/home/luciano/DEV/cmasm.erp`) contém **o núcleo + o PMOC único**. Não existem mais repos `pmoc_<dom>` separados — categorias do PMOC vivem em `pmoc/` dentro deste mesmo repo.

```
cmasm.erp/                       ← este repo (NÚCLEO + PMOC ÚNICO)
├── cmasm_erp.html               # ★ MAIN ERP — single-file app do núcleo
├── index.html                   # Portal de acesso rápido
│
├── pmoc/                        # ★ PMOC único (app de campo offline-first)
│   └── (a criar — categorias internas: refrigeracao, predial, paiois,
│        transportes, grama, eletrica, calibracao)
│
├── backend/                     # FastAPI — núcleo (port 8010)
│   ├── main.py                  # FastAPI app — serves HTML + all /api/* routes
│   ├── db_core.py               # aiosqlite singleton
│   └── grama.py                 # /api/grama/* routes
│
├── data/                        # DB schemas
│   ├── schema_core.sql          # Core: usuarios, ativos, locais, os, estoque, sessoes
│   ├── schema_catalogo.sql      # Catálogo de serviços + planos + qualificações + sync
│   └── schema_grama.sql         # Grama: areas, maquinas, operacoes, kanban, calendario
│
├── assets/                      # Static assets (served at /assets/*)
│   ├── xcmasm-sdk.js            # Shared JS SDK
│   ├── pmoc-engine.js           # Componentes UI usados pelo PMOC
│   ├── pmoc-engine.css
│   ├── erp-module-shell.css     # Shared shell CSS
│   └── fonts/                   # Self-hosted DM Sans + JetBrains Mono woff2
│
├── tools/                       # Seed/migration scripts
├── referencias/                 # Templates e seeds
├── docs/                        # Specs internas (skill: superpowers)
│
├── REQUISITOS.md                # Visão, princípios arquiteturais, roadmap
├── Regras de Negocio e Fluxos.md # ★ Modelo de domínio canônico
├── Rules.md                     # Regras técnicas/operacionais do núcleo
├── MODULOS_EXTERNOS.md          # Contrato com módulos realmente externos
├── todo.md                      # Backlog ativo
└── .docs_cmasm/                 # Documentos de referência (CSV, OSM, PDFs)
```

**Módulos *realmente* externos** (sistemas com hardware/Postgres próprio — detalhes em `MODULOS_EXTERNOS.md`):

| Módulo | Stack | Porta / Tipo |
|--------|-------|--------------|
| aguada-web | FastAPI + MQTT + nginx | 8001 (hardware ESP32) |
| xSeguranca | React + FastAPI + PostgreSQL | 8000/3000 |
| xFonoclama | firmware ESP32 | — |
| xCFTV | Java | — |

> Repos legados em `/home/luciano/DEV/pmoc_*` (refrigeracao, eletrica, calibracao, corte, transportes) estão a arquivar. `pmoc.refs` permanece como repo de referências/seeds.

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

### Starting xCore (FastAPI backend — optional)

```bash
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

**xPredial** (satellite — repo separado em `/home/luciano/DEV/xPredial`):
```bash
cd /home/luciano/DEV/xPredial
source .venv/bin/activate
uvicorn backend.main:app --reload --port 8002
pytest tests -q
```

---

## Architecture

### How xCore serves everything

`backend/main.py` is the single FastAPI app that:
1. Exposes all `/api/*` REST endpoints (auth, users, assets, locations, OS, inventory, grama, sync, catálogo)
2. Mounts static directories: `/assets` → `assets/`
3. Serve estaticamente o PMOC em `/pmoc/` (a configurar).

Módulos realmente externos (aguada-web, xSeguranca, xCFTV, xFonoclama) têm seus próprios servidores e se integram via `GET /api/usuarios` e `POST /api/os` com `modulo_origem`.

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

### Módulos externos — integration

Módulos realmente externos (aguada-web, xSeguranca, xCFTV, xFonoclama) configuram `XCORE_URL = os.getenv("XCORE_URL", "http://localhost:8010")` e chamam o núcleo para dados compartilhados (usuários, organograma). xSeguranca é totalmente independente (PostgreSQL + Redis próprios).

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
| PMOC sync | `GET /api/sync/manifest?modulo=<categoria>`, `POST /api/sync/push`, `GET /api/sync/cursor` |
| Categorias | `GET /api/modulos` (categorias registradas + status — `modulos_registrados`) |
| Catálogo | `GET/POST/PUT /api/catalogo/servicos|planos|qualificacoes` *(a implementar — schema pronto)* |
| Compat | `GET /api/shared` (formato legado para localStorage) |
| Import | `POST /api/sync/erp` (importa backup ERP_core JSON) |

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
| `REQUISITOS.md` | Visão, princípios arquiteturais, roadmap, decisões registradas |
| `Regras de Negocio e Fluxos.md` | **Modelo de domínio canônico** — categorias de ativos, planos, OS/PS/SR/NEC, transportes, estoque |
| `Rules.md` | Regras técnicas/operacionais do núcleo: schema, lifecycle, sync, catálogo |
| `MODULOS_EXTERNOS.md` | Contrato com módulos *realmente* externos (aguada-web, xSeguranca, xCFTV, xFonoclama) |
| `todo.md` | Backlog ativo, organizado por prioridade |
| `.docs_cmasm/` | Documentos autoritativos (CSV de usuários/cargos, mapas OSM) |
| `pmoc.refs/` (irmão deste repo) | Repositório de referências e seeds: CSVs normativos, POPs, mapas, planilhas |

### Convenções para mudanças

- **Núcleo**: tela de Manutenção é categorizada (tabs por `tipo` de ativo). Adicionar uma nova categoria significa adicionar tab + filtro, não criar repo novo.
- **PMOC único**: oferece as mesmas categorias no app de campo offline-first. Adicionar uma categoria nova ao PMOC = adicionar seção/aba interna em `cmasm.erp/pmoc/`.
- **Módulo externo**: reservado a sistemas com hardware/Postgres próprio. PMOC **não** é externo.
- **Migração de schema**: aditiva. `PRAGMA table_info` antes de qualquer `ALTER`. Nunca `DROP`.
