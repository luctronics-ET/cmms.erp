---
phase: 08-ajuda-e-documentacao
plan: "01"
subsystem: docs-backend
tags: [docs, ajuda, documentos, upload, security, versioning, sqlite]
requires: [schema_core.sql, schema_manutencao.sql, backend/main.py]
provides: [/api/docs/ajuda, /api/docs/documentos, data/schema_docs.sql, backend/docs.py]
affects: [backend/db_core.py, backend/main.py]
tech_stack_added: []
tech_stack_patterns: [FastAPI UploadFile, FileResponse, aiofiles, aiosqlite atomic transaction, ON CONFLICT DO UPDATE upsert]
key_files_created:
  - data/schema_docs.sql
  - backend/docs.py
key_files_modified:
  - backend/db_core.py
  - backend/main.py
decisions:
  - "Tables prefixed docs_ (docs_documentos, docs_versoes) to avoid collision with existing 'documentos' table in schema_core.sql"
  - "ALLOWED_EXTS includes .html (content-type spoofing addressed via filename extension whitelist; download uses Content-Disposition attachment to neutralize XSS)"
  - "Path traversal: second line of defense uses os.sep suffix check (abs + os.sep) to prevent sibling-dir false-positives"
metrics:
  duration_minutes: 25
  completed_date: "2026-06-29"
  tasks_completed: 2
  tasks_total: 2
  files_created: 2
  files_modified: 2
status: complete
requirements_satisfied: [DOC-01, DOC-02, DOC-03]
---

# Phase 08 Plan 01: Schema + Router de Ajuda e Documentação — Summary

**One-liner:** SQLite schema (ajuda_topicos + docs_documentos + docs_versoes) e router FastAPI `/api/docs/*` com upload seguro (whitelist categoria/extensão, 25 MB cap, path server-controlled, normpath prefix check no download, attachment download, versão atômica aiosqlite).

---

## Objective

Criar o backend completo de Ajuda & Documentação: schema SQLite + router `backend/docs.py` com todos os endpoints `/api/docs/*` servindo DOC-01 (ajuda contextual), DOC-02 (repositório versionado) e DOC-03 (guias/normas por categoria). Base de dados para o test suite (Plan 02) e frontend (Plan 03).

---

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Schema docs.sql + CoreDB._SCHEMAS | `8c5f18f` | data/schema_docs.sql, backend/db_core.py |
| 2 | Router backend/docs.py + register main.py | `1c22101` | backend/docs.py, backend/main.py |

---

## Security Implementation

### T-08-01: Path Traversal via categoria / arquivo_nome
- `ALLOWED_CATS` frozenset with 8 PMOC categories + "geral"; `_validate_cat()` called BEFORE any `os.path.join` with categoria → HTTP 400 if invalid
- On-disk path: `data/documentos/<categoria>/<doc_id>_v<versao><ext>` — built ONLY from server-controlled values (`doc_id`, `versao`, validated `ext`)
- `arquivo_nome` (client filename) stored SOLELY as metadata in `docs_versoes.arquivo_nome`, NEVER used in path construction

### T-08-02: Download Path Traversal (second line of defense)
- `arquivo_path` resolved via `os.path.normpath(os.path.join(data_dir, row["arquivo_path"]))`
- Guard: `abs_path == data_docs_abs or abs_path.startswith(data_docs_abs + os.sep)` → HTTP 403 on escape
- `os.sep` suffix prevents false-positive on sibling directories (e.g., `/data/documentos_evil` would NOT pass)
- `os.path.isfile(abs_path)` check → HTTP 404 if physical file missing

### T-08-03: Content-Type Spoofing
- `ALLOWED_EXTS` frozenset (14 extensions); security decision uses `os.path.splitext(file.filename)[1].lower()` — NOT `file.content_type`
- Client MIME stored only in `docs_versoes.mime` metadata for Content-Type header on download

### T-08-04: Unbounded Upload Size
- `contents = await file.read(MAX_UPLOAD_BYTES + 1)` reads at most 25 MB + 1 byte
- `len(contents) > MAX_UPLOAD_BYTES` check → HTTP 413 BEFORE writing any bytes to disk

