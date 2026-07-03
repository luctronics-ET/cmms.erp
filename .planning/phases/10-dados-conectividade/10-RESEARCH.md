# Phase 10: Dados & Conectividade - Research

**Researched:** 2026-07-03
**Domain:** SQLite/FastAPI backend connectivity — dead-FK activation, duplicate-registry retirement, integrity auditing (CON-01..06)
**Confidence:** HIGH (all findings verified directly against `data/core.db` and current source; no external libraries involved)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**CON-04 — Unificação grama_maquinas ↔ ativos**
- D-01: **Aposentar `grama_maquinas`.** `backend/grama.py` passa a ler `ativos` (categoria maquinas_corte) diretamente; `ativos.uso_atual` vira fonte única de horas. A tabela `grama_maquinas` (12 rows) fica como legado (nunca DROP), sem novos writes.
- D-02: Antes de aposentar, mapear as dependências internas de grama sobre `grama_maquinas` — `grama_operacoes`, kanban, calendário e status (`grama.py:600`) referenciam a máquina; cada uma precisa repontar para `ativos.id` (backfill por modelo/série para casar os 12 `gmaq-*` aos 28 ativos maquinas_corte). Maior risco da fase.

**CON-02 — Lotação na OS**
- D-03: Nova coluna aditiva `os.lotacao_id → estrutura(id)`. Preenchida auto + override: default derivado da unidade do cargo do solicitante (`cargos.usuario_id → cargos.unidade_id`), com seletor opcional no form da OS. `os.departamento` (TEXT) permanece só como rótulo denormalizado — não é removido.

**CON-01 — Backfill locais.estrutura_id**
- D-04: Backfill idempotente mapeia `locais.codigo → estrutura.id`. Locais sem match ficam com `estrutura_id` NULL (pular + listar) — não falha, não cria nós sintéticos. Órfãos entram no relatório de integridade (CON-06). Após o backfill, `main.py:1967-1988` passam a resolver por `estrutura_id`; fallback `COALESCE(estrutura_id, codigo)` só sobrevive enquanto houver órfãos.

**CON-06 — Relatório de integridade**
- D-05: Endpoint vivo + UI admin. `GET /api/admin/integridade` (auth, role admin) retorna inconsistências de conectividade (FK esperada não populada, `loc` sem `local_id`, órfãos do CON-01, `ativo_id`/`servico_id` de OS não resolvidos). Painel na aba admin existente do `cmasm_erp.html`. Auditoria contínua, não script pontual.

**CON-03 — Registrar módulo fonoclama**
- D-06: `INSERT OR IGNORE INTO modulos_registrados` com `categorias_atend='["fonoclama"]'` no seed de `schema_catalogo.sql`, de modo que `GET /api/sync/manifest?modulo=fonoclama` retorne os 10 ativos + 5 planos. Sem mudança de contrato.

**CON-05 — Limpeza de órfãos**
- D-07: Plano `climatizacao` com `aplicavel_tipos='[]'` arquivado via flag (nunca DROP). `planos_manutencao` (0 rows, APOSENTADO) documentado como legado intencional em `Rules.md`. Nenhuma linha deletada.

### Claude's Discretion
- Nome exato do flag de arquivamento (CON-05).
- Layout do painel de integridade (CON-06).
- Forma do seletor de lotação no form da OS (CON-02).
- Estratégia de casamento modelo/série no backfill de grama (CON-04) — ver §1 abaixo; dados reais mostram que `numero_serie` é `NULL` em 100% das linhas de `grama_maquinas`, então "modelo/série" na prática significa "modelo apenas" (ver Assumptions Log A1).

### Deferred Ideas (OUT OF SCOPE)
- De-duplicação das rotas `/api/pmoc/refrigeracao` (`:1151`/`:2392`) e das 3 UIs de refrigeração — housekeeping, avaliado em Future Requirements.
- Vínculo doc→ativo/OS/local — Fase 12 (DOC-04).
- Backfill de `ativos.local_id` dos não-climatização — RES-06 (Fase 11).
- `estoque.local_id` (0/65 morto) — só sinalizado pelo relatório de integridade nesta fase; popular fica para quando o modelo de estoque-por-seção for exercido.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CON-01 | `locais.estrutura_id` populado por backfill idempotente; org joins resolvem por FK | §3 — backfill script pattern + **CRITICAL data finding**: 0/163 locais.codigo atualmente casam com estrutura.id (ver Pitfall 1) |
| CON-02 | `os.lotacao_id → estrutura(id)` aditivo, auto-preenchido do cargo do solicitante | §2 — migration snippet + auto-fill query + Pydantic model diff |
| CON-03 | `fonoclama` registrado em `modulos_registrados` | §5 — seed INSERT exato + verificação dos 10 ativos/5 planos |
| CON-04 | `grama_maquinas` aposentada; `ativos.uso_atual` fonte única de horas | §1 — mapeamento completo de dependências, matching real gmaq↔ativos, repoint concreto por endpoint |
| CON-05 | Plano climatização órfão arquivado; `planos_manutencao` documentado | §6 — SQL exato do plano órfão + opções de flag |
| CON-06 | `GET /api/admin/integridade` com auditoria contínua | §4 — queries de integridade concretas + padrão de auth admin |
</phase_requirements>

## Summary

Esta fase é majoritariamente **de baixo risco de dados** porque as tabelas satélites de `grama` (`grama_operacoes_manutencao`, `grama_operacoes_servico`, `grama_kanban_tarefas`, `grama_calendario_eventos`, `grama_combustivel_log`) estão **todas com 0 linhas** em produção — não há histórico operacional para remapear. O risco real do CON-04 não é "migrar registros", é decidir **qual conjunto de campos** de `grama_maquinas` (nome, tipo, status, horas) tem equivalente direto em `ativos`, e qual não tem (numero_serie, fabricante, ano_fabricacao, combustível) — e como o frontend (`cmasm_erp.html:7986-8000`, `normalizeVegMaq`) que já espera esse shape exato reage à mudança.

A descoberta mais importante da pesquisa é para **CON-01**, não CON-04: os 163 registros reais de `locais.codigo` estão no formato `REFRI-<AREA>-<NOME>` (gerado por um import anterior de climatização), e **nenhum** bate com o formato `estrutura.id` (`CMASM-XX.Y`). Um backfill por igualdade de string, exatamente como descrito na decisão travada, é seguro e idempotente — mas hoje casará **0 de 163** linhas. Isso não é um bug de lógica; é a realidade dos dados atuais, e o plano deve fixar essa expectativa explicitamente (ver Pitfall 1) para não ser lido como falha de execução.

