---
phase: 07-auth-hardening
fixed_at: 2026-06-29T06:45:00Z
review_path: .planning/phases/07-auth-hardening/07-REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 07: Auth Hardening — Code Review Fix Report

**Fixed at:** 2026-06-29T06:45:00Z
**Source review:** `.planning/phases/07-auth-hardening/07-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 4 (CR-01, WR-01, WR-02, IN-01)
- Fixed: 4
- Skipped: 0

**Test result:** 38 passed, 0 failed (14 auth + 24 manutencao)
- 13 original auth tests now passing (were erroring pre-fix due to missing pmoc table DDL)
- 1 new CR-01 regression test added (`test_malformed_argon2_hash_returns_401_not_500`)
- 24 manutencao tests unchanged

---

## Fixed Issues

### CR-01: `VerificationError` not caught — HTTP 500 on malformed `$argon2` stored hash

**Files modified:** `backend/main.py`
**Commit:** `264f3d2`
**Applied fix:**
- Added `VerificationError` to the import: `from argon2.exceptions import VerifyMismatchError, InvalidHash, VerificationError`
- Changed `except (VerifyMismatchError, InvalidHash):` to `except (VerificationError, InvalidHash):` at line 1006
- `VerificationError` is the parent class of `VerifyMismatchError` and is raised by `_ph.verify()` when the stored hash starts with `$argon2` but is malformed or truncated (e.g., `"$argon2id$"`, `"$argon2id$v=19$"`, etc.). Previously these escaped as HTTP 500. Now all return 401 with the uniform generic message.
- Added explanatory comment to the except clause.

**Regression test added (in IN-01 commit):** `test_malformed_argon2_hash_returns_401_not_500` — seeds accounts with 4 truncated `$argon2` hashes and asserts each returns 401 with `"inválidas"` in detail.

---

### WR-01: Timing oracle for username enumeration (user-not-found branch ~0ms vs wrong-password ~100ms)

**Files modified:** `backend/main.py`
**Commit:** `264f3d2` (same commit as CR-01 — both touch `backend/main.py`)
**Applied fix:**
- Added a module-level constant `_DUMMY_HASH: str = _ph.hash("dummy-constant-time-placeholder")` immediately after the `_ph = PasswordHasher()` singleton (around line 840)
- Added a dummy `_ph.verify(_DUMMY_HASH, body.senha)` call (wrapped in `try/except Exception: pass`) on the user-not-found branch before `raise HTTPException(401, ...)`
- This equalizes response time between "user does not exist" and "user exists but wrong password" — both now run the full ~100ms Argon2id verify before returning 401, preventing username enumeration via timing side-channel.

---

### WR-02: Seed scripts write djb2 `"170842"` and advertise `"1234"` as durable credential

**Files modified:** `tools/seed_usuarios.py`, `tools/seed_from_backup.py`, `tools/seed_completo.py`
**Commit:** `d00b922`
**Applied fix:**

`tools/seed_usuarios.py`:
- Added `from argon2 import PasswordHasher`
- Replaced `DEFAULT_PW = "170842"` (djb2 literal) with:
  ```python
  INITIAL_PW = "ChangeMe@Boot"
  _ph_seed = PasswordHasher()
  DEFAULT_PW = _ph_seed.hash(INITIAL_PW)
  ```
- Changed final print from `"Senha padrão: 1234"` to `f"Senha bootstrap: {INITIAL_PW!r} (Argon2id) — ALTERE APÓS O PRIMEIRO LOGIN"`

`tools/seed_from_backup.py`:
- Added `from argon2 import PasswordHasher`
- Replaced `DEFAULT_PW = "170842"  # djb2-hex de "1234"` with Argon2id bootstrap hash
- Updated two print statements: `"senha padrão: 1234"` and `"Login: qualquer nome · senha: 1234"` now reference `INITIAL_PW` and include the "ALTERE APÓS O PRIMEIRO LOGIN" warning

`tools/seed_completo.py`:
- Added `from argon2 import PasswordHasher`
- Removed `DEFAULT_PW = "170842"`, the `djb2_hex()` function, and the `assert djb2_hex('1234') == DEFAULT_PW` guard (djb2 generation has no place in seed scripts)
- Replaced with Argon2id bootstrap hash using same `INITIAL_PW = "ChangeMe@Boot"` pattern
- Updated final print block to reference `INITIAL_PW` and warn to change after first login

All three scripts remain runnable; `argon2-cffi` is already in `requirements.txt`.

---

### IN-01: Vacuous assertion `assert X or resp.status_code == 401` in `test_empty_pw_hash_returns_401`

**Files modified:** `tests/test_auth.py`, `data/schema_core.sql`
**Commit:** `4956d03`
**Applied fix (IN-01):**
- Replaced `assert "inválidas" in body.get("detail", "").lower() or resp.status_code == 401` (always True — right operand was a repeated assertion) with:
  ```python
  assert "inválidas" in body.get("detail", "").lower(), (
      f"Expected 'inválidas' in detail, got: {body.get('detail')!r}"
  )
  ```
- The message check is now actually enforced; a change to the error string would cause the test to fail.

**Bonus fix (pre-existing blocking issue):** Added `CREATE TABLE IF NOT EXISTS` DDL for `pmoc_transportes`, `pmoc_corte`, and `pmoc_fonoclama` to `data/schema_core.sql`. These tables are queried in the `_seed_pmoc_frota_corte_if_empty()` startup function but were missing from all schema files, causing `sqlite3.OperationalError: no such table: pmoc_transportes` on every test run — all 13 auth tests errored before this fix (pre-existing, unrelated to the review findings, but blocking test verification). Tables use idempotent `IF NOT EXISTS` DDL and include all columns referenced in `_TRANSP_EDIT`, `_CORTE_EDIT`, `_FONO_EDIT` whitelists and the `_pmoc_ficha_list` / `_pmoc_ficha_edit` helpers.

---

## Test Results

```
38 passed, 0 failed, 88 warnings in 107.46s
```

| Suite | Before fixes | After fixes |
|-------|-------------|-------------|
| test_auth.py | 0 passed, 13 errors (schema bug) | **14 passed** (13 + 1 new) |
| test_manutencao.py | 24 passed | **24 passed** |

**Malformed `$argon2` → 401 confirmed:** `test_malformed_argon2_hash_returns_401_not_500` seeds 4 truncated hashes (`$argon2id$`, `$argon2id$v=19$`, `$argon2id$v=19$m=65536,t=3,p=4$`, `$argon2id$v=19$m=65536,t=3,p=4$aaaa$`) and asserts all return 401 with `"inválidas"` in detail — passes GREEN.

---

_Fixed: 2026-06-29T06:45:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
