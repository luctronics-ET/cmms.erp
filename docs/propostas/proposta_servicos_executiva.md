# Proposta de Servicos - Visao Executiva (CMASM ERP)

Data: 2026-06-02
Origem: consolidacao da proposta funcional para evolucao do modulo de Servicos.

---

## Status de implementacao

| Fase | Status | Data |
| --- | --- | --- |
| Fase 1 — hierarquia, requisitos, custo basico | ✅ Completa | 2026-06-02 |
| Fase 2 — classificacao multipla, catalogo, integracao estoque/manutencao | ⏳ Pendente | — |
| Fase 3 — caminho critico, integracao plena, dashboards | ⏳ Pendente | — |

**Implementado na Fase 1 (cmasm_erp.html):**

- Modelo de dados OS estendido: `osPai`, `osFilhos`, `requisitos`, `custoPlanejado`, `custoReal`, `origem`
- Gate de execucao: avanco para `em_andamento` bloqueado se requisito obrigatorio nao atendido
- Formulario Nova OS com campos custo planejado, OS pai e secao de requisitos
- Modal `verOS` com 3 abas: Dados / Requisitos / Custos
- KPI bar no topo do modulo: abertas, em andamento, bloqueadas, custo planejado, desvio
- Tabela OS com coluna Custo e badge de bloqueio (🔴) e hierarquia (↳ / ⊕n)
- Kanban com badge de bloqueio e custo no card
- Funcoes: `salvarRequisito`, `atenderRequisito`, `removerRequisito`, `lancarCustoReal`, `renderKpiServicos`
- Usuario padrao `admin`/`admin` adicionado ao SEED_USERS

---

## 1. Resumo executivo

Objetivo: transformar o modulo de Servicos em uma plataforma integrada de planejamento, execucao e controle de custos, conectada aos modulos Transportes, Manutencao, Vegetal, Predial e Estoque.

Resultados esperados:
- maior previsibilidade de prazo e custo;
- menos OS incompleta por falta de requisito;
- rastreabilidade tecnica e financeira ponta a ponta;
- padronizacao operacional com catalogo e instrucoes versionadas.

## 2. O que muda no negocio

- Servicos passam a ter estrutura pai e filhos.
- Cada servico pode ter requisitos obrigatorios e opcionais.
- OS so avanca quando requisitos criticos forem atendidos.
- Custos passam a ser controlados em 3 niveis: planejado, comprometido e real.
- Classificacao multipla: interna CMASM + CATSER/CATMAT + SINAPI (quando aplicavel).

## 3. Integracao com modulos do CMASM ERP

### 3.1 Transportes
- Servico pode exigir veiculo e motorista.
- Reserva de transporte vinculada a OS.
- Custo de transporte consolidado no custo real da OS.

### 3.2 Manutencao
- Planos preventivos/corretivos geram servicos periodicos automaticamente.
- Gatilhos por tempo, uso, horimetro e odometro.

### 3.3 Vegetal
- Demandas sazonais geram lotes de servicos por area.
- Insumos e maquinas entram como requisitos padrao.

### 3.4 Predial
- Inspecoes e laudos geram servicos corretivos/preventivos.
- Criticidade define prioridade e SLA.

### 3.5 Estoque
- Servicos consomem materiais e ativos com fluxo reservado -> separado -> consumido/devolvido.
- Falta de item obrigatorio bloqueia execucao.

## 4. Governanca de custo

Componentes principais:
- mao de obra;
- materiais;
- uso de ativos/equipamentos;
- transporte;
- terceiros;
- indiretos;
- contingencia.

Regras de governanca:
- conclusao exige fechamento tecnico e financeiro minimo;
- estouro de teto de aprovacao exige aprovacao adicional;
- mudanca de escopo apos inicio gera nova baseline de custo.

## 5. Riscos e mitigacoes

Riscos:
- complexidade inicial;
- baixa qualidade de cadastro;
- resistencia operacional aos gates.

Mitigacoes:
- implantacao por fases;
- templates padrao por area;
- treinamento focado;
- acompanhamento por indicadores.

## 6. Roadmap recomendado

Fase 1 (rapida)
- hierarquia pai/filhos;
- requisitos obrigatorio/opcional;
- gate de execucao;
- custo basico (planejado x real).

Fase 2 (intermediaria)
- classificacao multipla;
- catalogo versionado;
- documentos e instrucoes versionados;
- integracao inicial com estoque e manutencao.

Fase 3 (avancada)
- dependencias avancadas e caminho critico;
- integracao plena com transportes, vegetal e predial;
- dashboards de custo e desempenho.

## 7. KPIs de acompanhamento

- custo real x custo planejado por tipo de servico;
- desvio medio de custo por modulo de origem;
- taxa de bloqueio por falta de requisito;
- lead time por etapa do workflow;
- reincidencia de servicos reabertos;
- consumo de materiais por categoria.

## 8. Criterios de sucesso

- reducao de retrabalho;
- aumento da conformidade documental;
- melhoria da previsibilidade operacional;
- rastreabilidade completa da demanda ate o encerramento financeiro.
