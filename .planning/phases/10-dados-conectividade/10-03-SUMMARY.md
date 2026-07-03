---
phase: 10-dados-conectividade
plan: 03
subsystem: api
tags: [fastapi, aiosqlite, os, lotacao, organograma, cargos]

# Dependency graph
requires:
  - phase: 10-dados-conectividade
    provides: "Coluna aditiva os.lotacao_id TEXT REFERENCES estrutura(id) (plano 10-01)"
provides:
  - "POST /api/os grava os.lotacao_id: override explícito (body.lotacao_id) ou auto-fill via cargos.usuario_id → cargos.unidade_id do solicitante"
  - "Seletor opcional 'Lotação' no form de Nova OS de Manutenção (modal-nova-os-manut), reaproveitando ESTRUTURA_ORG/orgExecutorOptions"
  - "_persistManutOSInBackend passa a enviar solicitante_id e lotacao_id no POST /api/os, habilitando o auto-fill server-side no único fluxo do frontend já conectado ao backend"
affects: [10-04, 10-05, 10-06]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Auto-fill server-side via SELECT unidade_id FROM cargos WHERE usuario_id = ? (fetch_one) — espelha list_unidades (main.py:1130-1137)"
    - "Seletor de unidade no frontend reaproveita ESTRUTURA_ORG (seed estático já usado por orgExecutorOptions), sem novo endpoint"

key-files:
  created: []
  modified:
    - backend/main.py
    - cmasm_erp.html

key-decisions:
  - "Seletor de lotação foi adicionado ao modal 'Nova OS de Manutenção' (modal-nova-os-manut), não ao modal 'Nova Ordem de Serviço (OS)' (modal-nova-ps/criarPS) — investigação mostrou que criarPS() é 100% client-side (localStorage), nunca chama POST /api/os; o único caminho do frontend que hoje fala com o backend é o fluxo Manutenção → syncManutOSIntoServicos → _persistManutOSInBackend. Adicionar o seletor ali é a leitura correta de 'Claude's Discretion' (10-CONTEXT.md linha 38) sem inventar uma nova integração dual-write no form manual (que seria mudança arquitetural fora do escopo deste plano)."
  - "_persistManutOSInBackend passou a enviar solicitante_id (SESSION.id, já disponível em row.solicitanteId por syncManutOSIntoServicos) — sem isso, o auto-fill de lotacao_id implementado na Task 1 nunca teria dado de entrada para derivar nada nesse fluxo, tornando a feature inalcançável em produção (Rule 2 — completude necessária, não escopo extra)."

patterns-established:
  - "Campos opcionais de override client-side viajam como undefined (não string vazia) no JSON.stringify do payload de POST /api/os, para que o backend trate ausência (auto-fill) de forma idêntica a clientes legados que nunca enviaram o campo."

requirements-completed: [CON-02]

coverage:
  - id: D1
    description: "POST /api/os deriva lotacao_id de cargos.usuario_id → cargos.unidade_id quando o corpo não envia lotacao_id mas envia solicitante_id"
    requirement: "CON-02"
    verification:
      - kind: e2e
        ref: "uvicorn + curl POST /api/os {solicitante_id:1775404932674} sem lotacao_id -> GET /api/os/{id} retorna lotacao_id='CMASM-10' (unidade_id real do cargo do usuário no core.db)"
        status: pass
    human_judgment: false
  - id: D2
    description: "POST /api/os respeita override explícito de lotacao_id no corpo, mesmo com solicitante_id presente"
    requirement: "CON-02"
    verification:
      - kind: e2e
        ref: "curl POST /api/os {solicitante_id:1775404932674, lotacao_id:'CMASM-02'} -> GET /api/os/{id} retorna lotacao_id='CMASM-02' (valor do corpo, não o do cargo)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Contrato externo (módulos sem auth, ex. PMOC/satélites) não quebra: POST /api/os com modulo_origem e sem lotacao_id/solicitante_id retorna 201 e departamento preservado"
    requirement: "CON-02"
    verification:
      - kind: e2e
        ref: "curl POST /api/os {modulo_origem:'pmoc_predial', departamento:'Depto Legado'} sem auth -> HTTP 201, lotacao_id=null, departamento='Depto Legado'"
        status: pass
    human_judgment: false
  - id: D4
    description: "Seletor opcional 'Lotação' no form de OS (modal Nova OS de Manutenção) grava lotacao_id via auto-fill quando vazio e via override quando selecionado"
    requirement: "CON-02"
    verification:
      - kind: e2e
        ref: "curl simulando payload real de _persistManutOSInBackend: {solicitante_id, modulo_origem:'manutencao'} sem lotacao_id -> auto-fill 'CMASM-10'; com lotacao_id:'CMASM-21' -> override respeitado"
        status: pass
    human_judgment: false

duration: 35min
completed: 2026-07-03
status: complete
---

