---
phase: 08-ajuda-e-documentacao
plan: "02"
subsystem: docs-test
tags: [docs, ajuda, documentos, upload, security, versioning, sqlite, pytest]
requires: [backend/docs.py, data/schema_docs.sql]
provides: [tests/test_docs.py]
affects: []
tech_stack_added: []
tech_stack_patterns: [pytest monkeypatch, FastAPI TestClient multipart upload, in-memory BytesIO, aiosqlite UNIQUE constraint]
key_files_created:
  - tests/test_docs.py
key_files_modified: []
decisions:
  - "docs_versoes timestamp column is 'data' (not 'criado_em') — auto-fixed after first run revealed the actual schema; test updated to assert v.get('data')"
  - "fixture monkeypatches backend.docs._DATA_DOCS to tmp_path/documentos after module reload so all file writes go to tmp; path consistency verified: upload rel_path computed relative to real data_dir, download resolves same rel_path back to tmp abs_path, prefix check passes against monkeypatched _DATA_DOCS"
  - "MAX_UPLOAD_BYTES patched to 16 for oversize test to stay fast (no 25 MB buffer allocation)"
metrics:
  duration_minutes: 8
  completed_date: "2026-06-29"
  tasks_completed: 2
  tasks_total: 2
  files_created: 1
  files_modified: 0
status: complete
requirements_satisfied: [DOC-01, DOC-02, DOC-03]
---

# Phase 08 Plan 02: Test Suite para Ajuda e Documentação — Summary

**One-liner:** pytest suite (10 tests) covering DOC-01 ajuda upsert, DOC-02 versioned upload/download with history, DOC-03 categoria filter, 4 security rejections (extension/oversize/traversal/403), and migration idempotency — all green with zero regressions beyond the documented 12-failure baseline.

---

## Objective

Create `tests/test_docs.py` as the executable verification gate for Phase 08 Plan 01 backend. Runs against an isolated tmp DB and tmp documentos dir; leaves no artifacts; repeatable.

---

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Write tests/test_docs.py (9 behaviors + bonus) | `fd4d7f0` | tests/test_docs.py |
| 2 | Confirm no regression beyond 12-failure baseline | `fd4d7f0` | — |

---

## Test Coverage

| Test | Behavior | Requirements |
|------|----------|--------------|
| test_ajuda_upsert_persists | PUT twice same chave → same id; GET returns updated content | DOC-01 |
| test_documento_create_and_list_by_categoria | POST 201 + GET filter by categoria; other categoria excluded | DOC-02, DOC-03 |
| test_upload_versao_increments_and_preserves_history | v1→v2 versao increment; both rows in history; autor+data recorded | DOC-02 |
| test_download_returns_correct_bytes | v1 bytes exactly returned; Content-Disposition: attachment present | DOC-02 |
| test_extension_rejected | .exe/.sh/.zip → 400; 0 files written to disk | Security |
| test_oversize_rejected | cap=16 bytes; 16-byte upload OK; 17-byte → 413; 0 files written | Security |
| test_path_traversal_defense | ../../etc / /etc/passwd / unknown_cat → 400/422; no path constructed | Security |
| test_visualizador_write_403 | PUT ajuda / POST documentos / POST versoes → 403 each; GET → 200 | RES-05 |
| test_migracoes_idempotentes | db.init() × 2 no error; 3 docs tables present; UNIQUE(documento_id,versao) | DOC-01, DOC-02 |
| test_ajuda_list_all | GET /ajuda without chave param → list of all topics | DOC-01 |

---

## Security Tests Asserted 4xx (not 2xx)

| Case | Status Code | Endpoint |
|------|-------------|----------|
| .exe extension | 400 | POST /api/docs/documentos/{id}/versoes |
| .sh extension | 400 | POST /api/docs/documentos/{id}/versoes |
| .zip extension | 400 | POST /api/docs/documentos/{id}/versoes |
| 17 bytes (cap=16) | 413 | POST /api/docs/documentos/{id}/versoes |
| categoria ../../etc | 400 | POST /api/docs/documentos |
| categoria ../geral | 400 | POST /api/docs/documentos |
| categoria /etc/passwd | 422 | POST /api/docs/documentos |
| categoria unknown_cat | 400 | POST /api/docs/documentos |
| visualizador PUT ajuda | 403 | PUT /api/docs/ajuda/{chave} |
| visualizador POST documentos | 403 | POST /api/docs/documentos |
| visualizador POST versoes | 403 | POST /api/docs/documentos/{id}/versoes |

---

## Fixture Design

- `docs_client` fixture: monkeypatches `DB_PATH` env + reloads all backend modules + monkeypatches `backend.docs._DATA_DOCS` to `tmp_path/documentos`
- All file writes go to `tmp_path/documentos/` — zero writes to real `data/documentos/`
- `_auth_operador()` seeds admin user; `_auth_visualizador()` seeds visualizador user — both via direct DB insert + sessoes row
- Upload payloads: tiny `BytesIO` (22–44 bytes) — suite runs in ~30s

---

## Regression Check

| Suite | Before plan | After plan |
|-------|-------------|------------|
| Baseline failures | 12 | 12 (unchanged) |
| New passes | 0 | 10 |
| Total pass count | 128 | 138 |

Failing tests are the documented pre-existing 12 (test_catalogo.py plan CRUD × 10, test_import_ata2_climatizacao × 1, test_sync × 1). No new failures introduced.

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] docs_versoes timestamp column is 'data', not 'criado_em'**

- **Found during:** Task 1 first run
- **Issue:** Test asserted `v.get("criado_em") is not None` but the `docs_versoes` schema (schema_docs.sql) uses `data TEXT NOT NULL DEFAULT (datetime('now'))` — not `criado_em`. Assertion failed with `AssertionError: criado_em must be recorded for versao=1; got {..., 'data': '2026-06-29 06:04:42', ...}`
- **Fix:** Changed assertion to `v.get("data") is not None` with updated comment explaining the actual column name
- **Files modified:** tests/test_docs.py
- **Commit:** fd4d7f0

---

## Known Stubs

None. All assertions test real behavior against the fully-implemented backend from Plan 01.

---

## Threat Flags

No new security surface. Tests are read-only from a threat perspective — they exercise the existing backend's defenses and do not introduce new endpoints or data flows.

---

## Self-Check: PASSED

- `tests/test_docs.py` — FOUND
- Commit `fd4d7f0` — FOUND
- `python -m pytest tests/test_docs.py -q` → 10 passed
- `python -m pytest tests/ -q` → 12 failed (baseline), 138 passed (no regression)
