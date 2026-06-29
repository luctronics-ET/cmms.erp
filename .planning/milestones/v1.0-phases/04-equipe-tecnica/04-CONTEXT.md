# Phase 4: Equipe Técnica - Context

**Gathered:** 2026-06-28
**Status:** Ready for planning
**Mode:** Smart discuss (autonomous, recommendations auto-accepted)

<domain>
## Phase Boundary

Gestor cadastra/visualiza a equipe técnica (membros com ou sem login) e configura a capacidade (nº de equipes, dias úteis, turnos com horas). Resumo de capacidade (h/dia, h/semana, h/ano) recalculado. Persiste em `equipe_membros` + `equipe_config`. Alimenta o cronograma (Fase 5). Visual portado de `.docs_cmasm/referencias/cmasm13-govbr-v8_3.html` (aba Equipe Técnica).

Fora: o cálculo do cronograma em si (Fase 5 consome esta capacidade); auth/login de membros (membros podem não ter login).
</domain>

<decisions>
## Implementation Decisions

### Modelo de dados (em schema_manutencao.sql)
- `equipe_membros`: `id` PK, `nome` NOT NULL, `posto_grad` (posto/graduação militar), `especialidade`, `tem_login` INTEGER DEFAULT 0, `usuario_mat` TEXT (nullable; link opcional a usuarios.mat quando o membro tem login), `ativo` INTEGER DEFAULT 1, `created_at`.
- `equipe_config`: configuração única (id fixo = 1 / singleton): `num_equipes` INTEGER, `dias_semana` TEXT (JSON lista, ex. ["seg","ter","qua","qui","sex"]), `turnos` TEXT (JSON, ex. [{"nome":"manhã","horas":4},{"nome":"tarde","horas":4}]), `updated_at`. Capacidade NÃO é coluna — é derivada (computed) na resposta.
- CREATE TABLE IF NOT EXISTS, aditivo, nunca DROP.

### Cálculo de capacidade (derivado, não persistido)
- `horas_por_dia` = Σ horas dos turnos.
- `horas_dia_total` = horas_por_dia × num_equipes × (membros ativos? — ver nota).
- `horas_semana` = horas_dia_total × len(dias_semana).
- `horas_ano` = horas_semana × 52 (ou dias_uteis/ano; usar 52 semanas como aproximação, documentar).
- Decisão: a capacidade base usa num_equipes × turnos × dias (config). O nº de membros ativos é informativo no roster; se o legado multiplica por membros, seguir o legado — o planner confirma lendo `cmasm13-govbr-v8_3.html`. Membros inativos excluídos de qualquer contagem.

### Contrato de endpoints (backend/manutencao.py — router já registrado)
- `GET /api/manutencao/equipe/membros` (lista; filtro ativo opcional), `POST` (criar), `PUT /{id}` (editar), `DELETE /{id}` ou `PUT /{id}` com ativo=0 (desativar — soft, nunca apagar).
- `GET /api/manutencao/equipe/config` (retorna config + resumo de capacidade computado), `PUT /api/manutencao/equipe/config` (salva config; resposta recomputa capacidade).
- `_require_auth` em todas; escritas exigem token não-visitante.

### Frontend (UX)
- Nova aba "Equipe Técnica" (TAB_DEFS em assets/erp-manutencao.js), visual portado do legado.
- Roster: tabela com nome, posto/grad, especialidade, status ativo/inativo; botões +Membro, editar, desativar.
- Painel de config: inputs nº de equipes, checkboxes dias da semana, lista de turnos (nome+horas); ao salvar, exibe resumo de capacidade (h/dia, h/semana, h/ano) recalculado.
- Fetch + Bearer token; DOM seguro via el()/textContent.

### Testes
- `tests/test_manutencao.py::test_equipe_tecnica`: criar/editar/desativar membro (inativo excluído da capacidade); salvar config → capacidade recomputada correta; persistência em equipe_membros + equipe_config (banco limpo).

### Claude's Discretion
- Shape fino de JSON e nomes de colunas/endpoints.
- Se a capacidade multiplica por membros ativos ou só por num_equipes — seguir o legado (planner decide lendo o arquivo).
- Singleton de equipe_config: id=1 fixo ou upsert.
</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/manutencao.py` (router, _db, _require_auth, atomic txn), `schema_manutencao.sql` (em _SCHEMAS).
- `GET /api/usuarios` (backend/main.py:1014) — para link opcional de membros com login (usuario_mat).
- `assets/erp-manutencao.js` (TAB_DEFS, padrão das abas Registrar Uso/Sobressalentes, el()).
- Legado: `.docs_cmasm/referencias/cmasm13-govbr-v8_3.html` (Equipe Técnica + cálculo de capacidade por turnos — fonte do visual e da fórmula).

### Established Patterns
- Migração aditiva, CREATE TABLE IF NOT EXISTS.
- Frontend vanilla, fetch + Bearer, DOM seguro via el().
- CRUD + soft-delete (ativo=0) já praticado nas fases anteriores.

### Integration Points
- Tabelas em schema_manutencao.sql; endpoints em backend/manutencao.py; aba em erp-manutencao.js.
- equipe_config consumido pela Fase 5 (cronograma).
</code_context>

<specifics>
## Specific Ideas

- Membros com ou sem login (posto/grad militar) — campo posto_grad relevante (contexto naval).
- Resumo de capacidade recalculado é requisito (alimenta cronograma).
- Visual segue o legado cmasm13-govbr-v8_3.html (aprovado).
</specifics>

<deferred>
## Deferred Ideas

- Cronograma que consome a capacidade → Fase 5.
- Sincronizar membros↔usuarios automaticamente → futuro (link manual via usuario_mat agora).
</deferred>
