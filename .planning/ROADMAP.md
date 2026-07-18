# Roadmap: xCMASM ERP

## Milestones

- ✅ **v1.0 — Produção: Import + Hardening** — Phases 1-9 (shipped 2026-06-29)
- 🚧 **v2.0 — Conectividade, Deploy & Conteúdo** — Phases 10-15 (planning)

## Phases

<details>
<summary>✅ v1.0 — Produção: Import + Hardening (Phases 1-9) — SHIPPED 2026-06-29</summary>

- [x] Phase 1: Registrar Uso (2/2 plans) — completed 2026-06-28
- [x] Phase 2: Plano no Ativo (2/2 plans) — completed 2026-06-29
- [x] Phase 3: Estoque Sobressalentes (2/2 plans) — completed 2026-06-29
- [x] Phase 4: Equipe Técnica (2/2 plans) — completed 2026-06-29
- [x] Phase 5: Cronograma Preventivo (2/2 plans) — completed 2026-06-29
- [x] Phase 6: Residuais Funcionais (3/3 plans) — completed 2026-06-29
- [x] Phase 7: Auth Hardening (3/3 plans) — completed 2026-06-29
- [x] Phase 8: Ajuda e Documentação (3/3 plans) — completed 2026-06-29
- [x] Phase 9: Limpeza Final (1/1 plan) — completed 2026-06-29

Full detail: `.planning/milestones/v1.0-ROADMAP.md`

</details>

### v2.0 — Conectividade, Deploy & Conteúdo (Phases 10-15)

- [x] **Phase 10: Dados & Conectividade** - Ligar FKs mortas, unificar cadastros duplicados e limpar dados órfãos (completed 2026-07-03)
- [ ] **Phase 11: Residuais Funcionais** - Completar backfills, térmico real, disparo por_tempo e prefills que ficaram pela metade
- [ ] **Phase 12: Documentos — Vínculo & População** - Anexar documentos a ativos/OS/locais e popular o acervo de ~45 referências
- [ ] **Phase 13: Portabilidade & Deploy** - Same-origin, satélites derivados de location, Leaflet vendored e proxy-friendly
- [ ] **Phase 14: Import de Features** - Export CSV/XLSX, matriz de priorização GUT e gráficos Chart.js no dashboard
- [ ] **Phase 15: Consulta Pública QR + Manual & Demo** - Página pública read-only por QR, etiquetas, manual do sistema e demo consolidada

## Phase Details

### Phase 10: Dados & Conectividade

**Goal**: Ligar as FKs mortas e unificar cadastros duplicados/órfãos para que organização e ativos resolvam por relacionamento real, não por colisão de string `codigo`.
**Depends on**: Nada (primeira fase v2.0 — fundação de dados)
**Requirements**: CON-01, CON-02, CON-03, CON-04, CON-05, CON-06
**Success Criteria** (what must be TRUE):

  1. Após o backfill idempotente, `locais.estrutura_id` está populado (0/163 → N/163) e as consultas de organização (`main.py:1967-1988`) resolvem por FK, não por `codigo`.
  2. `POST /api/os` grava a nova coluna aditiva `os.lotacao_id → estrutura(id)` na criação (unidade do solicitante ou seletor explícito); `os.departamento` permanece como rótulo denormalizado e o contrato de API existente não quebra.
  3. `GET /api/sync/manifest?modulo=fonoclama` retorna os 10 ativos + 5 planos de fonoclama (categoria registrada em `modulos_registrados`).
  4. As máquinas de corte deixam de ter cadastro duplo — `grama_maquinas` referencia `ativos` (FK + backfill por modelo/série) com `uso_atual` como fonte única, ou a tabela paralela está aposentada e documentada.
  5. Um relatório de integridade (script ou endpoint) lista inconsistências de conectividade (FK esperada não populada, `loc` sem `local_id`), e os dados órfãos (plano `climatizacao` `aplicavel_tipos='[]'` arquivado, `planos_manutencao` APOSENTADO) estão documentados como legado em `Rules.md`.

**Plans**: 6/6 plans complete

