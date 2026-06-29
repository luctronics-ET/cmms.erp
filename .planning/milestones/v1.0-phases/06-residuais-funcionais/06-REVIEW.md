---
phase: 06-residuais-funcionais
reviewed: 2026-06-29T03:00:00Z
depth: deep
files_reviewed: 8
files_reviewed_list:
  - backend/main.py
  - backend/manutencao.py
  - backend/db_core.py
  - tools/backfill_local_id.py
  - tests/test_manutencao.py
  - cmasm_erp.html
  - assets/erp-refrigeracao.js
  - data/schema_core.sql
findings:
  critical: 2
  warning: 1
  info: 1
  total: 4
status: issues_found
---

# Phase 06: Code Review Report — Residuais Funcionais

**Reviewed:** 2026-06-29T03:00:00Z
**Depth:** deep (cross-file contract tracing)
**Commits:** 5368279, 7257e5b, d80692d, 362bf4c, 54892d3, 1e882eb, 3afe530, 378cbd6
**Files Reviewed:** 8
**Status:** issues_found

---

## Summary

Phase 6 landed five gap fixes across backend, DB migrations, tooling, and frontend. The
migration code (RES-02/03/04, `db_core.py`) is correct and idempotent. The `por_tempo`
branch (RES-01, both paths in `main.py` and `manutencao.py`) is logically sound: mutual
exclusivity enforced, NULL `last_exec` correctly skips, ISO parse errors swallowed, alert
threshold consistent with `por_uso` path. The `backfill_local_id.py` tool is safe. The
`abrirNovaSR` ctx extension is clean DOM-only work.

**Two blockers** arise from RES-05: `1e882eb` added `_require_auth + _require_escrita` to
`PUT /api/pmoc/refrigeracao/{ativo_id}` and `POST /api/pmoc/refrigeracao/{ativo_id}/os-preventiva`,
but the two corresponding `fetch()` calls in `assets/erp-refrigeracao.js` still omit the
`Authorization` header. Both calls will return **401** for every logged-in ERP user, silently
breaking ficha-save and OS-preventiva generation.

---

## Critical Issues

### CR-01: `saveFicha` omits Authorization header — PUT /api/pmoc/refrigeracao/{id} always 401

**File:** `assets/erp-refrigeracao.js:497-498`

**Issue:** Commit `1e882eb` added `_require_auth` to `PUT /api/pmoc/refrigeracao/{ativo_id}`
(main.py lines 1131-1132). The `saveFicha` function that calls this endpoint sends no
`Authorization` header. Every attempt to save a refrigeração ficha from the ERP will receive
a 401 response. The error is silently surfaced only as `alert('Falha ao salvar: HTTP 401')`.

The module already has a working `_authHeaders()` helper at line 591 that reads
`localStorage.getItem('xcmasm_token')` — it is used by the catalogo-servico and materiais
calls immediately below, but was not applied here.

**Fix:**
```javascript
// assets/erp-refrigeracao.js ~line 497
fetch('/api/pmoc/refrigeracao/' + encodeURIComponent(ativoId), {
  method: 'PUT',
  headers: _authHeaders(),          // was: { 'Content-Type': 'application/json' }
  body: JSON.stringify(body),
})
```

---

### CR-02: `gerar_os_preventiva` fetch omits Authorization header — POST .../os-preventiva always 401

**File:** `assets/erp-refrigeracao.js:474`

**Issue:** Commit `1e882eb` added `_require_auth + _require_escrita` to
`POST /api/pmoc/refrigeracao/{ativo_id}/os-preventiva` (main.py lines 1163-1164). The
"Gerar OS preventiva" button handler sends no `Authorization` header. Every click results in
a 401 from the backend. The error is caught and shown as `alert('Falha: Token ausente')`.

This endpoint was previously unauthenticated (`async def gerar_os_preventiva(ativo_id: str):`
before `1e882eb`). RES-05 added auth to the backend but did not update the frontend call.

**Fix:**
```javascript
// assets/erp-refrigeracao.js ~line 472
fetch('/api/pmoc/refrigeracao/' + encodeURIComponent(ativoId) + '/os-preventiva', {
  method: 'POST',
  headers: _authHeaders(),          // was: { 'Content-Type': 'application/json' }
})
```

