---
phase: 06-residuais-funcionais
plan: "02"
subsystem: backend-core
tags: [schema-migration, auth-guard, backfill, role-enforcement, os-lotacao]
dependency_graph:
  requires: ["06-01"]
  provides: ["departamento on OS", "ativos.local_id migrated", "visualizador 403 guard", "external-module OS path preserved"]
  affects: ["backend/main.py", "backend/db_core.py", "tests/test_manutencao.py"]
tech_stack:
  added: []
  patterns: ["PRAGMA-guarded additive ALTER", "_require_escrita helper", "conditional auth (modulo_origem discriminator)"]
key_files:
  created: ["tools/backfill_local_id.py"]
  modified: ["backend/db_core.py", "backend/main.py", "tests/test_manutencao.py"]
decisions:
  - "POST /api/os uses conditional auth: modulo_origem set = tokenless (external module); absent = _require_auth + _require_escrita (interactive ERP)"
  - "Backfill only copies pmoc_refrigeracao.local_id → ativos.local_id WHERE local_id IS NULL; non-refrigeração categories remain NULL for manual assignment"
  - "Two existing altura_m tests (Plan 06-01) updated to include auth headers after POST /api/locais gained guard (Rule 1 auto-fix)"
metrics:
  duration: "~98 minutes"
  completed: "2026-06-29"
  tasks_completed: 3
  files_changed: 4
status: complete
requirements: [RES-02, RES-03, RES-05]
---

# Phase 06 Plan 02: Departamento on OS + ativos.local_id + Visualizador 403 Guard Summary

One-liner: JWT-guarded write routes with visualizador-403, departamento field on OS, and idempotent local_id backfill for refrigeração assets.

## What Was Built

### RES-02: departamento on ordens_servico

- `backend/db_core.py`: PRAGMA-guarded `ALTER TABLE ordens_servico ADD COLUMN departamento TEXT` added to the `os_existing` migration block (idempotent, never DROP).
- `backend/main.py` (`OSIn`): `departamento: Optional[str] = None` field added.
- `backend/main.py` (`create_os`): `departamento` added to the explicit INSERT column list and values tuple.
- `GET /api/os/{id}` uses `SELECT o.*` — returns `departamento` automatically with no SELECT change needed.
- Existing clients that omit `departamento` receive `null` in response (no contract break).

### RES-03: ativos.local_id migration + backfill script

- `backend/db_core.py`: PRAGMA-guarded `ALTER TABLE ativos ADD COLUMN local_id INTEGER REFERENCES locais(id)` added to the `existing` (ativos) migration block.
- `tools/backfill_local_id.py`: Idempotent backfill — copies `pmoc_refrigeracao.local_id` → `ativos.local_id` only `WHERE ativos.local_id IS NULL`. Never overwrites. Second run updates 0 rows. Gracefully skips if `pmoc_refrigeracao` table absent. DB_PATH env respected; falls back to `data/core.db`.
- `GET /api/ativos` uses `SELECT *` — returns `local_id` automatically.

### RES-05: visualizador 403 guard on write routes

- `backend/main.py`: Added `_require_escrita(user: dict) -> None` helper immediately after `_require_auth`. Raises `HTTPException(403)` when `user.get("role") == "visualizador"`. Mirrors pattern in `backend/manutencao.py:724-726`.
- Applied `_require_auth` + `_require_escrita` to 11 write routes:
  - `PUT /api/os/{id}/status`
  - `POST /api/ativos`, `PUT /api/ativos/{id}`
  - `POST /api/estoque`, `PUT /api/estoque/{id}`, `POST /api/estoque/{id}/movimentos`
  - `POST /api/locais`, `PUT /api/locais/{id}`
  - `PUT /api/pmoc/refrigeracao/{id}`, `POST /api/pmoc/refrigeracao/{id}/os-preventiva`
  - `POST /api/manutencao/os-preventiva`
- `POST /api/os` uses **conditional auth** (MODULOS_EXTERNOS.md contract preserved): when `body.modulo_origem` is set → no auth required (external module path); when absent → `_require_auth` + `_require_escrita` (interactive ERP user). Branch documented inline.
- All GET routes remain open (no auth guard added).

## Test Results

```
tests/test_manutencao.py tests/test_manutencao_smoke.py
28 passed, 0 failed (49 warnings — pre-existing deprecation warnings only)
```

New tests added (all passing):
- `test_departamento_persists_on_os` — POST with departamento → GET round-trips value
- `test_departamento_optional_no_break` — POST without departamento → 201, departamento=null
- `test_ativos_expoe_local_id` — GET /api/ativos includes local_id key
- `test_visualizador_bloqueado_em_escrita` — visualizador → 403 on POST /api/ativos + PUT /api/os/{id}/status
- `test_visualizador_pode_ler` — visualizador → 200 on GET /api/ativos
- `test_os_modulo_origem_sem_token` — POST /api/os with modulo_origem works without Bearer token
- `test_operador_pode_escrever` — admin/operador → 201 on POST /api/ativos

Full suite: 14 pre-existing failures (test_catalogo, test_import_ata2, test_sync, test_sync_eventos — same baseline as before Plan 06-02). **No new regressions introduced.**

## Verification

- `python -c "import backend.main"` — imports cleanly.
- `db.init()` called twice — no duplicate-column error; both `ativos.local_id` and `ordens_servico.departamento` confirmed present via `PRAGMA table_info`.
- `python tools/backfill_local_id.py` run twice — second run reports `0 ativo(s) atualizado(s)` (idempotent).
- POST /api/os with `modulo_origem="aguada-web"` and no Bearer token → 201 (external-module contract preserved).

## Commits

| Hash | Description |
|------|-------------|
| `362bf4c` | feat(06-02): additive migrations + departamento on OS + local_id on ativos (RES-02, RES-03) |
| `54892d3` | feat(06-02): idempotent local_id backfill script (RES-03) |
| `1e882eb` | feat(06-02): visualizador 403 guard on write routes; external-module path preserved (RES-05) |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed two existing tests broken by POST /api/locais gaining auth guard**
- **Found during:** Task 3 — after adding `_require_auth + _require_escrita` to `POST /api/locais`, two tests from Plan 06-01 (`test_local_altura_m_persists`, `test_local_altura_m_null_safe_listagem`) began returning 401.
- **Issue:** These tests called `POST /api/locais` without `Authorization` headers (written before the auth guard existed).
- **Fix:** Added `headers = _auth(main)` and passed `headers=headers` to the POST calls in both tests.
- **Files modified:** `tests/test_manutencao.py` (lines ~824 and ~853)
- **Commit:** `1e882eb`

## Known Stubs

None — all three requirements implemented fully with data wired to the DB.

## Threat Flags

None — no new network endpoints or auth paths beyond what was planned. The conditional auth on POST /api/os is documented inline referencing MODULOS_EXTERNOS.md.

## Self-Check: PASSED

- `tools/backfill_local_id.py` — exists, parses, runs idempotently.
- `backend/db_core.py` — PRAGMA-guarded ALTERs for `ativos.local_id` and `ordens_servico.departamento` confirmed present.
- `backend/main.py` — `_require_escrita` defined; 11 write routes guarded; POST /api/os conditional logic present.
- Commits `362bf4c`, `54892d3`, `1e882eb` all confirmed in `git log`.
- `python -m pytest tests/test_manutencao.py tests/test_manutencao_smoke.py` → 28 passed, 0 failed.