- [x] 10-01-PLAN.md — Fundação de schema: 3 colunas aditivas (lotacao_id, grama_maquina_id, arquivado_motivo) + seed fonoclama (CON-02/03/04/05)
- [x] 10-02-PLAN.md — CON-01: backfill idempotente locais.estrutura_id + verificação do cutover por FK (COALESCE)
- [x] 10-03-PLAN.md — CON-02: os.lotacao_id auto-fill do cargo do solicitante + seletor opcional no form da OS
- [x] 10-04-PLAN.md — CON-04: repoint de horas para ativos.uso_atual + maquinas por JOIN + backfill de link 1:1 (MS650/SOL)
- [x] 10-05-PLAN.md — CON-05: arquivar plano órfão via flag + documentar planos_manutencao aposentado em Rules.md
- [x] 10-06-PLAN.md — CON-06: GET /api/admin/integridade (role admin) + painel de integridade na aba admin

### Phase 11: Residuais Funcionais

**Goal**: Completar os dados e disparos que ficaram pela metade na v1.0 para que térmico, vencimentos por tempo e prefills de SR funcionem com dados reais.
**Depends on**: Phase 10
**Requirements**: RES-06, RES-07, RES-08, RES-09, RES-10
**Success Criteria** (what must be TRUE):

  1. `local_id` está backfillado nos ~50 ativos não-climatização (corte, fonoclama, viaturas/embarcações, elétrica); `local_id` é a fonte única e `ativos.loc` vira rótulo legado.
  2. O motor de refrigeração consome `locais.area_m2` e `altura_m` reais (importados de planilha) no cálculo térmico.
  3. O cálculo de vencimentos dispara `por_tempo` a partir da data da última execução (além de h/km), computando próximo/atraso corretamente.
  4. `proxima_execucao` do plano é populada na 1ª manutenção registrada do ativo.
  5. A abertura de SR pré-preenche ativo + item quando originada de um serviço/contexto (paridade com o prefill de OS já existente).

**Plans**: TBD

### Phase 12: Documentos — Vínculo & População

**Goal**: Dar vínculo aos documentos (ativo/OS/local) e popular o acervo de referência para que o módulo Documentos deixe de estar vazio e passe a ser navegável por contexto.
**Depends on**: Phase 10
**Requirements**: DOC-04, DOC-05, DOC-06
**Success Criteria** (what must be TRUE):

  1. `docs_documentos` ganha as colunas aditivas `vinculo_tipo` + `vinculo_id`; a UI de Documentos e a ficha do ativo exibem e permitem anexar o vínculo a um ativo / OS / local.
  2. A tabela legada `documentos` (0 rows) está formalmente depreciada e as referências `catalogo_servicos.pop_doc_id` e `usuario_qualificacoes.doc_id` repontam para `docs_documentos`.
  3. Um script de seed idempotente popula ~45 arquivos de referência únicos (NBR 5674, guias PMOC/POP, planos, Regimento Interno, cargos/TMFT, normas CFTV/redes), cada um na categoria correta com `tipo` significativo (`norma`/`modelo`/`checklist`/`pop`/`mapa`/`cadastro`).
  4. Reexecutar o seed não duplica registros (idempotência verificada).

**Plans**: TBD
**UI hint**: yes

### Phase 13: Portabilidade & Deploy

**Goal**: Tornar o núcleo acessível fora de localhost — same-origin, URLs de satélites derivadas de `location`, assets vendored localmente e porta proxy-friendly — sem quebrar o desenvolvimento local.
**Depends on**: Phase 12 (independente das fases de dados; sequenciada aqui, pode rodar em paralelo)
**Requirements**: DEP-01, DEP-02, DEP-03, DEP-04, DEP-05
**Success Criteria** (what must be TRUE):

  1. As chamadas que hoje caem no fallback `http://localhost:8010` (`erp-docs.js`, `bridgeBackendLogin()` em `cmasm_erp.html`, `xcmasm-sdk.js`, `pmoc-engine.js`) usam same-origin (`''`/`location.origin`); Documentos e login bridge funcionam servidos de qualquer host.
  2. As URLs dos módulos satélites (predial, aguada, paiol, calibração, segurança) abertas via `window.open()` derivam de `location.hostname` ou de `GET /api/satellites`, funcionando para usuário remoto.
  3. Leaflet (CSS+JS) é servido de `assets/`; a página `mapa` funciona em rede fechada/air-gapped sem depender do CDN unpkg.
  4. A porta `:8010` deixa de ser hardcoded em `pmoc.js` e `xcmasm-shell.js` (omitida em 80/443 ou configurável) — o núcleo é acessível atrás de proxy reverso.
  5. `.env.example` traz um exemplo de `CORS_ORIGINS` de produção documentado, copiável verbatim sem falha de CORS.

