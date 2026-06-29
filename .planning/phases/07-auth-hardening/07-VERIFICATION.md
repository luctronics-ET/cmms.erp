---
phase: 07-auth-hardening
verified: 2026-06-29T05:03:10Z
status: passed
score: 12/12 must-haves verified
behavior_unverified: 0
overrides_applied: 0
---

# Phase 07: Auth Hardening Verification Report

**Phase Goal:** Harden authentication: replace djb2 with Argon2id (lazy upgrade), remove default password fallbacks, extend test coverage to all Phase 1-5 routes, and confirm zero new regressions.
**Verified:** 2026-06-29T05:03:10Z
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | SEC-01: djb2 account logs in and hash is upgraded to $argon2 in-request | VERIFIED | `test_legacy_djb2_login_success_and_upgrades_hash` PASSES; `main.py:1004-1013` implements dual-path with lazy UPDATE |
| 2 | SEC-01: second login for upgraded account uses Argon2 path and still returns 200 | VERIFIED | `test_second_login_uses_argon2_path` PASSES; code at `main.py:991-1003` branches on `$argon2` prefix |
| 3 | SEC-01: service account with pre-existing $argon2 hash logs in without caller change | VERIFIED | `test_service_account_argon2_login` PASSES; same login handler; no external module code touched |
| 4 | SEC-01: wrong password returns 401 for both hash types | VERIFIED | `test_wrong_password_djb2_returns_401` and `test_wrong_password_argon2_returns_401` both PASS |
| 5 | SEC-01: POST /api/auth/login {mat,senha} → {token, expira_em, usuario} shape unchanged | VERIFIED | `test_response_shape` PASSES; `main.py:1021-1025` returns exact same keys; `pw_hash` filtered out |
| 6 | SEC-02: account with NULL pw_hash returns 401 — no default fallback | VERIFIED | `test_null_pw_hash_returns_401` PASSES; `main.py:988-989`: `if not stored: raise HTTPException(401, ...)` |
| 7 | SEC-02: account with empty-string pw_hash returns 401 | VERIFIED | `test_empty_pw_hash_returns_401` PASSES; same `if not stored` guard covers empty string |
| 8 | SEC-02: POST /api/usuarios with no senha stores NULL/empty hash (never a hash of 1234) | VERIFIED | `test_create_usuario_without_senha_stores_empty_hash` PASSES; `main.py:1080`: `pw = _ph.hash(body.senha) if body.senha else ""` |
| 9 | SEC-02: no-senha account cannot authenticate (401) | VERIFIED | `test_create_usuario_without_senha_cannot_login` PASSES; includes attempt with "1234" |
| 10 | SEC-02: PUT /api/usuarios with no senha preserves existing pw_hash | VERIFIED | `test_put_usuario_without_senha_preserves_hash` PASSES; `main.py:1093-1098`: fetches existing hash directly from DB |
| 11 | SEC-02: no `_djb2("1234")` literal anywhere in active (non-comment) code of backend/main.py | VERIFIED | `grep -v '^[[:space:]]*#' backend/main.py \| grep -c '_djb2("1234")'` returns 0 |
| 12 | QA-01: all Phase 1-5 route families have passing tests; auth+manutencao suite green; full suite no new regressions | VERIFIED | `python -m pytest tests/test_auth.py tests/test_manutencao.py -q` → 37 passed; full suite 127 passed / 12 failed (all 12 are pre-existing documented failures, 2 closed from 14 baseline) |

