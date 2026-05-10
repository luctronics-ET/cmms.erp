# xPredial — Agent Instructions

Módulo de **gestão predial** do CMASM. Implementa NBR 5674:2012.

## Como Executar

```bash
# Backend (porta 8002)
cd /home/luciano/DEV/xCMASM/xPredial
pip install -r requirements.txt
uvicorn backend.main:app --host 127.0.0.1 --port 8002 --reload

# Frontend (porta 3001)
cd frontend
python3 -m http.server 3001

# Docker (completo)
docker compose up
```

Banco: `data/predial.db` (criado automaticamente). Seeds manuais: `database/seed_normas.sql`, `database/seed_locais_cmasm.sql`.

## Arquitetura

```
frontend/ (HTML + vanilla JS, porta 3001)
  ├── assets/predial-api.js    ← client HTTP (objeto predialAPI)
  ├── assets/predial.js        ← UI compartilhada (window.xPredialUI)
  └── assets/xpredial-core.css ← design system (tokens xCMASM)

backend/ (FastAPI, porta 8002)
  ├── main.py   ← endpoints /api/v1/
  └── db_predial.py  ← PredialDB async wrapper + migrations aditivas
```

## Modelo de Dados

### Hierarquia de Locais
```
locais (self-referência parent_id)
  ├── codigo: "CMASM-34.2"   (código hierárquico completo)
  ├── neo: "34.2"            (derivado, strip do prefixo CMASM-)
  ├── tipo: texto livre       (edificio|bloco|sala|paiol|cais|etc)
  ├── area: ADM|OPE|APA      (área funcional CMASM)
  └── restricao: civil|militar|reservado|secreto|proibido
```
Árvore em [`docs/arvore_locais_cmasm.md`](docs/arvore_locais_cmasm.md).

### Inspeções — State Machine
```
planejada → em_execucao → aguardando_aprovacao → aprovada → concluida
                                               ↘ reprovada → em_execucao
```
Transições validadas em `PUT /api/v1/inspecoes/{id}/status`. Audit trail em `workflow_events`.

### Entidades Principais
- **`locais`** — espaços físicos hierárquicos
- **`checklist_templates`** + **`checklist_template_items`** — modelos reutilizáveis por tipo de local
- **`inspecoes`** — instâncias de vistoria com itens do checklist copiados
- **`inspecao_itens`** — itens preenchidos: `condicao` = `ok|atencao|critico`
- **`laudos`** — documentos técnicos/ARTs vinculados a local ou inspeção
- **`normas`** — catálogo ABNT (NBR 5674, 15575, 14037, 16280)
- **`workflow_events`** — trilha imutável de transições de status

### Integração xServicos
Campo `servico_id` em `inspecoes` referencia OS (Ordem de Serviço) ou PS (Pedido de Serviço) do módulo xServicos. A lógica é: inspeção detecta problema → gera PS no xServicos → OS executada → conclusão da inspeção atualiza status.

## Endpoints API

| Método | Rota | Descrição |
|---|---|---|
| GET | `/health` | Health check |
| GET/POST | `/api/v1/locais` | Listar / criar locais |
| GET/POST | `/api/v1/templates` | Templates de checklist |
| GET/POST | `/api/v1/inspecoes` | Inspeções |
| GET | `/api/v1/inspecoes/{id}` | Inspeção completa (itens + workflow + laudos) |
| PUT | `/api/v1/inspecoes/{id}/itens` | Upsert item do checklist |
| PUT | `/api/v1/inspecoes/{id}/status` | Transição de estado |
| GET/POST | `/api/v1/laudos` | Laudos/ARTs |
| GET/POST | `/api/v1/normas` | Normas ABNT |
| GET | `/api/v1/historico` | Histórico filtrado |
| GET | `/api/v1/relatorio/resumo` | KPIs agregados |

## Padrões Frontend

### Estrutura de página
```html
<!-- Importar no <head> -->
<link rel="stylesheet" href="assets/xpredial-core.css">
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=DM+Sans:wght@400;500;600&display=swap" rel="stylesheet">

<!-- No <body> -->
<div id="app-header"></div>  <!-- preenchido por setHeader() -->
<script src="assets/predial-api.js"></script>
<script src="assets/predial.js"></script>
<script>
  xPredialUI.setHeader('nomePagina', 'Subtítulo');
  // lógica da página
</script>
```

### xPredialUI helpers
- `setHeader(activePage, subtitle)` — renderiza header + nav
- `navHTML(activePage)` — retorna HTML do nav (pages: `index|locais|planejamento|inspecoes|aprovacoes|laudos|normas|historico-relatorios`)
- `loadLocaisSelect(selectId)` — popula `<select>` com locais da API
- `badge(status)` — classes CSS para status/condição
- `toast(msg, type)` — notificações. `type`: `'success'|'error'` (warn → usar 'error')

### predialAPI methods
```js
predialAPI.listLocais()          // GET /api/v1/locais
predialAPI.createLocal(data)     // POST /api/v1/locais
predialAPI.listInspecoes(params) // GET /api/v1/inspecoes?status=&local_id=
predialAPI.getInspecao(id)       // GET /api/v1/inspecoes/{id}
predialAPI.createInspecao(data)  // POST /api/v1/inspecoes
predialAPI.upsertItem(id, item)  // PUT /api/v1/inspecoes/{id}/itens
predialAPI.transition(id, data)  // PUT /api/v1/inspecoes/{id}/status
predialAPI.listLaudos(params)    // GET /api/v1/laudos
predialAPI.createLaudo(data)     // POST /api/v1/laudos
predialAPI.listNormas()          // GET /api/v1/normas
predialAPI.resumo()              // GET /api/v1/relatorio/resumo
predialAPI.historico(params)     // GET /api/v1/historico
```

## Bugs Conhecidos / Issues Pendentes

| Prioridade | Issue | Arquivo |
|---|---|---|
| ALTA | `planejamento.html` e `aprovacoes.html` ausentes do `navHTML()` | `predial.js` |
| ALTA | "Salvar Análise Técnica" envia transição `em_execucao→em_execucao` → HTTP 400 quando já em execução | `inspecoes.html` |
| MÉDIA | `#historicoBtn` sem event listener (não abre histórico) | `inspecoes.html` |
| MÉDIA | Botão "Detalhes" em locais é stub | `locais.html` |
| MÉDIA | Google Fonts não importado no `<head>` de nenhuma página | todas as páginas |
| BAIXA | `toast(..., "warn")` inválido — usar `"error"` | `aprovacoes.html` |
| BAIXA | `badge()` trata `"critica"` mas backend usa `"critico"` | `predial.js` |
| BAIXA | `predial-theme.css` é arquivo morto (não linkado em nenhuma página) | assets/ |

## Convenções Importantes

- **Migrations aditivas**: sempre usar `PRAGMA table_info` guard antes de `ALTER TABLE ADD COLUMN`
- **NEO**: derivar como `codigo.replace('CMASM-', '')`, preservar pontos
- **Estado**: nunca re-enviar transição para estado atual — verificar estado atual antes de chamar `transition()`
- **Tipos de local expandidos**: além de `edificio|sala`, considerar `bloco|laboratorio|almoxarifado|paiol|cais|area_externa|instalacao`
- **Area funcional**: `ADM` (administrativa), `OPE` (operacional), `APA` (apoio)
- **Inspecoes filtragem**: na página de execução, filtrar para `status=planejada,em_execucao` — não mostrar todas
