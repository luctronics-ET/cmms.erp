# Manutenção unificada — refatoração da página `manutencao` no `cmasm_erp.html`

**Data:** 2026-05-19
**Status:** spec aprovado, pendente implementação
**Brainstorm:** sessão de 2026-05-19 (decisões 1-7 abaixo)

---

## 1. Contexto e motivação

O `cmasm_erp.html` atual tem uma página `manutencao` enxuta (66 linhas HTML em meio a 4281 do arquivo monolítico). A arquitetura registrada em `REQUISITOS.md` previa PMOCs offline-first por domínio (refrigeração, elétrica, transportes, paiois etc.) com sincronização periódica para o núcleo.

Reavaliação durante o brainstorm: para a maioria dos casos do CMASM, **o gestor de manutenção (CMASM-13) opera no desktop, online, e precisa ver várias categorias consolidadas**. Os PMOCs offline-first continuam fazendo sentido para operação em campo (paiol, embarcação, garagem com rede ruim), mas o painel central do gestor não precisa daquela complexidade.

A solução é uma **página única no núcleo** que consolida ativos + OS + planos + estoque relevantes às categorias selecionadas. Substitui a `manutencao` atual; PMOCs offline-first ficam como satélites para os domínios que exigem campo.

### Benefícios

- **Estoque unificado**: gestor vê consumo cross-categoria numa tela só.
- **Análise comparativa**: comparar OS abertas em Climatização vs Elétrica sem pular de módulo.
- **Simplicidade de desenvolvimento**: 1 página vs N PMOCs duplicando componentes.
- **Sem complexidade offline**: nada de IndexedDB, sync, conflito — só HTTP direto ao núcleo.

### O que esta refatoração **não** faz

- Não substitui os PMOCs offline-first dos domínios que precisam de campo (decisão deferida).
- Não toca outras páginas do ERP (`servicos`, `ativos`, `estoque`, `usuarios`, `admin`) — elas seguem como estão.
- Não cria endpoints novos no núcleo em V1 (vide §6).

---

## 2. Decisões registradas

| # | Decisão | Por quê |
|---|---|---|
| 1 | Módulo unificado vira **página do núcleo** (não PMOC) | Operação do gestor é online e em desktop; offline-first traz complexidade desnecessária aqui. PMOCs ficam para campo. |
| 2 | É a **refatoração da página `manutencao`** existente | Mantém URL e mental model. Outras páginas (servicos, ativos, estoque) continuam para CRUD pontual. |
| 3 | V1 cobre **painel + configuração + operação** (amplo, profundidade média) | Usuário aceitou risco de raso em troca de cobertura. Refinamentos por aba virão depois. |
| 4 | Filtro de categoria = **multi-select** (chips no topo) | Encarregado de CMASM-13 cuida de várias categorias simultâneas. |
| 5 | Estrutura interna = **tabs horizontais** (padrão da demo PMOC) | Consistência visual com o engine v2 já entregue. |
| 6 | V1 com 8 tabs: Dashboard, Ativos, OS, Planos, Catálogo, Estoque, Calendário+Gantt, Configuração | Cobertura máxima aceita. |
| 7 | **Vertical slice real**: Dashboard+Ativos+OS com API real; Planos+Catálogo+Estoque+Cal+Gantt+Config com mock fiel ao schema | Endpoints `/api/catalogo/*` e `/api/planos/*` ainda não existem; mock evita bloqueio. Wire-up vem depois. |

UX **deve manter compatibilidade visual** com o `cmasm_erp.html` (sidebar, header, paleta, tipografia). O engine v2 já usa as mesmas CSS variables — sem colisão de classes (prefixo `pe-*`).

---

## 3. Arquitetura

```
cmasm_erp.html  (shell existente: sidebar + header + container de páginas)
└── page-manutencao  (refatorada)
    ├── Topo fixo
    │   ├── Filtro multi-select de categorias (chips)
    │   ├── Botão ↻ refetch manual
    │   └── Ações: [+ Plano] [+ OS]
    ├── Barra de tabs (engine v2 tabBar)
    └── Conteúdo da tab ativa
        ├─ Dashboard    [REAL]    KPIs · donut · line · alertas
        ├─ Ativos       [REAL]    tabela com filtros + drawer detalhe
        ├─ OS           [REAL]    kanban (DnD → PUT status) + toggle lista
        ├─ Planos       [MOCK]    tabela + simulação de carga
        ├─ Catálogo     [MOCK]    lista de serviços + POPs
        ├─ Estoque      [PARCIAL] saldo real, filtro de relevância mock
        ├─ Cal+Gantt    [MOCK]    toggle de view + DnD
        └─ Config       [MOCK]    criticidade + qualificações
```

