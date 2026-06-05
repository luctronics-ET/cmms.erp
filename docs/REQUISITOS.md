# Requisitos do projeto xCMASM

Documento de visão e requisitos não-funcionais. Para o modelo de domínio e fluxos de negócio, ver `Regras de Negocio e Fluxos.md`. Para regras técnicas/operacionais do núcleo, ver `Rules.md`. Para integração com módulos *realmente* externos (hardware/Postgres próprio), ver `MODULOS_EXTERNOS.md`.

---

## 1. Visão

Plataforma integrada para gestão da **manutenção de ativos e dos serviços** do CMASM. Composta por:

1. **Núcleo** (`cmasm.erp`): backend FastAPI + ERP web (`cmasm_erp.html`). Centraliza usuários, organização, ativos, estoque, ordens de serviço e o painel de Manutenção. O painel de Manutenção é uma **tela única com tabs por categoria** de ativo (refrigeração, predial, paióis, transportes, grama, elétrica, calibração).
2. **PMOC único de campo** (`cmasm.erp/pmoc/`): aplicativo HTML offline-first, com seletor de categoria interno. Opera 100% local (IndexedDB) e sincroniza com o núcleo via API REST.

**Foco operacional**: gerar e executar serviços (OS) — preventivos (plano de manutenção), corretivos (defeito reportado) ou periódicos (rotina). Apoiar com cadastros mestres (usuários, ativos, estoque) e documentos.

**Não é foco** (não substitui sistemas existentes da Marinha):

- CADBEM — patrimônio (bens permanentes).
- Sistemas financeiros/orçamentários.
- Comunicações táticas.

---

## 2. Stakeholders e escala

| Perfil | Quantidade típica | Modo de uso |
|--------|-------------------|-------------|
| Direção/gestores | 5–10 | Painel, autorização de PS, relatórios |
| Encarregados de seção | 10–15 | Gera OS, gerencia equipe e estoque setorial |
| Operadores de campo | 2–5 por seção | PMOC na categoria da sua especialidade |
| Solicitantes | ~100 | Abre PS, acompanha status |

Escala total: 50–100 usuários ativos, dezenas de ativos por categoria. **Não** é sistema de massa — otimizar para clareza, não throughput.

---

## 3. Princípios arquiteturais

### 3.1 Núcleo único + PMOC único categorizado

O núcleo cobre usuários, organização, ativos, estoque, OS, painel de Manutenção (categorizado por `tipo` de ativo) e documentos. O PMOC de campo é **um único app**, com categorias internas que correspondem 1:1 às categorias de ativos do núcleo.

**Por quê**: tentar manter N PMOCs separados (um repo por domínio) gerou duplicação de código (sync, auth, IndexedDB, UI shell). Um PMOC único com categorias internas elimina essa duplicação e mantém um único contrato de sincronização.

### 3.2 Offline-first no PMOC

O PMOC opera 100% local (IndexedDB) e sincroniza com o núcleo. Operador trabalha sem rede; sincroniza quando volta para a base.

**Por quê**: paióis, garagens, embarcações e algumas oficinas têm rede instável ou inexistente. Exigir rede live trava operação real.

### 3.3 Núcleo é fonte da verdade do cadastro mestre

Usuários, ativos e catálogo de estoque vivem no núcleo. O PMOC **consome** (não cria, não edita). Eventos operacionais (OS, movimentos, leituras) fluem PMOC → núcleo.

### 3.4 HTML web artifacts sempre que possível

Preferir páginas HTML únicas + IndexedDB sobre servidor próprio. Exceção: módulos com hardware (MQTT, drivers — ex: `aguada-web`) ou dados pesados (`xSeguranca` com PostgreSQL).

**Por quê**: HTML autônomo roda em qualquer máquina/celular sem stack. Reduz custo de deploy, suporte e infra.

### 3.5 Migração de schema só aditiva

`PRAGMA table_info` antes de cada `ALTER`. Nunca `DROP`. IDs nunca reaproveitados. Arquivamento (`ativo=0`) substitui exclusão.

