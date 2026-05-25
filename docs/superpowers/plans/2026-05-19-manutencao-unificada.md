# Manutenção Unificada — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Spec:** `docs/superpowers/specs/2026-05-19-manutencao-unificada-design.md`

**Goal:** Refatorar a página `manutencao` do `cmasm_erp.html` em um módulo unificado que consolida ativos, OS, planos, catálogo, estoque e configuração com filtro multi-select por categoria.

**Architecture:** Página única online dentro do shell existente do `cmasm_erp.html`. Conteúdo extraído para `assets/erp-manutencao.js` (lógica + render) + `assets/erp-manutencao-mocks.js` (consts mock). Usa componentes do `pmoc-engine.js` v2. Vertical slice real: Dashboard, Ativos e OS consomem `/api/ativos`, `/api/os`, `/api/estoque` (já prontos). Planos, Catálogo, Cal+Gantt, Config ficam com mock fiel ao schema; Estoque combina saldo real com filtro de relevância mock.

**Tech Stack:** HTML + vanilla JS (sem build step). Backend: FastAPI + aiosqlite (já operacional). Testes: pytest + TestClient (smoke). Validação de sintaxe JS: parser de balanço de chaves em Python (padrão já usado para `pmoc-engine.js`).

---

## File Structure

| Arquivo | Ação | Responsabilidade |
|---|---|---|
| `assets/erp-manutencao-mocks.js` | Criar | Constantes mock para Planos, Catálogo, Estoque-filtro-relevância, Cal+Gantt, Configuração. Sem lógica. |
| `assets/erp-manutencao.js` | Criar | Boot, filtro de categorias, tab bar, renderers por aba, integração com APIs reais e mocks. |
| `cmasm_erp.html` | Modificar | (1) incluir `pmoc-engine.css`/`pmoc-engine.js`/`erp-manutencao-mocks.js`/`erp-manutencao.js`; (2) esvaziar conteúdo da `<div id="page-manutencao">` deixando só o mount point. |
| `tests/test_manutencao_smoke.py` | Criar | Smoke tests: ERP referencia os 4 arquivos; sintaxe JS balanceada. |
| `todo.md` | Modificar | Marcar V1 concluído + registrar pendências do spec §8. |

Notas:
- O `cmasm_erp.html` tem ~4281 linhas. Quaisquer mudanças usam **search-and-replace** por padrões estáveis (não números de linha frágeis).
- A página `page-manutencao` original ocupa linhas 932-998 do `cmasm_erp.html` (verificado em 2026-05-19). Manter o `<div>` raiz; substituir só o conteúdo interno.

---

## Task 1: Smoke tests + inclusão de assets no shell

Define a base: o `cmasm_erp.html` precisa carregar `pmoc-engine.css`/`pmoc-engine.js` e os dois novos arquivos JS. Os arquivos ainda não existem — vamos criar stubs vazios apenas para o smoke passar.

**Files:**
- Create: `tests/test_manutencao_smoke.py`
- Create: `assets/erp-manutencao.js` (stub vazio)
- Create: `assets/erp-manutencao-mocks.js` (stub vazio)
- Modify: `cmasm_erp.html` (incluir links/scripts)

- [ ] **Step 1.1: Criar o smoke test**

Conteúdo de `tests/test_manutencao_smoke.py`:

```python
"""Smoke tests para a refatoração da página manutencao."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# ──────────────────────── verificações no cmasm_erp.html ────────────────────────

def _erp_html() -> str:
    return (ROOT / "cmasm_erp.html").read_text(encoding="utf-8")


def test_erp_inclui_pmoc_engine_css():
    assert 'assets/pmoc-engine.css' in _erp_html()


def test_erp_inclui_pmoc_engine_js():
    assert 'assets/pmoc-engine.js' in _erp_html()


def test_erp_inclui_erp_manutencao_mocks_js():
    assert 'assets/erp-manutencao-mocks.js' in _erp_html()


def test_erp_inclui_erp_manutencao_js():
    assert 'assets/erp-manutencao.js' in _erp_html()


# ──────────────────── verificações de sintaxe nos JS ─────────────────────

def _check_braces(path: Path) -> tuple[dict[str, int], list[tuple[int, str]]]:
    """Verifica balanço de chaves/parênteses/colchetes ignorando strings e comentários.
    Retorna (depth_final, erros). Tudo zerado e sem erros = sintaticamente plausível."""
    src = path.read_text(encoding="utf-8")
    depth = {"{": 0, "(": 0, "[": 0}
    inv = {"}": "{", ")": "(", "]": "["}
    state = "code"  # code | line_cmt | blk_cmt | dq | sq | tq
    errors: list[tuple[int, str]] = []
    line = 1
    i = 0
    while i < len(src):
        c = src[i]
        nx = src[i + 1] if i + 1 < len(src) else ""
        if c == "\n":
            line += 1
        if state == "code":
            if c == "/" and nx == "/": state = "line_cmt"; i += 2; continue
            if c == "/" and nx == "*": state = "blk_cmt";  i += 2; continue
            if c == '"': state = "dq"
            elif c == "'": state = "sq"
            elif c == "`": state = "tq"
            elif c in "{([": depth[c] += 1
            elif c in "})]":
                o = inv[c]
                depth[o] -= 1
                if depth[o] < 0:
                    errors.append((line, c))
        elif state == "line_cmt":
            if c == "\n": state = "code"
        elif state == "blk_cmt":
            if c == "*" and nx == "/": state = "code"; i += 2; continue
        elif state == "dq":
            if c == "\\": i += 2; continue
            if c == '"': state = "code"
        elif state == "sq":
            if c == "\\": i += 2; continue
            if c == "'": state = "code"
        elif state == "tq":
            if c == "\\": i += 2; continue
            if c == "`": state = "code"
        i += 1
    return depth, errors


def test_erp_manutencao_js_sintaxe_balanceada():
    depth, errors = _check_braces(ROOT / "assets/erp-manutencao.js")
    assert errors == [], f"chaves não-balanceadas: {errors[:5]}"
    assert all(v == 0 for v in depth.values()), f"saldo final: {depth}"


def test_erp_manutencao_mocks_js_sintaxe_balanceada():
    depth, errors = _check_braces(ROOT / "assets/erp-manutencao-mocks.js")
    assert errors == [], f"chaves não-balanceadas: {errors[:5]}"
    assert all(v == 0 for v in depth.values()), f"saldo final: {depth}"
```

- [ ] **Step 1.2: Rodar o smoke test e confirmar que falha**

Run: `PYTHONPATH=. .venv/bin/pytest tests/test_manutencao_smoke.py -v`

Expected: 6 tests FAIL — os 4 primeiros por falta dos imports no HTML, os 2 últimos por arquivo inexistente (FileNotFoundError).

- [ ] **Step 1.3: Criar stubs vazios dos JS**

Conteúdo de `assets/erp-manutencao-mocks.js`:

```js
/**
 * Mocks fiéis ao schema para Planos / Catálogo / Estoque-filtro / Cal+Gantt / Configuração.
 * (preenchido na Task 2)
 */
window.ERP_MANUT_MOCKS = {};
```

Conteúdo de `assets/erp-manutencao.js`:

```js
/**
 * Módulo da página `manutencao` no cmasm_erp.html — refatoração V1.
 * Spec: docs/superpowers/specs/2026-05-19-manutencao-unificada-design.md
 * (preenchido nas Tasks 3-15)
 */
(function () {
  'use strict';
  // boot vazio — populated na Task 3
})();
```

- [ ] **Step 1.4: Adicionar links/scripts ao `cmasm_erp.html`**

Adicione **logo após** a linha `<link rel="stylesheet" href="assets/fonts.css">` (linha 5):

```html
<link rel="stylesheet" href="assets/pmoc-engine.css">
```

Adicione **logo antes** da linha 4275 (`<body>` do fallback noscript) — você encontra essa posição buscando pela última ocorrência de `</script>` antes do segundo `<body>`. Os scripts devem ficar nessa ordem:

```html
<script src="assets/pmoc-engine.js" defer></script>
<script src="assets/erp-manutencao-mocks.js" defer></script>
<script src="assets/erp-manutencao.js" defer></script>
```

- [ ] **Step 1.5: Rodar o smoke test e confirmar que passa**

Run: `PYTHONPATH=. .venv/bin/pytest tests/test_manutencao_smoke.py -v`

Expected: `6 passed`

- [ ] **Step 1.6: Commit**

```bash
git add tests/test_manutencao_smoke.py assets/erp-manutencao.js assets/erp-manutencao-mocks.js cmasm_erp.html
git commit -m "$(cat <<'EOF'
feat(manut): smoke tests + inclusão de pmoc-engine no cmasm_erp.html

Stubs vazios para erp-manutencao.js e erp-manutencao-mocks.js,
e 6 smoke tests (4 de referência + 2 de sintaxe balanceada).
EOF
)"
```

---

## Task 2: Mocks completos com shape do schema

Preenche `erp-manutencao-mocks.js` com dados mock fiéis a `data/schema_catalogo.sql` para Planos, Catálogo, Estoque-filtro-relevância, Cal+Gantt e Configuração.

**Files:**
- Modify: `assets/erp-manutencao-mocks.js`

- [ ] **Step 2.1: Substituir o stub pelos mocks completos**

Conteúdo completo de `assets/erp-manutencao-mocks.js`:

```js
/**
 * Mocks fiéis ao schema para Planos / Catálogo / Estoque-filtro / Cal+Gantt / Configuração.
 * Shape espelha data/schema_catalogo.sql para facilitar substituição por API real.
 *
 * Quando /api/catalogo/* e /api/planos/* existirem, esses consts são removidos e
 * `erp-manutencao.js` faz fetch direto.
 */
