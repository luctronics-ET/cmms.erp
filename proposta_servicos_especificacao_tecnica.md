porta# Proposta de Servicos - Especificacao Tecnica (CMASM ERP)

Data: 2026-06-02
Escopo: modelo funcional, dados, eventos, workflow e regras para implementacao.

## 1. Modelo funcional

### 1.1 Hierarquia de servicos

- Servico pai: macroprocesso.
- Servico filho: atividade executavel e rastreavel.
- Dependencias permitidas:
  - finish_to_start;
  - start_to_start;
  - bloqueio por requisito.

Regras:
- bloquear dependencia ciclica;
- pai so conclui com filhos obrigatorios concluidos;
- filho pode gerar OS propria quando configurado.

### 1.2 Requisitos por servico

Tipos:
- material;
- ativo/equipamento;
- veiculo/transporte;
- outro servico;
- documento/instrucao;
- requisito livre.

Atributos minimos:
- obrigatorio (bool);
- status (pendente, atendido, dispensado_com_justificativa);
- validade_inicio/validade_fim;
- evidencia_ref.

Gate:
- transicao para em_execucao exige todos requisitos obrigatorios atendidos.

## 2. Custos

### 2.1 Estrutura de custo

- mao_obra_prevista, mao_obra_real;
- material_previsto, material_consumido, material_devolvido;
- ativo_uso_hora_km_ciclo;
- transporte;
- terceiros;
- indiretos;
- contingencia.

### 2.2 Metricas por OS

- custo_planejado;
- custo_comprometido;
- custo_real;
- variacao_abs;
- variacao_pct;
- baseline_custo_id.

Regras:
- fechamento tecnico + financeiro obrigatorio para conclusao;
- threshold de aprovacao para sobrecusto;
- rebaseline obrigatorio em mudanca de escopo apos inicio.

## 3. Classificacao multipla

Sistemas de classificacao por servico:
- interna_cmasm;
- catser_catmat;
- sinapi.

Campos:
- sistema_classificacao;
- codigo;
- descricao;
- vigencia_inicio;
- vigencia_fim;
- fonte;
- ativo (bool).

## 4. Documentacao e instrucoes

Tipos de documento:
- instrucao_trabalho;
- pop_procedimento;
- checklist_tecnico;
- seguranca;
- criterio_aceite;
- evidencia_encerramento.

Controles:
- versao;
- vigencia;
- aprovador;
- data_aprovacao;
- leitura_aceite_obrigatorio.

## 5. Workflow de OS

Estados:
- aberta;
- planejada;
- aguardando_requisitos;
- liberada_execucao;
- em_execucao;
- aguardando_validacao;
- concluida;
- cancelada.

Validacoes por gate:
- gate_1_requisitos;
- gate_2_checklist;
- gate_3_evidencias;
- gate_4_fechamento_financeiro.

## 6. Integracao entre modulos

### 6.1 Entradas (eventos de origem)
- manutencao.plano_disparado;
- predial.laudo_gerado;
- vegetal.demanda_sazonal;
- transportes.reserva_confirmada;
- estoque.item_indisponivel.

### 6.2 Saidas (eventos de servicos)
- servico.gerado;
- os.criada;
- os.bloqueada_por_requisito;
- os.concluida;
- custo.fechado.

## 7. Modelo de dados (alto nivel)

Entidades:
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

## 8. Regras de consistencia

- impedir ciclo em service_relations;
- impedir uso de classificacao expirada em novos cadastros;
- impedir conclusao de OS sem evidencias minimas;
- impedir consumo de material sem reserva/separacao quando item for obrigatorio;
- registrar trilha de auditoria em toda transicao de estado.

## 9. KPIs tecnicos

- desvio de custo por versao de servico;
- taxa de bloqueio por requisito;
- tempo medio por estado do workflow;
- percentual de OS com evidencias completas;
- taxa de reabertura em 30/60/90 dias.

## 10. Ordem de implementacao tecnica

Sprint 1
- tabelas base de servicos, versoes, requisitos, workflow;
- validacao de gate_1 (requisitos) e gate_2 (checklist).

Sprint 2
- custos (planejado/comprometido/real) e baseline;
- classificacao multipla;
- documentos versionados.

Sprint 3
- eventos de integracao com modulos origem;
- dashboards de custo/desempenho;
- regras avancadas de dependencia e caminho critico.
