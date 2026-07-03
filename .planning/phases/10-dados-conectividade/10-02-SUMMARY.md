---
phase: 10-dados-conectividade
plan: 02
subsystem: database
tags: [sqlite, backfill, org-join, coalesce, idempotency]

# Dependency graph
requires:
  - phase: 10-dados-conectividade (plano 01)
    provides: colunas aditivas (locais.estrutura_id, os.lotacao_id, grama_maquina_id, arquivado_motivo) já existentes em db_core.py
provides:
  - "tools/backfill_estrutura_id.py — backfill idempotente locais.codigo → estrutura.id, com relatório de populados/órfãos/fallback"
  - "confirmação (verificação, sem edição de código) de que os org joins de main.py já resolvem por FK via COALESCE(l.estrutura_id, l.codigo)"
affects: [10-06-relatorio-integridade, future-requirements-mapeamento-refri-cmasm]

# Tech tracking
tech-stack:
  added: []
  patterns: ["backfill standalone em tools/ com conexão sqlite3 direta, espelhando tools/backfill_local_id.py"]

key-files:
  created: [tools/backfill_estrutura_id.py]
  modified: []

key-decisions:
  - "0/163 matches hoje é o resultado CORRETO e esperado (D-04b) — locais.codigo em REFRI-<AREA>-<NOME> vs estrutura.id em CMASM-XX.Y; nenhum mapeamento forçado foi criado"
  - "Task 2 não gerou diff adicional: o footer reportando a contagem de fallback (COUNT WHERE estrutura_id IS NULL) já foi implementado na Task 1 dentro do mesmo script — não há necessidade de duplicar/editar main.py"
  - "main.py permanece intocado neste plano — grep confirma COALESCE(l.estrutura_id, l.codigo) já presente 4x (2 joins × 2 queries), que é exatamente o cutover pedido por D-04"

patterns-established:
  - "Backfill idempotente: UPDATE ... WHERE <fk> IS NULL AND <origem> IN (SELECT id FROM <destino>) — nunca sobrescreve, nunca cria nós sintéticos"

requirements-completed: [CON-01]

coverage:
  - id: D1
    description: "tools/backfill_estrutura_id.py roda sem exceção, imprime contagens (total/populados/órfãos) e é idempotente (2ª execução = 0 alterações)"
    requirement: "CON-01"
    verification:
      - kind: other
        ref: "python3 tools/backfill_estrutura_id.py && python3 tools/backfill_estrutura_id.py && grep -q 'estrutura_id IS NULL' tools/backfill_estrutura_id.py && echo OK"
        status: pass
    human_judgment: false
  - id: D2
    description: "Mecanismo de matching realmente popula estrutura_id quando codigo bate com estrutura.id (validado em cópia isolada forjada, não em produção)"
    requirement: "CON-01"
    verification:
      - kind: other
        ref: "teste manual em copia isolada (scratchpad/test_mechanism.db): 1 codigo forjado para 'CMASM-01' -> populados=1, orfaos=162, 2a execucao atualizados_agora=0"
        status: pass
    human_judgment: false
  - id: D3
    description: "Nenhum nó sintético criado em estrutura ao rodar o backfill contra data/core.db real (79 antes/depois)"
    requirement: "CON-01"
    verification:
      - kind: other
        ref: "python3 -c \"import sqlite3;c=sqlite3.connect('data/core.db');print(c.execute('SELECT COUNT(*) FROM estrutura').fetchone()[0])\" — 79 antes e depois"
        status: pass
    human_judgment: false
  - id: D4
    description: "Org joins em main.py já resolvem por FK (estrutura_id) com fallback para codigo via COALESCE — confirmado sem editar main.py"
    requirement: "CON-01"
    verification:
      - kind: other
        ref: "grep -c 'COALESCE(l.estrutura_id, l.codigo)' backend/main.py -> 4; git diff --stat backend/main.py -> vazio"
        status: pass
    human_judgment: false
  - id: D5
    description: "GET /api/locais funciona fim-a-fim com o join (200, campo estrutura_nome presente por linha) após rodar o backfill"
    requirement: "CON-01"
    verification:
      - kind: e2e
        ref: "uvicorn backend.main:app --port 8010; POST /api/auth/login; GET /api/locais -H Authorization: Bearer <token> -> status 200, 163 linhas, estrutura_nome presente em cada"
        status: pass
    human_judgment: false

# Metrics
duration: 25min
completed: 2026-07-03
status: complete
---

# Phase 10 Plan 02: Backfill locais→estrutura (mecanismo CON-01) Summary

**Backfill idempotente `tools/backfill_estrutura_id.py` que mapeia `locais.codigo → estrutura.id`, confirmando 0/163 matches hoje como comportamento correto (D-04b) e validando que os org joins de `main.py` já resolvem por FK via `COALESCE(l.estrutura_id, l.codigo)`.**

