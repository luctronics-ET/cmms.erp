# Arquitetura de Módulos — xCMASM

## cmasm.erp — Hub Central

Serve auth, usuários, ativos, locais, OS, estoque, grama. Todos os módulos consomem sua API em `http://xcore:8010` (Docker) ou `http://localhost:8010` (dev local).

### API xCore — endpoints principais

| Grupo | Prefixo | Descrição |
|-------|---------|-----------|
| Auth | `/api/auth/` | login, logout, me |
| Usuários | `/api/usuarios` | CRUD + estrutura/unidades |
| Ativos | `/api/ativos` | CRUD + arquivar |
| Locais | `/api/locais` | CRUD de localizações |
| OS | `/api/os` | ordens de serviço + etapas + kanban + KPIs |
| Estoque | `/api/estoque` | CRUD + movimentos |
| Grama | `/api/grama/` | áreas, máquinas, manutenção, operações, kanban |
| Sync | `/api/sync/` | importa backup JSON do ERP legado |

---

## Módulos Internos (dentro de cmasm_erp.html)

São páginas renderizadas **dentro do portal principal** via `showPage()`. Não precisam de container próprio.

| Grupo | Page | Descrição |
|-------|------|-----------|
| HUB | `dashboard` | KPIs e visão geral |
| ERP | `organizacao` | Pessoal / TMFT |
| ERP | `cargos` | Tabela de cargos |
| ERP | `organograma` | Árvore organizacional |
| ERP | `servicos` | Ordens de Serviço (OS) |
| ERP | `transportes` | Viaturas e deslocamentos |
| ERP | `manutencao` | Resumo geral de manutenção (todos os PMOCs) |
| ERP | `estoque` | Almoxarifado |
| ERP | `vegetal` | Controle vegetal / xGrama |
| ERP | `predial` | Locais e inspeção predial |
| ERP | `paiois` | Paiois / munição |
| Admin | `usuarios` | Gestão de usuários |
| Admin | `admin` | Configurações |

---

## Módulos Externos (repos independentes)

Cada módulo tem repo, banco e Docker próprios em `/home/luciano/DEV/`. Conectam-se ao ERP via `XCORE_URL`.

### Módulos Operacionais

| Módulo | Path | Porta | Stack | Status |
|--------|------|-------|-------|--------|
| xPredial | `/home/luciano/DEV/xPredial` | 8002 | FastAPI + HTML/JS | ✅ Operacional |
| xPaiol | `/home/luciano/DEV/xPaiol` | 8003 | FastAPI + HTML/JS | 🔶 Parcial |
| xAguada | `/home/luciano/DEV/xAguada` | 8001 | FastAPI + MQTT + nginx | ✅ Operacional |
| xCalibracao | `/home/luciano/DEV/pmoc_calibracao` | 8004 | FastAPI + HTML/JS | 🔶 Parcial |
| xSeguranca | `/home/luciano/DEV/xSeguranca` | 8000/3000 | FastAPI + React + PostgreSQL | 🔶 Em desenvolvimento |

### Módulos PMOC (HTML web artifacts)

Módulos de Manutenção Preventiva por setor. São arquivos HTML autônomos (sem servidor próprio) baseados em `referencias/ativo-template.html`. Acesso via URL direta ou iframe no ERP.

| Módulo | Path | Setor | Status |
|--------|------|-------|--------|
| xRegrigeracao | `/home/luciano/DEV/xRegrigeracao` | Refrigeração e Climatização | 🔶 Em desenvolvimento |
| pmoc_eletrica | `/home/luciano/DEV/pmoc_eletrica` | Elétrica | 🔶 Em desenvolvimento |
| pmoc_calibracao | `/home/luciano/DEV/pmoc_calibracao` | Calibração | 🔶 Em desenvolvimento |
| pmoc_corte | `/home/luciano/DEV/pmoc_corte` | Máquinas e Equipamentos de Corte | 🔶 Em desenvolvimento |
| pmoc_transportes | `/home/luciano/DEV/pmoc_transportes` | Viaturas e Embarcações | 🔶 Em desenvolvimento |
| xFonoclama | `/home/luciano/DEV/xFonoclama` | Alertas Sonoros (ESP32) | 🔶 Firmware |
| xCFTV | `/home/luciano/DEV/xCFTV` | Vigilância CFTV | 🔷 Planejamento |

---

## Override de URLs sem editar código

O arquivo `assets/xcmasm-module-links.js` centraliza as URLs. Pode ser sobrescrito via `localStorage`:

```js
localStorage.setItem('xcmasm_module_links', JSON.stringify({
  xpredial:    { navUrl: 'http://localhost:8002', appUrl: 'http://localhost:8002' },
  xpaiol:      { navUrl: 'http://localhost:8003', appUrl: 'http://localhost:8003' },
  xcalibracao: { navUrl: 'http://localhost:8004', appUrl: 'http://localhost:8004' },
  xaguada:     { navUrl: 'http://localhost:8001', appUrl: 'http://localhost:8001' },
}));
```

---

## Diagrama de Containers (Docker network: `xcmasm`)

```
Browser
  │
  ├── :3000  static server (npx serve .) ── cmasm_erp.html
  │
  ├── :8010  xcore (cmasm.erp FastAPI) ── SQLite core.db
  │            └── serve assets/
  │
  ├── :8002  xpredial   ── SQLite predial.db    ──→ xcore:8010
  ├── :8003  xpaiol     ── SQLite paiol.db      ──→ xcore:8010
  ├── :8004  xcalibracao ── SQLite calib.db     ──→ xcore:8010
  ├── :8001  xaguada (nginx + api + mqtt)
  └── :8000  xseguranca (api + react + postgresql)
```

Início rápido de todos os containers: `cd /home/luciano/DEV && docker compose up`
