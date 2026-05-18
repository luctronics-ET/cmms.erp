# Plano de Implementação — xCMASM

**Última revisão:** 2026-05-17

---

## 0. Status dos Módulos

### Legenda
- ✅ Funcional — pronto para uso
- 🔶 Parcial — implementado com lacunas
- 🔷 Placeholder — iniciado mas sem funcionalidade real
- ❌ Ausente

| Módulo | Porta | Backend | Frontend | Docker | Testes | xCore | Status |
|--------|-------|---------|----------|--------|--------|-------|--------|
| **cmasm.erp (núcleo)** | 8010 | ✅ FastAPI | ✅ cmasm_erp.html | ❌ falta compose | ❌ | — hub | 🔶 |
| **xPredial** | 8002 | ✅ FastAPI | ✅ HTML/JS | ✅ | ✅ pytest | ✅ proxy usuarios | ✅ |
| **xPaiol** | 8003 | ✅ FastAPI | ✅ HTML/JS | ❌ | ❌ | ✅ XCORE_URL | 🔶 |
| **xAguada** | 8001 | ✅ FastAPI | ✅ HTML/JS | ✅ | ✅ pytest | ❌ futura | ✅ satélite |
| **xCalibracao** | 8004 | ✅ FastAPI | 🔶 HTML único | ❌ | ❌ | ✅ XCORE_URL | 🔶 |
| **xSeguranca** | 8000/3000 | 🔶 parcial | ✅ React | ✅ Postgres | scripts | ❌ | 🔶 |
| **xRegrigeracao** | — | ❌ | 🔶 HTML artifact | ❌ | ❌ | ❌ | 🔶 |
| **xFonoclama** | — | ESP32 | 🔶 React | ❌ | ❌ | ❌ | 🔷 |
| **xCFTV** | — | Java | ❌ | ❌ | ❌ | ❌ | 🔷 |
| **pmoc_eletrica** | — | ❌ | 🔶 HTML artifact | ❌ | ❌ | ❌ | 🔷 |
| **pmoc_corte** | — | ❌ | 🔶 HTML artifact | ❌ | ❌ | ❌ | 🔷 |
| **pmoc_transportes** | — | ❌ | 🔶 HTML artifact | ❌ | ❌ | ❌ | 🔷 |

---

## O que o núcleo já entrega

Schema SQLite em `data/schema_core.sql` com tabelas:
`usuarios`, `estrutura`, `cargos`, `ativos`, `sessoes`, `locais`, `ordens_servico`, `os_historico`, `os_etapas`, `estoque`, `estoque_movimentos`, `pmoc_refrigeracao`

Schema `data/schema_grama.sql`: `grama_areas`, `grama_maquinas`, `grama_operacoes_*`, `grama_kanban_tarefas`, `grama_calendario_eventos`

Endpoints em `backend/main.py` + `backend/grama.py`:
- `POST /api/auth/login|logout`, `GET /api/auth/me`
- `GET/POST/PUT /api/usuarios`, `GET /api/estrutura`, `GET /api/unidades`
- `GET/POST/PUT /api/ativos`
- `GET/POST/PUT /api/locais`
- `GET/POST /api/os`, `PUT /api/os/{id}`, `GET /api/os/kpis|kanban`
- `GET/POST/PUT /api/estoque`, `POST /api/estoque/{id}/movimentos`
- `GET/POST /api/grama/*` — áreas, máquinas, manutenção, operações, kanban, calendário
- `POST /api/sync/erp` — importa backup JSON do ERP legado
- `GET /api/shared` — retrocompatibilidade com localStorage

---

## Dados que cada módulo consome do Core

| Módulo | Consome | Produz |
|--------|---------|--------|
| xPredial | usuários (executante, aprovador) | laudos → OS (`servico_id`) |
| xGrama | usuários (operador), ativos (máquinas) | manutenções via OS (integrado ao core) |
| xPaiol | usuários (responsável), locais | alertas de sensores |
| xCalibracao | usuários (técnico), ativos | resultados de calibração via OS |
| xSeguranca | usuários, locais | eventos de detecção |
| xAguada | usuários (operador), locais | leituras de sensores |

---

## Pendências por prioridade

### P1 — Núcleo (desbloqueador)

| Tarefa | Arquivo | Observação |
|--------|---------|------------|
| Criar `docker-compose.yml` para xCore | `docker-compose.yml` (raiz) | Bloqueia stack unificada |
| Testes pytest para auth + usuarios + OS | `tests/` | Falta cobertura automatizada |
| Página `manutencao` no ERP | `cmasm_erp.html` | Resumo consolidado de todos os PMOCs |

### P2 — PMOC Refrigeração (dados prontos)

| Tarefa | Observação |
|--------|------------|
| API `/api/pmoc/refrigeracao` | Backend para expor tabela `pmoc_refrigeracao` |
| Frontend xRegrigeracao | Usar `referencias/ativo-template.html` como base |
| Importar CSV PMOC | `python tools/import_pmoc_refrigeracao.py` |

### P3 — PMOCs restantes (html web artifacts)

Cada PMOC usa `referencias/ativo-template.html` como ponto de partida.

| Módulo | Path | Próximo passo |
|--------|------|---------------|
| pmoc_eletrica | `/home/luciano/DEV/pmoc_eletrica` | Adaptar template para domínio elétrico |
| pmoc_corte | `/home/luciano/DEV/pmoc_corte` | Adaptar template para máquinas de corte |
| pmoc_transportes | `/home/luciano/DEV/pmoc_transportes` | Adaptar template para viaturas/embarcações |

### P4 — Módulos externos (completar)

| Tarefa | Módulo | Observação |
|--------|--------|------------|
| Docker Compose | xPaiol, xCalibracao | Falta |
| Testes pytest | xPaiol, xCalibracao | Falta |
| Integrar usuários do ERP | xSeguranca | `GET /api/usuarios` via XCORE_URL |
| Push leituras → xCore ativos | xAguada | Endpoint de atualização de uso_atual |

### P5 — Infraestrutura

| Tarefa | Observação |
|--------|------------|
| Docker Compose raiz (`/home/luciano/DEV/docker-compose.yml`) | Orquestrar todos os módulos com `docker compose up` |
| Rede Docker `xcmasm` | Comunicação inter-containers por nome de serviço |
| Fontes 100% offline | Substituir CDN do Google Fonts por `assets/fonts/` em todos os módulos externos |
| `GET /api/modulos` | Listar módulos externos registrados + health check de cada um |
