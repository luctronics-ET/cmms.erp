# CMASM — Sistema de Controle de Calibração
## API Node.js/Express + MySQL

### Modelo de dados fundamental
- **Equipamento** é identificado pelo `serial_number` (SN físico único)
- **PS (Pedido de Serviço)** tem relação N:1 com equipamento — um instrumento acumula um PS por calibração anual, mais PS de reparo
- Ao concluir PS de calibração: trigger atualiza `last_calibration_date`, `next_calibration_date` e `status=CALIBRADO` no equipamento
- Ao concluir PS de reparo: status vira `AGUARDANDO_CALIBRACAO`

### Instalação

```bash
cp .env.example .env
# Editar .env com credenciais MySQL

mysql -u root -p < database/migrations/001_schema.sql
mysql -u root -p cmasm_calibracao < database/migrations/002_seeds.sql

node src/server.js
# API em http://localhost:3001/api/v1
```

### Endpoints principais

#### Auth
- `POST /api/v1/auth/login`   — Login, retorna JWT
- `GET  /api/v1/auth/me`      — Dados do usuário logado

#### Equipamentos
- `GET    /api/v1/equipment/kpis`          — KPIs do dashboard
- `GET    /api/v1/equipment`               — Listagem (filtros: divisao, status, laboratorio, search)
- `GET    /api/v1/equipment/:id`           — Detalhe + histórico de PS
- `POST   /api/v1/equipment`               — Criar equipamento
- `PUT    /api/v1/equipment/:id`           — Atualizar equipamento
- `DELETE /api/v1/equipment/:id`           — Inativar (soft delete)

#### Histórico PS por equipamento
- `GET /api/v1/equipment/:id/service-orders` — Todos os PS de um instrumento (aceita id ou SN)

#### Pedidos de Serviço
- `GET    /api/v1/service-orders`          — Listagem (filtros: status, divisao, laboratorio, tipo)
- `GET    /api/v1/service-orders/:id`      — PS individual com calibração técnica
- `POST   /api/v1/service-orders`          — Emitir PS (número gerado automaticamente)
- `PATCH  /api/v1/service-orders/:id`      — Atualizar status/dados (valida transições)
- `DELETE /api/v1/service-orders/:id`      — Cancelar PS

#### Relatórios
- `GET /api/v1/reports/conformidade`       — Relatório ISO/IEC 17025
- `GET /api/v1/reports/certificados`       — Listagem de certificados

#### Importação
- `POST /api/v1/import/equipment`          — Importar array de equipamentos (upsert por SN ou PAT)

#### Laboratórios / Organizações
- `GET  /api/v1/laboratories`              — Lista de laboratórios
- `POST /api/v1/laboratories`              — Criar laboratório
- `PUT  /api/v1/laboratories/:id`          — Atualizar laboratório
- `GET  /api/v1/organizations`             — Estrutura hierárquica CMASM

### Transições de status de PS
```
RASCUNHO → EMITIDO → ENVIADO → EM_CALIBRACAO → CONCLUIDO
                    ↕                         ↓
                 CANCELADO              CANCELADO (não se aplica a CONCLUIDO)
```

### Estrutura de diretórios
```
src/
  server.js                      — Express app (porta 3001)
  routes/index.js                — Todas as rotas
  controllers/
    equipment.controller.js      — CRUD equipamentos + KPIs
    serviceOrders.controller.js  — PS: emissão, ciclo de vida, histórico
    misc.controller.js           — Auth, laboratórios, organizações
    reports.controller.js        — Relatório conformidade, certificados, importação
  middleware/auth.js             — JWT + asyncHandler + errorHandler
  utils/db.js                    — Pool MySQL
database/
  migrations/
    001_schema.sql               — Schema v3.0 (15 tabelas, triggers, views, procedures)
    002_seeds.sql                — Dados iniciais reais (labs, organizações, equipamentos)
```
