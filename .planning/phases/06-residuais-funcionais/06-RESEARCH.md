# Phase 6: Residuais Funcionais — Research

**Researched:** 2026-06-28
**Domain:** Backend FastAPI + SQLite schema + vanilla-JS frontend (integration surgery)
**Confidence:** HIGH — all findings verified by direct file reads with line citations

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- RES-01: por_tempo avalia `hoje >= ultima_execucao + intervalo_dias`. Gatilho mutuamente exclusivo com por_uso por plano (avaliar só `tipo_gatilho`). Migração aditiva se precisar de coluna.
- RES-02: `departamento` (lotação) gravado na OS: `ALTER TABLE os ADD COLUMN departamento TEXT` guarded. `POST /api/os` aceita e retorna. SR pré-preenche `ativo_id` + `item` via mecanismo `_osPrefill`/`setOsPrefill`.
- RES-03: Backfill/atribuição de `local_id` para ativos não-climatização (script idempotente). `GET /api/ativos` passa a retornar `local_id`. Nunca apagar; só preencher onde NULL. Mapeamento conservador.
- RES-04: Cálculo térmico lê `locais.area_m2` e `altura_m`. NULL/ausente: fallback seguro.
- RES-05: role `visualizador` → 403 em POST/PUT/DELETE de os, ativos, estoque/movimentos, manutenção. GET continua livre. Helper reutilizável `_require_escrita(user)`.

### Claude's Discretion
- Fonte exata de "última execução" para por_tempo.
- Heurística de backfill de local_id (conservadora; manual quando ambíguo).
- Lista exata de rotas de escrita a guardar.

### Deferred Ideas (OUT OF SCOPE)
- Auth hardening (bcrypt, default password) → Fase 7.
- Audit trail completo → v2 (SECA-03).
</user_constraints>

---

## Summary

Esta fase cirurgia 5 pontos residuais no código existente sem introduzir novos módulos ou quebrar contratos de API. Os 5 gaps foram completamente mapeados para localizações exatas de arquivo:linha.

**RES-01** requer extensão da função `manutencao_vencimentos` (main.py:2529) e do helper `_vencimentos_para_ativo` (manutencao.py:65) para avaliar `por_tempo` quando `f.get("tipo") == "por_tempo"`. A fonte de "última execução" é `manut_registros.data` (schema_manutencao.sql) — tabela já existente, mais recente por `ativo_id`. Planos de climatização já carregam `frequencia = {"tipo":"por_tempo","valor":90,"unidade":"dias"}` (main.py:516). A guarda `if f.get("tipo") != "por_uso": continue` (main.py:2568 e manutencao.py:110) é exatamente onde inserir o branch `por_tempo`.

**RES-02** requer: (a) `ALTER TABLE ordens_servico ADD COLUMN departamento TEXT` em db_core.py (padrão já estabelecido para `os_existing` em linha 54); (b) adicionar `departamento: Optional[str] = None` em `OSIn` (main.py:899); (c) incluir `departamento` no INSERT/SELECT de `create_os`/`get_os`; (d) no frontend, estender `novaOSComContexto` / `openModal('modal-nova-sr')` para propagar `ativo_id` e `item` via `_osPrefill`.

**RES-03** requer: (a) adicionar `local_id` à tabela `ativos` via migração em db_core.py (coluna não existe no schema_core.sql nem nas migrações existentes, mas é referenciada no código `_ATIVO_EDIT` e `PUT /api/pmoc/refrigeracao/{id}` que já a atualiza via whitelist); (b) GET /api/ativos usa `SELECT *` então retornará automaticamente após o ALTER; (c) script `tools/backfill_local_id.py` idempotente que só atualiza WHERE `local_id IS NULL`.

