# Pitfalls Research

**Domain:** Brownfield FastAPI + SQLite + vanilla-JS ERP — production hardening, legacy UI import, auth migration
**Researched:** 2026-06-28
**Confidence:** HIGH (grounded in actual code at backend/main.py, backend/db_core.py, .planning/codebase/)

---

## Critical Pitfalls

### Pitfall 1: Live bcrypt migration locks out every user simultaneously

**What goes wrong:**
The current login handler (main.py line 963) checks `user.get("pw_hash") or _djb2("1234")` — if `pw_hash` is NULL it falls back to the default. When you swap `_djb2(body.senha)` for `bcrypt.checkpw()` without a grace-period, every user whose `pw_hash` column still holds a djb2 hex string (`"170842"`, etc.) gets HTTP 401 on their next login. All 12 seeded real users are locked out simultaneously. There is no session-expiry buffer — existing Bearer tokens last up to 8 hours, so the outage hits when those tokens expire.

**Why it happens:**
Developers migrate the verification function first and forget that the stored hashes in the `usuarios` table are still djb2 hex, not bcrypt `$2b$...` strings. The column is named `pw_hash` with no format discriminator, so the new code cannot tell which algorithm was used to produce the stored value.

**How to avoid:**
Use a dual-hash grace period. The verification logic should be:
1. If `pw_hash` starts with `$2b$` — verify with bcrypt.
2. Otherwise — verify with djb2 (legacy path); on success, immediately re-hash and store the bcrypt value, then return the token.
3. Only after all users have logged in at least once (all rows start with `$2b$`) can the legacy path be removed.
Write a migration-state query: `SELECT COUNT(*) FROM usuarios WHERE pw_hash NOT LIKE '$2b$%' AND pw_hash IS NOT NULL` and block the removal until count = 0.

**Warning signs:**
- Login endpoint suddenly returns 401 for previously valid credentials after any deploy.
- `pw_hash` column values do not start with `$2b$` for any row — means that user will be broken.
- External modules (xSeguranca, aguada-web, xPredial) that call `POST /api/auth/login` with service accounts start reporting authentication failures.

**Phase to address:**
Security phase (bcrypt migration). Must be the first item in that phase, before removing the default password.

---

### Pitfall 2: Removing the default-password fallback before auditing NULL pw_hash rows

**What goes wrong:**
Line 963: `expected = user.get("pw_hash") or _djb2("1234")`. The `or` branch fires when `pw_hash` is NULL or empty string. Removing this line (to eliminate the default) before auditing for NULL rows means any user account with a NULL `pw_hash` gets HTTP 401 forever with no recovery path except direct DB surgery.

**Why it happens:**
The CONCERNS.md documents that "seed script sets real hash for all users; NULL should not occur in production" — but this is an assumption, not a verified constraint. Accounts created via `POST /api/usuarios` without a `senha` field produce NULL `pw_hash` (the `UsuarioIn` model has `senha: Optional[str] = None` and the insert does not substitute a default).

**How to avoid:**
Before removing the fallback:
1. Run `SELECT id, nome, mat, pw_hash FROM usuarios WHERE pw_hash IS NULL OR pw_hash = ''` against `core.db`.
2. For each NULL row, either set a forced-reset bcrypt hash or disable the account (`ativo = 0`).
3. Add a schema-level constraint: `ALTER TABLE usuarios ADD COLUMN pw_hash TEXT NOT NULL DEFAULT ''` — but this requires a migration since existing rows would violate it. Instead, add a `CHECK(pw_hash != '')` in `schema_core.sql` so new inserts cannot create NULL hashes.
4. Only then remove the `or _djb2("1234")` fallback.

**Warning signs:**
- Any row in `usuarios` with `pw_hash IS NULL` is a time-bomb.
- The `/api/usuarios` POST handler does not enforce a non-null password — new accounts created through the ERP UI can silently produce NULL rows.

**Phase to address:**
Security phase — sub-step within bcrypt migration. Audit must run before fallback removal.

---

### Pitfall 3: Breaking external modules that POST /api/auth/login

