---
phase: 10-dados-conectividade
plan: 04
subsystem: database
tags: [sqlite, fastapi, aiosqlite, grama, ativos, backfill, uso_atual]

requires:
  - phase: 10-dados-conectividade
    provides: "ativos.grama_maquina_id (coluna aditiva criada no plano 10-01)"
provides:
  - "ativos.uso_atual como fonte única de horas para máquinas de grama (Rules.md §3)"
  - "GET /api/grama/maquinas servindo por ativos + LEFT JOIN grama_maquinas (metadados satélite)"
  - "tools/backfill_grama_link.py — backfill idempotente de ativos.grama_maquina_id (MS650+SOL)"
affects: [grama, ativos, manutencao, admin-integridade]

tech-stack:
  added: []
  patterns:
    - "Repoint de escrita crítica (horas) para o cadastro mestre, mantendo tabela legada como satélite ligado por FK aditiva"
    - "Backfill de matching por contagem exata (1:1), nunca por atribuição ordinal, quando dados não têm chave forte"

key-files:
  created:
    - tools/backfill_grama_link.py
  modified:
    - backend/grama.py

key-decisions:
  - "update_operacao_status separa as duas escritas: horas vão para ativos.uso_atual (fonte única); combustivel_atual continua em grama_maquinas via ativos.grama_maquina_id"
  - "list_maquinas/get_maquina servem por ativos (categoria maquinas_corte) + LEFT JOIN grama_maquinas; status derivado de ativos.ativo (perda aceita de granularidade — Pitfall 2)"
  - "Backfill linka apenas grupos com contagem grama==1 E contagem ativos==1 (modelo normalizado por prefixo antes do hífen); ambíguos (FS220/GAR/TS114) e sem-equivalente (BR600) não são pareados (D-02)"

patterns-established:
  - "Fonte única de uso_atual: qualquer módulo satélite que hoje escreve horas/km em tabela própria deve repontar para ativos.uso_atual, mantendo a tabela satélite só para metadados sem lar em ativos"

requirements-completed: [CON-04]

coverage:
  - id: D1
    description: "update_operacao_status (grama.py) incrementa ativos.uso_atual ao concluir operação com horas_utilizadas; combustivel_atual continua em grama_maquinas via link"
    requirement: "CON-04"
    verification:
      - kind: integration
        ref: "curl PUT /api/grama/operacoes/{id}/status status=concluido horas_utilizadas=5.5 -> ativos.uso_atual +5.5, grama_maquinas.horas_uso inalterado (executado manualmente contra core.db, revertido após verificação)"
        status: pass
    human_judgment: false
  - id: D2
    description: "GET /api/grama/maquinas preserva o shape de normalizeVegMaq (id, nome, tipo, fabricante, modelo, numero_serie, ano_fabricacao, status, horas_uso, observacoes) servindo por ativos + LEFT JOIN grama_maquinas"
    requirement: "CON-04"
    verification:
      - kind: integration
        ref: "curl GET /api/grama/maquinas?tipo=MS650 e ?tipo=SOL — chaves e metadados (fabricante Stihl/Solaris) presentes via JOIN"
        status: pass
    human_judgment: false
  - id: D3
    description: "tools/backfill_grama_link.py linka apenas MS650+SOL (1:1); ambíguos (FS220/GAR/TS114) e BR600 não pareados; idempotente; grama_maquinas nunca DROP"
    requirement: "CON-04"
    verification:
      - kind: integration
        ref: "python3 tools/backfill_grama_link.py (2x) — 2 novos links na 1a execução, 0 novos na 2a; grama_maquinas COUNT(*)=12 inalterado"
        status: pass
    human_judgment: false

duration: 20min
completed: 2026-07-03
status: complete
---

# Phase 10 Plan 04: Aposentar grama_maquinas como cadastro-mestre Summary

**Horas de grama repontadas para ativos.uso_atual (fonte única, Rules.md §3); grama_maquinas vira satélite de metadados ligado por ativos.grama_maquina_id, com backfill idempotente linkando só os matches 1:1 (MS650, SOL).**

## Performance

- **Duration:** ~20 min
- **Tasks:** 2/2 completed
- **Files modified:** 2 (1 created, 1 modified)

## Accomplishments

