---
title: Esqueleto do PMOC único — 4 categorias com dados reais
date: 2026-05-22
status: aprovado
autor: luciano
spec_pai: 2026-05-22-pmoc-unificado-design.md
---

# Esqueleto do PMOC único — 4 categorias com dados reais

## 1. Contexto

A consolidação arquitetural (spec `2026-05-22-pmoc-unificado-design.md`) definiu que o PMOC é **um único app de campo** offline-first em `cmasm.erp/pmoc/`, com categorias internas. Esta spec descreve a **primeira entrega real** desse app, contendo 4 categorias com dados reais já cadastrados no núcleo.

Modelo visual de referência: `.archive_pmoc_legado/pmoc_refrigeracao/refrigeracao.html` (v8.9, single-file, 2619 linhas). Layout aproveitado e generalizado para múltiplas categorias; CSS e JS **extraídos** em arquivos separados para manutenibilidade.

## 2. Escopo

### 2.1 Categorias da primeira entrega

| Categoria PMOC | `categoria` no DB | Fonte de dados | Unidade |
|---|---|---|---|
| refrigeracao | `climatizacao` | `tools/seed_ativos.py` (u40-u43) + CSV de 171 ativos | meses / horas |
| maq_corte | `maquinas_corte` | `seed_ativos.py` (u01-u12) | h |
| viaturas | `viaturas` | `seed_ativos.py` (vtr01-vtr10) | km ou h |
| embarcacoes | `embarcacoes` | `seed_ativos.py` (emb01-emb03) | h |

Demais categorias (predial, paióis, elétrica, calibração) ficam para entregas futuras.

### 2.2 Fora do escopo desta entrega

- Motor de planos completo (`avaliarCondicionais`, janelas de manutenção). Versão mínima: alerta visual quando `uso_atual ≥ proximo_uso`, sem geração automática de PS.
- Hierarquia PS / NEC / SR. Esta entrega registra apenas `os_criada`, `os_status`, `uso_atual_inc`, `estoque_mov`.
- Chat dentro da OS — visualização somente, sem envio.
- Camera/foto — `<input type="file">` simples; sem captura nativa MediaDevices.
- PWA, service worker.
- Auth argon2 (segue djb2 enquanto não migrar no núcleo).

## 3. Estrutura de arquivos

```
cmasm.erp/pmoc/
├── index.html              # shell — HTML mínimo, refs a assets/
├── assets/
│   ├── pmoc.css            # tema dark + layout (extraído/adaptado de refrigeracao v8.9)
│   └── pmoc.js             # lógica completa do app
├── seeds/
│   ├── ativos.json
│   ├── locais.json
│   ├── estoque-catalogo.json
│   ├── planos.json
│   └── refrigeracao-detalhe.json
└── tools/
    └── gen_seeds.py        # gerador idempotente de seeds
```

## 4. Layout UI

Mantém o esqueleto visual do `refrigeracao.html` v8.9, generalizado:

```
┌────────────────────────────────────────────────────────────────────────┐
│ HEADER: logo · usuário · sync-status (último, pendentes) · btn Sinc.   │
├─────────────┬──────────────────────────────────────────────────────────┤
│             │ TOOLBAR: busca · filtros · "+ OS" · "+ Leitura"          │
│ SIDEBAR     ├──────────────────────────────────────────────────────────┤
│             │                                                          │
│ Categorias  │   LISTA DE ATIVOS (tabela, colunas por categoria)        │
│ ❄ Refrig.   │     status 🟢/🟡/🔴 conforme uso_atual vs proximo_uso     │
│ 🔧 Máq.Corte│                                                          │
│ 🚗 Viaturas │                                                          │
│ ⛵ Embarc.  │                                                          │
│             ├──────────────────────────────────────────────────────────┤
│ Filtros     │  DETAIL PANEL (slide-in à direita)                       │
│  - Local    │   Tabs: Geral · Histórico OS · Manutenção · Docs         │
│  - Status   │   Ações: "Nova OS" · "Registrar leitura" · "Anexar"      │
│  - Critic.  │                                                          │
└─────────────┴──────────────────────────────────────────────────────────┘
```

### 4.1 Tema visual

Tema dark obrigatório, paleta do núcleo:

```
--bg: #07111f   --bg2: #0d1e33   --bg3: #0a1828
--panel: #0f2035   --acc: #00b4d8
--green: #22c55e   --red: #ef4444   --amber: #f59e0b
```

Fontes self-hosted: DM Sans (UI) + JetBrains Mono (dados/código). Importadas de `/assets/fonts.css` do núcleo.

## 5. Configuração de categoria (declarativa)

Estrutura em `pmoc.js`:

```js
const CATEGORIAS = {
  refrigeracao: {
    label: 'Refrigeração', emoji: '❄️', cor: '#00b4d8',
    categoria_db: 'climatizacao',
    unidade_uso: 'meses',
    colunas_tabela: ['nome', 'local', 'btu', 'gas', 'criticidade', 'status'],
    campos_detalhe: ['btu', 'gas', 'carga_g', 'pressao_padrao', 'temperatura_evap'],
    modulo_sync: 'refrigeracao',
  },
  maq_corte: {
    label: 'Máq. de corte', emoji: '🔧', cor: '#f59e0b',
    categoria_db: 'maquinas_corte',
    unidade_uso: 'h',
    colunas_tabela: ['nome', 'tipo', 'local', 'uso_atual', 'status'],
    campos_detalhe: ['tipo', 'patrimonio', 'obs'],
    modulo_sync: 'maq_corte',
  },
  viaturas: {
    label: 'Viaturas', emoji: '🚗', cor: '#22c55e',
    categoria_db: 'viaturas',
    unidade_uso: 'km',
    colunas_tabela: ['nome', 'placa', 'subtipo', 'local', 'uso_atual', 'status'],
    campos_detalhe: ['placa', 'subtipo', 'obs'],
    modulo_sync: 'viaturas',
  },
  embarcacoes: {
    label: 'Embarcações', emoji: '⛵', cor: '#3b82f6',
    categoria_db: 'embarcacoes',
    unidade_uso: 'h',
    colunas_tabela: ['nome', 'placa', 'subtipo', 'local', 'uso_atual', 'status'],
    campos_detalhe: ['placa', 'subtipo', 'obs'],
    modulo_sync: 'embarcacoes',
  },
};
```

Adicionar categoria nova = entrada nesse objeto + seed JSON correspondente.

## 6. IndexedDB

Database `pmoc_v1`. Stores:

| Store | Key | Conteúdo |
|---|---|---|
| `ativos` | `id` | Cadastro mestre, todas as categorias |
| `locais` | `id` | Locais do núcleo |
| `catalogo_servicos` | `id` | Serviços central + locais |
| `planos_manutencao` | `id` | Planos por tipo/ativo |
| `estoque_catalogo` | `id` | Materiais |
| `eventos_pendentes` | `id` | Fila de push: `{id, tipo, payload, ts, tentativas}` |
| `eventos_aceitos` | `id` | Auditoria local |
| `config` | `chave` | `device_id`, `token`, `last_cursor`, `last_sync`, `categoria_ativa`, `seed_source` |

## 7. Boot híbrido (seed + sync)

```
boot:
  1. abre IndexedDB pmoc_v1
  2. se store `ativos` vazio:
       a. tenta pull /api/sync/manifest?modulo=<cat> para cada categoria
       b. se sucesso: hidrata stores, marca config.seed_source = 'nucleo'
       c. se falha (rede/auth): hidrata de pmoc/seeds/*.json,
          marca config.seed_source = 'local', mostra banner amarelo
     senão (já populado):
       a. tenta sync incremental com since=config.last_sync
       b. ignora silenciosamente se offline; mantém estado atual
  3. renderiza categoria ativa (default refrigeracao ou config.categoria_ativa)
```

## 8. Sync com o núcleo

Cada categoria sincroniza independentemente usando `modulo=<categoria>` no contrato existente:

| Direção | Endpoint | Carga |
|---|---|---|
| Pull | `GET /api/sync/manifest?modulo=<cat>&since=<iso>` | Ativos, locais, catálogo, planos da categoria |
| Push | `POST /api/sync/push` | Eventos da fila local |
| Cursor | `GET /api/sync/cursor?modulo=<cat>&device=<>` | Retomada após queda |

### 8.1 Eventos emitidos nesta entrega

