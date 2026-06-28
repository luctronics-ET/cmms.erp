# Testing Patterns

**Analysis Date:** 2026-06-28

## Test Framework

**Runner:**
- pytest (no explicit version pin, but `requirements.txt` is empty for test deps; pytest must be installed separately)
- Config: No `pytest.ini` or `pyproject.toml` detected; default pytest behavior
- See `tools/smoke_system.py` for CI integration: `[sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"]`

**Assertion Library:**
- pytest's built-in `assert` statements
- No unittest or nose framework observed

**Run Commands:**
```bash
pytest tests/                    # Run all tests
pytest tests/ -v                 # Verbose output
pytest tests/ -v --tb=short      # Short traceback format (used in CI)
pytest tests/test_catalogo.py::test_name  # Run specific test
```

## Test File Organization

**Location:**
- Co-located in `tests/` directory at repo root, separate from source code.
- Backend tests live in `tests/` (not `backend/tests/`).
- No frontend/JavaScript tests observed; only Python backend + smoke checks on HTML/JS files.

**Naming:**
- Files: `test_*.py` — `test_catalogo.py`, `test_sync.py`, `test_sync_eventos.py`, `test_manutencao_smoke.py`, `test_planos_climatizacao_api.py`, `test_import_refrigeracao_csv.py`, `test_import_ata2_climatizacao.py`
- Functions: `def test_*` — `test_create_servico_success`, `test_list_modulos_returns_seeded_pmocs`, `test_cursor_requires_modulo_and_device`

**Structure:**
```
tests/
├── conftest.py                 # Shared fixtures (app_client)
├── test_catalogo.py            # /api/catalogo/* endpoints
├── test_sync.py                # /api/sync/*, /api/modulos endpoints
├── test_sync_eventos.py        # Sync event parsing and idempotency
├── test_planos_climatizacao_api.py  # Plan management
├── test_manutencao_smoke.py    # HTML/JS syntax checks, no API calls
├── test_import_refrigeracao_csv.py  # Data import validators
└── test_import_ata2_climatizacao.py # Data import validators
```

## Test Structure

**Suite Organization:**
- No explicit test classes or `unittest.TestCase` inheritance.
- Tests are flat functions, optionally grouped with comment headers.
- Example from `test_catalogo.py`:
  ```python
  # ──────────────────────────── helpers ────────────────────────────────────────
  def _seed_user(main) -> int:
      """Insere usuário mínimo no DB de teste e retorna o id."""
      ...
  
  def _seed_sessao(main, uid: int = 1) -> str:
      """Insere sessão válida e retorna o token."""
      ...
  
  # ──────────────────────────── Serviços ───────────────────────────────────────
  def test_list_servicos_baseline_seeded(app_client):
      client, _ = app_client
      r = client.get("/api/catalogo/servicos")
      ...
  ```

**Patterns:**
- **Setup pattern:** Shared fixtures in `conftest.py`; per-test setup in helper functions prefixed with `_` (e.g., `_seed_user`, `_auth`, `_push_body`).
- **Teardown pattern:** FastAPI TestClient with context manager handles startup/shutdown lifecycle automatically. Temporary DB cleaned up per test.
- **Assertion pattern:** Direct `assert` statements; no custom matchers. Example: `assert r.status_code == 201`.

## Fixtures

**`conftest.py` — Core Fixture:**
```python
@pytest.fixture
def app_client(tmp_path, monkeypatch):
    """Fresh app + DB per test."""
    db_path = tmp_path / "test_core.db"
    monkeypatch.setenv("DB_PATH", str(db_path))
    # Reload main to pick up new DB_PATH
    for mod in ("backend.main", "backend.db_core", "backend.grama", "backend.sync"):
        sys.modules.pop(mod, None)
    main = importlib.import_module("backend.main")
    # TestClient triggers startup/shutdown lifespan
    with TestClient(main.app) as client:
        yield client, main
```

**Isolation Strategy:**
- Each test gets a fresh SQLite database in a temporary directory (`tmp_path`).
- Module-level singletons (`backend.main`, `backend.db_core`) are force-reloaded per test to pick up new `DB_PATH` env var.
- Eliminates test interdependency; all tests can run in parallel.