Para CON-04, o dado real mostra 12 `grama_maquinas` vs 28 `ativos` (categoria `maquinas_corte`), com correspondência 1:1 exata só em 2 casos (MS650, SOL) e ambígua em 3 grupos (FS220 5↔10, GAR 3↔8, TS114 1↔4); 1 máquina (soprador BR600) não tem tipo equivalente nenhum em `ativos`. `numero_serie` é `NULL` em todas as 12 linhas — não existe chave de casamento forte disponível, então qualquer estratégia é heurística e deve ser marcada para revisão humana.

**Primary recommendation:** Trate CON-04 como um recorte de escopo explícito — apenas `nome`/`tipo`/`status`/`uso_atual` (horas) migram para `ativos` como fonte única; combustível/fabricante/série continuam em `grama_maquinas` (agora só-leitura para novo código, mas ainda gravável pelo fluxo de combustível existente, que não duplica identidade de máquina). Trate CON-01 como "constrói o mecanismo, não garante o resultado" — o backfill deve rodar e reportar 0 (ou poucos) matches como resultado esperado e correto nesta fase.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Registro mestre de máquinas de corte (identidade, uso) | API/Backend (`ativos` table) | — | Rules.md §3: ativos = cadastro mestre + uso_atual fonte única |
| Metadados ricos de equipamento (fabricante, série, combustível) | API/Backend (`grama_maquinas` legado) | — | Sem equivalente em `ativos`; fora do escopo de "fonte única de horas" |
| Resolução de organização (locais→estrutura) | API/Backend (SQL joins em `main.py`) | Database (FK `locais.estrutura_id`) | Join hoje depende de `COALESCE`; FK real é o alvo |
| Lotação da OS | API/Backend (auto-fill na criação) | Database (FK `os.lotacao_id`) | Preenchimento server-side a partir de `cargos`, com override client-side opcional |
| Auditoria de integridade | API/Backend (novo endpoint `/api/admin/integridade`) | Browser/Client (painel admin) | Cálculo de FKs órfãs é puramente servidor; painel só consome |
| Registro de módulo/manifest sync | API/Backend (`modulos_registrados` seed) | Database | `sync.py` já é genérico — só precisa da linha de seed |
| Arquivamento de plano órfão | Database (flag column) | API/Backend (filtro `WHERE ativo/arquivado`) | Consistente com o padrão existente `ativo=0` do resto do sistema |

## Standard Stack

Nenhuma biblioteca nova é necessária nesta fase — é 100% SQL aditivo + rotas FastAPI existentes reaproveitadas. Stack confirmado in-place: FastAPI 0.115.0, aiosqlite 0.20.0, Pydantic 2.7.4 (ver `requirements.txt` — inalterado nesta fase).

### Core
Nenhuma dependência nova.

### Supporting
Nenhuma dependência nova.

### Alternatives Considered
Não aplicável — fase não introduz stack novo.

**Installation:** Nenhuma (sem novos pacotes).

## Package Legitimacy Audit

**Não aplicável.** Esta fase não instala pacotes externos — é backend/data-only sobre a stack já presente (FastAPI/aiosqlite/Pydantic). Nenhum pacote novo a auditar.

---

## §1 — CON-04: Aposentar `grama_maquinas` (maior risco — mapeamento completo)

### 1.1 Dados reais (verificado via `python3 sqlite3` direto em `data/core.db`)

**`grama_maquinas` (12 linhas):**

| id | nome | modelo | numero_serie | fabricante | horas_uso |
|----|------|--------|--------------|------------|-----------|
| gmaq-fs220-1..5 (5x) | Roçadeira FS220 #N | FS220 | `NULL` | Stihl | 142.5, 198.2, 76.0, 33.5, 12.0 |
| gmaq-gar-1..3 (3x) | Cortador GAR #N | GAR-53 | `NULL` | Garthen | 85.4, 60.1, 25.0 |
| gmaq-ms650 | Motosserra MS650 | MS650 | `NULL` | Stihl | 42.0 |
| gmaq-sopra-1 | Soprador BR600 | BR600 | `NULL` | Stihl | 18.0 |
| gmaq-ts114-1 | Cortadora concreto TS114 | TS114 | `NULL` | Stihl | 30.0 |
| gmaq-sol | Trator de corte SOL | SOL-1200 | `NULL` | Solaris | 220.1 |

`numero_serie` é `NULL` em **100% das 12 linhas** — a estratégia "modelo/série" mencionada em D-02/Claude's Discretion não tem componente "série" disponível na prática. `[VERIFIED: query direta em core.db]`

**`ativos` categoria `maquinas_corte` (28 linhas)** — schema não tem `modelo`/`numero_serie`/`fabricante`/`combustivel_*`; só `id, tipo, categoria, nome, pat, loc, ativo, uso_atual, unidade_uso`. Tipos presentes: `FS220`(10), `GAR`(8), `MS650`(1), `COY`(3), `LGT`(1), `TS114`(4), `SOL`(1). **Todos com `uso_atual = 0.0`** hoje (nenhuma hora foi registrada no lado `ativos` ainda). `[VERIFIED]`

### 1.2 Matriz de matching por tipo (modelo grama → tipo ativos)

| Modelo grama_maquinas | Contagem grama | Tipo ativos | Contagem ativos | Match determinístico? |
|---|---|---|---|---|
| MS650 | 1 | MS650 | 1 | **SIM — 1:1 exato** (gmaq-ms650 → u19) |
| SOL-1200 | 1 | SOL | 1 | **SIM — 1:1 exato** (gmaq-sol → u28) |
| FS220 | 5 | FS220 | 10 | NÃO — ambíguo (5 máquinas nomeadas, 10 ativos; sem série p/ desambiguar) |
| GAR-53 | 3 | GAR | 8 | NÃO — ambíguo (3 vs 8) |
| TS114 | 1 | TS114 | 4 | NÃO — ambíguo (1 vs 4) |
| BR600 (soprador) | 1 | *(nenhum tipo `BR600`/soprador em ativos)* | 0 | **SEM EQUIVALENTE** — órfão de `grama_maquinas`, fica só no legado |
| — | — | COY (3), LGT (1) | 4 | Ativos sem contrapartida em grama — nunca foram rastreados por hora no módulo grama |

**Soma de conferência:** 10(FS220)+8(GAR)+1(MS650)+3(COY)+1(LGT)+4(TS114)+1(SOL) = 28 ativos. Bate com a contagem real. `[VERIFIED]`

### 1.3 Consequência prática para o backfill de horas

