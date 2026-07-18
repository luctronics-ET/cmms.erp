# xCMASM ERP

## What This Is

Plataforma modular de gestão de ativos e serviços do CMASM (Centro de Mísseis e Armas Submarinas), instalação naval brasileira. Núcleo = backend FastAPI + ERP web single-file (`cmasm_erp.html`) com Manutenção categorizada por tipo de ativo, integrado a um PMOC único offline-first (`pmoc/`) que sincroniza via API. Uso interno por técnicos e gestores da Divisão de Manutenção.

## Core Value

A gestão de manutenção (ativos → planos → OS → estoque) tem que funcionar de ponta a ponta com os dados reais já cadastrados; nada deste milestone pode quebrar o que já roda em produção.

## Current Milestone: v2.0 Conectividade, Deploy & Conteúdo

**Goal:** Fechar as conexões de dados que ficaram frouxas na v1.0 (FKs mortas, colunas soltas, cadastros duplicados), tornar o sistema portável para fora de localhost, popular o módulo Documentos com o acervo de referência, e importar features maduras dos apps irmãos — sem quebrar produção.

**Target features:**
- **F10 — Dados & conectividade:** ligar FKs mortas (`locais.estrutura_id`, `estoque.local_id`), transformar `os.departamento` TEXT em FK `estrutura`, registrar módulo `fonoclama` no sync, unificar `grama_maquinas`↔`ativos`, limpar planos/dados órfãos.
- **F11 — Residuais funcionais:** térmico real (`locais.area_m2`/`altura_m`), disparo `por_tempo` no vencimento, `proxima_execucao` na 1ª manutenção, backfill de `local_id` dos ~50 ativos não-climatização, SR pré-preencher ativo+item.
- **F12 — Portabilidade / deploy:** eliminar fallbacks `http://localhost:8010` (usar same-origin), URLs de satélites derivadas de `location`, Leaflet vendored local, porta proxy-friendly, `.env.example` CORS de produção.
- **F13 — Documentos: vínculo + população:** colunas `vinculo_tipo`/`vinculo_id` em `docs_documentos`; seed de ~45 arquivos de referência (NBR 5674, guias PMOC, planos, regimento, cargos/TMFT, normas CFTV) via script.
- **F14 — Import de features:** export CSV/XLSX em todas as tabelas, matriz de priorização GUT, charts Chart.js no dashboard.
- **F15 — Consulta pública QR + etiquetas:** página pública read-only sem login (consulta de ativo/OS por QR via endpoint dedicado), impressão de etiquetas QR.
- **F16 — Manual + Demo:** manual do sistema (documento) + demo HTML consolidada e atualizada.

**Key context:** Escopo derivado de auditoria por 4 investigadores (conectividade via `core.db` real, páginas/portabilidade, acervo de docs, features de apps irmãos). Achados-chave: `locais.estrutura_id` 0/163, `os.departamento` 0/3, `grama_maquinas`×`ativos` duplo cadastro, `documentos`(0)×`docs_documentos`(3 sem vínculo), fonoclama fora do sync, fallback localhost dispara sempre (`XCMASM_API_BASE` nunca setado). Migrações aditivas; produção-first.

## Requirements

### Validated

<!-- Inferido do código existente (mapa em .planning/codebase/) — funcionalidades já em uso. -->

- ✓ Backend FastAPI servindo ERP + `/api/*` (auth, usuários, ativos, locais, OS, estoque, grama, catálogo, sync) — existente
- ✓ ERP web single-file (`cmasm_erp.html`) com Manutenção categorizada por tipo — existente
- ✓ PMOC único offline-first (`pmoc/`) com sync (manifest/push/cursor) — existente
- ✓ Catálogo de serviços + planos unificados (`catalogo_planos`) aplicáveis por tipo — existente
- ✓ Refrigeração: import 171 máquinas, motor de cálculo, planos preventivos, OS preventiva, estoque — existente
- ✓ Categorias replicadas: Corte, Transportes (viaturas/embarcações), Fonoclama — existente
- ✓ Débito de estoque ao concluir OS (idempotente); pré-preenchimento de OS/SR por contexto — existente
- ✓ Suíte pytest cobrindo catálogo, sync, imports e smoke de manutenção (`tests/`) — existente

<!-- Entregue no milestone v1.0 (Produção: Import + Hardening). -->

- ✓ Aba "Registrar Uso" — incremento atômico de `uso_atual` + histórico `uso_registros` + alerta de vencimento — **v1.0**
- ✓ Plano no ativo: itens com checkboxes, status/progresso, estado por item em `ativo_plano_estado` (anti-double-count) — **v1.0**
- ✓ Estoque de sobressalentes local dos técnicos (tabelas separadas do estoque central) — **v1.0**
- ✓ Equipe Técnica (membros + config de capacidade derivada) — **v1.0**
- ✓ Cronograma preventivo: packing greedy determinístico por capacidade de equipe + KPIs — **v1.0**
- ✓ Residuais: disparo `por_tempo`, `departamento` na OS + SR prefill, religar `local_id`, térmico `altura_m`, role `visualizador` 403 — **v1.0**
- ✓ Auth hardening: Argon2id com upgrade lazy do djb2, senha default removida — **v1.0**
- ✓ QA: suíte pytest expandida (auth, docs, todas as rotas de manutenção); 2 falhas pré-existentes fechadas — **v1.0**
- ✓ Módulo Ajuda & Documentação: ajuda contextual + repositório de documentos versionado por categoria (storage local seguro fora da árvore web) — **v1.0**
- ✓ Limpeza: HTMLs legados de referência removidos, código limpo (tag `milestone-import-verificado`) — **v1.0**

