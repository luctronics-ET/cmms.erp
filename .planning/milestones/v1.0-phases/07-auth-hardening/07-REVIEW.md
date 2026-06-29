---
phase: 07-auth-hardening
reviewed: 2026-06-29T05:30:00Z
depth: deep
files_reviewed: 5
files_reviewed_list:
  - backend/main.py
  - backend/db_core.py
  - tests/test_auth.py
  - tools/seed_usuarios.py
  - requirements.txt
findings:
  critical: 1
  warning: 2
  info: 1
  total: 4
status: findings
---

# Phase 07: Auth Hardening — Code Review Report

**Reviewed:** 2026-06-29T05:30:00Z
**Depth:** deep (cross-file, exception-hierarchy tracing)
**Files Reviewed:** 5
**Status:** findings

## Summary

The dual-hash detection logic, lazy Argon2id upgrade, enumeration-safe error messages, NULL/empty hash rejection, and write-path default-removal are all structurally correct. The happy-path security posture is sound.

One critical bug was found: `argon2.exceptions.VerificationError` (raised by `_ph.verify()` on a malformed `$argon2…` stored hash) is **not** in the `except (VerifyMismatchError, InvalidHash)` catch tuple — it escapes to FastAPI as an unhandled exception, returning HTTP 500 instead of 401. This turns any database record whose `pw_hash` starts with `$argon2` but is malformed (truncated, corrupted, or injected via the unauthenticated `POST /api/sync/erp`) into a denial-of-service against that account and a distinguishable 500 signal distinct from the uniform 401.

Two warnings are raised: (1) Phase 7 introduces a timing side-channel for username enumeration that did not exist pre-Phase-7 (djb2 was constant-time; Argon2id is intentionally slow); (2) the seed scripts in `tools/` still write djb2-hashed `"1234"` into the DB and are not updated to use Argon2id, so every freshly-seeded environment contains legacy-hash accounts — the lazy-upgrade path handles them at first login, but the operator documentation in those scripts still advertises `"senha padrão: 1234"` as a persistent credential rather than a one-time bootstrap value.

---

## Critical Issues

### CR-01: `VerificationError` escapes `except (VerifyMismatchError, InvalidHash)` — HTTP 500 on malformed `$argon2` stored hash

**File:** `backend/main.py:994-996`

**Issue:** `_ph.verify(stored, body.senha)` raises `argon2.exceptions.VerificationError` (e.g., "Decoding failed") when the stored hash starts with `$argon2` but is malformed — truncated, corrupted at rest, or synthesised via the unauthenticated `POST /api/sync/erp` endpoint. The exception hierarchy in argon2-cffi 25.1.0 is:

```
Argon2Error
└── VerificationError        ← raised for decode/structural failures
    └── VerifyMismatchError  ← raised for correct hash, wrong password
ValueError
└── InvalidHashError (= InvalidHash)  ← raised when hash is not argon2 at all
```

`VerificationError` is the **parent** of `VerifyMismatchError`, not a sibling. It is **not** caught by `except (VerifyMismatchError, InvalidHash)`. When it escapes, FastAPI returns HTTP 500 — a response code that is distinguishable from the 401 returned for every other failure, breaking the uniform-error guarantee of SEC-01. Additionally, any account whose stored hash triggers this path is permanently locked out with a 500 rather than a 401.

Verified with argon2-cffi 25.1.0:
```python
# All of these raise VerificationError, not caught by the current except:
ph.verify("$argon2id$", "pw")                              # "Decoding failed"
ph.verify("$argon2id$v=19$", "pw")                         # "Decoding failed"
ph.verify("$argon2id$v=19$m=65536,t=3,p=4$", "pw")        # "Decoding failed"
ph.verify("$argon2id$v=19$m=65536,t=3,p=4$aaaa$", "pw")   # "Decoding failed"
```

**Attack surface:** `POST /api/sync/erp` accepts `users[].pw_hash` without authentication and without format validation. An attacker (or a corrupted backup) can write `"$argon2id$TRUNCATED"` as a user's `pw_hash`, after which any login attempt for that user returns 500 rather than 401 — observable by any caller.

**Fix:** Catch `VerificationError` (the parent class) instead of `VerifyMismatchError` alone, which covers both mismatch and decode failures. `InvalidHash` remains needed for the case where the hash is not argon2 at all (though that case cannot reach this branch because of the `startswith("$argon2")` guard):

```python
from argon2.exceptions import VerifyMismatchError, InvalidHash, VerificationError

if stored.startswith("$argon2"):
    try:
        _ph.verify(stored, body.senha)
    except (VerificationError, InvalidHash):
        # VerificationError covers both VerifyMismatchError (wrong password)
        # and decode/structural failures (malformed hash). Both → 401.
        raise HTTPException(401, "Credenciais inválidas")
    if _ph.check_needs_rehash(stored):
        new_hash = _ph.hash(body.senha)
        await db.execute(
            "UPDATE usuarios SET pw_hash = ? WHERE id = ?",
            (new_hash, user["id"]),
        )
```

