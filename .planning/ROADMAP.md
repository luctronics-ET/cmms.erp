# Roadmap: xCMASM ERP — Produção (Import + Hardening)

## Overview

Milestone de produção: importar cinco telas aprovadas do legado HTML ao `core.db` um slice de cada vez (Copy-Section-Wire), resolver residuais funcionais, fortalecer a segurança mínima e limpar os arquivos de referência após verificação. Cada fase entrega uma fatia vertical completa (schema + endpoint + UI + testes) e é verificada em produção antes de avançar à próxima. Nada neste milestone quebra o que já roda.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

- [ ] **Phase 1: Registrar Uso** - Import da aba "Registrar Uso" com schema skeleton, endpoint atômico e testes de migração
- [ ] **Phase 2: Plano no Ativo** - Import dos checkboxes de plano por ativo com estado persistido por máquina
- [ ] **Phase 3: Estoque Sobressalentes** - Import do estoque local dos técnicos separado do estoque central
- [ ] **Phase 4: Equipe Tecnica** - Import do cadastro de equipe e configuração de capacidade
- [ ] **Phase 5: Cronograma Preventivo** - Import do cronograma calculado com packing diário por capacidade de equipe
- [ ] **Phase 6: Residuais Funcionais** - Disparo por_tempo, departamento na OS, religar local_id, térmico real, role visualizador
- [ ] **Phase 7: Auth Hardening** - Substituir djb2 por Argon2id com upgrade lazy; remover senha default; expandir pytest
- [ ] **Phase 8: Limpeza Final** - Remover HTMLs legados de referência após verificação; checkpoint git

## Phase Details

### Phase 1: Registrar Uso
**Goal**: Técnico pode registrar uso (horas/km) de um ativo com incremento atômico de `uso_atual`, histórico auditável em `uso_registros`, e alerta de vencimento preventivo — enquanto o schema skeleton e o fixture async para testes também são estabelecidos nesta fase
**Mode:** mvp
**Depends on**: Nothing (first phase)
**Requirements**: IMP-01, QA-02
**Success Criteria** (what must be TRUE):
  1. Técnico seleciona um ativo, informa delta de uso e data, clica "Registrar" — `ativos.uso_atual` incrementa atomicamente no banco e um registro em `uso_registros` persiste com operador, data e snapshot do horímetro
  2. Se após o incremento `uso_atual >= proximo_uso` em algum plano do ativo, o frontend exibe alerta de vencimento preventivo na mesma interação
  3. Técnico consegue ver os registros recentes de uso do ativo na aba ("Registros Recentes")
  4. `pytest tests/` verde (sem regressão nos testes existentes); `test_migracoes_idempotencia` passa: `db.init()` executado duas vezes contra o mesmo banco sem erro de "duplicate column name"
  5. `backend/manutencao.py` registrado em `main.py` via `include_router`; `data/schema_manutencao.sql` adicionado à lista `CoreDB._SCHEMAS` com todas as tabelas novas em `CREATE TABLE IF NOT EXISTS`
**Plans**: TBD
**UI hint**: yes

### Phase 2: Plano no Ativo
**Goal**: Técnico seleciona um ativo e vê os itens do plano de manutenção aplicável com checkboxes, status de vencimento e barra de progresso — ao registrar, o estado por item fica persistido em `ativo_plano_estado`
**Mode:** mvp
**Depends on**: Phase 1
**Requirements**: IMP-02
**Success Criteria** (what must be TRUE):
  1. Técnico abre o ativo na aba de manutenção e vê a lista de itens do plano com checkbox, status (VENCIDA / URGENTE / PROXIMA / EM DIA), barra de progresso e "faltam X h"
  2. Técnico seleciona ao menos um item, informa responsável e clica "Registrar Manutenção" — um registro é gravado em `manut_registros` e `ativo_plano_estado.proximo_uso` é atualizado para cada item marcado na mesma transação
  3. Na próxima abertura do ativo, os status dos itens refletem o `proximo_uso` atualizado (VENCIDA não reaparece para item recém-executado)
  4. `pytest tests/test_manutencao.py::test_plano_no_ativo` verde; `proximo_uso` após dois registros consecutivos = `uso_no_momento + 2 × intervalo` (sem double-count)