## Helper Patterns

**Database Query Helpers (Sync):**
Tests access the async database synchronously via raw SQLite connections:
```python
def _query(main, sql, params=()):
    """Consulta síncrona ao DB de teste."""
    conn = sqlite3.connect(main.db.db_path)
    conn.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()

def _exec(main, sql, params=()):
    conn = sqlite3.connect(main.db.db_path)
    try:
        conn.execute(sql, params)
        conn.commit()
    finally:
        conn.close()
```

**Auth Helpers:**
Tests build valid auth headers via helper factories:
```python
def _seed_user(main) -> int:
    _exec(main, "INSERT OR IGNORE INTO usuarios ...")
    return 1

def _seed_sessao(main, uid: int = 1) -> str:
    token = "test-token-123"
    _exec(main, "INSERT OR IGNORE INTO sessoes ...")
    return token

def _auth(main) -> dict:
    uid = _seed_user(main)
    token = _seed_sessao(main, uid)
    return {"Authorization": f"Bearer {token}"}
```

**Payload Builders:**
Factory functions produce test data with optional overrides:
```python
def _servico_payload(**kwargs):
    base = {
        "codigo": "SV001",
        "nome": "Inspecao Visual",
        "escopo": "central",
        "criado_por_modulo": "manutencao",
    }
    base.update(kwargs)
    return base

def _evento(eid, tipo="plano_adiado", payload=None, ts="2026-05-18T10:00:00"):
    return {"id": eid, "tipo": tipo, "ts": ts, "payload": payload or {}}
```

## Mocking

**Framework:** No external mocking library (unittest.mock) detected in current tests.

**Patterns Observed:**
- **Avoid mocking:** Tests use real FastAPI TestClient + real SQLite database (in-memory or tmp_path).
- **Mock data in fixtures:** PMOC test data seeded via `schema_catalogo.sql` at startup. Example:
  ```python
  def test_list_servicos_baseline_seeded(app_client):
      # startup semeia o catálogo de manutenção; SV001 (de teste) não existe ainda
      client, _ = app_client
      r = client.get("/api/catalogo/servicos")
      assert r.status_code == 200
  ```
- **Fallback mocks in code:** `erp-manutencao.js` loads fallback data from `window.ERP_MANUT_MOCKS` when API is offline (graceful degradation, not test mocking).

**What to Mock (if needed):**
- External APIs (aguada-web, xSeguranca) would be mocked by intercepting httpx calls or stubbing environment variables (not done in current suite).
- Time-based operations: Use fixed ISO timestamp strings in fixtures (e.g., `"2026-05-18T10:00:00"`), not `datetime.now()`.

**What NOT to Mock:**
- Database (use real SQLite with tmp_path).
- HTTP client (use TestClient, which intercepts all requests to FastAPI app).
- Business logic (test the actual implementation, not a stub).

## Test Types

**Unit Tests:**
- **Scope:** Individual endpoint or helper function.
- **Approach:** Call FastAPI TestClient on endpoint, assert status + response shape.
- **Example from `test_catalogo.py`:**
  ```python
  def test_create_servico_success(app_client):
      client, main = app_client
      headers = _auth(main)
      r = client.post("/api/catalogo/servicos", json=_servico_payload(), headers=headers)
      assert r.status_code == 201
      data = r.json()
      assert data["codigo"] == "SV001"
      assert data["versao"] == 1
  ```

**Integration Tests:**
- **Scope:** Multi-step workflows (seed data, call endpoint, verify DB state, call another endpoint).
- **Approach:** Use `_query()` helper to inspect database after API calls.
- **Example from `test_sync_eventos.py`:**
  ```python
  def test_push_evento_reserva_material_bloqueado_se_qtd_zero(app_client):
      client, main = app_client
      # seed material with qtd=0
      _exec(main, "INSERT INTO estoque (codigo, qtd_atual) VALUES (?, ?)", (matcod, 0))
      # push evento
      r = client.post("/api/sync/push", json=_push_body([_evento(...)]))
      # verify DB state
      eventos = _query(main, "SELECT * FROM sync_eventos WHERE id = ?", (eid,))
      assert eventos[0]["status"] == "bloqueado"
  ```

