# xCMASM — Agent Instructions

Sistema de gestão do CMASM (Centro de Mísseis e Armas Submarinas da Marinha).

## Arquitetura: Núcleo + Módulos Externos

O xCMASM é organizado em dois níveis:

- **Núcleo (`cmasm.erp`)** — API central única (porta 8010). Concentra usuários, ativos, locais, OS, estoque e controle vegetal. Frontend principal em `cmasm_erp.html`.
- **Módulos Externos** — sistemas especializados com repositórios próprios em `/home/luciano/DEV/`. Integram com o ERP via `XCORE_URL` para consultar dados.

## Estrutura do Núcleo (porta 8010)

| Domínio | Rotas | Tabelas |
|---------|-------|---------|
| Auth | `/api/auth/*` | sessoes |
| Usuários / Org | `/api/usuarios`, `/api/estrutura` | usuarios, estrutura, cargos |
| Ativos | `/api/ativos` | ativos |
| Locais | `/api/locais` | locais |
| Ordens de Serviço | `/api/os/*` | ordens_servico, os_etapas, os_historico |
| Estoque | `/api/estoque/*` | estoque, estoque_movimentos |
| Controle Vegetal | `/api/grama/*` | grama_areas, grama_maquinas, grama_operacoes_*, grama_kanban_tarefas, grama_calendario_eventos |
| PMOC Refrigeração | — | pmoc_refrigeracao |

## Páginas do ERP (`cmasm_erp.html`)

São seções renderizadas via `showPage()` — sem containers próprios.

| Grupo | Page | Descrição |
|-------|------|-----------|
| HUB | `dashboard` | KPIs e visão geral |
| ERP | `organizacao` | Pessoal / TMFT |
| ERP | `cargos` | Tabela de cargos |
| ERP | `organograma` | Árvore organizacional |
| ERP | `servicos` | Ordens de Serviço (OS) |
| ERP | `transportes` | Viaturas e deslocamentos |
| ERP | `manutencao` | Resumo de manutenção (todos os PMOCs) |
| ERP | `estoque` | Almoxarifado |
| ERP | `vegetal` | Controle vegetal / xGrama |
| ERP | `predial` | Locais e inspeção predial |
| ERP | `paiois` | Paiois / munição |
| Admin | `usuarios` | Gestão de usuários |
| Admin | `admin` | Configurações |

## Módulos Externos (repos independentes)

| Módulo | Porta | Stack | Path local | Integração |
|--------|-------|-------|------------|------------|
| **xPredial** | 8002 | FastAPI + HTML/JS | `/home/luciano/DEV/xPredial` | `GET /api/usuarios` via XCORE_URL |
| **xPaiol** | 8003 | FastAPI + HTML/JS | `/home/luciano/DEV/xPaiol` | `GET /api/usuarios` via XCORE_URL |
| **xAguada** | 8001 | FastAPI + MQTT + nginx | `/home/luciano/DEV/xAguada` | Independente |
| **xCalibracao** | 8004 | FastAPI + HTML/JS | `/home/luciano/DEV/pmoc_calibracao` | `GET /api/usuarios` via XCORE_URL |
| **xSeguranca** | 8000/3000 | FastAPI + React + PostgreSQL | `/home/luciano/DEV/xSeguranca` | Independente |
| **xRegrigeracao** | — | HTML web artifact | `/home/luciano/DEV/xRegrigeracao` | Planejamento |
| **xFonoclama** | — | ESP32 + React | `/home/luciano/DEV/xFonoclama` | Independente |
| **xCFTV** | — | Java / Spring | `/home/luciano/DEV/xCFTV` | Independente |
| **pmoc_eletrica** | — | HTML web artifact | `/home/luciano/DEV/pmoc_eletrica` | Planejamento |
| **pmoc_corte** | — | HTML web artifact | `/home/luciano/DEV/pmoc_corte` | Planejamento |
| **pmoc_transportes** | — | HTML web artifact | `/home/luciano/DEV/pmoc_transportes` | Planejamento |

### Princípios dos Módulos Externos

- **Banco separado**: cada módulo tem seu próprio SQLite/PostgreSQL — nunca compartilham DB com o núcleo
- **Usuários do ERP**: módulos obtêm a lista via `GET http://xcore:8010/api/usuarios` com Bearer token do operador
- **Docker independente**: cada módulo tem `docker-compose.yml` próprio; comunicação via rede Docker `xcmasm` ou `XCORE_URL` configurável
- **Todos definem**: `XCORE_URL = os.getenv("XCORE_URL", "http://localhost:8010")`

## Design System — xCMASM

**Dark theme obrigatório.** CSS tokens compartilhados:

```css
--bg: #07111f        /* fundo primário */
--bg2: #0d1e33       /* fundo secundário */
--bg3: #0a1828
--panel: #0f2035
--acc: #00b4d8       /* ciano/acento */
--green: #22c55e
--red: #ef4444
--amber: #f59e0b
```

Fontes: **JetBrains Mono** (dados/código) + **DM Sans** (UI).
Fontes self-hosted em `assets/fonts/` — importar via `assets/fonts.css`.

## Padrões de Código

- **Frontend**: HTML5 + vanilla JS puro. Sem framework, sem build step.
- **Backend**: FastAPI + aiosqlite. Async/await. Pydantic para validação.
- **API Client**: objeto plano `xcmasm.metodo()` — ver `assets/xcmasm-sdk.js`.
- **Banco**: SQLite com schemas aditivos em `data/`. Nunca DROP — só `ALTER TABLE ADD COLUMN IF NOT EXISTS`.
- **NEO**: código curto derivado do CMASM (ex: `CMASM-34.2` → NEO `34.2`), preservar pontos para hierarquia.

## Template para novos módulos

`referencias/ativo-template.html` é o ponto de partida para novos módulos PMOC (HTML web artifact, sem build step). Configurar: `TIPOS`, `UNIDADES_DEFAULT`, `PECAS_DEFAULT`, `SK`/`SE` (chaves únicas de localStorage).

## Integração entre Módulos

- **Externos → Núcleo**: `XCORE_URL` para `GET /api/usuarios` (Bearer token do operador)
- **Núcleo → Externos**: links na navbar do ERP abrem o módulo externo (URL configurável por `localStorage` via `xcmasm-module-links.js`)
- **xGrama**: embutido no núcleo via `/api/grama/*`

## Docs de Referência

- `Rules.md` — regras de negócio, fluxos, categorias de ativos
- `MODULOS_EXTERNOS.md` — arquitetura de integração e diagrama de containers
- `PLANO_IMPLEMENTACAO.md` — roadmap e status de implementação
- `.docs_cmasm/` — dados autoritativos (CSV de usuários/cargos, mapas OSM, PDFs)
- `pmoc.refs/` em `/home/luciano/DEV/` — referências PMOC (CSVs, planilhas, docs técnicos)