| Evento | Quando |
|---|---|
| `uso_atual_inc` | Operador registra leitura (km/h) |
| `os_criada` | Operador cria OS corretiva ou inspeção |
| `os_status` | Mudança de status (aberta → em_execucao → pronto → concluida) |
| `estoque_mov` | Saída/entrada manual de material |
| `documento_anexo` | Upload de arquivo a uma OS |

Demais eventos (`ps_criada`, `inspecao_concluida`, `plano_adiado`, `qualificacao_uso`) ficam para fase do motor de planos.

## 9. Auth (modo dev vs produção)

### Modo dev (sem rede ou núcleo indisponível)

- Tela de login mostra botão "Continuar offline (modo dev)".
- Usuário fictício: `{ id: 'dev', nome: 'operador.dev', lotacao: 'dev' }`.
- Banner amarelo visível: "Modo dev — sem sincronização com núcleo".
- Eventos ficam acumulados em `eventos_pendentes` (não são enviados).

### Produção (LAN do CMASM)

- Login via `POST /api/auth/login` com matrícula + senha.
- Token Bearer cacheado em `config.token`.
- Re-login forçado quando token expira (mantém eventos pendentes).

## 10. Geração de seeds

Script `pmoc/tools/gen_seeds.py`:

1. Importa lista `ATIVOS` de `tools/seed_ativos.py` e exporta `seeds/ativos.json` filtrando por `categoria ∈ {climatizacao, maquinas_corte, viaturas, embarcacoes}`.
2. Lê `pmoc.refs/CMASM_PMOC_REFRIG - CMASM_PMOC_REFRI.csv` (171 linhas) → `seeds/refrigeracao-detalhe.json` (com BTU, gás, criticidade, carga, pressão, temperatura).
3. Lê `pmoc.refs/pmoc_maq-agricola_dados.csv` (32 linhas) → catálogo de peças/intervalos para máquinas de corte.
4. Extrai planos básicos da tabela em `Regras de Negocio e Fluxos.md §3` (GAR 50h, SOL 50h, VTR_PICKUP 5000km, EMB_LANCHA 50h, GERADOR 250h, AC_SPLIT 1mês/12meses) → `seeds/planos.json`.
5. Locais e estoque-catálogo derivados das mesmas fontes.

Rodado uma vez agora; idempotente (regerar quando seeds mudarem).

## 11. Servir via FastAPI

`backend/main.py` adiciona após os outros mounts:

```python
from fastapi.staticfiles import StaticFiles
app.mount("/pmoc", StaticFiles(directory="pmoc", html=True), name="pmoc")
```

URL: `http://localhost:8010/pmoc/`. Também abre via `file:///cmasm.erp/pmoc/index.html` para uso offline puro.

## 12. Critério de aceitação

- [ ] `/pmoc/` abre e mostra a sidebar com 4 categorias.
- [ ] Em modo dev (sem núcleo), seeds locais hidratam IndexedDB e mostram dados reais.
- [ ] Em modo produção, primeiro boot puxa do `/api/sync/manifest` para cada categoria.
- [ ] Refrigeração mostra colunas específicas (BTU, gás, criticidade) com dados do CSV.
- [ ] Viaturas mostram placa e subtipo (`vtr_int` / `vtr_ext`).
- [ ] Embarcações mostram subtipo (`emb_rot` / `emb_pat`).
- [ ] Detail panel abre ao clicar ativo, com 4 tabs.
- [ ] Botão "Registrar leitura" gera evento `uso_atual_inc` na fila.
- [ ] Botão "Nova OS" gera evento `os_criada` na fila.
- [ ] Header mostra contador de eventos pendentes.
- [ ] Botão Sincronizar empilha eventos no `/api/sync/push` quando online; falha silenciosa quando offline.
- [ ] Recarregar a página preserva estado (IndexedDB).
- [ ] Banner amarelo visível em modo dev.

## 13. Próximos passos (após esta entrega)

1. Motor de planos completo (`avaliarCondicionais`, `verificarRecursos`, geração automática de PS).
2. Categorias adicionais: predial, paióis, elétrica, calibração.
3. PS / NEC / SR completos.
4. Chat + camera (MediaDevices).
5. PWA + service worker.
6. Migração para Auth Bearer com token de produção.
