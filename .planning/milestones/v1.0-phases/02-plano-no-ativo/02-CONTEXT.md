# Phase 2: Plano no Ativo - Context

**Gathered:** 2026-06-28
**Status:** Ready for planning
**Mode:** Smart discuss (autonomous, recommendations auto-accepted)

<domain>
## Phase Boundary

Técnico seleciona um ativo e vê os itens do plano de manutenção aplicável com checkboxes, status de vencimento (VENCIDA/URGENTE/PROXIMA/EM DIA), barra de progresso e "faltam X h/km". Ao marcar itens + informar responsável e clicar "Registrar Manutenção", grava registro em `manut_registros` e atualiza `ativo_plano_estado.proximo_uso` por item marcado, na mesma transação.

Visual portado de `.docs_cmasm/referencias/CMASM_Gestao_v2.html` (o dict `ulm`/`ultimo uso por item`, persistido). Reusa o skeleton da Fase 1 (`backend/manutencao.py`, `data/schema_manutencao.sql`).

Fora: cronograma por equipe (Fase 5), estoque sobressalentes (Fase 3).
</domain>

<decisions>
## Implementation Decisions

### Modelo de dados
- Nova tabela `ativo_plano_estado` em `schema_manutencao.sql`: `(ativo_id, catalogo_plano_item_id)` chave; `ultimo_uso` (REAL), `proximo_uso` (REAL), `updated_at`. É o `ulm` do legado persistido (estado por item por ativo).
- Nova tabela `manut_registros`: `id`, `ativo_id`, `responsavel`, `data`, `itens` (JSON dos catalogo_plano_item_id marcados ou linhas separadas), `uso_no_momento`, `observacao`, `created_at`. Trilha do que foi executado.
- Não dropar/alterar tabelas existentes; aditivo via `CREATE TABLE IF NOT EXISTS`.

### Cálculo de status e proximo_uso
- Status por item derivado de `uso_atual` do ativo vs `proximo_uso` do item: VENCIDA (uso_atual >= proximo_uso), URGENTE/PROXIMA por janelas (reusar limiar existente, ex. iv*0.15), EM DIA caso contrário.
- Ao registrar item marcado: `proximo_uso = uso_no_momento + intervalo` (intervalo = frequência do item no `catalogo_plano_itens`, com default do plano). Idempotente por registro — dois registros consecutivos dão `uso + 2×intervalo`, sem double-count.
- "faltam X" = `proximo_uso - uso_atual`. Barra de progresso = fração do intervalo consumida.
- Primeiro registro de um item sem estado prévio: cria a linha em `ativo_plano_estado` com `ultimo_uso=uso_no_momento`, `proximo_uso=uso_no_momento+intervalo`.

### Contrato de endpoint
- `GET /api/manutencao/plano-ativo?ativo_id=` retorna itens do plano aplicável ao tipo do ativo (via `catalogo_planos.aplicavel_tipos`) com estado (ultimo_uso/proximo_uso/status/falta) mesclado de `ativo_plano_estado`.
- `POST /api/manutencao/registro` payload `{ativo_id, responsavel, itens:[catalogo_plano_item_id...], observacao?}`: insere `manut_registros` + upsert `ativo_plano_estado.proximo_uso` por item marcado, tudo em UMA transação atômica (`aiosqlite.connect`, rollback se falhar). Responsável obrigatório.
- Operador/responsável: responsável vem do payload; operador (quem registrou) do token.

### Frontend (UX)
- Na aba de manutenção do ativo (reusar/estender o que já existe), renderizar lista de itens do plano com checkbox, badge de status colorido (tokens dark), barra de progresso, texto "faltam X".
- Campo responsável + botão "Registrar Manutenção". Após registrar: feedback, recarregar a lista (status atualizam, VENCIDA some para item recém-executado).
- Bearer token de `localStorage('xcmasm_token')`. Inserção segura no DOM (sem innerHTML de dados do servidor — usar el()/textContent, como corrigido na Fase 1).

### Testes
- `tests/test_manutencao.py::test_plano_no_ativo` (ou arquivo dedicado): registrar duas vezes → `proximo_uso = uso_no_momento + 2×intervalo`; status reflete proximo_uso atualizado; transação atômica.
- Sem nova regressão vs baseline (14 falhas pré-existentes não contam).

### Claude's Discretion
- Nomes exatos de endpoint/colunas e shape fino do JSON.
- Reuso vs nova seção na aba de manutenção (onde encaixa melhor no `erp-manutencao.js`).
- Limiares exatos de URGENTE/PROXIMA (seguir o padrão já usado em vencimentos).
</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- Fase 1: `backend/manutencao.py` (router `/api/manutencao`, `_db()`, `_require_auth`, padrão de transação atômica, `_vencimentos_para_ativo`), `data/schema_manutencao.sql` (em `_SCHEMAS`).
- `catalogo_planos` + `catalogo_plano_itens` (frequência por item + default do plano; `aplicavel_tipos` JSON liga plano↔tipo).
- `GET /api/manutencao/vencimentos` (lógica plano↔tipo + uso → próximo/falta) — reaproveitar.
- `assets/erp-manutencao.js` (aba de manutenção, FICHA_CFG, renderFichaTab; helper `el()` de pmoc-engine.js).
- Legado: `.docs_cmasm/referencias/CMASM_Gestao_v2.html` (plano no ativo + checkboxes + dict `ulm`).

### Established Patterns
- Transação atômica = `aiosqlite.connect` raw + commit único (não CoreDB.execute por-statement).
- Migração aditiva, CREATE TABLE IF NOT EXISTS, nunca DROP.
- Frontend vanilla, fetch + Bearer token, DOM seguro via el().

### Integration Points
- `ativo_plano_estado` e `manut_registros` em `schema_manutencao.sql` (já em `_SCHEMAS`).
- Novos endpoints em `backend/manutencao.py` (já registrado).
- Seção na aba de manutenção em `assets/erp-manutencao.js`.
</code_context>

<specifics>
## Specific Ideas

- Visual e comportamento de checkboxes/status seguem o legado `CMASM_Gestao_v2.html` (aprovado).
- Anti-double-count em `proximo_uso` é requisito explícito (teste cobre).
</specifics>

<deferred>
## Deferred Ideas

- Cronograma por equipe → Fase 5 (consome este estado).
- Gerar OS preventiva a partir do registro (já existe fluxo separado) — não ampliar aqui.
</deferred>
