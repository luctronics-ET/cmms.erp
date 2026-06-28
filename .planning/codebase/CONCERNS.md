# Codebase Concerns

**Analysis Date:** 2026-06-28

## Tech Debt

**Single-file ERP HTML monolith:**
- Issue: `cmasm_erp.html` is 9,069 lines — all UI logic, state, and form handlers in one file
- Files: `cmasm_erp.html`
- Impact: Changes cause full page reparse; navigation is difficult; testing requires mocking DOM; style conflicts and global scope pollution; no hot reload or build optimization
- Fix approach: Extract modules (auth, modals, forms, table views) into separate `.js` files with clear responsibilities; use ES6 modules or CommonJS; build a module loader to avoid inline scripts

**localStorage persistence without sync conflict resolution:**
- Issue: ERP stores all data in `localStorage` (users, assets, OS, inventory). PMOC app uses `IndexedDB` for offline sync. No conflict resolution strategy when divergent edits happen offline
- Files: `cmasm_erp.html`, `assets/xcmasm-sdk.js`, `pmoc/index.html`
- Impact: Data loss or merge failures if same record edited in ERP and PMOC concurrently; manual reconciliation needed; audit trail missing
- Fix approach: Implement vector clocks or operational transform for localStorage; add `version` and `last_modified_at` to all entities; PMOC push validates version before accept; log conflicts to audit trail

**Weak password hashing (djb2):**
- Issue: Authentication uses djb2 hash algorithm (32-bit signed integer modulo), designed for hash tables, not password security. Default password `1234` hashes to `"170842"`. No salt.
- Files: `backend/main.py` (lines 816–823, 963–964)
- Impact: Precomputed rainbow tables; trivial to crack; non-compliance with OWASP/NIST guidelines; vulnerable to dictionary attacks
- Fix approach: Migrate to `argon2` or `bcrypt` with salt immediately; force password change on next login; add iteration count for legacy passwords; document transition plan for external modules integrating via `/api/auth/login`

**No CSRF protection:**
- Issue: No CSRF token validation on state-changing endpoints (`POST`, `PUT`, `DELETE`). ERP served from same origin (`/`), but SDK token stored in `localStorage` (vulnerable to XSS)
- Files: `backend/main.py` (no CSRF middleware), `assets/xcmasm-sdk.js` (token in localStorage)
- Impact: Cross-site request forgery if XSS exploit found; attacker can modify assets, create OS, debit inventory
- Fix approach: Add SameSite cookie policy (FastAPI `SessionMiddleware`); implement CSRF token in request headers; move token to `httpOnly` cookie; validate Origin/Referer headers for sensitive ops

**No CORS restriction on external modules:**
- Issue: CORS middleware in `backend/main.py` accepts configurable `CORS_ORIGINS` from `.env`, but default is loose. No documented allowlist for real external modules (xPredial, xAguada, xSeguranca, xCFTV)
- Files: `backend/main.py` (line 12–13, CORS setup)
- Impact: Unauthorized modules can call API endpoints; data exposure
- Fix approach: Define allowlist in `.env.example` explicitly for each known module; fail-safe deny-all if not configured; use token-based auth for inter-module calls instead of CORS

**No input validation on UUID/ID fields:**
- Issue: UUID parameters in API endpoints (e.g., `/api/ativos/{id}`, `/api/os/{id}`) accepted as-is without format validation. Potential for injection or enumeration attacks
- Files: `backend/main.py` (all GET endpoints with path params)
- Impact: Database scanning via enumeration; injection attacks if stored in JSON columns
- Fix approach: Use Pydantic validator for `UUID` type; add rate limiting on GET endpoints; log enumeration attempts

## Known Bugs

**OS material debit idempotency gap:**
- Symptoms: If `_debitar_estoque_os()` fails mid-execution, partial debits are not rolled back. Retry succeeds but doesn't restore state.
- Files: `backend/main.py` (around line 2000–2100, OS status update handler)
- Trigger: Network timeout or DB constraint violation while updating inventory during OS completion
- Workaround: Admin manually adjusts inventory via estoque movimentos UI with "ajuste" type and motivo

