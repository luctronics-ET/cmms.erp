---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: — Conectividade, Deploy & Conteúdo
current_phase: 0
current_phase_name: roadmap v2.0 aprovado, 6 fases 10-15
status: planning
stopped_at: Phase 10 context gathered
last_updated: "2026-07-03T20:06:51.275Z"
last_activity: 2026-07-03
last_activity_desc: Roadmap v2.0 criado (Phases 10-15, 27 requisitos mapeados)
progress:
  total_phases: 6
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-07-03)

**Core value:** A gestão de manutenção (ativos → planos → OS → estoque) funciona de ponta a ponta com os dados reais já cadastrados; nada deste milestone quebra o que já roda em produção.
**Current focus:** Phase 10 — Dados & Conectividade (roadmap v2.0 criado; pronto para planejar)

## Current Position

Phase: Not started (roadmap v2.0 aprovado, 6 fases 10-15)
Plan: —
Status: Ready to plan Phase 10
Last activity: 2026-07-03 — Roadmap v2.0 criado (Phases 10-15, 27 requisitos mapeados)

## Performance Metrics

**Velocity:**

- Total plans completed: 20 (v1.0)
- Average duration: -
- Total execution time: -

**By Phase (v1.0):**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 | 2 | - | - |
| 02 | 2 | - | - |
| 03 | 2 | - | - |
| 04 | 2 | - | - |
| 05 | 2 | - | - |
| 06 | 3 | - | - |
| 07 | 3 | - | - |
| 08 | 3 | - | - |
| 09 | 1 | - | - |

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent roadmap decisions affecting current work:

- Roadmap v2.0: Numeração continua da v1.0 — v2.0 abre na Phase 10 (não reseta).
- Roadmap v2.0: 7 frentes (F10-F16) compactadas em 6 fases (granularity standard) — F15 (Consulta Pública) + F16 (Manual & Demo) fundidas na Phase 15 final, pois ambas são entregas de fechamento voltadas para fora.
- Roadmap v2.0: Phase 10 (Dados & Conectividade) primeiro por ser fundação — CON-01 (`locais.estrutura_id`) e o backfill de FKs destravam consultas de organização usadas rio abaixo.
- Roadmap v2.0: RES-06 (backfill `ativos.local_id`) fica na Phase 11 logo após a fundação de conectividade da Phase 10.
- Roadmap v2.0: DOC-04/05 (colunas vínculo) precedem DOC-06 (seed) dentro da Phase 12; população usa o vínculo.
- Roadmap v2.0: PUB-01 (endpoint público) precede PUB-02/03 (página + etiquetas) dentro da Phase 15.
- Roadmap v2.0: DEP-* (portabilidade) é independente — sequenciado no meio (Phase 13), pode rodar em paralelo às fases de dados.

### Pending Todos

None yet.

### Blockers/Concerns

- **Pre-Phase 10 (CON-02):** Confirmar de onde a lotação da OS é derivada na criação (unidade do solicitante vs. seletor explícito) antes de adicionar `os.lotacao_id` — não quebrar o contrato `POST /api/os` que PMOC + satélites consomem.
- **Pre-Phase 10 (CON-04):** Decidir entre FK `grama_maquinas → ativos` (com backfill por modelo/série) vs. aposentar a tabela paralela — checar quem lê `grama_maquinas` hoje (`/api/grama/*`).
- **Pre-Phase 11 (RES-07):** Localizar a planilha-fonte de `area_m2`/`altura_m` dos locais antes do import; `altura_m` já foi adicionada como coluna na v1.0 (Phase 6).
- **Pre-Phase 13 (DEP-02):** Enumerar os satélites e suas portas atuais (predial, aguada, paiol, calibração, segurança) para derivar URLs de `location`/`GET /api/satellites`.
- **Invariante (todas as fases):** migrações aditivas (`PRAGMA table_info` antes de `ALTER`, nunca `DROP`); backfills idempotentes; não quebrar `/api/usuarios`, `/api/os`, `/api/sync/*`.

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| Performance | Paginação, cache de vencimentos, pool de conexão | Deferred | v2.0 planning |
| Security | CSRF / httpOnly cookie / rate-limiting | Deferred | v2.0 planning |
| Audit | Audit trail de mutações | Deferred | v2.0 planning |
| UI import | Shell govbr acessível completo | Deferred | v2.0 planning |

## Session Continuity

Last session: 2026-07-03T20:06:51.243Z
Stopped at: Phase 10 context gathered
Resume file: .planning/phases/10-dados-conectividade/10-CONTEXT.md

## Operator Next Steps

- Plan the first v2.0 phase with /gsd-plan-phase 10