**RES-04** `altura_m` é referenciada em main.py:1094 mas NÃO existe em schema_core.sql nem em db_core.py — precisa ser adicionada ao bloco de migrações `locais_existing`. O fallback já funciona no frontend (`altura: env.local_altura_m || 2.7` em erp-refrigeracao.js:153 e `+p.altura || 2.7` em refrig-engine.js:147). Risco: SQLite retorna NULL sem erro se a coluna não existe no banco real — mas o SELECT pode falhar em engines sem graceful NULL-for-missing-col. Migração é mandatória.

**RES-05** `manutencao.py` já tem o padrão exato (linhas 725, 763, 823, 1107, 1144, 1224): `if user.get("role") == "visualizador": raise HTTPException(403, ...)`. O equivalente falta em main.py para as rotas de escrita centrais. Um helper `_require_escrita(user)` extraído e aplicado consistentemente é a abordagem correta.

**Primary recommendation:** Implementar em db_core.py as 3 migrações aditivas necessárias (departamento na OS, local_id em ativos, altura_m em locais), depois estender as lógicas de vencimento e guards de role com os padrões já estabelecidos no codebase.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| por_tempo trigger evaluation | API / Backend | — | Lógica de datas no servidor; frontend exibe resultado |
| departamento na OS | API / Backend (schema + endpoint) | Browser (form prefill) | Campo persistido no DB; frontend preenche do SESSION |
| local_id backfill | Database / Storage (migration script) | API (retornar campo) | Dado persistente; GET já usa SELECT * |
| altura_m em locais | Database / Storage (migration) | Frontend (calcBTU) | Coluna no DB; frontend a lê via API de refrigeração |
| role visualizador 403 | API / Backend | — | Guards de autorização pertencem ao servidor |
| SR prefill ativo+item | Browser / Client | — | Mecanismo `_osPrefill` é puramente frontend localStorage |

---

## RES-01 — por_tempo vencimento trigger

### Localização exata do código atual

**main.py:2529–2583** — `manutencao_vencimentos`
- Linha 2568: `if f.get("tipo") != "por_uso" or not f.get("valor"): continue`
  → Silencia qualquer plano `por_tempo`. Este é o ponto de extensão.

**manutencao.py:65–134** — `_vencimentos_para_ativo` (helper chamado após POST /uso)
- Linha 110: `if f.get("tipo") != "por_uso" or not f.get("valor"): continue`
  → Mesmo problema — por_tempo é ignorado aqui também.

**manutencao.py:368–384** — `get_plano_ativo`
- Linha 368: `if not isinstance(f, dict) or f.get("tipo") != "por_uso":` → retorna `status="POR_TEMPO"`
  → Correto para exibição de status, mas não computa data de alerta.

**manutencao.py:527–528** — `registrar_manutencao`
- Linha 527: `if not isinstance(f, dict) or f.get("tipo") != "por_uso": continue`
  → por_tempo skip no upsert de ativo_plano_estado — CORRETO (estado de uso não se aplica).

### Fonte de "última execução" para por_tempo

`manut_registros` (schema_manutencao.sql) tem coluna `data TEXT NOT NULL` (ISO YYYY-MM-DD) e `ativo_id`. A última execução de um serviço específico (`catalogo_plano_item_id`) pode ser obtida via:

```sql
SELECT MAX(mr.data) AS ultima_data
FROM manut_registros mr
WHERE mr.ativo_id = ? AND JSON_EXTRACT(mr.itens_json, ?) IS NOT NULL
```

**Problema:** `itens_json` é um JSON array de `catalogo_plano_item_id` (ex.: `[12, 15]`). `JSON_EXTRACT` com índice não busca membro de array pelo valor — precisa de `EXISTS (SELECT 1 FROM json_each(mr.itens_json) WHERE value = ?)`.

**Alternativa mais simples e robusta:** `planos_manutencao.ultima_execucao DATE` (schema_catalogo.sql:126) e `catalogo_planos.proxima_execucao DATE` (schema_catalogo.sql:120) — estes campos já existem na tabela `planos_manutencao`. Porém `planos_manutencao` é indicada como "APOSENTADA" (main.py:469,498). O caminho correto é:

1. Usar `manut_registros`: `SELECT MAX(data) AS ultima_data FROM manut_registros WHERE ativo_id = ?` — dá a data da última manutenção registrada para o ativo (não discrimina por item). Para a Fase 6 (MVP), isso é suficiente: se existe execução registrada, usa-a; senão, usa NULL (sem alerta).

2. **Fallback quando `manut_registros` vazio:** não emitir alerta (sem data base = sem gatilho).

### Forma do frequencia JSON para por_tempo

`catalogo_planos.frequencia` = `{"tipo": "por_tempo", "valor": 90, "unidade": "dias"}` (main.py:516 e schema_catalogo.sql:249).
`catalogo_plano_itens.frequencia` = mesmo shape quando override (schema_catalogo.sql:261). Se item não tem override, herda do plano.

### Mudança mínima

Em `manutencao_vencimentos` (main.py:2568) e `_vencimentos_para_ativo` (manutencao.py:110), substituir o `continue` cego por um branch:

```python
if f.get("tipo") == "por_tempo":
    valor = f.get("valor")
    if not valor:
        continue
    # busca última execução do ativo
    ultima = await db.fetch_one(
        "SELECT MAX(data) AS d FROM manut_registros WHERE ativo_id = ?",
        (a["id"],)  # 'a' no context de manutencao_vencimentos; ativo_id no helper
    )
    ultima_data = ultima["d"] if ultima and ultima["d"] else None
    if not ultima_data:
        continue  # sem base de data → sem alerta
    from datetime import date as _date, timedelta
    try:
        dt_ultima = _date.fromisoformat(ultima_data)
    except ValueError:
        continue
    dt_prox = dt_ultima + timedelta(days=int(valor))
    hoje = _date.today()
    falta_dias = (dt_prox - hoje).days
    if falta_dias <= int(valor) * 0.15:  # mesma janela 15% do intervalo
        out.append({ ... "unidade": "dias", "falta": falta_dias, "proximo": dt_prox.isoformat(), ... })
    continue  # não cai no bloco por_uso
elif f.get("tipo") != "por_uso" or not f.get("valor"):
    continue
```

**Contract-break risk:** Nenhum — adiciona itens novos ao response array sem remover os existentes. Clientes que ignoravam por_tempo continuam funcionando.

---

## RES-02 — departamento na OS + SR prefill

### Localização exata — schema

**schema_core.sql:80–104** — `ordens_servico` NÃO tem `departamento`. Coluna ausente.
**db_core.py:54–68** — bloco `os_existing` adiciona colunas a `ordens_servico`. Padrão: PRAGMA → check → ALTER.

### Localização exata — backend

**main.py:899–911** — `class OSIn(BaseModel)`: campos atuais. Adicionar `departamento: Optional[str] = None`.

**main.py:2046–2064** — `create_os`:
- Linha 2051–2053: INSERT com 13 colunas explícitas — precisa adicionar `departamento`.
- Linha 2055–2057: tupla de valores — precisa adicionar `body.departamento`.

**main.py:2025–2043** — `get_os` usa `SELECT o.*` na linha 2027 → `departamento` aparece automaticamente após o ALTER. Sem mudança no SELECT.

### Localização exata — frontend SR prefill

**cmasm_erp.html:2872–2885** — `_osPrefill`, `setOsPrefill`, `novaOSComContexto`. O contexto suporta: `{ativoId, servicoId, assunto, descricao}` (inferido do uso em openModal linha 3178).

**cmasm_erp.html:5297–5303** — `abrirNovaSR(osId)`: abre `modal-nova-sr` com `_currentOSId = osId`. NÃO preenche `ativo_id` nem `item` no formulário SR.

