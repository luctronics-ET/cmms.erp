# Plano de Implementação e Integração — xCMASM

**Última revisão:** 2026-05-01  
**Contexto:** O xCore API (`:8010`) já existe e é a âncora de integração. No workspace atual, `xPredial`, `xPaiol`, `xCalibracao` e `xSeguranca` aparecem como módulos locais; `xGrama` foi absorvido pelo `xCore`; `xServicos` não existe como módulo independente, embora o domínio e referências visuais existam no núcleo e no legado. O xAguada existe como sistema hídrico independente em `aguada-web/`, fora do escopo de publicação deste repositório. ERP_core permanece como legado HTML/localStorage enquanto a migração progressiva ocorre. Este documento descreve o estado atual, o que resta fazer e a prioridade de execução.

---

## 0. Status Real dos Módulos (01/05/2026)

### Legenda
- ✅ Funcional — pronto para uso em produção ou teste
- 🔶 Parcial — implementado mas com lacunas claras
- 🔷 Placeholder — pasta existe, sem código funcional

| Módulo | Porta | Backend | Frontend | Docker | Testes | Integração xCore | Status |
|---|---|---|---|---|---|---|---|
| **xCore** | 8010 | ✅ FastAPI | 🔶 frontend local parcial (`servicos/`, `mapa/`) | ❌ falta compose | ❌ | — (é o hub) | 🔶 |
| **xPredial** | 8002 | ✅ FastAPI | ✅ HTML/JS | ✅ | ✅ pytest | ✅ proxy `/api/usuarios` | ✅ |
| **xServicos** | — | ❌ módulo independente ausente no workspace | 🔶 referências em `xCore/frontend/servicos/` e legado | ❌ | ❌ | ❌ | 🔷 |
| **xGrama** | — | ✅ integrado ao `xCore` (`backend/grama.py`) | 🔶 sem frontend separado no workspace | ✅ via xCore | ❌ | parcial via xCore | 🔶 |
| **xAguada** | 8001 | ✅ FastAPI | ✅ HTML/JS | ✅ | ✅ pytest | ❌ (integração ainda não implementada) | ✅ satélite |
| **xPaiol** | 8003 | ✅ FastAPI | ✅ HTML/JS | ❌ | ❌ | ✅ `XCORE_URL` declarado | 🔶 |
| **xCalibracao** | 8004 | ✅ FastAPI | 🔶 HTML único | ❌ | ❌ | ✅ `XCORE_URL` declarado | 🔶 |
| **xSeguranca** | 8000 | 🔴 backend ausente como arquivo (`app.py/` está como diretório) | ✅ React | ✅ (Postgres+Redis) | scripts manuais | ❌ | 🔶 |
| **xMap** | — | ❌ | ✅ HTML/JS | ❌ | ❌ | ❌ | 🔶 |
| **ERP_core** | — | ❌ | ✅ HTML legado | ❌ | ❌ | ❌ (localStorage) | legado |
| **xEletrica** | — | ❌ | ❌ | ❌ | ❌ | ❌ | 🔷 |
| **xHVAC** | — | ❌ | ❌ | ❌ | ❌ | ❌ | 🔷 |
| **xCFTV** | — | ❌ (Java legado) | ❌ | ❌ | ❌ | ❌ | arquivado |

### Classificação arquitetural recomendada
- **Núcleo xCMASM:** `xCore`, `ERP_core` (até desligamento), `xPredial`, `xMap`, domínio de OS e grama centralizados no núcleo
- **Sistemas satélite especializados:** `xAguada`, `xPaiol`, `xCalibracao`, `xSeguranca`
- **Legado arquivado:** `xCFTV`
- **Backlog/placeholder:** `xEletrica`, `xHVAC`

### O que o xCore já entrega

Schema SQLite em `data/schema_core.sql` com 9 tabelas:
`usuarios`, `estrutura`, `cargos`, `ativos`, `sessoes`, `locais`, `ordens_servico`, `os_historico`, `os_etapas`, `estoque`, `estoque_movimentos`

