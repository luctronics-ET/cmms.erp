# Resumo Executivo de Demonstracao - cmasm.erp

Data da coleta: 31/05/2026  
Ambiente: cmasm.erp rodando local em <http://localhost:8010/cmasm_erp.html>  
Perfil usado na captura: Visitante (somente leitura)

## Objetivo da apresentacao

Este material foi estruturado para demonstrar aos diretores do CMASM:

- a capacidade atual do cmasm.erp como modulo central de gestao;
- o fluxo digital de solicitacao e execucao de servicos;
- a integracao entre Ativos, Materiais, Servicos e Transportes no nucleo;
- o papel do CMMS (Manutencao, PMOC e Calibracao);
- o papel dos modulos externos BMS;
- os proximos incrementos planejados para evolucao do sistema.

## Capturas geradas

Todas as imagens foram salvas em docs/demo_screenshots/.

### Tema escuro (base operacional)

- docs/demo_screenshots/01-dashboard.png
- docs/demo_screenshots/02-organizacao-pessoal.png
- docs/demo_screenshots/02-organizacao-cargos.png
- docs/demo_screenshots/02-organizacao-organograma.png
- docs/demo_screenshots/02-servicos.png
- docs/demo_screenshots/02-transportes.png
- docs/demo_screenshots/02-manutencao.png
- docs/demo_screenshots/02-calibracao.png
- docs/demo_screenshots/02-estoque.png
- docs/demo_screenshots/02-vegetal.png
- docs/demo_screenshots/02-predial.png
- docs/demo_screenshots/02-paiois.png

### Modais (fluxos chave)

- docs/demo_screenshots/10-modal-nova-ps.png
- docs/demo_screenshots/14-modal-agendamento-transporte.png
- docs/demo_screenshots/15-modal-cadastro-veiculo.png
- docs/demo_screenshots/16-modal-novo-registro-calibracao.png
- docs/demo_screenshots/17-modal-novo-item-estoque.png

### Tema claro (material para apresentacao)

- docs/demo_screenshots/20-light-dashboard.png
- docs/demo_screenshots/21-light-servicos.png
- docs/demo_screenshots/22-light-modal-nova-ps.png
- docs/demo_screenshots/23-light-modal-gerar-os.png
- docs/demo_screenshots/24-light-manutencao.png
- docs/demo_screenshots/25-light-estoque.png
- docs/demo_screenshots/26-light-modal-novo-item-estoque.png

## Narrativa sugerida para a diretoria

### 1) Visao integrada do comando

- O Dashboard centraliza indicadores de pessoal, servicos, manutencao, frota e calibracao em um unico painel.
- A diretoria consegue avaliar rapidamente carga operacional, pendencias e saude dos modulos.

### 2) Fluxo de servicos ponta a ponta

- O modulo Servicos opera o encadeamento PS -> OS -> SR.
- O modal de Nova PS demonstra a entrada estruturada da demanda.
- O modal de Gerar OS demonstra a transformacao da demanda em execucao com responsavel e prazo.

### 3) Integracao Manutencao + OS + Estoque

- A area de Manutencao consolida o CMMS do ambiente, incluindo PMOC e Calibracao.
- As OS de manutencao conectam planejamento/executado com consumo de recursos.
- O modulo Estoque registra entradas, saidas e itens; isso suporta a rastreabilidade de materiais usados nas OS.
- Resultado esperado na operacao: menos ruptura de insumos, melhor previsao de necessidade e maior governanca da execucao.

### 4) Fronteira entre nucleo e BMS

- cmasm.erp: modulo central de gestao de ativos, materiais, servicos e transportes.
- CMMS no nucleo: manutencao, PMOC e calibracao.
- Modulos externos BMS: aguada, paiois, eletrica, seguranca, cftv e grama.

## Funcionalidades atuais por pagina

### Dashboard

- KPIs operacionais com leitura rapida para decisao.
- Acoes rapidas para abrir fluxos criticos do dia a dia.
- Cartoes de status dos modulos internos e dos modulos externos BMS.

### Organizacao (Pessoal, Cargos, Organograma)

- Cadastro e consulta de pessoal TMFT.
- Estrutura de cargos com manutencao de ocupantes.
- Organograma navegavel para visao hierarquica institucional.

### Servicos (PS/OS/SR)

- Gestao completa de pedidos e ordens de servico.
- Filtros e busca por status para acompanhamento de carteira.
- Visualizacoes de operacao incluindo aba Kanban.

### Transportes

- Controle de frota (viaturas, embarcacoes e maquinas de peso).
- Agendamento de deslocamentos por modal.
- Cadastro e atualizacao de veiculos/embarcacoes.

### Manutencao

- Area CMMS do nucleo com renderizacao dinamica para evolucao modular.
- Inclui a linha de evolucao de PMOC e calibracao como parte da manutencao.
- Base para integracao de ativos, planos e execucao de OS.

### Calibracao

- Monitoramento por status de vencimento e conformidade metrologica.
- Registro de novos eventos de calibracao via modal.
- Funcao posicionada no dominio de manutencao (CMMS), nao como modulo externo.

### Estoque

- Controle de itens, movimentacoes e saldos.
- Cadastro de item e operacoes de entrada/saida.
- Suporte ao vinculo de materiais com ordens de servico.

### Controle Vegetal, Locais & Predial, Paiois

- Cobertura de operacoes setoriais com abertura de ocorrencias, reservas e movimentacoes.
- Interface padronizada com os demais modulos do nucleo.

## Implementacoes futuras (roadmap para diretoria)

### Prioridade imediata (P0)

- Tela de manutencao categorizada no nucleo com ativos por categoria e status visual do proximo servico.
- API de catalogo de servicos, planos e qualificacoes com versionamento.
- Fechamento do sync com delta por since e autenticacao bearer em todos os endpoints de sync.

### Evolucao curta (P1)

- Expansao das categorias do PMOC unico: predial, paiois, transportes, grama, eletrica e calibracao.
- Melhorias em Servicos/Estoque para reserva automatica, necessidades consolidadas e eventos de estoque vindos do PMOC.

### Evolucao de usabilidade e gestao (P2)

- Hub de categorias com saude de sincronizacao e alertas globais.
- Login com melhor ergonomia, timeout configuravel e dashboard de KPIs reais via API.

### Evolucao estrategica (P3)

- Fortalecimento de seguranca de autenticacao (argon2 + refresh token).
- PWA do PMOC, upload de fotos, integracoes IoT e indicadores avancados (MTBF/MTTR).

## Observacoes da sessao

- Modulos externos BMS (aguada, paiois, eletrica, seguranca, cftv e grama) podem aparecer offline quando nao inicializados na sessao.
- O nucleo foi demonstrado com sucesso em navegacao completa e abertura de modais em tema escuro e tema claro.