## Performance

- **Duration:** 25 min
- **Started:** 2026-07-03T21:40:00Z
- **Completed:** 2026-07-03T22:04:42Z
- **Tasks:** 2 completed
- **Files modified:** 1 (criado)

## Accomplishments
- Criado `tools/backfill_estrutura_id.py`: script standalone idempotente, seguindo o padrão de `tools/backfill_local_id.py` — conexão sqlite3 direta, `UPDATE ... WHERE estrutura_id IS NULL AND codigo IN (SELECT id FROM estrutura)`, com print de total/populados/órfãos/atualizados-agora e nota PT-BR fixando a expectativa de 0 matches como resultado correto (D-04/D-04b).
- Rodado 2x contra `data/core.db` real: 163 locais, 0 populados, 163 órfãos, 0 atualizados em ambas execuções — idempotência confirmada, nenhuma exceção lançada.
- Validado em cópia isolada (fora de produção) que o mecanismo realmente popula quando há match real: 1 `codigo` forjado para `CMASM-01` resultou em 1 populado / 162 órfãos na 1ª execução e 0 atualizados na 2ª — prova que a lógica SQL está correta, não só "sempre retorna 0".
- Confirmado (sem editar `backend/main.py`) que os dois org joins (`list_locais`, `get_local`) já implementam `LEFT JOIN estrutura e ON e.id = COALESCE(l.estrutura_id, l.codigo)` — grep retorna exatamente 4 ocorrências (2 joins × 2 queries); `git diff --stat backend/main.py` vazio, confirmando zero edição.
- Testado fim-a-fim: `uvicorn backend.main:app --port 8010` + login + `GET /api/locais` retorna 200 com 163 linhas, campo `estrutura_nome` presente em cada linha (join resolve sem erro mesmo com 0 FKs populadas, graças ao fallback `codigo`).
- Verificado que `data/core.db` não sofreu mutação de conteúdo (contagens de `locais`, `estrutura`, `usuarios`, `cargos`, `ativos` e linhas de `locais` byte-idênticas ao backup pré-execução).

## Task Commits

Each task was committed atomically:

1. **Task 1: Criar tools/backfill_estrutura_id.py (backfill idempotente)** - `37d8de4` (feat)
2. **Task 2: Verificar cutover do org join por FK (sem mudança de código)** - sem commit adicional (ver "Deviations from Plan" — footer de fallback já entregue na Task 1; verificação em runtime não gera diff)

**Plan metadata:** (commit final de documentação será feito pelo orquestrador conforme instrução do prompt)

## Files Created/Modified
- `tools/backfill_estrutura_id.py` - Script idempotente de backfill `locais.codigo → estrutura.id`; imprime total/populados/órfãos/fallback; nota PT-BR fixando expectativa de 0 matches hoje (D-04b).

## Decisions Made
- **Footer de fallback consolidado na Task 1:** a linha "quantos locais ainda dependem do fallback codigo" pedida pela Task 2 já estava naturalmente presente no print de "órfãos" implementado na Task 1 (mesma métrica: `COUNT WHERE estrutura_id IS NULL`). Não criei uma segunda edição redundante do mesmo arquivo — a Task 2 tornou-se puramente uma verificação (grep + teste de runtime), sem diff adicional para commitar.
- **Nenhum mapeamento REFRI→CMASM foi inventado.** Conforme prohibitions do plano, o script não tenta casar por prefixo, substring ou heurística — apenas igualdade exata de string, deixando os 163 órfãos visíveis para o CON-06 (10-06).
- **main.py não foi tocado.** O COALESCE existente já é o cutover correto; qualquer remoção do fallback fica para uma fase futura, quando o número de órfãos cair a zero.

## Deviations from Plan

None - plano executado exatamente como escrito. A única nuance é que a Task 2 não produziu um segundo commit de código (ver "Decisions Made" acima) — isso é uma consequência natural de a Task 1 já ter implementado o footer completo, não um desvio de comportamento ou escopo.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- O mecanismo de backfill está pronto e testado; quando/se `locais.codigo` for corrigido para o formato `CMASM-XX.Y` (Future Requirements), basta reexecutar `tools/backfill_estrutura_id.py` sem qualquer mudança de código — os 163 órfãos passam a popular automaticamente.
- CON-06 (plano 10-06, relatório de integridade) pode consumir diretamente `SELECT COUNT(*) FROM locais WHERE estrutura_id IS NULL` (hoje 163/163) como uma das categorias do endpoint `/api/admin/integridade`.
- Nenhum bloqueio identificado para os planos seguintes da fase 10.

---
*Phase: 10-dados-conectividade*
*Completed: 2026-07-03*

## Self-Check: PASSED
- FOUND: tools/backfill_estrutura_id.py
- FOUND: .planning/phases/10-dados-conectividade/10-02-SUMMARY.md
- FOUND: commit 37d8de4