(function () {
  'use strict';

  const today = new Date();
  const iso = d => new Date(d).toISOString().slice(0, 10);
  const plusD = n => iso(new Date(today.getTime() + n * 86400000));

  window.ERP_MANUT_MOCKS = {

    // shape: catalogo_servicos + sub-tables agrupadas em arrays
    catalogo_servicos: [
      {
        id: 'svc-limp-split-padrao',
        codigo: 'LIMP_SPLIT_PADRAO',
        nome: 'Limpeza padrão split 9k–18k BTU',
        descricao: 'Limpeza completa: filtro, evaporadora, condensadora.',
        escopo: 'central', versao: 2,
        pop_doc_id: 'doc-pop-limp-split-v2',
        tempo_estimado_min: 90,
        servico_pai_id: null,
        aplicavel_a: { categorias: ['climatizacao'], tipos: ['AC_SPLIT'] },
        criado_por_modulo: 'manutencao', ativo: 1,
        materiais: [
          { material_id: null, nome_livre: 'Detergente neutro', qtd: 1, unidade: 'L', obrigatorio: 1 },
          { material_id: null, nome_livre: 'Spray bactericida', qtd: 0.3, unidade: 'L', obrigatorio: 0 },
        ],
        ferramentas: [
          { nome: 'Hidrojateamento de baixa pressão', qtd: 1, obrigatorio: 1 },
          { nome: 'Bomba bag', qtd: 1, obrigatorio: 1 },
        ],
        pessoal: [{ qualificacao_codigo: 'tec_refrig', qtd: 1, opcional: 0 }],
        condicionais: [{ expressao: 'energia.ativa == true', bloqueante: 1 }],
      },
      {
        id: 'svc-recarga-r410a',
        codigo: 'RECARGA_R410A',
        nome: 'Recarga de gás R-410A',
        escopo: 'central', versao: 1, tempo_estimado_min: 60,
        aplicavel_a: { categorias: ['climatizacao'] },
        criado_por_modulo: 'manutencao', ativo: 1,
        materiais: [{ material_id: null, nome_livre: 'Gás R-410A', qtd: 1, unidade: 'kg', obrigatorio: 1 }],
        ferramentas: [{ nome: 'Manifold', qtd: 1, obrigatorio: 1 }],
        pessoal: [{ qualificacao_codigo: 'tec_refrig', qtd: 1, opcional: 0 }],
        condicionais: [],
      },
      {
        id: 'svc-gmg-250h',
        codigo: 'GMG_TROCA_OLEO_250H',
        nome: 'Troca óleo + filtro gerador (250h)',
        escopo: 'central', versao: 1, tempo_estimado_min: 120,
        aplicavel_a: { categorias: ['eletrica'], tipos: ['GERADOR'] },
        criado_por_modulo: 'manutencao', ativo: 1,
        materiais: [
          { material_id: null, nome_livre: 'Óleo 15W-40 lubrificante', qtd: 8, unidade: 'L', obrigatorio: 1 },
          { material_id: null, nome_livre: 'Filtro de óleo gerador', qtd: 1, unidade: 'un', obrigatorio: 1 },
        ],
        ferramentas: [],
        pessoal: [{ qualificacao_codigo: 'eletricista_nr10', qtd: 1, opcional: 0 }],
        condicionais: [{ expressao: 'ativo.disponivel == true', bloqueante: 1 }],
      },
      {
        id: 'svc-vtr-5000km',
        codigo: 'VTR_REVISAO_5000KM',
        nome: 'Revisão de viatura a cada 5.000 km',
        escopo: 'central', versao: 1, tempo_estimado_min: 180,
        aplicavel_a: { categorias: ['frota_terrestre'] },
        criado_por_modulo: 'manutencao', ativo: 1,
        materiais: [
          { material_id: null, nome_livre: 'Óleo 5W-30 sintético 4L', qtd: 1, unidade: 'un', obrigatorio: 1 },
          { material_id: null, nome_livre: 'Filtro de óleo', qtd: 1, unidade: 'un', obrigatorio: 1 },
        ],
        ferramentas: [],
        pessoal: [{ qualificacao_codigo: 'motorista_b', qtd: 1, opcional: 1 }],
        condicionais: [],
      },
    ],

    // shape: planos_manutencao
    planos_manutencao: [
      {
        id: 'plan-ac-cic', servico_id: 'svc-limp-split-padrao', servico_versao_pin: null,
        ativo_id: 'a-clim-cic', tipo_codigo: null,
        frequencia: { tipo: 'periodica', valor: { critico_24x7: 'P1M', operacional: 'P3M', admin: 'P1Y' } },
        criticidade_override: null,
        janela_permitida: { hora_inicio: '02:00', hora_fim: '05:00' },
        proxima_execucao: plusD(-2),  // vencida
        ultima_execucao: plusD(-35),
        responsavel_pmoc: 'pmoc_refrigeracao',
        ativo: 1, criado_por_modulo: 'manutencao',
      },
      {
        id: 'plan-ac-sala-202', servico_id: 'svc-limp-split-padrao', servico_versao_pin: null,
        ativo_id: null, tipo_codigo: 'AC_SPLIT',
        frequencia: { tipo: 'periodica', valor: 'P3M' },
        criticidade_override: 'operacional',
        proxima_execucao: plusD(3),
        ultima_execucao: plusD(-90),
        responsavel_pmoc: 'pmoc_refrigeracao',
        ativo: 1, criado_por_modulo: 'manutencao',
      },
      {
        id: 'plan-gmg1-250h', servico_id: 'svc-gmg-250h', servico_versao_pin: 1,
        ativo_id: 'a-gmg-1', tipo_codigo: null,
        frequencia: { tipo: 'por_uso', valor: 250, unidade: 'h' },
        proxima_execucao: plusD(8),
        ultima_execucao: plusD(-180),
        responsavel_pmoc: 'pmoc_eletrica',
        ativo: 1, criado_por_modulo: 'manutencao',
      },
      {
        id: 'plan-s10-5000', servico_id: 'svc-vtr-5000km', servico_versao_pin: null,
        ativo_id: 'a-vtr-s10', tipo_codigo: null,
        frequencia: { tipo: 'por_uso', valor: 5000, unidade: 'km' },
        proxima_execucao: plusD(15),
        ultima_execucao: plusD(-60),
        responsavel_pmoc: 'pmoc_transportes',
        ativo: 1, criado_por_modulo: 'manutencao',
      },
    ],

    // mapeamento mock de relevância: categoria → códigos de estoque relevantes
    estoque_relevancia: {
      climatizacao:     ['GAS-R410A', 'OLE-15W40-1L', 'FIL-AR-VTR'],
      eletrica:         ['OLE-15W40-1L', 'FIL-AR-VTR'],
      frota_terrestre:  ['OLE-15W40-1L', 'FIL-AR-VTR'],
      frota_naval:      ['OLE-15W40-1L'],
      maquinas_corte:   ['OLE-15W40-1L'],
      predial:          ['TIN-EPX-5L'],
      instrumentos:     [],
    },

    // shape: { codigo, nome, descricao, requer_validade } + lista de usuarios qualificados
    qualificacoes_catalogo: [
      { codigo: 'tec_refrig',       nome: 'Técnico em Refrigeração', requer_validade: 1, usuarios: 3 },
      { codigo: 'eletricista_nr10', nome: 'Eletricista NR-10',        requer_validade: 1, usuarios: 5 },
      { codigo: 'soldador',         nome: 'Soldador qualificado',     requer_validade: 1, usuarios: 2 },
      { codigo: 'operador_munk',    nome: 'Operador de Munk',         requer_validade: 1, usuarios: 1 },
      { codigo: 'motorista_b',      nome: 'Motorista categoria B',    requer_validade: 1, usuarios: 12 },
      { codigo: 'motorista_d',      nome: 'Motorista categoria D',    requer_validade: 1, usuarios: 3 },
      { codigo: 'arrais',           nome: 'Arrais Amador',             requer_validade: 1, usuarios: 2 },
      { codigo: 'operador_corte',   nome: 'Operador de máquina de corte', requer_validade: 1, usuarios: 4 },
    ],

    // shape: documento (apenas POPs vinculados a serviços)
    documentos_pop: [
      { id: 'doc-pop-limp-split-v2', nome: 'POP — Limpeza padrão split (v2)', tipo: 'pop', versao: 2, sha256: 'a1b2c3' },
      { id: 'doc-pop-gmg-v1',        nome: 'POP — Manutenção GMG (250h)',     tipo: 'pop', versao: 1, sha256: 'd4e5f6' },
    ],
  };
})();
```

- [ ] **Step 2.2: Rodar o smoke test (sintaxe balanceada)**

Run: `PYTHONPATH=. .venv/bin/pytest tests/test_manutencao_smoke.py::test_erp_manutencao_mocks_js_sintaxe_balanceada -v`

Expected: `1 passed`

- [ ] **Step 2.3: Commit**

```bash
git add assets/erp-manutencao-mocks.js
git commit -m "feat(manut): mocks fiéis ao schema para tabs sem API"
```

---

## Task 3: Boot + auto-init na página

Cria o esqueleto de `erp-manutencao.js`: detecta quando `page-manutencao` fica ativa (via MutationObserver — evita patchar `showPage`), inicializa uma única vez, esvazia o conteúdo HTML legado e injeta um mount point.

**Files:**
- Modify: `assets/erp-manutencao.js`
- Modify: `cmasm_erp.html` (linhas 932-998 — esvaziar o conteúdo da page-manutencao)

- [ ] **Step 3.1: Esvaziar o conteúdo HTML legado da `page-manutencao`**

Substituir o bloco entre as linhas 932 e 998 do `cmasm_erp.html`:

```html
<div id="page-manutencao" class="page">
  <!-- Conteúdo populado por assets/erp-manutencao.js (refatoração V1). -->
  <div id="manut-root"></div>