Endpoints implementados em `backend/main.py` e `backend/grama.py`:
- `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/me`
- `GET /api/usuarios`, `GET /api/usuarios/{id}`, `POST /api/usuarios`, `PUT /api/usuarios/{id}`
- `GET /api/estrutura`, `GET /api/unidades`
- `GET /api/ativos`, `POST /api/ativos`, `GET /api/ativos/{id}`, `PUT /api/ativos/{id}`
- `POST /api/sync/erp`, `POST /api/sync/ativos` — importa backup JSON do ERP_core
- `GET /api/shared` — retrocompatibilidade com localStorage
- `GET /api/locais`, `GET /api/locais/{id}`, `POST /api/locais`, `PUT /api/locais/{id}`
- `GET /api/os`, `POST /api/os`, `GET /api/os/{id}`, `PUT /api/os/{id}`, `GET /api/os/kpis`, `GET /api/os/kanban`
- `GET /api/estoque`, `POST /api/estoque`, `PUT /api/estoque/{id}`, `POST /api/estoque/{id}/movimentos`
- `GET /api/grama/*` — áreas, máquinas, manutenção, operações, kanban, calendário e relatórios
- `GET /health`, `GET /api/health`

Scripts de ferramentas disponíveis: `seed_usuarios.py`, `migrate_from_backup.py`, `migrate_legacy_js.py`

---

---

## 1. ERP_core — Estado e dados a migrar

Ainda ativo como interface administrativa principal (HTML/localStorage). A migração ocorre via `POST /api/sync/erp` no xCore.

### Chaves localStorage relevantes para migração

| Chave | Conteúdo | Destino no xCore |
|---|---|---|
| `cmasm_users` | Usuários | tabela `usuarios` |
| `cmasm_cargos` | Mapa unidade→ocupante | tabela `cargos` |
| `cmasm_shared` | Snapshot org tree | tabela `estrutura` |
| `srv_servicos` | OS e PS | tabela `ordens_servico` |
| `ga_units` | Ativos (22 itens, 7 categorias) | tabela `ativos` |
| `ga_hist` | Histórico de manutenções | futuro: `os_historico` |

Organograma: 79 nós em 3 departamentos (CMASM-10 Infraestrutura, CMASM-20 Armas, CMASM-30 Administração).  
Ativos default: `gestao-ativos-data.js` → `UNIDADES_DEFAULT`.

**Ação pendente:** Exportar backup JSON do ERP_core e rodar:
```bash
python xCore/tools/migrate_from_backup.py cmasm_erp_backup.json
```

---

## 2. Arquitetura de integração atual

```
ERP_core (HTML legado) ────────────────┐
                                       │ POST /api/sync/erp
xPredial (FastAPI :8002) ─────────────┤  GET /api/usuarios (proxy)
xGrama   (domínio embutido no xCore) ─┼──► xCore API (:8010) ──► SQLite
xAguada  (FastAPI :8001) ─────────────┤  integração futura via operadores/locais
xPaiol   (FastAPI :8003) ─────────────┤       (9 tabelas)
xCalibracao (FastAPI :8004) ──────────┤
xSeguranca  (FastAPI :8000) ──────────┘
```

Todos os backends já têm `XCORE_URL = os.getenv("XCORE_URL", "http://localhost:8010")` configurado.

---

## 3. Dados que cada módulo consome do Core

| Módulo | Consome do Core | Produz para o Core |
|---|---|---|
| **xPredial** | usuários (executante, aprovador) | laudos vinculados a OS (`servico_id`) |
| **xGrama** | usuários (operador), ativos (`maquinas_corte`) | manutenções realizadas (via OS), hoje dentro do próprio xCore |
| **xPaiol** | usuários (responsável), locais | alertas de sensores |
| **xCalibracao** | usuários (técnico), ativos (armas/instrumentos) | resultados de calibração (via OS) |
| **xSeguranca** | usuários, locais | eventos de detecção |
| **xAguada** | usuários (operador), locais (reservatórios) | leituras de sensores, relatórios |

---

## 4. Pendências por prioridade

### P1 — Completar xCore (desbloqueador)

| Tarefa | Arquivo alvo | Observação |
|---|---|---|
| Adicionar Docker Compose | `xCore/docker-compose.yml` | Falta; bloqueia stack unificada |
| Validar `.env.example` existente | `xCore/.env.example` | Arquivo já existe; revisar conteúdo para publicação |
| Adicionar testes pytest | `xCore/tests/` | Pelo menos auth + usuarios + sync |
| Consolidar testes do CRUD de OS já existente | `xCore/backend/main.py` | O CRUD principal existe; falta cobertura automatizada |
| Script `import_usuarios_csv.py` | `xCore/tools/` | Para `ERP_core/cmasm_usuarios (1).csv` |

### P2 — domínio de Serviços / OS

No workspace atual, `xServicos` não existe como módulo independente. O domínio aparece distribuído entre o `xCore`, o frontend em `xCore/frontend/servicos/` e referências legadas como `xCore/servicos.html`. O ERP consolidado já absorveu dashboard, lista, kanban, detalhe, etapas e histórico; `xCore/servicos.html` e `xCore/xservicos.html` ficam apenas como launchers de compatibilidade para `cmasm-erp.html?page=srv-dashboard`. Lacunas:

| Tarefa | Observação |
|---|---|
| Remover o frontend Vue remanescente após migrar toda lógica exclusiva | `xCore/frontend/servicos/` |
| Integrar selects de usuários ao `GET :8010/api/usuarios` no frontend de serviços do núcleo | `xCore/frontend/servicos/` |
| Adicionar testes para fluxo de OS no núcleo | `xCore/tests/` |

### P3 — xGrama (consolidação no xCore)

O domínio de grama já foi absorvido pelo núcleo em `xCore/backend/grama.py` e `xCore/data/schema_grama.sql`. Lacunas:

| Tarefa | Observação |
|---|---|
| Validar o schema grama contra todas as rotas expostas | `xCore/data/schema_grama.sql` + `xCore/backend/grama.py` |
| Ligar operadores e máquinas ao inventário central do xCore | Backend + frontend do núcleo |
| Implementar testes para rotas `/api/grama/*` | `xCore/tests/` |

### P4 — xPaiol / xCalibracao (completar)

| Tarefa | Módulo | Observação |
|---|---|---|
| Criar Docker Compose | ambos | Falta |
| Criar testes pytest | ambos | Falta |
| Frontend HTML multi-página | xCalibracao | Hoje 1 HTML monolítico; separar em index/instrumentos/certificados/vencimentos |
| Endpoint PDF de PS | xCalibracao | `GET /api/v1/ps/{codigo}/pdf` → servir pasta `certificados/` |
| Chamar `GET :8010/api/usuarios` em selects de responsável/técnico | ambos | |
| Adicionar tabela `paiois` no schema | xPaiol | Tem sensores/armas/alertas mas sem registro de paiois físicos |

### P5 — xSeguranca (integração xCore)

Frontend React TS presente + Docker Compose com Postgres/Redis. Porém `app.py/` é um diretório vazio e o backend esperado não existe como arquivo Python.

| Tarefa | Observação |
|---|---|
| Corrigir a estrutura de `app.py` e recriar o backend mínimo | `xSeguranca/app.py/` está como diretório vazio |
| Integrar usuários do xCore para controle de acesso | `GET :8010/api/usuarios` |
| Persistir eventos de detecção como OS no xCore | Via `POST :8010/api/os` |

### P6 — ERP_core → finalizar migração

| Tarefa | Observação |
|---|---|
| Botão "Sincronizar com xCore" no Admin | `POST :8010/api/sync/erp` com JSON backup |
| `srvGetCoreUsers()` → `fetch('http://localhost:8010/api/usuarios')` + fallback localStorage | |
| Login via xCore + fallback localStorage offline | |
| Badge Online/Offline no sidebar | |

### P7 — Backlog (novos módulos)

| Módulo | Fonte de referência | Porta sugerida |
|---|---|---|
| **xTransportes** | `ERP_core/transportes.html` + `.import_readonly/modulos/10-Infraestrutura/transportes/` | 8005 |
| **xHVAC** | `gestao-ativos.html` (AC_SPLIT, AC_CENTRAL) | 8006 |
| **xEletrica** | `gestao-ativos.html` (GERADOR) + quadros elétricos | 8007 |
| **xFonoclama** | `xFonoclama/esp32_warning_system.tsx` | 8008 |

---

## 5. Importação de dados existentes

```bash
# 1. Usuários + organograma + cargos (JSON backup do ERP_core)
python xCore/tools/migrate_from_backup.py cmasm_erp_backup.json

# 2. Ativos (lê gestao-ativos-data.js diretamente — script já existe)
python xCore/tools/migrate_legacy_js.py

# 3. Usuários CSV (a criar)
# python xCore/tools/import_usuarios_csv.py "ERP_core/cmasm_usuarios (1).csv"

# 4. Seed 12 usuários default (desenvolvimento)
python xCore/tools/seed_usuarios.py

# 5. Certificados de calibração (a criar)
# python xCalibracao/tools/import_certificados.py xCalibracao/.old/certificados.csv
```

---

## 6. Padrão de integração nos módulos

**FastAPI** (já usado em xPaiol, xCalibracao, xPredial):
```python
import os, httpx

XCORE_URL = os.getenv("XCORE_URL", "http://localhost:8010")

async def get_core_users() -> list[dict]:
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{XCORE_URL}/api/usuarios")
        return r.json() if r.status_code == 200 else []
```

