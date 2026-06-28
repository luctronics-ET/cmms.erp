# Project Research Summary

**Project:** xCMASM ERP — Brownfield Production-Readiness Milestone
**Domain:** CMMS (Computerized Maintenance Management System) — naval facility, FastAPI + SQLite + vanilla-JS
**Researched:** 2026-06-28
**Confidence:** HIGH

## Executive Summary

This milestone is a brownfield import-and-harden effort, not a greenfield build. The system already runs in production with 171 refrigeration machines, a service catalog, preventive OS generation, and a working PMOC field sync. Five legacy HTML screens hold approved UI that has never been wired to the real database — the job is to port those screens into `cmasm_erp.html` and back them with new FastAPI endpoints and SQLite schema, one feature at a time. Every architectural decision must preserve existing production data and API contracts consumed by the PMOC field app and satellite modules (xPredial, aguada-web).

The recommended approach is the "Copy-Section-Wire" pattern: extract HTML/CSS/JS from the legacy file, drop it into the ERP monolith as a new `<section>`, replace all `localStorage` calls with `sdk.fetch()` calls to new endpoints, and ship each feature independently before touching the next. New schema lives in `data/schema_manutencao.sql` (additive, `CREATE TABLE IF NOT EXISTS`); new endpoints live in `backend/manutencao.py` (new router, `include_router` in `main.py`). This keeps `main.py` readable and keeps the existing test suite green throughout.

The highest risks are all in the auth-hardening phase: replacing djb2 with Argon2id must use a dual-hash grace period or all 12 real users get locked out simultaneously, and service-account credentials used by external modules must be rotated atomically. The second category of risk is the monolith's global JS scope — every legacy paste must be namespace-checked before merging to avoid silent overwrites that break unrelated tabs. Both risks are well-understood and have specific prevention checklists in the research.

## Key Findings

### Recommended Stack

The existing stack (FastAPI 0.115, aiosqlite 0.20, SQLite, uvicorn, vanilla JS, no build step) is pinned and not under review. The only net-new dependencies for this milestone are `argon2-cffi 25.1.0` for password hashing and `pytest-asyncio 1.4.0` + `asgi-lifespan 2.1.0` for the expanded async test suite.

**Core technologies (new additions only):**
- `argon2-cffi 25.1.0`: Argon2id password hashing — PHC winner, memory-hard, actively maintained (June 2025); use `PasswordHasher` class directly, not via wrapper
- `pytest-asyncio 1.4.0`: async test support — required for `httpx.AsyncClient` + `ASGITransport` endpoint tests; set `asyncio_mode = "auto"` in `pyproject.toml`
- `asgi-lifespan 2.1.0`: triggers FastAPI lifespan events (including `db.init()`) inside tests — mandatory or every endpoint test fails with an uninitialized DB
- `httpx 0.27.2`: already pinned in `requirements.txt`; provides `AsyncClient` + `ASGITransport` for in-process endpoint testing

Do NOT use `passlib` (abandoned, broken on Python 3.13), `bcrypt` alone (silent truncation >72 bytes became hard error in 5.0.0), or `pwdlib` (requires Python 3.10+, project must support older versions).

### Expected Features

All five features are table stakes for a working CMMS. The legacy HTMLs provide complete, approved UI — the work is database and API wiring, not design.

**Must have (table stakes — all 5 must ship this milestone):**
- **Registrar Uso** — increments `ativos.uso_atual` per asset session; persists `uso_registros` audit log; triggers preventive alert when `uso_atual >= proximo_uso`. LOW complexity. Foundation for all other features.
- **Plano no Ativo (checkboxes)** — shows `catalogo_planos` items for the selected asset as a checklist; records which items were executed; updates `ativo_plano_estado.proximo_uso` per item. MEDIUM complexity. Requires Feature 1.
- **Estoque de Sobressalentes** — technicians' local bench stock separate from main `estoque` warehouse; CRUD + adjustment modal + movement log. LOW complexity. Independent.
- **Equipe Técnica** — team roster (name, rank, specialty) + capacity configuration (number of teams, working days, shift hours). LOW-MEDIUM complexity. Required by Feature 5.
- **Cronograma de Manutencao Preventiva** — greedy day-by-day schedule from asset backlog vs team capacity; sort by criticality; KPIs (OS count, person-hours, completion date, utilization %). MEDIUM complexity. Requires Features 1, 4; recurrent mode also requires Feature 2.