**cmasm_erp.html:2192–2253** — modal `modal-nova-sr`: campos `sr-tipo`, `sr-item-id` (select de estoque), `sr-qtd`, `sr-unidade`. Não há campo para `ativo_id` — SR é criada em contexto de uma OS e o `ativo_id` fica disponível através da OS.

**Análise:** "SR pré-preenche ativo_id + item" significa: quando abrirNovaSR é chamada a partir do contexto de vencimento de manutenção (onde já há ativo_id e servico_id), o modal SR deve pré-selecionar o item de estoque correspondente ao serviço. O mecanismo de pré-preenchimento é estender `abrirNovaSR(osId, ctx?)` para aceitar contexto opcional e preencher `sr-item-id` e `sr-qtd` quando o contexto traz `itemId`.

### Mudança mínima

1. **db_core.py** — adicionar ao bloco `os_existing` (após linha 65):
   ```python
   ("departamento", "ALTER TABLE ordens_servico ADD COLUMN departamento TEXT"),
   ```

2. **main.py:899–911** — adicionar campo em `OSIn`:
   ```python
   departamento: Optional[str] = None
   ```

3. **main.py:2051–2057** — estender INSERT:
   ```python
   # linha 2051: adicionar departamento à lista de colunas
   # linha 2055: adicionar body.departamento à tupla de valores
   ```

4. **cmasm_erp.html** — estender `abrirNovaSR(osId, ctx={})` para aceitar contexto opcional; quando `ctx.itemId` presente, selecionar em `sr-item-id`; quando `ctx.ativoId` presente, incluir info visual.

**Contract-break risk:** Nenhum — `departamento` é campo novo opcional; response `GET /api/os/{id}` usa `SELECT o.*` e incluirá automaticamente. Clientes antigos que não enviam `departamento` recebem NULL (sem erro).

---

## RES-03 — local_id nos ativos (backfill + GET retorna)

### Localização exata — schema

**schema_core.sql:39–51** — tabela `ativos`: NÃO tem coluna `local_id`. Coluna ausente no DDL base.

**db_core.py:27–37** — bloco `existing` para `ativos`: adiciona `subtipo`, `placa`, `criticidade`, `responsavel_pmoc`, `janela_default`. `local_id` NÃO está listado.

**Observação crítica:** `_ATIVO_EDIT` em main.py:1114 já inclui `"local_id"` no whitelist de edição via `PUT /api/pmoc/refrigeracao/{ativo_id}`. Isso significa que o código ESPERA que `local_id` exista em `ativos`, mas a coluna pode não estar criada em instâncias que nunca executaram o ALTER explicitamente. **O campo pode já existir em banco de produção se foi adicionado via path alternativo ou se o test db foi recriado do zero.** Verificar com `PRAGMA table_info(ativos)` em runtime.

**main.py:1152** — `gerar_os_preventiva`: `SELECT id, nome, tipo, local_id FROM ativos WHERE id = ?` — também pressupõe que a coluna existe.

**main.py:1074–1081** — `GET /api/ativos` usa `SELECT *` ou `SELECT *` com filtro de categoria → retornará `local_id` automaticamente se a coluna existir.

**main.py:1227–1232** — `GET /api/ativos/{aid}` usa `SELECT *` → mesmo comportamento.

### Heurística de backfill

Cenário identificado: ativos de categoria `climatizacao` já têm `local_id` ligado via `pmoc_refrigeracao.local_id`. Outros (corte, fonoclama, transportes, etc.) tipicamente têm `local_id IS NULL`.

**Heurística conservadora recomendada:**
- Ativos com ficha `pmoc_refrigeracao`: copiar `pmoc_refrigeracao.local_id` → `ativos.local_id` onde ativos.local_id IS NULL.
- Ativos com ficha `pmoc_transportes`/`pmoc_corte`/`pmoc_fonoclama`: `local_id` ambíguo → deixar NULL, atribuível via ficha no ERP.
- `refri171` (ELETRÔNICA/BIBLIOTECA): a ficha já é editável via `PUT /api/pmoc/refrigeracao/{ativo_id}` com `local_id` no whitelist `_ATIVO_EDIT` (main.py:1114). Não precisa de lógica especial.

