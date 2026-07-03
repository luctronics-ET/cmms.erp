---
phase: 10-dados-conectividade
plan: 06
subsystem: api
tags: [fastapi, admin-panel, integrity-audit, vanilla-js, sqlite]

# Dependency graph
requires:
  - phase: 10-dados-conectividade (10-01)
    provides: ativos.grama_maquina_id (coluna aditiva usada na query de máquinas de corte)
  - phase: 10-dados-conectividade (10-03)
    provides: os.lotacao_id e edições anteriores em backend/main.py e cmasm_erp.html (mesmos arquivos, sem conflito)
provides:
  - "GET /api/admin/integridade — endpoint de auditoria contínua de conectividade, gated por role admin"
  - "_require_admin(user) — helper de access control reutilizável para futuras rotas admin-only"
  - "Painel 'Integridade de Dados' na aba admin existente do cmasm_erp.html"
affects: [11-locais-fase-seguinte, qualquer-fase-que-adicione-nova-categoria-de-integridade]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "_require_auth → _require_admin (novo) → lógica da rota, espelhando o padrão _require_auth → _require_escrita já usado em 12+ rotas"
    - "Resposta de auditoria agrupada por categoria: {gerado_em, categorias:[{chave, titulo, total, itens}]}"

key-files:
  created: []
  modified:
    - backend/main.py
    - cmasm_erp.html

key-decisions:
  - "_require_admin(user) implementado como função síncrona simples (lança HTTPException 403), espelhando _require_escrita — sem middleware/decorator novo"
  - "Query de planos órfãos usa literalmente a condição de RESEARCH §4.2 (aplicavel_tipos IS NULL OR = '[]') AND ativo=1 — resulta em 12 hoje (13 planos climatização menos o 1 já arquivado por 10-05), não apenas o caso '[]' isolado citado no objetivo do plano; mantido fiel à query autoritativa do RESEARCH"
  - "gerado_em construído com datetime.utcnow().isoformat() (padrão já usado em outras rotas de main.py) em vez de um helper _utc_now() inexistente em main.py (esse helper só existe em catalogo.py)"
  - "Painel chama loadIntegridade() automaticamente dentro de renderAdminDB() (disparado por showPage('admin')) e expõe botão 'Atualizar' para refresh manual"

requirements-completed: [CON-06]

coverage:
  - id: D1
    description: "GET /api/admin/integridade retorna 401 sem token, 403 para role != admin, 200 com JSON {gerado_em, categorias} para admin"
    requirement: "CON-06"
    verification:
      - kind: integration
        ref: "curl manual contra uvicorn local: sem token -> 401; token role=gestor -> 403; token role=admin -> 200 com 7 categorias"
        status: pass
    human_judgment: false
  - id: D2
    description: "Categorias de integridade retornam contagens reais batendo com o baseline do RESEARCH (locais_sem_estrutura=163, estoque_sem_local=65)"
    requirement: "CON-06"
    verification:
      - kind: integration
        ref: "curl contra /api/admin/integridade com token admin, inspecionado via json.tool: locais_sem_estrutura=163, estoque_sem_local=65, maquinas_corte_sem_grama_maquina_id=26, planos_orfaos=12"
        status: pass
    human_judgment: false
  - id: D3
    description: "Painel 'Integridade de Dados' aparece na aba admin existente (#page-admin) e renderiza categorias com badges de contagem, expansível por item"
    verification: []
    human_judgment: true
    rationale: "Requer login real no browser como admin e como não-admin para confirmar renderização visual e gate de acesso — não verificável só por grep/curl neste ambiente sem browser headless"

# Metrics
duration: 25min
completed: 2026-07-03
status: complete
---

# Phase 10 Plan 06: Relatório de Integridade de Dados (CON-06) Summary

**GET /api/admin/integridade (gated por novo helper _require_admin) audita 7 categorias de inconsistência de FK/órfãos, consumido por um card "Integridade de Dados" na aba admin existente do cmasm_erp.html.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-07-03T22:10:00Z (aprox.)
- **Completed:** 2026-07-03T22:35:24Z
- **Tasks:** 2/2
- **Files modified:** 2

