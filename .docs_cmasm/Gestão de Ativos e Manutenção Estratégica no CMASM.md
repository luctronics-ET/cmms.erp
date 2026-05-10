# **Gestão de Ativos e Manutenção Estratégica no CMASM**

Este estudo de aplicação para o **CMASM** visa otimizar a gestão administrativa e operacional, garantindo a prontidão e confiabilidade dos sistemas críticos 

## **1\. Visão Geral dos Sistemas (ERP, CMMS e EAM) no CMASM**

Para uma organização complexa como o CMASM, a integração dessas três ferramentas é essencial:

* **ERP (Enterprise Resource Planning):** Funcionaria como o "cérebro" administrativo, gerenciando o **orçamento, recursos humanos, compras de suprimentos** (combustível para geradores, peças para viaturas) e a logística de transporte para a ilha.  
* **CMMS (Computerized Maintenance Management System):** Foca na **execução diária da manutenção**. A ferramenta dos técnicos para gerir Ordens de Serviço (OS):  limpeza de splits, revisão de máquinas de cortar grama, viaturas e embarcações,  lubrificação máquinas e motores, limpeza câmeras, troca de baterias.  
* **EAM (Enterprise Asset Management):** Essencial para o CMASM por gerir o **ciclo de vida completo de ativos de alto valor**, como subestações elétricas, embarcações e guindastes, viaturas e embarcações, refrigeração. 


##  **Aplicação Prática por Sistema de Equipamentos**

### **A. Sistemas de Refrigeração e PMOC**

Com centenas de splits, chillers e câmaras frigoríficas (vitais para a preservação de componentes de armamentos), o CMASM deve obrigatoriamente implementar o **PMOC (Plano de Manutenção, Operação e Controle)** conforme a Lei nº 13.589/2018.

* **Ação:** O software CMMS deve automatizar o calendário do PMOC, gerando alertas para limpezas mensais de filtros e inspeções semestrais de serpentinas. Isso evita a "Síndrome dos Edifícios Doentes" e garante a durabilidade dos chillers.

### **B. Sistemas Elétricos e Hidráulicos (Ativos Críticos)**

A subestação, os geradores e a rede de incêndio são ativos de **baixa tolerância a falhas**.

* **Integração IoT:** Sensores de vibração e temperatura nos geradores e sensores de pressão na rede de incêndio devem ser integrados ao EAM/CMMS.  
* **Manutenção Preditiva:** O sistema deve monitorar o estado real desses ativos, gerando uma OS automática se um gerador apresentar superaquecimento durante um teste, permitindo a intervenção antes de uma queda de energia na ilha.

### **C. Viaturas, Embarcações e Equipamentos de Segurança**

* **EAM para Embarcações:** Gerencia desde a aquisição até o desmantelamento, controlando custos de combustível e histórico de reparos navais.  
* **CFTV e Alarmes:** O CMMS garante que as inspeções de segurança e testes de alarmes sejam realizados e documentados para fins de auditoria militar

## **3\. Metodologia de Implantação Sugerida**

Baseando-se em práticas consolidadas (como a MISTRR), a implantação deve seguir etapas rígidas:

1. **Diagnóstico:** Levantamento de todos os ativos na ilha e seu estado atual.  
2. **Mapeamento de Processos:** Definir como a manutenção de uma embarcação difere da manutenção de um split de escritório.  
3. **Treinamento:** Capacitação dos militares e técnicos civis no uso de dispositivos móveis para registrar OS no campo (na ilha), mesmo em áreas sem Wi-Fi (modo offline).  
4. **Projeto Piloto:** Testar o sistema primeiramente em um setor crítico (ex: Geradores e Refrigeração das Câmaras) antes da expansão total.

## **4\. Benefícios Estratégicos para o CMASM**

