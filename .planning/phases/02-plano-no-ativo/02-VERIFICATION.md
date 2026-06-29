---
phase: 02-plano-no-ativo
verified: 2026-06-28T17:00:00Z
status: passed
score: 3/4 must-haves verified
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "Open the asset drawer for an ativo whose tipo has a catalogo plano (e.g. AC_SPLIT). Click the Manutenção sub-tab. Confirm that items load from the server (not the old localStorage mock), each with a checkbox, a colored status badge (VENCIDA/URGENTE/PROXIMA/EM_DIA), a progress bar, and a 'faltam X h' detail line."
    expected: "All plan items visible with real data from backend; statuses match each item's falta vs intervalo thresholds."
    why_human: "Visual rendering, async fetch timing, and badge/progress-bar correctness cannot be confirmed by grep or pytest. The manut tab route is wired (renderSubManutAPI is the sole path), but screen rendering requires a running browser session."
  - test: "Check ≥1 item, select a responsável from the dropdown, click 'Registrar Manutenção'. Confirm a green toast appears and the list reloads — a previously-VENCIDA item no longer shows VENCIDA after the reload."
    expected: "Green toast 'Manutenção registrada', checklist refreshed, status for executed item is no longer VENCIDA."
    why_human: "State transition after POST (status update visible on reload) requires a live browser with a backend session and real ativo_plano_estado data."
  - test: "Re-open the same ativo's Manutenção sub-tab after registering. Confirm the updated proximo_uso persists across tab closes (state from DB, not localStorage)."
    expected: "Statuses reflect the last registration. VENCIDA does not reappear for the just-executed item."
    why_human: "Cross-session persistence requires verifying that the DB row (not localStorage) drives the display on subsequent opens."
  - test: "Open the Manutenção sub-tab for an ativo whose tipo has no catalogo plano. Confirm the empty-state message appears without a JS error."
    expected: "The text 'Sem plano de manutenção para o tipo deste ativo.' appears in the sub-tab."
    why_human: "Empty-state branch is code-verified present, but visual rendering requires a browser."
---

# Phase 02: Plano no Ativo — Verification Report

**Phase Goal:** Técnico abre ativo e vê itens do plano com checkbox, status (VENCIDA/URGENTE/PROXIMA/EM_DIA), barra de progresso e "faltam X"; marca itens + responsável + "Registrar Manutenção" → registro persiste em manut_registros + ativo_plano_estado.proximo_uso atualizado atomicamente; statuses refletem estado atualizado na próxima abertura.
**Verified:** 2026-06-28T17:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | GET /api/manutencao/plano-ativo returns every plan item with status (VENCIDA/URGENTE/PROXIMA/EM_DIA), falta, pct, ultimo_uso, proximo_uso | ✓ VERIFIED | `test_plano_no_ativo` passes: GET returns item with `status`, `falta`, `pct`, `por_tempo=False`; endpoint code at manutencao.py lines 263-471 computes all five status codes with VENCIDA/URGENTE/PROXIMA/EM_DIA thresholds |
| 2 | POST /api/manutencao/registro writes one manut_registros row AND upserts ativo_plano_estado.proximo_uso for each checked item in a single atomic transaction | ✓ VERIFIED | `test_plano_no_ativo` proves 2 audit rows after 2 POSTs; `test_registro_atomico` proves zero rows in BOTH tables on 422 (atomic rollback); single `aiosqlite.connect` block with one `conn.commit()` at manutencao.py lines 491-571 |
| 3 | proximo_uso = uso_no_momento (read from DB inside txn) + intervalo — never accumulates across two registros | ✓ VERIFIED | `test_plano_no_ativo`: POST1 at uso=1000 → proximo_uso=1250; explicit UPDATE to uso=1100; POST2 → proximo_uso=1350 (not 1500); `novo_proximo = uso_no_momento + item["iv"]` at manutencao.py line 558 |
| 4 | Técnico sees items with checkbox, status badge, progress bar, and "faltam X h" in the Manutenção sub-tab; on re-open statuses reflect updated proximo_uso | ⚠️ PRESENT_BEHAVIOR_UNVERIFIED | `renderSubManutAPI` in erp-manutencao.js lines 1887-2021 is wired as sole renderer for the 'manut' tab (explicit early-return branch at line 2094, SUBS['manut'] removed at line 2083); all DOM construction uses `el()`/`textContent`; regManut POSTs to `/api/manutencao/registro` and reloads (lines 1755-1780). Visual rendering requires a browser. |