# Phase 10 Plan 03: Lotação na OS (auto-fill + override) Summary

**POST /api/os grava lotacao_id como FK real de estrutura — auto-derivada do cargo do solicitante (cargos.usuario_id → cargos.unidade_id) ou via override explícito — com seletor opcional "Lotação" habilitado no form de Nova OS de Manutenção, o único fluxo do frontend hoje conectado ao backend.**

## Performance

- **Duration:** ~35 min
- **Started:** 2026-07-03T21:55:00Z (aprox.)
- **Completed:** 2026-07-03T22:15:54Z
- **Tasks:** 2/2 completos
- **Files modified:** 2

## Accomplishments
- `backend/main.py`: `OSIn.lotacao_id: Optional[str]` adicionado; `create_os` deriva `lotacao_id` de `cargos.usuario_id → cargos.unidade_id` quando o corpo não envia o campo (mas envia `solicitante_id`), respeitando override explícito quando presente; coluna incluída no INSERT de `ordens_servico`. `departamento` e o contrato externo (`modulo_origem` sem auth) permanecem intactos.
- `cmasm_erp.html`: seletor opcional "Lotação" adicionado ao modal "Nova OS de Manutenção" (`modal-nova-os-manut`), populado via `orgExecutorOptions`/`ESTRUTURA_ORG` (mesma fonte já usada na tela de organização — nenhum endpoint novo). `criarOSManut()` → `syncManutOSIntoServicos()` → `_persistManutOSInBackend()` propagam `lotacao_id` (se selecionado) e `solicitante_id` (SESSION do usuário logado) no `POST /api/os`, tornando o auto-fill server-side realmente alcançável por este fluxo.
- Verificado ponta a ponta contra `data/core.db` (backup tirado antes; DB restaurado ao estado original após os testes — nenhum registro de teste permanece): auto-fill (`lotacao_id` = unidade do cargo do solicitante), override explícito, e contrato de compatibilidade externa (POST sem auth/sem lotacao_id/sem solicitante_id → 201, `departamento` preservado, `lotacao_id` NULL).
- Sintaxe do script inline de `cmasm_erp.html` validada com `node --check` (343KB de JS combinado, sem erro) e smoke test existente (`tests/test_manutencao_smoke.py`, 6/6 passed).

## Task Commits

Each task was committed atomically:

1. **Task 1: OSIn.lotacao_id + auto-fill + INSERT em create_os (backend)** - `0af118a` (feat)
2. **Task 2: Seletor opcional de lotação no form de OS (frontend)** - `76e22ae` (feat)

**Plan metadata:** (commit final de docs feito pelo passo de state_updates, fora deste plano por instrução do orquestrador)

## Files Created/Modified
- `backend/main.py` - `OSIn.lotacao_id: Optional[str]`; derivação via `cargos` antes do INSERT; coluna `lotacao_id` na lista de colunas/VALUES do INSERT de `ordens_servico`
- `cmasm_erp.html` - `<select id="os-manut-lotacao">` no modal de Nova OS de Manutenção; `populateLotacaoSelect()` (nova função, espelha `populateExecutorOrgSelect`); `criarOSManut()`, `syncManutOSIntoServicos()` e `_persistManutOSInBackend()` propagam `lotacao_id`/`solicitante_id` até o POST

## Decisions Made
- Seletor de lotação implementado no modal "Nova OS de Manutenção" (`modal-nova-os-manut`), não no modal "Nova Ordem de Serviço (OS)" genérico (`modal-nova-ps`/`criarPS`). Investigação de código mostrou que `criarPS()` é inteiramente client-side (persiste só em `localStorage`, nunca chama `POST /api/os`); o único caminho do frontend que hoje fala com o backend é `criarOSManut() → syncManutOSIntoServicos() → _persistManutOSInBackend()`. Fazer o form manual (`criarPS`) também dar POST no backend seria uma mudança arquitetural nova (dual-write onde nunca houve) fora do escopo deste plano — a CONTEXT.md linha 38 deixa a "forma do seletor" a critério do executor, e esta é a leitura de menor risco que ainda entrega lotacao_id gravável e verificável via `GET /api/os/{id}`.
- `_persistManutOSInBackend` passou a enviar `solicitante_id` (de `row.solicitanteId`, já preenchido por `syncManutOSIntoServicos` com `SESSION?.id`) — sem isso, o auto-fill de `lotacao_id` (Task 1) nunca teria um `solicitante_id` de entrada nesse fluxo e a feature ficaria implementada no backend mas inatingível pelo único form conectado a ele. Tratado como Rule 2 (completude necessária), documentado aqui por transparência.
- Campos `undefined` (não string vazia) usados no payload JS para `solicitante_id`/`lotacao_id` quando ausentes, para que `JSON.stringify` omita a chave e o backend trate exatamente como um cliente legado que nunca conheceu esses campos.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] `_persistManutOSInBackend` não enviava `solicitante_id`, tornando o auto-fill de `lotacao_id` inalcançável pelo único fluxo do frontend conectado ao backend**
- **Found during:** Task 2 (seletor de lotação no frontend)
- **Issue:** O payload de `POST /api/os` enviado por `_persistManutOSInBackend` (fluxo Manutenção → backend) só incluía `titulo, descricao, tipo, prioridade, modulo_origem, observacoes` — nunca `solicitante_id`. A lógica de auto-fill implementada na Task 1 depende de `body.solicitante_id` para derivar `lotacao_id` via `cargos`; sem esse campo, o recurso entregue pela Task 1 nunca seria exercitado em produção por nenhum caminho real do frontend.
- **Fix:** Adicionado `solicitante_id: row.solicitanteId || undefined` (e `lotacao_id: row.lotacao_id || undefined`) ao payload de `_persistManutOSInBackend`. `row.solicitanteId` já era preenchido por `syncManutOSIntoServicos` com `SESSION?.id` como fallback — dado já disponível, não exigiu novo estado.
- **Files modified:** cmasm_erp.html
- **Verification:** `curl POST /api/os` com o payload real (solicitante_id + modulo_origem='manutencao', sem lotacao_id) confirma `lotacao_id` auto-preenchido ('CMASM-10'); com `lotacao_id` explícito confirma override ('CMASM-21').
- **Committed in:** 76e22ae (Task 2 commit)

