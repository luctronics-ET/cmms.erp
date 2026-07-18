---
phase: 10-dados-conectividade
verified: 2026-07-03T22:45:00Z
status: passed
score: 6/6 must-haves verified (mecanismo/comportamento); 1 item de UAT visual pendente
behavior_unverified: 0
overrides_applied: 0
human_verification:

  - test: "Logar no ERP (cmasm_erp.html) como usuário role=admin, abrir a aba Admin e conferir visualmente o card 'Integridade de Dados' — se ele renderiza as 7 categorias com badges de contagem (verde/âmbar/vermelho) e se cada categoria expande ao clicar, listando os itens."
    expected: "Card visível, badges coloridos corretos (ex.: locais_sem_estrutura=163 em vermelho/âmbar), expansão funcional sem erro no console do browser."
    why_human: "Renderização visual e interação de clique/expansão não são verificáveis por grep/curl — o endpoint e o fetch já foram confirmados via curl (200/401/403 corretos, JSON com 7 categorias e contagens reais), mas a experiência visual no DOM real requer navegador."

  - test: "Logar como usuário NÃO-admin (ex.: role=gestor) e abrir a aba Admin — confirmar que o card de integridade não é populado (mensagem 'Acesso restrito a administradores')."
    expected: "Card mostra a mensagem de acesso restrito, sem vazar dados de integridade no DOM."
    why_human: "O gate client-side (SESSION.role!=='admin') foi confirmado por leitura de código (cmasm_erp.html:6928) e o gate server-side por curl (403 confirmado), mas a ausência de vazamento visual/requisição indevida no browser real é melhor confirmada por inspeção humana."
---

# Phase 10: Dados & Conectividade — Verification Report

**Phase Goal:** Ligar FKs mortas e unificar cadastros duplicados/órfãos para que organização e ativos resolvam por relacionamento real, não por colisão de string `codigo`.
**Verified:** 2026-07-03T22:45:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (por requisito CON-01..06)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | CON-01: backfill `locais.codigo → estrutura.id` é idempotente e correto; org joins resolvem por FK com fallback `codigo` via COALESCE | ✓ VERIFIED | `tools/backfill_estrutura_id.py` existe e roda 2x sem erro (0 populados/163 órfãos nas duas execuções, conforme D-04b — 0/163 é o resultado CORRETO hoje, não uma falha). `grep -c "COALESCE(l.estrutura_id, l.codigo)" backend/main.py` = 4 (linhas 2075,2076,2095,2096). `main.py` não foi alterado por este plano (cutover já preexistente). |
| 2 | CON-02: `POST /api/os` grava `os.lotacao_id` (auto-fill do cargo do solicitante, ou override explícito); `os.departamento` e contrato externo preservados | ✓ VERIFIED | Testado ao vivo (uvicorn real, `data/core.db`, dados restaurados após teste): POST sem `lotacao_id` mas com `solicitante_id=1775404932660` → `lotacao_id="CMASM-01"` (unidade real do cargo). POST com `lotacao_id="CMASM-02"` explícito → override respeitado. POST com `modulo_origem` sem auth/sem lotacao_id/solicitante_id → HTTP 201, `lotacao_id=null`, `departamento="Depto Legado"` preservado (contrato externo intacto). Seletor "Lotação" wired em `cmasm_erp.html` (`os-manut-lotacao`, `populateLotacaoSelect`, propagação até `_persistManutOSInBackend`). |
| 3 | CON-03: módulo `fonoclama` registrado; `GET /api/sync/manifest?modulo=fonoclama` retorna 10 ativos + 5 planos | ✓ VERIFIED | Testado ao vivo: `curl .../api/sync/manifest?modulo=fonoclama` → HTTP 200, `ativos`=10 (categoria fonoclama), `planos_manutencao`=7 entradas agrupadas em 5 `plano_id` distintos (plano-amplificador, plano-console, plano-alto_falante, plano-linha_70v, plano-sirene). Seed `INSERT OR IGNORE` em `data/schema_catalogo.sql:224` confirmado; `modulos_registrados.categorias_atend='["fonoclama"]'` confirmado no DB. |
| 4 | CON-04: `grama_maquinas` aposentada como cadastro-mestre; `ativos.uso_atual` é fonte única de horas; backfill linka só matches 1:1 (MS650/SOL); `grama_maquinas` nunca DROP | ✓ VERIFIED | `backend/grama.py:774` — `UPDATE ativos SET uso_atual = uso_atual + ?` confirmado no fluxo `update_operacao_status`; combustível permanece em `grama_maquinas` via link `ativos.grama_maquina_id` (linha 785). `list_maquinas`/`get_maquina` servem via `LEFT JOIN grama_maquinas` preservando o shape (linha 553-561). `tools/backfill_grama_link.py` re-executado ao vivo: 2 já-linkados (MS650, SOL), 3 grupos ambíguos corretamente pulados (FS220 5v10, GAR 3v8, TS114 1v4), BR600 sem equivalente — exatamente conforme D-02. `grama_maquinas` com 12 linhas intactas. |
| 5 | CON-05: plano climatização órfão (`aplicavel_tipos='[]'`) arquivado via flag; `planos_manutencao` documentado como legado aposentado em `Rules.md` | ✓ VERIFIED | `tools/archive_orphan_plano.py` re-executado ao vivo: "já estava arquivado" (idempotente). DB confirma `plano-3c349c22f4`: `ativo=0`, `arquivado_motivo` preenchido. Os 12 planos `plano-clima-g1..g12` continuam `ativo=1` (não afetados — distinção NULL vs `[]` respeitada). `Rules.md:321,323` documenta `planos_manutencao` como APOSENTADO e o arquivamento do plano órfão. |
| 6 | CON-06: `GET /api/admin/integridade` gated por role admin; retorna categorias de inconsistência com contagens reais; painel consome no frontend | ✓ VERIFIED (mecanismo) / ⚠ pendente confirmação visual | Testado ao vivo: sem token → 401; token `role=gestor` → 403; token `role=admin` → 200 com 7 categorias e contagens reais (`locais_sem_estrutura=163`, `estoque_sem_local=65`, `ativos_loc_sem_local_id=40`, `os_ativo_nao_resolvido=0`, `os_servico_nao_resolvido=0`, `planos_orfaos=12`, `maquinas_corte_sem_grama_maquina_id=26`). `_require_admin` helper confirmado (`main.py:964`). Card "Integridade de Dados" wired em `cmasm_erp.html` (fetch autenticado, gate client-side, expansão por categoria) — renderização visual não confirmada em browser real (ver Human Verification). |

