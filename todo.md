# xCMASM · TODO / Backlog

> Atualizado: 2026-05-22 · alinhado à arquitetura **núcleo + PMOC único categorizado**.
> Fontes: `REQUISITOS.md`, `Regras de Negocio e Fluxos.md`, `Rules.md`, `MODULOS_EXTERNOS.md`.
> Spec da consolidação: `docs/superpowers/specs/2026-05-22-pmoc-unificado-design.md`.

---

## 🚨 P0 — Tela Manutenção categorizada no núcleo

O painel central de Manutenção em `cmasm_erp.html` deve mostrar todos os ativos agrupados por categoria, conforme `Regras de Negocio e Fluxos.md §7` e `Rules.md §6`.

- [ ] Tabs por categoria: `climatizacao`, `frota_terrestre`, `frota_naval`, `maquinas_corte`, `eletrica`, `predial`, `instrumentos`, `paiois_item`
- [ ] Lista de ativos por tab com status do próximo serviço:
  - 🟢 verde = `uso_atual < proximo_uso × 0,80`
  - 🟡 amarelo = `uso_atual ≥ proximo_uso × 0,80`
  - 🔴 vermelho = `uso_atual ≥ proximo_uso`
- [ ] Origem do `uso_atual` visível (OS concluída | push de PMOC | manual) com timestamp
- [ ] Atalho "Abrir OS preventiva" → cria PS pré-preenchido com snapshot do serviço
- [ ] Histórico de OS por ativo (modal)
- [ ] Substituir mocks por dados reais (`/api/os/kpis` + `/api/ativos`)

---

## 🚨 P0 — API de Catálogo de Serviços + Planos

Schema já existe (`data/schema_catalogo.sql`); falta a camada de endpoints.

- [ ] `GET/POST/PUT /api/catalogo/servicos` com versionamento imutável (cada edit → nova `versao`)
- [ ] `GET/POST/PUT /api/catalogo/planos`
- [ ] `GET/POST/PUT /api/catalogo/qualificacoes` + `/api/usuarios/{id}/qualificacoes`
- [ ] Incluir catálogo + planos + qualificações + POPs no `manifest` (filtro por categoria)
- [ ] Aceitar `ps_criada` com `servico_snapshot` (escopo local) — armazenar snapshot e não criar entrada em `catalogo_servicos`
- [ ] UI núcleo: CRUD de serviços/planos com simulação (carga prevista de OS/mês)
- [ ] Seed inicial: serviços de refrigeração (limpeza padrão split, troca de gás, limpeza de duto) — extrair de `pmoc.refs/CMASM_PMOC_REFRIG*.csv`
- [ ] Seed: qualificações a partir de `pmoc.refs/cmasm10_competencias.csv`

---

## 🚨 P0 — Fechamento da API de sincronização

Sync já está ~90% pronta. Contrato agora usa `modulo=<categoria>` (ex: `modulo=refrigeracao`), não mais `pmoc_<dom>`.

- [x] Schema `sync_eventos`, `sync_cursor`, `modulos_registrados` em `data/schema_catalogo.sql`
- [x] `GET /api/sync/manifest?modulo=&since=` (delta via `since=` ainda não implementado — retorna full)
- [x] `POST /api/sync/push` idempotente
- [x] `GET /api/sync/cursor?modulo=&device=`
- [x] `GET /api/modulos`
- [x] Handlers: `uso_atual_inc`, `estoque_mov`, `os_criada`, `os_status`, `documento_anexo`, `ps_criada`, `os_executada`, `inspecao_concluida`, `plano_adiado`, `qualificacao_uso`
- [ ] Manifest com delta (`since=`): retornar só ativos/serviços/planos com `atualizado_em > since`
- [ ] **Auth Bearer em todos os endpoints `/api/sync/*`**
- [ ] **Teste de integração end-to-end**: criar 50 eventos offline no PMOC, sync, conferir consistência

---

## 🚨 P0 — Esqueleto do PMOC único

App de campo único em `cmasm.erp/pmoc/`, com categorias internas. Substitui o conceito antigo de "N PMOCs separados".

