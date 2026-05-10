# xCMASM · TODO / Backlog / Planos Futuros

> Status: 9 de Maio de 2026 · versão 5.4

---

## 🏗️ ARQUITETURA — Módulos Externos (containers independentes)

> Módulos externos têm repo, banco e Docker próprios. Conectam-se ao ERP via `XCORE_URL`.

### Integração ERP ↔ Módulos Externos
- [ ] Navbar ERP: botões "Módulos Externos" apontando para URLs configuráveis de cada módulo
- [ ] Página dashboard-resumo por módulo externo (iframe ou card com métricas chave via API)
- [ ] `GET /api/modulos` — endpoint xCore para listar módulos externos registrados + status (health check)
- [ ] Padronizar autenticação: módulos recebem Bearer token do operador para chamar `/api/usuarios`

### xPredial (porta 8002)
- [ ] Confirmar integração `GET /api/usuarios` com token do ERP
- [ ] Botão "→ OS" no ERP abre xPredial pré-filtrado por local

### aguada-web (porta 8001)
- [ ] Endpoint de push: aguada-web → xCore `/api/ativos/{id}` com leituras horárias

### xSeguranca (porta 8000/3000)
- [ ] Futura: importar lista de usuários do ERP via `GET /api/usuarios`

---

## 🔴 PRIORIDADE ALTA — Funcionalidades incompletas em módulos existentes

### Auth & Sessão
- [x] Timeout de sessão por inatividade (8h) — timer de inatividade JS, aviso 15min antes, auto-logout ✅
- [x] Log de acesso: registrar login/logout com timestamp — _appendAccessLog() + renderAccessLog() na aba Admin ✅
- [x] Perfil de acesso por seção: gestor só autoriza PS da sua lotação — canAutorizarPS() filtra por lotação do solicitante ✅

### Serviços (PS → OS → SR)
- [x] **SR (Solicitação de Recursos)** — workflow PS→OS→SR completo ✅
  - SR de material → baixa automática no Estoque + mov_estoque
  - SR de transporte → cria agendamento pendente em Transportes
  - SR de local → cria reserva confirmada em Predial
  - SR de serviço externo → registra fornecedor/NF (status pendente até NF vinculada)
- [x] Histórico de alterações em cada PS/OS — renderSrvHistorico() no modal de detalhe, mostra status_de→status_para + obs + timestamp ✅
- [x] Cancelamento OS com motivo obrigatório — modal modal-cancel-os com textarea + confirmCancelOs() ✅
- [x] Notificação visual quando uma PS do usuário logado muda de status — pollOsUpdates() compara snapshots a cada 5min, notifica via toast ✅
- [x] Prazo em OS: alerta visual quando está vencendo (< 2 dias) — badge VENCIDA/VENCENDO na lista, kanban e hist. dashboard ✅

### Locais & Predial
- [x] Modal `+ Local` para cadastrar/editar locais — modal-local-new com openLocalModal()/saveLocal() ✅
- [x] Modal `+ Edificação` — botão 🏢 no header de Locais abre modal-local-new com tipo=edificio ✅
- [x] Editar local: click na linha ou botão ✂ abre modal para edição ✅
- [ ] Mapa/planta baixa simplificada da instalação (SVG interativo)
- [ ] Controle de chaves: quem está com qual chave de qual sala
- [x] Integração com Serviços: ocorrência predial pode gerar OS automaticamente — botão "→ OS" em `renderOcorrencias()`, `gerarOSdeOcorrencia()` cria PS autorizada + OS aberta ✅
- [ ] Salas com controle de acesso, temperatura/umidade, alimentacao Eletrica initerrupta
- [ ] reserva de salas de reuniao, auditorio, refeitorio