**Should have (differentiators, v1.x after initial import):**
- Cronograma recurrent mode (uses `ativo_plano_estado.proximo_uso` to schedule only due assets)
- Edit/delete `uso_registros` with horimetro recalculation
- Qualification expiry warnings in the Equipe Tecnica roster

**Defer (v2+):**
- Per-technician job assignment within the daily schedule
- Local stock auto-debit when OS closes (complex; keep manual for now)
- Procurement/PO workflow for stock replenishment
- IoT/PMOC automatic `uso_atual` sync to `uso_registros`

**Anti-features (do not build in this milestone):**
- Real-time IoT horimetro (ESP32 hardware, out of scope)
- Per-person workload balancing (team-level capacity is sufficient at this team size)
- Full replenishment workflow (low-stock badge is sufficient; PO happens outside the system)

**Residual functional work (already in scope, not new features):**
- `disparo por_tempo` (date-based preventive trigger)
- `departamento` column on `ordens_servico`
- SR prefill from service context
- `local_id` reconnection for non-refrigeration assets
- `visualizador` role enforcement (403 on writes)

### Architecture Approach

The architecture is a strict vertical-slice import pattern. Each feature is: (1) new SQL in `data/schema_manutencao.sql`, (2) new endpoints in `backend/manutencao.py`, (3) new `<section>` in `cmasm_erp.html`, (4) new tests in `tests/test_manutencao.py`. Ship one slice, verify in production, proceed. Never merge multiple slices at once. Existing API contracts (`GET /api/os`, `POST /api/os`, `GET /api/usuarios`, sync endpoints) are read-only — new response fields must be optional/nullable.

**Major components:**
1. `cmasm_erp.html` — receives new inline `<section>` blocks per feature; all new JS namespaced under module-level IIFEs to avoid global collision
2. `backend/manutencao.py` — new router for all 5 features' endpoints; follows `grama.py`/`catalogo.py` pattern; included via `app.include_router(manutencao_router)` in `main.py`
3. `data/schema_manutencao.sql` — new tables: `uso_registros`, `ativo_plano_estado`, `sobressalentes`, `sobressalentes_movimentos`, `equipe_config`, `equipe_membros`; all `CREATE TABLE IF NOT EXISTS`; added to `CoreDB._SCHEMAS`
4. `tests/test_manutencao.py` — async test suite using the new `async_app_client` fixture pattern with `LifespanManager`

**Key patterns enforced:**
- Additive migrations only: `PRAGMA table_info` before every `ALTER TABLE`; wrap in `try/except` for "duplicate column name" to handle concurrent worker startup
- No `localStorage` in new sections: every read/write goes through `sdk.fetch()`
- No DROP, no CREATE OR REPLACE: legacy data is always preserved
- Sobressalentes in a separate table from `estoque` — do not overload `estoque` with a `scope` column; mixing tables corrupts main warehouse accounting

### Critical Pitfalls

1. **Dual-hash lockout on auth migration** — Swapping `_djb2()` for Argon2 without a grace period locks out all 12 real users simultaneously. Use a discriminator: if `stored_hash.startswith("$argon2")` verify with argon2, else verify with djb2 then re-hash and store argon2. Only remove djb2 path after `SELECT COUNT(*) FROM usuarios WHERE pw_hash NOT LIKE '$argon2%'` returns 0.

