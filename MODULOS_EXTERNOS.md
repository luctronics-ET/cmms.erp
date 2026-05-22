# Módulos Externos — contrato de integração

Este documento descreve sistemas **realmente externos** ao núcleo `cmasm.erp` — aqueles com hardware próprio (MQTT, ESP32), banco de dados independente (PostgreSQL) ou stack proprietária (firmware, Java). Cada um é um sistema autônomo com repo, container e ciclo de vida próprios.

> **Importante:** O **PMOC** (app de campo offline-first) **não** é um módulo externo. É parte do próprio repo `cmasm.erp` em `cmasm.erp/pmoc/`, com categorias internas (refrigeração, predial, paióis, transportes, grama, elétrica, calibração). O contrato de sincronização do PMOC com o núcleo está descrito em `Rules.md` e `Regras de Negocio e Fluxos.md`.

---

## 1. Catálogo de módulos externos

| Módulo | Path | Stack | Porta | Status | Motivo de ser externo |
|--------|------|-------|-------|--------|------------------------|
| `aguada-web` | `/home/luciano/DEV/aguada-web` | FastAPI + MQTT + nginx | 8001 | ✅ Operacional | Hardware ESP32 + sensores hidráulicos |
| `xSeguranca` | `/home/luciano/DEV/xSeguranca` | React + FastAPI + PostgreSQL | 8000/3000 | 🔶 Em desenvolvimento | Banco PostgreSQL próprio + Redis |
| `xCFTV` | `/home/luciano/DEV/xCFTV` | Java | — | 🔷 Planejamento | Stack proprietária de vídeo |
| `xFonoclama` | `/home/luciano/DEV/xFonoclama` | firmware ESP32 | — | 🔶 Firmware | Dispositivo embarcado |

---

## 2. Princípios de integração

### 2.1 Núcleo é fonte da verdade

Módulos externos **consomem** usuários, ativos e organograma do núcleo via `GET /api/usuarios`, `GET /api/ativos`, `GET /api/estrutura`. Não replicam essas tabelas.

### 2.2 Eventos operacionais voltam ao núcleo

Quando o módulo externo gera uma Ordem de Serviço, envia ao núcleo via `POST /api/os` com `modulo_origem` preenchido (ex: `aguada-web`, `xseguranca`).

### 2.3 Auth Bearer

Todo módulo externo obtém token Bearer em `cmasm.erp/api/auth/login` usando credenciais do operador logado. Token é cacheado até expirar; após expirar, força re-login.

### 2.4 `XCORE_URL` por variável de ambiente

```
XCORE_URL=http://localhost:8010   # ou IP do núcleo na LAN do CMASM
```

### 2.5 Independência de schema

xSeguranca tem PostgreSQL próprio. aguada-web tem banco próprio para telemetria. Nenhum módulo externo lê/escreve diretamente no SQLite do núcleo.

---

## 3. Endpoints do núcleo usados por módulos externos

Todas as rotas exigem `Authorization: Bearer <token>`.

| Endpoint | Uso |
|---|---|
| `POST /api/auth/login` | Autenticação |
| `GET /api/usuarios` | Lista de usuários (para dropdowns, alocação) |
| `GET /api/estrutura` | Organograma (lotações, cargos) |
| `GET /api/ativos` | Lista de ativos (se aplicável ao módulo) |
| `POST /api/os` | Criar OS com `modulo_origem=<nome_modulo>` |
| `GET /api/os?modulo_origem=<>` | Listar OS criadas por este módulo |

---

## 4. Bridge futuro: telemetria → sync

Para módulos com hardware (ESP32, sensores), a integração futura prevista é:

```
ESP32 / sensor → MQTT → bridge → POST /api/sync/push
  payload: { tipo: "uso_atual_inc", ativo_id, delta, fonte: "iot_<modulo>" }
```

Isso reaproveita o pipeline de sync que já existe para o PMOC. Ver `Rules.md §16` (roadmap de regras).

---

## 5. Para criar um novo módulo externo

Justificar antes de criar. Critério: o módulo **precisa** rodar fora do núcleo se, e somente se:

1. Tem hardware próprio (MQTT, drivers, firmware), **ou**
2. Tem banco de dados que não cabe no SQLite do núcleo (PostgreSQL, Redis), **ou**
3. Usa stack incompatível (Java, .NET, firmware embarcado).

Se nenhum dos três aplica, o domínio provavelmente é uma **categoria do PMOC** ou um **módulo interno do núcleo**, não um módulo externo.
