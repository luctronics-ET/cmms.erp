# External Integrations

**Analysis Date:** 2026-06-28

## Satellite Modules (External FastAPI Servers)

**Overview:**
The xCMASM core (xCore) at port 8010 integrates with four satellite FastAPI services, each with its own database and business logic. These satellites call back to xCore for shared data (users, assets, work orders) via REST API. Integration points documented in `CLAUDE.md` and `Rules.md §1`.

**[xPredial] — Building Inspection & Maintenance**
- **Stack:** FastAPI + PostgreSQL (repo: `/home/luc/DEV_ERP/xPredial`)
- **Port:** 8002
- **URL Config:** `XPREDIAL_URL` env var (default: `http://127.0.0.1:8002`)
- **Integration method:** HTTP proxy pass-through via `backend/main.py` lines 716–759
  - All requests to `/api/predial/*` are forwarded to xPredial
  - Headers filtered (removes `Host`, `Content-Length`, `Connection`)
  - Timeout: 30 seconds
  - Error handling: returns 502 if upstream unavailable
- **What it reads from xCore:** Users (`GET /api/usuarios`), organizational structure (`GET /api/estrutura`), assets (`GET /api/ativos`)
- **What it writes to xCore:** Work orders (`POST /api/os`) with `modulo_origem: "xpredial"`

**[xAguada] — Water/Hydraulics System (ESP32 IoT)**
- **Stack:** FastAPI + MQTT (hardware: ESP32)
- **Port:** 8001
- **URL Config:** `XAGUADA_URL` env var (default: `http://127.0.0.1:8001`)
- **Purpose:** Monitors hydraulic/water systems; sensor data via MQTT
- **Integration:** Health check endpoint at `GET /health` (line 763–774 in `backend/main.py`)
- **Communication:** Listed in `_SATELLITES` array; no direct API calls in codebase, but endpoint available for future expansion

**[xPaiol] — Storage/Logistics (Weapon Systems Depot)**
- **Stack:** FastAPI (satellite module)
- **Port:** 8003
- **URL Config:** `XPAIOL_URL` env var (default: `http://127.0.0.1:8003`)
- **Purpose:** Manages classified materials, weapon stores, ammunition inventory
- **Integration:** Health check endpoint via `GET /api/satellites` (line 762–774)
- **Isolation:** Separate Postgres database; shares only user/org lookup via xCore API

**[xCalibracao] — Metrology & Calibration**
- **Stack:** FastAPI (satellite module)
- **Port:** 8004
- **URL Config:** `XCALIBRACAO_URL` env var (default: `http://127.0.0.1:8004`)
- **Purpose:** Tracks calibration intervals and certificates for measurement instruments
- **Integration:** Health check via `GET /api/satellites`
- **Asset category:** Instruments (category: `instrumentos`, unidade_uso: meses/validade)

## Data Storage

**Primary Database:**
- SQLite 3 via aiosqlite
- Location: `./data/core.db` (configurable via `DB_PATH` env var)
- Schemas: `data/schema_core.sql`, `data/schema_catalogo.sql`, `data/schema_grama.sql`
- No backup automation in code — external responsibility (e.g., cron, container volume snapshots)

**Satellite Databases:**
- xPredial: PostgreSQL (independent; not managed by xCore)
- xAguada: Unknown (likely local state or upstream MQTT broker)
- xPaiol: PostgreSQL (independent)
- xCalibracao: PostgreSQL (independent)

**File Storage:**
- **Documents:** Planned in `schema_catalogo.sql` table `documentos` (id, storage_path, conteudo_inline)
  - `storage_path` field for relative paths or URLs
  - `conteudo_inline` for short text (markdown/POPs)
  - No S3/blob store configured — stored locally via `storage_path` (future integration point)
- **No current file upload endpoint** — schema ready but handler not yet implemented

**Caching:**
- **Client-side:** localStorage (JavaScript SDK caches auth token and user data)
- **HTTP Cache-Control:** Middleware prevents browser caching of HTML/JS (dev-friendly; line 340–346 in `backend/main.py`)
- **No server-side caching** — SQLite provides transaction isolation; no Redis or Memcached

## Authentication & Identity

**Auth Provider:**
- Custom in-band password verification (no external OAuth/SAML)
- Bearer token scheme (JWT-style, opaque tokens stored in `sessoes` table)
- Password hash: djb2 algorithm (legacy-compatible with ERP_core)

**Implementation (`backend/main.py` lines 815–980):**
- `POST /api/auth/login` accepts `{mat, senha}` (employee ID or name, password)
- Password hashed server-side using djb2; compared against stored `pw_hash`
- Token generated as random 43-byte URL-safe string (via `secrets.token_urlsafe(32)`)
- Token stored in DB with `expira_em` timestamp
- Token TTL: `TOKEN_TTL_HOURS` (default 8 hours)
- `Authorization: Bearer <token>` required for protected endpoints

**Session Management:**
- Table: `usuarios`, `sessoes`
- `POST /api/auth/logout` deletes session token from DB
- `GET /api/auth/me` returns authenticated user details
- Middleware: `_require_auth()` (line 826–837) validates token before request

**Satellite Integration with xCore Auth:**
- Each satellite configured with `XCORE_URL` env var
- Satellites call xCore's `GET /api/usuarios` to resolve user roles/permissions
- No SSO or federation — satellites maintain independent password schemes (if any)

## Monitoring & Observability

**Error Tracking:**
- No external error tracking service (Sentry, DataDog, etc.) configured
- Errors returned as JSON with `detail` field (FastAPI standard)
- Application logs written to stdout/stderr (captured by container/systemd)