- `update_operacao_status` (backend/grama.py) separa as duas escritas antes feitas em uma só: horas passam a incrementar `ativos.uso_atual` (fonte única); combustível continua decrementando em `grama_maquinas.combustivel_atual`, agora resolvido via o link `ativos.grama_maquina_id` em vez de `maquina_id` apontar diretamente para `grama_maquinas`.
- `list_maquinas`/`get_maquina` passam a ler `ativos` (categoria `maquinas_corte`) com `LEFT JOIN grama_maquinas` para os metadados sem lar em `ativos` (fabricante, modelo, número de série, ano, combustível) — o shape de resposta consumido por `normalizeVegMaq` no `cmasm_erp.html` foi preservado byte-a-byte (mesmas chaves).
- `tools/backfill_grama_link.py` popula `ativos.grama_maquina_id` só nos casamentos inequívocos: agrupa `grama_maquinas.modelo` por um candidato de tipo (prefixo antes do hífen) e só linka quando há exatamente 1 grama_maquina e exatamente 1 ativo daquele tipo — no dataset real isso resultou em MS650 e SOL, exatamente como previsto na pesquisa (RESEARCH §1.2/§1.3).
- Rodado contra `data/core.db` (com backup prévio): 2 novos links na primeira execução, 0 novos na segunda (idempotente), `grama_maquinas` permanece com 12 linhas (nunca DROP).

## Task Commits

Each task was committed atomically:

1. **Task 1: Repontar horas para ativos.uso_atual e servir maquinas por JOIN (grama.py)** - `1736233` (feat)
2. **Task 2: Backfill idempotente de ativos.grama_maquina_id (matches 1:1)** - `a255c87` (feat)

_Nenhuma tarefa TDD nesta plan; ambas as tarefas são `type="auto"`._

## Files Created/Modified

- `backend/grama.py` - `update_operacao_status` repontado para `ativos.uso_atual` (horas) + `grama_maquinas.combustivel_atual` via link legado; `list_maquinas`/`get_maquina` reescritas para `ativos LEFT JOIN grama_maquinas`, com comentário PT-BR documentando a perda aceita de granularidade de status (Pitfall 2)
- `tools/backfill_grama_link.py` - script standalone, idempotente, seguindo o padrão de `tools/backfill_estrutura_id.py`/`tools/backfill_local_id.py`; docstring cita CON-04/D-01/D-02

## Decisions Made

- Critério de "inequívoco" para o backfill: contagem exata (1 grama_maquina E 1 ativo do mesmo tipo normalizado), nunca atribuição ordinal — confirma D-02 travado em CONTEXT.md, sem gray area de checkpoint humano (a RESEARCH havia levantado a hipótese de atribuição ordinal com checkpoint, mas D-02 já a descartou explicitamente).
- Normalização `modelo` → candidato de `tipo`: prefixo antes do primeiro hífen/espaço (`GAR-53`→`GAR`, `SOL-1200`→`SOL`; `FS220`/`MS650`/`TS114` já batem literalmente). Critério estável derivado diretamente dos 12 valores reais de `grama_maquinas.modelo`, documentado na docstring do script.
- Combustível não migra para `ativos` — permanece em `grama_maquinas.combustivel_atual`, agora resolvido através de `ativos.grama_maquina_id` em vez de assumir que `maquina_id` aponta para `grama_maquinas` (fora do escopo de "uso_atual fonte única", conforme A2/RESEARCH §1.5).

## Deviations from Plan

None - plan executado exatamente como escrito. As duas tarefas (`type="auto"`) foram implementadas conforme a ação descrita, sem necessidade de Rule 1/2/3/4.

## Issues Encountered

None. A verificação comportamental (criar operação, concluir com `horas_utilizadas=5.5`, conferir `ativos.uso_atual` incrementado e `grama_maquinas.horas_uso` inalterado) foi feita contra `data/core.db` real (com backup prévio em `/tmp/.../scratchpad/core.db.bak-10-04`) e revertida manualmente após a checagem, para não deixar dado de teste no banco de desenvolvimento.

## User Setup Required

None - nenhuma configuração de serviço externo necessária.

## Next Phase Readiness

- `ativos.uso_atual` agora é a fonte única de horas para máquinas de grama; qualquer consumidor futuro (ex. painel de manutenção preventiva) pode confiar em `ativos.uso_atual` sem checar `grama_maquinas.horas_uso`.
- `grama_maquinas` permanece viva como satélite — CON-06 (relatório de integridade) pode expor os 22 ativos `maquinas_corte` ainda sem `grama_maquina_id` (FS220/GAR/TS114 ambíguos + COY/LGT sem correspondência em grama) como itens informativos, não como erro.
- Nenhum bloqueio para os próximos planos da fase (CON-05, CON-06).

---
*Phase: 10-dados-conectividade*
*Completed: 2026-07-03*

## Self-Check: PASSED

- FOUND: backend/grama.py
- FOUND: tools/backfill_grama_link.py
- FOUND: .planning/phases/10-dados-conectividade/10-04-SUMMARY.md
- FOUND: commit 1736233
- FOUND: commit a255c87
