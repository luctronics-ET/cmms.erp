# Proposta de Evolucao do Modulo de Servicos (CMASM ERP)

Data: 2026-06-02
Escopo: modelo funcional e tecnico para Servicos, OS e Tarefas, com custos e integracoes entre modulos.

## 1. Objetivo

Evoluir o modulo de Servicos para:
- suportar servicos pai e filhos;
- controlar requisitos obrigatorios/opcionais (materiais, outros servicos, ativos, documentos, veiculos);
- adotar classificacao multipla (interna + CATSER/CATMAT + SINAPI quando aplicavel);
- operar com custos planejados, comprometidos e realizados;
- integrar nativamente com Transportes, Manutencao, Vegetal, Predial e Estoque;
- manter rastreabilidade tecnica e financeira por OS.

## 2. Principios de Projeto

- Catalogo versionado: toda OS referencia uma versao congelada do servico.
- Separacao de classificacao por finalidade: operacional, contratacao e engenharia/custos.
- Workflow com gates: execucao somente com requisitos obrigatorios atendidos.
- Integracao por eventos de dominio: geracao automatica de servicos por modulo de origem.
- Auditoria completa: historico de transicoes, custos, consumo, evidencias e aprovacoes.

## 3. Modelo Funcional

### 3.1 Servicos pai e filhos

- Servico pai: macroprocesso ou pacote de entrega.
- Servico filho: atividade executavel, monitoravel e potencialmente convertida em OS.
- Dependencias entre filhos:
  - finish_to_start;
  - start_to_start;
  - bloqueio por requisito.

Regras:
- nao permitir ciclo de dependencia;
- filho obrigatoriamente vinculado ao pai quando tipo_hierarquia = obrigatoria;
- concluido do pai depende da conclusao dos filhos obrigatorios.

### 3.2 Requisitos do servico

Tipos de requisito:
- material (estoque);
- ativo/equipamento;
- veiculo/transporte;
- outro servico (predecessor);
- documento/instrucao;
- requisito livre (qualificacao, permissao, autorizacao etc.).

Cada requisito deve ter:
- obrigatoriedade (obrigatorio/opcional);
- status (pendente, atendido, dispensado_com_justificativa);
- validade (quando aplicavel);
- comprovacao (evidencia ou referencia).

Gate minimo:
- OS nao pode entrar em execucao com requisito obrigatorio pendente.

## 4. Custos

### 4.1 Componentes de custo

- mao de obra (horas previstas e reais por perfil);
- materiais (previsto x consumido x devolvido);
- ativos/equipamentos (hora/km/ciclo de uso);
- transportes (veiculo, motorista, combustivel, pedagio, diaria);
- terceiros (servico externo/locacao);
- indiretos (overhead);
- contingencia.

### 4.2 Indicadores por OS e por servico

- custo_planejado;
- custo_comprometido;
- custo_real;
- variacao_abs;
- variacao_pct;
- baseline_custo (versao).

Regras:
- conclusao exige fechamento tecnico e financeiro minimo;
- estouro de teto de aprovacao dispara aprovacao adicional;
- mudanca de escopo apos inicio gera nova baseline.

## 5. Classificacao

Adotar classificacao multipla por servico:
- interna_cmasm: navegacao e operacao;
- catser_catmat: aderencia administrativa;
- sinapi: referencia de composicoes/custos de engenharia (quando aplicavel).

Estrutura recomendada por classificacao:
- sistema_classificacao;
- codigo;
- descricao;
- vigencia_inicio;
- vigencia_fim;
- fonte.

## 6. Integracoes com modulos CMASM

### 6.1 Transportes

- Servico pode exigir reserva de veiculo como requisito.
- Criar solicitacao de transporte vinculada a OS.
- Consolidar custo de transporte no custo_real da OS.

### 6.2 Manutencao

- Planos preventivos/corretivos geram servicos periodicos.
- Gatilhos por tempo, uso, horimetro e odometro.
- Herdar checklist, requisitos e custo padrao da versao do servico.

### 6.3 Vegetal

- Demandas sazonais (poda, rocada, adubacao) geram lotes de servicos.
- Integracao com calendario operacional e areas.
- Maquinas e insumos entram como requisitos padrao.

### 6.4 Predial

- Inspecoes e laudos geram servicos corretivos/preventivos.
- Criticidade da nao conformidade define prioridade e SLA.
- Pode exigir anexos tecnicos obrigatorios para liberar execucao.

### 6.5 Estoque

- Servico declara materiais obrigatorios/opcionais e equivalentes.
- Fluxo recomendado: reservado -> separado -> consumido/devolvido.
- Falta de item obrigatorio bloqueia transicao para execucao.

## 7. Documentacao e instrucoes

Cada versao de servico deve suportar anexos e textos estruturados:
- instrucao de trabalho;
- POP/procedimento;
- checklist tecnico;
- requisitos de seguranca;
- criterio de aceite;
- evidencias obrigatorias de encerramento.

Controles:
- versao e vigencia;
- aprovador e data de aprovacao;
- leitura/aceite por executor (quando exigido).

## 8. Workflow sugerido para OS

Fluxo:
- aberta;
- planejada;
- aguardando_requisitos;
- liberada_execucao;
- em_execucao;
- aguardando_validacao;
- concluida;
- cancelada.

Gates:
- gate 1: requisitos obrigatorios atendidos;
- gate 2: checklist tecnico concluido;
- gate 3: evidencias minimas anexadas;
- gate 4: fechamento financeiro minimo.

## 9. Modelo de dados (alto nivel)

Entidades principais:
- services;
- service_versions;
- service_relations;
- service_requirements;
- service_requirement_materials;
- service_requirement_services;
- service_classifications;
- service_documents;
- work_orders;
- work_order_tasks;
- work_order_requirement_status;
- work_order_costs;
- work_order_evidences;
- integration_events.

## 10. Eventos de integracao (contrato)

Eventos de entrada:
- manutencao.plano_disparado;
- predial.laudo_gerado;
- vegetal.demanda_sazonal;
- transportes.reserva_confirmada;
- estoque.item_indisponivel.

Eventos de saida:
- servico.gerado;
- os.criada;
- os.bloqueada_por_requisito;
- os.concluida;
- custo.fechado.

## 11. KPIs recomendados

- custo_real x custo_planejado por tipo de servico;
- desvio medio de custo por modulo de origem;
- taxa de bloqueio por falta de requisito;
- lead time por etapa do workflow;
- reincidencia (reabertura em 30/60/90 dias);
- consumo de materiais por categoria de servico.

## 12. Roadmap de implementacao

Fase 1 (curta)
- hierarquia pai/filhos;
- requisitos obrigatorio/opcional;
- gate de execucao;
- custo basico (planejado x real).

Fase 2 (media)
- classificacao multipla;
- catalogo versionado;
- documentos/instrucoes versionadas;
- integracao inicial com estoque e manutencao.

Fase 3 (avancada)
- dependencias avancadas e caminho critico;
- integracao plena com transportes, vegetal e predial;
- dashboards de custo e desempenho.

## 13. Riscos e mitigacoes

Riscos:
- excesso de complexidade inicial;
- baixa qualidade de dados de catalogo;
- resistencia operacional na adocao de gates.

Mitigacoes:
- rollout incremental por fase;
- validacao com usuarios-chave por modulo;
- templates padrao de servico por area;
- treinamento rapido e indicadores de adesao.

## 14. Criterios de sucesso

- reducao do retrabalho e de OS incompleta;
- melhoria da previsibilidade de custo e prazo;
- aumento de conformidade documental;
- rastreabilidade fim a fim (origem -> execucao -> custo -> evidencia).
