# Requirements — Milestone v2.0: Conectividade, Deploy & Conteúdo

**Defined:** 2026-07-03
**Milestone goal:** Fechar conexões de dados frouxas da v1.0, tornar o sistema portável para fora de localhost, popular Documentos com o acervo de referência, e importar features maduras dos apps irmãos — sem quebrar produção.
**Scope source:** Auditoria por 4 investigadores (conectividade via `core.db` real, páginas/portabilidade, acervo de docs, features de apps irmãos).

**Invariantes (valem para todo requisito):**
- Migrações de schema **aditivas** — `PRAGMA table_info` antes de `ALTER`, nunca `DROP`.
- Produção-first — nenhum passo destrói dado existente em `core.db`; backfills idempotentes.
- Contratos de API existentes (`GET /api/usuarios`, `POST /api/os`, `/api/sync/*`) não podem quebrar (PMOC + satélites dependem).
- Tema dark obrigatório; JetBrains Mono + DM Sans; sem novo framework de build no núcleo.

---

## v2.0 Requirements

### F10 — Dados & Conectividade (CON)

- [ ] **CON-01**: `locais.estrutura_id` é populado por backfill (`locais.codigo → estrutura.id`) e as consultas de organização passam a resolver por FK, não por colisão de string `codigo` (`main.py:1967-1988`).
- [ ] **CON-02**: OS grava a lotação como FK — nova coluna aditiva `os.lotacao_id → estrutura(id)`, preenchida na criação a partir da unidade do solicitante ou de seletor explícito; `os.departamento` fica só como rótulo denormalizado.
- [ ] **CON-03**: Categoria `fonoclama` é registrada em `modulos_registrados` (`categorias_atend='["fonoclama"]'`), de modo que os 10 ativos + 5 planos aparecem em `GET /api/sync/manifest`.
- [ ] **CON-04**: As máquinas de corte deixam de ter cadastro duplo — `grama_maquinas` passa a referenciar `ativos` (FK + backfill por modelo/série) com `uso_atual` como fonte única, ou a tabela paralela é aposentada.
- [ ] **CON-05**: Dados órfãos são limpos/parkados — plano `climatizacao` com `aplicavel_tipos='[]'` arquivado; `planos_manutencao` (0 rows, APOSENTADO) documentado como legado intencional em `Rules.md`.
- [ ] **CON-06**: Um relatório de integridade (script ou endpoint) sinaliza inconsistências de conectividade (ex.: `loc` preenchido com `local_id` nulo, FK esperada não populada) para auditoria contínua.

### F11 — Residuais Funcionais (RES, continua v1.0)

- [ ] **RES-06**: `local_id` é backfillado para os ~50 ativos não-climatização (corte, fonoclama, viaturas/embarcações, elétrica), tornando `local_id` a fonte única e `ativos.loc` um rótulo legado.
- [ ] **RES-07**: O cálculo térmico usa dados reais — `locais.area_m2` e `altura_m` são preenchidos (import de planilha) e consumidos pelo motor de refrigeração.
- [ ] **RES-08**: O disparo `por_tempo` funciona no cálculo de vencimentos — usa base de data da última execução para computar próximo/atraso, além dos disparos por h/km.
- [ ] **RES-09**: `proxima_execucao` do plano é populada na 1ª manutenção registrada do ativo.
- [ ] **RES-10**: A abertura de SR pré-preenche ativo + item quando originada de um serviço/contexto (paridade com o prefill de OS já existente).

### F12 — Portabilidade / Deploy (DEP)

- [ ] **DEP-01**: As chamadas de API que hoje caem no fallback `http://localhost:8010` passam a usar same-origin (`''`/`location.origin`) — `erp-docs.js`, `bridgeBackendLogin()` em `cmasm_erp.html`, `xcmasm-sdk.js`, `pmoc-engine.js` — de modo que Documentos e login bridge funcionam servidos de qualquer host.
- [ ] **DEP-02**: As URLs dos módulos satélites (predial, aguada, paiol, calibração, segurança) abertas via `window.open()` derivam de `location.hostname` ou de `GET /api/satellites`, não de `localhost` hardcoded — funcionam para usuário remoto.
- [ ] **DEP-03**: Leaflet (CSS+JS) é servido localmente de `assets/` em vez do CDN unpkg, de modo que a página `mapa` funciona em rede fechada/air-gapped.
- [ ] **DEP-04**: O núcleo é acessível atrás de proxy reverso — a porta `:8010` deixa de ser hardcoded em `pmoc.js` e `xcmasm-shell.js` (omitida em 80/443 ou configurável).
- [ ] **DEP-05**: `.env.example` traz um exemplo de `CORS_ORIGINS` de produção documentado, evitando falha de CORS ao copiar verbatim.

