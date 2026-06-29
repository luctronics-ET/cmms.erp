# Phase 6: Residuais Funcionais - Context

**Gathered:** 2026-06-28
**Status:** Ready for planning
**Mode:** Smart discuss (autonomous, recommendations auto-accepted)

<domain>
## Phase Boundary

Resolver os 5 gaps do backlog (todo.md) SEM quebrar contratos de API existentes:
- RES-01: disparo `por_tempo` no vencimento (data da última execução + intervalo em dias).
- RES-02: campo `departamento` na OS (`POST /api/os`) + SR pré-preenche ativo_id+item quando vem de serviço.
- RES-03: religar `local_id` dos ativos não-climatização; `refri171` com local atribuível via ERP.
- RES-04: térmico usa `locais.area_m2`/`altura_m` quando preenchidos, fallback seguro quando NULL.
- RES-05: role `visualizador` enforced — escritas retornam 403, leituras (GET) seguem.

Fora: auth hardening (Fase 7); novas features.
</domain>

<decisions>
## Implementation Decisions

### RES-01 — por_tempo
- Plano avalia UM tipo de gatilho conforme `tipo_gatilho` (`por_uso` xor `por_tempo`). Para `por_tempo`: alerta quando `hoje >= ultima_execucao + intervalo_dias`.
- Base de "última execução": usar `manut_registros` (Fase 2) e/ou um campo de data já existente; o planner confirma a fonte no código. Sem conflitar com `por_uso` (não avaliar os dois para o mesmo plano).
- Migração aditiva se precisar de coluna (ex. `intervalo_dias`/`tipo_gatilho` em catalogo_planos/itens) — PRAGMA antes de ALTER, nunca DROP. Reusar colunas existentes se já houver (`frequencia` JSON pode conter tipo+valor).

### RES-02 — departamento na OS + SR prefill
- `departamento` (lotação) gravado na OS: migração aditiva `ALTER TABLE os ADD COLUMN departamento TEXT` (guarded). `POST /api/os` aceita e a resposta inclui `departamento`. Não quebrar o shape existente (campo novo opcional).
- SR a partir de um serviço pré-preenche `ativo_id` e `item` no frontend (mecanismo `_osPrefill`/`setOsPrefill` já existe — estender para SR).

### RES-03 — religar local_id
- Backfill/atribuição de `local_id` para ativos não-climatização (script de migração idempotente em tools/ ou seed no boot, aditivo). `refri171` (ELETRÔNICA/BIBLIOTECA) recebe local atribuível pela ficha do ativo no ERP (já editável). `GET /api/ativos` passa a retornar local_id associado.
- Nunca apagar; só preencher onde NULL. Mapeamento conservador (o planner define a heurística; se ambíguo, deixar atribuível manual via ficha).

### RES-04 — térmico real
- Cálculo térmico lê `locais.area_m2` e `altura_m`. Quando NULL/ausente: fallback seguro (usar default atual ou pular o cálculo sem erro). Não quebrar telas quando os campos estão vazios.

### RES-05 — role visualizador 403
- Adicionar dependência/guard de role nas rotas de ESCRITA (POST/PUT/DELETE de os, ativos, estoque/movimentos, e as novas rotas de manutenção) → 403 se `user.role == 'visualizador'`. GET continua livre (auth normal).
- Implementar como helper reutilizável (ex. `_require_escrita(user)`), aplicado consistentemente. Não bloquear leitura.

### Testes
- `tests/test_manutencao.py` (ou test dedicado): por_tempo dispara por data; departamento persiste/retorna; térmico com area/altura NULL não quebra; visualizador recebe 403 em escrita e 200 em GET. Banco limpo, sem regressão.

### Claude's Discretion
- Fonte exata de "última execução" p/ por_tempo.
- Heurística de backfill de local_id (conservadora; manual quando ambíguo).
- Onde exatamente aplicar o guard de role (lista de rotas de escrita) — cobrir as principais.
</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/main.py`: `POST /api/os` (criação de OS), `GET /api/ativos`, rotas de estoque/movimentos, `manutencao_vencimentos` (~2527), auth/`role` do usuário no token.
- `manut_registros` (Fase 2) — data de execução p/ por_tempo.
- `catalogo_planos`/`catalogo_plano_itens` — `frequencia` JSON (tipo+valor) p/ por_tempo.
- `locais` (area_m2/altura_m) — térmico. `ativos.local_id`. `_osPrefill`/`setOsPrefill` (cmasm_erp.html) — SR prefill.
- `schema_core.sql` (tabela os, locais, ativos, estoque).

### Established Patterns
- Migração aditiva: PRAGMA table_info antes de ALTER, nunca DROP.
- Auth bearer; `user` tem `role`. Erros com `detail`.
- Frontend prefill via contexto (`novaOSComContexto`).

### Integration Points
- main.py (rotas existentes + guard de role), schema_core.sql (ALTER aditivo os.departamento + backfill local_id), cálculo térmico (refrig-engine/manutencao), frontend SR prefill.
</code_context>

<specifics>
## Specific Ideas

- "Sem quebrar contratos de API existentes" é requisito duro — campos novos opcionais, GETs inalterados.
- por_tempo e por_uso são mutuamente exclusivos por plano (avaliar só o tipo_gatilho).
- Role guard só em escrita; leitura livre.
</specifics>

<deferred>
## Deferred Ideas

- Auth hardening (bcrypt, default password) → Fase 7.
- Audit trail completo → v2 (SECA-03).
</deferred>