- Para **MS650** e **SOL** (match exato): copiar `grama_maquinas.horas_uso` diretamente para `ativos.uso_atual` no ativo correspondente (u19 = 42.0h; u28 = 220.1h). Seguro, sem ambiguidade.
- Para **FS220, GAR, TS114** (contagem divergente, sem chave forte): **não existe forma verificável** de saber qual `Roçadeira FS220 #1..#5` nomeada corresponde a qual `u01..u10`. Qualquer atribuição ordinal (ex.: por ordem de `id`) é uma suposição, não um fato recuperável dos dados. Recomendação: aplicar a atribuição ordinal como *default* pragmático (determinística e reprodutível — ordenar `grama_maquinas` por `id` e `ativos` por `id`, casar em sequência os primeiros N), mas **marcar cada linha resultante no relatório de integridade (CON-06)** com uma flag `origem: heuristica_ordinal` e **gate a operação atrás de um checkpoint humano** antes de aplicar em produção — não é um dado auditável, é uma melhor suposição.
- Para **BR600/soprador**: sem ativo-alvo. Fica só no legado `grama_maquinas` (consistente com "nunca DROP" e "não cria nós sintéticos" do CON-01).

### 1.4 Dependências internas de `grama.py` sobre `grama_maquinas` (mapeamento por endpoint)

Tabelas satélite (`grama_operacoes_manutencao`, `grama_operacoes_servico`, `grama_kanban_tarefas`, `grama_calendario_eventos`, `grama_combustivel_log`) — **todas com 0 linhas em produção** `[VERIFIED: COUNT(*) = 0 em todas]`. Isso **de-risca drasticamente** o CON-04: não há histórico de `maquina_id` para remapear; a mudança de semântica de `maquina_id` (de "aponta para `grama_maquinas.id`" para "aponta para `ativos.id`") pode ser feita **apenas para escritas futuras**, sem migração de dados existentes.

| grama.py | Linha | O que faz hoje | Repoint concreto |
|---|---|---|---|
| `list_maquinas` / `get_maquina` | 541-558 | `SELECT * FROM grama_maquinas` | `SELECT * FROM ativos WHERE categoria='maquinas_corte'` (+ filtro `tipo`); `status` vira derivado de `ativo` (1→'operacional', 0→'inativo') — **perde granularidade** `em_manutencao`/`aposentada` (ver Pitfall 2) |
| `create_maquina` / `update_maquina` / `delete_maquina` | 561-603 | INSERT/UPDATE em `grama_maquinas`, incluindo `status='inativo'` (delete, linha ~599-601 — **este é o "status" que D-02 referencia em `grama.py:600`**) | Recomendado: **deprecar estas rotas** e redirecionar o frontend para `/api/ativos` (já existe CRUD completo — `main.py:1141,1298,1306,1320`), seguindo o padrão já usado por `pmoc_refrigeracao` (`_ATIVO_EDIT` whitelist em `main.py:1181-1206`) |
| `alertas_manutencao`, `list_manutencao`, `create_manutencao`, `update_manutencao_status` | 608-672 | JOIN com `grama_maquinas.id` via `maquina_id` — **0 linhas hoje** | Repontar `maquina_id` para `ativos.id` daqui em diante (novas escritas); nada a migrar |
| `create_operacao` | 712-723 | INSERT em `grama_operacoes_servico` com `maquina_id` — **0 linhas hoje** | `OperacaoIn.maquina_id` passa a significar `ativos.id` |
| **`update_operacao_status`** | **726-752** | **A escrita crítica**: linhas 744-751 fazem `UPDATE grama_maquinas SET horas_uso=horas_uso+?, combustivel_atual=... WHERE id=(SELECT maquina_id FROM grama_operacoes_servico WHERE id=?)` | **Trocar para `UPDATE ativos SET uso_atual = uso_atual + ? WHERE id = (SELECT maquina_id FROM grama_operacoes_servico WHERE id=?)`** — este é o ponto que unifica `uso_atual` como fonte única (Rules.md §3). O incremento de `combustivel_atual` continua em `grama_maquinas` via o link legado (ver 1.5) |
| `list_combustivel`, `create_combustivel` | 757-834 | Lê/escreve `grama_maquinas.combustivel_atual/capacidade` — **sem equivalente em `ativos`** | Ver 1.5 — mantido como está, é uma preocupação distinta de "duplicidade de cadastro" |
| `relatorios/resumo`, `relatorios/combustivel` | 925-956 | Agrega sobre `grama_maquinas` | Ajustar `maquinas_operacionais`/`em_manutencao` para consultar `ativos`; `relatorios/combustivel` continua sobre `grama_maquinas` (combustível não migra) |

### 1.5 Campos SEM equivalente em `ativos` (decisão de escopo explícita)

`grama_maquinas` tem: `numero_serie`, `fabricante`, `ano_fabricacao`, `combustivel_tipo`, `combustivel_capacidade`, `combustivel_atual`, `valor_aquisicao`, `data_aquisicao`. **Nenhum destes existe em `ativos`** e Rules.md §3 não os inclui nos "campos críticos" do cadastro mestre. Recomendação (a confirmar com o planner): estes campos **não migram** — continuam vivos em `grama_maquinas`, que passa a ser uma tabela de metadados-satélite ligada por um **novo campo aditivo `ativos.grama_maquina_id`** (nullable, `REFERENCES grama_maquinas(id)`), preenchido pelo backfill de matching (§1.3). Isso permite:
1. `GET /api/grama/maquinas` continuar devolvendo o shape exato que `cmasm_erp.html:7986-8000` (`normalizeVegMaq`) já espera (`nome, tipo, marca/fabricante, modelo, serie, ano, status, horimetro/horas_uso, obs`) via `ativos LEFT JOIN grama_maquinas ON grama_maquinas.id = ativos.grama_maquina_id`.
2. `horas_uso` exposto ao frontend passa a ser `ativos.uso_atual` (fonte única); `fabricante/modelo/numero_serie/ano_fabricacao` continuam vindo do JOIN (NULL se não linkado, ex. os 22 ativos sem correspondente em grama_maquinas — 10 FS220 sem link direto exceto os N escolhidos, 8 GAR, etc.).
3. O fluxo de combustível (`create_combustivel`) continua escrevendo em `grama_maquinas.combustivel_atual` via este mesmo link — não é uma escrita de "identidade duplicada", é uma escrita de dado operacional sem lar em `ativos` (fora do escopo literal de CON-04, que fala especificamente de `uso_atual`).

