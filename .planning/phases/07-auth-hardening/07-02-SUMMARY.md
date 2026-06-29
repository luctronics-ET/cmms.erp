---
phase: 07-auth-hardening
plan: "02"
subsystem: auth
tags: [security, argon2, default-password, sec-02, write-path]
dependency_graph:
  requires: [07-01]
  provides: [no-default-credential-write-path, argon2-on-create, preserve-hash-on-put]
  affects: [backend/main.py, tests/test_auth.py]
tech_stack:
  added: []
  patterns: [argon2id-on-create, empty-hash-no-auth, preserve-existing-hash-on-put]
key_files:
  created: []
  modified:
    - backend/main.py
    - tests/test_auth.py
decisions:
  - "POST /api/usuarios with senha: _ph.hash(senha) [Argon2id via singleton from 07-01]; without senha: store empty string — never a default credential hash"
  - "PUT /api/usuarios: get_usuario() omits pw_hash from SELECT (by design); must do a separate DB fetch of pw_hash to preserve it when senha is absent"
  - "Row returned by get_usuario() used only for 404 guard in PUT; pw_hash fetched directly from usuarios table"
  - "Seed/sync path (/api/sync/erp line 1417) already uses u.get('pw_hash','') — no default injection; confirmed clean, no change needed"
  - "Pre-existing accounts without a hash now require explicit provisioning (PUT with senha) to authenticate — expected SEC-02 consequence documented in SUMMARY"
metrics:
  duration: "12 minutes"
  completed: "2026-06-29"
  tasks_completed: 2
  files_changed: 2
  tests_added: 6
status: complete
---

# Phase 07 Plan 02: SEC-02 Remove Default Password — Summary

**One-liner:** Removed all `_djb2("1234")` defaults from write paths; POST/PUT /api/usuarios now store Argon2id hashes when senha is provided, or empty string when absent — accounts without a provisioned password cannot authenticate.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Add failing tests for SEC-02 write-path + empty hash login guard | 11a4719 | tests/test_auth.py |
| 2 (GREEN) | Fix POST/PUT /api/usuarios — remove default-credential fallbacks | a9f6cd6 | backend/main.py |

## What Was Built

### backend/main.py — POST /api/usuarios

**Before:**
```python
pw = _djb2(body.senha) if body.senha else _djb2("1234")
```

**After:**
```python
# SEC-02: quando senha informada usa Argon2id; sem senha armazena "" (conta não autentica).
pw = _ph.hash(body.senha) if body.senha else ""
```

When `senha` is provided: password is hashed with Argon2id via the `_ph` singleton (from plan 07-01). When `senha` is absent: `pw_hash` is stored as `""` — the account cannot authenticate until a real password is set via PUT.

### backend/main.py — PUT /api/usuarios

**Before:**
```python
row = await get_usuario(uid)
pw = _djb2(body.senha) if body.senha else row.get("pw_hash", _djb2("1234"))
```

**After:**
```python
await get_usuario(uid)  # valida existência; 404 se não encontrado
existing = await db.fetch_one("SELECT pw_hash FROM usuarios WHERE id = ?", (uid,))
existing_hash = (existing or {}).get("pw_hash") or ""
pw = _ph.hash(body.senha) if body.senha else existing_hash
```

Key correction: `get_usuario()` returns only `id, nome, posto, mat, email, tel, tipo, role, ativo` — it deliberately excludes `pw_hash` for security. The old code `row.get("pw_hash", _djb2("1234"))` would always fall through to the default because `pw_hash` was never in `row`. The fix fetches `pw_hash` directly from the DB before the UPDATE.

### tests/test_auth.py — 6 new test cases

| Test | Verifies |
|------|---------|
| test_empty_pw_hash_returns_401 | empty-string pw_hash returns 401 (login guard) |
| test_create_usuario_with_senha_stores_argon2_and_can_login | POST with senha → $argon2 hash + login 200 |
| test_create_usuario_without_senha_stores_empty_hash | POST without senha → NULL/empty hash |
| test_create_usuario_without_senha_cannot_login | no-senha account returns 401 for any login attempt |
| test_put_usuario_with_senha_updates_hash_and_can_login | PUT with senha → $argon2 hash + login 200 |
| test_put_usuario_without_senha_preserves_hash | PUT without senha → hash unchanged |

### Seed/sync path confirmed clean

`/api/sync/erp` (line 1417) uses `u.get("pw_hash","")` — already correct; no default injection. No change needed.

### Pre-existing account impact (SEC-02 consequence)

Accounts seeded before this plan that have no `pw_hash` set (NULL or "") are now permanently locked out until an administrator performs a `PUT /api/usuarios/{id}` with a `senha`. This is the intended security posture: unprovisioned accounts must never have a guessable default credential.

## Test Results

```
tests/test_auth.py: 13 passed (7 from 07-01 + 6 new)
tests/test_manutencao.py: 22 passed (no regressions)
Total: 35 passed
```

TDD gate: RED commit (11a4719) → GREEN commit (a9f6cd6). Gate compliance verified.

## Verification

```
python -c "import backend.main" → OK
grep -v '^[[:space:]]*#' backend/main.py | grep -c '_djb2("1234")' → 0 (NO_DEFAULT_IN_CODE: PASSED)
python -m pytest tests/test_auth.py tests/test_manutencao.py -q → 35 passed
```

## Deviations from Plan

### Auto-fixed (Rule 1 — Bug)

**[Rule 1 - Bug] get_usuario() omits pw_hash — separate DB fetch required in PUT**

- **Found during:** GREEN phase of Task 2
- **Issue:** `get_usuario()` SELECT omits `pw_hash` by design (security). The original code `row.get("pw_hash", _djb2("1234"))` always used the default because `pw_hash` was never in `row`. The planned fix `row.get("pw_hash") or ""` would still return `""` and overwrite the existing hash with empty.
- **Fix:** Added `await db.fetch_one("SELECT pw_hash FROM usuarios WHERE id = ?", ...)` before the UPDATE to retrieve the current hash before deciding whether to preserve or replace it.
- **Files modified:** backend/main.py
- **Commit:** a9f6cd6 (included in GREEN commit, not a separate fix)

## Security Surface

All surfaces were in-plan.

| Threat ID | Status |
|-----------|--------|
| T-07-05 | Mitigated — all `_djb2("1234")` fallbacks removed from write paths; NULL/empty pw_hash hard-fails to 401 |
| T-07-06 | Mitigated — empty-hash 401 uses same generic "Credenciais inválidas" message as wrong-password |
| T-07-07 | Mitigated — POST/PUT without senha stores empty hash; account cannot authenticate |

## Known Stubs

None.

## Self-Check: PASSED

- [x] backend/main.py modified: FOUND
- [x] tests/test_auth.py modified: FOUND
- [x] Commit 11a4719 (RED) exists: CONFIRMED
- [x] Commit a9f6cd6 (GREEN) exists: CONFIRMED
- [x] `python -c "import backend.main"` succeeds: CONFIRMED
- [x] 13 auth tests pass: CONFIRMED
- [x] 22 manutencao tests pass (no regressions): CONFIRMED
- [x] NO_DEFAULT_IN_CODE check: PASSED (0 occurrences)
