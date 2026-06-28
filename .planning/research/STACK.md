# Stack Research

**Domain:** Brownfield CMMS (FastAPI + aiosqlite + vanilla-JS ERP) — production-readiness additions only
**Researched:** 2026-06-28
**Confidence:** MEDIUM (primary sources: FastAPI official docs, PyPI release pages, pytest-asyncio readthedocs; cross-checked via community discussions)

---

## Scope

This research covers only the two new additions for this milestone:

1. Password hashing migration (djb2 → modern algorithm)
2. Async test suite expansion (pytest-asyncio + httpx + aiosqlite fixture pattern)

The rest of the stack (FastAPI 0.115, aiosqlite 0.20, uvicorn 0.30.6, pydantic 2.7.4, vanilla JS, SQLite) is pinned and not under review.

---

## Recommended Stack — New Additions

### Password Hashing

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| `argon2-cffi` | `25.1.0` | Argon2id password hashing and verification | Winner of Password Hashing Competition (PHC). Memory-hard, GPU/ASIC resistant. Actively maintained (June 2025 release). No wrapper library needed — `PasswordHasher` class covers hash/verify/rehash in 3 lines. FastAPI official docs now use Argon2 as the primary recommendation. |
| `pwdlib[argon2]` | `0.3.0` | Thin wrapper over argon2-cffi, bcrypt | Endorsed by FastAPI team as the post-passlib replacement; `PasswordHash.recommended()` returns Argon2id defaults. Use if you want a passlib-style API without the maintenance risk. Pre-1.0 but stable for this use case. |

**Decision: use `argon2-cffi` directly (not via wrapper).** Rationale: fewer moving parts, no pre-1.0 wrapper in the dependency chain, `PasswordHasher` API is just as simple, and argon2-cffi itself is stable and actively maintained. Reserve `pwdlib` for projects starting from zero with no legacy hash concerns.

### Testing Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pytest` | `>=8.0` (current: 8.x) | Test runner | Already assumed present; no change needed |
| `pytest-asyncio` | `1.4.0` | Makes async def test functions and fixtures work with pytest | Required for any async test (httpx AsyncClient, async DB fixtures). Latest release May 2026. |
| `httpx` | `0.27.2` (already pinned) | HTTP client — provides `AsyncClient` + `ASGITransport` | Already in requirements.txt. Used to test FastAPI endpoints in-process without a real server. |
| `anyio[trio]` | optional | Alternative async backend for `@pytest.mark.anyio` | Only needed if you mix trio-style tests; pure asyncio projects skip this. |

---

## Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `asgi-lifespan` | `2.1.0` | Trigger FastAPI lifespan events in tests | Required when your `@asynccontextmanager` startup hook (the `db.init()` call in `backend/main.py`) must run before test requests. Without it, the DB is not initialized and every endpoint call fails. |

---

## Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| `pytest` pyproject.toml config | Configure asyncio_mode and fixture loop scope | Set `asyncio_mode = "auto"` + `asyncio_default_fixture_loop_scope = "function"` to suppress deprecation warnings in pytest-asyncio 1.x |

---

## Installation

```bash
# Password hashing — add to requirements.txt
pip install "argon2-cffi==25.1.0"

# Testing — dev only (do NOT add to production requirements.txt)
pip install "pytest-asyncio==1.4.0" "asgi-lifespan==2.1.0"
# httpx 0.27.2 is already in requirements.txt (shared with production)
```

---

## Configuration

### pyproject.toml (or pytest.ini)

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
asyncio_default_test_loop_scope = "function"
```

This eliminates the `PytestUnraisableExceptionWarning` and loop-scope deprecation warnings that appear in pytest-asyncio 1.x when these are left unset.

### conftest.py — Async Client Fixture Pattern

The existing test suite uses sync `TestClient` + `importlib` reload. For new async tests, add a parallel `async_client` fixture:

```python
# tests/conftest.py (addition — do not remove existing app_client fixture)
import importlib
import sys
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from asgi_lifespan import LifespanManager

@pytest_asyncio.fixture(scope="function")
async def async_app_client(tmp_path, monkeypatch):
    """Fresh app + DB per test — async variant for endpoint tests."""
    db_path = tmp_path / "test_core.db"
    monkeypatch.setenv("DB_PATH", str(db_path))
    for mod in ("backend.main", "backend.db_core", "backend.grama",
                "backend.sync", "backend.catalogo"):
        sys.modules.pop(mod, None)
    main = importlib.import_module("backend.main")
    # LifespanManager triggers startup (db.init) and shutdown
    async with LifespanManager(main.app) as manager:
        async with AsyncClient(
            transport=ASGITransport(app=manager.app),
            base_url="http://test",
        ) as client:
            yield client, main
