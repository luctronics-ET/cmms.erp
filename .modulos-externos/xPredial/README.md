# xPredial

O objetivo é fornecer um roteiro estruturado para gestores, com foco em gestao predial e de edificacoes. O documento deve integrar os requisitos técnicos da NBR 5674:2012, detalhando a organização necessária, o planejamento anual de atividades, a previsão orçamentária e os mecanismos de controle documental. O foco deve ser na criação de um fluxo de trabalho que consiste em locais, inspecoes, planejamento, gerenciamento, laudos. locais: modelo da area e edificacoes da organizacao, inspecao - vistoria e levantamento de necessidades de reparos. planejamento - reune e classifica e prioriza necessidades e seus servicos associados. gera 'Pedidos de Servicos'.  gerenciamento - visualizacao gantt/calendario/ lista de necessiades, andamento de servicos, inspecoes agendadas, .. , laudos - formularios - criar e visualizar documentos, laudos, inspecoes....

## Escopo implementado

- Cadastro de locais e predios com hierarquia.
- Checklist predial padrao cobrindo:
  - Pintura de fachada externa
  - Pintura interior
  - Verificacao de iluminacao
  - Piso
  - Portas
  - Janelas
  - Estado do mobiliario
  - Infiltracoes
  - Banheiros (sanitarios, pias, vazamentos)
- Workflow de inspecao:
  - `planejada -> em_execucao -> aguardando_aprovacao -> aprovada/reprovada -> concluida`
- Historico e resumo de indicadores.

## Rodar local

1. Criar ambiente e instalar dependencias:
   - `python3 -m venv .venv && source .venv/bin/activate`
   - `pip install -r requirements.txt`
2. Iniciar API:
   - `uvicorn backend.main:app --reload --port 8002`
3. Iniciar frontend:
   - `cd frontend && python3 -m http.server 3001`
4. Acessar:
   - API: `http://127.0.0.1:8002/docs`
   - Frontend: `http://127.0.0.1:3001/index.html`

## Testes

- `pytest tests -q`

## Docker

- `docker compose up`