**2. [Rule 4-adjacent, resolvido via Claude's Discretion pré-autorizado] Form assumido pelo plano ("form de criação de OS") não corresponde 1:1 a nenhum único form existente**
- **Found during:** Task 2 (leitura do read_first)
- **Issue:** O plano assumia que "o form de criação de OS" chama `POST /api/os` diretamente. A investigação mostrou dois forms distintos: `modal-nova-ps` (rotulado "Nova Ordem de Serviço (OS)", 100% client-side, nunca chama o backend) e `modal-nova-os-manut` ("Nova OS de Manutenção", que via `syncManutOSIntoServicos`/`_persistManutOSInBackend` já fala com `POST /api/os`). Fazer o form manual também postar no backend seria uma mudança arquitetural nova, não coberta pelos arquivos/escopo do plano.
- **Fix:** Seletor implementado no form que já tem integração real com o backend (`modal-nova-os-manut`), evitando introduzir uma nova arquitetura de dual-write não solicitada. Documentado explicitamente aqui e no frontmatter (`key-decisions`) para rastreabilidade — não foi tratado como checkpoint bloqueante porque `10-CONTEXT.md` linha 38 já delega "forma do seletor de lotação no form da OS" à discrição do executor.
- **Files modified:** cmasm_erp.html
- **Verification:** `grep -n "lotacao_id" cmasm_erp.html` mostra o campo do form e a propagação condicional até o payload do POST; smoke test de sintaxe (`node --check`) e `tests/test_manutencao_smoke.py` (6/6) sem regressão.
- **Committed in:** 76e22ae (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 missing critical, 1 discretion documentado)
**Impact on plan:** Ambos necessários para que a feature entregue pela Task 1 seja de fato alcançável e verificável a partir do frontend real do repo. Nenhum scope creep: nenhuma nova arquitetura de sincronização foi introduzida; o form manual (`criarPS`) permanece como estava, fora de escopo.

## Issues Encountered
- Testes de verificação e2e (Task 1 e Task 2) criaram registros de OS reais em `data/core.db` (backup tirado em `/tmp/.../scratchpad/core.db.bak-10-03` antes de qualquer escrita). Todos os registros de teste foram deletados (`ordens_servico` + `os_historico` correspondentes) ao final da verificação; contagem de `ordens_servico` conferida como idêntica à do backup (3 linhas) antes de encerrar.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `os.lotacao_id` grava por relacionamento real (auto ou override) nos dois fluxos de escrita do backend hoje existentes (uso direto de `POST /api/os` e o fluxo Manutenção→backend); `os.departamento` e o contrato externo (PMOC/satélites) permanecem intocados.
- Pendência conhecida, fora de escopo deste plano: o modal "Nova Ordem de Serviço (OS)" (`modal-nova-ps`/`criarPS`) ainda não sincroniza com o backend — se uma fase futura decidir migrar esse form para `POST /api/os`, ele já poderá reaproveitar o mesmo padrão de seletor (`populateLotacaoSelect`) criado aqui.
- Nenhum stub, nenhuma mudança de contrato pendente para 10-04/10-05/10-06.

---
*Phase: 10-dados-conectividade*
*Completed: 2026-07-03*

## Self-Check: PASSED

- FOUND: backend/main.py
- FOUND: cmasm_erp.html
- FOUND: .planning/phases/10-dados-conectividade/10-03-SUMMARY.md
- FOUND: 0af118a (git log)
- FOUND: 76e22ae (git log)
