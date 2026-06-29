# Retrospective — xCMASM ERP

## Milestone: v1.0 — Produção: Import + Hardening

**Shipped:** 2026-06-29
**Phases:** 9 | **Plans:** 20

### What Was Built
Importou 5 telas legadas (Registrar Uso, Plano-no-ativo, Sobressalentes, Equipe Técnica, Cronograma) do HTML legado para o `core.db` via router `backend/manutencao.py` + `schema_manutencao.sql`; fechou 5 residuais funcionais; trocou djb2 por Argon2id com upgrade lazy; adicionou o módulo Ajuda & Documentação (`backend/docs.py`, upload versionado seguro); removeu os HTMLs legados. 18/18 requisitos, 138 testes verdes.

### What Worked
- **Fatias verticais (MVP) por feature**: cada import shippado e verificado independente — "aos poucos" reduziu risco em produção.
- **Pipeline research → plan → plan-check → execute → code-review → verify por fase** pegou bugs reais que testes não pegariam: XSS em alerta de vencimento, crash pós-commit em `_vencimentos`, **auth bypass via /static** no módulo docs, RES-05 incompleto em 2 rotas (pego no integration check do milestone).
- **Research ancorado em file:line** + planner Opus deram execução precisa; deviations dos executores foram corretas (renomear tabelas em colisão, anti-sibling no path check).
- **Argon2id lazy upgrade** evitou lockout; contrato de login preservado p/ módulos externos.

### What Was Inefficient
- Suíte completa lenta (~5min, seeding no boot) → vários timeouts; executores rodaram alvos targeted.
- Plan-checker (haiku) gerou muitos "blockers" que eram rigor de verify-command, não defeito — resolvidos injetando guardrails no executor em vez de re-planejar (economizou round-trips).
- 14 falhas pré-existentes (10 endpoints catalogo não-implementados + sync legado) viraram ruído de baseline o milestone inteiro; 2 fechadas.
- Slug do roadmapper quebrou com `&`/acentos (fase 8) → renomeei p/ ASCII.

### Patterns Established
- Transação atômica = `aiosqlite.connect` raw + commit único (não CoreDB.execute por-statement).
- DOM seguro no frontend: `el()`/`textContent`/`replaceChildren`, nunca `innerHTML` de dado do servidor.
- Migração aditiva: `CREATE TABLE IF NOT EXISTS` em arquivo schema próprio + `CoreDB._SCHEMAS`, nunca DROP.
- Guard de escrita: `_require_escrita`/check `visualizador` em TODA rota de escrita.
- Storage de arquivo fora da árvore servida por `/static` (auth bypass).

### Key Lessons
- **Integration check no fim do milestone vale ouro**: RES-05 tinha escapado em 2 rotas criadas antes do guard (Fases 1-2 < Fase 6).
- **/static mount na raiz do repo é perigoso**: qualquer arquivo gravado vira público — armazenar uploads fora da árvore.
- Comentários de procedência ("portado do legado X") conflitam com critério de grep-zero na limpeza; decidir cedo manter vs remover.

### Cost Observations
- Model mix: planner Opus, executores/reviewers Sonnet, plan-checker Haiku (adaptive).
- Execução autônoma com agentes em background (plan/execute/review/verify) manteve o contexto do orquestrador enxuto.
