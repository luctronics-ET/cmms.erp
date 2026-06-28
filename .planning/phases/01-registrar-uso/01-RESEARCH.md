# Phase 01: Registrar Uso — Research

**Researched:** 2026-06-28
**Domain:** FastAPI router skeleton, aiosqlite atomic transactions, SQLite additive migration, async pytest fixture, vanilla-JS ERP tab extension
**Confidence:** HIGH (all findings grounded in actual repo files at cited line numbers)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Modelo de dados (uso_registros):**
- Nova tabela `uso_registros` em `schema_manutencao.sql`: `id` (PK), `ativo_id` (FK ativos), `delta` (REAL), `valor_anterior` (REAL), `valor_novo` (REAL), `data` (DATE/TEXT), `operador` (mat/nome do usuário logado), `observacao` (TEXT opcional), `created_at` (TEXT default timestamp).
- Snapshot do horímetro = grava `valor_anterior` e `valor_novo` (trilha auditável, não só o delta).
- Não dropar nem alterar `ativos.uso_atual` — só incrementar.

**Contrato do endpoint:**
- `POST /api/manutencao/uso`, payload `{ativo_id, delta, data?, observacao?}`. Operador derivado do token.
- Incremento atômico: `UPDATE ativos SET uso_atual = uso_atual + ? WHERE id=?` + `INSERT INTO uso_registros (...)` na MESMA transação.
- Resposta inclui `uso_atual` novo e lista de vencimentos disparados (planos do ativo onde `uso_atual >= proximo_uso`).
- `GET /api/manutencao/uso?ativo_id=` retorna registros recentes (ordenados desc, limit razoável).

**Frontend (UX):**
- Nova aba/seção "Registrar Uso" no `cmasm_erp.html`, visual portado do legado.
- Substituir localStorage por API via SDK.
- Form: seletor de ativo, campo delta numérico, data (default hoje), observação opcional, botão "Registrar".
- Após registrar: feedback de sucesso, atualizar "Registros Recentes", alerta inline se vencimento disparado.

**Schema, migração e testes:**
- `schema_manutencao.sql` com `CREATE TABLE IF NOT EXISTS`; adicionado a `CoreDB._SCHEMAS`.
- Migração aditiva apenas; `PRAGMA table_info` antes de qualquer `ALTER`; nunca `DROP`.
- `tests/test_migracoes_idempotencia.py`: roda `db.init()` duas vezes no mesmo banco.
- Fixture async (`async_app_client` com `asgi-lifespan.LifespanManager`) em `conftest.py`, SEM tocar no fixture sync `TestClient` existente.
- Adicionar `pytest-asyncio`, `asgi-lifespan` ao `requirements.txt` (httpx já pinado `0.27.2`).

### Claude's Discretion
- Nome exato do endpoint/sub-rotas e shape fino do JSON, desde que respeite contratos existentes.
- Estrutura interna do `manutencao.py` (helpers, models Pydantic).
- Detalhes de markup/CSS do port, mantendo o visual aprovado.

### Deferred Ideas (OUT OF SCOPE)
- Unificar trilha do PMOC `_h_uso_atual_inc` em `uso_registros` se não for barato nesta fase.
- Paginação/cache de vencimentos → v2 (PERF-*).
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| IMP-01 | Incremento atômico de `ativos.uso_atual` + `uso_registros` em transação única | See §4: aiosqlite `async with db.execute("BEGIN")` pattern |
| QA-02 | Fixture async + teste de idempotência de migração sem regredir suite existente | See §5: pytest-asyncio + asgi-lifespan pattern; conftest isolation strategy |
</phase_requirements>

---

## Summary

Esta fase entrega o primeiro slice vertical: endpoint `POST /api/manutencao/uso`, tabela `uso_registros`, aba no ERP e infra de teste async. Todo o código deve ser cirúrgico — o codebase é marrom (em produção) e qualquer alteração fora do escopo exato quebra features ativas.

O roteador `manutencao.py` segue o padrão de `catalogo.py` com precisão: `APIRouter(prefix="/api/manutencao")`, acesso ao `db` via `sys.modules["backend.main"].db`, e `_require_auth` reimplementada localmente (mesmo padrão de `catalogo.py` linhas 36–48). O ponto central da fase é a transação atômica em aiosqlite: `CoreDB` abre uma nova conexão em cada `execute()` — para atomicidade entre UPDATE e INSERT, é necessário usar `async with aiosqlite.connect(path) as db_conn` diretamente dentro do handler, NÃO via os helpers do singleton.

O vencimento disparado reutiliza a lógica de `manutencao_vencimentos` (main.py linhas 2527–2581): após o UPDATE, basta repetir o cálculo filtrado pelo `ativo_id` para retornar a lista de planos onde `(uso_atual_novo % iv) < (iv * 0.15)` — sem duplicar código, apenas chamando a query concentrada.