Esta é a leitura recomendada, mas fica como decisão explícita para o planner confirmar — está listada no Assumptions Log (A2) porque `[ASSUMED]`, não travada em CONTEXT.md.

### 1.6 Frontend impact (cmasm_erp.html)

`cmasm_erp.html:8046` chama `GET /api/grama/maquinas` como parte de `loadVegetalData()` (Promise.all com areas/operacoes/manutencao). `normalizeVegMaq` (linha 7986-8000) consome exatamente: `id, nome, tipo, fabricante, modelo, numero_serie, ano_fabricacao, status, horas_uso, observacoes`. **Nenhuma mudança de contrato de resposta é necessária** se o backend continuar devolvendo este shape via o JOIN proposto em 1.5 — o `id` retornado passa a ser `ativos.id` (`uXX`) em vez de `gmaq-*`; isso é uma mudança de valor, não de shape, mas qualquer código do frontend que persista `maqId` localmente (localStorage) entre sessões deve ser revisto — `saveMaqVegetal`/`getMaqVegetal` fazem cache local (linha ~8052) que será re-sincronizado no próximo `loadVegetalData()`, então não há id "preso" permanentemente no client. Nenhuma referência a `gmaq-` foi encontrada fora de `data/core.db` e `grama.py`/`schema_grama.sql`. `[VERIFIED: grep completo em cmasm_erp.html, assets/*.js, pmoc/]`

---

## §2 — CON-02: `os.lotacao_id` (padrão de migração aditiva)

### 2.1 Padrão exato (citar `backend/db_core.py:57-74`)

```python
# db_core.py — já existe este padrão para ordens_servico; seguir IDENTICAMENTE
os_existing = {row[1] async for row in await db.execute("PRAGMA table_info(ordens_servico)")}
for col, ddl in [
    ("ativo_id",                "ALTER TABLE ordens_servico ADD COLUMN ativo_id TEXT"),
    ("servico_id",              "ALTER TABLE ordens_servico ADD COLUMN servico_id TEXT"),
    # ... existentes ...
    ("departamento",            "ALTER TABLE ordens_servico ADD COLUMN departamento TEXT"),
    # NOVO — CON-02
    ("lotacao_id",              "ALTER TABLE ordens_servico ADD COLUMN lotacao_id TEXT REFERENCES estrutura(id)"),
]:
    if col not in os_existing:
        await db.execute(ddl)
```

Este é o mesmo padrão usado para `locais.estrutura_id` (`db_core.py:45`) e `ativos.local_id` (`db_core.py:37`) — `PRAGMA table_info` seguido de `ALTER TABLE ADD COLUMN` condicional, nunca `DROP`. `[VERIFIED: db_core.py:41-49, 57-74]`

### 2.2 Auto-preenchimento (`main.py`)

`OSIn` (main.py:924-937) precisa de um novo campo opcional:
```python
class OSIn(BaseModel):
    # ...campos existentes...
    lotacao_id: Optional[str] = None  # override explícito do form; se ausente, auto-derivado
```

Em `create_os` (`main.py:2125-2152`), antes do INSERT: se `body.lotacao_id` não foi enviado, derivar a partir do solicitante:
```python
lotacao_id = body.lotacao_id
if not lotacao_id and body.solicitante_id:
    cargo = await db.fetch_one(
        "SELECT unidade_id FROM cargos WHERE usuario_id = ?", (body.solicitante_id,)
    )
    lotacao_id = cargo["unidade_id"] if cargo else None
```
Isso reaproveita exatamente o padrão `cargos.usuario_id → cargos.unidade_id → estrutura.id` já usado em `list_unidades` (`main.py:1130-1137`) e `equipe_refrigeracao` (`main.py:1276-1295`). `[VERIFIED: main.py:1130-1137]` — nota: `cargos.unidade_id` é a PK (uma pessoa por unidade), então `SELECT ... WHERE usuario_id=?` pode retornar 0 ou 1 linha por usuário; usar `fetch_one` (já trata isso). Dado real: 12/12 linhas de `cargos` têm `usuario_id` preenchido — auto-fill terá cobertura completa para solicitantes que ocupam cargo formal.

### 2.3 Não quebra contrato existente

`departamento` (TEXT) permanece intocado — clientes antigos (PMOC/satélites) que não enviam `lotacao_id` continuam funcionando; o campo é `Optional`. `GET /api/os`/`get_os` já fazem `SELECT o.*` (main.py:2092, 2106) — `lotacao_id` aparece automaticamente na resposta sem mudança de código nesses handlers.

---

## §3 — CON-01: Backfill `locais.estrutura_id` e cutover dos org joins

### 3.1 ⚠️ Descoberta crítica de dados (ver Pitfall 1 para detalhe)

`locais.codigo` (163/163 linhas) está no formato `REFRI-<AREA>-<NOME>` (ex.: `REFRI-ADMINISTRATIVA-ACADEMIA`), gerado por um import de climatização anterior (`tools/backfill_local_id.py`, mencionado em CONTEXT). `estrutura.id` (79 linhas) está no formato `CMASM-XX.Y` (ex.: `CMASM-01.2`). **Verificado: 0 de 163 `locais.codigo` batem exatamente com algum `estrutura.id`.** `[VERIFIED: comparação direta de sets em Python contra core.db]`

Isso significa que o backfill **D-04, executado literalmente como descrito, terá 0 matches hoje** — resultado tecnicamente correto (idempotente, sem falha, sem nós sintéticos, todos os 163 entram no relatório de órfãos), mas o plano **não deve prometer "N/163 populado com N>0"** como critério de sucesso; deve prometer "backfill executa, é idempotente, e reporta corretamente 163 órfãos via CON-06" como o resultado esperado desta fase.

### 3.2 Script de backfill (idempotente)

```sql
-- Idempotente: só atualiza linhas ainda não linkadas; reexecutar não duplica/sobrescreve.
UPDATE locais
SET estrutura_id = codigo
WHERE estrutura_id IS NULL
  AND codigo IN (SELECT id FROM estrutura);
```
Rodar isso hoje afeta 0 linhas (confirmado). Deixar o mecanismo pronto é correto porque (a) é o comportamento definido em D-04, (b) se no futuro alguém popular `locais.codigo` com valores no formato `CMASM-XX.Y`, o backfill passa a funcionar sem mudança de código, (c) reexecutável com segurança em qualquer momento (startup do backend, como as outras migrações).