### 3.6 Auditoria por design

Todo evento (OS, movimento, leitura, mudança de status) traz `ts`, `autor`, `origem`. Histórico imutável. Correção é novo evento, não edição.

### 3.7 Catálogo de serviços híbrido

Núcleo guarda o catálogo **central** (serviços oficiais com POP, materiais, pessoal, condicionais). O PMOC pode criar serviços **locais** que vivem só no device — não voltam ao núcleo. Quando uma OS é gerada a partir de serviço local, ela carrega um **snapshot embarcado** com toda a definição, garantindo histórico íntegro no núcleo.

**Por quê híbrido**: serviços oficiais garantem consistência entre setores e auditoria normativa. Serviços locais cobrem casos excepcionais (paiol específico, equipamento atípico) sem poluir o catálogo central nem bloquear a operação esperando aprovação.

### 3.8 Motor de geração de OS no PMOC

O motor que avalia planos de manutenção e gera PS roda **dentro do PMOC**, offline. Tem o catálogo + planos + estoque + qualificações na cópia local. Avalia condicionais com contexto do device (clima, energia, escala). Falha de condicional adia, não cancela. PS criadas entram na fila de sync e são oficializadas no próximo push.

### 3.9 Componentes UI obrigatórios (PMOC)

O PMOC inclui um conjunto padronizado de componentes UI (originalmente desenhados em `pmoc-engine.js`). Componentes ativados conforme a categoria selecionada:

| Componente | Função |
|---|---|
| Header com sync-status | Usuário, último sync, pendentes, online/offline |
| Calendar | Visão de manutenções/vencimentos por mês |
| Kanban | OS por status |
| Tabela com filtros | Ativos, OS, materiais, qualificações |
| Modal | Padronizado (header/body/footer) |
| Badge | Status, prioridade, contadores |
| Chart donut/linha | Dashboard (MTBF, conformidade, OS por estado) |
| Direct chat | Mensagens dentro de uma OS (executor ↔ gestor) |
| Camera/foto | Anexar mídia via celular |

---

## 4. Requisitos funcionais (visão alta)

### 4.1 Núcleo (`cmasm.erp`)

- Login + sessão com timeout configurável.
- CRUD de usuários, cargos, lotações, organograma.
- CRUD de ativos com `uso_atual` rastreável.
- CRUD de estoque com modelo distribuído por seção.
- Workflow PS → OS → SR completo (`Rules.md §4`).
- **Painel de Manutenção categorizado** (`Regras de Negocio e Fluxos.md §7` e `Rules.md §6`): tabs por categoria, status verde/amarelo/vermelho conforme `uso_atual` vs `proximo_uso`.
- Repositório de documentos vinculáveis (`Rules.md §7`).
- API de sincronização (`/api/sync/manifest`, `/api/sync/push`, `/api/sync/cursor`) com `modulo=<categoria>` no contrato.
- API de catálogo de serviços + planos + qualificações.

### 4.2 PMOC único (`cmasm.erp/pmoc/`)

- Login com credenciais do núcleo (cache de token).
- Seletor de categoria (refrigeração, predial, paióis, transportes, grama, elétrica, calibração).
- Pull periódico do manifest da categoria selecionada (ativos + usuários + estoque + catálogo).
- Criar/listar OS locais.
- Registrar leitura (horímetro/km/data).
- Movimentar estoque local (saída por OS, entrada manual).
- Anexar fotos/documentos a OS.
- Sincronização explícita + automática.
- Status de sync sempre visível.

---

## 5. Requisitos não-funcionais