### Materiais e Estoque
- [x] Modal completo de `+ Item` (modal-estoque) — todos os campos: nome, código, categoria, unidade, qtd, local, obs ✅
- [x] Modal de `+ Entrada` e `− Saída` com campos: documento, fornecedor/requisitante, obs ✅
- [x] Histórico de movimentações no modal de edição do item (últimas 50, com tipo/qty/fornecedor/data) ✅
- [x] Relatório de consumo por período — filtro De/Até + tipo + exportação CSV em `exportarConsumoCSV()` ✅
- [x] Requisição de material linkada a OS de Serviços (SR → Estoque) — coberta pela SR de material ✅
- [x] Controle de validade para itens perecíveis — campo `validade` no modal de item, aba "Validades" com semáforo 30/90 dias, `renderEstoqueValidades()` ✅
- [x] Alertas de reposição automáticos no dashboard — painel Estoque Baixo no srv-dashboard ✅

### Transportes 
- [x] Modal de detalhes do agendamento confirmado — openAgendaDetalhe() mostra veículo, tripulação, destino, km, obs ✅
- [ ] Permissoes de uso, habilitacoes, 
- [x] Histórico de viagens por veículo — aba agenda-dp no detalhe do veículo + seção "Histórico recente" na agenda (inclui concluídas) ✅
- [x] Exportação de escala de transportes (CSV) — botão "↓ CSV" na aba Agendamentos, `exportarEscalaCSV()` ✅
- [x] Controle de kilometragem: atualizar km ao concluir agendamento — modal-concluirViagem + confirmarConclusaoViagem() atualiza vehicle.km ✅
- [x] Integração com Manutenção: bloqueio automático de veículo com OS aberta — já existia via `criarOSManut()`; agendamento confirmado seta status `OR`, conclusão restaura para `P` ✅
- [ ] mock para reastreamento via GPS e telemetria condicao 

### Controle Vegetal
- [x] Modal `+ Maquinário` — modal-nova-maq + salvarMaquina() em xgrama.html ✅
- [x] Modal `+ Atividade` com seleção de maquinário e operador — modal-nova-op em xgrama.html ✅
- [x] Área cadastrada com frequência de corte — modal-nova-area + salvarArea() em xgrama.html ✅
- [x] Integração com horímetro: atualizar ao registrar atividade — xgrama.html registra horas de uso ✅
- [x] Programação de cortes por área (calendário) — página calendario em xgrama.html ✅



### Paiois
- [x] Modal `+ Paiol` (modal-paiol) — salvarPaiol(), editarPaiol(), detalhe do paiol em paiol-inventario.html ✅
- [x] Modal `+ Item de Inventário` — campos lote, validade, qtd, qtdMin, categoria, unidade em paiol-inventario.html ✅
- [x] Controle de acesso: log de entrada/saída — aba Log de Acesso + modal Registrar Acesso em paiol-inventario.html ✅
- [x] Alerta de validade: aba Validades com semáforo 30/90/180d + banner de alerta no topo ✅
- [x] Relatório de inventário: exportação CSV de todos os itens em paiol-inventario.html ✅
- [x] Integração com OS de Serviços: saída de material por OS — modal `modal-mov-paiol` com select de OS vinculada, `salvarMovPaiol()` ✅

---

## 🟡 PRIORIDADE MÉDIA — Módulos planejados mas não iniciados

### Calibração (módulo existente — melhorias)
- [ ] Importação CSV de instrumentos
- [ ] Gerar documento de programação de calibração (lista mensal)
- [ ] Histórico completo por instrumento (todos os certificados anteriores)
- [ ] Alerta de vencimento no dashboard por módulo (GAMI, GAS, GM separados)

### Manutenção (módulo existente — melhorias)
- [ ] Plano preventivo completo: frequência por tipo de equipamento configurável
- [ ] Peças de reposição: link com Estoque (ao criar OS, reservar peças)
- [ ] Checklist de inspeção por ativo
- [ ] QR Code por ativo para abertura rápida de OS via celular
- [ ] Exportar histórico de manutenção de um ativo (PDF)

### Serviço de Estado
- [ ] Escala de serviço: plantões (OSD, OID, Quarto de Serviço)
- [ ] Motorista de Serviço: escala mensal com visualização
- [ ] Lançador de ilha: roteiro fixo de horários (saída 07:00, 12:00, 17:30)
- [ ] Oficial de Serviço do Dia: designação diária com roteiro e passagem de serviço
- [ ] Livro de Quarto digital: registro de ocorrências do plantão
- [ ] Integração com organograma: só militares CMASM podem ser escalados

