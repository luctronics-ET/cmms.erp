# xCMASM ERP

## What This Is

Plataforma modular de gestão de ativos e serviços do CMASM (Centro de Mísseis e Armas Submarinas), instalação naval brasileira. Núcleo = backend FastAPI + ERP web single-file (`cmasm_erp.html`) com Manutenção categorizada por tipo de ativo, integrado a um PMOC único offline-first (`pmoc/`) que sincroniza via API. Uso interno por técnicos e gestores da Divisão de Manutenção.

## Core Value

A gestão de manutenção (ativos → planos → OS → estoque) tem que funcionar de ponta a ponta com os dados reais já cadastrados; nada deste milestone pode quebrar o que já roda em produção.

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

### Active

<!-- Escopo deste milestone: produção. Hipóteses até entregues e validadas. -->

**Import de features legadas (front visual bom → integrar ao `core.db`):**
- [ ] Aba "Registrar Uso" (incremento de `uso_atual` por ativo) — de `.docs_cmasm/referencias/CMASM_Gestao_v2.html`
- [ ] Manutenção: plano aplicado ao ativo selecionado + itens de serviço com checkboxes (multi-seleção) — de `CMASM_Gestao_v2.html`
- [ ] Estoque de sobressalentes (estoque local dos técnicos) — de `CMASM_Gestao_v2.html`
- [ ] Equipe Técnica — de `.docs_cmasm/referencias/cmasm13-govbr-v8_3.html`
- [ ] Cronograma de manutenção preventiva + cálculo do cronograma considerando a equipe — de `cmasm13-govbr-v8_3.html`
- [ ] Detalhes visuais menores adicionais, importados incrementalmente ("aos poucos")

**Residuais funcionais (FALTAs do `todo.md`):**
- [ ] Térmico real: preencher `locais.area_m2` / `altura_m`
- [ ] Disparo `por_tempo` no vencimento (base de data/última execução)
- [ ] SR pré-preencher ativo+item quando vier de serviço; gravar `departamento` na OS (coluna nova)
- [ ] Religar `local_id` dos ativos não-climatização; atribuir local de `refri171`
- [ ] Role `visualizador` enforced nas rotas (403 em escrita)

**Qualidade e segurança mínima:**
- [ ] Expandir suíte pytest cobrindo código novo/alterado (não regredir produção)
- [ ] Segurança mínima: substituir hash djb2 por bcrypt + remover senha default `1234`/`170842`
- [ ] Revisões/ajustes/melhorias sucessivas até o código estar OK (não precisa 100% funcional)

### Out of Scope

- Migração de banco (SQLite → Postgres) — escala atual não justifica; registrado como ideia futura
- CSRF / token httpOnly cookie / rate-limiting — rede interna fechada; risco aceitável por ora
- Performance pesada (paginação de listas, cache de vencimentos, pool de conexão) — só se for barato; senão fora
- Reescrita total do monolito `cmasm_erp.html` — refatorar só onde dói
- Runtime de hardware de módulos externos (aguada-web, xSeguranca, xCFTV, firmware Fonoclama) — sistemas próprios

## Context

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
| Importar features do legado HTML em vez de reescrever | Visual/layout legado já bom; menor risco; aproveita trabalho feito | — Pending |
| Import incremental ("aos poucos") com revisões sucessivas | Reduz risco em produção; permite validar cada feature antes da próxima | — Pending |
| Migração de banco fora de escopo | Escala atual (SQLite) suficiente; migração dominaria o milestone | — Pending |
| Segurança só mínima (bcrypt + sem default) | Rede interna; CSRF/cookies/rate-limit dariam escopo grande sem ganho proporcional agora | — Pending |
| Preservar dados de produção; migrações aditivas | Sistema já em uso com dados reais | — Pending |

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
*Last updated: 2026-06-28 after initialization*