* **Confiabilidade e Segurança:** Redução de paradas não planejadas em sistemas de armas e refrigeração, minimizando riscos de acidentes e perdas de estoque estratégico.  
* **Despersonalização das Funções:** O conhecimento sobre a manutenção da subestação deixa de estar "na cabeça" de um único militar e passa para o histórico digital do EAM, facilitando passagens de serviço e substituições de pessoal.  
* **Controle Logístico na Ilha:** O ERP integrado permite prever a necessidade de peças e insumos antes que acabem, considerando o tempo de transporte logístico para a ilha.  
* **Auditoria e Conformidade:** Geração imediata de relatórios para inspeções da Marinha ou órgãos reguladores, com assinaturas digitais e histórico imutável 

## **Integração entre CMMS, ERP e EAS**

A integração de um sistema **CMMS** (Sistema de Gestão de Manutenção Computadorizado) com sistemas **ERP** (Planejamento de Recursos Empresariais) e **EAM** (Gestao de Ativos) é fundamental para gerar e analisar informacao sobre os ativos e garantir que os dados de manutenção fluam por toda a organização.

Abaixo estão detalhadas as formas como essa integração ocorre e seus principais benefícios:

Integração com o ERP (Foco em Gestão e Finanças)

O CMMS conecta-se ao ERP para alinhar as atividades de manutenção aos objetivos financeiros e logísticos da empres.

* **Sincronização de Custos e Orçamentos:** A integração permite que o custo de cada ordem de serviço (peças, mão de obra e serviços externos) seja refletido automaticamente nos dashboards financeiros e de contabilidade do ERP  
* **Gestão de Estoque e Compras:** Quando o CMMS identifica a necessidade de uma peça sobressalente, ele pode disparar solicitações de compra ou atualizar os níveis de inventário diretamente no ERP, evitando a duplicidade de lançamentos manuais  
* **Dados de Recursos Humanos:** Informações sobre a disponibilidade de técnicos, suas habilidades e certificações são compartilhadas entre os sistemas para otimizar as escalas de trabalho.

Gestão de Ativos e Manutenção Industrial

1\. Contextualização Estratégica e Objetivos da Modernização

Processos fundamentados em planilhas manuais e registros físicos não são apenas ineficientes; eles constituem passivos estratégicos caracterizados por alta latência de dados e silos de informação que comprometem a agilidade decisória da alta gestão.

Este relatório fundamenta tecnicamente a substituição de fluxos analógicos por um ecossistema digital integrado, visando à mitigação de riscos jurídicos e à maximização do  *Total Cost of Ownership*  (TCO). A modernização proposta está alicerçada nos seguintes objetivos centrais:

* **Minimização do Downtime Não Planejado:**  Redução drástica de paradas emergenciais que corroem a margem operacional.  
* **Otimização do Ciclo de Vida:**  Prolongamento da vida útil dos ativos e maximização do retorno sobre o investimento (ROI).  
* **Conformidade Normativa e Segurança Jurídica:**  Garantia de integridade de dados para atendimento rigoroso à legislação vigente, transformando a manutenção em um pilar de defesa legal. A viabilidade técnica do projeto inicia-se na correta definição das arquiteturas de sistemas, distinguindo as capacidades operacionais e estratégicas das plataformas CMMS e EAM.

## **2\. Fundamentação Tecnológica: CMMS, EAM e o Papel da IoT**

A escolha da arquitetura tecnológica dita a escalabilidade da operação industrial. É imperativo compreender que a escolha entre CMMS e EAM não é meramente semântica, mas sim uma decisão sobre a profundidade da inteligência de ativos desejada pela organização.

Diferenciação Crítica: CMMS vs. EAM (LCMS)

Enquanto o CMMS funciona como o motor operacional da oficina de manutenção, o EAM — frequentemente referido como  **LCMS (Life Cycle Management System)**  — atua como uma plataforma de gestão global e financeira.

| Funcionalidade | CMMS  operação | EAM estratégia |
| :---- | :---- | :---- |
| **Foco Estratégico** | monitoramento e controle em tempo real.  IoT \+ IA \+ APIs | Gestão global do ciclo de vida, finanças e conformidade. |
| **Escopo de Dados** | Ordens de serviço, histórico técnico e inventário de peças. | inclui CMMS \+ depreciação financeira, compras e CAPEX/OPEX. |
| **Visão do Ativo** | Do recebimento técnico ao descarte operacional. | Do planejamento da aquisição à substituição estratégica. |
| **Impacto** | Redução de custos diretos e aumento da confiabilidade. | Gestão de riscos corporativos e otimização do TCO. |

