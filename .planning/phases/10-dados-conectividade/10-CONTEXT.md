# Phase 10: Dados & Conectividade - Context

**Gathered:** 2026-07-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Ligar as FKs mortas e unificar cadastros duplicados/órfãos do núcleo para que organização e ativos resolvam por relacionamento real, não por colisão de string `codigo`. Escopo = CON-01..06 (backend/data). **Não** inclui os residuais funcionais (F11/Fase 11) nem UI além do painel de integridade admin.

**Invariantes:** migrações aditivas (`PRAGMA table_info` antes de `ALTER`, nunca `DROP`); backfills idempotentes e não-destrutivos; contratos `GET /api/usuarios`, `POST /api/os`, `/api/sync/*` não podem quebrar (PMOC + satélites dependem).
</domain>

<decisions>
## Implementation Decisions

### CON-04 — Unificação grama_maquinas ↔ ativos
- **D-01:** **Aposentar `grama_maquinas`.** `backend/grama.py` passa a ler `ativos` (categoria maquinas_corte) diretamente; `ativos.uso_atual` vira fonte única de horas. A tabela `grama_maquinas` (12 rows) fica como legado (nunca DROP), sem novos writes.
- **D-02:** Antes de aposentar, o planner/researcher DEVE mapear as dependências internas de grama sobre `grama_maquinas` — `grama_operacoes`, kanban, calendário e status (`grama.py:600`) referenciam a máquina; cada uma precisa repontar para `ativos.id` (backfill por modelo/série para casar os 12 `gmaq-*` aos 28 ativos maquinas_corte). Isso é o maior risco da fase — tratar como item de pesquisa.

### CON-02 — Lotação na OS
- **D-03:** Nova coluna aditiva `os.lotacao_id → estrutura(id)`. Preenchida **auto + override**: default derivado da unidade do cargo do solicitante (`cargos.usuario_id` → `cargos.unidade_id`), com seletor opcional no form da OS para corrigir/escolher outra lotação. `os.departamento` (TEXT) permanece só como rótulo denormalizado — não é removido.

### CON-01 — Backfill locais.estrutura_id
- **D-04:** Backfill idempotente mapeia `locais.codigo → estrutura.id`. Locais sem match ficam com `estrutura_id` NULL (**pular + listar**) — não falha, não cria nós sintéticos. Os órfãos entram no relatório de integridade (CON-06). Após o backfill, as consultas de organização (`main.py:1967-1988`) passam a resolver por `estrutura_id`; o fallback `COALESCE(estrutura_id, codigo)` só sobrevive enquanto houver órfãos.

### CON-06 — Relatório de integridade
- **D-05:** **Endpoint vivo + UI admin.** `GET /api/admin/integridade` (auth, role admin) retorna as inconsistências de conectividade (FK esperada não populada, `loc` sem `local_id`, órfãos do CON-01, `ativo_id`/`servico_id` de OS não resolvidos). Painel na aba admin existente do `cmasm_erp.html` consome e exibe. Auditoria contínua, não script pontual.

### CON-03 — Registrar módulo fonoclama (locked pela auditoria, sem gray area)
- **D-06:** `INSERT OR IGNORE INTO modulos_registrados` com `categorias_atend='["fonoclama"]'` no seed de `schema_catalogo.sql`, de modo que `GET /api/sync/manifest?modulo=fonoclama` retorne os 10 ativos + 5 planos. Sem mudança de contrato — só passa a incluir a categoria que faltava.

### CON-05 — Limpeza de órfãos (locked pela auditoria, sem gray area)
- **D-07:** Plano `climatizacao` com `aplicavel_tipos='[]'` (aplicável a nada) é arquivado via flag (nunca DROP). `planos_manutencao` (0 rows, APOSENTADO) documentado como legado intencional em `Rules.md`. Nenhuma linha é deletada — só marcada/documentada.

### Claude's Discretion
- Nome exato do flag de arquivamento, layout do painel de integridade, forma do seletor de lotação no form da OS, e estratégia de casamento modelo/série no backfill de grama — escolha do planner/executor dentro das convenções do repo.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Modelo de domínio & regras
- `Rules.md` — regras técnicas/operacionais do núcleo (§2/§3 ativos = cadastro mestre + `uso_atual` fonte única; §5 estoque por seção; §7 docs vinculáveis; §8 sync/manifest; §11 planos). CON-04/CON-05 dependem de §3/§11.
- `.docs_cmasm/Regras de Negocio e Fluxos.md` — modelo de domínio canônico (categorias, planos, OS, transportes, estoque). Nota: só cópias arquivadas sobrevivem em `/home/luc/DEV_ERP/arquivo_cmms_25mai2026/.../Regras de Negocio e Fluxos.md` — verificar qual é a viva.