**Plans**: TBD
**UI hint**: yes

### Phase 14: Import de Features

**Goal**: Importar features maduras dos apps irmãos — export universal CSV/XLSX, matriz de priorização GUT e gráficos de tendência no dashboard.
**Depends on**: Phase 13
**Requirements**: FEA-01, FEA-02, FEA-03
**Success Criteria** (what must be TRUE):

  1. Todas as tabelas principais (ativos, OS, estoque, catálogo) exportam CSV/XLSX via helper genérico (padrão de xCalibracao `app.js`).
  2. Existe uma matriz de priorização GUT (Gravidade × Urgência × Tendência, seletores 1–5, score `g*u*t`, ranking colorido) aplicável a OS/inspeções.
  3. O dashboard exibe gráficos de tendência (Chart.js vendored, séries temporais de OS/estoque) com auto-refresh, além dos cards numéricos atuais.

**Plans**: TBD
**UI hint**: yes

### Phase 15: Consulta Pública QR + Manual & Demo

**Goal**: Entregar a consulta pública read-only por QR (endpoint + página + etiquetas) e fechar o milestone documentando o sistema já completo com manual e demo atualizados.
**Depends on**: Phase 14 (última — documenta o sistema finalizado)
**Requirements**: PUB-01, PUB-02, PUB-03, MAN-01, MAN-02
**Success Criteria** (what must be TRUE):

  1. `GET /publico/...:id` retorna o status de um ativo/OS sem autenticação, limitado a campos seguros de consulta.
  2. Uma página pública sem login renderiza o card de status de um ativo/OS a partir do `?id` (padrão de xCalibracao `publica.html`), consumível por leitura de QR em campo.
  3. É possível imprimir etiquetas com QR (folha `@media print`, QR gerado client-side) que apontam para a página pública de consulta.
  4. O manual do sistema (módulos, fluxos ativos → planos → OS → estoque, papéis/permissões, operação do PMOC) está versionado e acessível pelo módulo Documentos.
  5. A demo HTML está consolidada e atualizada a partir de `demos/demo.html`, refletindo os módulos atuais para apresentação.

**Plans**: TBD
**UI hint**: yes

## Progress

| Phase | Milestone | Plans | Status | Completed |
|-------|-----------|-------|--------|-----------|
| 1. Registrar Uso | v1.0 | 2/2 | Complete | 2026-06-28 |
| 2. Plano no Ativo | v1.0 | 2/2 | Complete | 2026-06-29 |
| 3. Estoque Sobressalentes | v1.0 | 2/2 | Complete | 2026-06-29 |
| 4. Equipe Técnica | v1.0 | 2/2 | Complete | 2026-06-29 |
| 5. Cronograma Preventivo | v1.0 | 2/2 | Complete | 2026-06-29 |
| 6. Residuais Funcionais | v1.0 | 3/3 | Complete | 2026-06-29 |
| 7. Auth Hardening | v1.0 | 3/3 | Complete | 2026-06-29 |
| 8. Ajuda e Documentação | v1.0 | 3/3 | Complete | 2026-06-29 |
| 9. Limpeza Final | v1.0 | 1/1 | Complete | 2026-06-29 |
| 10. Dados & Conectividade | v2.0 | 6/6 | Complete   | 2026-07-03 |
| 11. Residuais Funcionais | v2.0 | 0/? | Not started | - |
| 12. Documentos — Vínculo & População | v2.0 | 0/? | Not started | - |
| 13. Portabilidade & Deploy | v2.0 | 0/? | Not started | - |
| 14. Import de Features | v2.0 | 0/? | Not started | - |
| 15. Consulta Pública QR + Manual & Demo | v2.0 | 0/? | Not started | - |

### Phase 16: Modulo Predial (incorporar xPredial: rotas FastAPI, frontend, migracao de dados)

**Goal:** [To be planned]
**Requirements**: TBD
**Depends on:** Phase 15
**Plans:** 0 plans

Plans:

- [ ] TBD (run /gsd-plan-phase 16 to break down)