Local de execução recomendado: `backend/db_core.py`, na mesma seção de migrações aditivas (após adicionar a coluna, que já existe — `db_core.py:45`), OU um script standalone em `tools/` (padrão já usado por `tools/backfill_local_id.py`). Como o requisito pede idempotência e é dado (não schema), um script em `tools/` chamável do startup ou manualmente é mais alinhado ao padrão existente do que embutir lógica de dados em `db_core.py` (que hoje só faz DDL condicional, não DML).

### 3.3 Cutover dos org joins (`main.py:1958-1973`, `1979-1992`)

Estado atual:
```python
LEFT JOIN estrutura e ON e.id = COALESCE(l.estrutura_id, l.codigo)
LEFT JOIN cargos c ON c.unidade_id = COALESCE(l.estrutura_id, l.codigo)
```
Isso já tenta `estrutura_id` primeiro (correto por design), caindo para `codigo` só se `estrutura_id` for NULL. **Nenhuma mudança de código é estritamente necessária aqui** — o `COALESCE` já implementa exatamente o comportamento "resolve por FK quando existe, cai para string quando não" que D-04 pede. O que muda é apenas que, quando o backfill popular `estrutura_id` para os casos que baterem (hoje: nenhum), a query passa a usar a FK automaticamente sem precisar de deploy adicional.

Recomendação: **manter o `COALESCE` como está** (é o "fallback que sobrevive enquanto houver órfãos" que D-04 já antecipa) — não remover, não é dívida técnica nesta fase. Documentar no CON-06 quantos locais ainda dependem do fallback `codigo` (hoje: 163/163) para que uma fase futura saiba quando é seguro removê-lo.

---

## §4 — CON-06: `GET /api/admin/integridade`

### 4.1 Padrão de auth a reutilizar

Não existe hoje nenhuma rota que exija especificamente `role == 'admin'` no backend (`_require_escrita`, `main.py:859-863`, só bloqueia `visualizador`). É necessário um novo helper, espelhando o padrão existente:

```python
def _require_admin(user: dict) -> None:
    """CON-06: só role='admin' acessa o relatório de integridade."""
    if user.get("role") != "admin":
        raise HTTPException(403, "Acesso restrito a administradores")
```
Uso: `user = await _require_auth(authorization); _require_admin(user)` — idêntico ao padrão `_require_auth` + `_require_escrita` já usado em 12+ rotas (`main.py:1188-1189, 1220-1221, 1308-1309`, etc.). `[VERIFIED: main.py:845-863]`. Frontend já usa `SESSION.role==='admin'` em múltiplos pontos (`cmasm_erp.html:3033,3822,3903,4816`), e a aba admin já tem CSS class `admin-only` (`cmasm_erp.html:761`) e `div#page-admin` (linha 1514) — o painel de integridade deve ser um novo card dentro de `#page-admin`, não uma página nova.

### 4.2 Queries de integridade concretas (com contagens reais de baseline)

```sql
-- 1. FKs esperadas não populadas
SELECT COUNT(*) FROM locais WHERE estrutura_id IS NULL;                    -- baseline: 163/163
SELECT COUNT(*) FROM estoque WHERE local_id IS NULL;                       -- baseline: 65/65
SELECT COUNT(*) FROM ativos WHERE local_id IS NULL AND categoria != 'climatizacao'; -- RES-06, fora de escopo aqui, só sinalizar
SELECT COUNT(*) FROM ordens_servico WHERE local_id IS NULL;                -- baseline: 3/3 (dataset de dev)

-- 2. `loc` (texto legado) preenchido mas `local_id` nulo — ativos "meio migrados"
SELECT id, nome, loc FROM ativos WHERE loc IS NOT NULL AND loc != '' AND local_id IS NULL;

-- 3. OS com referência não resolvida
SELECT id, codigo FROM ordens_servico WHERE ativo_id IS NOT NULL
  AND ativo_id NOT IN (SELECT id FROM ativos);
SELECT id, codigo FROM ordens_servico WHERE servico_id IS NOT NULL
  AND servico_id NOT IN (SELECT id FROM catalogo_servicos);

-- 4. Órfãos do CON-01 — listar (não só contar), para a lista do relatório
SELECT id, codigo, nome FROM locais WHERE estrutura_id IS NULL ORDER BY codigo;

-- 5. Órfãos do CON-05 — planos sem tipos aplicáveis
SELECT id, codigo, nome FROM catalogo_planos
  WHERE (aplicavel_tipos IS NULL OR aplicavel_tipos = '[]') AND ativo = 1;

-- 6. CON-04 — ativos maquinas_corte sem link a grama_maquinas (se ativos.grama_maquina_id existir)
SELECT id, nome, tipo FROM ativos WHERE categoria='maquinas_corte' AND grama_maquina_id IS NULL;
```

Formato de resposta recomendado (agrupado por categoria, para o painel renderizar seções):
```json
{
  "gerado_em": "2026-07-03T12:00:00Z",
  "categorias": [
    {"chave": "locais_sem_estrutura", "titulo": "Locais sem estrutura_id", "total": 163, "itens": [...]},
    {"chave": "estoque_sem_local", "titulo": "Itens de estoque sem local_id", "total": 65, "itens": [...]},
    {"chave": "os_ativo_nao_resolvido", "titulo": "OS com ativo_id inválido", "total": 0, "itens": []},
    {"chave": "planos_orfaos", "titulo": "Planos sem tipo aplicável", "total": 1, "itens": [...]}
  ]
}
```
Isso é consumível diretamente por um card no painel admin (uma lista de "categorias com badge de contagem", expansível).

---

## §5 — CON-03: Registrar `fonoclama` em `modulos_registrados`

### 5.1 Estado atual confirmado

`modulos_registrados` tem 7 linhas (`pmoc_refrigeracao, pmoc_eletrica, pmoc_predial, pmoc_paiois, pmoc_transportes, pmoc_grama, pmoc_calibracao`) — **nenhuma para fonoclama**. `[VERIFIED: query direta]`. `ativos WHERE categoria='fonoclama'` = **10 linhas**; `catalogo_planos WHERE categoria='fonoclama'` = **5 linhas** — bate exatamente com o número citado em CONTEXT/REQUIREMENTS. `[VERIFIED]`

### 5.2 Seed a adicionar (`data/schema_catalogo.sql:215-222`)