### T-08-05: Visualizador Write Escalation
- `_require_escrita(user)` called on: PUT `/ajuda/{chave}`, POST `/documentos`, POST `/documentos/{doc_id}/versoes` → HTTP 403 if `role == 'visualizador'`
- All GET and download endpoints require `_require_auth` (authentication) only

### T-08-06: Version Race Condition
- `SELECT COALESCE(MAX(versao), 0) + 1` and `INSERT INTO docs_versoes` executed in ONE `aiosqlite.connect()` context with single `await conn.commit()`
- `UNIQUE(documento_id, versao)` in schema is the DB-level backstop (raises `IntegrityError` if concurrent race occurs)
- `aiofiles.open(abs_path, "wb")` for async disk write

### Content-Disposition: attachment
- `FileResponse(path, filename=arquivo_nome, media_type=...)` — FastAPI sets `Content-Disposition: attachment; filename=<arquivo_nome>`
- Attachment mode neutralizes XSS in .html files (browser downloads instead of rendering)

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Renamed docs tables to avoid collision with existing 'documentos' table**

- **Found during:** Task 1 verification
- **Issue:** `schema_core.sql` already defines a `documentos` table with a different schema (UUID PK, no `categoria` column). `CREATE TABLE IF NOT EXISTS documentos` in schema_docs.sql silently no-ops; the subsequent `CREATE INDEX IF NOT EXISTS idx_doc_cat_tipo ON documentos(categoria, tipo, ativo)` fails with `OperationalError: no such column: categoria`
- **Fix:** Renamed tables to `docs_documentos` and `docs_versoes` (prefix `docs_`). Updated all SQL in `backend/docs.py` accordingly. Plan artifact `schema_docs.sql` reflects the corrected names.
- **Files modified:** data/schema_docs.sql, backend/docs.py
- **Commits:** 8c5f18f (schema), 1c22101 (router)

**2. [Rule 2 - Security] os.sep suffix in download prefix check**

- **Found during:** Task 2 implementation
- **Issue:** Plan specified `startswith(os.path.abspath(_DATA_DOCS))` but this is vulnerable to false-positive on sibling directories (`/data/documentos_evil` passes the prefix check for `/data/documentos`)
- **Fix:** Guard uses `abs_path == data_docs_abs or abs_path.startswith(data_docs_abs + os.sep)` — os.sep suffix closes the sibling-dir bypass
- **Files modified:** backend/docs.py
- **Commit:** 1c22101

---

## Known Stubs

None. All endpoints are fully implemented and wired to the SQLite DB. No hardcoded empty values, placeholder text, or unconnected data sources.

---

## Threat Flags

No new security surface beyond what the plan's threat model covers. All five STRIDE threats (T-08-01 to T-08-05) and the race condition (T-08-06) are mitigated with code-level defenses verified in CI.

---

## Verification Results

```
python -c "import backend.main, backend.docs"  → Import OK
db.init() × 2                                   → Idempotent, no error
ALLOWED_EXTS: .exe/.sh/.zip/.js absent          → OK
ALLOWED_CATS: geral + 7 PMOC categories         → OK
MAX_UPLOAD_BYTES: 25 × 1024 × 1024              → OK
Routes: /api/docs/ajuda, /api/docs/ajuda/{chave},
        /api/docs/documentos (×2 GET+POST),
        /api/docs/documentos/{doc_id},
        /api/docs/documentos/{doc_id}/versoes,
        /api/docs/documentos/{doc_id}/versoes/{versao}/download
        → All registered
```

## Self-Check: PASSED

- `data/schema_docs.sql` — FOUND
- `backend/docs.py` — FOUND
- Commit `8c5f18f` — FOUND
- Commit `1c22101` — FOUND
- Tables ajuda_topicos, docs_documentos, docs_versoes — all created and verified
- UNIQUE(documento_id, versao) — present in DDL
- db.init() idempotent — verified