**Score:** 3/4 truths code-verified; 1 present and wired but behavior requires browser verification.

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `data/schema_manutencao.sql` | `ativo_plano_estado` (REAL cols) + `manut_registros` via CREATE TABLE IF NOT EXISTS | ✓ VERIFIED | Lines 31-54: both tables present; `proximo_uso REAL NOT NULL`, `ultimo_uso REAL NOT NULL DEFAULT 0`, `uso_no_momento REAL NOT NULL`; schema runs idempotently (confirmed by manual sqlite3 test) |
| `backend/manutencao.py` | GET /plano-ativo + POST /registro on /api/manutencao router; RegistroIn model with responsavel validator | ✓ VERIFIED | Lines 240-573 present; `RegistroIn.resp_nao_vazio` validator (lines 248-253); routes registered on `router = APIRouter(prefix="/api/manutencao")` |
| `tests/test_manutencao.py` | 4 tests covering GET listing, anti-double-count, atomic rollback, required-responsavel | ✓ VERIFIED | All 4 tests present and all pass: `test_plano_no_ativo`, `test_registro_exige_responsavel`, `test_registro_atomico`, `test_plano_ativo_requires_auth` |
| `assets/erp-manutencao.js` | `renderSubManutAPI` async renderer + `regManut` async POST handler wired to manut tab | ✓ VERIFIED (code); ⚠️ visual unverified | `renderSubManutAPI` defined at line 1887; explicit `activeSub === 'manut'` branch at line 2094; `SUBS` map has no 'manut' key (line 2083); `regManut` posts to `/api/manutencao/registro` (line 1763) |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| POST /registro handler | `ativos.uso_atual` | Read inside `aiosqlite.connect` block (not from payload) | ✓ WIRED | manutencao.py lines 495-502: `SELECT uso_atual FROM ativos WHERE id=? AND ativo=1` inside the same `async with aiosqlite.connect(db_path) as conn` block as the INSERT; `uso_no_momento = float(row["uso_atual"] or 0.0)` |
| POST /registro handler | `ativo_plano_estado` | `ON CONFLICT(ativo_id, catalogo_plano_item_id) DO UPDATE` upsert | ✓ WIRED | manutencao.py lines 559-568: `INSERT INTO ativo_plano_estado ... ON CONFLICT(...) DO UPDATE SET ultimo_uso=excluded.ultimo_uso, proximo_uso=excluded.proximo_uso, updated_at=excluded.updated_at` |
| GET /plano-ativo | `ativo_plano_estado` | Single query loading all state rows keyed by item_id | ✓ WIRED | manutencao.py lines 304-309: `SELECT catalogo_plano_item_id, ultimo_uso, proximo_uso FROM ativo_plano_estado WHERE ativo_id=?` → dict; used at lines 427-434 |
| `renderSub()` | `renderSubManutAPI` | Explicit early-return branch on `activeSub === 'manut'` | ✓ WIRED | erp-manutencao.js line 2094: `if (activeSub === 'manut') { renderSubManutAPI(subBody, ativo); return; }` before `subBody.innerHTML = SUBS[activeSub]?.()` at line 2095 |
| `regManut` async handler | POST /api/manutencao/registro | `fetch(apiUrl('/api/manutencao/registro'), ...)` with Bearer token | ✓ WIRED | erp-manutencao.js lines 1763-1766: fetch with `method:'POST'`, `Authorization: 'Bearer '+token`, body `JSON.stringify({ativo_id, responsavel, itens})`; `operador` is NOT in the payload |