2. **NULL pw_hash lockout on default removal** — Removing the `or _djb2("1234")` fallback before auditing NULL rows creates permanently locked accounts. Run `SELECT id, nome FROM usuarios WHERE pw_hash IS NULL OR pw_hash = ''` first; handle each row before removing the fallback.

3. **External module auth breakage during password rotation** — xPredial, aguada-web, and the PMOC app authenticate with service accounts. Rotating those passwords without updating the modules' `.env` files causes silent 401 failures and breaks PMOC field sync. Coordinate atomically; add a pytest contract test hitting `/api/auth/login` with service account credentials.

4. **Global JS scope collision on paste** — `cmasm_erp.html` is a 9000-line single-file app where all JS runs in one global scope. Legacy HTML defines bare globals that silently overwrite existing handlers. Before every paste: `grep -oP '(?<=window\.)\w+' cmasm_erp.html | sort | uniq -d` to detect duplicates; namespace all new code under feature-specific IIFEs.

5. **Off-by-one in `proximo_uso` calculation** — If `proximo_uso` is computed from a stale in-memory `uso_atual` rather than from the DB in the same transaction, the preventive trigger drifts. Use a single atomic SQL: `UPDATE ativos SET proximo_uso = uso_atual + ? WHERE id = ?`. Assert `proximo_uso = 2 x intervalo` after two simulated OS completions in pytest.

6. **PRAGMA race on concurrent worker startup** — With `--workers 2`, two processes both read `PRAGMA table_info` and both attempt the same `ALTER TABLE`, causing `OperationalError: duplicate column name`. Wrap every `ALTER TABLE` in `try/except` that ignores "duplicate column name" to make migrations idempotent.

7. **Premature deletion of legacy reference HTMLs** — The `.docs_cmasm/referencias/` files are the canonical source for the UI import. Deleting them before all Active requirements in PROJECT.md move to Validated leaves the team relying on `git show` archaeology. Gate deletion on explicit sign-off per feature.

## Implications for Roadmap

Based on combined research, the natural phase structure follows the feature dependency graph and risk profile:

### Phase 1: Schema + Backend Skeleton
**Rationale:** Everything else depends on having new tables and the new router in place. Zero user-visible changes; safe first step; existing tests must stay green.
**Delivers:** `schema_manutencao.sql` with all new tables; `backend/manutencao.py` stub router registered in `main.py`; `pyproject.toml` pytest-asyncio config; `async_app_client` fixture in `conftest.py`
**Addresses:** Unblocks all 5 feature slices; establishes additive migration pattern with try/except idempotency fix
**Avoids:** PRAGMA race condition (Pitfall 6 — fix the try/except here, not later)

### Phase 2: Registrar Uso
**Rationale:** Foundation feature; no dependencies; LOW complexity; unblocks Features 2 and 5 (recurrent mode). Best first import — proves the Copy-Section-Wire pattern end-to-end.
**Delivers:** `POST /api/ativos/{id}/uso` endpoint; `uso_registros` table populated; `GET /api/ativos/{id}/uso` history; section in `cmasm_erp.html`; `test_registrar_uso` passing
**Implements:** Copy-Section-Wire pattern; event delegation to avoid listener leak (Pitfall 7)
**Avoids:** Off-by-one in `uso_atual` (Pitfall 5 — use atomic DB update here)

### Phase 3: Estoque de Sobressalentes
**Rationale:** Fully independent; LOW complexity; quick win that builds import confidence without touching the preventive trigger chain.
**Delivers:** `sobressalentes` + `sobressalentes_movimentos` tables; full CRUD + adjustment endpoints; Sobressalentes tab in ERP; `test_sobressalentes` passing
**Avoids:** Sobressalentes-into-estoque anti-pattern (keep tables separate)

### Phase 4: Equipe Tecnica
**Rationale:** Low complexity; must ship before Cronograma (Phase 6 reads team capacity config). Decoupled from preventive trigger chain.
**Delivers:** `equipe_config` + `equipe_membros` tables; GET/POST/PUT endpoints; Equipe Tecnica tab in ERP; `test_equipe_tecnica` passing