**Plans**: TBD
**UI hint**: yes

### Phase 3: Estoque Sobressalentes
**Goal**: Técnico consulta e ajusta o estoque local de sobressalentes por categoria (separado do estoque central), com CRUD, ajuste de quantidade, log de movimentos e badges de status
**Mode:** mvp
**Depends on**: Phase 1
**Requirements**: IMP-03
**Success Criteria** (what must be TRUE):
  1. Técnico abre a aba "Sobressalentes" e vê a lista de peças com quantidade atual, unidade, badge de status (ZERADO / BAIXO / OK) e valor estimado do estoque
  2. Técnico pode adicionar nova peça, editar e fazer ajuste de quantidade (modal com motivo + obs) — quantidade é atualizada e movimento registrado em `sobressalentes_movimentos`
  3. O estoque de sobressalentes não interfere com os dados do `estoque` central (sem mistura de tabelas; `GET /api/estoque` retorna os mesmos registros de antes)
  4. `pytest tests/test_manutencao.py::test_sobressalentes` verde; CRUD e ajuste passam com banco limpo
**Plans**: TBD
**UI hint**: yes

### Phase 4: Equipe Tecnica
**Goal**: Gestor cadastra e visualiza a equipe técnica (membros com ou sem login de sistema) e configura a capacidade (número de equipes, dias úteis, turnos), alimentando o cálculo do cronograma
**Mode:** mvp
**Depends on**: Phase 1
**Requirements**: IMP-04
**Success Criteria** (what must be TRUE):
  1. Gestor abre a aba "Equipe Técnica" e vê o roster de membros com nome, posto/grad, especialidade e status ativo/inativo
  2. Gestor pode adicionar, editar e desativar membros — membros inativas ficam excluídos do cálculo de capacidade
  3. Gestor pode salvar a configuração de equipe (número de equipes, dias da semana, turnos com horas) e o resumo de capacidade (h/dia, h/semana, h/ano) é recalculado automaticamente
  4. `pytest tests/test_manutencao.py::test_equipe_tecnica` verde; config de equipe persiste em `equipe_config` e membros em `equipe_membros`
**Plans**: TBD
**UI hint**: yes

### Phase 5: Cronograma Preventivo
**Goal**: Gestor visualiza o cronograma de manutenção preventiva calculado dia-a-dia, com packing por capacidade de equipe, ordenação por criticidade e KPIs de mobilização
**Mode:** mvp
**Depends on**: Phase 4
**Requirements**: IMP-05
**Success Criteria** (what must be TRUE):
  1. Gestor abre a aba "Cronograma" e vê o plano dia-a-dia com os ativos agendados, criticidade (CRITICA → ALTA → MEDIA → BAIXA), duração estimada e capacidade usada vs disponível por dia
  2. KPIs de mobilização aparecem: total de OS, horas-pessoa estimadas, número de dias úteis, data de conclusão prevista e percentual de utilização — com alerta visual quando demanda > capacidade
  3. O cronograma respeita os dias úteis e turnos configurados na Fase 4 (Equipe Técnica) — alterar a config da equipe altera o cronograma no reload
  4. `pytest tests/test_manutencao.py::test_cronograma` verde; algoritmo de packing greedy produz resultado determinístico para um dataset fixo de ativos e config de equipe conhecida
**Plans**: TBD
**UI hint**: yes

