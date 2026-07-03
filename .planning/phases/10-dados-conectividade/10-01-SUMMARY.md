---
phase: 10-dados-conectividade
plan: 01
subsystem: database
tags: [sqlite, aiosqlite, additive-migration, schema, sync-manifest]

# Dependency graph
requires: []
provides:
  - "Coluna aditiva os.lotacao_id TEXT REFERENCES estrutura(id) (CON-02, D-03)"
  - "Coluna aditiva ativos.grama_maquina_id TEXT REFERENCES grama_maquinas(id) (CON-04, D-01)"
  - "Coluna aditiva catalogo_planos.arquivado_motivo TEXT (CON-05, D-07)"
  - "Seed modulos_registrados linha 'fonoclama' com categorias_atend='[\"fonoclama\"]' (CON-03, D-06)"
affects: [10-02, 10-03, 10-04, 10-05, 10-06]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Migração aditiva: PRAGMA table_info(<tabela>) seguido de ALTER TABLE ADD COLUMN condicional, sempre antes de db.commit() — padrão já existente em db_core.py, espelhado identicamente"

key-files:
  created: []
  modified:
    - backend/db_core.py
    - data/schema_catalogo.sql

key-decisions:
  - "nome='fonoclama' (sem prefixo pmoc_) no seed de modulos_registrados — o PLAN.md sobrepõe a recomendação do RESEARCH (pmoc_fonoclama) porque o critério de aceitação do ROADMAP chama literalmente GET /api/sync/manifest?modulo=fonoclama e sync.py resolve o módulo por nome exato"
  - "catalogo_planos.arquivado_motivo adicionado como coluna nova (Opção B do RESEARCH §6.2) em vez de reaproveitar só ativo=0 — preserva a causa do arquivamento, mas este plano só cria a coluna; o UPDATE de arquivamento do plano climatização órfão é escopo de outro plano da fase (CON-05 completo)"

patterns-established:
  - "3 colunas aditivas seguem exatamente o bloco condicional já usado por local_id/estrutura_id/departamento em db_core.py — nenhuma nova convenção introduzida"

requirements-completed: [CON-02, CON-03, CON-04, CON-05]

coverage:
  - id: D1
    description: "Coluna os.lotacao_id (TEXT REFERENCES estrutura(id)) criada via migração aditiva idempotente"
    requirement: "CON-02"
    verification:
      - kind: integration
        ref: "python3 -c PRAGMA table_info(ordens_servico) contém lotacao_id; init() rodado 2x sem erro"
        status: pass
    human_judgment: false
  - id: D2
    description: "Coluna ativos.grama_maquina_id (TEXT REFERENCES grama_maquinas(id)) criada via migração aditiva idempotente"
    requirement: "CON-04"
    verification:
      - kind: integration
        ref: "python3 -c PRAGMA table_info(ativos) contém grama_maquina_id; init() rodado 2x sem erro"
        status: pass
    human_judgment: false
  - id: D3
    description: "Coluna catalogo_planos.arquivado_motivo (TEXT) criada via migração aditiva idempotente"
    requirement: "CON-05"
    verification:
      - kind: integration
        ref: "python3 -c PRAGMA table_info(catalogo_planos) contém arquivado_motivo; init() rodado 2x sem erro"
        status: pass
    human_judgment: false
  - id: D4
    description: "Módulo fonoclama registrado em modulos_registrados; GET /api/sync/manifest?modulo=fonoclama retorna 10 ativos + 5 planos distintos"
    requirement: "CON-03"
    verification:
      - kind: e2e
        ref: "uvicorn backend.main:app --port 8010 && curl http://localhost:8010/api/sync/manifest?modulo=fonoclama -> HTTP 200, ativos=10, planos_manutencao com 5 plano_id distintos (plano-amplificador, plano-console, plano-alto_falante, plano-linha_70v, plano-sirene)"
        status: pass
    human_judgment: false

duration: 20min
completed: 2026-07-03
status: complete
---

# Phase 10 Plan 01: Fundação de schema — colunas aditivas + seed fonoclama Summary