### Mudança mínima

1. **db_core.py** — adicionar ao bloco `existing` de `ativos` (após linha 35):
   ```python
   ("local_id", "ALTER TABLE ativos ADD COLUMN local_id INTEGER REFERENCES locais(id)"),
   ```

2. **tools/backfill_local_id.py** — script idempotente:
   ```python
   # UPDATE ativos SET local_id = (SELECT local_id FROM pmoc_refrigeracao WHERE ativo_id = ativos.id)
   # WHERE local_id IS NULL AND id IN (SELECT ativo_id FROM pmoc_refrigeracao WHERE local_id IS NOT NULL)
   ```

3. **main.py:1235–1244** — `create_ativo` e `update_ativo`: AtivoIn não tem `local_id`; o PATCH via ficha de refrigeração já funciona. Considerar adicionar `local_id: Optional[int] = None` a `AtivoIn` e incluir no UPDATE para generalizar (mas não obrigatório para fechar o gap — a ficha existente cobre).

**Contract-break risk:** Baixo. `GET /api/ativos` já usa `SELECT *` — adicionar a coluna só enriquece a resposta. A única preocupação é que `local_id` estava no whitelist `_ATIVO_EDIT` sem que a coluna fosse garantida em db_core — se o banco de produção NÃO tem a coluna, o UPDATE em `_ATIVO_EDIT` falharia silenciosamente (SQLite não valida colunas em SET dynamically formado). A migração em db_core elimina esse risco.

---

## RES-04 — cálculo térmico usa area_m2/altura_m reais

### Localização exata — ausência de altura_m

**schema_core.sql:63–77** — tabela `locais`: tem `area_m2 REAL` (linha 74), mas **NÃO tem `altura_m`**.

**db_core.py:38–45** — bloco `locais_existing`: adiciona `neo`, `restricao`, `estrutura_id`. **`altura_m` ausente.**

**main.py:1094** — `list_refrigeracao` query: `l.altura_m AS local_altura_m` — referencia coluna que pode não existir. SQLite retorna NULL para colunas inexistentes em SELECT (não erro), mas **`INSERT`/`UPDATE` falhariam**. O SELECT funciona por sorte; a coluna precisa existir para ser persistível.

**main.py:1930** — `create_local` INSERT: não inclui `altura_m` — consistente com ausência da coluna.

**main.py:1940** — `update_local` UPDATE: idem.

**LocalIn model (main.py:884–895)**: tem `area_m2: Optional[float] = None` mas NÃO tem `altura_m`.

### Localização exata — cálculo frontend

**assets/refrig-engine.js:145–171** — `calcBTU(p)`:
- Linha 146: `if (!p || !p.area || p.area <= 0) return null` — fallback já implementado: NULL area → retorna null, tela mostra "Pendente".
- Linha 147: `var area = +p.area || 0, altura = +p.altura || 2.7` — fallback para 2.7m se `altura` é falsy.

**assets/erp-refrigeracao.js:147** — `renderTermico`:
- `altura: r.local_altura_m` → alimenta `calcBTU`.
- Linha 153: `var calc = env.area_m2 ? E.calcBTU({ area: env.area_m2, altura: env.altura || 2.7 }) : null` — se `area_m2` NULL, calc = null → `thermalStatus` retorna `{cls:'ts-pending', lbl:'Pendente'}`. Comportamento de fallback já correto.

### O que falta (mudança mínima)

1. **db_core.py** — adicionar ao bloco `locais_existing` (após linha 44):
   ```python
   ("altura_m", "ALTER TABLE locais ADD COLUMN altura_m REAL"),
   ```

2. **main.py:884–895** — `LocalIn`: adicionar `altura_m: Optional[float] = None`.