### Decisões estruturais

1. **Onde mora**: conteúdo extraído para 2 arquivos: `assets/erp-manutencao.js` (~600-800 linhas: lógica e renderização) + `assets/erp-manutencao-mocks.js` (~200 linhas: consts mock para Planos/Catálogo/Estoque-filtro/Cal+Gantt/Config). Ambos carregados via `<script>` no `cmasm_erp.html`. O `<div id="page-manutencao">` fica vazio e é populado pelo JS no boot da page. Separar mocks facilita a substituição quando `/api/catalogo/*` e `/api/planos/*` forem criados.
2. **CSS**: incluir `assets/pmoc-engine.css` no `<head>` do `cmasm_erp.html`. Convive com classes existentes (prefixo `pe-*` evita colisão).
3. **Engine**: incluir `assets/pmoc-engine.js`. Acessível via `window.engine`.
4. **APIs reais**: `/api/ativos`, `/api/os`, `/api/estoque` (já existem). Catálogo/Planos/Config em objetos mock locais com **shape idêntico** ao schema do backend (`data/schema_catalogo.sql`) para facilitar wire-up posterior.

---

## 4. Componentes

### 4.1 Topo fixo (sticky)

```
┌────────────────────────────────────────────────────────────────────┐
│ Manutenção                                       [+ Plano] [+ OS]  │
│ Categorias: (●Climatização) (○Frota terr.) (●Elétrica) (○Predial)  │
│             (○Frota naval)  (○Máq. corte)  (○Outros)   [Tudo] [↻]  │
└────────────────────────────────────────────────────────────────────┘
```

- Chips clicáveis, multi-select. "Tudo" desmarca todos (= sem filtro).
- Seleção persiste em `localStorage` (`xerp_manut_cats`) + querystring `?cats=climatizacao,eletrica` para deep-link.
- Lista de categorias derivada de `SELECT DISTINCT categoria FROM ativos WHERE ativo=1`.
- Botão ↻ força refetch manual de todas as tabelas reais.

### 4.2 Detalhe de cada aba

#### Dashboard
- 4 cards KPI: `Vencidos · Próx. 30d · OS abertas · Estoque baixo` (números refletem o filtro)
- `engine.chartDonut` — "OS por status" (filtrado)
- `engine.chartLine` — "Concluídas/mês (últimos 12m)" (filtrado)
- Lista vertical "Alertas críticos": ativos vencidos + estoque crítico + qualificações vencendo (limite 10 itens; "ver mais" leva à aba relevante)

#### Ativos
- `engine.table` com colunas: nome · tipo · categoria · criticidade (badge colorido) · uso_atual · próximo_servico (calculado) · status (badge)
- Click em linha → `engine.modal` (drawer) com 3 sub-abas: **Dados · Planos · Histórico OS**

#### OS
- Toggle no canto: `[Kanban] [Lista]`
- Kanban (`engine.kanban`): 8 colunas (status canônicos de `Rules.md §4`)
- Cards: titulo + badges de tipo + criticidade do ativo + dias-até-vencimento
- DnD entre colunas → `PUT /api/os/{id}/status` com `obs="movido via painel"`
- Click no card → modal de detalhe + thread de chat (mock em V1)

#### Planos (MOCK)
- `engine.table`: serviço · ativo/tipo · frequência (resolvida por criticidade) · próxima execução · ativo (toggle on/off)
- Botão `[Simular]` → modal com cálculo de carga prevista para os próximos 90 dias (qtd de OS, horas-homem, materiais agregados)

#### Catálogo (MOCK)
- `engine.table`: código · nome · escopo (central/local) · versão · tempo_estimado
- Click → drawer com materiais, ferramentas, pessoal, condicionais, POP vinculado (link p/ documento)

#### Estoque (PARCIAL — saldo real)
- `engine.table`: código · nome · categoria · qtd_atual · qtd_minima · status (badge ok/baixo/crítico)
- Saldos vêm de `GET /api/estoque`. Filtro de relevância às categorias selecionadas é mock em V1: lista hardcoded por categoria (ex: "climatização" puxa `GAS-R410A`, `FIL-AC-*`, etc.).

#### Calendário+Gantt (MOCK)
- Toggle `[📅 Calendário] [📈 Gantt]`
- Eventos = próximas execuções de planos
- DnD reagenda eventos (V1: só state local — não persiste)

#### Configuração (MOCK)
- Sub-abas: **Criticidade dos ativos** · **Qualificações do pessoal**
- Cada uma é tabela editável (inline ou via modal)
- V1: edições só em state local — não persistem

---

## 5. Data flow

### 5.1 Carregamento inicial