### Phase 5: Plano no Ativo (checkboxes)
**Rationale:** MEDIUM complexity; requires Phase 2 (uso_atual reliably populated). Ships before Cronograma so recurrent mode has data to read.
**Delivers:** `ativo_plano_estado` populated on each maintenance registration; `POST /api/manutencao/registrar`; `GET /api/ativos/{id}/planos`; checklist UI in ERP; `test_plano_no_ativo` passing
**Avoids:** Date+usage trigger conflict (Pitfall 9 — enforce single `tipo_gatilho` per plan item at the Pydantic model level here)

### Phase 6: Cronograma de Manutencao Preventiva
**Rationale:** Depends on Phases 2, 4, 5. Ships last in the import sequence; caps the brownfield import with the highest-value manager-facing feature.
**Delivers:** `GET /api/cronograma?categoria=&tipo=inicial|recorrente`; day-by-day schedule with capacity packing; KPI summary; Cronograma tab in ERP; `test_cronograma` passing
**Avoids:** Stale `uso_atual` reads (algorithm always queries DB, not in-memory state)

### Phase 7: Residuais Funcionais
**Rationale:** After all 5 imports are verified in production, address the functional gaps in PROJECT.md Active that are not part of the legacy import.
**Delivers:** `disparo por_tempo` (date-based trigger); `departamento` on `ordens_servico`; SR prefill from service context; `local_id` reconnection for non-refrigeration assets; `visualizador` role enforcement (403 on writes)
**Avoids:** Date+usage trigger conflict (Pitfall 9 — the `por_tempo` logic must respect `tipo_gatilho` set in Phase 5)

### Phase 8: Auth Hardening
**Rationale:** Ships after all feature work is stable so auth migration does not risk breaking a partly-functional system. Short phase, high-impact.
**Delivers:** `argon2-cffi` dependency added; dual-hash verification with lazy Argon2 upgrade on login; audit query clears before djb2 fallback removal; service account credential rotation coordinated with external modules; `1234` default removed from seeds and user-creation endpoint
**Uses:** `argon2-cffi 25.1.0` (from STACK.md); dual-hash pattern (from STACK.md transition path section)
**Avoids:** Simultaneous user lockout (Pitfall 1); NULL pw_hash lockout (Pitfall 2); external module auth breakage (Pitfall 3)

### Phase 9: Legacy Cleanup
**Rationale:** Only after all Active requirements in PROJECT.md have moved to Validated.
**Delivers:** Legacy reference HTML files removed; `localStorage` grep confirms none remain in new sections; global collision check passes; milestone tag created
**Avoids:** Premature deletion (Pitfall 10 — explicit exit criterion gate)

### Phase Ordering Rationale

- Phase 1 first because every subsequent phase depends on the schema and router skeleton existing.
- Registrar Uso (Phase 2) before Plano (Phase 5) because `ativo_plano_estado` records are only meaningful when `uso_atual` is reliably tracked.
- Equipe Tecnica (Phase 4) before Cronograma (Phase 6) because the schedule algorithm reads `equipe_config` for daily capacity.
- Sobressalentes (Phase 3) placed third as a confidence-building quick win between the two dependency chains.
- Residuais (Phase 7) after all imports — avoids functional gaps blocking the import loop; `por_tempo` trigger also depends on `ativo_plano_estado` populated in Phase 5.
- Auth hardening (Phase 8) last among code phases — auth migration risk is highest when the system is stable; shipping it mid-import would compound risk.
- Cleanup (Phase 9) last — cannot delete reference files until everything is verified.

### Research Flags

Phases needing deeper research during planning:
- **Phase 8 (Auth Hardening):** External module credential enumeration requires reading `MODULOS_EXTERNOS.md` and each module's `.env.example`; coordinate timing with aguada-web and xPredial maintainers before execution. The dual-hash code pattern is fully specified in STACK.md — no additional implementation research needed.
- **Phase 7 (Residuais — por_tempo trigger):** The exact data model for date-based preventive triggers (`proxima_execucao` column location and type) needs confirmation against `data/schema_catalogo.sql` before implementation. Pitfall 9 describes the interaction risk with usage triggers.

