# xCMASM — Agent Instructions

Sistema de gestão do CMASM (Centro de Mísseis e Armas Submarinas da Marinha).

## Arquitetura: Núcleo + Módulos Externos

O xCMASM é organizado em dois níveis:

- **Núcleo (`xCore/`)** — API central única (porta 8010). Concentra usuários, ativos, locais, OS, estoque e controle vegetal.
- **Módulos Externos** — sistemas especializados com repositórios, bancos e containers Docker próprios. Integram com o ERP via `XCORE_URL` para consultar ou fornecer dados. Ficam **fora** do repo `cmasm.erp`, em repos independentes.

## Estrutura do Núcleo (xCore — porta 8010)

| Domínio | Rotas | Tabelas |
|---------|-------|---------|
| Auth | `/api/auth/*` | sessoes |
| Usuários / Org | `/api/usuarios`, `/api/estrutura` | usuarios, estrutura, cargos |
| Ativos | `/api/ativos` | ativos |
| Locais | `/api/locais` | locais |
| Ordens de Serviço | `/api/os/*` | ordens_servico, os_etapas, os_historico |
| Estoque | `/api/estoque/*` | estoque, estoque_movimentos |
| Controle Vegetal | `/api/grama/*` | grama_areas, grama_maquinas, grama_operacoes_*, grama_kanban_tarefas, grama_calendario_eventos |

### Frontends embutidos no xCore

| Pasta | Conteúdo |
|-------|----------|
| `xCore/cmasm-erp.html` | Portal principal ERP |
| `xCore/servicos.html` | Tela de OS legado |
| `xCore/frontend/servicos/` | Entrada legada (compatibilidade) redirecionada para `cmasm-erp.html?page=srv-dashboard` |
| `xCore/frontend/mapa/` | xMap — mapa de instalações com camadas Leaflet |

## Módulos Externos (containers independentes)

Cada módulo externo é um sistema autônomo com seu próprio repo, banco de dados e container Docker. Eles se conectam ao ERP consultando a API do xCore (usuários, ativos, OS) e aparecem como botões na navbar do ERP na seção **Módulos Externos**.

| Módulo | Stack | Porta | Integração com xCore |
|--------|-------|-------|----------------------|
| **xPredial** | FastAPI + HTML/JS | 8002 | `GET /api/usuarios` via XCORE_URL; pode gerar OS |
| **xSeguranca** | React + FastAPI + PostgreSQL | 8000/3000 | Independente (próprio DB); futura integração de usuários |
| **xPaiol** | FastAPI + HTML/JS | 8003 | `GET /api/usuarios`, futura integração de ativos |
| **xCalibracao** | FastAPI (stub) | 8004 | `GET /api/usuarios` via XCORE_URL |
| **aguada-web** | FastAPI + MQTT + HTML/JS | 8001 | Independente; futuramente enviará dados de ativos hidráulicos |
| **xCFTV** | Java (Spring) | — | Independente (vídeo/plantas CFTV) |
| **xFonoclama** | ESP32 + React | — | Independente (alertas sonoros) |

### Princípios dos Módulos Externos

- **Banco separado**: cada módulo tem seu próprio SQLite/PostgreSQL — nunca compartilham DB com o xCore
- **Usuários do ERP**: módulos obtêm a lista de usuários via `GET http://xcore:8010/api/usuarios` usando o token Bearer do operador logado; não duplicam a tabela de usuários
- **Docker independente**: cada módulo tem `docker-compose.yml` próprio; comunicação via rede Docker ou `XCORE_URL` configurável por env
- **Acesso no ERP**: botões na navbar do ERP (`cmasm_erp.html`) na seção "Módulos Externos"; cada módulo terá página de dashboard-resumo futuramente
- **Todos definem**: `XCORE_URL = os.getenv("XCORE_URL", "http://localhost:8010")`

## Design System — xCMASM

**Dark theme obrigatório.** CSS tokens compartilhados em todos os módulos:

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

Fontes: JetBrains Mono (dados/código) + DM Sans (UI). Carregar do Google Fonts no `<head>`.

Referência de componentes: `xCore/CMASM_Gestao_v2.html` e `xCore/predial/assets/xpredial-core.css`.

## Padrões de Código

- **Frontend HTML**: HTML5 + vanilla JS puro. Sem framework, sem build step.
- **Frontend Vue**: legado em processo de descontinuação; a entrada `xCore/frontend/servicos/index.html` redireciona para o ERP consolidado.
- **Backend**: FastAPI + aiosqlite. Async/await. Pydantic para validação.
- **API Client**: objeto plano `predialAPI.metodo()` — ver `xCore/predial/assets/predial-api.js`.
- **Banco**: SQLite com schemas aditivos. `db_core.py` carrega `schema_core.sql` + `schema_grama.sql` no startup.
- **NEO**: código curto derivado do CMASM (ex: `CMASM-34.2` → NEO `34.2`), preservar pontos para hierarquia.

## Integração entre Módulos

- **Módulos Externos → xCore**: cada módulo usa `XCORE_URL` para `GET /api/usuarios` (Bearer token do operador)
- **xCore → Módulos Externos**: links na navbar do ERP abrem o módulo externo (URL configurável por env)
- `xCore/frontend/servicos/` → launcher de compatibilidade para o módulo interno de serviços no ERP (`srv-dashboard`)
- `xCore/frontend/mapa/` → `xCore API`: fetch `http://localhost:8010/api/grama/*`
- `xGrama` → domínio embutido no `xCore` via `/api/grama/*`
- Navegação cross-módulo: link `⇚ xCMASM` aponta para o portal principal em `xCore/cmasm-erp.html`

## Docs de Referência

- Locais CMASM: [`xCore/predial/docs/arvore_locais_cmasm.md`](xCore/predial/docs/arvore_locais_cmasm.md)
- Norma principal: NBR 5674:2012 (manutenção de edificações)