```sql
INSERT OR IGNORE INTO modulos_registrados (nome, descricao, categorias_atend) VALUES
  ('pmoc_refrigeracao', 'Climatização (splits, central)',         '["climatizacao"]'),
  ('pmoc_eletrica',     'Elétrica e geradores',                   '["eletrica"]'),
  ('pmoc_predial',      'Locais e inspeção predial',              '["predial"]'),
  ('pmoc_paiois',       'Paiois e inventário militar',            '["paiois_item"]'),
  ('pmoc_transportes',  'Viaturas e embarcações',                 '["viaturas","embarcacoes"]'),
  ('pmoc_grama',        'Controle vegetal / máquinas de corte',   '["maquinas_corte"]'),
  ('pmoc_calibracao',   'Instrumentos calibrados',                '["instrumentos"]'),
  ('pmoc_fonoclama',    'Sistema de aviso sonoro (fonoclama)',    '["fonoclama"]');  -- NOVO
```
Nomenclatura `pmoc_fonoclama` segue o padrão `pmoc_<domínio>` de todas as outras 7 linhas. **Nota de atenção:** o valor de `nome` é o que o cliente deve passar em `GET /api/sync/manifest?modulo=<nome>` (`sync.py:465,473` — `_modulo_existe(modulo)` compara contra `nome` exato). Se o cliente/teste esperar literalmente `?modulo=fonoclama` (sem prefixo `pmoc_`), ajustar o valor de `nome` para `'fonoclama'` em vez de `'pmoc_fonoclama'` — nenhum código existente no repo faz essa chamada hoje (`[VERIFIED: grep completo, sem ocorrência]`), então a escolha é livre; **recomendo manter o prefixo `pmoc_` por consistência com as 7 linhas existentes**, e o planner deve confirmar contra qualquer teste de aceitação que já exista para CON-03.

### 5.3 Verificação do fluxo (`sync.py:463-576`)

`manifest()` já é 100% genérico sobre `categorias_atend` (`sync.py:475-486` para ativos; `518-550` para planos derivados de `catalogo_planos`) — **nenhuma mudança de código é necessária em `sync.py`**, só a linha de seed. Isso satisfaz literalmente "Sem mudança de contrato — só passa a incluir a categoria que faltava" do D-06.

---

## §6 — CON-05: Arquivar plano climatização órfão

### 6.1 Linha exata identificada

```
id='plano-3c349c22f4', codigo='9C22F4', categoria='climatizacao', aplicavel_tipos='[]', ativo=1
```
`[VERIFIED: query direta]` — é a única linha de `catalogo_planos` com `aplicavel_tipos='[]'` (as outras 12 de climatização, `plano-clima-g1..g12`, têm `aplicavel_tipos=NULL`, que é semanticamente diferente: "não restringido" vs "explicitamente vazio/nenhum tipo").

### 6.2 Opções de flag (Claude's Discretion — nome exato)

**Opção A (mínima, zero migração):** reusar `catalogo_planos.ativo` — `UPDATE catalogo_planos SET ativo=0 WHERE id='plano-3c349c22f4'`. Consistente com Rules.md §9 ("Arquivamento (`ativo=0`) substitui exclusão") e já filtrado automaticamente por `sync.py:519` (`WHERE ativo = 1`). Risco: conflate com "genuinamente inativo por escolha administrativa" — perde a informação "por que foi arquivado".

**Opção B (recomendada — flag dedicado):** nova coluna aditiva, ex. `catalogo_planos.arquivado_motivo TEXT` (nullable), seguindo o padrão do `db_core.py`:
```python
planos_existing = {row[1] async for row in await db.execute("PRAGMA table_info(catalogo_planos)")}
for col, ddl in [
    ("arquivado_motivo", "ALTER TABLE catalogo_planos ADD COLUMN arquivado_motivo TEXT"),
]:
    if col not in planos_existing:
        await db.execute(ddl)
```
E então: `UPDATE catalogo_planos SET ativo=0, arquivado_motivo='CON-05: aplicavel_tipos=[] — sem ativos correspondentes' WHERE id='plano-3c349c22f4' AND arquivado_motivo IS NULL` (idempotente — não sobrescreve se já arquivado). Isso preserva `ativo=0` (comportamento de filtro já correto) mas documenta a causa, diferenciando de outros planos futuramente desativados por outro motivo.

Recomendação: **Opção B** — CONTEXT trata isso como decisão de nome de flag explicitamente separada do conceito genérico `ativo`, sugerindo que reaproveitar `ativo` sozinho não capturaria a intenção.

### 6.3 `planos_manutencao` (documentação, não código)

Tabela existe no schema (`Rules.md §11` documenta o modelo conceitual), mas **0 linhas** em produção — confirmado tabela existe mas vazia. Adicionar a `Rules.md` uma nota explícita (ex. no §11, logo após o bloco de schema conceitual): "`planos_manutencao` — **APOSENTADO**: nunca populada em produção; o modelo de planos vivo é `catalogo_planos` + `catalogo_plano_itens` (§10). Mantida no schema por compatibilidade retroativa, nunca `DROP`." Isso é edição de documentação, não de código/dados.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Comparação idempotente de coluna antes de ALTER | Lógica de migração customizada por tabela | O padrão já estabelecido `PRAGMA table_info` + `if col not in existing` em `db_core.py` | Já testado (`tests/test_migracoes_idempotencia.py`), consistente em todo o repo |
| CRUD de máquinas de corte | Uma segunda API de máquinas em `grama.py` | `/api/ativos` (já existe CRUD completo) | Evita duas fontes de verdade para o mesmo tipo de entidade |
| Auth "role admin" | Middleware novo/decorator novo | Função `_require_admin(user)` espelhando `_require_escrita` | Consistência de padrão, mesma forma de uso (`_require_auth` → `_require_X`) |

**Key insight:** Toda a fase é sobre *reaproveitar* padrões que já existem no repo (migração aditiva, whitelist de edição tipo `_ATIVO_EDIT`, auth por role) — não introduzir nenhuma abstração nova.

## Common Pitfalls

### Pitfall 1: Assumir que o backfill de CON-01 vai popular a maioria dos 163 locais
**What goes wrong:** O plano/execução declara sucesso baseado em "N/163 populado" e é surpreendido ao ver N=0.
**Why it happens:** `locais.codigo` real está em formato `REFRI-<AREA>-<NOME>` (de um import de climatização), não no formato `CMASM-XX.Y` que o comentário do schema (`schema_core.sql:64`) sugere (`-- CMASM-10.2.1, G5, D5`). É um drift entre o schema documentado e os dados seedados depois.
**How to avoid:** Fixar a expectativa no plano: "o backfill roda, é idempotente e correto; resultado esperado hoje é 0 (ou poucos) matches — os 163 vão para o relatório de órfãos do CON-06, isso É o comportamento correto de D-04 (skip + list)."
**Warning signs:** Se o plano tiver um passo de verificação tipo "assert locais.estrutura_id populado > 0", ele vai falhar incorretamente — o critério de aceitação certo é "backfill idempotente + relatório lista os órfãos corretamente", não "X% populado".