**API Contract Tests (Smoke Tests):**
- **Scope:** Verify HTML/JS files are syntactically valid and reference correct assets.
- **Approach:** Parse HTML/JS without execution; check for brace balance, required script tags.
- **Example from `test_manutencao_smoke.py`:**
  ```python
  def test_erp_inclui_pmoc_engine_css():
      assert 'assets/pmoc-engine.css' in _erp_html()
  
  def test_erp_manutencao_js_sintaxe_balanceada():
      depth, errors = _check_braces(ROOT / "assets/erp-manutencao.js")
      assert errors == [], f"chaves não-balanceadas: {errors[:5]}"
      assert all(v == 0 for v in depth.values()), f"saldo final: {depth}"
  ```

**Data Import Validators:**
- **Scope:** CSV parsing, data transformation.
- **Approach:** Load CSV, parse, assert shape and values.
- **Example:** `test_import_refrigeracao_csv.py`, `test_import_ata2_climatizacao.py`

## Async Testing

**Pattern:**
- pytest-asyncio not explicitly configured. Tests use synchronous TestClient, which manages async event loop internally.
- If testing async functions directly, would use `pytest-asyncio` fixture decorator (not observed in current suite).

**Current approach:**
```python
# Don't do this:
async def test_fetch_one():
    row = await db.fetch_one(sql)  # ← Requires @pytest.mark.asyncio

# Do this instead (for API tests):
def test_fetch_one(app_client):
    client, main = app_client  # TestClient already handles async
    r = client.get("/api/ativos")  # FastAPI processes request internally
    assert r.status_code == 200
```

## Error Testing

**Pattern:**
Tests assert HTTP status codes for error paths:
```python
def test_create_servico_requires_auth(app_client):
    client, _ = app_client
    r = client.post("/api/catalogo/servicos", json=_servico_payload())
    assert r.status_code == 401

def test_create_servico_duplicate_codigo_rejected(app_client):
    client, main = app_client
    headers = _auth(main)
    client.post("/api/catalogo/servicos", json=_servico_payload(), headers=headers)
    # Second attempt
    r = client.post("/api/catalogo/servicos", json=_servico_payload(), headers=headers)
    assert r.status_code == 409
    assert "já existe" in r.json()["detail"]
```

## Coverage

**Requirements:** None enforced. No `.coveragerc` or coverage threshold in CI config.

**View Coverage (manual):**
```bash
pip install pytest-cov
pytest tests/ --cov=backend --cov-report=html
open htmlcov/index.html
```

## Test Count & Distribution

| Module | Test Count | Focus |
|--------|-----------|-------|
| `test_catalogo.py` | ~32 | Serviços, Planos, Qualificações CRUD |
| `test_sync.py` | ~20 | Módulos, cursor, push/pull endpoints |
| `test_sync_eventos.py` | ~29 | Event parsing, conflict resolution, idempotency |
| `test_manutencao_smoke.py` | ~10 | HTML/JS syntax, asset inclusion |
| `test_planos_climatizacao_api.py` | ~3 | Refrigeration plan API |
| `test_import_*.py` | ~6 | CSV import validators |
| **Total** | **~100** | Backend API + data integrity |

## Coverage Gaps

**Areas with sparse/no tests:**
- **Frontend JavaScript:** No test framework detected. Smoke tests check syntax only, not runtime behavior.
- **Error recovery:** No tests for network failures, malformed JSON, or timeout scenarios.
- **Concurrent requests:** No tests for race conditions or concurrent database access.
- **Authentication edge cases:** Basic auth tested; session expiry, token refresh, permission checks have minimal coverage.
- **PMOC offline sync:** Sync protocol tested (`test_sync_eventos.py`), but client-side offline queue behavior not tested.
- **Grama module:** No dedicated tests found; API exposed but integration untested.

---

*Testing analysis: 2026-06-28*