3. **main.py:1930** — `create_local` INSERT: adicionar `altura_m` à lista de colunas e `body.altura_m` à tupla.

4. **main.py:1940** — `update_local` UPDATE: idem.

**Contract-break risk:** Nenhum. O frontend já tem fallback `|| 2.7`. Se `altura_m` permanece NULL após a migração (registros antigos), o comportamento não muda. Telas existentes não quebram.

---

## RES-05 — role visualizador → 403 em escritas

### Padrão existente (referência canônica)

**manutencao.py:724–726** — PRIMEIRO uso do padrão:
```python
user = await _require_auth(authorization)
if user.get("role") == "visualizador":
    raise HTTPException(403, "Visualizadores não podem criar peças")
```

Ocorre também em manutencao.py: linhas 762–764, 822–824, 1106–1108, 1143–1145, 1223–1225.

### Objeto `user` retornado por _require_auth

**main.py:828–839** — `_require_auth`:
```python
row = await db.fetch_one(
    "SELECT s.usuario_id, u.nome, u.role FROM sessoes s JOIN usuarios u ON u.id = s.usuario_id "
    "WHERE s.token = ? AND s.expira_em > datetime('now')",
    (token,),
)
```
Retorna dict com chaves: `usuario_id`, `nome`, `role`. O campo `role` está sempre presente (NOT NULL com DEFAULT 'operador' no schema).

**manutencao.py:32–44** — `_require_auth` local: idêntico mas adiciona `u.mat`. Inclui `role`.

**schema_core.sql:12** — `role TEXT DEFAULT 'operador' CHECK (role IN ('admin','gestor','operador','visualizador'))`.

### Rotas de escrita em main.py que NÃO têm role guard

As rotas abaixo usam autenticação (`_require_auth`) implícita ou NÃO a usam:

| Rota | Linha | Auth atual | Guard RES-05 |
|------|-------|------------|--------------|
| `POST /api/os` | 2046 | **Nenhuma** | Adicionar auth + guard |
| `PUT /api/os/{id}/status` | 2090 | **Nenhuma** | Adicionar auth + guard |
| `POST /api/ativos` | 1235 | **Nenhuma** | Adicionar auth + guard |
| `PUT /api/ativos/{id}` | 1247 | **Nenhuma** | Adicionar auth + guard |
| `POST /api/estoque` | 2191 | **Nenhuma** | Adicionar auth + guard |
| `PUT /api/estoque/{id}` | 2200 | **Nenhuma** | Adicionar auth + guard |
| `POST /api/estoque/{id}/movimentos` | 2689 | **Nenhuma** | Adicionar auth + guard |
| `POST /api/locais` | 1927 | **Nenhuma** | Adicionar auth + guard |
| `PUT /api/locais/{id}` | 1936 | **Nenhuma** | Adicionar auth + guard |
| `PUT /api/pmoc/refrigeracao/{id}` | 1117 | **Nenhuma** | Adicionar auth + guard |
| `POST /api/pmoc/refrigeracao/{id}/os-preventiva` | 1146 | **Nenhuma** | Adicionar auth + guard |
| `POST /api/manutencao/os-preventiva` | 2586 | **Nenhuma** | Adicionar auth + guard |

**GETs a NÃO guardar:** `GET /api/os`, `GET /api/ativos`, `GET /api/estoque`, `GET /api/locais`, etc. — leitura livre (sessão válida basta).

**Observação:** `POST /api/usuarios`, `PUT /api/usuarios/{id}` (linhas 1033, 1043) criam/atualizam usuários sem auth. Estes são candidatos ao escopo RES-05 também — incluir é conservador e correto.

### Helper recomendado

```python
# Em main.py, após _require_auth (linha 839):
def _require_escrita(user: dict) -> None:
    """Lança 403 se role == 'visualizador'. Chamar APÓS _require_auth."""
    if user.get("role") == "visualizador":
        raise HTTPException(403, "Visualizadores não têm permissão de escrita")
```