**What goes wrong:**
xPredial (port 8002), aguada-web (port 8001), and the PMOC app all authenticate via `POST /api/auth/login` using fixed service-account credentials that were set up with djb2 hashes. After bcrypt migration and a forced password rotation, these modules continue sending the old plaintext password. Their tokens expire in 8 hours and they are locked out permanently until their own configuration is updated — potentially taking down PMOC field sync with no visible error to users.

**Why it happens:**
Service accounts are often treated as set-and-forget. The modules store credentials in their own `.env` files (`XCORE_URL`, credentials). There is no contract test that verifies external auth still works after a hash migration.

**How to avoid:**
Before rotating any password used by an external module:
1. Enumerate service accounts used by external modules (check `MODULOS_EXTERNOS.md` and each module's `.env.example`).
2. Coordinate rotation: update the external module's `.env` credential at the same time as the DB row.
3. Add a pytest integration test that hits `POST /api/auth/login` with the service account credentials from env — this test will catch drift immediately.
4. Announce the rotation to maintainers of xSeguranca and aguada-web before executing.

**Warning signs:**
- PMOC sync push returns 401 from the field app.
- xPredial logs show `401 Unauthorized` on its upstream calls.
- Any module that was working stops emitting OS records via `POST /api/os`.

**Phase to address:**
Security phase — coordinate external module credential rotation as a checklist item before deployment.

---

### Pitfall 4: PRAGMA table_info set comprehension silently skipping columns on concurrent app starts

**What goes wrong:**
`db_core.py` lines 26–76 run `PRAGMA table_info(table)` and build a set of existing column names. If two FastAPI worker processes (e.g., `uvicorn --workers 2`) call `db.init()` at the same time, both see the column missing and both attempt `ALTER TABLE ativos ADD COLUMN subtipo TEXT`. SQLite raises `OperationalError: duplicate column name: subtipo` on the second worker. The app crashes at startup; `core.db` is left in a partially-initialized state.

**Why it happens:**
The PRAGMA check and the ALTER are not atomic — there is a TOCTOU window. aiosqlite does not serialize across process boundaries; only within a single process via the async lock.

**How to avoid:**
Wrap each ALTER TABLE in a try/except that catches `OperationalError` with "duplicate column name":
```python
try:
    await db.execute(ddl)
except Exception as e:
    if "duplicate column name" not in str(e).lower():
        raise
```
This makes each column-add idempotent regardless of race. Alternatively, run migrations in a separate startup script (not in `CoreDB.init()`) before the ASGI app starts, using a file-lock (`fcntl.flock`) to prevent concurrent runs.

**Warning signs:**
- `uvicorn` with `--workers N > 1` crashes on startup with `OperationalError: duplicate column name`.
- Running `pytest` in parallel (`-n auto`) causes test isolation failures because multiple test processes call `CoreDB.init()` against shared tmp paths.
- A migration that was added to `db_core.py` appears in PRAGMA output but the app still crashes.

**Phase to address:**
Quality/testing phase — add a migration idempotency test that runs `db.init()` twice against the same DB and asserts no error.

---

### Pitfall 5: Production core.db schema diverging from schema_core.sql during additive migration

**What goes wrong:**
`schema_core.sql` is applied via `executescript` at startup. SQLite `CREATE TABLE IF NOT EXISTS` is idempotent, but any `CHECK`, `DEFAULT`, or `FOREIGN KEY` constraint added to `schema_core.sql` after the table was first created will never apply to the existing production table. The production table and the schema file diverge silently — `PRAGMA table_info` shows the column exists (from the initial CREATE) but without the new constraint.

**Why it happens:**
Developers add a constraint to `schema_core.sql` thinking it will be applied on next startup. It will only apply on a fresh DB (tests), not on the production DB that was created months earlier. The result is tests pass (fresh DB gets the constraint) but production does not have it.

**How to avoid:**
After adding any constraint to `schema_core.sql`, also add an explicit check in `db_core.py`'s migration block:
- For CHECK constraints: verify with `PRAGMA table_info` that the type matches; if not, SQLite does not support `ALTER TABLE ADD CONSTRAINT` — document the mismatch and plan a table-rebuild migration if the constraint is critical.
- For DEFAULT values on new columns: the `ALTER TABLE ... ADD COLUMN col TEXT DEFAULT 'x'` form does carry the default — verify this works in a migration test.
Document the known divergence list in a `MIGRATIONS.md` file.

**Warning signs:**
- A test that creates a fresh DB passes a constraint check but production does not enforce it.
- `PRAGMA table_info(ativos)` on production shows a column with no DEFAULT while `schema_core.sql` declares one.
- `INSERT` without specifying `criticidade` stores NULL in production but stores `'operacional'` in tests.

**Phase to address:**
Any schema-change work (residuals phase, import phase). Add a migration test fixture that runs against a pre-existing DB snapshot (copy of `core.db` schema structure without PII) alongside the fresh-DB test.

---

### Pitfall 6: Global scope collisions when porting legacy HTML into the 9000-line ERP monolith

**What goes wrong:**
`cmasm_erp.html` attaches all state and handlers to `window` (e.g., `window.predialAPI`, `window.openModal`). Legacy HTML files (`CMASM_Gestao_v2.html`, `cmasm13-govbr-v8_3.html`) define their own globals with the same or similar names. When pasted into the monolith as a new tab section, the new `window.openModal` or `window.renderTable` silently overwrites the existing one. Features that were working before the paste break without any error message.

**Why it happens:**
There is no module system — all JS runs in a single global scope. `<script>` tags in the monolith execute in document order; the last definition wins. Variable name collisions are invisible at paste-time and only manifest at runtime on a specific user action.

**How to avoid:**
- Before pasting any legacy JS block, `grep -n "window\.\|var \|let \|const \|function " legacy.html` and diff against the same pattern in `cmasm_erp.html`. Resolve any collision before merging.
- Namespace new feature code: `window.EquipeTecnica = (function() { ... })();` instead of bare globals.
- Run the brace-balance smoke test (`test_manutencao_smoke.py`) after each paste to catch obvious JS syntax breaks early.
- Add an id-collision check to the smoke test: `assert len(set(ids)) == len(ids)` over all `id="..."` attributes in the merged HTML.

**Warning signs:**
- A previously working tab stops responding to clicks after a new section is added — its handler was overwritten.
- `console.error: Uncaught TypeError: X is not a function` where X was defined in the original monolith.
- Duplicate `id="modal-detalhes"` or similar causes `document.getElementById` to return the wrong element.

**Phase to address:**
Legacy UI import phase — apply the namespace check and id-collision smoke test before each merge, not after.

---

### Pitfall 7: Event-handler leaks on tab-switch re-render in the monolith

**What goes wrong:**
When a tab is activated in `cmasm_erp.html`, the pattern is typically to call a render function that rewrites `innerHTML` and re-attaches event listeners via `addEventListener`. If the tab is switched away and back without destroying the old listeners (because the container element is kept alive, not replaced), each tab activation doubles the listener count. After 10 switches, a single button click fires 10 handler executions — producing 10 API calls, 10 modal opens, or 10 `uso_atual` increments.

**Why it happens:**
`innerHTML` replacement destroys child DOM nodes but the listeners are attached to the container — which is never replaced. `removeEventListener` is skipped because the anonymous callback reference is lost. This is endemic in vanilla-JS SPAs without a framework.

**How to avoid:**
- Use event delegation: attach one listener to the stable container, not to the dynamic children. `container.addEventListener('click', (e) => { if (e.target.matches('.btn-registrar')) ... })`.
- Or track and explicitly remove: store listener refs in a module-level map keyed by tab id; call `remove()` before `add()`.
- The `erp-manutencao.js` and `erp-refrigeracao.js` files are the highest-risk areas since they have the most interactive tabs.

**Warning signs:**
- API call count (visible in Network tab) multiplies per tab switch for a given action.
- Estoque debits happen multiple times for a single OS completion click.
- `uso_atual` increments by 2x or 4x after rapid tab switches.

**Phase to address:**
Legacy UI import phase — when adding new tab sections, audit the existing pattern for the new tab and enforce delegation from the start, not as a cleanup afterward.

---

### Pitfall 8: Off-by-one in uso-based preventive schedule (proximo_uso calculation)

**What goes wrong:**
The preventive rule (Rules.md): `proximo_uso = uso_atual + intervalo` when an OS is completed. If the completion handler reads `uso_atual` from the DB at the moment of OS completion, but the OS itself also increments `uso_atual` as part of the debit flow, the new `proximo_uso` is calculated from an already-incremented base. The next preventive fires one `intervalo` early. At 250h intervals this is invisible for years then suddenly wrong.

A second variant: the trigger condition `uso_atual >= proximo_uso` is evaluated on `GET /api/manutencao/vencimentos` — if `proximo_uso` was stored as an integer and `uso_atual` is a float (km/h to decimal precision), floating-point comparison may skip the trigger: e.g., `uso_atual = 250.0`, `proximo_uso = 250` — comparing a float to an int in SQLite uses numeric affinity and works, but if `proximo_uso` is stored as TEXT (no column type check in migration) the comparison is lexicographic and `'99' > '250'`.

**How to avoid:**
- Read `uso_atual` from the DB immediately before computing `proximo_uso`, after all other updates in the same transaction. Use a single SQL update:
  `UPDATE ativos SET proximo_uso = uso_atual + ? WHERE id = ?` — this reads the already-committed `uso_atual` in one atomic step.
- Assert column type: `PRAGMA table_info(planos_manutencao)` must show `proximo_uso` as REAL or INTEGER, never TEXT.
- Write a pytest that simulates: create asset at uso=0, complete OS, assert proximo_uso = intervalo, complete second OS, assert proximo_uso = 2 * intervalo (no double-count).

**Warning signs:**
- Preventive OS fires before expected hours for a machine that had a recent completion.
- `proximo_uso` values in the DB that do not equal a clean multiple of the plan's `intervalo`.
- SQLite query `SELECT proximo_uso, typeof(proximo_uso) FROM planos_manutencao` returns `text` — the comparison is broken.

**Phase to address:**
Residuals phase (disparo por_tempo + trigger logic). This is the highest-risk business-logic correctness issue in the scheduler.

---

### Pitfall 9: Date-trigger (por_tempo) interacting incorrectly with uso-trigger (por_uso) on the same plan

**What goes wrong:**
A plano can have both `tipo_gatilho = 'por_tempo'` and `por_uso` semantics (the schema supports both). If the date-based trigger fires and creates a preventiva OS, and the completion handler resets `proximo_uso` (usage-based field), the usage counter is reset to `uso_atual + intervalo` at the wrong base point. Over 6 months the two triggers drift: one says "due in 200h", the other says "due in 30 days" — and the UI shows conflicting "vencido" badges.

**How to avoid:**
- Enforce a single trigger type per plano at the model level: if `tipo_gatilho = 'por_tempo'` then `proximo_uso` updates are skipped; if `por_uso` then date-based `proxima_execucao` is not touched.
- Add a Pydantic validator on `PlanoIn` that raises if both `intervalo_uso` and `intervalo_dias` are set without an explicit `tipo_gatilho` value.
- Smoke test: create a plan with both fields, complete the OS, assert only the relevant field was updated.

**Warning signs:**
- A machine appears in both the usage-overdue list and the date-overdue list simultaneously after a maintenance completion.
- `proxima_execucao` and `proximo_uso` are both reset in the same completion handler with no conditional logic.

**Phase to address:**
Residuals phase (disparo por_tempo implementation). Clarify the trigger-type contract before writing the date-trigger logic.

---

### Pitfall 10: Premature deletion of legacy reference files (.docs_cmasm/ and .delete/)

**What goes wrong:**
The git status shows `.docs_cmasm/` files as deleted (D in index). These HTMLs (`CMASM_Gestao_v2.html`, `cmasm13-govbr-v8_3.html`) are the canonical source for the UI to be imported — "Visual/layout legado já bom; copiar front e ligar ao banco real." If these files are committed as deleted before the UI import is complete, the team loses the reference. Recovering them requires a `git show` against an older commit — an error-prone manual step under deadline pressure.

A subtler variant: partial import where only 60% of a legacy HTML's features have been ported. The developer deletes the reference file after porting the first visible tab, then later discovers that a scheduling algorithm or CSS class was still needed from the original.

**How to avoid:**
- Stage the deletion of each legacy HTML only after explicitly checking off every feature in the import scope against `PROJECT.md § Active` requirements.
- Keep a `.docs_cmasm/referencias/` (already exists as `??` untracked in git status) as the permanent read-only archive — never delete from there, only from the `D`-staged top-level entries.
- Before committing any reference file deletion, run a `grep -r "Gestao_v2\|cmasm13-govbr" assets/ pmoc/ cmasm_erp.html` to confirm no code still references the filename.

**Warning signs:**
- A requirement in `PROJECT.md` is marked "done" but the implementation team cannot find where the original UI logic came from.
- CSS class names in the new code that are not in `assets/erp-module-shell.css` and not in any local style block — they came from the deleted legacy HTML.
- The `git status` `D` entries are committed before the corresponding Active items are moved to Validated.

**Phase to address:**
Legacy UI import phase — make reference file deletion an explicit exit criterion gate, not something that happens during cleanup commits.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Keep djb2 for service accounts during migration | No external module breakage | Permanent dual-path in auth code if never cleaned up | Only as explicit grace period with a removal date committed |
| Paste legacy JS directly into monolith without namespacing | Fast feature delivery | Silent global overwrites break unrelated tabs | Never — namespace first, paste second |
| Skip migration test for new column on existing DB | Faster schema work | Test passes (fresh DB), production silently lacks constraint | Never for CHECK/DEFAULT — always verify on existing DB |
| Use `window.openModal` for new modals | Consistent with existing code | Overwrite risk with any future paste | Only if the name is unique and grep-verified |
| Read `uso_atual` from request payload instead of DB in completion handler | Simpler code | Off-by-one in proximo_uso when payload is stale | Never for preventive schedule calculation |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| External modules calling POST /api/auth/login | Assume service accounts are unaffected by hash migration | Enumerate service accounts before migration; rotate credentials atomically with DB update |
| PMOC sync after bcrypt migration | PMOC has its own auth token; assume it still works | PMOC tokens are Bearer tokens from sessoes — not affected unless service account password changes |
| xPredial calling GET /api/usuarios | Assume API contract is stable — it is | Only risk is if the `role` field name changes during auth refactor; verify response shape in a contract test |
| Legacy HTML import into ERP monolith | Import CSS in `<style>` block without scoping | Scope all imported CSS under a tab-specific class: `.tab-equipe-tecnica .btn {}` |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| bcrypt cost factor too high | Login takes 2–5 seconds; all users complain simultaneously | Use `bcrypt.gensalt(rounds=12)` — standard; test latency in dev before deploying | Any rounds > 14 on the current server hardware |
| Vencimento calculation iterating all planos × ativos on every tab render | Maintenance tab takes 3+ seconds to open with 171 machines × N plans | Add index on `proximo_uso`; cache in `window.__vencimentos` with a 60s TTL | Already painful at 171 machines if each has 3+ plans |
| Monolith re-parses 9000 lines on page reload after each feature addition | Page load time increases linearly | Do not add more than necessary; extract large new JS sections to external files | Already at risk; each 500-line paste adds ~100ms parse time |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Removing `or _djb2("1234")` before auditing NULL rows | Permanent lockout of accounts with NULL pw_hash | Audit query before removal; add NOT NULL constraint to schema |
| Storing bcrypt hash in same column as djb2 without format discriminator | Cannot distinguish which algorithm to use for verification | Check `pw_hash.startswith('$2b$')` as the discriminator — document this invariant |
| Rotating passwords for all users at once (forced reset on first login) | If the forced-reset UI is broken, all users are locked out simultaneously | Test the forced-reset flow with one non-admin account before deploying to all |
| Using `secrets.token_urlsafe(32)` for session tokens without expiry enforcement | Long-lived tokens if expiry column is not checked | The current query `WHERE expira_em > datetime('now')` is correct — do not remove this condition during any auth refactor |

## "Looks Done But Isn't" Checklist

- [ ] **bcrypt migration:** Verify `SELECT COUNT(*) FROM usuarios WHERE pw_hash NOT LIKE '$2b$%' AND pw_hash IS NOT NULL` = 0 before removing the djb2 fallback path
- [ ] **Default password removal:** Verify `SELECT COUNT(*) FROM usuarios WHERE pw_hash IS NULL OR pw_hash = ''` = 0 before removing the `or _djb2("1234")` branch
- [ ] **Legacy UI import:** Verify every Active requirement in PROJECT.md has moved to Validated before committing deletion of the legacy HTML source
- [ ] **Schema migration:** Verify `PRAGMA table_info(table)` on a copy of `core.db` (not just a fresh test DB) shows all expected columns with correct types
- [ ] **Preventive schedule:** Verify `proximo_uso` is updated in the same DB transaction as `uso_atual`; never computed from a stale in-memory value
- [ ] **Global collision check:** Run `grep -oP '(?<=window\.)\w+' cmasm_erp.html | sort | uniq -d` — any duplicates are overwrite collisions
- [ ] **Event listener leak:** Open the new tab, switch away, switch back 5 times, trigger an action, confirm exactly 1 API call fires in Network tab

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| All users locked out after bcrypt migration | HIGH | `sqlite3 core.db "UPDATE usuarios SET pw_hash = '<djb2_of_1234>' WHERE pw_hash NOT LIKE '$2b$%'"` to restore temporary access; then re-run migration correctly |
| Production DB has NULL pw_hash rows after lockout | MEDIUM | `sqlite3 core.db "UPDATE usuarios SET pw_hash = '<bcrypt_of_forced_password>' WHERE pw_hash IS NULL"` + notify affected users |
| Global variable overwrite breaks existing tab | MEDIUM | `git bisect` to find the paste commit; rename the colliding variable; redeploy |
| proximo_uso computed from wrong base — records drifted | MEDIUM | Audit `proximo_uso` for each machine against its `intervalo` and last OS completion `uso_atual`; correct rows via admin estoque-movimentos-style adjustment endpoint |
| Legacy HTML reference file deleted prematurely | LOW | `git show HEAD~N:path/to/file > /tmp/recovered.html` — locate via `git log --diff-filter=D --name-only` |
| PRAGMA migration fails on concurrent startup | LOW | Kill extra workers; restart single worker; the try/except fix makes it idempotent going forward |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| bcrypt migration locks out users (dual-hash) | Security phase | `startswith('$2b$')` discriminator in code; login test with legacy-hash user |
| NULL pw_hash lockout | Security phase | Audit query returns 0 before PR merge |
| External module auth breakage | Security phase | pytest contract test hitting /api/auth/login with service account creds |
| PRAGMA race condition on concurrent init | Quality/testing phase | Migration idempotency test: `db.init()` twice, no error |
| Production schema diverges from schema_core.sql | Any schema-change phase | Migration test uses DB snapshot, not just fresh DB |
| Global scope collision on paste | Legacy UI import phase | id-collision smoke test added to test_manutencao_smoke.py before first merge |
| Event handler leak on tab re-render | Legacy UI import phase | Manual network-tab verification after each new tab; delegation pattern enforced |
| Off-by-one in proximo_uso (usage trigger) | Residuals phase | pytest: complete OS twice, assert proximo_uso = 2 × intervalo |
| Date + usage trigger conflict on same plan | Residuals phase | Pydantic validator on PlanoIn; completion handler conditional on tipo_gatilho |
| Legacy reference file deleted prematurely | Legacy UI import phase | Exit criterion: all Active items Validated before deletion commit |

## Sources

- `backend/db_core.py` lines 26–77 — PRAGMA-based migration pattern (direct code inspection)
- `backend/main.py` lines 816–823, 952–967 — djb2 implementation and login handler (direct code inspection)
- `.planning/codebase/CONCERNS.md` — documented bugs: PRAGMA fragility, default-password fallback, monolith scope pollution
- `.planning/codebase/TESTING.md` — test isolation patterns and coverage gaps
- `.planning/PROJECT.md` — scope constraints and production-data preservation requirements
- `CLAUDE.md` — architecture invariants, migration rules, design system

---
*Pitfalls research for: xCMASM ERP — brownfield production hardening milestone*
*Researched: 2026-06-28*