The import line at the top of `main.py` must be updated to include `VerificationError`:
```python
from argon2.exceptions import VerifyMismatchError, InvalidHash, VerificationError
```

---

## Warnings

### WR-01: Phase 7 introduces a timing oracle for username enumeration (new regression)

**File:** `backend/main.py:982-1013`

**Issue:** Before Phase 7, the login handler used `_djb2()` for all comparisons — a microsecond-scale operation with no meaningful timing difference between "user not found" and "wrong password". Phase 7 replaces password verification with `_ph.verify()` (Argon2id), which intentionally takes ~100 ms. The new control flow is:

1. User not found → `raise HTTPException(401)` — **fast** (~0 ms after DB lookup)
2. User found, correct argon2 path, wrong password → `_ph.verify()` → **slow** (~100 ms)

An observer with network access can distinguish existing from non-existing usernames by measuring response latency. This is a **regression introduced by Phase 7** — it did not exist when djb2 was the only hash.

**Fix:** Execute a dummy `_ph.verify()` on the not-found path so response time is uniform regardless of whether the user exists:

```python
# At module level — a fixed dummy hash for the constant-time dummy verify
_DUMMY_HASH = PasswordHasher().hash("dummy-constant-time-placeholder")

async def login(body: LoginIn):
    user = await db.fetch_one(
        "SELECT * FROM usuarios WHERE (mat = ? OR nome = ?) AND ativo = 1",
        (body.mat, body.mat),
    )
    if not user:
        # Constant-time dummy verify prevents username enumeration via timing.
        try:
            _ph.verify(_DUMMY_HASH, body.senha)
        except Exception:
            pass
        raise HTTPException(401, "Credenciais inválidas")
    # ... rest of handler unchanged
```

---

### WR-02: Seed scripts in `tools/` still write djb2-hashed `"1234"` — not updated to Argon2id

**Files:** `tools/seed_usuarios.py:21,34` · `tools/seed_from_backup.py:26,124` · `tools/seed_completo.py:27,38`

**Issue:** All three seed scripts write `DEFAULT_PW = "170842"` (djb2 of `"1234"`) directly into `pw_hash` for every seeded user. The lazy-upgrade path in `login()` will rehash to Argon2id on first login, so **authentication is not broken** — but the scripts were not updated as part of Phase 7, which means:

1. Every freshly-seeded environment starts with all accounts carrying a weak djb2 hash until each user individually logs in.
2. The scripts print `"Senha padrão: 1234"` and `"Login: qualquer nome da lista acima + senha '1234'"` — framing "1234" as a durable credential rather than a bootstrap-only value to be changed immediately.
3. `seed_from_backup.py` concludes with `"✓ Importação concluída. Login: qualquer nome · senha: 1234"`, which will remain accurate (and misleading) after Phase 7 ships.

Phase 7's stated goal was to remove the default password from active code paths. These scripts are the canonical bootstrap tool documented in `CLAUDE.md` and called by operators — leaving them unchanged is an incomplete fix.

**Fix:** Update `tools/seed_usuarios.py` (and the other two scripts) to hash with Argon2id at seed time. Since Argon2id is only in the FastAPI process, the seed scripts should either call the same algorithm or generate a known-strong initial credential and print a warning:

```python
# tools/seed_usuarios.py
from argon2 import PasswordHasher
_ph = PasswordHasher()

INITIAL_PW = "ChangeMe@Boot"          # operator must change after first login
DEFAULT_PW_HASH = _ph.hash(INITIAL_PW)

# ...INSERT uses DEFAULT_PW_HASH...
print(f"  Senha inicial de bootstrap: {INITIAL_PW!r} — ALTERE APÓS O PRIMEIRO LOGIN")
```

---

## Info

### IN-01: Assertion in `test_empty_pw_hash_returns_401` is vacuously true

**File:** `tests/test_auth.py:235`

**Issue:** The assertion:
```python
assert "inválidas" in body.get("detail", "").lower() or resp.status_code == 401
```
is logically `assert <message-check> or True` — since `resp.status_code == 401` was already asserted on line 231, the right operand is always `True`, making the `"inválidas"` string check dead. If the error message were accidentally changed (e.g., to `"Erro de autenticação"`), this test would still pass.

**Fix:** Use `and` instead of `or`, or assert the message check directly after the status code check:
```python
assert resp.status_code == 401
assert "inválidas" in resp.json().get("detail", "").lower(), (
    f"Expected 'inválidas' in detail, got: {resp.json().get('detail')!r}"
)
```

---

_Reviewed: 2026-06-29T05:30:00Z_
_Reviewer: Claude (gsd-code-reviewer) — adversarial pass_
_Depth: deep_