### Schema (migrações aditivas)
- `data/schema_core.sql` — `usuarios`, `cargos` (:34-35 FKs), `estrutura` (:24 self-ref), `locais` (:72 `estrutura_id`, :134 `estoque.local_id`), `ativos` (`local_id`/`loc`), `ordens_servico`.
- `data/schema_catalogo.sql` — `catalogo_planos`, `modulos_registrados` (seed ~:215 p/ CON-03), `documentos` legado.
- `data/schema_manutencao.sql` — `ativo_plano_estado`, `equipe_membros`.
- `data/schema_grama.sql` — `grama_maquinas`, `grama_operacoes`, kanban/calendário (alvo do CON-04).

### Backend
- `backend/main.py` — org joins `:1967-1988` (COALESCE codigo → CON-01); OS POST/reads `:2059-2145` (CON-02); rotas `/api/pmoc/refrigeracao` duplicadas `:1151`/`:2392` (nota); `db_core.py` migrações aditivas (`:45` estrutura_id, `:60-61` os.ativo_id/servico_id, `:71` os.departamento).
- `backend/grama.py` — alvo do CON-04 (aposentar grama_maquinas; mapear operacoes/kanban/calendario/status `:600`).
- `backend/sync.py` — manifest `:490` `categoria IN (...)` (CON-03 fonoclama excluído hoje); planos derivados `:514-573`.
- `backend/db_core.py` — padrão de migração aditiva via `PRAGMA table_info`.
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Padrão de migração aditiva em `backend/db_core.py` (`PRAGMA table_info` antes de `ALTER ADD COLUMN`) — usar para `os.lotacao_id`.
- Aba admin já existente em `cmasm_erp.html` (`/api/usuarios`, `/api/satellites`, `/api/modulos`) — pendurar o painel de integridade (CON-06) aqui, não criar página nova.
- `cargos.usuario_id → cargos.unidade_id → estrutura.id` já é FK sólida (`main.py:1133-1134,1290`) — base do auto-preenchimento da lotação (CON-02).
- Backfill anterior `tools/backfill_local_id.py` cobriu só climatização — CON-04/RES-06 estendem o padrão.

### Established Patterns
- Auth Bearer + role check por request; endpoints admin exigem role admin.
- Contadores de uso: Rules.md §3 = `ativos.uso_atual` fonte única (justifica aposentar grama_maquinas).
- Nunca DROP — arquivar via flag/`ativo=0`, tabelas legadas ficam.

### Integration Points
- `POST /api/os` (novo `lotacao_id`), `GET /api/sync/manifest` (fonoclama incluído), novo `GET /api/admin/integridade`, org joins em `main.py` migram de `codigo` para `estrutura_id`.
</code_context>

<specifics>
## Specific Ideas

- Contagens reais do `core.db` (baseline p/ verificar backfill): `locais.estrutura_id` 0/163 → deve ficar N/163; `ativos.local_id` 170/220; `os.lotacao_id` novo 0→populado no POST; fonoclama 10 ativos + 5 planos; grama_maquinas 12 vs ativos maquinas_corte 28.
- Backfills devem ser idempotentes (reexecutar não duplica nem sobrescreve manual).
</specifics>

<deferred>
## Deferred Ideas

- De-duplicação das rotas `/api/pmoc/refrigeracao` (`:1151`/`:2392`) e das 3 UIs de refrigeração — housekeeping, avaliado em Future Requirements, não nesta fase.
- Vínculo doc→ativo/OS/local — é a Fase 12 (DOC-04), não aqui.
- Backfill de `ativos.local_id` dos não-climatização — é RES-06 (Fase 11).
- `estoque.local_id` (0/65 morto) — só sinalizado pelo relatório de integridade nesta fase; popular fica p/ quando o modelo de estoque-por-seção for exercido.

### Reviewed Todos (not folded)
None — sem todos pendentes casando com a fase.
</deferred>

---

*Phase: 10-dados-conectividade*
*Context gathered: 2026-07-03*