</div>
```

(O conteúdo antigo — manut-header, manut-list, etc. — é totalmente removido.)

- [ ] **Step 3.2: Substituir o stub de `erp-manutencao.js` pelo boot**

Conteúdo de `assets/erp-manutencao.js`:

```js
/**
 * Módulo da página `manutencao` no cmasm_erp.html — refatoração V1.
 * Spec: docs/superpowers/specs/2026-05-19-manutencao-unificada-design.md
 */
(function () {
  'use strict';

  let initialized = false;

  function boot() {
    if (initialized) return;
    initialized = true;
    const root = document.getElementById('manut-root');
    if (!root) {
      console.warn('[manut] #manut-root não encontrado');
      return;
    }
    if (!window.engine) {
      console.warn('[manut] pmoc-engine.js não carregado');
      root.innerHTML = '<div style="padding:24px;color:#ef4444">Erro: pmoc-engine não carregado.</div>';
      return;
    }
    render(root);
  }

  function render(root) {
    // populado nas Tasks 4+
    root.replaceChildren(
      window.engine.utils.el('div',
        { style: { padding: '20px', color: 'var(--ink-2)' } },
        'Manutenção · refatorando (Task 3 ok).'),
    );
  }

  function isManutActive() {
    const p = document.getElementById('page-manutencao');
    return !!(p && p.classList.contains('active'));
  }

  // 1) Se a página já está visível na carga (caso DOMContentLoaded em deeplink),
  //    boot imediato. 2) Caso contrário, observa mudanças de classe na page.
  function setup() {
    if (isManutActive()) { boot(); return; }
    const p = document.getElementById('page-manutencao');
    if (!p) return;
    const obs = new MutationObserver(() => { if (isManutActive()) boot(); });
    obs.observe(p, { attributes: true, attributeFilter: ['class'] });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', setup);
  } else {
    setup();
  }
})();
```

- [ ] **Step 3.3: Rodar todos os smoke tests para confirmar**

Run: `PYTHONPATH=. .venv/bin/pytest tests/test_manutencao_smoke.py -v`

Expected: `6 passed`

- [ ] **Step 3.4: Verificação visual (manual)**

Servir os arquivos:

```bash
python3 -m http.server 8765 > /tmp/srv.log 2>&1 &
```

Abrir `http://localhost:8765/cmasm_erp.html`, navegar até a aba "Manutenção" na sidebar. Esperado: ver o texto "Manutenção · refatorando (Task 3 ok)." na área da página, sem erros no console (`F12 → Console`).

- [ ] **Step 3.5: Commit**

```bash
git add assets/erp-manutencao.js cmasm_erp.html
git commit -m "feat(manut): boot + auto-init via MutationObserver"
```

---

## Task 4: Topo fixo com filtro multi-select de categorias

Adiciona a barra superior com chips de categoria, persistência em localStorage e URL, botão refetch e ações `[+ Plano]`/`[+ OS]` (visuais; ação real virá depois).

**Files:**
- Modify: `assets/erp-manutencao.js`

- [ ] **Step 4.1: Atualizar `assets/erp-manutencao.js` substituindo a função `render`**

No arquivo `assets/erp-manutencao.js`, **substituir** a função `render(root)` atual por:

```js
  // ── estado global do módulo ──────────────────────────────────────────────
  const state = {
    cats: new Set(),            // categorias selecionadas
    catsAvailable: [],          // derivado dos ativos carregados
    cache: { ativos: null, os: null, estoque: null },
    activeTab: 'dashboard',
    tabDirty: { dashboard: true, ativos: true, os: true, planos: true,
                catalogo: true, estoque: true, calgantt: true, config: true },
  };

  const TAB_DEFS = [
    { id: 'dashboard', icon: '📊', label: 'Dashboard' },
    { id: 'ativos',    icon: '📦', label: 'Ativos' },
    { id: 'os',        icon: '🧰', label: 'OS' },
    { id: 'planos',    icon: '⚙️', label: 'Planos' },
    { id: 'catalogo',  icon: '📖', label: 'Catálogo' },
    { id: 'estoque',   icon: '🗄️', label: 'Estoque' },
    { id: 'calgantt',  icon: '📅', label: 'Cal+Gantt' },
    { id: 'config',    icon: '📄', label: 'Configuração' },
  ];

  // ── persistência ─────────────────────────────────────────────────────────
  const LS_KEY = 'xerp_manut_cats';

  function loadFilter() {
    const url = new URLSearchParams(location.search).get('cats');
    if (url) return url.split(',').filter(Boolean);
    try { return JSON.parse(localStorage.getItem(LS_KEY) || '[]'); }
    catch (_) { return []; }
  }

  function saveFilter() {
    const arr = [...state.cats];
    localStorage.setItem(LS_KEY, JSON.stringify(arr));
    const url = new URL(location.href);
    if (arr.length) url.searchParams.set('cats', arr.join(','));
    else url.searchParams.delete('cats');
    history.replaceState(null, '', url.toString());
  }

  function markAllDirty() { for (const k of Object.keys(state.tabDirty)) state.tabDirty[k] = true; }

  // ── render principal ─────────────────────────────────────────────────────
  function render(root) {
    state.cats = new Set(loadFilter());
    root.replaceChildren(
      renderTopBar(),
      renderTabBar(),
      renderTabContainer(),
    );
    renderActiveTab();
  }

  function renderTopBar() {
    const { el } = window.engine.utils;
    const chipBox = el('div', { id: 'manut-chips', style: {
      display: 'flex', flexWrap: 'wrap', gap: '6px', alignItems: 'center',
    } });

    function renderChips() {
      chipBox.replaceChildren(
        ...state.catsAvailable.map(cat => {
          const on = state.cats.has(cat);
          return el('button', {
            class: 'pe-btn ' + (on ? 'pe-btn--primary' : 'pe-btn--ghost'),
            style: { minHeight: '28px', padding: '4px 10px', fontSize: '12px' },
            onclick: () => {
              if (on) state.cats.delete(cat); else state.cats.add(cat);
              saveFilter(); markAllDirty(); renderChips(); renderActiveTab();
            },
          }, cat);
        }),
        el('button', {
          class: 'pe-btn pe-btn--ghost',
          style: { minHeight: '28px', padding: '4px 10px', fontSize: '12px' },
          onclick: () => { state.cats.clear(); saveFilter(); markAllDirty(); renderChips(); renderActiveTab(); },
        }, 'Tudo'),
        el('button', {
          class: 'pe-btn pe-btn--ghost', title: 'Recarregar do núcleo',
          style: { minHeight: '28px', padding: '4px 10px', fontSize: '12px' },
          onclick: () => fetchAll().then(() => { markAllDirty(); renderActiveTab(); }),
        }, '↻'),
      );
    }
    // exposta como callback para fetchAll() atualizar depois
    state._renderChips = renderChips;
    renderChips();

    return el('div', { style: {
      position: 'sticky', top: '0', zIndex: '5',
      background: 'var(--bg)', padding: '12px 0', marginBottom: '12px',
      borderBottom: '1px solid var(--line)',
    } },
      el('div', { style: { display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' } },
        el('h2', { style: { margin: 0, fontSize: '18px' } }, 'Manutenção'),
        el('div', { style: { flex: 1 } }),
        el('button', { class: 'pe-btn', onclick: () => alert('Em breve: criar plano') }, '+ Plano'),
        el('button', { class: 'pe-btn pe-btn--primary', onclick: () => alert('Em breve: nova OS') }, '+ OS'),
      ),
      el('div', { style: { display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' } },
        el('span', { style: { fontSize: '12px', color: 'var(--ink-3)' } }, 'Categorias:'),
        chipBox,
      ),
    );
  }

  function renderTabBar() {
    const { el } = window.engine.utils;
    const bar = el('div', { id: 'manut-tabbar', style: {
      display: 'flex', gap: '4px', padding: '4px',
      background: 'var(--bg2)', borderRadius: '8px',
      marginBottom: '14px', overflowX: 'auto',
    } });
    function updateStyles() {
      bar.querySelectorAll('[data-tab]').forEach(b => {
        const on = b.dataset.tab === state.activeTab;
        Object.assign(b.style, {
          background: on ? 'var(--panel)' : 'transparent',
          color: on ? 'var(--ink)' : 'var(--ink-2)',
          boxShadow: on ? 'inset 0 -2px 0 var(--acc)' : 'none',
        });
      });
    }
    TAB_DEFS.forEach(t => {
      bar.appendChild(el('button', {
        class: 'pe-btn pe-btn--ghost',
        dataset: { tab: t.id },
        style: { borderRadius: '6px', minHeight: '32px', whiteSpace: 'nowrap' },
        onclick: () => {
          state.activeTab = t.id;
          updateStyles();
          renderActiveTab();
        },
      }, `${t.icon} ${t.label}`));
    });
    state._updateTabStyles = updateStyles;
    updateStyles();
    return bar;
  }

  function renderTabContainer() {
    const { el } = window.engine.utils;
    return el('div', { id: 'manut-tab-content' });
  }

  function renderActiveTab() {
    const cont = document.getElementById('manut-tab-content');
    if (!cont) return;
    const id = state.activeTab;
    // tasks 6-13 substituem este placeholder por renderers reais
    if (!RENDERERS[id]) {
      cont.replaceChildren(window.engine.utils.el('div',
        { style: { padding: '24px', color: 'var(--ink-3)' } },
        `Tab "${id}" — pendente (Tasks 6-13).`));
      return;
    }
    RENDERERS[id](cont);
    state.tabDirty[id] = false;
  }

  const RENDERERS = {};  // populated nas tasks 6-13

  // ── data fetch (mínimo agora; Task 6 expande) ────────────────────────────
  async function fetchAll() {
    // stub: chamada real virá na Task 6
    return Promise.resolve();
  }
```