**3 colunas aditivas (os.lotacao_id, ativos.grama_maquina_id, catalogo_planos.arquivado_motivo) mais o seed de modulos_registrados para o módulo fonoclama, todas idempotentes via PRAGMA table_info.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-07-03T18:50:00-03:00 (aprox.)
- **Completed:** 2026-07-03T18:58:48-03:00
- **Tasks:** 2/2 completos
- **Files modified:** 2

## Accomplishments
- `backend/db_core.py`: 3 colunas aditivas adicionadas seguindo identicamente o padrão `PRAGMA table_info` + `ALTER TABLE ADD COLUMN` condicional já existente no arquivo — `os.lotacao_id`, `ativos.grama_maquina_id`, `catalogo_planos.arquivado_motivo` (novo bloco `catalogo_planos_existing`).
- `data/schema_catalogo.sql`: seed `INSERT OR IGNORE INTO modulos_registrados` ganhou a linha `('fonoclama', 'Sistema de aviso sonoro (fonoclama)', '["fonoclama"]')`.
- Verificado ponta a ponta contra `data/core.db`: init 2x sem erro (idempotência), `os.departamento` intacto, `GET /api/sync/manifest?modulo=fonoclama` retorna HTTP 200 com 10 ativos e 5 planos distintos (7 entradas flatten em `planos_manutencao`, agrupadas em 5 `plano_id`), `GET /api/usuarios` segue 200 OK (contrato não quebrado). Nenhuma mudança em `backend/sync.py`.

## Task Commits

Each task was committed atomically:

1. **Task 1: Adicionar 3 colunas aditivas em db_core.py** - `b8bcda1` (feat)
2. **Task 2: Registrar módulo fonoclama no seed** - `2969a39` (feat)

**Plan metadata:** (pendente — commit final de docs feito pelo passo de state_updates)

## Files Created/Modified
- `backend/db_core.py` - 3 novos pares (coluna, DDL) nos blocos de migração aditiva de `ativos`, `ordens_servico`, e um novo bloco `catalogo_planos_existing`
- `data/schema_catalogo.sql` - nova linha de seed `fonoclama` no `INSERT OR IGNORE INTO modulos_registrados`

## Decisions Made
- `nome='fonoclama'` (sem prefixo `pmoc_`) no seed, conforme instrução explícita do PLAN.md (Task 2 `<action>`), que sobrepõe a recomendação do RESEARCH §5.2 (`pmoc_fonoclama`) — o critério de aceitação do ROADMAP exige literalmente `?modulo=fonoclama`, e `sync.py` resolve por `nome` exato.
- `catalogo_planos.arquivado_motivo` foi adicionado apenas como coluna (Opção B do RESEARCH §6.2/D-07); o `UPDATE` que efetivamente arquiva o plano climatização órfão (`plano-3c349c22f4`) não faz parte deste plano — este plano entrega só a coluna que os planos de lógica (10-05) vão consumir.

## Deviations from Plan

None - plano executado exatamente como escrito.

## Issues Encountered
- Primeira tentativa de contar `planos` no manifest usou a chave errada (`planos` em vez de `planos_manutencao`, que é a chave real da resposta de `backend/sync.py:573`). Corrigido na própria verificação — não afetou o código produzido, só o comando de teste ad-hoc.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- As 3 colunas aditivas estão prontas para os planos de lógica da Wave 2 (10-03 consome `os.lotacao_id`, 10-04 consome `ativos.grama_maquina_id`, 10-05 consome `catalogo_planos.arquivado_motivo`) sem disputar `backend/db_core.py`.
- Módulo fonoclama já resolve no manifest — nenhum bloqueio para o restante da fase.
- Nenhum stub, nenhuma mudança de contrato pendente.

---
*Phase: 10-dados-conectividade*
*Completed: 2026-07-03*

## Self-Check: PASSED

- FOUND: backend/db_core.py
- FOUND: data/schema_catalogo.sql
- FOUND: .planning/phases/10-dados-conectividade/10-01-SUMMARY.md
- FOUND: b8bcda1 (git log)
- FOUND: 2969a39 (git log)