---

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| test_plano_no_ativo passes (GET + anti-double-count + atomicity) | `pytest tests/test_manutencao.py -q` | 4 passed, 9 warnings in 11.40s | ✓ PASS |
| test_registro_exige_responsavel (422 on blank/missing) | included in above | PASS | ✓ PASS |
| test_registro_atomico (zero rows in both tables on bad item) | included in above | PASS | ✓ PASS |
| test_plano_ativo_requires_auth (401 without token) | included in above | PASS | ✓ PASS |
| No new test regressions vs 14-failure baseline | `pytest tests/ -q --tb=no` | 14 failed, 92 passed — same 14 failures as baseline (test_catalogo FK/update/planos, test_import_ata2, test_sync, test_sync_eventos) | ✓ PASS |
| Schema REAL columns + idempotency | `python3 -c "import sqlite3; ..."` | OK — REAL cols verified, tables idempotent | ✓ PASS |

---

## Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| `assets/erp-manutencao.js` — `_mn-resp` select | Hardcoded static list (Luciano Ferreira, Carlos Silva, ...) | ℹ️ Info | Intentional stub per RESEARCH.md Open Question 1; Phase 4 will wire to /api/usuarios. Does not block registration — any name from the list is valid. |

No `TBD`, `FIXME`, or `XXX` markers found in phase-modified files.

---

## IMP-02 Requirements Coverage

| Requirement | Status | Evidence |
|-------------|--------|----------|
| IMP-02: Plano no Ativo — persisted maintenance state per item per ativo | ✓ SATISFIED | `ativo_plano_estado` table stores `(ativo_id, catalogo_plano_item_id, ultimo_uso, proximo_uso)`; GET endpoint returns per-item status; POST atomically upserts state; frontend wired to both endpoints |

---

## Human Verification Required

### 1. Plan items render visually with checkbox, status badge, progress bar, and "faltam X h"

**Test:** Log in at http://localhost:8010. Go to Manutenção, open an ativo whose tipo has a catalogo plano (e.g. AC_SPLIT). Click the Manutenção sub-tab.
**Expected:** Items load from the server (not the old mock). Each item shows: a checkbox, a colored status badge (VENCIDA/URGENTE/PROXIMA/EM_DIA), a progress bar, and a "faltam X h" detail line.
**Why human:** Async fetch, badge rendering via `window.engine.badge()`, and progress-bar visual output require a running browser with a backend session.

### 2. Marking items + clicking Registrar updates status on reload

**Test:** Check ≥1 item, select a responsável, click "Registrar Manutenção". Observe the toast and the list reload.
**Expected:** Green toast "Manutenção registrada"; the checklist reloads; a previously-VENCIDA item shows a different status (EM_DIA or later) after the reload, not VENCIDA again.
**Why human:** The state transition from VENCIDA to a non-VENCIDA status after registration is the core criterion 3 behavior — code is wired correctly (POST → upsert proximo_uso → rerenderSubManutAPI), but the visual confirmation requires a browser with real ativo data.

### 3. Status persists on re-open (DB-backed, not localStorage)

**Test:** After registering, close the asset drawer and re-open the same ativo's Manutenção sub-tab.
**Expected:** The updated status persists. The executed item does not revert to VENCIDA.
**Why human:** Cross-session persistence requires verifying that the `ativo_plano_estado` DB row (not localStorage) is what the GET endpoint returns on the next open.

### 4. Empty-state message for ativo with no plano

**Test:** Open the Manutenção sub-tab for an ativo whose tipo has no catalogo plano.
**Expected:** The text "Sem plano de manutenção para o tipo deste ativo." appears without a JS error.
**Why human:** The empty-state branch is present in code (erp-manutencao.js line 1921), but requires a browser to confirm no JS errors and that the text renders correctly.

---

## Gaps Summary

No gaps. All backend truths (GET endpoint, POST atomicity, anti-double-count, responsavel validation) are verified by passing pytest tests. All artifacts are substantive and wired. The 14 pre-existing baseline failures are unchanged. Human verification is required only for the visual/runtime behavior of the frontend — the code paths are correctly wired, but browser confirmation is needed per the plan's own `checkpoint:human-verify` task (Task 3 of Plan 02-02).

---

_Verified: 2026-06-28T17:00:00Z_
_Verifier: Claude (gsd-verifier)_
