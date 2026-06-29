---
phase: 06-residuais-funcionais
verified: 2026-06-29T03:45:23Z
status: passed
score: 9/11 must-haves verified
behavior_unverified: 2
overrides_applied: 0
behavior_unverified_items:
  - truth: "Opening a SR from a service context pre-fills ativo_id + item in the SR modal (RES-02 frontend)"
    test: "Serve the app; open an OS from a service/maintenance context; click '+ SR'"
    expected: "SR modal opens with sr-item-id pre-selected, sr-qtd pre-filled, sr-obs carrying asset reference"
    why_human: "abrirNovaSR(osId, ctx) and _srPrefill wiring are present in DOM code; pre-fill only fires when ctx carries itemId/qtd/ativoId — needs real browser session to confirm callers pass ctx with correct data"
  - truth: "refri171 (and other non-climatizacao assets) can be assigned a local via the existing editable ficha (RES-03 frontend)"
    test: "Serve app + backend; open ficha for asset refri171 (ELETRONICA/BIBLIOTECA); select a local and save; close and reopen ficha"
    expected: "Localização section visible with populated select; after save, local persists on reload"
    why_human: "_localSelect + NUMS.local_id + /api/locais fetch confirmed wired in erp-refrigeracao.js; actual persistence requires backend running and round-trip to PUT /api/pmoc/refrigeracao/{id} with local_id"
human_verification:
  - test: "SR prefill from service context (RES-02 frontend)"
    expected: "SR modal pre-fills item + qty + asset ref when opened with ctx; plain SR (no ctx) is unchanged"
    why_human: "DOM/localStorage-only flow; ctx must be passed at call site from service-context code path — needs browser inspection"
  - test: "refri171 local assignment persists (RES-03 frontend)"
    expected: "Ficha Localização select is editable for non-climatizacao assets; saving persists via PUT; reload shows assigned local"
    why_human: "Requires backend running at :8010; visual confirm of select presence for non-climatizacao type; round-trip persistence check"
---

# Phase 06: Residuais Funcionais — Verification Report

**Phase Goal:** Close 5 functional gaps (RES-01..05) left from prior phases: date-triggered maintenance alerts, departamento on OS, non-climatizacao asset local assignment, NULL-safe thermal calc, and read-only role enforcement.
**Verified:** 2026-06-29T03:45:23Z
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | por_tempo plan raises alert when today >= last_exec_date + interval_days (RES-01) | VERIFIED | `backend/main.py:2605-2631` and `backend/manutencao.py:110-142` both implement the por_tempo branch with `date.fromisoformat` + 15% window; `test_por_tempo_alerta_por_data` passes |
| 2 | por_tempo and por_uso are mutually exclusive — por_tempo branch ends with `continue` before falling into por_uso path | VERIFIED | Both files: `continue  # por_tempo never falls into por_uso path` at main.py:2631 and manutencao.py:142; `test_por_uso_nao_afetado_por_por_tempo` passes |
| 3 | por_tempo plan with NO manut_registros does not alert and does not crash | VERIFIED | `if not ultima_data: continue` guard in both paths; `test_por_tempo_sem_registro_nao_alerta` passes |
| 4 | por_tempo plan with recent execution (well within interval) does not alert | VERIFIED | `falta_dias <= int(valor) * 0.15` gate (only emits when within 15%); `test_por_tempo_recente_nao_alerta` passes |
| 5 | POST /api/os accepts departamento; GET /api/os/{id} returns it (RES-02) | VERIFIED | `OSIn.departamento: Optional[str] = None` in main.py:920; INSERT at main.py:2083 includes `departamento`; `SELECT o.*` auto-returns it; `test_departamento_persists_on_os` and `test_departamento_optional_no_break` pass |
| 6 | ativos.local_id exists; GET /api/ativos returns it; idempotent backfill fills only NULL (RES-03 backend) | VERIFIED | `ALTER TABLE ativos ADD COLUMN local_id` in db_core.py:36 under PRAGMA guard; `GET /api/ativos` uses `SELECT *`; backfill runs twice → second run `0 ativo(s) atualizado(s)`; `test_ativos_expoe_local_id` passes |
| 7 | Thermal calc reads locais.altura_m when present; fallback safe when NULL (RES-04) | VERIFIED | `locais.altura_m REAL` migration in db_core.py:45; `LocalIn.altura_m: Optional[float] = None` at main.py:903; INSERT/UPDATE at main.py:1950+1962 persist it; `list_refrigeracao` SELECTs `l.altura_m AS local_altura_m`; `test_local_altura_m_persists` and `test_local_altura_m_null_safe_listagem` pass |
| 8 | visualizador receives 403 on guarded write routes; 200 on GET (RES-05) | VERIFIED | `_require_escrita` defined at main.py:842-845; applied to 11 write routes (confirmed); `test_visualizador_bloqueado_em_escrita` (403 on POST /api/ativos + PUT /api/os/{id}/status) and `test_visualizador_pode_ler` (200 GET) pass |
| 9 | POST /api/os with modulo_origem set works without Bearer token (RES-05 external-module contract) | VERIFIED | Conditional auth at main.py:2074 — `if not body.modulo_origem:` gates auth; external path stays open; `test_os_modulo_origem_sem_token` passes |
| 10 | Opening a SR from a service context pre-fills ativo_id + item in the SR modal (RES-02 frontend) | PRESENT_BEHAVIOR_UNVERIFIED | `abrirNovaSR(osId, ctx)` with `_srPrefill` wiring confirmed in cmasm_erp.html:5319,3283-3299,4217; ctx plumbing present; actual caller-to-modal pre-fill needs browser session to confirm |
| 11 | refri171 / non-climatizacao assets can be assigned a local via the existing editable ficha (RES-03 frontend) | PRESENT_BEHAVIOR_UNVERIFIED | `_localSelect`, `name="local_id"`, `NUMS.local_id: 1`, `fetch /api/locais` all confirmed in erp-refrigeracao.js; persistence via `PUT /api/pmoc/refrigeracao/{id}` requires live backend + browser round-trip |