- [ ] **Step 4.2: Validar sintaxe**

Run: `PYTHONPATH=. .venv/bin/pytest tests/test_manutencao_smoke.py -v`

Expected: `6 passed`

- [ ] **Step 4.3: Verificação visual**

Recarregar `http://localhost:8765/cmasm_erp.html` → aba Manutenção.
Esperado:
- Cabeçalho com título "Manutenção" + botões `+ Plano`, `+ OS`
- Linha de chips (vazia por enquanto, sem categorias carregadas) + botão "Tudo" + botão "↻"
- Barra de tabs com 8 itens; clique alterna o ativo (sublinhado azul)
- Conteúdo mostra "Tab \"<id>\" — pendente"
- URL não tem `?cats=`. Localstorage `xerp_manut_cats` ainda não setado.

- [ ] **Step 4.4: Commit**

```bash
git add assets/erp-manutencao.js
git commit -m "feat(manut): topo fixo com filtro de categorias + tab bar"
```

---

## Task 5: Cliente HTTP + carregamento inicial dos dados reais

Implementa `fetchAll()` real chamando `/api/ativos`, `/api/os`, `/api/estoque` em paralelo. Deriva categorias disponíveis dos ativos e popula o chip box. Adiciona banner de erro/desatualizado.

**Files:**
- Modify: `assets/erp-manutencao.js`

- [ ] **Step 5.1: Substituir o stub `fetchAll`**

No `assets/erp-manutencao.js`, **substituir** a função `async function fetchAll()` (stub) por:

```js
  async function fetchAll() {
    const banner = document.getElementById('manut-banner');
    if (banner) banner.remove();
    try {
      const [ativos, os, estoque] = await Promise.all([
        fetch('/api/ativos').then(r => { if (!r.ok) throw new Error('ativos ' + r.status); return r.json(); }),
        fetch('/api/os').then(r => { if (!r.ok) throw new Error('os ' + r.status); return r.json(); }),
        fetch('/api/estoque').then(r => { if (!r.ok) throw new Error('estoque ' + r.status); return r.json(); }),
      ]);
      state.cache.ativos   = { data: ativos,   ts: Date.now() };
      state.cache.os       = { data: os,       ts: Date.now() };
      state.cache.estoque  = { data: estoque,  ts: Date.now() };
      state.catsAvailable = [...new Set(ativos.map(a => a.categoria).filter(Boolean))].sort();
      if (state._renderChips) state._renderChips();
    } catch (e) {
      console.warn('[manut] fetchAll falhou:', e);
      showErrorBanner(e.message, !!state.cache.ativos);
    }
  }

  function showErrorBanner(msg, hasCache) {
    const { el } = window.engine.utils;
    const root = document.getElementById('manut-root');
    if (!root) return;
    const banner = el('div', {
      id: 'manut-banner',
      style: {
        background: hasCache ? 'rgba(245,158,11,.15)' : 'rgba(239,68,68,.15)',
        border: '1px solid ' + (hasCache ? 'var(--amber)' : 'var(--red)'),
        color: hasCache ? 'var(--amber)' : 'var(--red)',
        padding: '8px 12px', borderRadius: '6px',
        margin: '0 0 12px', display: 'flex', gap: '12px', alignItems: 'center',
      },
    },
      el('span', {}, hasCache ? `⚠ Dados desatualizados (${msg}).` : `⛔ Sem conexão com o núcleo (${msg}).`),
      el('div', { style: { flex: 1 } }),
      el('button', { class: 'pe-btn', onclick: () => fetchAll() }, 'Tentar novamente'),
    );
    root.insertBefore(banner, root.firstChild);
  }
```

- [ ] **Step 5.2: Disparar `fetchAll` no boot**

No `boot()`, **logo após** `if (!window.engine) { ... return; }`, **antes de** `render(root)`, adicionar:

```js
    fetchAll().finally(() => { render(root); });
    return;
```

(O `render(root)` que estava ali precisa ser **removido** — agora `fetchAll` aguarda e depois chama render.)

A função `boot()` completa fica:

```js
  function boot() {
    if (initialized) return;
    initialized = true;
    const root = document.getElementById('manut-root');
    if (!root) {
      console.warn('[manut] #manut-root não encontrado');
      return;
    }
    if (!window.engine) {
      console.warn('[manut] pmoc-engine.js não carregado');
      root.innerHTML = '<div style="padding:24px;color:#ef4444">Erro: pmoc-engine não carregado.</div>';
      return;
    }
    fetchAll().finally(() => { render(root); });
  }
```

- [ ] **Step 5.3: Validar sintaxe**

Run: `PYTHONPATH=. .venv/bin/pytest tests/test_manutencao_smoke.py -v`

Expected: `6 passed`

- [ ] **Step 5.4: Verificação visual com backend rodando**

Em um terminal: `uvicorn backend.main:app --port 8010 --reload`.
Em outro: `python3 -m http.server 8765` (se ainda não estiver rodando).

Acessar `http://localhost:8765/cmasm_erp.html` → aba Manutenção.

Esperado:
- Chips populados com categorias reais do `core.db` (ex: `climatizacao`, `frota_terrestre`, etc.)
- Sem banner de erro
- Clicar num chip → URL atualiza (`?cats=climatizacao`), localStorage atualiza
- Reload mantém o filtro selecionado

Cenário de erro: parar o uvicorn e clicar em `↻`. Esperado: banner amarelo aparece (cache existe). Se nunca conseguiu carregar (limpar localStorage e reload com uvicorn off), banner vermelho.

- [ ] **Step 5.5: Commit**

```bash
git add assets/erp-manutencao.js
git commit -m "feat(manut): fetchAll() carrega ativos/os/estoque + banner de erro"
```

---

## Task 6: Tab Dashboard (real) — KPIs + donut + line + alertas

Primeira tab funcional com dados reais. KPIs calculados em runtime a partir do cache, charts via engine v2.

**Files:**
- Modify: `assets/erp-manutencao.js`

- [ ] **Step 6.1: Adicionar helpers de derivação e o renderer do Dashboard**

No `assets/erp-manutencao.js`, **logo antes** da linha `const RENDERERS = {};`, **adicionar**:

```js
  // ── helpers de derivação (filtrados pelo state.cats) ─────────────────────
  function filteredAtivos() {
    const all = state.cache.ativos?.data || [];
    if (state.cats.size === 0) return all;
    return all.filter(a => state.cats.has(a.categoria));
  }
  function filteredOS() {
    const all = state.cache.os?.data || [];
    if (state.cats.size === 0) return all;
    const ativosIds = new Set(filteredAtivos().map(a => a.id));
    return all.filter(o => !o.ativo_id || ativosIds.has(o.ativo_id));
  }
  function estoqueBaixo() {
    const all = state.cache.estoque?.data || [];
    return all.filter(i => (i.qtd_atual ?? 0) < (i.qtd_minima ?? 0));
  }
```

E **substituir** a linha `const RENDERERS = {};` por:

```js
  // ── renderers de cada tab ────────────────────────────────────────────────
  const RENDERERS = {
    dashboard(cont) {
      const { el, fmt } = window.engine.utils;
      const ativos = filteredAtivos();
      const os = filteredOS();
      const baixo = estoqueBaixo();
      const vencidos = ativos.filter(a => a.uso_atual != null);  // placeholder; planos reais entram com API
      const osPorStatus = {};
      for (const o of os) osPorStatus[o.status] = (osPorStatus[o.status] || 0) + 1;

      const KPIS = [
        { label: 'Ativos no filtro', value: ativos.length, sub: `${ativos.filter(a => a.ativo).length} em serviço` },
        { label: 'OS abertas',       value: os.filter(o => o.status !== 'concluida' && o.status !== 'cancelada').length },
        { label: 'OS concluídas',    value: os.filter(o => o.status === 'concluida').length },
        { label: 'Estoque baixo',    value: baixo.length, sub: 'itens < min' },
      ];

      const kpiGrid = el('div', { style: {
        display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(160px,1fr))',
        gap: '12px', marginBottom: '14px',
      } }, ...KPIS.map(k => el('div', { style: {
        background: 'var(--panel)', border: '1px solid var(--line)',
        borderRadius: '8px', padding: '12px',
      } },
        el('div', { style: { fontSize: '11px', color: 'var(--ink-3)', textTransform: 'uppercase', letterSpacing: '.5px' } }, k.label),
        el('div', { style: { fontFamily: 'var(--font-mono)', fontSize: '24px', color: 'var(--acc)', fontWeight: '700', marginTop: '4px' } }, String(k.value)),
        k.sub ? el('div', { style: { fontSize: '11px', color: 'var(--ink-2)' } }, k.sub) : null,
      )));

      const charts = el('div', { style: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px', marginBottom: '14px' } });
      const donutEl = el('div'); const lineEl = el('div');
      charts.appendChild(donutEl); charts.appendChild(lineEl);

      window.engine.chartDonut(donutEl, {
        title: 'OS por status',
        data: Object.entries(osPorStatus).map(([label, value]) => ({
          label, value,
          color: ({
            aberta: 'var(--blue)', em_execucao: 'var(--amber)',
            concluida: 'var(--green)', cancelada: 'var(--red)',
          })[label] || 'var(--ink-3)',
        })),
        totalLabel: 'OS',
      });
      // Line chart com mock simples por enquanto (mês x OS concluídas naquele mês)
      const byMonth = {};
      for (const o of os.filter(x => x.status === 'concluida' && x.data_conclusao)) {
        const m = (o.data_conclusao || '').slice(0, 7);
        byMonth[m] = (byMonth[m] || 0) + 1;
      }
      const months = Object.keys(byMonth).sort().slice(-12);
      window.engine.chartLine(lineEl, {
        title: 'OS concluídas/mês (12m)',
        series: [{ label: 'Concluídas', points: months.map((m, i) => ({ x: i + 1, y: byMonth[m] })) }],
      });

      const alertas = el('div', {
        style: { background: 'var(--panel)', border: '1px solid var(--line)', borderRadius: '8px', padding: '12px' },
      },
        el('div', { style: { fontWeight: '600', marginBottom: '8px' } }, 'Alertas críticos'),
        baixo.length === 0 ? el('div', { style: { color: 'var(--ink-3)', fontSize: '13px' } }, 'Nenhum alerta de estoque') :
        el('ul', { style: { margin: 0, paddingLeft: '18px', fontSize: '13px' } },
          ...baixo.slice(0, 10).map(i => el('li', {}, `${i.nome} · saldo ${fmt.num(i.qtd_atual)} < min ${fmt.num(i.qtd_minima)}`))),
      );

      cont.replaceChildren(kpiGrid, charts, alertas);
    },
  };
```

- [ ] **Step 6.2: Validar sintaxe**

Run: `PYTHONPATH=. .venv/bin/pytest tests/test_manutencao_smoke.py -v`

Expected: `6 passed`

- [ ] **Step 6.3: Verificação visual**

Recarregar a página → aba Manutenção → Dashboard.
Esperado:
- 4 KPIs com números reais (do `core.db`)
- Donut "OS por status" com cores
- Line "OS concluídas/mês (12m)" (pode estar vazio se não houver OS concluídas com `data_conclusao` no DB)
- Lista de alertas críticos (ou "Nenhum alerta de estoque")
- Selecionar/desselecionar chips de categoria → KPIs e charts atualizam

- [ ] **Step 6.4: Commit**

```bash
git add assets/erp-manutencao.js
git commit -m "feat(manut): tab Dashboard com KPIs + donut + line + alertas reais"
```

---

## Task 7: Tab Ativos (real) — tabela com filtros + drawer de detalhe

**Files:**
- Modify: `assets/erp-manutencao.js`

- [ ] **Step 7.1: Adicionar renderer da tab Ativos**

Dentro do objeto `RENDERERS = { ... }` em `erp-manutencao.js`, **adicionar** após o renderer `dashboard`:

```js
    ativos(cont) {
      const { el, fmt } = window.engine.utils;
      const rows = filteredAtivos();
      const wrap = el('div');
      cont.replaceChildren(wrap);
      window.engine.table(wrap, {
        cols: [
          { key: 'nome', label: 'Nome' },
          { key: 'tipo', label: 'Tipo', filter: true },
          { key: 'categoria', label: 'Categoria', filter: true },
          { key: 'criticidade', label: 'Criticidade', filter: true,
            format: v => v ? window.engine.badge(v,
              v === 'critico_24x7' ? 'red' : v === 'operacional' ? 'amber' : 'green') : '—' },
          { key: 'uso_atual', label: 'Uso atual', format: v => fmt.num(v, 1) },
          { key: 'unidade_uso', label: 'Un' },
          { key: 'responsavel_pmoc', label: 'PMOC dono', filter: true },
        ],
        rows,
        onRowClick: openAtivoDrawer,
      });
    },
```

E **adicionar**, fora do objeto `RENDERERS` (logo após o fechamento `};`), a função `openAtivoDrawer`:

```js
  function openAtivoDrawer(ativo) {
    const { el, fmt } = window.engine.utils;
    const planos = (window.ERP_MANUT_MOCKS?.planos_manutencao || [])
      .filter(p => p.ativo_id === ativo.id || (p.tipo_codigo && p.tipo_codigo === ativo.tipo));
    const osDoAtivo = (state.cache.os?.data || []).filter(o => o.ativo_id === ativo.id);

    function dadosView() {
      return el('div', {},
        ...Object.entries(ativo).map(([k, v]) =>
          el('div', { style: { display: 'flex', gap: '8px', padding: '6px 0', borderBottom: '1px solid var(--line)' } },
            el('div', { style: { color: 'var(--ink-3)', minWidth: '160px' } }, k),
            el('div', {}, v == null ? '—' : String(v)),
          )),
      );
    }
    function planosView() {
      if (!planos.length) return el('div', { style: { color: 'var(--ink-3)' } }, 'Sem planos vinculados.');
      return el('ul', {}, ...planos.map(p =>
        el('li', {}, `${p.servico_id} · ${JSON.stringify(p.frequencia)} · próx ${p.proxima_execucao}`)));
    }
    function osView() {
      if (!osDoAtivo.length) return el('div', { style: { color: 'var(--ink-3)' } }, 'Sem OS para este ativo.');
      return el('ul', {}, ...osDoAtivo.map(o =>
        el('li', {}, `[${o.status}] ${o.codigo || o.id} · ${o.titulo}`)));
    }

    let activeSub = 'dados';
    const subBody = el('div', { style: { marginTop: '10px' } });
    function renderSub() {
      subBody.replaceChildren(({ dados: dadosView, planos: planosView, os: osView }[activeSub])());
    }
    function tabBtn(id, label) {
      return el('button', {
        class: 'pe-btn ' + (activeSub === id ? 'pe-btn--primary' : 'pe-btn--ghost'),
        style: { marginRight: '4px' },
        onclick: () => { activeSub = id; renderSub(); refreshSubTabs(); },
      }, label);
    }
    const subTabs = el('div', {}, tabBtn('dados', 'Dados'), tabBtn('planos', 'Planos'), tabBtn('os', 'OS'));
    function refreshSubTabs() {
      subTabs.replaceChildren(tabBtn('dados', 'Dados'), tabBtn('planos', 'Planos'), tabBtn('os', 'OS'));
    }

    const m = window.engine.modal({
      title: ativo.nome,
      body: el('div', {}, subTabs, subBody),
      footer: [el('button', { class: 'pe-btn pe-btn--primary', onclick: () => m.close() }, 'Fechar')],
    });
    m.open();
    renderSub();
  }
```

- [ ] **Step 7.2: Validar sintaxe**

Run: `PYTHONPATH=. .venv/bin/pytest tests/test_manutencao_smoke.py -v`

Expected: `6 passed`

- [ ] **Step 7.3: Verificação visual**

Recarregar → aba Manutenção → tab "Ativos". Esperado:
- Tabela paginada listando ativos reais do `core.db`
- Busca/filtros por coluna funcionam
- Click em linha abre modal com sub-abas Dados/Planos/OS
- Filtro de categorias no topo filtra também a tabela

- [ ] **Step 7.4: Commit**

```bash
git add assets/erp-manutencao.js
git commit -m "feat(manut): tab Ativos com tabela + drawer de detalhe"
```

---

## Task 8: Tab OS (real) — kanban com DnD + validação de transições + toggle lista

**Files:**
- Modify: `assets/erp-manutencao.js`

- [ ] **Step 8.1: Adicionar renderer da tab OS + helpers de status**

Dentro de `RENDERERS = { ... }`, **adicionar** após `ativos`:

```js
    os(cont) {
      const { el } = window.engine.utils;
      const view = state._osView || (state._osView = 'kanban');
      const toggleWrap = el('div', { style: { marginBottom: '10px', display: 'flex', gap: '4px' } },
        el('button', {
          class: 'pe-btn ' + (view === 'kanban' ? 'pe-btn--primary' : 'pe-btn--ghost'),
          onclick: () => { state._osView = 'kanban'; RENDERERS.os(cont); },
        }, 'Kanban'),
        el('button', {
          class: 'pe-btn ' + (view === 'lista' ? 'pe-btn--primary' : 'pe-btn--ghost'),
          onclick: () => { state._osView = 'lista'; RENDERERS.os(cont); },
        }, 'Lista'),
      );
      const body = el('div');
      cont.replaceChildren(toggleWrap, body);

      if (view === 'kanban') renderOsKanban(body);
      else renderOsLista(body);
    },
```

E **adicionar**, fora do objeto `RENDERERS`, as funções auxiliares:

```js
  const OS_STATUS_ORDEM = ['aberta', 'autorizada', 'iniciada', 'em_execucao', 'espera', 'pronto', 'concluida', 'cancelada'];

  // Transições permitidas (espelha Rules.md §4)
  const OS_TRANSICOES = {
    aberta:      ['autorizada', 'cancelada'],
    autorizada:  ['iniciada', 'cancelada'],
    iniciada:    ['em_execucao', 'espera', 'cancelada'],
    em_execucao: ['espera', 'pronto', 'cancelada'],
    espera:      ['em_execucao', 'cancelada'],
    pronto:      ['concluida', 'em_execucao', 'cancelada'],
    concluida:   [],
    cancelada:   [],
  };

  function transitionAllowed(de, para) {
    return (OS_TRANSICOES[de] || []).includes(para);
  }

  function renderOsKanban(body) {
    const os = filteredOS();
    const cards = os.map(o => ({
      id: o.id, columnId: o.status, title: o.titulo || o.codigo || o.id,
      badges: [
        o.tipo ? { text: o.tipo, kind: 'blue' } : null,
        o.prioridade ? { text: o.prioridade, kind: o.prioridade === 'urgente' || o.prioridade === 'alta' ? 'red' : 'amber' } : null,
      ].filter(Boolean),
      _raw: o,
    }));
    const k = window.engine.kanban(body, {
      columns: OS_STATUS_ORDEM.map(s => ({ id: s, title: s })),
      cards,
      onCardClick: c => openOsDrawer(c._raw),
      onMove: async (id, from, to) => {
        if (!transitionAllowed(from, to)) {
          toast(`Transição inválida: ${from} → ${to}`, 'red');
          // reverte client-side
          const card = k._cards?.find(c => c.id === id);
          if (card) card.columnId = from;
          state.tabDirty.os = true; RENDERERS.os(document.getElementById('manut-tab-content'));
          return;
        }
        try {
          const r = await fetch(`/api/os/${id}/status`, {
            method: 'PUT', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: to, obs: 'movido via painel manutenção' }),
          });
          if (!r.ok) throw new Error('HTTP ' + r.status);
          const o = (state.cache.os?.data || []).find(x => x.id === id);
          if (o) o.status = to;
          toast(`OS movida: ${from} → ${to}`, 'green');
        } catch (e) {
          toast(`Falha ao mover OS: ${e.message}`, 'red');
          state.tabDirty.os = true; RENDERERS.os(document.getElementById('manut-tab-content'));
        }
      },
    });
    k._cards = cards;
  }

  function renderOsLista(body) {
    const { el, fmt } = window.engine.utils;
    const os = filteredOS();
    const wrap = el('div');
    body.replaceChildren(wrap);
    window.engine.table(wrap, {
      cols: [
        { key: 'codigo', label: 'Código' },
        { key: 'titulo', label: 'Título' },
        { key: 'tipo', label: 'Tipo', filter: true },
        { key: 'status', label: 'Status', filter: true,
          format: v => window.engine.badge(v, v === 'concluida' ? 'green' : v === 'cancelada' ? 'red' : 'amber') },
        { key: 'prioridade', label: 'Prioridade', filter: true },
        { key: 'data_abertura', label: 'Aberta', format: v => fmt.date(v) },
      ],
      rows: os,
      onRowClick: openOsDrawer,
    });
  }

  function openOsDrawer(os) {
    const { el } = window.engine.utils;
    const m = window.engine.modal({
      title: `${os.codigo || os.id} · ${os.titulo || ''}`,
      body: el('div', {},
        ...Object.entries(os).map(([k, v]) =>
          el('div', { style: { display: 'flex', gap: '8px', padding: '4px 0', borderBottom: '1px solid var(--line)' } },
            el('div', { style: { color: 'var(--ink-3)', minWidth: '140px' } }, k),
            el('div', {}, v == null ? '—' : String(v)),
          )),
      ),
      footer: [el('button', { class: 'pe-btn pe-btn--primary', onclick: () => m.close() }, 'Fechar')],
    });
    m.open();
  }

  // Toast simples (5s)
  function toast(text, kind) {
    const { el } = window.engine.utils;
    const t = el('div', { style: {
      position: 'fixed', bottom: '20px', right: '20px', zIndex: '999',
      background: 'var(--panel)', border: `1px solid var(--${kind || 'acc'})`,
      color: `var(--${kind || 'acc'})`,
      padding: '10px 14px', borderRadius: '6px', boxShadow: '0 4px 12px rgba(0,0,0,.4)',
      maxWidth: '420px',
    } }, text);
    document.body.appendChild(t);
    setTimeout(() => t.remove(), 5000);
  }
```

- [ ] **Step 8.2: Validar sintaxe**

Run: `PYTHONPATH=. .venv/bin/pytest tests/test_manutencao_smoke.py -v`

Expected: `6 passed`

- [ ] **Step 8.3: Verificação visual + funcional**

Recarregar → aba Manutenção → tab "OS".
Esperado:
- Toggle `Kanban | Lista`
- Kanban com 8 colunas; cards arrastáveis
- Arrastar de `aberta → autorizada` → toast verde + `PUT /api/os/{id}/status` no Network → card permanece
- Arrastar de `concluida → aberta` → toast vermelho "Transição inválida" + card reverte
- Lista: tabela com busca/filtros, click abre modal

Confirmar no DB:

```bash
sqlite3 data/core.db "SELECT id, status FROM ordens_servico WHERE id='<id-que-você-moveu>';"
```

- [ ] **Step 8.4: Commit**

```bash
git add assets/erp-manutencao.js
git commit -m "feat(manut): tab OS com kanban DnD + transições validadas + lista"
```

---

## Task 9: Tab Planos (mock) — tabela + simulação de carga

**Files:**
- Modify: `assets/erp-manutencao.js`

- [ ] **Step 9.1: Adicionar renderer**

Dentro de `RENDERERS = { ... }`, **adicionar** após `os`:

```js
    planos(cont) {
      const { el, fmt } = window.engine.utils;
      const planos = window.ERP_MANUT_MOCKS?.planos_manutencao || [];
      // filtra por categorias selecionadas usando o ativo OU o tipo de ativo
      const ativos = state.cache.ativos?.data || [];
      const ativosById = Object.fromEntries(ativos.map(a => [a.id, a]));
      const cats = state.cats;
      const filtered = planos.filter(p => {
        if (cats.size === 0) return true;
        if (p.ativo_id) return cats.has(ativosById[p.ativo_id]?.categoria);
        if (p.tipo_codigo) return ativos.some(a => a.tipo === p.tipo_codigo && cats.has(a.categoria));
        return false;
      });

      const wrap = el('div');
      const actions = el('div', { style: { marginBottom: '10px' } },
        el('button', { class: 'pe-btn', onclick: () => simularCarga(filtered, ativosById) }, '🧮 Simular carga (90d)'),
      );
      cont.replaceChildren(actions, wrap);
      window.engine.table(wrap, {
        cols: [
          { key: 'id', label: 'ID' },
          { key: 'servico_id', label: 'Serviço' },
          { key: 'alvo', label: 'Alvo',
            format: (_, p) => p.ativo_id ? `ativo:${p.ativo_id}` : `tipo:${p.tipo_codigo}` },
          { key: 'frequencia', label: 'Frequência',
            format: v => typeof v === 'object' ? JSON.stringify(v.valor || v) : String(v) },
          { key: 'proxima_execucao', label: 'Próxima', format: v => fmt.date(v) },
          { key: 'responsavel_pmoc', label: 'PMOC dono', filter: true },
          { key: 'ativo', label: 'Ativo',
            format: v => window.engine.badge(v ? 'on' : 'off', v ? 'green' : 'red') },
        ],
        rows: filtered,
        onRowClick: p => alert('Detalhe do plano ' + p.id + ' — em breve'),
      });
    },
```

E **adicionar**, fora do `RENDERERS`, a função `simularCarga`:

```js
  function simularCarga(planos, ativosById) {
    const { el, fmt } = window.engine.utils;
    const horizonte = 90;
    const hoje = new Date();
    let totalOS = 0, totalMin = 0;
    for (const p of planos) {
      if (!p.proxima_execucao) continue;
      const prox = new Date(p.proxima_execucao);
      if ((prox - hoje) / 86400000 > horizonte) continue;
      const svc = (window.ERP_MANUT_MOCKS?.catalogo_servicos || []).find(s => s.id === p.servico_id);
      totalOS += 1;
      totalMin += svc?.tempo_estimado_min || 60;
    }
    const m = window.engine.modal({
      title: 'Simulação de carga · 90 dias',
      body: el('div', {},
        el('p', {}, `Planos elegíveis: ${planos.length}`),
        el('p', {}, `OS previstas: ${totalOS}`),
        el('p', {}, `Tempo total estimado: ${fmt.num(totalMin)} min (~${fmt.num(totalMin / 60, 1)} h)`),
        el('p', { style: { color: 'var(--ink-3)', fontSize: '12px' } },
          'Estimativa baseada em mock. Após /api/planos, considerará criticidade real e janelas.'),
      ),
      footer: [el('button', { class: 'pe-btn pe-btn--primary', onclick: () => m.close() }, 'Fechar')],
    });
    m.open();
  }
```