```
1. cmasm_erp.html → showPage('manutencao')
2. erp-manutencao.js boot():
   ├─ lê filtro persistido (localStorage + URL params)
   ├─ Promise.all:
   │   ├─ GET /api/ativos
   │   ├─ GET /api/os
   │   └─ GET /api/estoque
   ├─ deriva: lista de categorias disponíveis, KPIs, séries de gráfico
   └─ renderiza topo (chips) + tab Dashboard ativa
```

### 5.2 Mudança de filtro

```
filtro muda
  → grava localStorage + atualiza URL (history.replaceState)
  → dispara evento 'manut:filter-change' no document
  → tab ativa escuta e re-renderiza com state filtrado
  → outras tabs ficam "dirty" → re-renderizam ao serem ativadas
```

Filtro é client-side; não há refetch (dados em memória). Premissa: < 5k ativos no CMASM (verdadeiro hoje).

### 5.3 Mudança de tab

```
click em tab
  → marca tab como ativa
  → se dirty: renderTab(tabId)
  → senão: deixa DOM cacheado
```

### 5.4 Ações de escrita

| Ação | Endpoint | Após resposta |
|---|---|---|
| Drag de card no kanban | `PUT /api/os/{id}/status` | Refetch só desta OS + atualiza card |
| Concluir OS no modal | `PUT /api/os/{id}/status` → `concluida` | Refetch OS + invalida Dashboard (KPIs mudam) |
| Cancelar OS | `PUT /api/os/{id}/status` com `obs` (motivo via `engine.confirm({requireReason:true})`) | Idem concluir |
| Toggle plano on/off (V1 mock) | Só state local | — |
| Reagendar no calendário (V1 mock) | Só state local | — |

### 5.5 Cache em memória

```js
const cache = {
  ativos:   { data: [], ts: null },
  os:       { data: [], ts: null },
  estoque:  { data: [], ts: null },
  // mocks: consts no arquivo
};
```

Sem TTL — refresh manual pelo botão ↻.

---

## 6. Error handling

### 6.1 Falhas de rede (GET)

| Cenário | Comportamento |
|---|---|
| Carga inicial falha (cache vazio) | Banner vermelho sticky: `⛔ Sem conexão com o núcleo · [Tentar novamente]`. Tabs mostram skeleton/empty state. |
| Refetch falha (já há cache) | Banner amarelo: `⚠ Última atualização há Xmin · [Tentar novamente]`. Dados em cache continuam visíveis com badge `⏱ desatualizado` em cada tabela. |
| 4xx (ex: 401 token expirado) | `engine.confirm` propondo re-login. Sem retry automático. |

### 6.2 Falhas de escrita (PUT)

| Cenário | Comportamento |
|---|---|
| `PUT /api/os/{id}/status` falha (kanban DnD) | Card volta à coluna original. Toast vermelho: `Falha ao mover OS-XXX: <motivo>. Tente novamente.` |
| Validação rejeita (400) | Mostra `detail` da resposta no toast. Ex: "OS já concluída — não pode voltar para 'iniciada'". |
| Conflito (409) | Toast + força refetch da OS individual. Card pode aparecer em outra coluna se outro operador mexeu. |

### 6.3 Estados vazios

- Filtro selecionado mas sem ativos → ilustração + texto + botão `[Limpar filtros]`
- Catálogo sem entradas → `Catálogo ainda não tem serviços · [+ Criar primeiro serviço]` (V1: botão disabled com tooltip "Em breve")
- Configuração / qualificações vazias → similar

### 6.4 Validações de cliente (antes de POST/PUT)

- Drag no kanban entre status **não-canônicos** (ex: `concluida → aberta`) → toast vermelho + reverte sem chamar API. Tabela de transições permitidas embarcada no JS (espelha o ciclo de vida em `Rules.md §4`).
- Modal de cancelamento sem motivo → input destacado, botão "OK" disabled.

### 6.5 Telemetria

`console.warn` com `{endpoint, status, payload}`. Sem analytics externos.

---

## 7. Testing

### 7.1 Backend (TDD)

Endpoints reusados (`/api/ativos`, `/api/os`, `/api/estoque`) já têm cobertura indireta via `tests/test_sync*.py`. Nada novo a fazer nesta V1.

Quando `/api/catalogo/*` e `/api/planos/*` forem criados (pós-V1), virão com testes TDD seguindo o padrão de `tests/test_sync.py`.

### 7.2 Frontend (V1 manual + smoke)

V1 está em arquivo único — testes E2E completos são exagero. Estratégia:

1. **Smoke test** (`tests/test_manutencao_smoke.py`):
   - TestClient já existente
   - `GET /cmasm_erp.html` retorna 200 e referencia `erp-manutencao.js`
   - Roda parser de balanço de chaves em `erp-manutencao.js` (técnica já usada em `pmoc-engine.js`) → 0 erros

2. **Roteiro manual de aceite** (documentado neste spec, §7.4):

3. **Playwright (deferred)** — registrado em `todo.md`. 4-5 cenários quando o stack estabilizar.

### 7.3 Critérios de "pronto" para V1

1. Filtro de categorias persiste entre reloads e refilra todas as tabs ativas.
2. Dashboard mostra KPIs reais do `core.db`.
3. Tab Ativos lista, busca, filtra, ordena, pagina.
4. Tab OS mostra kanban; DnD altera status no backend; reverte em falha.
5. Tabs Planos/Catálogo/Estoque/Cal+Gantt/Config renderizam com mock fiel ao schema.
6. Sem 4xx/5xx no console em uso normal.
7. Funciona em Chrome 110+ (desktop) e Chrome Android (≥ 360px largura).

### 7.4 Roteiro manual de aceite (V1)

| # | Cenário | Esperado |
|---|---|---|
| 1 | Aplicar filtro de 2 categorias | Dashboard, Ativos, OS, Estoque refiltram. URL atualiza com `?cats=...`. Reload preserva. |
| 2 | Limpar filtro com "Tudo" | Tudo volta a mostrar dados consolidados. localStorage limpa. |
| 3 | Drag card no Kanban (`aberta → iniciada`) | Card muda de coluna. `PUT /api/os/{id}/status` chamado. DB confirma. |
| 4 | Drag inválido (`concluida → aberta`) | Card reverte. Toast vermelho. Sem chamada à API. |
| 5 | Cancelar OS sem motivo | Botão "OK" disabled. Input destacado. |
| 6 | Cancelar OS com motivo | `PUT /api/os/{id}/status` com `obs`. Card sai do kanban. |
| 7 | Parar uvicorn e tentar refetch | Banner vermelho. Cache anterior visível com badge desatualizado. |
| 8 | Click em linha de Ativo | Modal abre com sub-abas Dados/Planos/Histórico. |
| 9 | Tab Calendário → arrastar evento | Evento muda de dia (state local). |
| 10 | Toggle Calendário ↔ Gantt | Conteúdo da aba alterna mantendo dados. |

---

## 8. Pendências e próximos passos (pós-V1)

- Implementar `GET/POST/PUT /api/catalogo/servicos`, `GET/POST/PUT /api/planos/manutencao` (com TDD)
- Plugar Planos, Catálogo e Configuração na API real
- Reagendamento no calendário/gantt deve persistir (`PUT /api/planos/{id}`)
- Toggle on/off de plano deve persistir
- Cenários Playwright (§7.2.3)
- Decisão sobre fate dos PMOCs offline-first (manter todos? Só alguns? Quais?) — escopo separado

---

## 9. Riscos identificados

| Risco | Mitigação |
|---|---|
| 8 tabs em V1 = raso em tudo | Aceito explicitamente. Cada aba ganha profundidade em iterações dedicadas. |
| Mock de Planos/Catálogo divergir do schema | Mocks vivem em const com shape idêntico ao DDL de `data/schema_catalogo.sql`. Revisar a cada mudança de schema. |
| `cmasm_erp.html` (4281 linhas) fica mais difícil de manter ao adicionar `<script src>` | Extrair a JS para arquivo dedicado já é melhoria — reduz o monolito. Padrão pode ser replicado para outras pages no futuro. |
| Performance com muitos ativos | Premissa < 5k. Caso evolua: paginação server-side + filtros via querystring. |
| PMOCs offline-first agora ficam órfãos | Decisão deferida para outro brainstorm. Não bloqueia esta refatoração. |

---

## 10. Arquivos a criar/modificar

| Arquivo | Ação | Notas |
|---|---|---|
| `assets/erp-manutencao.js` | criar | Conteúdo da página, ~600-800 linhas |
| `assets/erp-manutencao-mocks.js` | criar | Constantes de mock para Planos/Catálogo/Config (separar facilita revisar) |
| `cmasm_erp.html` | editar | Incluir `pmoc-engine.css`, `pmoc-engine.js`, `erp-manutencao*.js`. Esvaziar `<div id="page-manutencao">` para ser populado pelo JS. |
| `tests/test_manutencao_smoke.py` | criar | Smoke test (sintaxe + carga da página) |
| `todo.md` | editar | Marcar V1 como em andamento; registrar pendências do §8 |

---

**Próximo passo:** invocar `writing-plans` para gerar o plano de implementação detalhado, seguindo TDD para cada parte que envolve backend e smoke test para o front.
