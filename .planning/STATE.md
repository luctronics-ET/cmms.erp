---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: — Conectividade, Deploy & Conteúdo
current_phase: 10
current_phase_name: dados-conectividade
status: executing
stopped_at: Phase 10 executed + verified (6/6 plans, VERIFICATION passed)
last_updated: "2026-07-03T22:44:04.932Z"
last_activity: 2026-07-03
last_activity_desc: Phase 10 execution started
progress:
  total_phases: 6
  completed_phases: 1
  total_plans: 6
  completed_plans: 6
  percent: 17
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-07-03)

**Core value:** A gestão de manutenção (ativos → planos → OS → estoque) funciona de ponta a ponta com os dados reais já cadastrados; nada deste milestone quebra o que já roda em produção.
**Current focus:** Phase 10 — dados-conectividade

## Current Position

Phase: 10 (dados-conectividade) — EXECUTING
Plan: 1 of 6
Status: Executing Phase 10
Last activity: 2026-07-03 — Phase 10 execution started

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

### Roadmap Evolution

- Phase 16 added (2026-07-18): Modulo Predial — incorporar xPredial como módulo nativo do núcleo (portar rotas FastAPI + frontend para os padrões do cmasm.erp, migrar schema + dados reais do predial.db, migração aditiva). Decisões: módulo nativo (não satélite proxy), migrar todos os dados, xPredial vira código incorporado. Mapa do codebase do xPredial disponível em `/home/luc/DEV_ERP/xPredial/.planning/codebase/`.

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

Last session: 2026-07-03T22:44:04.901Z
Stopped at: Phase 10 executed + verified (6/6 plans, VERIFICATION passed)
Resume file: .planning/phases/10-dados-conectividade/10-VERIFICATION.md

## Operator Next Steps

- Plan the first v2.0 phase with /gsd-plan-phase 10
