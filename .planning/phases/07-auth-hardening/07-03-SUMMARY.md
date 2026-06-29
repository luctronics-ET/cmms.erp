---
phase: 07-auth-hardening
plan: "03"
subsystem: tests / QA
tags: [qa, coverage, regression-gate, auth, manutencao]
dependency_graph:
  requires: [07-01, 07-02]
  provides: [QA-01]
  affects: [tests/test_manutencao.py, tests/test_sync_eventos.py, tests/test_sync.py]
tech_stack:
  added: []
  patterns: [pytest, TestClient, aiosqlite, sqlite3 sync helper]
key_files:
  created: []
  modified:
    - tests/test_manutencao.py
    - tests/test_sync_eventos.py
    - tests/test_sync.py
decisions:
  - "Phase 1 uso routes had no test coverage — added test_registrar_uso_post_atomico and test_listar_uso_get"
  - "Catalogo planos failures (10) are out of scope — endpoints marked 'a implementar' in CLAUDE.md"
  - "test_manifest_includes_planos_for_module_ativos uses legacy planos_manutencao table; manifest reads catalogo_planos — non-trivial to fix without production code change, deferred"
  - "test_parse_ata2_estrutura requires .docs_cmasm/ata2_carioca_solution.html which was deleted from the repo — deferred"
metrics:
  duration: "~12 minutes"
  completed: "2026-06-29"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 3
status: complete
---

# Phase 07 Plan 03: QA-01 Coverage Audit + Regression Gate Summary

**One-liner:** All Phase 1-5 manutencao routes now covered by passing tests; full suite 12 failed / 127 passed with 0 new regressions vs 14-failure baseline.

## Tasks Completed

| # | Task | Status | Commit |
|---|------|--------|--------|
| 1 | Audit Phase 1-5 route coverage + gap-fill | Done — 2 new tests | 14b53e7 |
| 2 | Triage cheap pre-existing failures + full-suite gate | Done — 2 closed | b74e3bc |

## Phase 1-5 Route Coverage Audit

| Phase | Method | Route | Coverage Status |
|-------|--------|-------|-----------------|
| 1 | POST | /api/manutencao/uso | **GAP-FILLED** — test_registrar_uso_post_atomico |
| 1 | GET  | /api/manutencao/uso | **GAP-FILLED** — test_listar_uso_get |
| 1 | GET  | /api/manutencao/vencimentos | Covered — test_por_tempo_alerta_por_data, test_por_uso_nao_afetado |
| 2 | GET  | /api/manutencao/plano-ativo | Covered — test_plano_no_ativo, test_plano_ativo_requires_auth |
| 2 | POST | /api/manutencao/registro | Covered — test_plano_no_ativo, test_registro_exige_responsavel, test_registro_atomico |
| 3 | GET  | /api/manutencao/sobressalentes | Covered — test_sobressalentes |
| 3 | POST | /api/manutencao/sobressalentes | Covered — test_sobressalentes |
| 3 | PUT  | /api/manutencao/sobressalentes/{id} | Covered — test_sobressalentes |
| 3 | POST | /api/manutencao/sobressalentes/{id}/ajuste | Covered — test_sobressalentes |
| 3 | GET  | /api/manutencao/sobressalentes/{id}/movimentos | Covered — test_sobressalentes |
| 4 | GET  | /api/manutencao/equipe/membros | Covered — test_equipe_tecnica |
| 4 | POST | /api/manutencao/equipe/membros | Covered — test_equipe_tecnica |
| 4 | PUT  | /api/manutencao/equipe/membros/{id} | Covered — test_equipe_tecnica |
| 4 | GET  | /api/manutencao/equipe/config | Covered — test_equipe_tecnica |
| 4 | PUT  | /api/manutencao/equipe/config | Covered — test_equipe_tecnica |
| 5 | GET  | /api/manutencao/cronograma | Covered — test_cronograma, test_cronograma_alerta, test_cronograma_requires_auth |

**Gaps found and filled:** Phase 1 uso endpoints (`POST /uso` and `GET /uso`) had no tests.  
**All other Phase 2-5 families:** Previously covered. No additional gaps found.

## Auth + Manutencao Suite Result

```
tests/test_auth.py       13 tests — 13 passed
tests/test_manutencao.py 24 tests — 24 passed (22 existing + 2 new)
Total: 37 passed, 0 failed
```

## Full-Suite Regression Gate

| Metric | Baseline | Final |
|--------|----------|-------|
| Passed | 123 | 127 |
| Failed | 14 | 12 |
| New regressions | — | **0** |

**QA-01 PASSED:** No new failures introduced by the SEC-01/SEC-02 auth changes.

## Pre-existing Failure Disposition

| # | Test | Disposition |
|---|------|-------------|
| 1 | test_catalogo::test_create_plano_requires_auth | **Deferred** — `/api/catalogo/planos` endpoint unimplemented (schema-only, "a implementar" in CLAUDE.md). Out of scope for this phase. |
| 2 | test_catalogo::test_create_plano_success_with_tipo_codigo | **Deferred** — same as above |
| 3 | test_catalogo::test_create_plano_success_with_ativo_id | **Deferred** — same as above |
| 4 | test_catalogo::test_create_plano_xor_constraint_neither | **Deferred** — same as above |
| 5 | test_catalogo::test_create_plano_xor_constraint_both | **Deferred** — same as above |
| 6 | test_catalogo::test_create_plano_invalid_servico_fk | **Deferred** — same as above |
| 7 | test_catalogo::test_create_plano_invalid_ativo_fk | **Deferred** — same as above |
| 8 | test_catalogo::test_update_plano | **Deferred** — KeyError 'id'; endpoint unimplemented |
| 9 | test_catalogo::test_arquivar_plano | **Deferred** — KeyError 'id'; endpoint unimplemented |
| 10 | test_catalogo::test_list_planos_filter_by_tipo_codigo | **Deferred** — endpoint returns 410 |
| 11 | test_import_ata2_climatizacao::test_parse_ata2_estrutura | **Deferred** — `FileNotFoundError: .docs_cmasm/ata2_carioca_solution.html` deleted from repo. Would need file restoration or test skip — non-trivial without the source document. |
| 12 | test_sync::test_manifest_includes_planos_for_module_ativos | **Deferred** — test inserts into legacy `planos_manutencao` table, but manifest now reads from `catalogo_planos`. Fix would require production code change (manifest endpoint) or schema mapping — out of scope. |
| ~~13~~ | ~~test_sync_eventos::test_estoque_mov_saida_decrementa_qtd~~ | **CLOSED** — item_id=10 conflicted with fonoclama startup seed (autoincrement IDs 1-10). Fixed by using item_id=1010. |
| ~~14~~ | ~~test_sync::test_list_modulos_parses_categorias_atend_as_list~~ | **CLOSED** — assertion expected legacy names `frota_terrestre/frota_naval`; DB has `viaturas/embarcacoes` after `_migrate_modulo_transportes_categorias`. Fixed test assertion. |

## Deviations from Plan

None — plan executed exactly as written. The two "cheap, clearly-bounded" fixes were applied (test-only changes); the non-trivial ones were documented and deferred as instructed.

## Self-Check: PASSED

- SUMMARY.md: FOUND at .planning/phases/07-auth-hardening/07-03-SUMMARY.md
- Commit 14b53e7 (Task 1 gap-fill): FOUND
- Commit b74e3bc (Task 2 triage): FOUND
- tests/test_manutencao.py: 24 tests pass (verified)
- tests/test_auth.py: 13 tests pass (verified)
- Full suite: 127 passed / 12 failed — no new regressions vs 14-failure baseline (verified)