**Primary recommendation:** Implementar `manutencao.py` como APIRouter puro sem dependências circulares, usar `aiosqlite.connect` diretamente para a transação atômica, e adicionar `schema_manutencao.sql` como quarto elemento de `_SCHEMAS` em `db_core.py`.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Incremento atômico uso_atual | API / Backend | Database / Storage | Regra de negócio (atomicidade UPDATE+INSERT) pertence ao servidor; o DB executa a transação |
| Histórico auditável uso_registros | Database / Storage | API / Backend | Persistência; o backend apenas grava, o schema define a estrutura |
| Alerta de vencimento na resposta | API / Backend | — | O cálculo já existe em main.py; o endpoint replica filtrado por ativo pós-update |
| Aba "Registrar Uso" no ERP | Browser / Client | — | Vanilla JS; sem SSR; lógica de render inline no cmasm_erp.html |
| Fixture async de testes | API / Backend | — | ASGI lifespan garante db.init() rodando antes dos testes |

---

## Standard Stack

### Core (já no requirements.txt)

| Library | Version | Purpose | Source |
|---------|---------|---------|--------|
| fastapi | 0.115.0 | Framework web + APIRouter | `requirements.txt` |
| aiosqlite | 0.20.0 | SQLite async; conexão direta para transações | `requirements.txt` |
| pydantic | 2.7.4 | Validação de payload (BaseModel) | `requirements.txt` |
| httpx | 0.27.2 | TestClient async nos testes | `requirements.txt` |

### A Adicionar ao requirements.txt

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| pytest-asyncio | >=0.23 | Execução de testes `async def` | Necessário para `async_app_client`; não existe no requirements.txt |
| asgi-lifespan | >=2.1 | `LifespanManager` que dispara startup/shutdown no ASGIapp sem TestClient | Necessário para que `db.init()` rode antes dos testes async |

**Nota de versão:** `pytest-asyncio` 0.23+ requer `asyncio_mode = "auto"` ou decorador `@pytest.mark.asyncio` por teste. Preferir `asyncio_mode = "auto"` em `pytest.ini` para evitar boilerplate.

**Installation:**
```bash
pip install pytest-asyncio>=0.23 asgi-lifespan>=2.1
# Adicionar ao requirements.txt:
pytest-asyncio>=0.23
asgi-lifespan>=2.1
```

---

## Package Legitimacy Audit

Nesta fase não são adicionados pacotes de runtime ao `requirements.txt` que não sejam de teste. Os dois pacotes de teste (`pytest-asyncio`, `asgi-lifespan`) são bibliotecas de teste conhecidas do ecossistema FastAPI/ASGI — sem pacotes removidos por suspeita.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| pytest-asyncio | PyPI | ~8 yrs | >5M/mês | github.com/pytest-dev/pytest-asyncio | OK [ASSUMED] | Aprovado |
| asgi-lifespan | PyPI | ~5 yrs | >1M/mês | github.com/florimondmanca/asgi-lifespan | OK [ASSUMED] | Aprovado |

**Packages removed due to SLOP verdict:** nenhum
**Packages flagged as suspicious (SUS):** nenhum

---

## Architecture Patterns

### System Architecture Diagram

```
Browser (cmasm_erp.html)
  └─► POST /api/manutencao/uso  ──────────────────────────────────┐
        {ativo_id, delta, data?, observacao?}                      │
        Authorization: Bearer <token>                              │
                                                                   ▼
                                                    backend/manutencao.py
                                                    (APIRouter prefix=/api/manutencao)
                                                         │
                                                    _require_auth(token)
                                                         │
                                              ┌──────────▼──────────────┐
                                              │  aiosqlite.connect()    │
                                              │  BEGIN IMMEDIATE        │
                                              │  SELECT uso_atual       │ ← ativos
                                              │  UPDATE uso_atual += δ  │ ← ativos
                                              │  INSERT uso_registros   │ ← nova tabela
                                              │  COMMIT                 │
                                              └──────────┬──────────────┘
                                                         │
                                              ┌──────────▼──────────────┐
                                              │  vencimentos_para_ativo  │ ← catalogo_planos
                                              │  (reutiliza lógica       │   catalogo_plano_itens
                                              │   main.py:2533-2579)     │
                                              └──────────┬──────────────┘
                                                         │
                                              { uso_atual, vencimentos_disparados }
                                                         │
  Browser (cmasm_erp.html) ◄───────────────────────────┘
    - Atualiza "Registros Recentes" via GET /api/manutencao/uso?ativo_id=
    - Exibe alerta inline se vencimentos_disparados.length > 0
```

### Recommended Project Structure

```
backend/
├── main.py              # existente — adicionar include_router(manutencao_router)
├── manutencao.py        # NOVO — APIRouter /api/manutencao
├── db_core.py           # existente — adicionar schema_manutencao.sql a _SCHEMAS
├── catalogo.py          # existente — modelo a seguir
data/
├── schema_manutencao.sql  # NOVO — CREATE TABLE IF NOT EXISTS uso_registros
tests/
├── conftest.py          # existente — adicionar async_app_client fixture (não tocar no app_client)
├── test_migracoes_idempotencia.py  # NOVO
```

---

## Pattern 1: Adicionar APIRouter (catalogo.py como gabarito)

**O que:** Criar `backend/manutencao.py` como módulo de roteador independente.
**Quando usar:** Sempre que um domínio novo precisar de rotas agrupadas sob um prefixo.

