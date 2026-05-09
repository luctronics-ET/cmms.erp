# xCMASM — Agent Instructions

Sistema de gestão do CMASM (Centro de Mísseis e Armas Submarinas da Marinha).

## Arquitetura: Núcleo + Satélites

O xCMASM é organizado em dois níveis:

- **Núcleo (`xCore/`)** — API central única (porta 8010). Concentra usuários, ativos, locais, OS, estoque e controle vegetal.
- **Satélites** — módulos especializados com repos e containers próprios, integram via `XCORE_URL`.

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

## Satélites (espelhos locais no workspace)

| Satélite | Pasta | Stack | Porta | Integração |
|----------|-------|-------|-------|------------|
| **xPredial** | `xPredial/` | FastAPI + HTML/JS | 8002/3001 | `GET /api/usuarios` via XCORE_URL |
| **xSeguranca** | `xSeguranca/` | React + stack Docker; backend Python precisa ser restaurado | 8000 | — |
| **xPaiol** | `xPaiol/` | FastAPI + HTML/JS | 8003 | XCORE_URL configurado |
| **xCalibracao** | `xCalibracao/` | FastAPI (stub) | 8004 | XCORE_URL configurado |
| **aguada-web** | `aguada-web/` | FastAPI + MQTT + HTML/JS | 8001 | espelho local do sistema hídrico |

Os satélites podem continuar existindo como repositórios independentes fora desta pasta, mas o `cmasm.erp` agora mantém cópias locais para referência, migração e consolidação.

Todos os satélites definem `XCORE_URL = os.getenv("XCORE_URL", "http://localhost:8010")`.

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

Referência de componentes: `xCore/CMASM_Gestao_v2.html` e `xPredial/frontend/assets/xpredial-core.css`.

## Padrões de Código

- **Frontend HTML**: HTML5 + vanilla JS puro. Sem framework, sem build step.
- **Frontend Vue**: legado em processo de descontinuação; a entrada `xCore/frontend/servicos/index.html` redireciona para o ERP consolidado.
- **Backend**: FastAPI + aiosqlite. Async/await. Pydantic para validação.
- **API Client**: objeto plano `predialAPI.metodo()` — ver `xPredial/frontend/assets/predial-api.js`.
- **Banco**: SQLite com schemas aditivos. `db_core.py` carrega `schema_core.sql` + `schema_grama.sql` no startup.
- **NEO**: código curto derivado do CMASM (ex: `CMASM-34.2` → NEO `34.2`), preservar pontos para hierarquia.

## Integração entre Módulos

- `xPredial` → `xCore`: proxy `/api/v1/usuarios` → `GET http://xcore:8010/api/usuarios`
- `xCore/frontend/servicos/` → launcher de compatibilidade para o módulo interno de serviços no ERP (`srv-dashboard`)
- `xCore/frontend/mapa/` → `xCore API`: fetch `http://localhost:8010/api/grama/*`
- `xGrama` → no workspace atual, o domínio está embutido no `xCore` via `/api/grama/*`
- Navegação cross-módulo: link `⇚ xCMASM` aponta para o portal principal em `xCore/cmasm-erp.html`

## Docs de Referência

- Locais CMASM: [`xPredial/docs/arvore_locais_cmasm.md`](xPredial/docs/arvore_locais_cmasm.md)
- Norma principal: NBR 5674:2012 (manutenção de edificações)
- Plano estratégico: [`xPredial/.referencias/Plano Estratégico de Gestão de Manutenção Edificada_.md`](xPredial/.referencias/Plano%20Estratégico%20de%20Gestão%20de%20Manutenção%20Edificada_%20Diretrizes%20e%20Fluxos%20Operacionais.md)