- [ ] **Step 9.2: Validar sintaxe**

Run: `PYTHONPATH=. .venv/bin/pytest tests/test_manutencao_smoke.py -v`

Expected: `6 passed`

- [ ] **Step 9.3: Verificação visual**

Tab "Planos". Esperado: tabela com 4 planos mock; clicar `🧮 Simular carga (90d)` abre modal com totais.

- [ ] **Step 9.4: Commit**

```bash
git add assets/erp-manutencao.js
git commit -m "feat(manut): tab Planos (mock) + simulação de carga 90d"
```

---

## Task 10: Tab Catálogo (mock) — lista + drawer

**Files:**
- Modify: `assets/erp-manutencao.js`

- [ ] **Step 10.1: Adicionar renderer**

Dentro de `RENDERERS = { ... }`, **adicionar** após `planos`:

```js
    catalogo(cont) {
      const { el } = window.engine.utils;
      const servicos = window.ERP_MANUT_MOCKS?.catalogo_servicos || [];
      const filtered = state.cats.size === 0 ? servicos : servicos.filter(s => {
        const cats = s.aplicavel_a?.categorias || [];
        return cats.length === 0 || cats.some(c => state.cats.has(c));
      });
      const wrap = el('div');
      cont.replaceChildren(wrap);
      window.engine.table(wrap, {
        cols: [
          { key: 'codigo', label: 'Código' },
          { key: 'nome', label: 'Nome' },
          { key: 'escopo', label: 'Escopo', filter: true,
            format: v => window.engine.badge(v, v === 'central' ? 'acc' : 'blue') },
          { key: 'versao', label: 'Versão' },
          { key: 'tempo_estimado_min', label: 'Tempo (min)' },
        ],
        rows: filtered,
        onRowClick: openCatalogoDrawer,
      });
    },
```

E **adicionar**, fora do `RENDERERS`, a função `openCatalogoDrawer`:

```js
  function openCatalogoDrawer(svc) {
    const { el } = window.engine.utils;
    function section(title, items, formatter) {
      return el('div', { style: { marginTop: '10px' } },
        el('div', { style: { fontWeight: '600', marginBottom: '4px', color: 'var(--ink-2)' } }, title),
        items.length === 0
          ? el('div', { style: { color: 'var(--ink-3)', fontSize: '13px' } }, 'Nenhum.')
          : el('ul', { style: { margin: 0, paddingLeft: '18px', fontSize: '13px' } },
              ...items.map(it => el('li', {}, formatter(it)))),
      );
    }
    const m = window.engine.modal({
      title: `${svc.codigo} (v${svc.versao}) · ${svc.nome}`,
      body: el('div', {},
        svc.descricao ? el('p', { style: { color: 'var(--ink-2)' } }, svc.descricao) : null,
        section('Materiais', svc.materiais || [], m => `${m.nome_livre || m.material_id} · ${m.qtd} ${m.unidade}${m.obrigatorio ? '' : ' (opcional)'}`),
        section('Ferramentas', svc.ferramentas || [], f => `${f.nome} ×${f.qtd}${f.obrigatorio ? '' : ' (opcional)'}`),
        section('Pessoal', svc.pessoal || [], p => `${p.qualificacao_codigo} ×${p.qtd}${p.opcional ? ' (opcional)' : ''}`),
        section('Condicionais', svc.condicionais || [], c => `${c.expressao}${c.bloqueante ? ' (bloqueante)' : ''}`),
      ),
      footer: [el('button', { class: 'pe-btn pe-btn--primary', onclick: () => m.close() }, 'Fechar')],
    });
    m.open();
  }
```

- [ ] **Step 10.2: Validar sintaxe + visual**

Run: `PYTHONPATH=. .venv/bin/pytest tests/test_manutencao_smoke.py -v` → 6 passed.
Tab "Catálogo": tabela com 4 serviços; clicar abre modal com seções de materiais/ferramentas/pessoal/condicionais.

- [ ] **Step 10.3: Commit**

```bash
git add assets/erp-manutencao.js
git commit -m "feat(manut): tab Catálogo (mock) + drawer detalhe"
```

---

## Task 11: Tab Estoque (saldo real + filtro mock por relevância)

**Files:**
- Modify: `assets/erp-manutencao.js`

- [ ] **Step 11.1: Adicionar renderer**

Dentro de `RENDERERS = { ... }`, **adicionar** após `catalogo`:

```js
    estoque(cont) {
      const { el, fmt } = window.engine.utils;
      const all = state.cache.estoque?.data || [];
      const rel = window.ERP_MANUT_MOCKS?.estoque_relevancia || {};
      let rows = all;
      if (state.cats.size > 0) {
        const codigos = new Set();
        for (const c of state.cats) (rel[c] || []).forEach(k => codigos.add(k));
        rows = all.filter(i => codigos.has(i.codigo));
      }
      const wrap = el('div');
      cont.replaceChildren(wrap);
      window.engine.table(wrap, {
        cols: [
          { key: 'codigo', label: 'Código' },
          { key: 'nome', label: 'Nome' },
          { key: 'categoria', label: 'Categoria', filter: true },
          { key: 'qtd_atual', label: 'Saldo', format: v => fmt.num(v) },
          { key: 'qtd_minima', label: 'Mín', format: v => fmt.num(v) },
          { key: 'unidade', label: 'Un' },
          { key: 'status', label: 'Status',
            format: (_, r) => {
              const baixo = (r.qtd_atual ?? 0) < (r.qtd_minima ?? 0);
              const zero = (r.qtd_atual ?? 0) === 0;
              return window.engine.badge(zero ? 'crítico' : baixo ? 'baixo' : 'ok',
                zero ? 'red' : baixo ? 'amber' : 'green');
            } },
        ],
        rows,
        onRowClick: i => alert('Detalhe do item ' + i.codigo + ' — em breve'),
      });
    },
```

- [ ] **Step 11.2: Validar + visual**

Run: smoke tests → 6 passed.
Tab "Estoque": com filtro vazio mostra todos os itens reais; com `climatizacao` ativo mostra só os relevantes (GAS-R410A etc., se existirem no DB).

- [ ] **Step 11.3: Commit**

```bash
git add assets/erp-manutencao.js
git commit -m "feat(manut): tab Estoque com saldo real + filtro mock de relevância"
```

---

## Task 12: Tab Calendário+Gantt (mock) com toggle

**Files:**
- Modify: `assets/erp-manutencao.js`

- [ ] **Step 12.1: Adicionar renderer**

Dentro de `RENDERERS = { ... }`, **adicionar** após `estoque`:

```js
    calgantt(cont) {
      const { el, fmt } = window.engine.utils;
      const view = state._calView || (state._calView = 'cal');
      const toggleWrap = el('div', { style: { marginBottom: '10px', display: 'flex', gap: '4px' } },
        el('button', {
          class: 'pe-btn ' + (view === 'cal' ? 'pe-btn--primary' : 'pe-btn--ghost'),
          onclick: () => { state._calView = 'cal'; RENDERERS.calgantt(cont); },
        }, '📅 Calendário'),
        el('button', {
          class: 'pe-btn ' + (view === 'gantt' ? 'pe-btn--primary' : 'pe-btn--ghost'),
          onclick: () => { state._calView = 'gantt'; RENDERERS.calgantt(cont); },
        }, '📈 Gantt'),
      );
      const body = el('div');
      cont.replaceChildren(toggleWrap, body);

      const planos = window.ERP_MANUT_MOCKS?.planos_manutencao || [];
      const ativos = state.cache.ativos?.data || [];
      const ativosById = Object.fromEntries(ativos.map(a => [a.id, a]));
      const filtered = state.cats.size === 0 ? planos : planos.filter(p =>
        p.ativo_id ? state.cats.has(ativosById[p.ativo_id]?.categoria)
                   : ativos.some(a => a.tipo === p.tipo_codigo && state.cats.has(a.categoria)));

      if (view === 'cal') {
        const events = filtered
          .filter(p => p.proxima_execucao)
          .map(p => ({
            id: p.id, date: p.proxima_execucao,
            title: p.servico_id,
            color: new Date(p.proxima_execucao) < new Date() ? 'var(--red)' : undefined,
          }));
        window.engine.calendar(body, { events,
          onEventDrop: (id, novo, antigo) => {
            const p = filtered.find(x => x.id === id);
            if (p) p.proxima_execucao = novo;
            toast(`Plano reagendado: ${id} ${antigo} → ${novo} (mock — não persiste)`, 'amber');
          },
        });
      } else {
        const today = new Date();
        const start = fmt.iso(new Date(today.getFullYear(), today.getMonth(), 1));
        const end   = fmt.iso(new Date(today.getFullYear(), today.getMonth() + 2, 0));
        const tasks = filtered
          .filter(p => p.proxima_execucao)
          .map(p => ({
            id: p.id, label: p.servico_id,
            start: p.proxima_execucao,
            end: fmt.iso(new Date(new Date(p.proxima_execucao).getTime() + 86400000)),
            color: 'var(--acc)',
          }));
        window.engine.gantt(body, { range: { start, end }, tasks });
      }
    },
```