## Accomplishments
- Novo helper `_require_admin(user)` em `backend/main.py`, espelhando `_require_escrita` — primeiro gate `role='admin'` do backend (nenhuma rota existente exigia isso antes)
- Novo endpoint `GET /api/admin/integridade`: 401 sem token, 403 para role != admin, 200 com JSON agrupado por 7 categorias (locais sem estrutura_id, estoque sem local_id, ativos "meio migrados", OS com ativo_id/servico_id não resolvidos, planos órfãos, máquinas de corte sem `grama_maquina_id`)
- Painel "Integridade de Dados" adicionado dentro de `#page-admin` (sem página nova), consumindo o endpoint com token Bearer, com badges verde/âmbar/vermelho por contagem e seções expansíveis listando os itens de cada categoria
- Baseline validado ao vivo contra `data/core.db`: `locais_sem_estrutura=163`, `estoque_sem_local=65` — batendo exatamente com os números documentados em RESEARCH §4.2

## Task Commits

Each task was committed atomically:

1. **Task 1: _require_admin + GET /api/admin/integridade (backend)** - `c493189` (feat)
2. **Task 2: Painel de integridade na aba admin (frontend)** - `6e2db37` (feat)

_Note: nenhuma tarefa era TDD; ambas são `type="auto"` sem `tdd="true"`._

## Files Created/Modified
- `backend/main.py` - Adiciona `_require_admin(user)` (após `_require_escrita`) e `GET /api/admin/integridade` (antes de `@app.on_event("startup")`), com 7 queries de integridade agrupadas por categoria
- `cmasm_erp.html` - Adiciona card "Integridade de Dados" dentro de `#page-admin` e função `loadIntegridade()` (fetch autenticado, renderização de badges/seções expansíveis), chamada por `renderAdminDB()` ao abrir a aba admin

## Decisions Made
- `_require_admin` implementado como função síncrona simples que lança `HTTPException(403, ...)`, sem decorator/middleware novo — consistente com o padrão `_require_escrita` já estabelecido.
- `gerado_em` usa `datetime.utcnow().isoformat(timespec="seconds") + "Z"` em vez de um helper `_utc_now()` — esse helper existe em `backend/catalogo.py`, não em `backend/main.py`; usar `datetime` já importado no topo do arquivo evita import cruzado desnecessário.
- Query de planos órfãos mantida literalmente igual à de RESEARCH §4.2 (`aplicavel_tipos IS NULL OR = '[]'` AND `ativo=1`), resultando em 12 hoje. O objetivo do plano menciona apenas o caso `'[]'` isolado, mas a ação do Task 1 explicitamente instrui reaproveitar as queries de §4.2 sem modificação — mantido fiel à fonte autoritativa (RESEARCH), não ao resumo do objetivo.
- Painel dispara `loadIntegridade()` automaticamente ao navegar para a aba admin (via `renderAdminDB()`, já registrado em `showPage`'s `renders` map) e expõe um botão "Atualizar" para refresh manual sem recarregar a página inteira.

## Deviations from Plan

None - plan executado como escrito, com um pequeno ajuste técnico documentado acima (uso de `datetime.utcnow()` em vez de um helper inexistente `_utc_now()` em `main.py` — Rule 3, correção bloqueante, já que o nome do helper citado no RESEARCH pertence a outro módulo).

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Corrigido helper de timestamp inexistente em main.py**
- **Found during:** Task 1 (implementação do endpoint)
- **Issue:** Rascunho inicial usava `_utc_now()`, que não está definido em `backend/main.py` (só existe em `backend/catalogo.py`) — causaria `NameError` em runtime
- **Fix:** Substituído por `datetime.utcnow().isoformat(timespec="seconds") + "Z"`, usando o import `datetime` já presente no topo do arquivo
- **Files modified:** `backend/main.py`
- **Verification:** Endpoint testado ao vivo via curl retornando `200` com campo `gerado_em` válido
- **Committed in:** `c493189` (parte do commit da Task 1, corrigido antes do commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Correção interna ao processo de implementação, sem impacto de escopo — o plano e a query permanecem exatamente como especificados.

## Issues Encountered
None além do já documentado acima.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Endpoint e painel prontos para uso contínuo; qualquer fase futura que adicione uma nova FK esperada (ex.: `estoque.local_id` populado, backfill de `ativos.local_id` não-climatização em Fase 11/RES-06) pode adicionar uma nova categoria à mesma resposta sem quebrar o formato existente.
- Verificação visual no browser (D3, `human_judgment: true`) ainda pendente de UAT humano — endpoint e wiring já confirmados via curl/grep; falta apenas confirmação visual do card renderizado e do gate admin-only no browser real.

---
*Phase: 10-dados-conectividade*
*Completed: 2026-07-03*

## Self-Check: PASSED
All created/modified files verified present on disk; both task commits (c493189, 6e2db37) verified in git log.