### F13 — Documentos: Vínculo + População (DOC, continua v1.0)

- [ ] **DOC-04**: `docs_documentos` ganha colunas aditivas `vinculo_tipo` + `vinculo_id`, permitindo anexar um documento a um ativo / OS / local; a UI de Documentos e a ficha do ativo expõem o vínculo.
- [ ] **DOC-05**: A tabela legada `documentos` (0 rows) é formalmente depreciada e as referências (`catalogo_servicos.pop_doc_id`, `usuario_qualificacoes.doc_id`) repontam para `docs_documentos`.
- [ ] **DOC-06**: O módulo Documentos é populado por script de seed idempotente com ~45 arquivos de referência únicos (NBR 5674, guias PMOC/POP, planos de manutenção, Regimento Interno, cargos/TMFT, normas CFTV/redes), cada um na categoria correta com `tipo` significativo (`norma`/`modelo`/`checklist`/`pop`/`mapa`/`cadastro`).

### F14 — Import de Features (FEA)

- [ ] **FEA-01**: Todas as tabelas principais (ativos, OS, estoque, catálogo) têm export CSV/XLSX via helper genérico (padrão importado de xCalibracao `app.js`).
- [ ] **FEA-02**: Existe matriz de priorização GUT (Gravidade × Urgência × Tendência, seletores 1–5, score `g*u*t`, ranking colorido) aplicável a OS/inspeções (padrão importado de xPredial `inspecao_gut.html`).
- [ ] **FEA-03**: O dashboard exibe gráficos de tendência (Chart.js vendored, séries temporais de OS/estoque) com auto-refresh — hoje só há cards numéricos.

### F15 — Consulta Pública QR + Etiquetas (PUB)

- [ ] **PUB-01**: Existe endpoint público read-only (`/publico/...:id`) que retorna o status de um ativo/OS sem autenticação, limitado a campos seguros de consulta.
- [ ] **PUB-02**: Uma página pública sem login renderiza o card de status de um ativo/OS a partir do `?id` (padrão importado de xCalibracao `publica.html`), consumível por leitura de QR em campo.
- [ ] **PUB-03**: É possível imprimir etiquetas com QR (folha `@media print`, QR gerado client-side) que apontam para a página pública de consulta.

### F16 — Manual + Demo (MAN)

- [ ] **MAN-01**: Existe um manual do sistema (documento) cobrindo módulos, fluxos (ativos → planos → OS → estoque), papéis/permissões e operação do PMOC — versionado e acessível pelo módulo Documentos.
- [ ] **MAN-02**: A demo HTML é consolidada e atualizada (a partir de `demos/demo.html`), refletindo os módulos atuais para apresentação.

---

## Future Requirements (deferidos)

- Paginação de listas grandes; cache de vencimentos; pool de conexão.
- CSRF / token httpOnly cookie / rate-limiting.
- Audit trail de mutações.
- Shell govbr acessível completo (sidebar+breadcrumb+avatar ARIA) — import estratégico maior, adiado; padrões pontuais (overlay mobile, breadcrumb) podem ser puxados sob demanda.
- Import de CSV com mapeamento de campos (xCalibracao `importar.html`); gestão de laudos/ART normativos (xPredial `laudos.html`).
- De-duplicação de UIs (refrigeração 3 UIs, transportes 3 surfaces) e das rotas duplicadas `/api/pmoc/refrigeracao` em `main.py` — housekeeping, avaliar por fase.

## Out of Scope

- Migração SQLite → Postgres — escala atual não justifica.
- Reescrita do monolito `cmasm_erp.html` — refatorar só onde dói.
- Runtime de hardware de módulos externos (aguada-web, xSeguranca, xCFTV, firmware Fonoclama) — sistemas próprios.
- SCADA/synoptic e player de vídeo CFTV — hardware-específico, sem reuso genérico.
- Merge de backends dos apps irmãos — importam-se padrões de UI/UX e features genéricas, não os backends.

## Traceability

*(Preenchido pelo roadmapper — mapeia cada REQ-ID à sua fase.)*