**Score:** 6/6 truths verificadas no nível de mecanismo/comportamento (endpoint, dados, wiring de código); 1 item de confirmação visual em browser pendente (não bloqueante — não é um "behavior-dependent truth" no sentido de state-transition, é checagem de UX).

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/db_core.py` | 3 colunas aditivas (`os.lotacao_id`, `ativos.grama_maquina_id`, `catalogo_planos.arquivado_motivo`) via PRAGMA guard | ✓ VERIFIED | Confirmado via `PRAGMA table_info` nas 3 tabelas (data/core.db) e leitura de código (linhas 39,75,96-100). Idempotência confirmada — server já rodou múltiplas vezes sem erro. |
| `data/schema_catalogo.sql` | Seed `INSERT OR IGNORE` para `fonoclama` | ✓ VERIFIED | Linha 223-224, `nome='fonoclama'`, `categorias_atend='["fonoclama"]'`. |
| `tools/backfill_estrutura_id.py` | Backfill idempotente `locais.codigo → estrutura.id` | ✓ VERIFIED | Existe, roda sem exceção, idempotente (2 execuções consecutivas nesta sessão = 0 alterações). |
| `tools/backfill_grama_link.py` | Backfill idempotente 1:1 grama↔ativos | ✓ VERIFIED | Existe, roda sem exceção, idempotente (0 novos links na re-execução desta sessão). |
| `tools/archive_orphan_plano.py` | Arquivamento idempotente do plano órfão | ✓ VERIFIED | Existe, roda sem exceção, idempotente ("já estava arquivado" na re-execução). |
| `Rules.md` | Nota `planos_manutencao` APOSENTADO + registro do arquivamento | ✓ VERIFIED | Linhas 321 e 323 confirmadas. |
| `backend/main.py` | `OSIn.lotacao_id`, auto-fill, INSERT, `_require_admin`, `/api/admin/integridade`, COALESCE joins | ✓ VERIFIED | Todos os trechos lidos e testados ao vivo (ver Truths acima). |
| `backend/grama.py` | Repoint de horas para `ativos.uso_atual`; JOIN em `list_maquinas`/`get_maquina` | ✓ VERIFIED | Linhas 553-561 (JOIN), 773-788 (repoint + combustível satélite). |
| `cmasm_erp.html` | Seletor de lotação + painel de integridade | ✓ VERIFIED (wiring) | `lotacao_id` (linhas 2458-2459, 4281, 4343-4346, 6482, 6499-6521); painel de integridade (linhas 1539-1548, 6912-6963). Smoke test de sintaxe (`tests/test_manutencao_smoke.py`, 6/6) passou nesta sessão. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `os.lotacao_id` | `estrutura.id` | `cargos.usuario_id → cargos.unidade_id` (auto-fill) | ✓ WIRED | Testado ao vivo: derivação correta (`CMASM-01`). |
| `ativos.grama_maquina_id` | `grama_maquinas.id` | backfill 1:1 + JOIN em `list_maquinas` | ✓ WIRED | 2 links (MS650, SOL) confirmados; JOIN confirmado em código e retorno de `/api/grama/maquinas` (shape preservado). |
| `modulos_registrados.categorias_atend` | `GET /api/sync/manifest` | `sync.py:manifest()` filtro `categoria IN (...)` | ✓ WIRED | 10 ativos + 5 planos retornados ao vivo. |
| `_require_auth` → `_require_admin` | `/api/admin/integridade` | gate sequencial | ✓ WIRED | 401/403/200 confirmados ao vivo. |
| `catalogo_planos.arquivado_motivo` | `sync.py` manifest (`WHERE ativo=1`) | flag de arquivamento | ✓ WIRED | Plano órfão `ativo=0`, ausente do filtro `ativo=1` usado pelo manifest. |
| `cmasm_erp.html:loadIntegridade()` | `GET /api/admin/integridade` | fetch autenticado | ✓ WIRED (código) | Confirmado por leitura; render visual não confirmado em browser (UAT). |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| CON-01 | 10-02 | Backfill `locais.estrutura_id` + cutover por FK | ✓ SATISFIED | Mecanismo idempotente confirmado; 0/163 é o resultado esperado por design (D-04b), documentado explicitamente no script e no plano. |
| CON-02 | 10-01, 10-03 | `os.lotacao_id` FK + auto-fill/override | ✓ SATISFIED | Testado ao vivo end-to-end (backend + frontend). |
| CON-03 | 10-01 | Módulo fonoclama no manifest | ✓ SATISFIED | Testado ao vivo — 10 ativos + 5 planos. |
| CON-04 | 10-01, 10-04 | `grama_maquinas` como satélite; `uso_atual` fonte única | ✓ SATISFIED | Repoint confirmado no código; backfill 1:1 confirmado ao vivo; ambíguos corretamente não pareados. |
| CON-05 | 10-01, 10-05 | Órfãos arquivados/documentados | ✓ SATISFIED | Arquivamento via flag confirmado ao vivo; `Rules.md` documentado. |
| CON-06 | 10-01, 10-06 | Relatório de integridade | ✓ SATISFIED (endpoint); confirmação visual pendente | Endpoint testado ao vivo com gate de role e 7 categorias; painel wired no código, visual não confirmado em browser. |

**Nota de bookkeeping (não-bloqueante):** `.planning/REQUIREMENTS.md` ainda lista CON-01..06 como `[ ] Pending` na tabela de status (linhas 19-24, 90-95), desatualizado em relação ao `ROADMAP.md` (que já marca a Fase 10 como `Complete`) e à evidência de código coletada nesta verificação. Isso é uma divergência de documentação de rastreamento, não uma lacuna de implementação — recomenda-se atualizar `REQUIREMENTS.md` para refletir o estado real, mas não bloqueia esta fase.

### Anti-Patterns Found

Nenhum. Varredura de `TBD|FIXME|XXX|TODO|HACK|PLACEHOLDER` em todos os arquivos modificados (`backend/db_core.py`, `backend/main.py`, `backend/grama.py`, `data/schema_catalogo.sql`, os 3 scripts em `tools/`, `Rules.md`) não retornou nenhuma ocorrência. Nenhum `DROP`/`DELETE` encontrado em nenhum dos artefatos — todas as operações são `ALTER TABLE ADD COLUMN` (aditivas) ou `UPDATE` com flags (`ativo=0`, `arquivado_motivo`, `grama_maquina_id`).

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Migração aditiva idempotente (3 colunas) | `PRAGMA table_info` nas 3 tabelas via sqlite3 | `lotacao_id`, `grama_maquina_id`, `arquivado_motivo` presentes | ✓ PASS |
| Manifest fonoclama | `curl .../api/sync/manifest?modulo=fonoclama` | 10 ativos, 5 planos distintos | ✓ PASS |
| Admin gate (sem token) | `curl .../api/admin/integridade` sem Authorization | HTTP 401 | ✓ PASS |
| Admin gate (não-admin) | `curl` com token `role=gestor` | HTTP 403 | ✓ PASS |
| Admin gate (admin) | `curl` com token `role=admin` | HTTP 200, 7 categorias, contagens reais | ✓ PASS |
| POST /api/os auto-fill | `curl POST` com `solicitante_id`, sem `lotacao_id` | `lotacao_id="CMASM-01"` (unidade do cargo) | ✓ PASS |
| POST /api/os override | `curl POST` com `lotacao_id="CMASM-02"` explícito | `lotacao_id="CMASM-02"` (override respeitado) | ✓ PASS |
| POST /api/os contrato externo | `curl POST` com `modulo_origem`, sem auth/lotacao_id/solicitante_id | HTTP 201, `lotacao_id=null`, `departamento` preservado | ✓ PASS |
| Backfill locais (idempotência) | `python3 tools/backfill_estrutura_id.py` (2x nesta sessão) | 0 populados/163 órfãos ambas execuções (esperado — D-04b) | ✓ PASS |
| Backfill grama (idempotência) | `python3 tools/backfill_grama_link.py` (re-executado) | 0 novos links; 2 já-linkados; 3 ambíguos pulados; 1 sem-equivalente | ✓ PASS |
| Arquivamento plano órfão (idempotência) | `python3 tools/archive_orphan_plano.py` (re-executado) | "já estava arquivado" | ✓ PASS |
| Smoke test JS | `pytest tests/test_manutencao_smoke.py` | 6/6 passed | ✓ PASS |
| Smoke test migrações | `pytest tests/test_migracoes_idempotencia.py` | 2/2 passed | ✓ PASS |

**Nota de integridade do ambiente:** Todos os testes ao vivo (POST /api/os, curls de auth) foram feitos contra `data/core.db` real com backup prévio; os 3 registros de teste de OS criados foram deletados ao final e a contagem de linhas de todas as tabelas relevantes (`ordens_servico`, `os_historico`, `ativos`, `locais`, `catalogo_planos`, `grama_maquinas`, `usuarios`) foi conferida idêntica ao estado pré-verificação.

### Human Verification Required

1. **Confirmar renderização visual do painel "Integridade de Dados"**
   **Teste:** Logar no ERP como usuário `role=admin`, abrir a aba Admin.
   **Esperado:** O card "Integridade de Dados" aparece, lista as 7 categorias com badges de contagem coloridos (verde=0, âmbar/vermelho>0), e cada categoria expande ao clicar mostrando os itens.
   **Por que humano:** Endpoint e fetch já confirmados via curl/grep; falta só a confirmação visual em DOM real de browser.

2. **Confirmar gate visual para não-admin**
   **Teste:** Logar como usuário `role≠admin`, abrir a aba Admin.
   **Esperado:** Card de integridade mostra "Acesso restrito a administradores", sem vazar dados.
   **Por que humano:** Gate client-side e server-side já confirmados por código/curl; confirmação de comportamento real no browser é mais confiável feita por um humano.

### Gaps Summary

Nenhuma lacuna de implementação encontrada. Todas as 6 requisitos (CON-01..06) têm evidência de código E de comportamento ao vivo (curl/DB real), incluindo os pontos que o CONTEXT.md trava explicitamente como corretos-por-design (0/163 em CON-01; MS650+SOL apenas em CON-04). O único item pendente é uma confirmação visual de UI que o próprio executor (10-06-SUMMARY.md) já havia sinalizado como `human_judgment: true` — não é um defeito de implementação, é o tipo de checagem que grep/curl não pode fazer.

---

_Verified: 2026-07-03T22:45:00Z_
_Verifier: Claude (gsd-verifier)_
