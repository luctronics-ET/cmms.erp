# Requirements: xCMASM ERP — Produção (Import + Hardening)

**Defined:** 2026-06-28
**Core Value:** A gestão de manutenção (ativos → planos → OS → estoque) funciona de ponta a ponta com os dados reais já cadastrados; nada deste milestone quebra o que já roda em produção.

## v1 Requirements

Cada requisito mapeia para uma fase do roadmap. Brownfield: features importadas de HTML legado aprovado e ligadas ao `core.db`; migrações aditivas; contratos de API existentes preservados.

### Import de Features Legadas

- [ ] **IMP-01**: Técnico pode registrar uso (horas/km) de um ativo numa aba "Registrar Uso", incrementando `uso_atual` de forma atômica e gravando histórico (`uso_registros`)
- [ ] **IMP-02**: Técnico pode selecionar um ativo, ver o plano de manutenção aplicado e marcar múltiplos itens de serviço via checkboxes, salvando o estado por ativo (`ativo_plano_estado`)
- [ ] **IMP-03**: Técnico pode consultar o estoque de sobressalentes local (separado do estoque central) por categoria
- [ ] **IMP-04**: Gestor pode cadastrar e visualizar a equipe técnica (membros sem login de sistema) e a configuração de equipe que alimenta o cronograma
- [ ] **IMP-05**: Gestor pode visualizar o cronograma de manutenção preventiva calculado considerando a capacidade da equipe (endpoint computado, sem estado persistente)

### Residuais Funcionais

- [ ] **RES-01**: Sistema usa disparo `por_tempo` no cálculo de vencimento, com base em data/última execução
- [ ] **RES-02**: OS grava o `departamento` (lotação) numa coluna dedicada do backend; SR pré-preenche ativo+item quando vier de um serviço
- [ ] **RES-03**: Ativos não-climatização têm `local_id` religado e `refri171` recebe local atribuível
- [ ] **RES-04**: Térmico real usa `locais.area_m2`/`altura_m` quando preenchidos (sem quebrar quando ausentes)
- [ ] **RES-05**: Role `visualizador` é enforced nas rotas de escrita (retorna 403)

### Qualidade & Testes

- [ ] **QA-01**: Suíte pytest (async, httpx + asgi-lifespan) cobre as novas rotas de manutenção importadas, sem regredir os testes existentes
- [ ] **QA-02**: Migrações aditivas têm teste que roda o schema do zero e valida idempotência (`PRAGMA table_info`)

### Segurança Mínima

- [ ] **SEC-01**: Login verifica senha com Argon2id (substituindo djb2), com upgrade lazy do hash no primeiro login bem-sucedido, sem quebrar o contrato `POST /api/auth/login` usado por módulos externos
- [ ] **SEC-02**: Senha default hardcoded (`1234`/`170842`) é removida; ausência de hash não autentica

### Limpeza Final

- [ ] **CLN-01**: Após todas as features importadas serem verificadas e os testes verdes, os HTMLs legados de referência são removidos, deixando código limpo (com tag git de checkpoint antes da deleção)

## v2 Requirements

Reconhecidos, fora do roadmap atual.

### Performance

- **PERF-01**: Paginação nas listas (`/api/ativos`, `/api/os`, `/api/estoque`)
- **PERF-02**: Cache de vencimentos com TTL + índice em `proxima_execucao`
- **PERF-03**: Singleton de conexão aiosqlite com lock de escrita

### Segurança Avançada

- **SECA-01**: CSRF token + SameSite cookie; token em httpOnly cookie
- **SECA-02**: Rate-limiting nas rotas de auth
- **SECA-03**: Audit trail de mudanças (ativos, OS, estoque)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Migração SQLite → Postgres | Escala atual suficiente; dominaria o milestone |
| CSRF / cookies httpOnly / rate-limit | Rede interna fechada; escopo grande sem ganho proporcional agora |
| Reescrita total do monolito `cmasm_erp.html` | Refatorar só onde dói |
| Runtime de hardware de módulos externos | Sistemas próprios (aguada-web, xSeguranca, xCFTV, firmware) |
| Conflict-resolution avançado de sync offline | Last-write-wins atual aceitável p/ este milestone |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| IMP-01 | Phase 1 | Pending |
| QA-02 | Phase 1 | Pending |
| IMP-02 | Phase 2 | Pending |
| IMP-03 | Phase 3 | Pending |
| IMP-04 | Phase 4 | Pending |
| IMP-05 | Phase 5 | Pending |
| RES-01 | Phase 6 | Pending |
| RES-02 | Phase 6 | Pending |
| RES-03 | Phase 6 | Pending |
| RES-04 | Phase 6 | Pending |
| RES-05 | Phase 6 | Pending |
| SEC-01 | Phase 7 | Pending |
| SEC-02 | Phase 7 | Pending |
| QA-01 | Phase 7 | Pending |
| CLN-01 | Phase 8 | Pending |

**Coverage:**
- v1 requirements: 15 total
- Mapped to phases: 15 ✓
- Unmapped: 0 ✓

---
*Requirements defined: 2026-06-28*
*Last updated: 2026-06-28 — traceability preenchida pelo roadmapper*