**Node.js** (xGrama/xServicos):
```javascript
const XCORE_URL = process.env.XCORE_URL || 'http://localhost:8010';

async function getCoreUsers() {
  const r = await fetch(`${XCORE_URL}/api/usuarios`);
  return r.ok ? r.json() : [];
}
```

---

## 7. Variáveis de ambiente

`xCore/.env.example` (já existente; revisar):
```
PORT=8010
DB_PATH=./data/core.db
TOKEN_TTL_HOURS=8
CORS_ORIGINS=http://localhost:3001,http://localhost:8002,http://localhost:8003,http://localhost:8004,http://localhost:5000,http://localhost:5001
```

Cada módulo adiciona:
```
XCORE_URL=http://localhost:8010
```

---

## 8. Docker Compose unificado (a criar na raiz)

```yaml
# /xCMASM/docker-compose.yml
services:
  xcore:
    build: ./xCore
    ports: ["8010:8010"]
    volumes: ["./xCore/data:/app/data"]

  xpredial:
    build: ./xPredial
    ports: ["8002:8002"]
    depends_on: [xcore]
    environment:
      - XCORE_URL=http://xcore:8010

  xgrama:
    build: ./xGrama/controle-vegetal/backend
    ports: ["5000:5000"]
    depends_on: [xcore]
    environment:
      - XCORE_URL=http://xcore:8010

  xservicos:
    build: ./xServicos/backend
    ports: ["5001:5001"]
    depends_on: [xcore]
    environment:
      - XCORE_URL=http://xcore:8010

  xpaiol:
    build: ./xPaiol
    ports: ["8003:8003"]
    depends_on: [xcore]
    environment:
      - XCORE_URL=http://xcore:8010

  xcalibracao:
    build: ./xCalibracao
    ports: ["8004:8004"]
    depends_on: [xcore]
    environment:
      - XCORE_URL=http://xcore:8010
```

---

## 9. Sequência de execução recomendada

```
[ Agora — Desbloqueadores ]
  ├─ Exportar backup ERP_core + rodar migrate_from_backup.py
  ├─ xCore: Docker + .env.example + testes + CRUD OS completo
  └─ xSeguranca: verificar/criar app.py (está como pasta vazia)

[ Curto prazo — Integrar módulos existentes ]
  ├─ xServicos: integrar xCore usuarios + Docker + testes
  ├─ xGrama: integrar xCore usuarios + ativos + testes
  └─ xPredial: já funciona; monitorar integração com executante_id

[ Médio prazo — Completar protótipos ]
  ├─ xPaiol: Docker + testes + tabela paiois + integração xCore
  └─ xCalibracao: frontend multi-página + Docker + testes

[ Longo prazo — Backlog ]
  ├─ ERP_core: botão sync + fallback API
  └─ xTransportes / xHVAC / xEletrica / xFonoclama
```

---

## 10. Arquivos a criar (pendentes)

| Arquivo | O que é |
|---|---|
| `xCore/docker-compose.yml` | Stack isolada do xCore |
| `xCore/.env.example` | Variáveis documentadas |
| `xCore/tests/test_core.py` | Testes auth + usuarios + sync |
| `xCore/tools/import_usuarios_csv.py` | Importa CSV de usuários do ERP |
| `xServicos/docker-compose.yml` | Stack do xServicos |
| `xPaiol/docker-compose.yml` | Stack do xPaiol |
| `xCalibracao/docker-compose.yml` | Stack do xCalibracao |
| `xCalibracao/tools/import_certificados.py` | Importa `.old/certificados.csv` |
| `xCalibracao/frontend/` (multi-página) | index, instrumentos, certificados, vencimentos |
| `docker-compose.yml` (raiz) | Stack unificada de toda a plataforma |

---

## 11. xCore — endpoints ainda pendentes

Schema tem tabelas criadas mas sem rotas no `main.py`:

| Endpoint | Tabela | Prioridade |
|---|---|---|
| `GET /api/os`, `POST /api/os` | `ordens_servico` | Alta — xPredial e outros precisam criar OS |
| `PUT /api/os/{id}/status` | `ordens_servico` / `os_historico` | Alta |
| `GET /api/estoque`, `POST /api/estoque` | `estoque` | Média |
| `POST /api/estoque/{id}/movimentos` | `estoque_movimentos` | Média |
| `PUT /api/ativos/{id}`, `DELETE /api/ativos/{id}` | `ativos` | Baixa |

---

## 5. Sequência de implementação (legado — substituída pela seção 9)

> Seção mantida como referência histórica do plano original (2026-04-28).
> O estado real em 2026-05-01 é descrito nas seções 0–4 e 9–11 acima.