| Aspecto | Requisito |
|---------|-----------|
| Disponibilidade do núcleo | "Melhor esforço" em LAN do CMASM. Sem SLA de produção. |
| Performance | Páginas do núcleo < 2 s no Chrome desktop. PMOC abre offline em < 1 s após primeiro uso. |
| Backup | Núcleo: backup diário do SQLite (`data/core.db`). PMOC: export JSON manual via UI. |
| Compatibilidade | Chrome 110+ (desktop e Android). Firefox aceitável. |
| Mobile | PMOC deve funcionar em celular Android (≥ 360px). Núcleo pode ser desktop-first. |
| Offline | PMOC: 100% funcional por até 30 dias offline. Núcleo: requer rede (LAN interna basta). |
| Internacionalização | Português do Brasil apenas. |
| Acessibilidade | Alvos de toque ≥ 44px. Contraste AA no tema escuro. |
| Segurança | Auth Bearer. HTTPS recomendado em produção. Hash djb2 no estado atual (a evoluir para argon2). |

---

## 6. Restrições e dependências

- Sem dependência de internet pública para operação normal (CDNs só como fallback, fontes vendored).
- Sem dependência de licenças pagas.
- Equipamento típico: laptops Windows/Linux + celulares Android da Marinha.
- Sem acesso a APIs governamentais externas no MVP.

---

## 7. Roadmap macro

### Curto prazo (3 meses)

1. **Tela Manutenção categorizada no núcleo** (`cmasm_erp.html`): tabs por categoria conforme `Regras §7`, painel verde/amarelo/vermelho.
2. **API de Catálogo** (`/api/catalogo/servicos|planos|qualificacoes`): schema já existe; falta a camada de endpoints.
3. **Fechamento da API de sincronização**: manifest com delta (`since=`), Auth Bearer, teste de integração end-to-end.
4. **Esqueleto do PMOC único** (`cmasm.erp/pmoc/`): shell com seletor de categoria + cliente sync + IndexedDB wrapper + categoria piloto (refrigeração).

### Médio prazo (3–9 meses)

5. Demais categorias do PMOC: predial, paióis, transportes, grama, elétrica, calibração.
6. Painel de saúde de sync no Hub.
7. Backup automatizado e restore.
8. Auth com argon2 + refresh token.

### Longo prazo (9+ meses)

9. RFID/QR no Estoque.
10. Bridge IoT ESP32 → MQTT → `/api/sync/push`.
11. Telemetria de viaturas (GPS, temperatura motor).
12. Bridge CADBEM (importação CSV).
13. PWA do PMOC com service worker.

---

## 8. Decisões registradas

| # | Data | Decisão | Justificativa |
|---|------|---------|---------------|
| 1 | 2026-05-18 | Núcleo cobre usuários, ativos, estoque, OS, manutenção, documentos | Reduzir complexidade do single-file ERP |
| 2 | 2026-05-18 | Cliente de campo é offline-first com IndexedDB | Rede instável em campo |
| 3 | 2026-05-18 | HTML autônomo é o formato preferido para o app de campo | Menor custo de deploy e suporte |
| 4 | 2026-05-18 | Núcleo é fonte da verdade do cadastro mestre | Evita divergência |
| 5 | 2026-05-18 | API de sync com eventos idempotentes (UUID local) | Sync confiável em ambiente com queda |
| 6 | 2026-05-18 | Catálogo de serviços híbrido (central + local) | Consistência + flexibilidade |
| 7 | 2026-05-18 | Motor de geração de OS roda no PMOC offline | Setores trabalham sem rede |
| 8 | 2026-05-18 | Shell de componentes UI padronizado (originário do `pmoc-engine.js`) | Padroniza UX e centraliza correções |
| 9 | 2026-05-18 | OS criada de serviço local carrega snapshot embarcado no push | Histórico íntegro no núcleo |
| 10 | 2026-05-22 | **PMOC único com categorias internas** (substitui "N PMOCs offline-first") | Elimina duplicação de código sync/auth/UI; mantém contrato único; reflete o modelo de domínio (`Regras de Negocio e Fluxos.md`) onde Manutenção é uma tela categorizada |
| 11 | 2026-05-22 | PMOC vive em `cmasm.erp/pmoc/` (mesmo repo do núcleo) | Compartilha assets, deploy e ciclo de vida do núcleo |
| 12 | 2026-05-22 | Repos `pmoc_<dom>` legados a arquivar; `pmoc.refs` permanece como fonte de seeds/referências | Arquitetura nova consolida no app único |