### Phase 6: Residuais Funcionais
**Goal**: Os cinco gaps funcionais documentados no backlog são resolvidos sem quebrar contratos de API existentes: disparo por_tempo, departamento na OS, SR prefill, religar local_id e role visualizador enforced
**Mode:** mvp
**Depends on**: Phase 2
**Requirements**: RES-01, RES-02, RES-03, RES-04, RES-05
**Success Criteria** (what must be TRUE):
  1. Planos com `tipo_gatilho = 'por_tempo'` geram alerta de vencimento com base em data da última execução + intervalo em dias — sem conflitar com o trigger `por_uso` (apenas um tipo por plano é avaliado, conforme `tipo_gatilho`)
  2. OS gravadas via `POST /api/os` incluem o campo `departamento` (lotação) na resposta; SR aberta a partir de um serviço pré-preenche `ativo_id` e `item` correspondentes
  3. Ativos não-climatização aparecem com `local_id` associado no `GET /api/ativos`; ativos do grupo `refri171` têm local atribuível via ERP
  4. Cálculo térmico usa `locais.area_m2` e `altura_m` quando preenchidos — e não quebra quando esses campos são NULL (fallback seguro)
  5. Rotas de escrita (`POST /api/os`, `POST /api/ativos`, `POST /api/estoque/{id}/movimentos`, etc.) retornam HTTP 403 para usuários com role `visualizador`; leitura (`GET`) continua funcionando
**Plans**: TBD

### Phase 7: Auth Hardening
**Goal**: Login usa Argon2id com upgrade lazy do hash na primeira autenticação bem-sucedida, sem lockout de usuários nem quebra dos módulos externos; senha default removida; suíte pytest expandida cobre as rotas de manutenção importadas
**Mode:** mvp
**Depends on**: Phase 5
**Requirements**: SEC-01, SEC-02, QA-01
**Success Criteria** (what must be TRUE):
  1. Usuário com hash djb2 antigo faz login com a senha correta e, na resposta, o banco já armazena o hash Argon2id — na próxima autenticação apenas o caminho Argon2 é usado; sem HTTP 401 em nenhuma conta existente
  2. Conta sem `pw_hash` (NULL ou vazio) não autentica — e o seed / endpoint `POST /api/usuarios` não cria mais contas com senha `1234` hardcoded
  3. `POST /api/auth/login` com as credenciais de conta de serviço dos módulos externos (xPredial, aguada-web, PMOC) continua retornando token válido sem nenhuma mudança nos módulos
  4. `pytest tests/test_manutencao.py` cobre todas as rotas novas de manutenção importadas (Fases 1–5) sem regredir os testes existentes; `pytest -x` verde na suíte completa
**Plans**: TBD

### Phase 8: Limpeza Final
**Goal**: Após todas as features importadas verificadas e testes verdes, os HTMLs legados de referência são removidos com checkpoint git — deixando o repositório sem arquivos de UI não mais necessários
**Mode:** mvp
**Depends on**: Phase 7
**Requirements**: CLN-01
**Success Criteria** (what must be TRUE):
  1. Tag git `milestone-import-verificado` criada antes de qualquer deleção, com o estado completo do milestone gravado
  2. `git rm` executado para os HTMLs de referência confirmadamente não mais necessários (todos os itens "Active" de PROJECT.md movidos para "Validated" antes da execução)
  3. `grep -r "Gestao_v2\|cmasm13-govbr" assets/ pmoc/ cmasm_erp.html` retorna zero resultados — nenhum código ativo referencia os arquivos deletados
  4. `pytest -x` verde após a limpeza — deleção de arquivos estáticos não afetou nenhum teste
**Plans**: TBD

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Registrar Uso | 0/? | Not started | - |
| 2. Plano no Ativo | 0/? | Not started | - |
| 3. Estoque Sobressalentes | 0/? | Not started | - |
| 4. Equipe Tecnica | 0/? | Not started | - |
| 5. Cronograma Preventivo | 0/? | Not started | - |
| 6. Residuais Funcionais | 0/? | Not started | - |
| 7. Auth Hardening | 0/? | Not started | - |
| 8. Limpeza Final | 0/? | Not started | - |