### Recursos Humanos / Pessoal
- [ ] Férias e licenças: controle de períodos por militar
- [ ] Cursos e qualificações: registro por pessoa com validade
- [ ] Avaliações de desempenho: TAF, ficha de conceito
- [ ] Organograma com fotos (upload de foto por usuário)
- [ ] Quadro de pessoal presente/ausente do dia

### Contratos e Licitações (CMASM-30)
- [ ] Registro de contratos ativos: fornecedor, objeto, vigência, valor
- [ ] Alerta de vencimento de contratos
- [ ] Integração com Estoque (NFs vinculadas a contratos)
- [ ] DFD, ETP, Termo de Referência — formulários padronizados
- [ ] Pesquisa de preços PNCP (integração API externa — requer conexão)

### Comunicação Interna
- [ ] Avisos e comunicados: admin publica, todos visualizam no dashboard
- [ ] Mensagens diretas entre usuários (BroadcastChannel ou localStorage polling)
- [ ] Boletim Interno digital: criação e publicação de BIs

---

## 🟢 PRIORIDADE BAIXA — Roadmap futuro

### IoT / Telemetria ESP32
- [ ] Bridge Python/Raspberry Pi ↔ ESP32 via MQTT (Mosquitto)
- [ ] Endpoint local REST: `POST /telemetria` recebe JSON do bridge
- [ ] Dados por veículo/embarcação: GPS (lat/lon), temperatura motor, vibração
- [ ] Mapa de posicionamento em tempo real (Leaflet.js + tile local)
- [ ] Histórico de rotas por veículo
- [ ] RFID: registro automático de saída/retorno do cais/garagem
- [ ] Alertas de temperatura: motor acima de 95°C → notificação em Transportes

### BMS (Building Management System)
- [ ] Sensores de temperatura por ambiente (ESP32 + DHT22)
- [ ] Consumo elétrico por edificação (via medidor com saída RS-485)
- [ ] Nível de cisternas e reservatórios
- [ ] Dashboard predial em tempo real com mapa da instalação
- [ ] Histórico de consumo de água/energia com gráficos mensais

### Migração para Stack Laravel + Docker
- [ ] PRD já gerado (sessão anterior — disponível em project files)
- [ ] Docker Compose com: app, nginx, postgres, redis, websockets, mqtt
- [ ] Laravel 10+ / PHP 8.2 backend
- [ ] Vue.js 3 + CoreUI Free Edition frontend
- [ ] Migração dos dados do localStorage para PostgreSQL 15
- [ ] Auth com JWT + refresh tokens
- [ ] WebSockets para notificações em tempo real (substituir polling)
- [ ] API REST documentada com OpenAPI/Swagger
- [ ] RBAC completo por módulo e operação

### Mobile
- [ ] PWA: manifest.json + service worker para uso offline
- [ ] Interface responsiva para tablets (patrulha, depósito, cais)
- [ ] QR Code scanner via câmera do celular (ativos, paiois)

### Relatórios e BI
- [ ] Relatório mensal de OS por departamento (exportar PDF)
- [ ] Indicadores de manutenção: MTBF, MTTR por ativo
- [ ] Consumo de estoque por período e por seção
- [ ] Painel gerencial: KPIs consolidados para Direção

---

## 🔧 DÍVIDA TÉCNICA

- [ ] `editCargo()` / `salvarCargo()` — modal existe mas função edit não preenche select de ocupante corretamente
- [ ] `populateUserSelect()` usa nome como `value` em vez de `id` — inconsistente com o resto
- [x] `renderAdminDB()` agora busca counts reais da API (usuarios, ativos, locais, OS, estoque) ✅
- [ ] `exportBackup()` / `importBackup()` não incluem módulos novos
- [ ] `clearAllData()` não limpa chaves dos módulos novos
- [ ] Dashboard: cards de módulo não refletem status de estoque/paiois
- [ ] IDs em módulos novos usam `Date.now()` — possível colisão em loop
- [ ] `fmtDateSimple()` não trata datas no formato `ISO completo` corretamente