Phases with standard patterns (skip research-phase):
- **Phase 1 (Schema skeleton):** Additive migration pattern is fully documented in ARCHITECTURE.md; no unknowns.
- **Phases 2-6 (Feature imports):** Copy-Section-Wire pattern is explicit; legacy HTML sources exist and are analyzed; endpoints follow established `grama.py`/`catalogo.py` convention.
- **Phase 9 (Legacy cleanup):** Mechanical git operations; no research needed.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | MEDIUM | argon2-cffi and pytest-asyncio versions verified from PyPI; API patterns from official docs; pwdlib Python version constraint is a firm blocker if Python < 3.10 needed |
| Features | HIGH | Legacy HTML fully analyzed; existing schema fully mapped; CMMS domain patterns well-established; feature boundaries are clear |
| Architecture | HIGH | Based on direct codebase inspection of backend/db_core.py, main.py, schema files; no external research needed; patterns are well-established in existing code |
| Pitfalls | HIGH | Grounded in actual code (main.py line 963 for djb2 path, db_core.py lines 26-76 for PRAGMA pattern); not theoretical |

**Overall confidence:** HIGH

### Gaps to Address

- **Python version floor:** CLAUDE.md says Python 3.7+ but `pwdlib` requires Python 3.10+. Research correctly excludes pwdlib and recommends `argon2-cffi` directly. Confirm the actual runtime Python version before Phase 8 to ensure `argon2-cffi 25.1.0` compatibility (requires Python 3.8+).
- **`proxima_execucao` column location:** The `por_tempo` trigger (Phase 7) reads a date from either `planos_manutencao` or `ativo_plano_estado`. Confirm which table holds this field and its type before writing the Phase 7 trigger logic.
- **Service account enumeration:** Before Phase 8, explicitly list every service account credential used by xPredial, aguada-web, and PMOC; check current `pw_hash` format for each. This audit is a Phase 8 pre-condition, not researchable upfront without reading the live DB.
- **Event listener leak assessment:** The existing `erp-manutencao.js` and `erp-refrigeracao.js` tabs may already have the listener-leak pattern. A quick audit at the start of each import phase (Phases 2-6) will confirm whether delegation is needed before each paste.

## Sources

### Primary (HIGH confidence)
- `backend/db_core.py` lines 26-77 — PRAGMA migration pattern (direct code inspection)
- `backend/main.py` lines 816-823, 952-967 — djb2 implementation and login handler
- `data/schema_core.sql`, `data/schema_catalogo.sql` — existing table structures
- `.docs_cmasm/referencias/CMASM_Gestao_v2.html` (1495 lines) — Features 1-3 UI source
- `.docs_cmasm/referencias/cmasm13-govbr-v8_3.html` (3298 lines) — Features 4-5 UI source
- `.planning/PROJECT.md` — scope and constraints
- `.planning/codebase/CONCERNS.md`, `TESTING.md` — documented bugs and test gaps

### Secondary (MEDIUM confidence)
- PyPI: argon2-cffi 25.1.0 (Jun 2025), pytest-asyncio 1.4.0 (May 2026), asgi-lifespan 2.1.0 — version numbers verified
- FastAPI official docs (oauth2-jwt tutorial, async-tests guide) — argon2 recommendation, async client pattern
- pytest-asyncio readthedocs 1.4.0 — `asyncio_mode = "auto"` config reference
- FastAPI GitHub discussion #11773 — passlib abandonment, team move to pwdlib/argon2

### Tertiary (LOW confidence)
- pwdlib Python 3.10+ constraint: from PyPI metadata; runtime Python version on the server not confirmed — validate before Phase 8

---
*Research completed: 2026-06-28*
*Ready for roadmap: yes*