**Score:** 9/11 truths verified (2 present, behavior-unverified — interactive UI)

---

### Deferred Items

None. All RES-01..05 backend requirements are implemented and tested in this phase.

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/db_core.py` | altura_m migration + local_id + departamento additive alters | VERIFIED | Lines 36 (local_id), 45 (altura_m), 70 (departamento) — all under PRAGMA guard |
| `backend/main.py` | por_tempo branch + LocalIn.altura_m + _require_escrita + OSIn.departamento + conditional OS auth | VERIFIED | por_tempo at 2605-2631; LocalIn at 892-903; _require_escrita at 842; OSIn at 907-920; conditional auth at 2074 |
| `backend/manutencao.py` | por_tempo branch in _vencimentos_para_ativo | VERIFIED | Lines 110-142; identical algorithm to main.py path |
| `tests/test_manutencao.py` | 13 new tests for RES-01..05 | VERIFIED | 6 from Plan 01 + 7 from Plan 02; all 28 tests pass |
| `tools/backfill_local_id.py` | Idempotent backfill — fills only WHERE local_id IS NULL | VERIFIED | File exists, parses, runs twice → second run 0 updates |
| `cmasm_erp.html` | abrirNovaSR(osId, ctx) + _srPrefill + openModal pre-fill block | VERIFIED (struct) | Signature confirmed; _srPrefill wiring present; behavior is human_needed |
| `assets/erp-refrigeracao.js` | _localSelect + NUMS.local_id + /api/locais fetch in openFicha | VERIFIED (struct) | All four elements confirmed; behavior is human_needed |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `manut_registros.data MAX(ativo_id)` | por_tempo last-execution source | `SELECT MAX(data) AS d FROM manut_registros WHERE ativo_id = ?` | VERIFIED | Present in both main.py:2609 and manutencao.py:114-116 |
| `locais.altura_m` column | `list_refrigeracao SELECT l.altura_m AS local_altura_m` | frontend `calcBTU` fallback `\|\| 2.7` | VERIFIED | main.py:1104 confirms SELECT; frontend JS handles NULL |
| `_require_auth(authorization)` | `_require_escrita(user)` | 11 write routes — auth FIRST, then guard | VERIFIED | Pitfall 3 (auth before escrita) confirmed in all guarded routes |
| `OSIn.departamento` | `ordens_servico INSERT` | `SELECT o.*` auto-returns | VERIFIED | INSERT at main.py:2083 explicitly includes departamento |
| `abrirNovaSR(osId, ctx)` | `sr-item-id select pre-fill` | `_srPrefill` → `openModal` reads + clears → `onSRItemChange()` | STRUCT VERIFIED | Wiring confirmed by code reading; behavioral execution is human_needed |
| `ficha edit (PUT /api/pmoc/refrigeracao/{id})` | `ativos.local_id` | `_localSelect` → `NUMS.local_id` → `saveFicha` FormData | STRUCT VERIFIED | All links present; persistence round-trip is human_needed |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `manutencao_vencimentos` (main.py) | `out` list | `catalogo_planos` + `manut_registros MAX(data)` DB queries | Yes — real DB reads | FLOWING |
| `_vencimentos_para_ativo` (manutencao.py) | `out` list | Same catalog + `manut_registros` DB query | Yes | FLOWING |
| `create_os` | `departamento` in response | `OSIn.departamento` → INSERT → `SELECT o.*` GET | Yes | FLOWING |
| `GET /api/ativos` | `local_id` key | `ativos` table `SELECT *` after migration | Yes | FLOWING |
| `erp-refrigeracao.js openFicha` | `locais` for select | `fetch('/api/locais')` → real API call | Yes (backend required) | FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All 28 test_manutencao tests pass | `python -m pytest tests/test_manutencao.py tests/test_manutencao_smoke.py -q` | 28 passed, 49 warnings | PASS |
| db.init() called twice raises no duplicate-column error | `asyncio.run(db.init()); asyncio.run(db.init())` | OK — no error | PASS |
| locais.altura_m column exists after double init | PRAGMA table_info check | `altura_m: True` | PASS |
| ativos.local_id column exists after double init | PRAGMA table_info check | `local_id: True` | PASS |
| os.departamento column exists after double init | PRAGMA table_info check | `departamento: True` | PASS |
| backfill idempotent — second run updates 0 rows | `python tools/backfill_local_id.py` × 2 | `0 ativo(s) atualizado(s)` both runs | PASS |
| No new regressions beyond 14-failure baseline | `python -m pytest tests/ -q` (full suite) | 14 failed (same set: test_catalogo, test_import_ata2, test_sync, test_sync_eventos), 82 passed | PASS |
| abrirNovaSR accepts ctx param | `node -e` signature check | `osId, ctx` confirmed | PASS |
| erp-refrigeracao.js local_id wiring | `node -e` structural check | `_localSelect`, `name="local_id"`, `NUMS.local_id`, `/api/locais` all confirmed | PASS |

---

### Probe Execution

Step 7c: No dedicated probe scripts found for this phase. Behavioral spot-checks above serve as the phase verification probes.

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| RES-01 | 06-01 | por_tempo plans fire by date, mutual exclusion with por_uso | SATISFIED | por_tempo branch in both paths; 4 targeted tests pass |
| RES-02 | 06-01 (backend), 06-03 (frontend) | departamento on OS (backend) + SR prefill (frontend) | SATISFIED (backend) / PRESENT_BEHAVIOR_UNVERIFIED (frontend) | Backend: tests pass. Frontend: wiring confirmed, interactive behavior unverified |
| RES-03 | 06-02 (backend), 06-03 (frontend) | ativos.local_id migrated + backfill + ficha assignment | SATISFIED (backend) / PRESENT_BEHAVIOR_UNVERIFIED (frontend) | Backend: migration + test pass. Frontend: wiring confirmed, persistence unverified |
| RES-04 | 06-01 | locais.altura_m migrated; thermal NULL-safe | SATISFIED | Migration in db_core.py; LocalIn + CRUD persist it; 2 tests pass |
| RES-05 | 06-02 | visualizador 403 on writes; GET open; modulo_origem tokenless | SATISFIED | _require_escrita on 11 routes; 3 role tests pass |

---

### Anti-Patterns Found

No `TBD`, `FIXME`, or `XXX` markers found in any phase-modified file. No stubs or placeholder returns identified in the implementation. All empty-state returns in the vencimentos paths are intentional (no alert = correct when no base date or recent execution).

---

### Human Verification Required

#### 1. SR prefill from service context (RES-02 frontend)

**Test:** Serve the app (`python3 -m http.server 8080`); open an OS that originated from a service/maintenance context; click `+ SR`.
**Expected:** The SR modal opens with `sr-item-id` pre-selected to the relevant stock item, `sr-qtd` pre-filled from context, and `sr-obs` carrying `"Ref. ativo: <id>"` when ativoId is in ctx.
**Why human:** `abrirNovaSR(osId, ctx)` with `_srPrefill` is wired correctly in the DOM. The pre-fill logic fires only when callers pass a `ctx` object — verify that the service-context button actually passes `ctx` with `itemId`/`qtd`/`ativoId` populated. Then confirm a plain SR (no ctx) remains unchanged (regression check).

#### 2. No-context SR regression (RES-02 frontend — regression guard)

**Test:** Same session; open a plain OS (not from a service context); click `SR` button.
**Expected:** SR modal opens with blank `sr-item-id` (`— Selecionar item —`), `sr-qtd = 1`, `sr-obs` empty — exactly as before Plan 03.
**Why human:** `_srPrefill` is set to `null` on non-ctx calls; regression must be confirmed visually.

#### 3. refri171 local assignment persists (RES-03 frontend)

**Test:** Start backend (`uvicorn backend.main:app --port 8010 --reload`); navigate to Manutenção → Refrigeração → Inventário; click on asset `refri171` (ELETRONICA/BIBLIOTECA) to open its ficha.
**Expected:** Ficha overlay shows a `Localização` group with a `<select>` populated from `/api/locais`. Select any local and save. Close and reopen the ficha — the selected local persists.
**Why human:** `_localSelect`, `NUMS.local_id: 1`, and the `/api/locais` fetch are confirmed in code. The actual persistence requires a live backend, network call to `PUT /api/pmoc/refrigeracao/{id}`, and a read-back to confirm `local_id` round-trips. The `_ATIVO_EDIT` whitelist already accepts `local_id` (confirmed via Plan 03 research).

---

### Gaps Summary

No gaps found. All 9 backend must-haves are VERIFIED with passing tests. The 2 PRESENT_BEHAVIOR_UNVERIFIED items (truths #10 and #11) are frontend interactive behaviors whose structural wiring is confirmed in code but whose runtime behavior requires a live browser session to exercise. These are correctly classified as `human_needed`, not `gaps_found`.

---

## Verification Summary by Criterion

| Criterion | Verdict | One-line evidence |
|-----------|---------|-------------------|
| **RES-01** por_tempo alerts by date, no conflict with por_uso | VERIFIED | Both paths implement date branch + `continue` guard; 4 tests pass |
| **RES-02** POST /api/os departamento persists + returns; SR prefill (backend) | VERIFIED | OSIn + INSERT include departamento; `test_departamento_persists_on_os` passes; SR modal wiring confirmed (frontend behavior is human_needed) |
| **RES-03** ativos.local_id in GET; refri171 assignable via ficha | VERIFIED (backend) / PRESENT_BEHAVIOR_UNVERIFIED (ficha UI) | Migration + backfill + `test_ativos_expoe_local_id` pass; ficha `_localSelect` wired but persistence needs browser |
| **RES-04** altura_m NULL-safe thermal | VERIFIED | PRAGMA-guarded migration; LocalIn + CRUD persist it; `test_local_altura_m_null_safe_listagem` passes |
| **RES-05** visualizador 403 on writes, 200 GET, modulo_origem tokenless | VERIFIED | `_require_escrita` on 11 routes; 3 role tests pass; external-module path confirmed |
| **Baseline** 14 pre-existing failures NOT introduced by phase | CONFIRMED | Full suite shows same 14 failures (test_catalogo, test_import_ata2, test_sync, test_sync_eventos); 82 other tests pass |

---

_Verified: 2026-06-29T03:45:23Z_
_Verifier: Claude (gsd-verifier)_