**Logs:**
- **Application logs:** Printed to console (via FastAPI/Uvicorn defaults)
- **Database logs:** None (SQLite is silent; schema migrations logged to app output)
- **API access logs:** Uvicorn access logs (method, path, status, latency)
- **No structured logging** (JSON logs) — uses Python print/logging

**Health Checks:**
- `GET /health` - Simple status endpoint (line 999–1008)
  - Returns JSON: `{ "status": "ok", "usuarios": count, "ativos": count }`
  - Used for container orchestration (Kubernetes, Docker Compose health checks)
- `GET /api/satellites` - Probes all four satellite modules (line 762–774)
  - Timeout: 3 seconds per satellite
  - Returns array: `[{id, name, url, port, status}]` (status: "online", "error", "offline")

**Performance Metrics:**
- No APM (Application Performance Monitoring) configured
- No custom instrumentation (timing, profiling) in code
- Uvicorn reports request metrics to stdout if `--log-level` set to DEBUG

## CI/CD & Deployment

**Hosting:**
- Local development: Uvicorn on localhost (`uvicorn backend.main:app --reload --port 8010`)
- Production: Intended for Docker container or systemd service
  - No Dockerfile in repo (external deployment responsibility)
  - No Docker Compose for full stack (satellites run separately)

**CI Pipeline:**
- Not detected in codebase
- GitHub Actions workflows may exist in `.github/workflows/` (not visible in scan)
- No automatic tests run on push (no pytest/vitest configured)

**Deployment Targets:**
- Linux server (development on WSL/Ubuntu observed; production likely DoD-compatible infrastructure)
- Python 3.7+ runtime required
- SQLite (file-based) allows easy backup/restore

## Environment Configuration

**Required Environment Variables:**
- `DB_PATH` - SQLite database file path (default: `./data/core.db`)
- `TOKEN_TTL_HOURS` - Session token lifetime in hours (default: 8)
- `CORS_ORIGINS` - Comma-separated list of allowed origins (default: `*`)
- `XPREDIAL_URL` - xPredial base URL (default: `http://127.0.0.1:8002`)
- `XAGUADA_URL` - xAguada base URL (default: `http://127.0.0.1:8001`)
- `XPAIOL_URL` - xPaiol base URL (default: `http://127.0.0.1:8003`)
- `XCALIBRACAO_URL` - xCalibracao base URL (default: `http://127.0.0.1:8004`)

**Optional Environment Variables:**
- `TELEGRAM_BOT_TOKEN` - Loaded by `tools/telegram_spike.py` (purpose: future notifications; not yet integrated in main app)

**Secrets Location:**
- `.env` file (gitignored; copy from `.env.example`)
- Environment variables passed at container startup or systemd service definition
- No secrets manager (Vault, AWS Secrets Manager) integrated
- Caution: Do NOT commit `.env` or any file containing `TELEGRAM_BOT_TOKEN`, database credentials, etc.

## Webhooks & Callbacks

**Incoming Webhooks:**
- Not implemented in current codebase
- Planned for PMOC field app sync: `POST /api/sync/push` (line 1725+, not shown) accepts event arrays from offline PMOC
  - Events: OS created, inventory movement, asset use update, documents uploaded
  - Payload: JSON array of event objects with origin_id, timestamp, type, data

**Outgoing Webhooks:**
- Not implemented
- Satellites receive work orders via `POST /api/os` — synchronous HTTP, not webhooks

**PMOC Sync Mechanism (Custom Protocol):**
- Manifest endpoint: `GET /api/sync/manifest?modulo=<categoria>&since=<iso>` (line 1789+)
  - Returns: ativos, users, estoque, catalog filtered by category
  - Consumed by PMOC IndexedDB for offline operation
- Push endpoint: `POST /api/sync/push`
  - PMOC sends event array (OS changes, inventory movements)
  - Nucleus merges into `ordens_servico`, `estoque_movimentos` tables
- Cursor endpoint: `GET /api/sync/cursor?modulo=<categoria>&device=<uuid>`
  - Returns: timestamp of last confirmed sync
  - Used for resumable sync (restart from last checkpoint)

## Third-Party Service Integrations

**Maps:**
- Leaflet 1.9.4 library (loaded from unpkg.com CDN)
- Maps rendered client-side in `cmasm_erp.html`
- No backend geocoding or routing API

**Fonts:**
- Self-hosted woff2 files in `assets/fonts/`
  - JetBrains Mono (data/code display)
  - DM Sans (UI text)
- Fallback: Google Fonts CDN (if offline/woff2 unavailable)
- Loaded via `assets/fonts.css`

**External APIs:**
- None directly consumed (no Stripe, Slack, GitHub, etc.)
- Potential future integrations documented in `todo.md` and `docs/propostas/`

## Integration Patterns & Best Practices

**Satellite Discovery:**
- Satellites configured via env vars (static list in `_SATELLITES` array)
- Health probes run at app startup and on-demand via `GET /api/satellites`
- Failures do not block xCore startup (graceful degradation)

**Error Handling:**
- xCore proxy (line 729–739) catches `httpx.HTTPError`, returns 502 with detail
- Satellites unresponsive → returns 503 or timeout error
- No retry logic in xCore proxy (upstream responsibility)

**Data Consistency:**
- xCore is source of truth for users, assets, organizational structure
- Satellites fetch their own local copies; conflicts resolved at satellite level
- Work orders flow from satellites → xCore (append-only log in `ordens_servico`)
- No distributed transactions (2PC) — eventual consistency model

**CORS:**
- Allow-origins list configurable via `CORS_ORIGINS` env var (default: `*`)
- All methods allowed (`*`)
- All headers allowed (`*`)
- Applied at `backend/main.py` line 317–322 via FastAPI CORSMiddleware

---

*Integration audit: 2026-06-28*