- [x] Componentes UI base em `assets/pmoc-engine.js` v2 (vanilla JS): `header`, `table`, `modal`, `badge`, `kanban`, `calendar`, `chartDonut`, `chartLine`, `chat`, `camera`, `confirm`, `gantt`
- [x] `engine.bootstrap({ modulo, nucleo, cssPath })`
- [x] Eventos via `CustomEvent`
- [x] Demo standalone: `/assets/pmoc-engine-demo.html`
- [ ] **Criar `cmasm.erp/pmoc/index.html`** — shell único com seletor de categoria
- [ ] **Cliente sync embutido** (push/pull/cursor) — chama `/api/sync/*`
- [ ] **Wrapper IndexedDB** (`idb.get`, `idb.put`, `idb.bulkPut`, `idb.getAll`, `idb.delete`)
- [ ] **Auth helper** (login, refresh, cache de token)
- [ ] **Motor de planos** embutido (`resolverFrequencia`, `calcularProxima`, `avaliarCondicionais`, `verificarRecursos`)
- [ ] Servir `cmasm.erp/pmoc/` em `/pmoc/` via FastAPI (mount estático)
- [ ] **Categoria piloto: refrigeração** — seeds prontos em `pmoc.refs/`

---

## 🟠 P1 — Demais categorias do PMOC

Cada item abaixo é uma **seção interna** do PMOC único (não um repo).

- [ ] Categoria: predial
- [ ] Categoria: paióis
- [ ] Categoria: transportes
- [ ] Categoria: grama
- [ ] Categoria: elétrica
- [ ] Categoria: calibração

---

## 🟠 P1 — Núcleo: melhorias de Serviços / Estoque / Manutenção

### Serviços (PS → OS → SR) — Fase 2 da proposta_servicos_executiva.md

- [ ] Classificação múltipla: interna CMASM + CATSER/CATMAT + SINAPI
- [ ] Catálogo de serviços versionado (cada edição gera nova `versao`, imutável) — aproveitar `schema_catalogo.sql`
- [ ] Documentos e instruções versionadas vinculadas a OS
- [ ] Integração com Estoque: materiais em OS disparam `reservado → separado → consumido/devolvido`; falta de item obrigatório bloqueia execução
- [ ] Integração com Manutenção: planos preventivos/corretivos geram OS automaticamente por gatilho (tempo/uso/horímetro/odômetro)
- [ ] Origens: aceitar criação de OS via push do PMOC (`modulo_origem = <categoria>`, `origem_id = uuid`)
- [ ] Vínculo SR ↔ Estoque ↔ Transportes ↔ Predial usando o catálogo
- [ ] Notificação ao solicitante quando status muda (polling 5min)
- [ ] Exportar histórico de OS de um ativo (PDF)

### Serviços — Fase 3 da proposta_servicos_executiva.md

- [ ] Dependências avançadas entre OS e caminho crítico
- [ ] Integração plena com Transportes: reserva de veículo/motorista, custo de transporte consolidado na OS
- [ ] Integração com Vegetal: demandas sazonais geram lotes de OS por área; insumos/máquinas como requisitos padrão
- [ ] Integração com Predial: inspeções/laudos geram OS corretivas/preventivas com prioridade por criticidade
- [ ] Governança de custo avançada: custo comprometido, teto de aprovação, nova baseline ao mudar escopo
- [ ] Dashboards de custo e desempenho (custo real × planejado por tipo; desvio médio por módulo; lead time por etapa; reincidência)

### Estoque
- [ ] Marcar materiais como "relevantes para categoria X" — filtra no manifest
- [ ] `POST /api/estoque/{id}/reservar` chamado em OS aberta com material
- [ ] Painel "Necessidades" consolida `qtd_atual < qtd_minima` por seção
- [ ] Aceitar eventos `estoque_mov` vindos do PMOC

### Manutenção (painel)
- [ ] Ao detectar `uso_atual ≥ proximo_uso`, gerar PS rascunho clicável (sem auto-abrir OS)

### Documentos
- [ ] Schema `documentos (id, nome, tipo, vinculo_tipo, vinculo_id, url, sha256, criado_por, ts)`
- [ ] Upload via núcleo (drag & drop) e via push do PMOC (`documento_anexo`)
- [ ] Filtro por ativo / OS / local
- [ ] Versionamento via `substitui_doc_id`

---

## 🟡 P2 — Hub e ergonomia