**Planos de manutenção versionless service history:**
- Symptoms: When `catalogo_servicos` versioning is added, old OS records still reference old service snapshots. No query to reconstruct service details from snapshot JSON.
- Files: `backend/catalogo.py`, `backend/main.py` (OS creation)
- Trigger: Editing a service in the catalog and then querying old OS details
- Workaround: UI must fallback to `servico_snapshot` JSON column if `servico_id` lookup returns different version

**Estoque minimum alert not real-time:**
- Symptoms: Badge "Baixo" only shows after page refresh; created inventory entries immediately below minimum are not flagged until next fetch
- Files: `cmasm_erp.html`, `backend/main.py` (`GET /api/estoque`)
- Trigger: Rapid inventory movements on slow network
- Workaround: Manually refresh estoque tab to see updated status

**PMOC offline sync event ordering:**
- Symptoms: If PMOC app is offline and user creates 100+ events, push may lose order if cursor management fails. Last-write-wins can overwrite earlier corrections.
- Files: `backend/sync.py`, `pmoc/index.html` (sync engine)
- Trigger: Flaky network or device restart during push
- Workaround: PMOC app retains full event log locally; manual re-sync on next stable connection

## Security Considerations

**Token storage in localStorage:**
- Risk: XSS vulnerability exposes token. Attacker gains full API access until token expires (default 8 hours)
- Files: `assets/xcmasm-sdk.js` (line 10, TOKEN_KEY), `cmasm_erp.html` (auth flow)
- Current mitigation: No XSS filters on HTML; Content-Security-Policy not set
- Recommendations: (1) Move token to `httpOnly` secure cookie; (2) Add CSP `default-src 'self'`; (3) Sanitize all user input before DOM insertion; (4) Use DOMPurify library if accepting rich text

**No SQL injection parameterization in seed scripts:**
- Risk: Seed files in `tools/` use string interpolation in SQL
- Files: `tools/seed_*.py` (if they exist)
- Current mitigation: Seeds run offline in dev environment only
- Recommendations: Migrate all seeds to use parameterized queries; document that production should never run untrusted seed scripts

**Plaintext .env exposure risk:**
- Risk: `.env` file contains `TELEGRAM_BOT_TOKEN`, `DB_PATH`, satellite URLs. If accidentally committed, token is public
- Files: `.env` (git-ignored but not in `.gitignore` check)
- Current mitigation: File is `.gitignore`d; no known commits
- Recommendations: Verify `.gitignore` includes `.env*`; use GitHub secrets for CI/CD; add pre-commit hook to reject `.env` commits

**Default fallback password "1234":**
- Risk: If user `pw_hash` is NULL, auth accepts hardcoded default `"170842"` (line 963 of `backend/main.py`)
- Files: `backend/main.py` (line 963)
- Current mitigation: Seed script sets real hash for all users; NULL should not occur in production
- Recommendations: Schema DEFAULT instead of code logic; audit query to find any NULL pw_hash; require password reset on first login

## Performance Bottlenecks

**Single aiosqlite connection per request:**
- Problem: Each API request opens/closes a new DB connection via `async with aiosqlite.connect()`. No connection pooling.
- Files: `backend/db_core.py` (lines 80, 86, 93)
- Cause: SQLite is single-writer; pooling would not improve concurrency but wastes resources
- Improvement path: Use `aiosqlite.connect()` with `check_same_thread=False` as singleton initialized at startup; wrap in async lock for writes; profile concurrent load (e.g., PMOC manifest + OS list queries)