Padrão de uso em cada rota:
```python
@app.post("/api/os", status_code=201)
async def create_os(body: OSIn, authorization: str | None = Header(None)):
    user = await _require_auth(authorization)
    _require_escrita(user)
    ...
```

**Contract-break risk:** Rotas que hoje não exigem token passarão a exigir. Isso é intencional para RES-05. Clientes que chamam sem token receberão 401 (não era 403 antes). Verificar se há chamadas internas (seed, migration) que usam estas rotas — nenhuma encontrada no código (seeds usam `db.execute` direto).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---------|-------------|-------------|
| Role check | Custom middleware | `_require_escrita(user)` helper inline |
| Date arithmetic (por_tempo) | Comparação manual de strings | `datetime.date.fromisoformat` + `timedelta` |
| JSON frequencia parse | Regex ou split | `json.loads` com try/except (padrão já existente) |
| Schema migration | DROP/CREATE | `PRAGMA table_info` → condicional `ALTER TABLE ADD COLUMN` |

---

## Common Pitfalls

### Pitfall 1: Dupla avaliação por_uso + por_tempo para o mesmo plano
**O que vai errado:** Se o branch por_tempo não tiver `continue` explícito antes de cair no bloco por_uso, itens sem `valor` em por_uso produzirão divisão por zero.
**Como evitar:** O branch por_tempo deve ter `continue` ou `else` explícito — não deixar cair no fluxo de por_uso.
**Onde:** main.py:2568 e manutencao.py:110.

### Pitfall 2: altura_m NULL no SELECT antes da migração
**O que vai errado:** `SELECT l.altura_m` em main.py:1094 retorna NULL silenciosamente em SQLite se a coluna não existe (comportamento não garantido em todas as versões). Em versões mais novas, pode retornar erro de parsing. A migração em db_core deve vir antes de qualquer código que lê a coluna.
**Como evitar:** Adicionar ao bloco `locais_existing` em db_core.py e reiniciar o server.

### Pitfall 3: _require_auth não está em todas as rotas de escrita de main.py
**O que vai errado:** Diferentemente de manutencao.py (que usa `_require_auth` como primeiro passo em todos os endpoints), main.py tem rotas sem auth (criadas antes da fase de segurança). Adicionar apenas `_require_escrita` sem primeiro chamar `_require_auth` causará NameError.
**Como evitar:** Sempre chamar `user = await _require_auth(authorization)` ANTES de `_require_escrita(user)`.

### Pitfall 4: local_id em AtivoIn vs update_ativo
**O que vai errado:** `update_ativo` (main.py:1247) não inclui `local_id` no UPDATE SQL. Se `AtivoIn` receber `local_id` mas o handler não o passar, o campo é silenciosamente descartado.
**Como evitar:** Se `local_id` for adicionado a `AtivoIn`, adicionar ao UPDATE SQL também.

### Pitfall 5: manut_registros como fonte de última execução — granularidade de item
**O que vai errado:** `MAX(data) FROM manut_registros WHERE ativo_id = ?` dá a última manutenção do ATIVO, não do item específico. Se o ativo tem planos com itens de frequências diferentes, itens mais raros podem ter alerta postergado.
**Aceitável para Fase 6:** O gap é menor que o custo de implementar `json_each` — aceitar como MVP. Anotar para Fase 7 se necessário.

---

## Code Examples

### Padrão de migração aditiva (db_core.py:27–45)
```python
# [ASSUMED] — padrão estabelecido no codebase:
existing = {row[1] async for row in await db.execute("PRAGMA table_info(tabela)")}
for col, ddl in [
    ("nova_coluna", "ALTER TABLE tabela ADD COLUMN nova_coluna TEXT"),
]:
    if col not in existing:
        await db.execute(ddl)
```