### Pitfall 2: Perder granularidade de status ao repontar `grama_maquinas.status` para `ativos.ativo`
**What goes wrong:** `grama_maquinas.status` tem 4 valores (`operacional, em_manutencao, inativo, aposentada`); `ativos.ativo` é boolean (0/1). Um mapeamento ingênuo (`ativo=1` → sempre "operacional") esconde máquinas em manutenção.
**Why it happens:** `ativos` não foi desenhado para granularidade de status operacional por categoria — Rules.md §3 só define `ativo: 1=em serviço, 0=arquivado`.
**How to avoid:** Documentar explicitamente no plano que esta é uma perda de informação aceita (fora do escopo de "uso_atual fonte única"); se granularidade de status for necessária no futuro, seria um novo campo aditivo em `ativos` (ex. `estado_operacional`, que aliás já existe como conceito em `pmoc_refrigeracao._PMOC_EDIT` para outro domínio) — não neste phase.
**Warning signs:** Frontend (`normalizeVegMaq` + `mapVegMachineStatus`) espera um dos 4 valores originais — verificar se `mapVegMachineStatus` (buscar em cmasm_erp.html) trata bem um valor reduzido para 2 estados.

### Pitfall 3: Tratar a escrita de combustível como violação do invariante "sem novos writes" em `grama_maquinas`
**What goes wrong:** Interpretar D-01 literalmente ("sem novos writes") como bloqueio de QUALQUER escrita em `grama_maquinas`, incluindo `create_combustivel` (que hoje atualiza `grama_maquinas.combustivel_atual`), gerando trabalho desnecessário de migrar tracking de combustível para `ativos` (que não tem campo equivalente).
**Why it happens:** Leitura ampla demais do invariante.
**How to avoid:** O invariante do Rules.md §3 e da CONTEXT é especificamente sobre `uso_atual` (horas) ser fonte única — não sobre congelar toda a tabela. Combustível é uma preocupação de domínio distinta sem lar em `ativos`; manter viva em `grama_maquinas` via o link `ativos.grama_maquina_id` é a leitura recomendada (ver §1.5), mas está no Assumptions Log (A2) para confirmação do planner/usuário.
**Warning signs:** Se o plano incluir uma tarefa "adicionar `combustivel_atual` a `ativos`", questionar se isso é realmente necessário para CON-04 ou é escopo extra não pedido.

### Pitfall 4: Assumir que existe uma chave `numero_serie` para casamento gmaq↔ativos
**What goes wrong:** Escrever um script de backfill que faz `WHERE grama_maquinas.numero_serie = ativos.pat` esperando matches, e obter 0 resultados silenciosamente (ambos os campos são `NULL`/vazios na prática, `ativos.pat` também é `NULL` em todas as 28 linhas verificadas).
**Why it happens:** A CONTEXT menciona "modelo/série" como estratégia de casamento, mas os dados reais não têm série capturada em nenhum dos dois lados.
**How to avoid:** Usar `modelo`(grama) → `tipo`(ativos) como único critério de agrupamento; tratar contagens divergentes como ambíguas (ver §1.3) em vez de tentar inferir uma correspondência de série inexistente.
**Warning signs:** Qualquer script de matching que dependa de `numero_serie IS NOT NULL` vai processar 0 linhas.

## Code Examples

### Padrão de migração aditiva (para `os.lotacao_id`)
```python
# Source: backend/db_core.py:57-74 (padrão existente, adaptar)
os_existing = {row[1] async for row in await db.execute("PRAGMA table_info(ordens_servico)")}
for col, ddl in [
    ("lotacao_id", "ALTER TABLE ordens_servico ADD COLUMN lotacao_id TEXT REFERENCES estrutura(id)"),
]:
    if col not in os_existing:
        await db.execute(ddl)
```

### Padrão de auth por role (novo helper para CON-06)
```python
# Source: backend/main.py:859-863 (_require_escrita, espelhar)
def _require_admin(user: dict) -> None:
    if user.get("role") != "admin":
        raise HTTPException(403, "Acesso restrito a administradores")

@app.get("/api/admin/integridade")
async def admin_integridade(authorization: str | None = Header(None)):
    user = await _require_auth(authorization)
    _require_admin(user)
    # ... queries de §4.2 ...
```

