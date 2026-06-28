# Coding Conventions

**Analysis Date:** 2026-06-28

## Naming Patterns

**Files:**
- Python files (backend): snake_case — `db_core.py`, `catalogo.py`, `sync.py`, `grama.py`
- JavaScript files (frontend/assets): kebab-case or snake_case — `xcmasm-sdk.js`, `pmoc-engine.js`, `erp-manutencao.js`, `tbl-enhance.js`, `xmap-layers-grama.js`
- HTML files: lowercase, descriptive — `cmasm_erp.html` (main ERP), `index.html` (PMOC), `CLAUDE.md` (developer guidance)
- SQL schema files: snake_case with `schema_` prefix — `schema_core.sql`, `schema_catalogo.sql`, `schema_grama.sql`

**Functions & Methods:**
- Python: snake_case for all functions and methods — `_require_auth()`, `_db()`, `_new_uuid()`, `_utc_now()`, `fetch_one()`, `fetch_all()`
- JavaScript: camelCase for functions and methods — `getAtivos()`, `criarUsuario()`, `atualizarLocal()`, `resolveTipoCodigo()`, `getMH()` (get/set/create/update prefixes common)
- Private functions prefixed with `_` in both Python and JavaScript — `_req()` in `xcmasm-sdk.js`, `_seed_user()` in tests

**Variables:**
- Python: snake_case — `db_path`, `user_id`, `last_sync`, `estado_operacional`
- JavaScript: camelCase — `state`, `cache`, `activeTab`, `tabDirty`, `catsAvailable`, `isInitialized`
- Constants (JavaScript): UPPER_SNAKE_CASE — `TOKEN_KEY`, `USER_KEY`, `LS_KEY`, `VERSION`, `TAB_DEFS`, `CAT_DBCATS`
- State objects use descriptive lowercase keys — `{ hor: 0, regs: [], manut: [], ulm: {} }` in localStorage structures

**Types (Python Pydantic):**
- PascalCase for all Pydantic models — `ServicoIn`, `PlanoIn`, `QualificacaoIn`, `UsuarioQualificacaoIn`
- Model suffixes: `In` for input validation models, no suffix for output/response models
- Enum-like constants: descriptive strings — `escopo` accepts `"central"` or `"local"`, `status` accepts `"valida"` | `"vencida"` | `"suspensa"`

## Code Style

**Formatting:**
- **Python:** 4-space indentation (PEP 8 compliant). Line length implicit soft limit ~100 chars. Imports organized: stdlib, third-party, local (no enforcement tool detected).
- **JavaScript:** 2-space indentation (vanilla JS, no build step). Single quotes preferred in code, but double quotes for HTML attributes. No semicolon rule strictly enforced (mixed style observed).
- **HTML/CSS:** 2-space indentation. CSS custom properties (design tokens) prefixed with `--` for theme values (`--bg`, `--bg2`, `--acc`, `--ok`, `--warn`, `--danger`).

**Linting:**
- No ESLint or Prettier detected. JavaScript relies on smoke tests (`test_manutencao_smoke.py`) that verify brace balance in `.js` files.
- Python has no formal linter configured; relies on Pydantic validation and test suite for correctness.

**Docstrings & Comments:**
- Python files: Module-level docstrings describing purpose and key references to domain docs (e.g., `"""API de Catálogo de Serviços...\n\nReferências: Rules.md §§10-15"""`).
- Function docstrings: Brief purpose. Example: `"""Verifica balanço de chaves/parênteses/colchetes ignorando strings e comentários."""`
- Inline comments: Explanatory for complex logic. Prefixed with `# ` on own line or inline after code.
- JavaScript: JSDoc comments rare; header comments in modules describe purpose and usage. Example: `/**\n * xcmasm-sdk.js — SDK compartilhado...\n */`
- PT-BR language used in docstrings and comments throughout both backend and frontend.

## Import Organization

**Order (Python):**
1. Future imports (`from __future__ import annotations`)
2. Standard library (`os`, `sys`, `datetime`, `uuid`, `csv`, `io`, `secrets`, `json`)
3. Third-party (`aiosqlite`, `httpx`, `fastapi`, `pydantic`)
4. Local imports (`from .db_core import`, `from .catalogo import router`)