- [ ] Hub: card por categoria do PMOC com último sync, pendentes, status (verde/amarelo/vermelho)
- [ ] Hub: alerta global de categorias com sync > 24h
- [ ] Login: lembrar último mat. + atalho de Enter
- [ ] Timeout configurável por usuário (1h–24h)
- [ ] Mapa/planta da instalação (Leaflet + tile local) para Locais
- [ ] QR Code por ativo (núcleo gera; PMOC consome via scanner do celular)
- [ ] Dashboard: KPIs reais a partir de `/api/os/kpis`

---

## 🟡 P2 — DevEx e padronização

- [ ] Documento `cmasm.erp/pmoc/CATEGORIAS.md` — guia para adicionar uma nova categoria ao PMOC
- [ ] Lint do ERP: rodar ESLint no `cmasm_erp.html`
- [ ] `docker-compose.yml` orquestrador em `/home/luciano/DEV/` — sobe núcleo + módulos com hardware
- [ ] Garantir 100% offline: substituir referências a `fonts.googleapis.com` por `/assets/fonts.css`

---

## 🟢 P3 — Roadmap longo (REQUISITOS.md §7)

- [ ] Auth com argon2 + refresh token (substituir djb2)
- [ ] PWA do PMOC (manifest + service worker)
- [ ] Upload de fotos no PMOC com `multipart/form-data` (hoje só base64)
- [ ] RFID/QR no Estoque
- [ ] Bridge IoT ESP32 (MQTT → `/api/sync/push`)
- [ ] Telemetria GPS/temperatura na categoria transportes
- [ ] Bridge CADBEM (CSV)
- [ ] BMS (sensores prediais)
- [ ] Indicadores: MTBF, MTTR por ativo

---

## 🧹 Limpeza pós-consolidação (2026-05-22)

- [ ] Arquivar repos legados: `pmoc_refrigeracao`, `pmoc_eletrica`, `pmoc_calibracao`, `pmoc_corte`, `pmoc_transportes` → `.archive_pmoc_legado/` ou `.delete/`
- [ ] Validar que nada do `cmasm.erp` ainda referencia esses repos por path
- [ ] Atualizar `xCMASM.code-workspace` / `cmasm.erp.code-workspace` se houver folders apontando para repos arquivados

---

## 🔧 Dívida técnica

- [ ] `cmasm_erp.html` está em 4281 linhas — dividir em arquivos quando passar para módulos ES (`<script type="module">`) sem build step
- [ ] `Date.now()` como ID em módulos legados — migrar para `crypto.randomUUID()`
- [ ] `clearAllData()` não limpa stores de módulos novos
- [ ] `populateUserSelect()` usa nome como `value` — inconsistente com IDs
- [ ] Remover arquivos órfãos em `referencias/` (duplicatas)

---

## ✅ Concluído recente

- [x] 2026-06-02 — **Transportes / Viagem** (`cmasm_erp.html`): frota continua derivada de `ativos`, agenda migrou para o store `viagens`, formulário ganhou regras de VTR interna/externa, sobreaviso, retorno previsto e autorizador; fluxo validado no navegador com criação, atribuição, início, conclusão, incremento de uso, sumário e Papeleta 6.
- [x] 2026-06-02 — **Serviços — Fase 1** (`cmasm_erp.html`): hierarquia pai/filho, requisitos obrigatórios/opcionais, gate de execução, custo planejado × real, KPI bar, tabs Dados/Requisitos/Custos em `verOS`, badges de bloqueio na tabela e Kanban. Ver `proposta_servicos_executiva.md` para detalhes.
- [x] 2026-06-02 — Usuário `admin`/`admin` adicionado ao SEED_USERS
- [x] 2026-05-22 — **Consolidação arquitetural**: docs atualizadas para "núcleo + PMOC único categorizado". `TEMPLATE_PMOC.md` removido. `MODULOS_EXTERNOS.md` enxugado para módulos *realmente* externos. `Regras de Negocio e Fluxos.md` copiado para o repo do núcleo.
- [x] 2026-05-18 — Reestruturação dos `.md`: `Rules.md`, `MODULOS_EXTERNOS.md`, `TEMPLATE_PMOC.md`, `REQUISITOS.md`, `todo.md`
- [x] 2026-05-17 — Endpoints `POST` e `DELETE /api/pmoc/refrigeracao`
- [x] 2026-05-16 — `GET /api/pmoc/refrigeracao` inclui `zona_nome`
- [x] 2026-05-14 — Bugs e melhorias nos scripts de importação