### Auto-preenchimento de lotação (CON-02)
```python
# Source: main.py:1130-1137 (padrão cargos→estrutura já usado em list_unidades)
lotacao_id = body.lotacao_id
if not lotacao_id and body.solicitante_id:
    cargo = await db.fetch_one(
        "SELECT unidade_id FROM cargos WHERE usuario_id = ?", (body.solicitante_id,)
    )
    lotacao_id = cargo["unidade_id"] if cargo else None
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| `grama_maquinas` como registro independente de máquinas | `ativos` (categoria `maquinas_corte`) como cadastro mestre; `grama_maquinas` vira satélite de metadados | Esta fase (CON-04) | `uso_atual` deixa de poder divergir entre os dois cadastros |
| Join de organização por string `codigo` | Join por FK `estrutura_id` com fallback `COALESCE` | Esta fase (CON-01), mecanismo pronto; resultado real depende de dados futuros | Nenhuma mudança de comportamento observável hoje (0 matches), mas elimina a dívida de dead-FK |

**Deprecated/outdated:**
- `grama_maquinas` como fonte de `horas_uso`/identidade de máquina — legado, só leitura de metadados extra a partir de agora.
- Nenhuma remoção de tabela — todas seguem existindo (invariante "nunca DROP").

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | "Modelo/série" no matching gmaq↔ativos, na prática, significa só "modelo" (tipo), porque `numero_serie` é `NULL` em 100% das 12 linhas de `grama_maquinas` | §1.2/§1.3 | Baixo — é um fato verificado diretamente no DB, não uma suposição de negócio; risco é apenas se dados de produção tiverem sido alterados desde a leitura desta pesquisa |
| A2 | Combustível/fabricante/série continuam em `grama_maquinas` como satélite ligado por `ativos.grama_maquina_id`, em vez de serem descontinuados ou migrados para novos campos em `ativos` | §1.5, Pitfall 3 | Médio — se o usuário/planner quiser que TODA a funcionalidade de combustível também migre para um novo campo em `ativos`, o escopo do CON-04 cresce; precisa confirmação explícita antes do plano travar isso |
| A3 | Nome do módulo em `modulos_registrados` para fonoclama deve seguir o padrão `pmoc_fonoclama` (com prefixo), não `fonoclama` puro | §5.2 | Baixo-médio — se algum teste de aceitação já esperar `?modulo=fonoclama` sem prefixo, o seed precisa ajustar o valor de `nome`; fácil de corrigir, sem migração de dados envolvida |
| A4 | Atribuição ordinal (por ordem de `id`) é o critério de desambiguação recomendado para os grupos FS220/GAR/TS114, gated atrás de checkpoint humano | §1.3 | Médio — se a atribuição errada for aceita sem revisão, o histórico de horas fica associado ao ativo físico errado; mitigado por exigir checkpoint:human-verify antes de aplicar em produção |
| A5 | Reaproveitar `ativo=0` + novo `arquivado_motivo` (Opção B) é a melhor leitura de "flag de arquivamento" do CON-05, em vez de reusar só `ativo=0` (Opção A) | §6.2 | Baixo — ambas opções satisfazem o requisito funcional (plano some do manifest); é uma diferença de auditabilidade, não de comportamento |

**Se esta tabela estivesse vazia:** não estaria — há decisões de desambiguação de dados que genuinamente carecem de confirmação humana nesta fase.

## Open Questions

1. **Qual é o critério de aceitação real para CON-01 dado que o backfill hoje resulta em 0 matches?**
   - What we know: o mecanismo (backfill idempotente + relatório de órfãos) é exatamente o que D-04 pede.
   - What's unclear: se "sucesso" para o milestone significa apenas "o mecanismo existe e roda corretamente" ou se há expectativa (não documentada) de que alguém vá popular `locais.codigo` com valores reais `CMASM-XX.Y` antes/depois desta fase.
   - Recommendation: Plano deve entregar o mecanismo + relatório; não incluir uma tarefa de "corrigir os 163 códigos" (fora de escopo — seria dado, não schema, e não está em nenhum requisito desta fase).

2. **A atribuição ordinal para FS220/GAR/TS114 deve mesmo escrever um link persistente, ou é suficiente deixar esses ativos sem `grama_maquina_id` (só os 2 casos exatos linkados)?**
   - What we know: só MS650 e SOL têm correspondência inequívoca.
   - What's unclear: se o valor de preservar o histórico de horas dos 10 restantes (FS220×5, GAR×3, TS114×1... total 9, não 10 — conferir) justifica o risco de atribuição errada, versus simplesmente começar `ativos.uso_atual=0` para esses e considerar o histórico do `grama_maquinas` como puramente arquivístico.
   - Recommendation: Planner decide com checkpoint humano; a opção mais conservadora (não linkar os ambíguos, uso_atual começa do zero) é mais segura e mais simples de implementar — recomendo esta como default se não houver forte necessidade de negócio de preservar o histórico agregado.

## Environment Availability

Não aplicável — fase é backend/data-only sobre stack já instalada e rodando (`.venv` presente, FastAPI/aiosqlite já em uso). Nenhuma dependência externa nova, nenhum serviço externo novo.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | Sim (indireto) | Reaproveita `_require_auth` (Bearer token via tabela `sessoes`) — já existente, não alterado nesta fase |
| V4 Access Control | **Sim — novo controle** | CON-06 precisa de `_require_admin(user)` (novo helper) para restringir `/api/admin/integridade` a `role='admin'`; seguir exatamente o padrão `_require_escrita` |
| V5 Input Validation | Sim | `lotacao_id` (CON-02) deve ser validado contra `estrutura.id` existente antes do INSERT (ou aceitar FK solta como o resto do schema já faz — SQLite não impõe FK por padrão sem `PRAGMA foreign_keys=ON`, que não está habilitado no repo — verificar se deve continuar assim por consistência) |
| V6 Cryptography | Não aplica | Nenhum dado sensível novo introduzido |

### Known Threat Patterns for este stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Escalação de privilégio no endpoint de integridade (usuário não-admin acessa dados de auditoria interna) | Elevation of Privilege | `_require_admin` — 403 explícito se `role != 'admin'`, mesmo padrão de `_require_escrita` |
| SQL injection via parâmetros de filtro nas novas queries de integridade | Tampering | Todas as queries em §4.2 usam apenas literais fixas / parâmetros já validados por FastAPI/Pydantic — nenhuma interpolação de string de usuário nessas queries; manter esse padrão ao implementar |
| Vazamento de dados via relatório de integridade (nomes de locais/ativos sensíveis expostos a quem não deveria) | Information Disclosure | Endpoint já gated atrás de `role='admin'`; não expor este endpoint sem autenticação em nenhum cenário (diferente de rotas públicas futuras da Fase 15) |

## Sources

### Primary (HIGH confidence)
- `data/core.db` (produção real) — consultas diretas via `python3 sqlite3` para `grama_maquinas`, `ativos`, `locais`, `estrutura`, `cargos`, `catalogo_planos`, `modulos_registrados`, `ordens_servico`, `estoque`, e todas as tabelas satélite de grama.
- `backend/grama.py`, `backend/main.py`, `backend/sync.py`, `backend/db_core.py`, `data/schema_grama.sql`, `data/schema_core.sql`, `data/schema_catalogo.sql` — leitura completa/segmentada do código-fonte atual.
- `cmasm_erp.html` (grep + leitura segmentada) — consumo real do frontend das rotas `/api/grama/*`.
- `Rules.md` §3, §9, §11 — regras de domínio canônicas.
- `.planning/phases/10-dados-conectividade/10-CONTEXT.md` — decisões travadas.

### Secondary (MEDIUM confidence)
- Nenhuma fonte externa consultada — fase 100% interna ao repositório, sem necessidade de documentação de terceiros.

### Tertiary (LOW confidence)
- Nenhuma.

## Metadata

**Confidence breakdown:**
- Standard stack: N/A — nenhuma dependência nova
- Architecture (repoint de grama, backfill locais, integridade): HIGH — todos os números vêm de queries diretas contra `data/core.db`, não de suposição
- Pitfalls: HIGH — Pitfall 1 e 4 são fatos verificados (0/163 matches, 12/12 numero_serie NULL), não hipóteses
- Decisões de escopo (A2, A3, A5): MEDIUM — tecnicamente corretas mas dependem de confirmação de intenção do usuário/planner

**Research date:** 2026-07-03
**Valid until:** Válido enquanto `data/core.db` de produção não mudar estruturalmente (locais/estrutura/grama_maquinas) — recomendo revalidar contagens se mais de ~2 semanas se passarem antes da execução do plano, ou se algum outro phase tocar essas tabelas antes desta.
