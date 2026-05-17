# Arquitetura de Módulos — xCMASM

## xCore (cmasm.erp) — Hub Central

Serve auth, usuários, ativos, locais, OS, estoque. Todos os módulos consomem sua API em `http://xcore:8010` (Docker) ou `http://localhost:8010` (dev local).

### API xCore — endpoints principais

| Grupo | Prefixo | Descrição |
|-------|---------|-----------|
| Auth | `/api/auth/` | login, logout, me |
| Usuários | `/api/usuarios` | CRUD + estrutura/unidades |
| Ativos | `/api/ativos` | CRUD + arquivar + import/export CSV |
| Locais | `/api/locais` | CRUD de localizações |
| OS | `/api/os` | ordens de serviço + etapas + kanban + KPIs |
| Estoque | `/api/estoque` | CRUD + movimentos + export CSV |
| Grama | `/api/grama/` | áreas, máquinas, manutenção, operações, kanban |
| Sync | `/api/sync/` | sincronização ERP/ativos |

---

## Módulos Internos (dentro de cmasm_erp.html)

São páginas renderizadas **dentro do portal principal** via `showPage()`. Não precisam de container próprio.

| Seção | Módulo (page) | Descrição |
|-------|---------------|-----------|
| Principal | `dashboard` | KPIs e visão geral |
| Organização | `organizacao` | Pessoal / TMFT |
| Organização | `cargos` | Tabela de cargos |
| Organização | `organograma` | Árvore organizacional |
| Operações | `servicos` | Ordens de Serviço (OS) |
| Operações | `transportes` | Viaturas e deslocamentos |
| Operações | `manutencao` | Gestão de manutenção |
| Operações | `calibracao` | Controle de calibração |
| Instalações | `estoque` | Almoxarifado |
| Instalações | `vegetal` | Controle vegetal / xGrama |
| Instalações | `predial` | Locais e inspeção predial |
| Instalações | `paiois` | Paiois / munição |
| Admin | `usuarios` | Gestão de usuários |
| Admin | `admin` | Configurações |

### Módulos de Manutenção por Setor (template comum)

Cada um é um HTML autônomo que usa `ativo-template.html` como base. Navegação interna: `dash → frota (equipamentos) → [unidade] → estoque → rel`.

| Arquivo | Setor |
|---------|-------|
| `refrigeracao.html` | Refrigeração e Climatização |
| `eletrica.html` | Elétrica e Eletrônica |
| `maq-corte.html` | Máquinas e Equipamentos de Corte |
| `xgrama.html` | Controle Vegetal (xGrama) |

---

## Módulos Externos (containers separados)

São serviços independentes com backend FastAPI próprio. O portal os referencia via `openModulo()` / `xcmasm-module-links.js`.

| Módulo | Container | Porta | Stack | Status |
|--------|-----------|-------|-------|--------|
| xPredial | `xpredial` | 8002 | FastAPI + HTML/JS | Operacional ✓ |
| xPaiol | `xpaiol` | 8003 | FastAPI + HTML/JS | Operacional ✓ |
| xAguada | `xaguada` | 8001 | FastAPI + MQTT + nginx | Operacional ✓ |
| xCalibracao | `xcalibracao` | 8004 | FastAPI + HTML/JS | Operacional ✓ |
| xSeguranca | `xseguranca` | 8005 | FastAPI + React + PostgreSQL | Em desenvolvimento |
| xcftv-webapp | `xcftv-ui` | 3001 | React + Vite (nginx) | Em desenvolvimento |
| xCFTV | — | — | Java / Spring | Planejamento |
| xFonoclama | — | — | ESP32 + React | Firmware (não containerizável) |
| xRegrigeracao | — | — | Apenas documentação | Planejamento |

---

## Override de URLs sem editar código

O arquivo `assets/xcmasm-module-links.js` centraliza as URLs. É possível sobrescrever via `localStorage`:

```js
localStorage.setItem('xcmasm_module_links', JSON.stringify({
  xpredial:   { navUrl: 'http://localhost:8002', appUrl: 'http://localhost:8002' },
  xpaiol:     { navUrl: 'http://localhost:8003', appUrl: 'http://localhost:8003' },
  xcalibracao:{ navUrl: 'http://localhost:8004', appUrl: 'http://localhost:8004' },
  xaguada:    { navUrl: 'http://localhost:8001', appUrl: 'http://localhost:8001' },
}));
```

---

## Diagrama de Containers (Docker network: `xcmasm`)

```
Browser
  │
  ├── :8010  xcore (cmasm.erp FastAPI) ── SQLite core.db
  │            └── serve assets/, *.html
  │
  ├── :8002  xpredial ── SQLite predial.db  ──→ xcore:8010
  ├── :8003  xpaiol   ── SQLite paiol.db    ──→ xcore:8010
  ├── :8004  xcalibracao ── SQLite calib.db ──→ xcore:8010
  ├── :8001  xaguada (nginx+api+mqtt)       ──→ xcore:8010
  └── :8005  xseguranca (api+react+pg)      ──→ xcore:8010
```

Início rápido: `cd /home/luciano/DEV && bash setup-docker.sh`