**Example from `backend/main.py`:**
```python
from __future__ import annotations
import csv, io, os, secrets, uuid
from datetime import datetime, timedelta
from typing import Optional
import httpx
from fastapi import FastAPI, HTTPException, Header, Query
from pydantic import BaseModel
from .db_core import CoreDB
from .catalogo import router as catalogo_router
```

**Order (JavaScript):**
- No formal import system (vanilla JS, file:// breaks fonts). Scripts loaded inline in HTML `<head>/<body>` in dependency order:
  1. Design system CSS: `assets/fonts.css`, `pmoc-engine.css`, custom module CSS
  2. Foundation JS: `xcmasm-sdk.js` (shared SDK, establishes `window.xcmasm`)
  3. Feature engines: `pmoc-engine.js`, `erp-manutencao.js`, domain-specific modules
  4. Inline scripts in HTML for page initialization

**Path Aliases:**
- No path aliases or resolveAlias detected in TypeScript or JavaScript.
- All paths are relative or absolute URLs served by FastAPI.

## Error Handling

**Python (FastAPI/async):**
- Errors raised as `HTTPException(status_code, detail_message)` — always include a human-readable `detail` string.
- Pydantic validation errors trigger `ValueError` in `@field_validator` methods; FastAPI converts to 422 response automatically.
- Pattern in `catalogo.py`:
  ```python
  async def _require_auth(authorization: str | None) -> dict:
      if not authorization or not authorization.startswith("Bearer "):
          raise HTTPException(401, "Token ausente")
      token = authorization[7:]
      row = await _db().fetch_one(...)
      if not row:
          raise HTTPException(401, "Token inválido ou expirado")
      return row
  ```
- Try-catch for type coercion in CRUD operations (parsing incoming JSON to Python types).

**JavaScript:**
- Errors caught in fetch responses: `.catch(() => ({ detail: res.statusText }))` — always fall back to a `detail` field.
- Offline resilience: when xCore is unreachable, SDK logs warning and returns `null` (no throw).
- Pattern in `xcmasm-sdk.js`:
  ```javascript
  try {
    const res = await fetch(url.toString(), { ... });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw Object.assign(new Error(err.detail || res.statusText), { status: res.status });
    }
    return res.status === 204 ? null : res.json();
  } catch (e) {
    if (e.name === 'TypeError') {
      console.warn('[xcmasm-sdk] xCore offline:', path);
      return null;
    }
    throw e;
  }
  ```
- Module-level error logging: `console.warn()` for expected conditions (offline, migrations failing), `console.error()` for assertions.

## Logging

**Framework:** Console-based (`console.log`, `console.warn`, `console.error` in JavaScript; Python has no formal logger configured).

**Patterns:**
- **JavaScript:** Prefixed log messages with module name in brackets — `[xcmasm-sdk]`, `[manut]`, `[xMap]`, `[refrig-engine]` — to identify source in browser DevTools.
- **Python:** Not observed in current codebase; tests use assertions and fixtures for visibility.
- **When to log:**
  - `console.warn()`: Degraded functionality (offline, failed migration, missing dependency).
  - `console.log()`: Self-test confirmations (`refrig-engine self-test OK`), sync status.
  - `console.info()`: Informational events (PMOC offline fallback to mock data).
  - `console.error()`: Assertions only (not in production logic).

## Comments

**When to Comment:**
- Complex business logic: Explain *why*, not *what*. Example: `// categoria de navegação → categoria(s) de ativos no DB` links UI tabs to database categories.
- Non-obvious conditionals: `// Visitante mode — hide write actions` explains the intent behind CSS selectors.
- Migration references: Point to authoritative docs. Example: `# núcleo magro v2 — campos exigidos pelo motor de manutenção (Rules.md §15)`.
- Do NOT comment obvious code (`// increment i` is redundant).

**JSDoc/TSDoc:**
- Minimal usage observed. Module-level JSDoc headers document purpose, params, and return type for exported functions.
- Example from `pmoc-engine.js`:
  ```javascript
  /**
   * pmoc-engine v2.0.0
   * Vanilla JS, sem build step, sem dependências externas.
   * Componentes: header, modal, badge, table, kanban, calendar, ...
   * Cada componente recebe (el, options) e retorna uma API com { update, destroy, ... }
   */
  ```
- Pydantic models in Python use brief inline docstrings:
  ```python
  class ServicoIn(BaseModel):
      codigo: str
      nome: str
      descricao: Optional[str] = None
  ```

## Function Design

**Size:**
- Python: Functions range 5–50 lines typical. Complex CRUD operations split into helpers (e.g., `_seed_user()`, `_auth()` in tests).
- JavaScript: Utility functions 10–30 lines; component factories (header, modal) 30–80 lines. Event handlers inline or delegated to dispatcher.

**Parameters:**
- Python: Explicit keyword arguments for Pydantic models. Optional types marked `Optional[Type]`. Defaults specified in class definitions.
  ```python
  async def fetch_all(self, sql: str, params=()) -> list[dict]:
  ```
- JavaScript: Options objects passed as second parameter to component constructors.
  ```javascript
  function header(target, opts = {}) {
    const state = { user: opts.user || { nome: 'Operador' }, ... };
  }
  ```

**Return Values:**
- Python: Explicit type hints on all functions. `dict | None` for fetch operations; `int` for lastrowid; `list[dict]` for query results.
  ```python
  async def fetch_one(self, sql: str, params=()) -> dict | None:
  ```
- JavaScript: Component functions return API objects with `.update()`, `.destroy()`, `.element` properties.
  ```javascript
  return {
    element: root,
    update(patch) { Object.assign(state, patch); render(); },
    setSync(s) { state.sync = { ...state.sync, ...s }; render(); },
  };
  ```

## Module Design

**Exports (JavaScript):**
- No module.exports; functions and objects attached to `window` object or returned from IIFE.
- Pattern: `(function (global) { ... global.xcmasm = xcmasm; ... })(window);` or `window.ERP_MANUT = { init, ... };`
- Shared SDK accessible as `window.xcmasm({ baseURL: '...' })`.

**Barrel Files (re-export indices):**
- Not used in this codebase. Python imports from modules directly (`from .db_core import`, `from .catalogo import router`).

## Database Patterns

**Aiosqlite + Raw SQL:**
- No ORM. All queries are raw SQL strings passed to `db.execute()`, `db.fetch_one()`, `db.fetch_all()`.
- SQL parameterization required: `db.execute(sql, params)` — never string interpolation.
- Row factory: `db.row_factory = aiosqlite.Row` converts rows to dict-like objects.
- Connection management: Each operation opens its own connection; no connection pooling configured.

**Migrations:**
- Additive only. Schema changes use `PRAGMA table_info(table_name)` to check column existence before `ALTER TABLE ADD COLUMN`.
- Example from `db_core.py`:
  ```python
  existing = {row[1] async for row in await db.execute("PRAGMA table_info(ativos)")}
  for col, ddl in [("subtipo", "ALTER TABLE ativos ADD COLUMN subtipo TEXT"), ...]:
      if col not in existing:
          await db.execute(ddl)
  ```

## Design System

**Dark Theme Required:**
- All pages must declare `data-theme="light"` or `data-theme="dark"` on `<html>`.
- CSS custom properties defined per theme:
  - Dark: `--bg: #07111f; --bg2: #0d1e33; --bg3: #0a1828; --acc: #00b4d8; --green: #22c55e; --red: #ef4444; --amber: #f59e0b;`
  - Light: `--bg: #f0f4f8; --bg2: #ffffff; --bg3: #e8eef5; --acc: #3b82f6; --ok: #22c55e; --warn: #f59e0b; --danger: #ef4444;`

**Fonts:**
- Primary: **JetBrains Mono** (code, mono elements) — self-hosted woff2 in `assets/fonts/`
- Secondary: **DM Sans** (UI text, labels) — fallback to generic sans-serif
- Import via `assets/fonts.css` or Google Fonts CDN as fallback
- Example from `cmasm_erp.html`:
  ```html
  <link rel="stylesheet" href="assets/fonts.css">
  <style>
    html, body { font-family: 'IBM Plex Sans', sans-serif; }
    .mono { font-family: 'IBM Plex Mono', monospace; }
  </style>
  ```

**Component Conventions:**
- Modular CSS classes with `pe-` prefix (pmoc-engine components) — `pe-header`, `pe-badge`, `pe-modal`.
- Module-specific prefixes: `sb-` (sidebar), `ni-` (nav item), `topbar-`.
- No Tailwind or utility CSS. Semantic class names tied to specific component purposes.

---

*Convention analysis: 2026-06-28*
