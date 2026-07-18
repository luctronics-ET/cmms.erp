---
phase: 10
slug: dados-conectividade
status: secured
threats_open: 0
asvs_level: 1
created: 2026-07-18
---

# Phase 10 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| startup → SQLite DDL | Migrações executadas no boot alteram o schema de produção | Schema (DDL aditivo) |
| cliente PMOC → GET /api/sync/manifest | Cliente de campo (sem token interativo) lê o manifest | Ativos/planos por categoria |
| script tools/ → SQLite | Backfills e arquivamento tocam dados de produção | locais.estrutura_id, ativos.grama_maquina_id, catalogo_planos |
| cliente/externo → POST /api/os | Corpo pode conter lotacao_id fornecido pelo cliente | OS + lotação |
| PUT /api/grama/operacoes/{id}/status → SQLite | Escrita de horas cruza para ativos.uso_atual | Horímetro |
| cliente → GET /api/admin/integridade | Dados de auditoria interna só para admin | Relatório de inconsistências |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-10-01 | Tampering | ALTER TABLE no startup | medium | mitigate | `backend/db_core.py`: 7× ADD COLUMN condicionado por `PRAGMA table_info`; nenhum DROP (única ocorrência é comentário "nunca DROP") | closed |
| T-10-02 | Information Disclosure | manifest fonoclama | low | accept | Contrato existente do PMOC; nenhum campo novo sensível | closed |
| T-10-SC | Tampering | npm/pip/cargo installs | low | accept | Nenhum pacote instalado nesta fase | closed |
| T-10-03 | Tampering | UPDATE locais.estrutura_id | medium | mitigate | `tools/backfill_estrutura_id.py`: `WHERE estrutura_id IS NULL` (linhas 14, 62); sem DELETE/DROP | closed |
| T-10-04 | Repudiation | backfill sem log | low | mitigate | Script imprime contagens antes/depois (9 prints de auditoria) | closed |
| T-10-05 | Spoofing | lotacao_id no corpo | low | accept | SQLite sem FK enforcement por padrão no repo; CON-06 (integridade) sinaliza inconsistências | closed |
| T-10-06 | Tampering | INSERT ordens_servico | low | mitigate | `backend/main.py:create_os` (2234): queries parametrizadas via bind (`VALUES (?,...)`) | closed |
| T-10-07 | Elevation of Privilege | create_os | low | mitigate | `_require_auth` + `_require_escrita` no path interno (main.py 2240-2241); path externo por modulo_origem preservado | closed |
| T-10-08 | Tampering | UPDATE ativos.uso_atual | medium | mitigate | `backend/grama.py` ~773: UPDATE parametrizado derivado de operação registrada; grama_maquinas preservada | closed |
| T-10-09 | Repudiation | link heurístico grama↔ativos | low | mitigate | `tools/backfill_grama_link.py`: só links 1:1 determinísticos; ambíguos não pareados (verificado por teste automatizado, UAT #18) | closed |
| T-10-10 | Information Disclosure | GET /api/grama/maquinas | low | accept | Mesmo shape existente; JOIN não expõe campo novo sensível | closed |
| T-10-11 | Tampering | UPDATE catalogo_planos | low | mitigate | `tools/archive_orphan_plano.py`: `WHERE id` fixo + `arquivado_motivo IS NULL`; linha única; sem DELETE/DROP | closed |
| T-10-12 | Repudiation | motivo de arquivamento | low | mitigate | `arquivado_motivo` grava causa auditável | closed |
| T-10-13 | Elevation of Privilege | GET /api/admin/integridade | high | mitigate | `_require_admin` (main.py 964) após `_require_auth`; 403 explícito se role != admin (main.py 807); UAT #24: 401/403/200 verificados | closed |
| T-10-14 | Information Disclosure | relatório de integridade | high | mitigate | Endpoint sempre gated por role admin (main.py 800-807); nunca exposto sem auth | closed |
| T-10-15 | Tampering | queries de integridade | medium | mitigate | Queries usam apenas literais fixas/parâmetros validados (docstring main.py 803); sem interpolação de input | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-10-01 | T-10-02 | Manifest já expõe categorias registradas ao PMOC por contrato existente; nenhum campo novo sensível adicionado | plan-time (10-01-PLAN) | 2026-07-18 |
| AR-10-02 | T-10-SC | Nenhum pacote novo instalado na fase (Package Legitimacy Audit = N/A) | plan-time (10-01-PLAN) | 2026-07-18 |
| AR-10-03 | T-10-05 | SQLite não impõe FK por padrão no repo (consistente com schema atual); lotacao_id inválido não quebra e o relatório de integridade (CON-06) sinaliza | plan-time (10-03-PLAN) | 2026-07-18 |
| AR-10-04 | T-10-10 | Shape/consumo já existente; JOIN não expõe campo novo sensível | plan-time (10-04-PLAN) | 2026-07-18 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-07-18 | 15 | 15 | 0 | orchestrator (L1 grep-depth, short-circuit: register plan-time + ASVS 1) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