- ✓ Dados & Conectividade (F10): `os.lotacao_id` com auto-fill do solicitante, backfill `locais.estrutura_id` (FK + fallback COALESCE), horas de grama repontadas para `ativos.uso_atual` (fonte única), plano órfão arquivado via flag, fonoclama registrado no sync, relatório de integridade admin (`GET /api/admin/integridade` + painel na aba admin) — **v2.0 Phase 10**

### Active

<!-- Milestone v2.0 em execução — requisitos detalhados em REQUIREMENTS.md. -->

- Milestone **v2.0 Conectividade, Deploy & Conteúdo** em execução — Phase 10 entregue; restam F11–F15 + Phase 16 (Modulo Predial).
- Phase 16 (2026-07-18): incorporar xPredial como módulo nativo do núcleo (rotas FastAPI, frontend, migração de schema+dados do predial.db).
- Candidatos ainda diferidos: paginação, cache de vencimentos, CSRF/cookies/rate-limit, audit trail.

### Out of Scope

- Migração de banco (SQLite → Postgres) — escala atual não justifica; registrado como ideia futura
- CSRF / token httpOnly cookie / rate-limiting — rede interna fechada; risco aceitável por ora
- Performance pesada (paginação de listas, cache de vencimentos, pool de conexão) — só se for barato; senão fora
- Reescrita total do monolito `cmasm_erp.html` — refatorar só onde dói
- Runtime de hardware de módulos externos (aguada-web, xSeguranca, xCFTV, firmware Fonoclama) — sistemas próprios

## Context

- **Estado atual (v1.0 entregue 2026-06-29)**: 9 fases, 18 requisitos. Novos módulos no núcleo: Registrar Uso, Plano-no-ativo, Sobressalentes, Equipe Técnica, Cronograma (router `backend/manutencao.py` + `schema_manutencao.sql`), Auth Argon2id, e o módulo Ajuda & Documentação (`backend/docs.py` + `schema_docs.sql`, storage em `~/.cmasm/docs`). Suíte: 138 passed / 12 falhas pré-existentes (catalogo não-implementado + sync legado — fora de escopo). Tag `v1.0` + `milestone-import-verificado`.
- **Brownfield**: código maduro e em uso. Mapa completo em `.planning/codebase/` (STACK, ARCHITECTURE, STRUCTURE, CONVENTIONS, TESTING, INTEGRATIONS, CONCERNS).
- **Legado a importar**: HTMLs de referência em `.docs_cmasm/referencias/` (`CMASM_Gestao_v2.html`, `cmasm13-govbr-v8_3.html`, etc.) e material em `.delete/`. Visual/layout dessas telas é considerado bom — copiar front e ligar ao banco real.
- **Dados de produção**: preservar tudo que já existe no `core.db` (171 máquinas refrig, catálogo, planos, OS). Nenhum import pode destruir dado existente.
- **Correção ao mapa**: a suíte pytest existe (`tests/` com 7 arquivos + conftest) — o `CONCERNS.md`/`TESTING.md` gerado afirmou "0% coverage", o que está incorreto; expandir, não criar do zero.
- **Migrações de schema**: aditivas apenas (`PRAGMA table_info` antes de `ALTER`, nunca `DROP`).

## Constraints

- **Tech stack**: manter FastAPI + aiosqlite + SQLite + ERP vanilla JS single-file + PMOC offline-first. Sem novo framework.
- **Compatibilidade**: PMOC app de campo e módulos externos consomem `GET /api/usuarios` e `POST /api/os` — não quebrar contratos de API existentes.
- **Dados**: produção-first — preservar dados existentes; imports idempotentes e não-destrutivos.
- **Arquitetura**: refatorar só onde dói (cirúrgico por padrão; modularizar pontos críticos quando justificar).
- **Design**: tema dark obrigatório, JetBrains Mono + DM Sans (tokens em CLAUDE.md); reaproveitar layout legado já aprovado.
- **Segurança**: somente o mínimo barato neste milestone (bcrypt + sem senha default).

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Importar features do legado HTML em vez de reescrever | Visual/layout legado já bom; menor risco; aproveita trabalho feito | ✓ Good — 9 fases entregues sem quebrar produção |
| Import incremental ("aos poucos") com revisões sucessivas | Reduz risco em produção; permite validar cada feature antes da próxima | ✓ Good — review+verify por fase pegou bugs reais (XSS, auth bypass, crash pós-commit) |
| Migração de banco fora de escopo | Escala atual (SQLite) suficiente; migração dominaria o milestone | ✓ Good |
| Segurança mínima (Argon2id + sem default) | Rede interna; CSRF/cookies/rate-limit fora de escopo | ✓ Good — usou Argon2id (não bcrypt); upgrade lazy sem lockout |
| Preservar dados de produção; migrações aditivas | Sistema já em uso com dados reais | ✓ Good — todas migrações aditivas, db.init() idempotente |
| Phase 10: lotação da OS derivada da unidade do solicitante com override opcional | Resolve CON-02 sem quebrar `POST /api/os` (PMOC/satélites) | ✓ Good — contrato externo preservado (UAT #14) |
| Phase 10: `grama_maquinas` vira satélite de metadados linkado por `ativos.grama_maquina_id` | Resolve CON-04; `uso_atual` como fonte única de horas (Rules.md §3) | ✓ Good — só links 1:1 determinísticos |
| Incorporar xPredial como módulo nativo (Phase 16) em vez de satélite via proxy | Mesmo stack (FastAPI+aiosqlite+vanilla JS); elimina servidor separado; dados migram para o núcleo | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-07-18 after Phase 10 (Dados & Conectividade)*