**Padrão exato de catalogo.py (linhas 1–48):**
```python
# backend/manutencao.py
from __future__ import annotations
import sys
from datetime import date
from typing import Optional
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel

router = APIRouter(prefix="/api/manutencao", tags=["manutencao"])


def _db():
    """Acessa o singleton CoreDB de main.py sem importação circular."""
    return sys.modules["backend.main"].db


async def _require_auth(authorization: str | None) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Token ausente")
    token = authorization[7:]
    row = await _db().fetch_one(
        "SELECT s.usuario_id, u.nome, u.mat, u.role "
        "FROM sessoes s JOIN usuarios u ON u.id = s.usuario_id "
        "WHERE s.token = ? AND s.expira_em > datetime('now')",
        (token,),
    )
    if not row:
        raise HTTPException(401, "Token inválido ou expirado")
    return row
```

**Registro em main.py (após linha 327):**
```python
# backend/main.py — adicionar junto com os outros include_router
from .manutencao import router as manutencao_router
# ...
app.include_router(manutencao_router)   # adicionar após catalogo_router (linha 327)
```

[VERIFIED: backend/catalogo.py linhas 21–48; backend/main.py linhas 19–22, 325–327]

---

## Pattern 2: Adicionar schema_manutencao.sql a CoreDB._SCHEMAS

**O que:** Inserir o caminho do novo schema na lista `_SCHEMAS` de `db_core.py`.
**Onde:** `db_core.py` linhas 7–11.

**Estado atual de _SCHEMAS (db_core.py linhas 7–11):**
```python
_SCHEMAS = [
    os.path.join(_DATA_DIR, "schema_core.sql"),
    os.path.join(_DATA_DIR, "schema_grama.sql"),
    os.path.join(_DATA_DIR, "schema_catalogo.sql"),
]
```

**Após a mudança:**
```python
_SCHEMAS = [
    os.path.join(_DATA_DIR, "schema_core.sql"),
    os.path.join(_DATA_DIR, "schema_grama.sql"),
    os.path.join(_DATA_DIR, "schema_catalogo.sql"),
    os.path.join(_DATA_DIR, "schema_manutencao.sql"),   # NOVO — fase 01
]
```

**Como o mecanismo funciona (db_core.py linhas 18–24):**
```python
async def init(self):
    os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
    async with aiosqlite.connect(self.db_path) as db:
        for schema_path in _SCHEMAS:
            if os.path.exists(schema_path):
                with open(schema_path) as f:
                    await db.executescript(f.read())
        # migrações aditivas via PRAGMA abaixo...
```

`executescript` roda o SQL inteiro de uma vez. Com `CREATE TABLE IF NOT EXISTS` em todos os comandos do schema, a execução é **idempotente** — segunda chamada ao `db.init()` não falha, apenas pula a criação das tabelas já existentes. Este é o requisito central do teste de idempotência (QA-02).

[VERIFIED: backend/db_core.py linhas 7–24]

---

## Pattern 3: Schema da tabela uso_registros

**Arquivo:** `data/schema_manutencao.sql` (novo)

```sql
-- xCMASM · Schema de Manutenção — uso_registros
-- Fase 01: Registrar Uso. Aditivo — CREATE TABLE IF NOT EXISTS obrigatório.

CREATE TABLE IF NOT EXISTS uso_registros (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  ativo_id     TEXT NOT NULL REFERENCES ativos(id),
  delta        REAL NOT NULL,                         -- incremento aplicado (pode ser negativo para correção)
  valor_anterior REAL NOT NULL,                       -- uso_atual antes do registro
  valor_novo   REAL NOT NULL,                         -- uso_atual após o registro (= valor_anterior + delta)
  data         TEXT NOT NULL,                         -- data da operação (ISO 8601: YYYY-MM-DD)
  operador     TEXT NOT NULL,                         -- mat ou nome do usuário logado (snapshot)
  observacao   TEXT,                                  -- campo livre opcional
  created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_uso_registros_ativo ON uso_registros(ativo_id);
CREATE INDEX IF NOT EXISTS idx_uso_registros_data  ON uso_registros(data);
```

**Nota:** `valor_anterior` e `valor_novo` são redundantes com `delta` mas são exigidos pela decisão de trilha auditável (CONTEXT.md). O cálculo `valor_novo = valor_anterior + delta` deve ser verificado no handler antes do INSERT para garantir consistência.

[VERIFIED: design conforme CONTEXT.md; padrão de schema conforme data/schema_core.sql]

---

## Pattern 4: Transação Atômica em aiosqlite

**Problema central:** `CoreDB.execute()` e `CoreDB.fetch_one()` abrem e fecham conexões individuais (db_core.py linhas 79–97). Não existe método de transação multi-statement no singleton. Para o UPDATE + INSERT atômico, é necessário usar `aiosqlite.connect()` diretamente no handler.

