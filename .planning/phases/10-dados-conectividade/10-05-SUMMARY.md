---
phase: 10-dados-conectividade
plan: 05
subsystem: database
tags: [sqlite, catalogo_planos, arquivamento, cleanup, sync-manifest]

# Dependency graph
requires:
  - phase: 10-dados-conectividade
    provides: "coluna aditiva catalogo_planos.arquivado_motivo (plano 10-01)"
provides:
  - "tools/archive_orphan_plano.py — script idempotente que arquiva plano-3c349c22f4 via flag"
  - "Rules.md §11 documentando planos_manutencao como legado aposentado"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Arquivamento via flag dupla (ativo=0 + arquivado_motivo com WHERE ... IS NULL) para idempotência, seguindo padrão de tools/backfill_local_id.py"

key-files:
  created: [tools/archive_orphan_plano.py]
  modified: [Rules.md]

key-decisions:
  - "Opção B (RESEARCH §6.2): reusar ativo=0 + novo arquivado_motivo, em vez de só ativo=0, para preservar a causa do arquivamento e diferenciar de desativação administrativa comum"
  - "Nenhuma linha deletada (D-07) — plano-3c349c22f4 permanece na tabela, apenas marcado"

patterns-established:
  - "Script tools/*.py standalone, idempotente, sem exceção, seguindo o mesmo esqueleto de tools/backfill_local_id.py (resolução de DB_PATH, print de resultado, docstring PT-BR citando decisão)"

requirements-completed: [CON-05]

coverage:
  - id: D1
    description: "Plano órfão plano-3c349c22f4 (aplicavel_tipos='[]') arquivado via ativo=0 + arquivado_motivo, nunca DROP"
    requirement: "CON-05"
    verification:
      - kind: integration
        ref: "python3 tools/archive_orphan_plano.py (executado 2x contra data/core.db) + assert ativo=0/arquivado_motivo preenchido"
        status: pass
    human_judgment: false
  - id: D2
    description: "Plano arquivado some da query real do manifest (backend/sync.py:519, WHERE ativo=1)"
    requirement: "CON-05"
    verification:
      - kind: integration
        ref: "SELECT ... FROM catalogo_planos WHERE ativo=1 executado contra data/core.db — plano-3c349c22f4 ausente do resultado (27 planos ativos restantes)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Vizinhos plano-clima-g1..g12 (aplicavel_tipos=NULL) permanecem intactos e ativos"
    requirement: "CON-05"
    verification:
      - kind: integration
        ref: "SELECT COUNT(*) FROM catalogo_planos WHERE id LIKE 'plano-clima-g%' AND ativo=1 = 12 (antes e depois)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Script é idempotente — segunda execução não sobrescreve arquivado_motivo"
    requirement: "CON-05"
    verification:
      - kind: integration
        ref: "segunda execução de tools/archive_orphan_plano.py imprime 'já estava arquivado' e não altera nenhuma linha"
        status: pass
    human_judgment: false
  - id: D5
    description: "Rules.md §11 documenta planos_manutencao (0 linhas) como APOSENTADO/legado, nunca DROP"
    requirement: "CON-05"
    verification:
      - kind: other
        ref: "grep -q planos_manutencao Rules.md && grep -qi APOSENTAD Rules.md && grep -q arquivado_motivo Rules.md"
        status: pass
    human_judgment: false

duration: 12min
completed: 2026-07-03
status: complete
---

# Phase 10 Plan 05: Limpeza de órfãos (CON-05) Summary

**Script idempotente `tools/archive_orphan_plano.py` arquiva o plano de climatização órfão `plano-3c349c22f4` via flag (ativo=0 + arquivado_motivo), e `Rules.md` documenta `planos_manutencao` como legado aposentado — nenhuma linha deletada.**

## Performance

- **Duration:** 12 min
- **Started:** 2026-07-03T22:15:00Z (aprox.)
- **Completed:** 2026-07-03T22:27:41Z
- **Tasks:** 2/2
- **Files modified:** 2 (tools/archive_orphan_plano.py criado, Rules.md modificado)

## Accomplishments

- `tools/archive_orphan_plano.py` criado: arquiva `plano-3c349c22f4` (`aplicavel_tipos='[]'`) via `UPDATE catalogo_planos SET ativo=0, arquivado_motivo=... WHERE id=... AND arquivado_motivo IS NULL` — idempotente por construção, nunca DROP/DELETE.
- Verificado ao vivo contra `data/core.db` (backup prévio salvo em scratchpad): primeira execução arquivou a linha; segunda execução reportou "já estava arquivado" sem alterar nada; os 12 planos `plano-clima-g1..g12` permaneceram `ativo=1`; a query real do manifest (`backend/sync.py:519`, `WHERE ativo=1`) já não retorna o plano órfão.
- `Rules.md` §11 recebeu nota explícita: `planos_manutencao` (0 linhas) é APOSENTADO — modelo vivo é `catalogo_planos` + `catalogo_plano_itens`, mantido no schema só por compatibilidade, nunca DROP — e registro do arquivamento do plano órfão, distinguindo `aplicavel_tipos='[]'` de `aplicavel_tipos IS NULL` (g1..g12).

## Task Commits

Each task was committed atomically:

1. **Task 1: Script idempotente de arquivamento do plano órfão (CON-05)** - `7836d70` (feat)
2. **Task 2: Documentar planos_manutencao como legado aposentado (Rules.md)** - `cc03188` (docs)

_Nenhum plan-metadata commit adicional foi solicitado pelo orquestrador para este plano (STATE.md/ROADMAP.md não atualizados por instrução explícita)._

## Files Created/Modified

- `tools/archive_orphan_plano.py` - script standalone, idempotente, arquiva o plano órfão via flag dupla (ativo=0 + arquivado_motivo)
- `Rules.md` - §11 recebeu nota de legado (`planos_manutencao` APOSENTADO) e registro do arquivamento do plano órfão

## Decisions Made

- Seguida a recomendação do RESEARCH §6.2 (Opção B): reusar `ativo=0` (já filtrado por `sync.py:519`) + novo `arquivado_motivo` (coluna aditiva já criada no plano 10-01), em vez de só `ativo=0` puro — preserva a causa do arquivamento e evita confundir com desativação administrativa comum.
- Nenhuma decisão divergiu do plano; "Claude's Discretion" do CONTEXT.md (nome exato do flag) já estava pré-decidido pelo RESEARCH como `arquivado_motivo`.

## Deviations from Plan

None - plano executado exatamente como escrito.

## Issues Encountered

None.

## User Setup Required

None - nenhuma configuração de serviço externo necessária.

## Next Phase Readiness

- CON-05 concluído: plano órfão arquivado, `planos_manutencao` documentado.
- `data/core.db` de produção já reflete o arquivamento (verificado ao vivo; backup salvo em `/tmp/claude-1000/.../scratchpad/core.db.bak-10-05` antes da alteração, por precaução).
- Sem blockers para as demais fases (10-01..10-06).

---
*Phase: 10-dados-conectividade*
*Completed: 2026-07-03*

## Self-Check: PASSED

- FOUND: tools/archive_orphan_plano.py
- FOUND: .planning/phases/10-dados-conectividade/10-05-SUMMARY.md
- FOUND commit: 7836d70
- FOUND commit: cc03188
