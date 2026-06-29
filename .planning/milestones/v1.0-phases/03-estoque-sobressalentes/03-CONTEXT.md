# Phase 3: Estoque Sobressalentes - Context

**Gathered:** 2026-06-28
**Status:** Ready for planning
**Mode:** Smart discuss (autonomous, recommendations auto-accepted)

<domain>
## Phase Boundary

Estoque local de sobressalentes dos técnicos, SEPARADO do estoque central: aba "Sobressalentes" com lista (qtd atual, unidade, badge ZERADO/BAIXO/OK, valor estimado), CRUD de peça, ajuste de quantidade (modal motivo+obs) e log em `sobressalentes_movimentos`. Visual portado de `.docs_cmasm/referencias/CMASM_Gestao_v2.html`.

Fora: estoque central (`estoque`/`estoque_movimentos`) — NÃO tocar; equipe (Fase 4); cronograma (Fase 5).
</domain>

<decisions>
## Implementation Decisions

### Modelo de dados — TABELAS SEPARADAS (decisão sobrepõe research)
- O success criteria exige "sem mistura de tabelas" e "GET /api/estoque retorna os mesmos registros de antes". Portanto NÃO adicionar coluna `scope` ao `estoque`. Criar tabelas dedicadas em `schema_manutencao.sql`:
  - `sobressalentes`: `id` PK, `codigo` (UNIQUE nullable), `nome` NOT NULL, `categoria` (consumivel|sobressalente|ferramenta — alinhar com refrig), `unidade` DEFAULT 'un', `qtd_atual` REAL, `qtd_minima` REAL, `preco_unitario` REAL DEFAULT 0, `obs`, `ativo` INTEGER DEFAULT 1, `criado_em` DEFAULT CURRENT_TIMESTAMP.
  - `sobressalentes_movimentos`: `id` PK, `item_id` FK sobressalentes, `tipo` (entrada|saida|ajuste), `quantidade` REAL, `motivo`, `obs`, `operador`, `created_at`.
- CREATE TABLE IF NOT EXISTS, aditivo, nunca DROP. Não alterar `estoque`/`estoque_movimentos`.

### Status e valor
- Badge: ZERADO (qtd_atual <= 0), BAIXO (0 < qtd_atual < qtd_minima), OK (qtd_atual >= qtd_minima).
- Valor estimado do estoque = Σ qtd_atual × preco_unitario.

### Contrato de endpoints (em backend/manutencao.py — router já registrado)
- `GET /api/manutencao/sobressalentes` → lista (filtro opcional por categoria) com badge calculado.
- `POST /api/manutencao/sobressalentes` → cria peça.
- `PUT /api/manutencao/sobressalentes/{id}` → edita campos da peça.
- `POST /api/manutencao/sobressalentes/{id}/ajuste` → ajuste de quantidade: payload `{quantidade, tipo, motivo, obs?}`; atualiza `qtd_atual` + grava `sobressalentes_movimentos`, em UMA transação atômica. Operador do token.
- `GET /api/manutencao/sobressalentes/{id}/movimentos` → histórico.
- Auth (`_require_auth`) em todas. Escritas exigem token não-visitante (consistente com o sistema).

### Frontend (UX)
- Nova aba "Sobressalentes" (TAB_DEFS em assets/erp-manutencao.js, como na Fase 1), visual portado do legado.
- Lista com badges coloridos (tokens dark), valor estimado total no topo. Botões: + Nova peça, editar, Ajustar (modal motivo+obs).
- Fetch + Bearer token localStorage('xcmasm_token'); DOM seguro via el()/textContent (sem innerHTML de dados do servidor).

### Testes
- `tests/test_manutencao.py::test_sobressalentes`: CRUD (criar/editar) + ajuste (qtd atualiza + movimento gravado) com banco limpo; ajuste atômico; `GET /api/estoque` inalterado (não retorna sobressalentes).

### Claude's Discretion
- Nomes finos de colunas/endpoints e shape JSON.
- Categorias exatas (alinhar com as já usadas em refrigeração: consumível/sobressalente/ferramenta).
- Seed inicial de peças locais (opcional; pode ficar vazio e o usuário cadastra).
</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- Fase 1/2: `backend/manutencao.py` (router, _db, _require_auth, transação atômica), `schema_manutencao.sql` (em _SCHEMAS).
- `estoque`/`estoque_movimentos` (data/schema_core.sql:126+) como REFERÊNCIA de shape (badge BAIXO, movimentos) — NÃO reutilizar a tabela, só o padrão.
- Refrigeração já tem 25 itens de estoque local (categorias consumível/sobressalente/ferramenta) — alinhar vocabulário.
- `assets/erp-manutencao.js` (TAB_DEFS, renderActiveTab, el()).
- Legado: `.docs_cmasm/referencias/CMASM_Gestao_v2.html` (estoque de sobressalentes, visual aprovado).

### Established Patterns
- Transação atômica = aiosqlite.connect raw + commit único.
- Migração aditiva, CREATE TABLE IF NOT EXISTS.
- Frontend vanilla, fetch + Bearer, DOM seguro via el().

### Integration Points
- Tabelas em `schema_manutencao.sql`; endpoints em `backend/manutencao.py`; aba em `assets/erp-manutencao.js`.
</code_context>

<specifics>
## Specific Ideas

- "Estoque local dos técnicos" distinto do central — separação é requisito duro (SC).
- Visual segue o legado (aprovado).
</specifics>

<deferred>
## Deferred Ideas

- Integração sobressalentes ↔ consumo em OS (débito automático) — fora; estoque central já faz isso, sobressalentes é gestão manual aqui.
- Transferência entre central e local → futuro.
</deferred>