---

## Warnings

### WR-01: `timedelta` imported 1,274 lines after first use — misleading placement in manutencao.py

**File:** `backend/manutencao.py:15` (import) vs `125` (use) vs `1289` (actual import)

**Issue:** The module-level imports at lines 10-20 include `from datetime import date` but
NOT `timedelta`. The `timedelta` symbol is used at line 125 inside `_vencimentos_para_ativo`,
and is only imported by a module-level statement at line 1289 (`from datetime import timedelta
# noqa: E402`). Python executes all module-level statements sequentially on import, so there
is no runtime `NameError` — by the time any function is called the symbol is bound. However:

1. Any static analysis tool (mypy, pylint, ruff) will flag line 125 as a potential
   `NameError` because `timedelta` is not visible in the imports at the top of the file.
2. Reading `_vencimentos_para_ativo` in isolation makes it appear to reference an undefined
   name — a future editor will not find the import without scrolling 1,200 lines.
3. The `# noqa: E402` comment at 1289 hints this was flagged but suppressed rather than fixed.

**Fix:** Move `timedelta` into the top-level import at line 15:
```python
# backend/manutencao.py line 15
from datetime import date, timedelta   # timedelta needed by _vencimentos_para_ativo (por_tempo branch)
```
Then remove the duplicate `from datetime import timedelta` at line 1289.

---

## Info

### IN-01: Stale docstring in `manutencao_vencimentos` claims por_tempo is omitted

**File:** `backend/main.py:2568-2570`

**Issue:** The docstring still says *"Disparo por tempo é omitido (sem base de data
confiável)."* Commit `7257e5b` (RES-01) added a working `por_tempo` branch to the same
function. The claim is now factually wrong and will mislead anyone reading the endpoint docs
or the auto-generated `/docs` page.

**Fix:** Update the docstring to reflect the new behavior:
```python
"""Para cada ativo, resolve o plano pelo tipo (aplicavel_tipos) e calcula o
próximo vencimento por uso (h/km) e por tempo (dias). Disparo por_tempo usa
MAX(data) de manut_registros como base; sem registro, nenhum alerta é emitido.
Plano↔tipo É a atribuição (decisão do modelo)."""
```

---

## Findings NOT Raised

The following were considered and ruled out:

- **`POST /api/os` modulo_origem bypass:** The conditional auth at main.py:2074-2076 is
  correct per MODULOS_EXTERNOS.md. An ERP caller cannot bypass auth by supplying
  `modulo_origem` because: (a) the ERP frontend never sets `modulo_origem` in its own
  POST /api/os calls; (b) even if a browser caller did supply it, the worst outcome is an
  unauthenticated OS creation with a visible `modulo_origem` string — not a privilege
  escalation to write protected records (no PII or financial data at stake; same data
  accessible via open GET routes). This is a documented architectural trade-off, not a
  security finding within this phase's scope.

- **`db_core.py` migrations:** All five additive migrations (`locais.altura_m`,
  `ativos.local_id`, `ordens_servico.departamento`) use PRAGMA table_info checks before
  ALTER. No DROP. Schema shape preserved for existing callers. Clean.

- **`backfill_local_id.py`:** Parameterized, idempotent (WHERE IS NULL guard), gracefully
  skips absent table, second run updates 0 rows. No issues.

- **`_vencimentos_para_ativo` por_tempo branch:** NULL `last_exec` → `continue` (no alert,
  no crash) is correct per RES-01 spec ("no date base → no trigger"). Overdue assets
  (falta_dias < 0) satisfy `falta_dias <= valor * 0.15` trivially and DO alert.

- **`abrirNovaSR(osId, ctx)` extension:** `_srPrefill` is consumed on first use (set to
  null immediately in the `if(_srPrefill)` branch). The `else { _srPrefill=null; }` at
  line 3299 is a harmless no-op (already null when else branch runs) but does not cause
  any bug. `onSRItemChange()` is safe to call after `sel.value` is set.

---

_Reviewed: 2026-06-29T03:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_