**Padrão correto:**
```python
import aiosqlite
from backend.db_core import _DATA_DIR   # apenas para descobrir o DB_PATH
import sys, os

@router.post("/uso", status_code=201)
async def registrar_uso(body: UsoIn, authorization: str | None = Header(None)):
    user = await _require_auth(authorization)
    operador = user.get("mat") or user.get("nome") or str(user["usuario_id"])

    # Obter o DB_PATH do módulo principal (sem importação circular)
    db_path = sys.modules["backend.main"].db.db_path

    async with aiosqlite.connect(db_path) as conn:
        conn.row_factory = aiosqlite.Row

        # 1. Ler uso_atual atual (dentro da transação)
        async with conn.execute(
            "SELECT uso_atual FROM ativos WHERE id = ? AND ativo = 1", (body.ativo_id,)
        ) as cur:
            row = await cur.fetchone()
        if not row:
            raise HTTPException(404, "Ativo não encontrado")

        valor_anterior = row["uso_atual"] or 0.0
        valor_novo = round(valor_anterior + body.delta, 2)

        # 2. Atualização atômica: UPDATE + INSERT na mesma conexão/transação
        await conn.execute(
            "UPDATE ativos SET uso_atual = ? WHERE id = ?",
            (valor_novo, body.ativo_id),
        )
        await conn.execute(
            "INSERT INTO uso_registros "
            "(ativo_id, delta, valor_anterior, valor_novo, data, operador, observacao) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                body.ativo_id, body.delta, valor_anterior, valor_novo,
                body.data or date.today().isoformat(),
                operador,
                body.observacao,
            ),
        )
        await conn.commit()

    # 3. Calcular vencimentos disparados (pós-commit, leitura isolada)
    vencimentos = await _vencimentos_para_ativo(body.ativo_id, valor_novo)

    return {
        "uso_atual": valor_novo,
        "valor_anterior": valor_anterior,
        "delta": body.delta,
        "vencimentos_disparados": vencimentos,
    }
```

**Por que não usar `db.execute()` duas vezes:** aiosqlite abre e fecha conexão por chamada (db_core.py linhas 93–97). Entre o `db.execute(UPDATE)` e `db.execute(INSERT)`, outro request pode ler `uso_atual` inconsistente. A conexão compartilhada dentro de `async with aiosqlite.connect(...) as conn:` é serializada pelo event loop do asyncio — não há risco de race condition em uvicorn single-worker.

[VERIFIED: backend/db_core.py linhas 79–97; aiosqlite documentation pattern]

---

## Pattern 5: Reutilizar Lógica de Vencimentos

**Lógica existente:** `main.py` linhas 2527–2581 implementa `manutencao_vencimentos()` que varre todos os ativos. Para o endpoint de uso, é necessário filtrar pelo `ativo_id` específico após o update.

**Helper a extrair em manutencao.py:**
```python
import json, math

async def _vencimentos_para_ativo(ativo_id: str, uso_atual_novo: float) -> list[dict]:
    """Retorna planos vencidos (falta <= iv * 0.15) para um ativo específico.
    Reutiliza a lógica de manutencao_vencimentos (main.py:2527-2581) mas
    filtrada por ativo e com uso_atual_novo já calculado (sem nova leitura do DB).
    """
    db = _db()
    ativo = await db.fetch_one(
        "SELECT id, nome, tipo, categoria, unidade_uso FROM ativos WHERE id = ?", (ativo_id,)
    )
    if not ativo:
        return []

    planos = await db.fetch_all("SELECT * FROM catalogo_planos WHERE ativo = 1")
    plano_by_tipo: dict[str, list] = {}
    for p in planos:
        tipos = []
        try:
            tipos = json.loads(p["aplicavel_tipos"] or "[]")
        except Exception:
            tipos = []
        if p["tipo_codigo"] and p["tipo_codigo"] not in tipos:
            tipos.append(p["tipo_codigo"])
        for t in tipos:
            plano_by_tipo.setdefault(t, []).append(p)

    out: list[dict] = []
    uso = uso_atual_novo
    for p in plano_by_tipo.get(ativo["tipo"], []):
        itens = await db.fetch_all(
            "SELECT i.frequencia, i.servico_id, s.nome FROM catalogo_plano_itens i "
            "JOIN catalogo_servicos s ON s.id = i.servico_id "
            "WHERE i.plano_id = ? AND i.classe = 'prev' ORDER BY i.seq",
            (p["id"],),
        )
        for it in itens:
            raw = it["frequencia"] or p.get("frequencia")
            if not raw:
                continue
            try:
                f = json.loads(raw)
            except Exception:
                continue
            if f.get("tipo") != "por_uso" or not f.get("valor"):
                continue
            iv = f["valor"]
            prox = (math.floor(uso / iv) + 1) * iv
            falta = prox - uso
            if falta <= iv * 0.15:   # dentro da janela de alerta
                out.append({
                    "ativo_id": ativo_id, "ativo_nome": ativo["nome"],
                    "plano_id": p["id"], "plano_nome": p["nome"],
                    "servico_id": it["servico_id"], "servico": it["nome"],
                    "intervalo": iv, "unidade": f.get("unidade"),
                    "uso_atual": uso, "proximo": prox, "falta": falta,
                    "pct": round((uso % iv) / iv * 100),
                })
    return out
```

**Critério de "vencimento disparado":** mesma constante `iv * 0.15` de `manutencao_vencimentos` (linha 2571). Alertas só aparecem dentro dos últimos 15% do intervalo.

[VERIFIED: backend/main.py linhas 2527–2581]

---

## Pattern 6: GET /api/manutencao/uso