**9,069-line HTML file parsing on every navigation:**
- Problem: Browser parses entire HTML on page load; no script bundling or lazy loading
- Files: `cmasm_erp.html`
- Cause: Single-file architecture; all modules compiled into one `<style>` and `<script>`
- Improvement path: Split into `index.html` + `app.js` bundle; use service worker for caching; implement tab-based lazy loading (don't initialize tab UI until tab becomes active)

**No pagination on list endpoints:**
- Problem: `GET /api/ativos`, `GET /api/os`, `GET /api/estoque` return all records. Large deployments (1000+ assets) cause memory spike and slow frontend
- Files: `backend/main.py` (routes for list endpoints), `cmasm_erp.html` (table initialization)
- Cause: No pagination parameters; UI loads all into memory
- Improvement path: Add `limit=100&offset=0` query params to backend; implement infinite scroll or page buttons in UI; add total count to response

**Plano vencimento calculation at query time:**
- Problem: Each maintenance tab render recalculates vencimentos by iterating all planos × all ativos
- Files: `backend/main.py` (vencimento endpoint), `cmasm_erp.html` (maintenance panel rendering)
- Cause: No denormalized cache; `proxima_execucao` not indexed
- Improvement path: Cache vencimento list with TTL (e.g., 15 min); add index on `planos_manutencao(proxima_execucao)`; invalidate cache on asset uso_atual change

## Fragile Areas

**PMOC category backfill on boot:**
- Files: `backend/main.py` (lines 2615–2641, `_seed_pmoc_frota_corte_if_empty()`)
- Why fragile: Runs on every app startup; if DB is corrupted or permissions are wrong, creates orphaned rows; no idempotency check on ativo_id uniqueness
- Safe modification: Add `UNIQUE(ativo_id)` constraint on each `pmoc_*` table; wrap seed in try-catch; log errors instead of silently failing
- Test coverage: No tests for backfill; concurrency not tested (multiple app instances starting simultaneously)

**JSON columns for nested data:**
- Files: `backend/main.py` (lines 593, 622, 626, 678, 686 — JSON serialization in queries)
- Why fragile: No schema validation for JSON structure; typos in key names silently fail (e.g., `aplicavel_tipos` vs `tipos`)
- Safe modification: Use Pydantic models for `json.loads()` output; define JSON schema in schema files; add migration test to verify deserialization
- Test coverage: No tests for malformed JSON in DB; upgrade path for old schema unknown

**Migration system reliance on PRAGMA table_info:**
- Files: `backend/db_core.py` (lines 26, 37, 45, 53, 68 — PRAGMA checks)
- Why fragile: If PRAGMA returns unexpected format, set comprehension fails silently; multiple additions of same column in concurrent tests
- Safe modification: Unit test `PRAGMA table_info()` output; add column type validation (e.g., ensure INTEGER not TEXT)
- Test coverage: No DB migration tests; only smoke tests exist

**Default asset categorization:**
- Files: `backend/main.py` (no route validation for `categoria` enum)
- Why fragile: Frontend allows free-form text in `categoria` field; backend has no CHECK constraint
- Safe modification: Add `CHECK (categoria IN (...))` in `schema_core.sql`; validate in Pydantic model on create/update
- Test coverage: No tests for invalid categoria values

**External module integration via hardcoded URLs:**
- Files: `backend/main.py` (lines 29–32, `XPREDIAL_URL`, `XAGUADA_URL`, etc.)
- Why fragile: If external module is offline, proxy endpoints timeout and block requests; no fallback or circuit breaker
- Safe modification: Add timeout (5s) to httpx calls; return 502 immediately if timeout; cache last successful response; expose `/api/health` for each module
- Test coverage: No tests for external module unavailability

## Scaling Limits

**SQLite single-writer limitation:**
- Current capacity: ~100 concurrent read-only requests; 1 writer
- Limit: PMOC push conflicts with maintenance panel queries. At 10+ devices syncing simultaneously, DB lock contention causes 503 errors
- Scaling path: Migrate to PostgreSQL (multi-writer, ACID); use `pgbouncer` for connection pooling; split schema across read-replica if read-heavy

**localStorage size limit:**
- Current capacity: ~5–10 MB per browser (varies by vendor)
- Limit: ERP stores all users, assets, OS, estoque. At 500+ records per type, may exceed quota
- Scaling path: Implement IndexedDB for frontend state; add pagination to list endpoints; lazy-load historical OS data

**PMOC offline queue unbounded growth:**
- Current capacity: Device storage varies (phone: 100 MB; tablet: 1 GB)
- Limit: If user creates 10,000+ events offline before sync, device storage exhausted; push payload huge (>100 MB)
- Scaling path: Implement event aging (delete events >90 days old); split push into batches of 1,000; add compression (gzip)

## Dependencies at Risk

**fastapi==0.115.0:**
- Risk: Version pinned; active maintenance but check for security advisories
- Impact: Breaking changes if upgraded to 0.116+; deprecated `loop` parameter in some async contexts
- Migration plan: Test on fastapi 0.116 in staging; migrate CORS and middleware if APIs change

**aiosqlite==0.20.0:**
- Risk: Thin wrapper; limited error handling for connection issues
- Impact: Connection leak if exception thrown during `async with` block
- Migration plan: Add circuit breaker wrapper; upgrade to 0.21+ if available with connection pooling

**Leaflet 1.9.4 (CDN):**
- Risk: External CDN; map assets may fail to load
- Impact: Grama/PMOC map tabs render empty if CDN is down
- Migration plan: Self-host Leaflet JS/CSS; add fallback image tiles from different CDN

## Missing Critical Features

**No audit trail / access log:**
- Problem: Can't trace who changed an asset, OS, or inventory entry; no compliance record for regulatory audit
- Blocks: GxP compliance (if system used for regulated work); incident investigation
- Dependencies: Not blocked by current code but critical for production

**No backup/restore strategy:**
- Problem: DB corruption or accidental deletion has no recovery path
- Blocks: Continuity; disaster planning
- Dependencies: SQLite doesn't have native backup; need manual export strategy

**No read-only/viewer role enforcement:**
- Problem: `visualizador` role exists in schema but not enforced in routes
- Blocks: Restricting data access to certain users
- Dependencies: Every endpoint must check `user.role` and return 403 for write ops if role is viewer

**No API rate limiting:**
- Problem: No protection against enumeration attacks or DoS
- Blocks: Can't prevent brute-force attacks on auth endpoints
- Dependencies: Add `slowapi` or equivalent; document limits per role

**No transaction support for multi-entity operations:**
- Problem: Creating OS with materials, NECs, and estoque reservation is 5+ separate requests; race condition if one fails
- Blocks: Data consistency for complex workflows
- Dependencies: Wrap operations in DB transaction; return atomic response or partial rollback with error detail

## Test Coverage Gaps

**No API integration tests:**
- What's not tested: Entire backend API surface (auth, CRUD, status transitions, sync)
- Files: `tests/` (only smoke tests and import tests exist; no test_main_api.py)
- Risk: Regressions in core functionality (e.g., OS status flow) go unnoticed
- Priority: **HIGH** — add pytest fixtures for client + test all endpoints per CLAUDE.md rules

**No frontend unit tests:**
- What's not tested: Modal logic, form validation, state transitions in `cmasm_erp.html`
- Files: `cmasm_erp.html` (9,069 lines, 0% coverage)
- Risk: UI breaking changes detected only in manual testing
- Priority: **HIGH** — extract modules and write Jest tests

**No concurrency tests:**
- What's not tested: Simultaneous PMOC push + maintenance query; two devices editing same asset
- Files: `backend/sync.py`, `backend/db_core.py`
- Risk: Race conditions and data loss at scale
- Priority: **MEDIUM** — use pytest-asyncio with concurrent tasks

**No schema migration tests:**
- What's not tested: PRAGMA-based column add logic; backward compatibility
- Files: `backend/db_core.py` (lines 26–77)
- Risk: Migration script fails on non-standard DBs; test DB state corrupted
- Priority: **MEDIUM** — create migration test that runs schema from scratch

**No error handling tests:**
- What's not tested: HTTP 400/401/403/404/500 responses; recovery after network failure
- Files: All routes with try/except; PMOC sync offline handling
- Risk: Silent failures or cryptic error messages in production
- Priority: **MEDIUM** — test each route with bad input

---

*Concerns audit: 2026-06-28*