- [ ] **Step 12.2: Validar + visual**

Run: smoke tests → 6 passed.
Tab "Cal+Gantt": toggle alterna views; calendário mostra eventos dos planos mock; arrastar evento dispara toast amarelo.

- [ ] **Step 12.3: Commit**

```bash
git add assets/erp-manutencao.js
git commit -m "feat(manut): tab Cal+Gantt (mock) com toggle de view"
```

---

## Task 13: Tab Configuração (mock) — criticidade + qualificações

**Files:**
- Modify: `assets/erp-manutencao.js`

- [ ] **Step 13.1: Adicionar renderer**

Dentro de `RENDERERS = { ... }`, **adicionar** após `calgantt`:

```js
    config(cont) {
      const { el } = window.engine.utils;
      const sub = state._configSub || (state._configSub = 'criticidade');
      const subBar = el('div', { style: { marginBottom: '10px', display: 'flex', gap: '4px' } },
        el('button', {
          class: 'pe-btn ' + (sub === 'criticidade' ? 'pe-btn--primary' : 'pe-btn--ghost'),
          onclick: () => { state._configSub = 'criticidade'; RENDERERS.config(cont); },
        }, 'Criticidade de ativos'),
        el('button', {
          class: 'pe-btn ' + (sub === 'qualif' ? 'pe-btn--primary' : 'pe-btn--ghost'),
          onclick: () => { state._configSub = 'qualif'; RENDERERS.config(cont); },
        }, 'Qualificações'),
      );
      const body = el('div');
      cont.replaceChildren(subBar, body);

      if (sub === 'criticidade') {
        const ativos = filteredAtivos();
        window.engine.table(body, {
          cols: [
            { key: 'nome', label: 'Ativo' },
            { key: 'tipo', label: 'Tipo', filter: true },
            { key: 'criticidade', label: 'Criticidade', filter: true,
              format: v => window.engine.badge(v || 'operacional',
                v === 'critico_24x7' ? 'red' : v === 'admin' ? 'blue' : 'amber') },
            { key: 'responsavel_pmoc', label: 'PMOC dono', filter: true },
          ],
          rows: ativos,
          onRowClick: a => alert('Editar criticidade de ' + a.nome + ' — em breve (precisa PUT /api/ativos)'),
        });
      } else {
        const quals = window.ERP_MANUT_MOCKS?.qualificacoes_catalogo || [];
        window.engine.table(body, {
          cols: [
            { key: 'codigo', label: 'Código' },
            { key: 'nome', label: 'Nome' },
            { key: 'requer_validade', label: 'Valida?',
              format: v => window.engine.badge(v ? 'sim' : 'não', v ? 'green' : 'amber') },
            { key: 'usuarios', label: 'Qualificados' },
          ],
          rows: quals,
          onRowClick: q => alert('Detalhe ' + q.codigo + ' — em breve'),
        });
      }
    },
```

- [ ] **Step 13.2: Validar + visual**

Run: smoke tests → 6 passed.
Tab "Configuração": toggle entre `Criticidade de ativos` e `Qualificações`.

- [ ] **Step 13.3: Commit**

```bash
git add assets/erp-manutencao.js
git commit -m "feat(manut): tab Configuração (mock) com sub-abas criticidade/qualif"
```

---

## Task 14: Roteiro de aceite (manual) + atualização do todo.md

Roda os 10 cenários do spec §7.4 sequencialmente e registra resultado no `todo.md`.

**Files:**
- Modify: `todo.md`

- [ ] **Step 14.1: Executar o roteiro manual de aceite**

Com `uvicorn backend.main:app --port 8010 --reload` e `python3 -m http.server 8765` rodando:

Abrir `http://localhost:8765/cmasm_erp.html` e validar os 10 cenários da tabela em `docs/superpowers/specs/2026-05-19-manutencao-unificada-design.md` §7.4. Anotar qualquer divergência.

- [ ] **Step 14.2: Atualizar o `todo.md`**

**Adicionar** no `todo.md` (logo após o bloco de tasks recém-concluídas), a seção:

```markdown
## ✅ Concluído recente

- [x] 2026-05-19 — Refatoração da página `manutencao` (V1): 8 tabs, filtro multi-select de categoria, Dashboard/Ativos/OS com API real, Planos/Catálogo/Estoque-filtro/Cal+Gantt/Config com mock. Spec: `docs/superpowers/specs/2026-05-19-manutencao-unificada-design.md`. Plano: `docs/superpowers/plans/2026-05-19-manutencao-unificada.md`.

## 🟠 P1 — Pós-V1 da manutencao

- [ ] Criar endpoints `GET/POST/PUT /api/catalogo/servicos` (com testes TDD seguindo `tests/test_sync.py`)
- [ ] Criar endpoints `GET/POST/PUT /api/planos/manutencao`
- [ ] Plugar Planos, Catálogo, Configuração na API real (remove mock daquelas tabs)
- [ ] Reagendamento no calendário/gantt deve persistir (`PUT /api/planos/{id}`)
- [ ] Toggle on/off de plano deve persistir
- [ ] Endpoint `PUT /api/ativos/{id}` para editar criticidade pela aba Configuração
- [ ] Cenários Playwright (4-5 do spec §7.2.3)
- [ ] Decisão sobre fate dos PMOCs offline-first (brainstorm separado)
```

- [ ] **Step 14.3: Commit final**

```bash
git add todo.md
git commit -m "$(cat <<'EOF'
chore(manut): registra conclusão da V1 e pendências P1 no todo

V1 da refatoração da página manutencao entregue:
- 8 tabs (Dashboard/Ativos/OS reais; demais mock)
- Filtro multi-select de categorias persistente
- DnD no kanban com validação de transições
- Smoke tests passando

Pendências P1 listadas para próximo ciclo.
EOF
)"
```

---

## Self-review

**Spec coverage:**

| Spec § | Coberto por |
|---|---|
| §1 contexto e motivação | (documentação — não exige task) |
| §2 decisões registradas 1-7 | Refletidas em Tasks 3-13 |
| §3 arquitetura (mount point, separar JS, engine v2) | Tasks 1, 3 |
| §4.1 topo fixo (chips + ações) | Task 4 |
| §4.2 Dashboard | Task 6 |
| §4.2 Ativos | Task 7 |
| §4.2 OS (kanban + DnD + lista) | Task 8 |
| §4.2 Planos | Task 9 |
| §4.2 Catálogo | Task 10 |
| §4.2 Estoque | Task 11 |
| §4.2 Cal+Gantt | Task 12 |
| §4.2 Configuração | Task 13 |
| §5.1 carregamento inicial | Task 5 |
| §5.2 mudança de filtro (LS+URL+rerender) | Task 4 |
| §5.3 mudança de tab (dirty) | Task 4 |
| §5.4 ações de escrita (PUT status) | Task 8 |
| §5.5 cache em memória | Task 5 |
| §6.1 falhas de rede (GET) | Task 5 (banner) |
| §6.2 falhas de escrita (PUT) | Task 8 (toast + revert) |
| §6.3 estados vazios | Tasks 4-13 (renderers já tratam empty via `engine.table.__empty`) |
| §6.4 validações de cliente (transições inválidas) | Task 8 (`OS_TRANSICOES`) |
| §6.5 telemetria (console.warn) | Tasks 5, 8 |
| §7.2 smoke + roteiro manual | Tasks 1, 14 |
| §7.3 critérios de pronto | Task 14 |
| §7.4 roteiro de aceite | Task 14 |
| §10 arquivos a criar/modificar | Tasks 1-13 |

Cobertura completa. Sem gaps.

**Placeholder scan:** nenhum "TBD" / "TODO" / "fill in later" / referências a funções não definidas. Cada step com código tem o código completo.

**Type consistency:**
- `state.cats` é sempre `Set` (definido na Task 4, usado em todas as tabs)
- `state.cache.{ativos,os,estoque}` sempre `{data, ts}` (Task 5)
- `state._renderChips`, `state._updateTabStyles`, `state._osView`, `state._calView`, `state._configSub` — convenção `_` para callbacks internos consistente
- Funções compartilhadas (`toast`, `transitionAllowed`, `filteredAtivos`, `filteredOS`, `openOsDrawer`, `openAtivoDrawer`, `openCatalogoDrawer`, `simularCarga`) — nomes consistentes; assinaturas alinham com chamadores
- `OS_STATUS_ORDEM` e `OS_TRANSICOES` definidas uma vez (Task 8), usadas no kanban

**Risco identificado:** o `cmasm_erp.html` tem 2 `<body>` tags (linhas 343 e 4275). O Step 1.4 instrui a inserir scripts antes da linha 4275 (`<body>` do fallback noscript). O implementador deve confirmar o local exato com `grep -n "<body" cmasm_erp.html` antes de editar.

---

**Plano completo e salvo em `docs/superpowers/plans/2026-05-19-manutencao-unificada.md`.**
