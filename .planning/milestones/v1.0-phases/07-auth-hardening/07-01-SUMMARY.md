---
phase: 07-auth-hardening
plan: "01"
subsystem: auth
tags: [security, argon2, password-hashing, lazy-upgrade, sec-01]
dependency_graph:
  requires: []
  provides: [argon2-cffi-dep, dual-hash-login, lazy-upgrade-djb2-to-argon2]
  affects: [backend/main.py, requirements.txt, tests/test_auth.py]
tech_stack:
  added: [argon2-cffi==25.1.0]
  patterns: [dual-hash-detect-on-prefix, lazy-upgrade-same-request, no-default-fallback]
key_files:
  created:
    - tests/test_auth.py
  modified:
    - requirements.txt
    - backend/main.py
decisions:
  - "Use argon2-cffi directly (not passlib/pwdlib) — fewer deps, PasswordHasher API is 3-line, actively maintained"
  - "Module-level _ph = PasswordHasher() singleton — thread-safe, default params are secure (time_cost=2, memory_cost=65536, parallelism=2)"
  - "Hash type detection on $argon2 prefix (argon2-cffi emits this for all PHC-encoded argon2id hashes)"
  - "NULL/empty pw_hash returns 401 with same generic message (SEC-02 login side removed `or _djb2('1234')` fallback)"
  - "Error message unified to 'Credenciais inválidas' for all failure paths — prevents user enumeration"
  - "check_needs_rehash() called on every argon2 verify pass — future-proof if params ever tightened"
metrics:
  duration: "5 minutes"
  completed: "2026-06-29"
  tasks_completed: 2
  files_changed: 3
  tests_added: 7
status: complete
---

# Phase 07 Plan 01: Argon2id Lazy Upgrade — Auth Hardening Summary

**One-liner:** JWT login handler upgraded from djb2 to Argon2id with transparent lazy-upgrade: first legacy login re-hashes and persists in-request; subsequent logins verify via argon2 path only.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add argon2-cffi dependency + module-level PasswordHasher | 28eb298 | requirements.txt, backend/main.py |
| 2 (RED) | Add failing tests for dual-hash verify + lazy upgrade | c047abd | tests/test_auth.py |
| 2 (GREEN) | Dual-hash verify + lazy Argon2id upgrade in login handler | f90a4c8 | backend/main.py |

## What Was Built

### requirements.txt
Added `argon2-cffi==25.1.0` pinned to the version verified in STACK.md (PyPI June 2025 release). Placed above test-only deps.

### backend/main.py — New imports + singleton
```python
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHash
...
_ph = PasswordHasher()  # Argon2id, library defaults
```

### backend/main.py — Rewritten login handler (POST /api/auth/login)

Five-step structure per SEC-01 + plan constraints:

1. User lookup by mat/nome — if not found → 401 "Credenciais inválidas" (generic)
2. `stored = user.get("pw_hash")` — if NULL/empty → 401 same message (SEC-02 login side; removes `or _djb2("1234")` fallback)
3. `stored.startswith("$argon2")` → `_ph.verify(stored, senha)`; `VerifyMismatchError`/`InvalidHash` → 401; `check_needs_rehash()` + `UPDATE` if True
4. Legacy djb2: `_djb2(senha) == stored`; mismatch → 401; match → `_ph.hash(senha)` + `UPDATE usuarios SET pw_hash WHERE id` (lazy upgrade, same request)
5. Token + session INSERT + return `{token, expira_em, usuario}` — shape unchanged

`_djb2` kept unchanged as legacy-verify-only. Never generates new djb2 hashes.

### tests/test_auth.py — 7 new test cases

| Test | Verifies |
|------|---------|
| test_legacy_djb2_login_success_and_upgrades_hash | djb2 account logs in (200) AND pw_hash becomes $argon2 in DB |
| test_second_login_uses_argon2_path | second login still 200 via argon2 path |
| test_service_account_argon2_login | pre-existing $argon2 account → 200 + token |
| test_null_pw_hash_returns_401 | NULL pw_hash → 401 (no default fallback) |
| test_wrong_password_djb2_returns_401 | wrong pw against djb2 → 401 |
| test_wrong_password_argon2_returns_401 | wrong pw against argon2 → 401 |
| test_response_shape | {token, expira_em, usuario}; pw_hash excluded from usuario |

## Test Results

```
tests/test_auth.py: 7 passed
tests/test_manutencao.py: 22 passed (no regressions)
```

TDD gate: RED commit (c047abd) → GREEN commit (f90a4c8). Gate compliance verified.

## Deviations from Plan

### Auto-applied (per constraints spec)

**[Rule 2 - Missing Critical Functionality] Removed `or _djb2("1234")` default fallback in Task 2**

- **Found during:** Task 2 implementation
- **Issue:** Plan task 2 action said "leave NULL handling exactly as-is so this plan stays scoped to SEC-01" but the explicit constraints in the execution prompt override: "REMOVE the `or _djb2("1234")` default fallback NOW (this is the login-side of SEC-02; it belongs with the block rewrite)."
- **Fix:** Removed the `or _djb2("1234")` line. NULL/empty pw_hash returns 401 with the generic "Credenciais inválidas" message. The test `test_null_pw_hash_returns_401` proves this behaviour.
- **Files modified:** backend/main.py
- **Commit:** f90a4c8

**[Rule 1 - Bug] Unified error message to "Credenciais inválidas" (not "Usuário não encontrado" / "Senha incorreta")**

- **Found during:** Task 2 implementation (threat model T-07-02)
- **Issue:** Original handler used different messages for "user not found" vs "wrong password" — enables user enumeration.
- **Fix:** All 401 paths return the same generic "Credenciais inválidas" message.
- **Files modified:** backend/main.py
- **Commit:** f90a4c8

## Security Surface

All surfaces were in-plan. No new trust boundaries introduced.

| Threat ID | Status |
|-----------|--------|
| T-07-01 | Mitigated — Argon2id replaces djb2 as the authoritative stored hash |
| T-07-02 | Mitigated — djb2 is verify-only; argon2 errors all map to 401; unified error message |
| T-07-03 | Accepted — one extra UPDATE per account, once |
| T-07-04 | Mitigated — tests prove djb2 account, argon2 service account, and NULL account all behave correctly |
| T-07-SC | Mitigated — argon2-cffi==25.1.0 pinned, verified in STACK.md |

## Known Stubs

None.

## Self-Check: PASSED

- [x] tests/test_auth.py exists: FOUND
- [x] backend/main.py modified: FOUND
- [x] requirements.txt contains argon2-cffi: FOUND
- [x] Commit 28eb298 exists: FOUND
- [x] Commit c047abd exists: FOUND
- [x] Commit f90a4c8 exists: FOUND
- [x] 7 auth tests pass: CONFIRMED
- [x] 22 manutencao tests pass (no regressions): CONFIRMED
- [x] `python -c "import backend.main"` succeeds: CONFIRMED