```

Key points:
- `LifespanManager` is mandatory because `backend/main.py` runs `db.init()` inside `@asynccontextmanager` startup; without it the SQLite schema is never created.
- Keep the existing sync `app_client` fixture untouched — it powers 7 existing test files.
- `scope="function"` gives a fresh DB per test, matching the existing sync fixture behaviour.

---

## Alternatives Considered

| Recommended | Alternative | When Alternative Makes Sense |
|-------------|-------------|------------------------------|
| `argon2-cffi` direct | `pwdlib[argon2]` | Use pwdlib if you want passlib-style multi-algorithm CryptContext and future algorithm agility in one object |
| `argon2-cffi` direct | `passlib[bcrypt]` | Never: passlib is unmaintained, broken on Python 3.13, generates bcrypt version warnings |
| `argon2-cffi` direct | `bcrypt` 5.0.0 directly | Only if you need bcrypt specifically (e.g., interop with a system that stores bcrypt hashes). Note: bcrypt 5.0.0 raises `ValueError` for passwords > 72 bytes — a silent truncation that existed in older versions became a hard error. |
| `pytest-asyncio` | `anyio` + `@pytest.mark.anyio` | Use anyio if mixing trio-based libraries; overkill for this asyncio-only stack |
| `asgi-lifespan` | manual startup call | Manual approach works but is fragile — lifespan context manager skipped = no DB init; asgi-lifespan is the standard solution |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `passlib` | Last release 2020, not Python 3.13 compatible, generates `bcrypt` version detection warnings, effectively abandoned. FastAPI team removed it from their docs. | `argon2-cffi` or `pwdlib[argon2]` |
| `passlib.context.CryptContext` | Pulls in passlib (see above) | Call `argon2.PasswordHasher().hash()` and `.verify()` directly |
| `bcrypt` Python lib alone (without wrapper) | bcrypt 5.0.0 raises `ValueError` for passwords > 72 bytes — silently truncated before, now a hard error. Needs explicit pre-hash or length check. Also bcrypt is weaker than Argon2 at equivalent cost. | `argon2-cffi` |
| `pytest.mark.asyncio` without `asyncio_mode = "auto"` | In pytest-asyncio 1.x, missing decorator gives cryptic errors; strict mode requires every async test and fixture to be explicitly marked — tedious on a growing suite | Set `asyncio_mode = "auto"` in pyproject.toml |
| `event_loop` fixture (pytest-asyncio) | Removed in pytest-asyncio 1.0. Using it causes `AttributeError`. | Use `@pytest_asyncio.fixture(loop_scope="session")` or rely on per-function loops (default) |
| `TestClient` for new async endpoint tests | Synchronous; cannot `await` in test body, cannot use async DB fixtures | `httpx.AsyncClient` + `ASGITransport` |

---

## Transition Path: djb2 → Argon2

The existing `pw_hash` column stores djb2 hex strings (e.g., `"170842"` for `"1234"`). The migration must be backward-compatible because:

- External modules (`aguada-web`, `xSeguranca`) call `POST /api/auth/login` using the same endpoint.
- Existing users in `core.db` have djb2 hashes and must not be locked out.

**Recommended approach — dual-hash with lazy upgrade:**

```python
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

ph = PasswordHasher()

def _djb2(pw: str) -> str:  # keep existing function
    h = 5381
    for c in pw:
        h = ((h << 5) + h) ^ ord(c)
    return format(h & 0xFFFFFFFF, "x")

async def verify_and_upgrade(db, user_id: int, plain: str, stored_hash: str) -> bool:
    """Verify password; upgrade djb2 to Argon2 on first successful login."""
    # Check if stored as Argon2 (starts with $argon2)
    if stored_hash.startswith("$argon2"):
        try:
            ph.verify(stored_hash, plain)
        except VerifyMismatchError:
            return False
        if ph.check_needs_rehash(stored_hash):
            new_hash = ph.hash(plain)
            await db.execute("UPDATE usuarios SET pw_hash=? WHERE id=?", (new_hash, user_id))
        return True
    # Legacy djb2 path
    if stored_hash == _djb2(plain):
        new_hash = ph.hash(plain)
        await db.execute("UPDATE usuarios SET pw_hash=? WHERE id=?", (new_hash, user_id))
        return True
    return False
```

No schema change required — `pw_hash` column already stores `TEXT` and `$argon2id$...` strings fit fine.

**Removing the default `1234` / `170842`:** After migration logic is in place, seed scripts and user-creation endpoints should no longer set `pw_hash` to `_djb2("1234")`. Force a password-reset flag or require password on first login instead.

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| `argon2-cffi 25.1.0` | Python 3.8+ | No conflict with FastAPI 0.115 / aiosqlite 0.20 |
| `pytest-asyncio 1.4.0` | pytest 8.x, Python 3.8+ | Removed `event_loop` fixture from 1.0 — any existing `event_loop` fixture must be removed |
| `asgi-lifespan 2.1.0` | Python 3.8+, ASGI 3.0 | Works with FastAPI 0.115 lifespan; no conflict |
| `httpx 0.27.2` | Already in requirements.txt | `ASGITransport` available since httpx 0.20; 0.27.2 is fine |
| `pwdlib 0.3.0` | Python ≥ 3.10 only | **Constraint:** project CLAUDE.md says Python 3.7+. pwdlib requires 3.10+. If Python < 3.10 support is needed, use argon2-cffi directly instead. |

---

## Sources

- FastAPI official docs (oauth2-jwt tutorial, async-tests guide) — verified June 2026
- PyPI: passlib 1.7.4 (last release Oct 2020), argon2-cffi 25.1.0 (June 2025), bcrypt 5.0.0 (Sep 2025), pwdlib 0.3.0 (Oct 2025), pytest-asyncio 1.4.0 (May 2026)
- FastAPI GitHub discussion #11773 — passlib abandonment, team decision to move to pwdlib
- pytest-asyncio readthedocs 1.4.0 configuration reference — asyncio_mode values and fixture loop scope
- pwdlib GitHub discussion #1 — project rationale (modern passlib replacement, argon2 + bcrypt backends)
- Confidence: MEDIUM (PyPI version numbers verified from live pages; API patterns from official docs; community consensus cross-checked)

---
*Stack research for: xCMASM ERP brownfield production-readiness milestone*
*Researched: 2026-06-28*