### Padrão de role guard (manutencao.py:724–726)
```python
user = await _require_auth(authorization)
if user.get("role") == "visualizador":
    raise HTTPException(403, "Visualizadores não podem criar peças")
```

### calcBTU com fallback (refrig-engine.js:145–147)
```javascript
function calcBTU(p) {
    if (!p || !p.area || p.area <= 0) return null;   // NULL → Pendente
    var area = +p.area || 0, altura = +p.altura || 2.7;  // fallback 2.7m
```

### frequencia JSON shape (catalogado em catalogo_planos)
```json
{"tipo": "por_uso",   "valor": 500, "unidade": "h"}
{"tipo": "por_tempo", "valor": 90,  "unidade": "dias"}
```

---

## Package Legitimacy Audit

Esta fase não instala nenhum pacote externo. Todas as mudanças são em código Python/JS/SQL existente.
**Nenhum pacote a auditar.**

---

## Environment Availability

Esta fase é cirurgia em código existente — sem dependências externas novas. O backend FastAPI, SQLite e o servidor estático já estão em operação.

| Dependency | Required By | Available | Notes |
|------------|------------|-----------|-------|
| aiosqlite | db_core.py migrations | ✓ | já instalado |
| datetime (stdlib) | por_tempo date calc | ✓ | stdlib |
| json (stdlib) | frequencia parse | ✓ | já em uso |

---

## Open Questions

1. **local_id já existe em banco de produção?**
   - O que sabemos: `_ATIVO_EDIT` (main.py:1114) e `SELECT id, nome, tipo, local_id FROM ativos` (main.py:1152) referenciam a coluna, mas db_core.py não tem o ALTER.
   - O que é incerto: Se o banco foi criado do zero recentemente (sem migração manual prévia), a coluna PODE não existir e os SELECTs em main.py:1152 falhariam silenciosamente ou com erro.
   - Recomendação: Adicionar ao bloco `ativos_existing` em db_core.py sem condição — se já existe, `ALTER TABLE ADD COLUMN` em SQLite é idempotente via PRAGMA check.

2. **Granularidade de por_tempo por item vs por ativo**
   - O que sabemos: `manut_registros.itens_json` contém os item_ids executados, mas `json_each` tem suporte variável em versões de SQLite.
   - Recomendação: MVP usa `MAX(data) WHERE ativo_id = ?` (por ativo). Documentar limitação.

---

## Sources

### Primary (HIGH confidence — leitura direta dos arquivos)
- `backend/main.py` — rotas, modelos Pydantic, lógica de vencimentos, auth (verificado linha a linha)
- `backend/manutencao.py` — router de manutenção, padrão role guard, manut_registros
- `backend/db_core.py` — migrações aditivas existentes, padrão PRAGMA
- `data/schema_core.sql` — DDL das tabelas os, ativos, locais, estoque
- `data/schema_catalogo.sql` — DDL catalogo_planos, catalogo_plano_itens com frequencia JSON
- `data/schema_manutencao.sql` — DDL manut_registros, ativo_plano_estado
- `assets/refrig-engine.js` — calcBTU, fallback NULL/altura
- `assets/erp-refrigeracao.js` — renderTermico, uso de area_m2/altura_m
- `cmasm_erp.html` — _osPrefill, setOsPrefill, novaOSComContexto, abrirNovaSR, soLeitura

---

## Metadata

**Confidence breakdown:**
- Localização exata de código: HIGH — verificado por leitura de arquivo com números de linha
- Heurística de backfill RES-03: MEDIUM — decisão conservadora, casos ambíguos requerem confirmação manual
- Fonte última execução RES-01 (granularidade ativo vs item): MEDIUM — solução MVP documentada com limitação conhecida
- Ausência de altura_m em schema: HIGH — confirmado por ausência em schema_core.sql e db_core.py

**Research date:** 2026-06-28
**Valid until:** 2026-07-28 (schema estável; válido por 30 dias)