---

## ✅ CONCLUÍDO (histórico)

### Sessão 9 Mai 2026 (tarde)
- [x] SR (Solicitação de Recursos) implementada: tab SR em Serviços, modal com 4 tipos (material/transporte/local/externo), integração com Estoque/Transportes/Predial ✅
- [x] Perfil de acesso por seção: `canAutorizarPS()` — gestor só autoriza PS da sua lotação; guards em `autorizarPS()` e `rejeitarPS()` ✅
- [x] Predial → Serviços: `gerarOSdeOcorrencia()` — botão "→ OS" em cada ocorrência aberta ✅
- [x] Estoque: filtro de período + exportação CSV de movimentações (`exportarConsumoCSV`) ✅
- [x] Estoque: modal de criação/edição de itens com campo `validade`; aba "Validades" com semáforo ✅
- [x] Paiois: modal `modal-mov-paiol` com select de OS vinculada (`salvarMovPaiol`) ✅
- [x] Transportes: exportação CSV da escala (`exportarEscalaCSV`) ✅
- [x] Transportes: veículo marcado `OR` ao confirmar agendamento, restaurado para `P` ao concluir ✅

### Sessão 9 Mai 2026
- [x] Rules.md reestruturado: diagrama limpo, categorias snake_case, tipos OS completos, máquina de estados PS/OS (8 status), seção PS/NECs, funcionalidades Transportes, modelo distribuído de Estoque + CADBEM
- [x] Modal de movimentação de estoque (↕) — entrada / saída / ajuste com campos documento, fornecedor e obs
- [x] Migração aditiva `estoque_movimentos`: colunas `documento` e `fornecedor` via `ALTER TABLE`
- [x] `MovimentoIn` atualizado + INSERT com novos campos
- [x] Botão ↕ na tabela de estoque (ao lado de ✎), funções `openMovimentoModal` + `saveMovimento`
- [x] 12/12 vínculos locais→cargos→usuários (estrutura_id aditivo + JOIN COALESCE)
- [x] 8 locais físicos inseridos (IDs 301-308), 27 ativos.loc corrigidos → contadores reais na tabela Locais
- [x] `xCMASM/frontend/servicos/index.html` → redirect para `cmasm-erp.html?page=srv-dashboard`

- [x] Single-file HTML unificado (todos os módulos separados → xcmasm.html)
- [x] Login com identificação parcial (nome/NIP/lotação/e-mail, case-insensitive)
- [x] Acesso visitante (somente leitura, sem senha)
- [x] TMFT com seed data real (15 pessoas)
- [x] Cargos com CRUD e ocupante linkado
- [x] Organograma colapsável (Regimento Interno Nov/2024, 29 nós)
- [x] Fluxo PS → OS (criação, autorização, rejeição, execução, conclusão)
- [x] Kanban de OS por status
- [x] Transportes: frota (viatura/embarcação/máquina), agendamento 2 fases
- [x] Serviço do Dia: Motorista do Diretor + MS com histórico
- [x] Manutenção CMMS: ativos, OS corretiva/preventiva, horímetro
- [x] Calibração: instrumentos, KPIs, alertas de vencimento
- [x] Dashboard com KPIs globais, badge de alertas, relógio
- [x] Lazy rendering (boot rápido — apenas dashboard na inicialização)
- [x] Tema dark/light com persistência
- [x] Backup/restore JSON
- [x] Guard de visitante em todas as funções de escrita
- [x] Módulo Estoque (estrutura + seed + CRUD básico)
- [x] Módulo Controle Vegetal (maquinário + atividades + OS)
- [x] Módulo Locais & Predial (edificações + reservas + ocorrências)
- [x] Módulo Paiois (inventário + movimentações + alertas de validade)

---

*Atualizado em: 9 de Maio de 2026 (noite — sessão 3)*
