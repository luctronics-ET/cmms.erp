---
phase: 08-ajuda-e-documentacao
reviewed: 2026-06-29T07:45:00Z
depth: deep
files_reviewed: 6
files_reviewed_list:
  - data/schema_docs.sql
  - backend/docs.py
  - backend/main.py
  - tests/test_docs.py
  - assets/erp-docs.js
  - cmasm_erp.html
findings:
  critical: 2
  warning: 2
  info: 0
  total: 4
status: issues_found
---

# Phase 08: Code Review Report — Ajuda e Documentação

**Reviewed:** 2026-06-29T07:45:00Z
**Depth:** deep (cross-file, call-chain)
**Files Reviewed:** 6
**Status:** issues_found

## Summary

Phase 8 adds a contextual help drawer (DOC-01) and a versioned document repository with file upload/download (DOC-02/DOC-03). The core upload pipeline is well-constructed: ALLOWED_CATS and ALLOWED_EXTS whitelists fire before any filesystem use, size is capped before disk write, atomic versioning uses a single connection, the server-controlled `{doc_id}_v{versao}{ext}` scheme eliminates client-filename path traversal, and the download handler enforces a normpath prefix check as a second line of defence. The safe Markdown renderer is genuinely XSS-free. Tests cover the security cases they claim to cover.

Two blockers were found: one is a pre-existing architecture issue in `main.py` that Phase 8 directly worsens by placing uploaded documents inside the tree that the unauthenticated `/static/` mount exposes; the other is a file-orphan data-loss race inside `upload_versao`. Two warnings address a role mismatch (confusing UI for `visualizador` users) and `.html` in the extension whitelist.

---

## Critical Issues

### CR-01: Uploaded documents served unauthenticated via `/static/data/documentos/`

**File:** `backend/main.py:340` (pre-existing mount) + `backend/docs.py:79` (Phase 8 storage root)

**Issue:** `_FRONTEND_DIR` is resolved to the repository root (`cmasm.erp/`). `main.py:340` mounts the entire repo root as a static file tree at `/static/` with no authentication:

```python
_FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..")  # = cmasm.erp/
app.mount("/static", StaticFiles(directory=_FRONTEND_DIR), name="static")
```

`_DATA_DOCS` in `docs.py` is `cmasm.erp/data/documentos/`. Every file uploaded through the new endpoint is therefore directly reachable at:

```
GET /static/data/documentos/<categoria>/<doc_id>_v<versao><ext>
```

No `Authorization` header is required. The path is fully deterministic from publicly observable document IDs and version numbers. The `/api/docs/documentos/{id}/versoes/{v}/download` endpoint correctly enforces auth, but this `/static/` bypass makes that enforcement irrelevant. Additionally, `.html` files uploaded via the new endpoint are served from `/static/` without `Content-Disposition: attachment`, so they render in the browser — the XSS-neutralisation in the download handler does not apply here.

Note: `data/core.db` is also reachable at `/static/data/core.db` for the same reason; that is a pre-existing problem. Phase 8 adds the document confidentiality dimension.

**Fix (two-step):**

*Step 1* — Move document storage outside the web-served tree. Use a `docs_storage/` directory that is sibling to the repo root, or at minimum outside `data/`:

```python
# backend/docs.py — change _DATA_DOCS to a path outside /static/ reach
_DATA_DOCS: str = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "docs_storage")
)
```

*Step 2* — Fix the root cause in `main.py`: either restrict `_FRONTEND_DIR` to files that should be publicly served, or exclude `data/` from the static mount using a sub-directory mount:

```python
# Serve only what should be public
_FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..")
# Replace the broad /static mount with targeted mounts:
# app.mount("/static", StaticFiles(directory=_FRONTEND_DIR), name="static")
# → nothing needs /static/data — remove this or scope it tightly
```

Until the storage root is moved, the auth enforcement on the download endpoint is a dead letter.

---

### CR-02: Orphan file on DB write failure inside `upload_versao`

**File:** `backend/docs.py:349-366`

**Issue:** The file is written to disk before the `INSERT INTO docs_versoes` is committed. If the INSERT fails (e.g., a concurrent upload hits the `UNIQUE(documento_id, versao)` constraint despite the `SELECT MAX` guard, or any other database error), the `aiosqlite` context manager rolls back the transaction but there is no cleanup of the already-written physical file. The file persists on disk indefinitely with no DB record, and the version number is permanently consumed (the next upload will compute `MAX+1` over the gap).

Concurrent upload scenario:
1. Request A and B both execute `SELECT COALESCE(MAX(versao),0)+1` → both get `next_v=1`.
2. Both compute the same `abs_path` (`42_v1.pdf`).
3. Both open the file for writing: the second write silently overwrites the first file content.
4. The DB `UNIQUE` constraint causes one INSERT to fail.
5. One DB record exists; the on-disk file contains whichever content was written last. The winning DB record's metadata (filename, size, mime) describes the upload that may have been overwritten.

```python
# Current (dangerous ordering):
async with aiofiles.open(abs_path, "wb") as f:
    await f.write(contents)          # ← file written
await conn.execute("INSERT ...")     # ← if this raises, file is orphaned
await conn.commit()
```

**Fix:** Write the file inside a `try/except` that removes the file if the DB commit fails. Also use SQLite `BEGIN IMMEDIATE` or `BEGIN EXCLUSIVE` to serialise the SELECT+INSERT at the DB level, preventing the concurrent-version collision:

```python
# Step 1: get next version number
cur = await conn.execute(
    "SELECT COALESCE(MAX(versao), 0) + 1 AS next_v "
    "FROM docs_versoes WHERE documento_id = ?", (doc_id,)
)
row = await cur.fetchone()
next_v = row["next_v"]

abs_path = _make_safe_path(doc["categoria"], doc_id, next_v, ext)
rel_path = os.path.relpath(abs_path, start=data_dir)

# Step 2: write file; roll back on DB failure
async with aiofiles.open(abs_path, "wb") as f:
    await f.write(contents)

try:
    await conn.execute("INSERT INTO docs_versoes (...) VALUES (...)", (...))
    await conn.commit()
except Exception:
    # Clean up the orphaned file before re-raising
    try:
        os.remove(abs_path)
    except OSError:
        pass
    raise
```

For the concurrency race, store the SELECT inside an explicit `BEGIN IMMEDIATE` transaction so that a concurrent connection cannot read the same `MAX(versao)` before the first INSERT commits.

---

## Warnings

### WR-01: `canWrite()` in frontend checks `'visitante'`, backend blocks `'visualizador'` — write controls displayed to read-only users

**File:** `assets/erp-docs.js:69-71`

**Issue:** The role taxonomy in `schema_core.sql:12` is `admin | gestor | operador | visualizador`. `'visitante'` is not a database role; it is a synthetic frontend fallback used when `xcmasm_me` is absent or unparseable.

```js
function canWrite() {
  return getUserRole() !== 'visitante';   // ← wrong predicate
}
```

A user with `role = 'visualizador'` (a real DB role that maps to read-only by design per `_require_escrita`) has `getUserRole()` return `'visualizador'`, so `canWrite()` returns `true`. The UI renders the "Upload de versão", "+ Novo documento", and "Editar" (ajuda) controls for them. Every submission returns a `403` from the backend. The error message ("Erro: Visualizadores não têm permissão de escrita") is not surfaced with the HTTP status code, just as a generic error in `showMsg`.

**Fix:**

```js
function canWrite() {
  const role = getUserRole();
  return role !== 'visitante' && role !== 'visualizador';
}
```

---

### WR-02: `.html` in `ALLOWED_EXTS` — stored files bypass `Content-Disposition: attachment` via the unauthenticated `/static/` route

**File:** `backend/docs.py:72`

**Issue:** `.html` is included in the allowed extension whitelist:

```python
ALLOWED_EXTS: frozenset[str] = frozenset({
    ...
    ".html",     # ← allows upload of HTML documents
})
```

The download endpoint correctly serves `.html` files with `Content-Disposition: attachment`, preventing browser-side execution for authenticated downloads. However, as documented in CR-01, the same files are reachable at `/static/data/documentos/<categoria>/<id>_v<n>.html` without authentication and without any `Content-Disposition` header. A `StaticFiles` response for an `.html` file will use `Content-Type: text/html` and the browser will render and execute it in the origin of the FastAPI server.

This is partly a consequence of CR-01, but `.html` in the allowlist is independently unsafe because it creates an XSS vector that survives even if CR-01 is fixed imperfectly (e.g., moving files but leaving an old location reachable). The `<input accept>` in the frontend already excludes `.html`, confirming this extension has no legitimate documented use case in the document repository.

**Fix:** Remove `.html` from `ALLOWED_EXTS`:

```python
ALLOWED_EXTS: frozenset[str] = frozenset({
    ".pdf", ".doc", ".docx",
    ".xls", ".xlsx",
    ".odt", ".ods",
    ".txt", ".md", ".csv",
    ".png", ".jpg", ".jpeg",
    # ".html" removed — no legitimate use case; XSS vector via /static/ bypass
})
```

Also update `test_extension_rejected` to include `.html` in the rejected list.

---

## Notes on Verified Correct Behaviour

The following areas were scrutinised and found sound:

- **Path traversal**: `_validate_cat(categoria)` fires before `os.path.join` in every code path (create, upload, download re-validation). Client `arquivo_nome` never enters any filesystem path.
- **Versioning atomicity**: SELECT MAX + INSERT share one `aiosqlite.connect` context. The `UNIQUE(documento_id, versao)` DB constraint is a correct backstop. (The concurrency gap in CR-02 exists at the filesystem level, not the DB level.)
- **Size limit**: `file.read(MAX_UPLOAD_BYTES + 1)` is evaluated before any filesystem operation. `413` fires before disk write.
- **Auth ordering**: `_require_auth` + `_require_escrita` are the first two statements in all write handlers, before `file.read`.
- **SQL parameterisation**: All user-supplied values go through `?` bound parameters. The `WHERE` clause f-string interpolates only Python literals built from those parameters.
- **Download prefix check**: `normpath + abspath.startswith(data_docs_abs + os.sep)` correctly avoids the false-positive on `/data/documentos_evil`.
- **Markdown renderer**: `renderMdSafe` / `_applyInline` are DOM-only; no `innerHTML` of server content anywhere in the file.
- **`FileResponse` default**: Starlette's `content_disposition_type` defaults to `"attachment"` and is set whenever `filename` is not `None`. Schema marks `arquivo_nome NOT NULL`, so `filename` is always provided to `FileResponse`.

---

_Reviewed: 2026-06-29T07:45:00Z_
_Reviewer: Claude Sonnet 4.6 (gsd-code-reviewer — adversarial, deep)_
_Depth: deep_