|

## **3\. Matriz de Estratégias de Manutenção e Aplicação Operacional**

Um mix de manutenção equilibrado é o alicerce da estabilidade produtiva. O ecossistema digital permite a transição para modelos baseados em dados reais:

1. **Manutenção Preventiva:**  Estruturada em calendários e métricas de uso para evitar o desgaste prematuro, garantindo o cumprimento dos planos de fábrica.  
2. **Manutenção Corretiva (Planejada vs. Emergencial):**  Foco na redução da cultura de "apagar incêndios", priorizando a correção programada de anomalias detectadas.  
3. **Manutenção Preditiva e Baseada na Condição:**  Utilização de IoT para monitorar variáveis como vibração e temperatura, intervindo quando a condição real do ativo o exigir.  
4. **Manutenção por Risco e Ciclo de Vida:**  Priorização de intervenções com base na criticidade estratégica do ativo para a planta e na sua fase de depreciação física.

4\. Conformidade Normativa e Gestão de Facilidades (PMOC)

A conformidade com a  **Lei nº 13.589/2018**  não é apenas uma obrigação administrativa, mas um componente crítico da Saúde e Segurança Ocupacional (SSO). A negligência no Plano de Manutenção, Operação e Controle (PMOC) expõe a liderança a sanções civis e criminais.

Componentes Obrigatórios do Plano

O ecossistema digital automatiza o preenchimento dos requisitos legais:

*   **Cadastro Detalhado de Ativos:**  Marca, potência, modelo e número de série integrados à árvore de ativos.  
*   **Plano de Atividades Recorrentes:**  O "coração" do PMOC, com agendamentos automáticos mensais, trimestrais e anuais.  
* **OS** automáticas, hierárquicas, com instruções, lista de materiais, ferramentas e EPIs

5\. Ciclo de Vida da Ordem de Serviço (OS) e Mobilidade

A Ordem de Serviço é a unidade atômica de inteligência da manutenção. Sua gestão dita a produtividade real das equipes de campo.

6\. Inteligência de Dados: KPIs e Suporte à Decisão

A transição para uma "gestão por indicadores" elimina a intuição e introduz o rigor estatístico no suporte à decisão.

**MTBF (Tempo Médio Entre Falhas):**  Indicador de confiabilidade que valida a eficácia dos planos de manutenção.

**MTTR (Tempo Médio Para Reparo):**  Medida de agilidade e eficiência técnica na resolução de problemas.

**MTTA (Mean Time to Acknowledge):**  Tempo médio para resposta inicial, essencial para o controle de SLAs operacionais.

**Wrench Time:**  Percentual de tempo produtivo da equipe em contato direto com o ativo, descontando deslocamentos e tarefas administrativas.

**Backlog de Manutenção:**  Volume de horas de trabalho pendentes, essencial para o dimensionamento de recursos.

As organizações frequentemente criam e refinam sistemas de EAM em vários estágios, começando com o rastreamento básico de ativos antes de passar para estratégias de manutenção mais avançadas e computacionalmente complexas. As etapas comuns incluem:

Planejamento: avaliação do escopo das necessidades de manutenção de uma organização, definição de metas e principais indicadores de desempenho (KPI), consulta aos stakeholders e escolha de uma solução de software de EAM apropriada.

Preparação de dados: coleta, integração e padronização de dados de ativos de toda a organização. Identificação de dados inacessíveis, incompatíveis ou corrompidos e preenchimento de lacunas de informação.

Alocação de tarefas: definição de quais equipes são responsáveis pela manutenção de quais ativos. Estabelecimento de limites claros entre as equipes e, ao mesmo tempo, criação de linhas abertas de comunicação em toda a organização. Equilíbrio de cargas de trabalho, cronogramas e recursos entre departamentos.