**Score:** 12/12 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `requirements.txt` | argon2-cffi==25.1.0 pinned | VERIFIED | Line 7: `argon2-cffi==25.1.0`; importable in .venv |
| `backend/main.py` | dual-hash verify + lazy upgrade in POST /api/auth/login | VERIFIED | Lines 985-1013: NULL guard → $argon2 branch → djb2 legacy branch with UPDATE |
| `backend/main.py` | Argon2id on POST /api/usuarios; preserve hash on PUT | VERIFIED | Lines 1080, 1098: `_ph.hash(body.senha) if body.senha else ""` / `else existing_hash` |
| `tests/test_auth.py` | 13 test cases covering SEC-01 + SEC-02 | VERIFIED | 13 test functions confirmed via grep; all 13 pass |
| `tests/test_manutencao.py` | Phase 1-5 route coverage filled; 24 tests green | VERIFIED | 24 test functions; `test_registrar_uso_post_atomico` + `test_listar_uso_get` gap-filled |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| POST /api/auth/login | argon2 PasswordHasher.verify | `stored.startswith("$argon2")` branch at main.py:991 | WIRED | Exceptions VerifyMismatchError + InvalidHash → 401 at main.py:995-996 |
| POST /api/auth/login | lazy UPDATE usuarios SET pw_hash | djb2 branch match → `_ph.hash(body.senha)` + `db.execute(UPDATE)` at main.py:1009-1013 | WIRED | Same-request persistence confirmed by test |
| POST /api/auth/login | NULL/empty guard | `if not stored: raise HTTPException(401)` at main.py:988-989 | WIRED | Covers both None and "" |
| POST /api/usuarios | Argon2id hash on create | `pw = _ph.hash(body.senha) if body.senha else ""` at main.py:1080 | WIRED | No _djb2 call, no default |
| PUT /api/usuarios | preserve existing hash | Direct `SELECT pw_hash FROM usuarios WHERE id=?` at main.py:1093-1096; `pw = _ph.hash(...) if body.senha else existing_hash` at main.py:1098 | WIRED | Fixes the get_usuario() omission bug |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| 13 auth tests pass | `python -m pytest tests/test_auth.py -q` | 13 passed in ~100s | PASS |
| 24 manutencao tests pass | `python -m pytest tests/test_manutencao.py -q` | 24 passed | PASS |
| Full suite: no new regressions | `python -m pytest tests/ -q` | 127 passed, 12 failed (all pre-existing) | PASS |
| argon2 importable | `python3 -c "from argon2 import PasswordHasher"` | exit 0 | PASS |
| No _djb2("1234") in active code | `grep -v '^[[:space:]]*#' backend/main.py \| grep -c '_djb2("1234")'` | 0 | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| SEC-01 | 07-01 | djb2 → Argon2id lazy upgrade; no lockout | SATISFIED | 7 auth tests pass; login handler dual-path at main.py:985-1013 |
| SEC-02 | 07-02 | Remove default password from all write paths | SATISFIED | 6 additional auth tests pass; _djb2("1234") count = 0 in active code |
| QA-01 | 07-03 | Phase 1-5 route coverage; no new regressions | SATISFIED | 24 manutencao tests (2 gaps filled); full suite 127/127 target paths green |

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `tools/seed_usuarios.py` | 20-21 | `DEFAULT_PW = "170842"` (djb2 of "1234") — dev seed tool still plants djb2 hashes | INFO | Not a blocker: (a) this is a dev-only CLI tool, not the web API; (b) any user seeded this way gets their hash lazily upgraded to Argon2id on first login (SEC-01 covers it); (c) CLAUDE.md documents `seed_usuarios.py` as a dev bootstrap step with password `1234`; (d) plan scope explicitly targeted only `POST/PUT /api/usuarios` and the login handler |

---

### External Module Contract (service-account path)

The "real staging call" criterion (xPredial, aguada-web, PMOC service accounts calling POST /api/auth/login against the production instance) is not automatable without live external systems. The contract shape is verified synthetically: `test_service_account_argon2_login` seeds a user with a pre-existing `$argon2` hash and confirms `POST /api/auth/login` returns 200 + `{token, expira_em, usuario}`. No code change was made to any external module. Real staging validation is deferred as a manual check and is not a gap per the verification instructions.

---

### Pre-existing Failure Disposition (QA-01)

All 12 remaining failures are pre-existing and out of scope:

- **10 x test_catalogo** — `catalogo/planos` endpoints unimplemented (schema-only, "a implementar" per CLAUDE.md)
- **1 x test_import_ata2_climatizacao** — `FileNotFoundError`: `.docs_cmasm/ata2_carioca_solution.html` deleted from repo
- **1 x test_sync::test_manifest_includes_planos_for_module_ativos** — test uses legacy `planos_manutencao`; manifest reads `catalogo_planos`; fix requires production code change (out of scope)

2 failures were CLOSED from the 14-failure baseline: `test_estoque_mov_saida_decrementa_qtd` (item_id conflict fixed) and `test_list_modulos_parses_categorias_atend_as_list` (stale assertion updated).

---

## Summary

All three plans executed cleanly with TDD gate compliance (RED → GREEN commits documented). The lazy-upgrade path is correctly implemented and proven by 13 passing tests. No `_djb2("1234")` literal exists in active API code. The full test suite shows 127 passing / 12 failing, with all 12 failures being pre-existing out-of-scope items — 2 fewer than the 14-failure baseline. Phase goal achieved.

---

_Verified: 2026-06-29T05:03:10Z_
_Verifier: Claude (gsd-verifier)_