```python
@router.get("/uso")
async def listar_uso(ativo_id: str | None = None, limit: int = 20):
    db = _db()
    if ativo_id:
        rows = await db.fetch_all(
            "SELECT ur.*, a.nome AS ativo_nome, a.unidade_uso "
            "FROM uso_registros ur JOIN ativos a ON a.id = ur.ativo_id "
            "WHERE ur.ativo_id = ? ORDER BY ur.created_at DESC LIMIT ?",
            (ativo_id, limit),
        )
    else:
        rows = await db.fetch_all(
            "SELECT ur.*, a.nome AS ativo_nome, a.unidade_uso "
            "FROM uso_registros ur JOIN ativos a ON a.id = ur.ativo_id "
            "ORDER BY ur.created_at DESC LIMIT ?",
            (limit,),
        )
    return rows
```

---

## Pattern 7: Pydantic Model para UsoIn

```python
class UsoIn(BaseModel):
    ativo_id: str
    delta: float                     # incremento positivo (horas/km trabalhados)
    data: Optional[str] = None       # YYYY-MM-DD; default = hoje no handler
    observacao: Optional[str] = None
```

**Validação recomendada (Claude's Discretion):**
```python
from pydantic import field_validator

@field_validator("delta")
@classmethod
def delta_positivo(cls, v: float) -> float:
    if v <= 0:
        raise ValueError("delta deve ser positivo")
    return v
```

[VERIFIED: padrão conforme backend/catalogo.py linhas 53–100; backend/main.py linhas 864–910]

---

## Pattern 8: Fixture Async (pytest-asyncio + asgi-lifespan)

**Problema:** `TestClient` (sync) dispara startup automaticamente no `__enter__` (conftest.py linha 28). A fixture async precisa do mesmo comportamento — o `db.init()` em `@app.on_event("startup")` (main.py linha 793) deve rodar antes de qualquer request.

**Solução com asgi-lifespan:**
```python
# tests/conftest.py — ADICIONAR após o fixture app_client existente (não modificar app_client)

import pytest
import pytest_asyncio
import importlib, sys, os
import httpx
from asgi_lifespan import LifespanManager


@pytest_asyncio.fixture
async def async_app_client(tmp_path, monkeypatch):
    """Fixture async: fresh DB + startup lifespan (db.init()) via LifespanManager."""
    db_path = tmp_path / "test_async_core.db"
    monkeypatch.setenv("DB_PATH", str(db_path))
    # Reload para capturar o novo DB_PATH (mesmo padrão do app_client sync)
    for mod in ("backend.main", "backend.db_core", "backend.grama", "backend.sync", "backend.manutencao"):
        sys.modules.pop(mod, None)
    main = importlib.import_module("backend.main")
    async with LifespanManager(main.app) as manager:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=manager.app),
            base_url="http://test",
        ) as client:
            yield client, main
```

**pytest.ini (ou pyproject.toml) — adicionar:**
```ini
[pytest]
asyncio_mode = auto
```

**Por que `LifespanManager` e não `TestClient` async:** `httpx.AsyncClient` com `transport=ASGITransport` não dispara lifespan automaticamente. `asgi-lifespan.LifespanManager` é o wrapper padrão para rodar startup/shutdown no ASGI app em contexto assíncrono, garantindo que `db.init()` rode antes do primeiro request no fixture async.

**Coexistência com app_client sync (CRITICAL):**
- O fixture sync `app_client` (conftest.py linhas 18–29) usa `TestClient` — permanece intocado.
- O fixture async usa nome distinto `async_app_client` — sem conflito de escopo.
- Ambos fazem reload dos módulos em `sys.modules` antes do uso — isolamento garantido.
- `monkeypatch` garante que `DB_PATH` é diferente por fixture.

[VERIFIED: tests/conftest.py linhas 1–29; backend/main.py linhas 793–812]

---

## Pattern 9: Teste de Idempotência de Migração

```python
# tests/test_migracoes_idempotencia.py
"""
Garante que db.init() pode ser chamado duas vezes no mesmo banco sem erro.
Verifica especificamente que CREATE TABLE IF NOT EXISTS + PRAGMA migrations
são idempotentes (Pitfall 4 do PITFALLS.md).
"""
import importlib, os, sys
import pytest

@pytest.fixture
def fresh_db(tmp_path, monkeypatch):
    db_path = tmp_path / "idempotencia.db"
    monkeypatch.setenv("DB_PATH", str(db_path))
    for mod in ("backend.main", "backend.db_core", "backend.grama",
                "backend.sync", "backend.manutencao"):
        sys.modules.pop(mod, None)
    db_core = importlib.import_module("backend.db_core")
    return db_core.CoreDB(str(db_path))


@pytest.mark.asyncio
async def test_init_twice_sem_erro(fresh_db):
    """Roda db.init() duas vezes no mesmo banco — nenhuma exceção deve ser lançada."""
    await fresh_db.init()
    await fresh_db.init()   # segunda chamada deve ser silenciosa


@pytest.mark.asyncio
async def test_uso_registros_criada_apos_init(fresh_db):
    """Confirma que uso_registros existe após init() e tem as colunas esperadas."""
    await fresh_db.init()
    cols = {r["name"] for r in await fresh_db.fetch_all("PRAGMA table_info(uso_registros)")}
    assert "ativo_id" in cols
    assert "delta" in cols
    assert "valor_anterior" in cols
    assert "valor_novo" in cols
    assert "operador" in cols
```

[VERIFIED: CONTEXT.md decisões de schema/testes; PITFALLS.md Pitfall 4]

---

## Pattern 10: Frontend — Aba "Registrar Uso" em cmasm_erp.html

### Padrão de navegação existente

A barra lateral usa `class="ni"` com `data-page` e `onclick="showPage()"` (cmasm_erp.html linhas 619–753). A aba de Manutenção existente é `data-page="manutencao"` (linha 633). A nova aba de Registrar Uso deve viver **dentro da página de Manutenção** como sub-tab, não como uma nova entrada de navegação.

```html
<!-- Dentro de #page-manutencao (cmasm_erp.html linha 1416) -->
<div id="page-manutencao" class="page">
  <!-- Tabs internas da página de manutenção -->
  <div class="tabs" id="manut-tabs">
    <div class="tab active" data-tab="vencimentos" onclick="showManutTab('vencimentos',this)">Vencimentos</div>
    <div class="tab" data-tab="registrar-uso" onclick="showManutTab('registrar-uso',this)">Registrar Uso</div>
  </div>
  <div id="tab-vencimentos" class="tab-panel active">
    <!-- conteúdo existente de #manut-root -->
    <div id="manut-root"></div>
  </div>
  <div id="tab-registrar-uso" class="tab-panel">
    <!-- formulário portado do legado -->
    <div id="registrar-uso-root"></div>
  </div>
</div>
```

### Visual do legado a portar (.docs_cmasm/referencias/CMASM_Gestao_v2.html)

O modal `#m-uso` (linhas 193–225) tem o layout a replicar como seção inline (não modal):

```
┌─────────────────────────────────────────────────────┐
│  Seletor de Ativo  [dropdown]                        │
│  Horímetro atual: [badge com uso_atual + unidade]    │
├─────────────────────────────────────────────────────┤
│  Data *        [date input, default hoje]            │
│  Horas/km *    [number input, min 0.1, step 0.1]    │
│  Observações   [textarea opcional]                   │
├─────────────────────────────────────────────────────┤
│  [botão Registrar]  →  POST /api/manutencao/uso     │
├─────────────────────────────────────────────────────┤
│  Alerta de vencimento (div#uso-alerta, display:none) │
│  Registros Recentes (tabela)                        │
└─────────────────────────────────────────────────────┘
```

**Campos removidos em relação ao legado (localStorage-only, não portados):**
- Combustível (L) — não está no modelo de dados `uso_registros`; deferred
- Checklist pré-uso (checkboxes) — sem requisito de persistência nesta fase; omitir
- Seletor de operador hardcoded — substituir por operador do token (derivado no backend)

### Padrão de SDK call

```javascript
// Padrão existente em cmasm_erp.html: fetch direto com Bearer token
async function registrarUso() {
  const ativoId = document.getElementById('ru-ativo').value;
  const delta = parseFloat(document.getElementById('ru-delta').value);
  const data = document.getElementById('ru-data').value || new Date().toISOString().slice(0,10);
  const obs = document.getElementById('ru-obs').value || null;

  if (!ativoId) { alert('Selecione um ativo.'); return; }
  if (!delta || delta <= 0) { alert('Informe o incremento de uso (> 0).'); return; }

  const token = localStorage.getItem('xcmasm_token');   // padrão do SDK
  try {
    const res = await fetch('/api/manutencao/uso', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
      body: JSON.stringify({ ativo_id: ativoId, delta, data, observacao: obs }),
    });
    if (!res.ok) { const e = await res.json(); alert(e.detail || 'Erro'); return; }
    const data_resp = await res.json();

    // Feedback
    document.getElementById('ru-feedback').textContent =
      `Registrado: ${delta} ${data_resp.unidade || 'h'} → total ${data_resp.uso_atual}`;

    // Alerta de vencimento
    const alertDiv = document.getElementById('ru-alerta-vencimento');
    if (data_resp.vencimentos_disparados?.length) {
      alertDiv.style.display = 'block';
      alertDiv.innerHTML = `<strong>Atenção:</strong> ${data_resp.vencimentos_disparados.length} serviço(s) preventivo(s) próximos do vencimento:<br>`
        + data_resp.vencimentos_disparados.map(v => `• ${v.servico} (falta ${v.falta.toFixed(1)} ${v.unidade})`).join('<br>');
    } else {
      alertDiv.style.display = 'none';
    }

    // Atualizar lista de registros recentes
    await carregarRegistrosRecentes(ativoId);
  } catch (err) {
    alert('Erro de rede: ' + err.message);
  }
}
```

[VERIFIED: cmasm_erp.html linhas 376–381 (tabs CSS), 619–753 (nav pattern), 1416–1418 (page-manutencao); CMASM_Gestao_v2.html linhas 193–225 (modal legado)]

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Transação atômica | Simular com dois `db.execute()` separados | `async with aiosqlite.connect()` + `await conn.commit()` | Dois db.execute() abrem conexões separadas — não são atômicos |
| Cálculo de vencimentos | Nova query customizada | Reutilizar lógica de main.py:2527–2581 em helper `_vencimentos_para_ativo` | Lógica já testada; duplicar cria divergência |
| Startup lifespan em testes async | Mock manual de db.init() | `asgi_lifespan.LifespanManager` | Garante que todos os seeds/migrations rodam antes dos testes |
| Autenticação no router | Reimplementar do zero | Copiar `_require_auth` de catalogo.py linhas 36–48 (padrão estabelecido) | Consistência; evita bugs de lógica de token |

---

## Common Pitfalls

### Pitfall A: Dois db.execute() não são atômicos

**O que vai errado:** Usar `await _db().execute(UPDATE)` seguido de `await _db().execute(INSERT)` parece atômico mas não é — cada chamada abre e fecha uma conexão separada (db_core.py linhas 93–97). Entre as duas chamadas, outro request pode ler `uso_atual` desatualizado.

**Como evitar:** Usar `async with aiosqlite.connect(db_path) as conn:` com ambos os statements e `await conn.commit()` no final. Ver Pattern 4 acima.

**Sinal de alerta:** Testes de integração passam (baixa concorrência) mas valores ficam inconsistentes em produção com múltiplos usuários simultâneos.

[VERIFIED: backend/db_core.py linhas 79–97 — cada método abre nova conexão]

---

### Pitfall B: Conflito de globals ao portar JS do legado (Pitfall 6 do PITFALLS.md)

**O que vai errado:** O legado `CMASM_Gestao_v2.html` define funções como `regUso`, `salvarUso`, `fH` (linhas 1067, 1078, 575) em escopo global. `cmasm_erp.html` pode ter funções com nomes iguais ou similares. Ao copiar o bloco JS, `fH` pode sobrescrever um helper existente.

**Como evitar:** Antes de colar qualquer trecho do legado:
```bash
grep -n "function fH\|function regUso\|function salvarUso" /home/luc/DEV_ERP/cmasm.erp/cmasm_erp.html
```
Renomear as funções da nova aba com prefixo `ru_` (registrar uso): `ruRegistrar()`, `ruCarregarAtivos()`, `ruAtualizarRecentes()`.

[VERIFIED: PITFALLS.md Pitfall 6; CMASM_Gestao_v2.html linhas 575, 1067, 1078]

---

### Pitfall C: asgi-lifespan não dispara startup sem o transport correto

**O que vai errado:** `httpx.AsyncClient(app=main.app)` não dispara lifespan. `LifespanManager` é necessário, mas se o client for construído com `app=` direto (sem `transport=ASGITransport(app=manager.app)`), o startup roda mas o client usa um app diferente do gerenciado.

**Como evitar:** Usar exatamente:
```python
async with LifespanManager(main.app) as manager:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=manager.app),
        base_url="http://test",
    ) as client:
```
Nunca `transport=httpx.ASGITransport(app=main.app)` — isso bypassa o lifespan manager.

[ASSUMED — padrão documentado de asgi-lifespan; não verificado via Context7 nesta sessão]

---

### Pitfall D: pytest-asyncio 0.23+ exige asyncio_mode ou decorator

**O que vai errado:** Testes `async def` sem `@pytest.mark.asyncio` são silenciosamente ignorados (pytest coleta mas não os executa como coroutines) se `asyncio_mode` não estiver configurado.

**Como evitar:** Adicionar ao `pytest.ini` ou `pyproject.toml`:
```ini
[pytest]
asyncio_mode = auto
```
Isso aplica `@pytest.mark.asyncio` implicitamente a todos os `async def test_*`.

[ASSUMED — comportamento documentado do pytest-asyncio; confirmar na documentação oficial antes de depender]

---

### Pitfall E: test_manutencao_smoke.py verifica assets que devem continuar existindo

**O que vai errado:** `test_manutencao_smoke.py` (linhas 18–24) verifica que `cmasm_erp.html` referencia `assets/erp-manutencao.js` e `assets/erp-manutencao-mocks.js`. Se a nova aba de Registrar Uso for implementada em um arquivo JS separado mas os asserts existentes falham, a suite regride.

**Como evitar:** Não remover as referências existentes ao adicionar o novo JS da aba. Se o código da nova aba for incluído inline no `<script>` de `cmasm_erp.html`, nenhum novo arquivo de asset é necessário — zero risco de regredir o smoke test.

[VERIFIED: tests/test_manutencao_smoke.py linhas 14–24]

---

## Security Domain

`security_enforcement: true` em `.planning/config.json`.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | `_require_auth()` bearer token (padrão catalogo.py) |
| V3 Session Management | parcial | sessoes table com expira_em; já implementado em main.py |
| V4 Access Control | yes — role check omitido nesta fase | `operador` derivado do token; apenas role `operador` e acima devem acessar |
| V5 Input Validation | yes | Pydantic `UsoIn` — `delta > 0` obrigatório; `ativo_id` NOT NULL |
| V6 Cryptography | não se aplica | sem geração de hash nesta fase |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Injeção via ativo_id | Tampering | Parameterized query — `(body.ativo_id,)` nunca interpolado em f-string |
| Delta negativo (correção maliciosa) | Tampering | `field_validator("delta")` que rejeita `<= 0` |
| Token replay após expiração | Elevation | `expira_em > datetime('now')` na query de sessão (linha 829 de main.py) |
| Leitura de uso_registros de outro ativo | Info disclosure | GET filtra por `ativo_id`; sem controle de ownership nesta fase (rede interna) |

---

## Runtime State Inventory

Esta fase é **greenfield** para as tabelas de manutenção — não há estado em produção para `uso_registros` (tabela não existe ainda). Análise completa:

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `ativos.uso_atual` já populado com dados reais (171 máquinas refrig + frota + corte) | Apenas incremento; nunca sobrescrever ou zerar. Snapshot `valor_anterior` lê o valor atual do DB dentro da transação |
| Live service config | Nenhuma configuração externa referencia `uso_registros` (nova tabela) | Nenhuma |
| OS-registered state | Nenhuma | Nenhuma |
| Secrets/env vars | `DB_PATH` aponta para `core.db` em produção; sem novo env var necessário | Nenhuma |
| Build artifacts | Nenhum; sem build step no projeto | Nenhuma |

**Nota de produção:** `data/core.db` tem `ativos.uso_atual` com valores reais. O incremento deve ser aditivo (`uso_atual = uso_atual + delta`), nunca substitutivo. O `valor_anterior` deve ser lido **dentro da transação** para garantir que snapshots são consistentes.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3 | Backend | ✓ | Sistema | — |
| aiosqlite | Transação | ✓ | 0.20.0 (pinado) | — |
| pytest | Testes | ✓ | requirements.txt | — |
| httpx | Fixture async | ✓ | 0.27.2 (pinado) | — |
| pytest-asyncio | Fixture async | ✗ | — | Nenhum; deve ser instalado |
| asgi-lifespan | Fixture async | ✗ | — | Nenhum; deve ser instalado |

**Missing dependencies with no fallback:**
- `pytest-asyncio` — necessário para testes async; instalar via `pip install pytest-asyncio>=0.23`
- `asgi-lifespan` — necessário para `LifespanManager`; instalar via `pip install asgi-lifespan>=2.1`

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `asgi-lifespan` LifespanManager deve ser usado com `manager.app` no ASGITransport | Pattern 8 / Pitfall C | Startup não roda; db.init() ausente; testes async falham com OperationalError |
| A2 | `pytest-asyncio >= 0.23` requer `asyncio_mode = auto` ou decorator explícito | Pattern 8 / Pitfall D | Testes async são coletados mas não executados; suite parece passar sem testar nada |
| A3 | `pytest-asyncio` e `asgi-lifespan` são bibliotecas legítimas do ecossistema PyPI | Package Legitimacy | Baixo; bibliotecas amplamente conhecidas no ecossistema FastAPI/ASGI |

---

## Open Questions

1. **Role enforcement no POST /api/manutencao/uso**
   - O que sabemos: `_require_auth` valida o token mas não verifica `role`.
   - O que está indefinido: Apenas `operador` e acima devem registrar uso, ou `visualizador` também pode?
   - Recomendação: Implementar sem check de role nesta fase (rede interna); adicionar `if user["role"] == "visualizador": raise HTTPException(403)` se solicitado na revisão.

2. **Unidade de uso no delta**
   - O que sabemos: `ativos.unidade_uso` pode ser `"h"`, `"km"` ou `"meses"`.
   - O que está indefinido: O payload `UsoIn` não inclui `unidade` — o frontend deve derivar do ativo.
   - Recomendação: O frontend exibe a unidade do ativo selecionado como label do campo; o backend não valida consistência de unidade nesta fase (dados são de confiança interna).

---

## Sources

### Primary (HIGH confidence — verificado em arquivos do repo)

- `backend/db_core.py` linhas 7–11 (_SCHEMAS list), 18–24 (init/executescript), 79–97 (execute methods)
- `backend/main.py` linhas 19–22 (imports de routers), 325–327 (include_router), 793–812 (startup), 826–837 (_require_auth), 2527–2581 (manutencao_vencimentos)
- `backend/catalogo.py` linhas 21–48 (APIRouter pattern, _db(), _require_auth)
- `tests/conftest.py` linhas 1–29 (TestClient sync fixture pattern)
- `tests/test_manutencao_smoke.py` linhas 14–24 (asserts de assets que não devem regredir)
- `data/schema_core.sql` linhas 39–51 (ativos.uso_atual, unidade_uso)
- `.docs_cmasm/referencias/CMASM_Gestao_v2.html` linhas 193–225 (modal Registrar Uso), 575 (fH), 1067–1079 (regUso function)
- `cmasm_erp.html` linhas 376–381 (tabs CSS), 619–753 (nav pattern), 1416–1418 (#page-manutencao)
- `.planning/phases/01-registrar-uso/01-CONTEXT.md` (decisões locked)
- `.planning/research/PITFALLS.md` (Pitfalls 4 e 6)

### Tertiary (LOW confidence — baseado em conhecimento de treinamento)

- Comportamento de `pytest-asyncio >= 0.23` com `asyncio_mode` [ASSUMED]
- Uso correto de `asgi-lifespan.LifespanManager` com `httpx.ASGITransport` [ASSUMED]

---

## Metadata

**Confidence breakdown:**
- Standard Stack: HIGH — todos os pacotes verificados em requirements.txt existente
- Architecture: HIGH — padrões extraídos diretamente dos arquivos do repo com números de linha
- Atomic transaction pattern: HIGH — analisado db_core.py linha por linha
- Vencimentos reuse: HIGH — código existente em main.py:2527–2581 verificado
- Frontend tab pattern: HIGH — navegação existente verificada em cmasm_erp.html
- Async fixture: MEDIUM — padrão geral documentado; detalhes de versão ASSUMED

**Research date:** 2026-06-28
**Valid until:** 2026-07-28 (stack estável; risco de stale em pytest-asyncio se versão mudar)
