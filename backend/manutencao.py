"""
Router de Manutenção — Registrar Uso de Ativos (IMP-01).

Endpoints:
  POST /api/manutencao/uso  — incremento atômico de ativos.uso_atual + audit row
  GET  /api/manutencao/uso  — histórico de registros (newest-first)

Referências: Rules.md §15, CONTEXT.md Phase 1, schema_manutencao.sql.
"""
from __future__ import annotations

import json
import math
import sys
from datetime import date
from typing import Optional

import aiosqlite
from fastapi import APIRouter, HTTPException, Header, Query
from pydantic import BaseModel, field_validator

router = APIRouter(prefix="/api/manutencao", tags=["manutencao"])


# ── DB / Auth helpers (copied verbatim from catalogo.py pattern) ──────────────

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


# ── Models ────────────────────────────────────────────────────────────────────

class UsoIn(BaseModel):
    ativo_id: str
    delta: float
    data: Optional[str] = None       # ISO date YYYY-MM-DD; default = today in handler
    observacao: Optional[str] = None

    @field_validator("delta")
    @classmethod
    def delta_positivo(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("delta deve ser positivo (> 0)")
        return v


# ── Vencimentos helper ────────────────────────────────────────────────────────

async def _vencimentos_para_ativo(ativo_id: str, uso_atual_novo: float) -> list[dict]:
    """Retorna planos vencidos (falta <= iv * 0.15) para um ativo específico.

    Reutiliza a lógica de manutencao_vencimentos (main.py:2527-2581) mas
    filtrada por ativo e com uso_atual_novo já calculado (sem nova leitura do DB).
    Janela de alerta: últimos 15% do intervalo (mesma constante de main.py:2571).
    """
    db = _db()
    ativo = await db.fetch_one(
        "SELECT id, nome, tipo, categoria, unidade_uso FROM ativos WHERE id = ?",
        (ativo_id,),
    )
    if not ativo:
        return []

    planos = await db.fetch_all("SELECT * FROM catalogo_planos WHERE ativo = 1")
    plano_by_tipo: dict[str, list] = {}
    for p in planos:
        tipos: list = []
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
    for p in plano_by_tipo.get(ativo["tipo"] or "", []):
        itens = await db.fetch_all(
            "SELECT i.frequencia, i.servico_id, s.nome FROM catalogo_plano_itens i "
            "JOIN catalogo_servicos s ON s.id = i.servico_id "
            "WHERE i.plano_id = ? AND i.classe = 'prev' ORDER BY i.seq",
            (p["id"],),
        )
        for it in itens:
            try:
                raw = it["frequencia"] or p.get("frequencia")
                if not raw:
                    continue
                f = json.loads(raw)
                if not isinstance(f, dict):
                    continue                       # guard: bare number/array/string
                if f.get("tipo") != "por_uso" or not f.get("valor"):
                    continue
                iv = float(f["valor"])             # coerce string to float defensively
                if iv <= 0:
                    continue
                prox = (math.floor(uso / iv) + 1) * iv
                falta = prox - uso
                if falta <= iv * 0.15:   # dentro da janela de alerta (mesma constante de main.py:2571)
                    out.append({
                        "ativo_id": ativo_id,
                        "ativo_nome": ativo["nome"],
                        "plano_id": p["id"],
                        "plano_nome": p["nome"],
                        "servico_id": it["servico_id"],
                        "servico": it["nome"],
                        "intervalo": iv,
                        "unidade": f.get("unidade"),
                        "uso_atual": uso,
                        "proximo": prox,
                        "falta": falta,
                        "pct": round((uso % iv) / iv * 100),
                    })
            except Exception:
                continue                           # skip malformed item — never crash after commit
    return out


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/uso", status_code=201)
async def registrar_uso(body: UsoIn, authorization: str | None = Header(None)):
    """Incremento atômico de ativos.uso_atual + INSERT uso_registros em uma transação.

    Atomicidade garantida por um único aiosqlite.connect block com um único commit.
    Não usa _db().execute() (que abre conexão por chamada) para evitar escrita parcial.
    Mitigações STRIDE: T-01-01 (params), T-01-02 (field_validator delta>0),
    T-01-03 (_require_auth), T-01-04 (transação única), T-01-05 (audit row com operador+snapshot).
    """
    user = await _require_auth(authorization)
    operador = user.get("mat") or user.get("nome") or str(user.get("usuario_id", ""))

    # db_path via singleton de main.py (sem importação circular)
    db_path = _db().db_path

    async with aiosqlite.connect(db_path) as conn:
        conn.row_factory = aiosqlite.Row

        # 1. Ler uso_atual atual dentro da transação (snapshot consistente)
        async with conn.execute(
            "SELECT uso_atual FROM ativos WHERE id = ? AND ativo = 1",
            (body.ativo_id,),  # parameterized — T-01-01
        ) as cur:
            row = await cur.fetchone()

        if not row:
            raise HTTPException(404, "Ativo não encontrado")

        valor_anterior = float(row["uso_atual"] or 0.0)
        valor_novo = round(valor_anterior + body.delta, 2)

        # 2. UPDATE + INSERT atômicos na mesma conexão — rollback automático em exceção
        await conn.execute(
            "UPDATE ativos SET uso_atual = ? WHERE id = ?",
            (valor_novo, body.ativo_id),
        )
        await conn.execute(
            "INSERT INTO uso_registros "
            "(ativo_id, delta, valor_anterior, valor_novo, data, operador, observacao) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                body.ativo_id,
                body.delta,
                valor_anterior,
                valor_novo,
                body.data or date.today().isoformat(),
                operador,
                body.observacao,
            ),
        )
        # 3. Commit único — garante atomicidade (T-01-04)
        await conn.commit()

    # 4. Calcular vencimentos disparados pós-commit (leitura isolada via singleton)
    vencimentos = await _vencimentos_para_ativo(body.ativo_id, valor_novo)

    return {
        "uso_atual": valor_novo,
        "valor_anterior": valor_anterior,
        "delta": body.delta,
        "vencimentos_disparados": vencimentos,
    }


@router.get("/uso")
async def listar_uso(
    ativo_id: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
    authorization: str | None = Header(None),
):
    """Retorna registros de uso recentes, ordenados mais novos primeiro.

    Parâmetros:
      ativo_id — filtra por ativo específico (opcional)
      limit    — máx de linhas retornadas (padrão 50, min 1, max 200)
    """
    await _require_auth(authorization)
    db = _db()
    if ativo_id:
        rows = await db.fetch_all(
            "SELECT ur.*, a.nome AS ativo_nome, a.unidade_uso "
            "FROM uso_registros ur "
            "JOIN ativos a ON a.id = ur.ativo_id "
            "WHERE ur.ativo_id = ? "
            "ORDER BY ur.created_at DESC LIMIT ?",
            (ativo_id, limit),
        )
    else:
        rows = await db.fetch_all(
            "SELECT ur.*, a.nome AS ativo_nome, a.unidade_uso "
            "FROM uso_registros ur "
            "JOIN ativos a ON a.id = ur.ativo_id "
            "ORDER BY ur.created_at DESC LIMIT ?",
            (limit,),
        )
    return rows


# ── Fase 02: Plano no Ativo (IMP-02) ─────────────────────────────────────────


class RegistroIn(BaseModel):
    """Payload para POST /registro — execução de manutenção por item de plano."""

    ativo_id: str
    responsavel: str
    itens: list[int]            # lista de catalogo_plano_item_id (integers)
    observacao: Optional[str] = None

    @field_validator("responsavel")
    @classmethod
    def resp_nao_vazio(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Responsável é obrigatório")
        return v.strip()

    @field_validator("itens")
    @classmethod
    def itens_nao_vazios(cls, v: list) -> list:
        if not v:
            raise ValueError("Selecione ao menos um item")
        return v


@router.get("/plano-ativo")
async def get_plano_ativo(
    ativo_id: str = Query(...),
    authorization: str | None = Header(None),
):
    """Retorna os itens do plano de manutenção aplicável ao ativo, com status calculado.

    Status por item: VENCIDA / URGENTE / PROXIMA / EM_DIA (mesmas constantes de main.py).
    Itens por_tempo ou sem frequência válida retornam com status=POR_TEMPO / SEM_FREQ.
    Mitigações STRIDE: T-02-01 (params), T-02-06 (_require_auth).
    """
    await _require_auth(authorization)
    db = _db()

    # 1. Fetch ativo
    ativo = await db.fetch_one(
        "SELECT id, nome, tipo, uso_atual, unidade_uso FROM ativos WHERE id = ? AND ativo = 1",
        (ativo_id,),
    )
    if not ativo:
        raise HTTPException(404, "Ativo não encontrado")

    uso = float(ativo["uso_atual"] or 0.0)

    # 2. Resolve plans for this ativo's tipo (same algorithm as _vencimentos_para_ativo)
    planos = await db.fetch_all("SELECT * FROM catalogo_planos WHERE ativo = 1")
    plano_by_tipo: dict[str, list] = {}
    for p in planos:
        tipos: list = []
        try:
            tipos = json.loads(p["aplicavel_tipos"] or "[]")
        except Exception:
            tipos = []
        if p["tipo_codigo"] and p["tipo_codigo"] not in tipos:
            tipos.append(p["tipo_codigo"])
        for t in tipos:
            plano_by_tipo.setdefault(t, []).append(p)

    planos_do_ativo = plano_by_tipo.get(ativo["tipo"] or "", [])

    # 3. Load all state rows for this ativo in ONE query → dict keyed by item id
    estado_rows = await db.fetch_all(
        "SELECT catalogo_plano_item_id, ultimo_uso, proximo_uso "
        "FROM ativo_plano_estado WHERE ativo_id = ?",
        (ativo_id,),
    )
    estado_by_item: dict[int, dict] = {r["catalogo_plano_item_id"]: dict(r) for r in estado_rows}

    # 4. Build itens list
    itens: list[dict] = []
    for p in planos_do_ativo:
        plano_items = await db.fetch_all(
            "SELECT i.id, i.seq, i.classe, i.frequencia, s.nome AS servico_nome "
            "FROM catalogo_plano_itens i "
            "JOIN catalogo_servicos s ON s.id = i.servico_id "
            "WHERE i.plano_id = ? ORDER BY i.seq",
            (p["id"],),
        )
        for it in plano_items:
            item_id = it["id"]

            # Resolve raw frequency (item override else plan default)
            raw = it["frequencia"] or p.get("frequencia")

            # Guard: missing/None frequency
            if not raw:
                itens.append({
                    "plano_id": p["id"],
                    "plano_nome": p["nome"],
                    "item_id": item_id,
                    "servico_nome": it["servico_nome"],
                    "intervalo": None,
                    "unidade": None,
                    "ultimo_uso": None,
                    "proximo_uso": None,
                    "uso_atual": uso,
                    "falta": None,
                    "pct": None,
                    "status": "SEM_FREQ",
                    "por_tempo": True,
                })
                continue

            # Guard: malformed JSON
            try:
                f = json.loads(raw)
            except Exception:
                itens.append({
                    "plano_id": p["id"],
                    "plano_nome": p["nome"],
                    "item_id": item_id,
                    "servico_nome": it["servico_nome"],
                    "intervalo": None,
                    "unidade": None,
                    "ultimo_uso": None,
                    "proximo_uso": None,
                    "uso_atual": uso,
                    "falta": None,
                    "pct": None,
                    "status": "SEM_FREQ",
                    "por_tempo": True,
                })
                continue

            # Guard: por_tempo (or any non-por_uso tipo) — BEFORE float() coercion
            if not isinstance(f, dict) or f.get("tipo") != "por_uso":
                itens.append({
                    "plano_id": p["id"],
                    "plano_nome": p["nome"],
                    "item_id": item_id,
                    "servico_nome": it["servico_nome"],
                    "intervalo": None,
                    "unidade": None,
                    "ultimo_uso": None,
                    "proximo_uso": None,
                    "uso_atual": uso,
                    "falta": None,
                    "pct": None,
                    "status": "POR_TEMPO",
                    "por_tempo": True,
                })
                continue

            # Confirmed por_uso item — safe to coerce
            try:
                iv = float(f["valor"])
            except (KeyError, TypeError, ValueError):
                itens.append({
                    "plano_id": p["id"],
                    "plano_nome": p["nome"],
                    "item_id": item_id,
                    "servico_nome": it["servico_nome"],
                    "intervalo": None,
                    "unidade": None,
                    "ultimo_uso": None,
                    "proximo_uso": None,
                    "uso_atual": uso,
                    "falta": None,
                    "pct": None,
                    "status": "SEM_FREQ",
                    "por_tempo": True,
                })
                continue

            # Guard: zero/negative interval (div-by-zero)
            if iv <= 0:
                itens.append({
                    "plano_id": p["id"],
                    "plano_nome": p["nome"],
                    "item_id": item_id,
                    "servico_nome": it["servico_nome"],
                    "intervalo": None,
                    "unidade": None,
                    "ultimo_uso": None,
                    "proximo_uso": None,
                    "uso_atual": uso,
                    "falta": None,
                    "pct": None,
                    "status": "SEM_FREQ",
                    "por_tempo": True,
                })
                continue

            # Compute state
            estado = estado_by_item.get(item_id)
            if estado:
                proximo_uso = float(estado["proximo_uso"])
                ultimo_uso = float(estado["ultimo_uso"])
            else:
                # No history: extrapolate virtual next from current usage
                proximo_uso = (math.floor(uso / iv) + 1) * iv
                ultimo_uso = None

            falta = proximo_uso - uso
            pct = round(min(100, max(0, (uso - (proximo_uso - iv)) / iv * 100)))

            # Status thresholds (same constants as main.py:2571 and manutencao.py:117)
            if falta <= 0:
                status = "VENCIDA"
            elif falta <= iv * 0.15:
                status = "URGENTE"
            elif falta <= iv * 0.30:
                status = "PROXIMA"
            else:
                status = "EM_DIA"

            itens.append({
                "plano_id": p["id"],
                "plano_nome": p["nome"],
                "item_id": item_id,
                "servico_nome": it["servico_nome"],
                "intervalo": iv,
                "unidade": f.get("unidade"),
                "ultimo_uso": ultimo_uso,
                "proximo_uso": proximo_uso,
                "uso_atual": uso,
                "falta": falta,
                "pct": pct,
                "status": status,
                "por_tempo": False,
            })

    return {
        "ativo_id": ativo["id"],
        "ativo_nome": ativo["nome"],
        "uso_atual": uso,
        "unidade_uso": ativo["unidade_uso"],
        "itens": itens,
    }


@router.post("/registro", status_code=201)
async def registrar_manutencao(
    body: RegistroIn,
    authorization: str | None = Header(None),
):
    """Registra execução de manutenção por item de plano em uma transação atômica.

    Atomicidade: único aiosqlite.connect block + único commit.
    uso_no_momento lido de ativos.uso_atual DENTRO da txn (anti-double-count — T-02-02).
    operador derivado do token, nunca do payload (T-02-03).
    Mitigações STRIDE: T-02-01 (params), T-02-02, T-02-03, T-02-04 (audit), T-02-05 (txn atômica).
    """
    user = await _require_auth(authorization)
    operador = user.get("mat") or user.get("nome") or str(user.get("usuario_id", ""))

    db_path = _db().db_path

    async with aiosqlite.connect(db_path) as conn:
        conn.row_factory = aiosqlite.Row

        # (a) Read uso_atual INSIDE the transaction (never from payload — T-02-02)
        async with conn.execute(
            "SELECT uso_atual FROM ativos WHERE id = ? AND ativo = 1",
            (body.ativo_id,),
        ) as cur:
            row = await cur.fetchone()
        if not row:
            raise HTTPException(404, "Ativo não encontrado")
        uso_no_momento = float(row["uso_atual"] or 0.0)

        # (b) Resolve intervals for each checked item; skip por_tempo/no-interval items
        itens_validos: list[dict] = []
        for item_id in body.itens:
            async with conn.execute(
                "SELECT i.id, i.frequencia, p.frequencia AS plano_freq "
                "FROM catalogo_plano_itens i "
                "JOIN catalogo_planos p ON p.id = i.plano_id "
                "WHERE i.id = ?",
                (item_id,),
            ) as cur:
                it = await cur.fetchone()
            if not it:
                raise HTTPException(422, f"Item {item_id} não encontrado")

            raw = it["frequencia"] or it["plano_freq"]
            if not raw:
                continue  # por_tempo / sem frequência: inclui no audit mas não atualiza estado

            try:
                f = json.loads(raw)
            except Exception:
                continue  # malformed JSON: skip estado upsert

            if not isinstance(f, dict) or f.get("tipo") != "por_uso":
                continue  # por_tempo ou outro tipo: skip estado upsert

            try:
                iv = float(f["valor"])
            except (KeyError, TypeError, ValueError):
                raise HTTPException(422, f"Frequência inválida no item {item_id}")

            if iv <= 0:
                continue  # intervalo inválido: skip (guard div-by-zero)

            itens_validos.append({"item_id": item_id, "iv": iv})

        # (c) Insert audit row (ALL itens requested, including por_tempo ones)
        await conn.execute(
            "INSERT INTO manut_registros "
            "(ativo_id, responsavel, operador, data, uso_no_momento, itens_json, observacao) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                body.ativo_id,
                body.responsavel,
                operador,
                date.today().isoformat(),
                uso_no_momento,
                json.dumps(body.itens),
                body.observacao,
            ),
        )

        # (d) Upsert ativo_plano_estado per por_uso item only
        for item in itens_validos:
            novo_proximo = uso_no_momento + item["iv"]   # sempre uso_no_momento + iv (anti-double-count)
            await conn.execute(
                "INSERT INTO ativo_plano_estado "
                "(ativo_id, catalogo_plano_item_id, ultimo_uso, proximo_uso, updated_at) "
                "VALUES (?, ?, ?, ?, datetime('now')) "
                "ON CONFLICT(ativo_id, catalogo_plano_item_id) DO UPDATE SET "
                "ultimo_uso  = excluded.ultimo_uso, "
                "proximo_uso = excluded.proximo_uso, "
                "updated_at  = excluded.updated_at",
                (body.ativo_id, item["item_id"], uso_no_momento, novo_proximo),
            )

        # (e) Single commit — garante atomicidade (T-02-05)
        await conn.commit()

    return {"ok": True, "uso_no_momento": uso_no_momento, "itens_registrados": len(itens_validos)}


# ── Fase 03: Estoque de Sobressalentes (IMP-03) ───────────────────────────────
# Tabelas SEPARADAS de estoque/estoque_movimentos (SC: sem mistura).
# Mitigações STRIDE: T-03-01 (params), T-03-02 (operador do token), T-03-03 (txn atômica),
# T-03-04 (role check), T-03-05 (estoque isolado), T-03-06 (saida negativa → 422).

TIPOS_MOVIMENTO = {"entrada", "saida", "ajuste"}


class SobressalanteIn(BaseModel):
    """Payload para POST /sobressalentes — criar nova peça."""

    nome: str
    codigo: Optional[str] = None
    categoria: str = "sobressalente"   # consumivel | sobressalente | ferramenta
    unidade: str = "un"
    qtd_minima: float = 0.0
    preco_unitario: float = 0.0
    obs: Optional[str] = None

    @field_validator("nome")
    @classmethod
    def nome_nao_vazio(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("nome é obrigatório")
        return v.strip()


class SobressalanteUpdate(BaseModel):
    """Payload para PUT /sobressalentes/{id} — editar campos (exceto qtd_atual)."""

    nome: Optional[str] = None
    codigo: Optional[str] = None
    categoria: Optional[str] = None
    unidade: Optional[str] = None
    qtd_minima: Optional[float] = None
    preco_unitario: Optional[float] = None
    obs: Optional[str] = None

    @field_validator("nome")
    @classmethod
    def nome_nao_vazio(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("nome não pode ser vazio")
        return v.strip() if v else v


class AjusteIn(BaseModel):
    """Payload para POST /sobressalentes/{id}/ajuste.

    Semântica dos tipos:
      entrada — adiciona quantidade ao estoque atual (qtd_atual += quantidade)
      saida   — subtrai quantidade do estoque atual (qtd_atual -= quantidade); 422 se ficaria negativo
      ajuste  — define o delta: qtd_atual += quantidade (positivo = adiciona, negativo = subtrai);
                422 se resultado ficaria negativo

    operador NÃO vem do payload — é extraído do token (_require_auth) — T-03-02.
    """

    quantidade: float
    tipo: str      # entrada | saida | ajuste
    motivo: Optional[str] = None
    obs: Optional[str] = None

    @field_validator("tipo")
    @classmethod
    def tipo_valido(cls, v: str) -> str:
        if v not in TIPOS_MOVIMENTO:
            raise ValueError(f"tipo deve ser um de {sorted(TIPOS_MOVIMENTO)}")
        return v


def _badge(qtd_atual: float, qtd_minima: float) -> str:
    """Calcula badge: ZERADO | BAIXO | OK.

    ZERADO: qtd_atual <= 0
    BAIXO:  0 < qtd_atual < qtd_minima
    OK:     qtd_atual >= qtd_minima
    """
    if qtd_atual <= 0:
        return "ZERADO"
    if qtd_atual < qtd_minima:
        return "BAIXO"
    return "OK"


@router.get("/sobressalentes")
async def listar_sobressalentes(
    categoria: Optional[str] = None,
    authorization: str | None = Header(None),
):
    """Lista peças ativas com badge calculado (ZERADO|BAIXO|OK) e valor estimado total.

    Parâmetros:
      categoria — filtra por categoria (opcional)
    Retorna:
      { items: [..., badge, ...], valor_estimado_total: float }

    Mitigações STRIDE: T-03-01 (params), _require_auth (T-03-04).
    """
    await _require_auth(authorization)
    db = _db()
    if categoria:
        rows = await db.fetch_all(
            "SELECT * FROM sobressalentes WHERE ativo = 1 AND categoria = ? ORDER BY nome",
            (categoria,),  # parameterized — T-03-01
        )
    else:
        rows = await db.fetch_all(
            "SELECT * FROM sobressalentes WHERE ativo = 1 ORDER BY nome",
        )

    items = []
    valor_estimado_total = 0.0
    for row in rows:
        row_dict = dict(row)
        qtd = float(row_dict.get("qtd_atual") or 0.0)
        preco = float(row_dict.get("preco_unitario") or 0.0)
        minima = float(row_dict.get("qtd_minima") or 0.0)
        row_dict["badge"] = _badge(qtd, minima)
        valor_estimado_total += qtd * preco
        items.append(row_dict)

    return {
        "items": items,
        "valor_estimado_total": round(valor_estimado_total, 2),
    }


@router.post("/sobressalentes", status_code=201)
async def criar_sobressalente(
    body: SobressalanteIn,
    authorization: str | None = Header(None),
):
    """Cria uma nova peça no estoque de sobressalentes.

    Requer token não-visitante (role != 'visualizador' — T-03-04).
    Mitigações STRIDE: T-03-01 (params), T-03-04 (role check).
    """
    user = await _require_auth(authorization)
    if user.get("role") == "visualizador":
        raise HTTPException(403, "Visualizadores não podem criar peças")

    db_path = _db().db_path
    async with aiosqlite.connect(db_path) as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute(
            "INSERT INTO sobressalentes "
            "(codigo, nome, categoria, unidade, qtd_minima, preco_unitario, obs) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                body.codigo,
                body.nome,
                body.categoria,
                body.unidade,
                body.qtd_minima,
                body.preco_unitario,
                body.obs,
            ),
        )
        new_id = cur.lastrowid
        await conn.commit()

    return {"id": new_id}


@router.put("/sobressalentes/{item_id}")
async def editar_sobressalente(
    item_id: int,
    body: SobressalanteUpdate,
    authorization: str | None = Header(None),
):
    """Edita campos editáveis de uma peça (nome, codigo, categoria, unidade, qtd_minima, preco_unitario, obs).

    NÃO altera qtd_atual — use /ajuste para isso.
    404 se não encontrado. 403 para visualizador. Mitigações T-03-01, T-03-04.
    """
    user = await _require_auth(authorization)
    if user.get("role") == "visualizador":
        raise HTTPException(403, "Visualizadores não podem editar peças")

    db = _db()
    row = await db.fetch_one(
        "SELECT id FROM sobressalentes WHERE id = ? AND ativo = 1",
        (item_id,),
    )
    if not row:
        raise HTTPException(404, "Peça não encontrada")

    # Build SET clause from provided fields only (never qtd_atual)
    updates = {}
    if body.nome is not None:
        updates["nome"] = body.nome
    if body.codigo is not None:
        updates["codigo"] = body.codigo
    if body.categoria is not None:
        updates["categoria"] = body.categoria
    if body.unidade is not None:
        updates["unidade"] = body.unidade
    if body.qtd_minima is not None:
        updates["qtd_minima"] = body.qtd_minima
    if body.preco_unitario is not None:
        updates["preco_unitario"] = body.preco_unitario
    if body.obs is not None:
        updates["obs"] = body.obs

    if not updates:
        return {"ok": True, "message": "Nenhum campo para atualizar"}

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [item_id]

    db_path = _db().db_path
    async with aiosqlite.connect(db_path) as conn:
        await conn.execute(
            f"UPDATE sobressalentes SET {set_clause} WHERE id = ?",  # noqa: S608 — set_clause is from hardcoded keys
            values,
        )
        await conn.commit()

    return {"ok": True}


@router.post("/sobressalentes/{item_id}/ajuste", status_code=201)
async def ajustar_sobressalente(
    item_id: int,
    body: AjusteIn,
    authorization: str | None = Header(None),
):
    """Ajusta a quantidade de uma peça em uma transação atômica.

    Semântica:
      entrada — qtd_atual += quantidade (entrada positiva)
      saida   — qtd_atual -= quantidade (saida; 422 se ficaria negativo — T-03-06)
      ajuste  — qtd_atual += quantidade (positivo = adiciona, negativo = subtrai;
                422 se resultado ficaria negativo — T-03-06)

    Atomicidade: único aiosqlite.connect block + único commit (T-03-03).
    operador lido do token, nunca do payload (T-03-02).
    Retorna o novo qtd_atual.
    """
    user = await _require_auth(authorization)
    if user.get("role") == "visualizador":
        raise HTTPException(403, "Visualizadores não podem ajustar estoque")

    operador = user.get("mat") or user.get("nome") or str(user.get("usuario_id", ""))
    db_path = _db().db_path

    async with aiosqlite.connect(db_path) as conn:
        conn.row_factory = aiosqlite.Row

        # 1. Ler a peça DENTRO da transação (snapshot consistente)
        async with conn.execute(
            "SELECT id, qtd_atual FROM sobressalentes WHERE id = ? AND ativo = 1",
            (item_id,),
        ) as cur:
            row = await cur.fetchone()

        if not row:
            raise HTTPException(404, "Peça não encontrada")

        qtd_anterior = float(row["qtd_atual"] or 0.0)

        # 2. Calcular nova quantidade segundo semântica do tipo
        if body.tipo == "entrada":
            nova_qtd = qtd_anterior + body.quantidade
        elif body.tipo == "saida":
            nova_qtd = qtd_anterior - body.quantidade
        else:  # ajuste
            nova_qtd = qtd_anterior + body.quantidade

        # Nunca deixar negativo (T-03-06)
        if nova_qtd < 0:
            raise HTTPException(
                422,
                f"Operação resultaria em estoque negativo "
                f"(atual={qtd_anterior}, delta={body.quantidade} → {nova_qtd})",
            )

        nova_qtd = round(nova_qtd, 4)

        # 3. UPDATE + INSERT em única transação atômica (T-03-03)
        await conn.execute(
            "UPDATE sobressalentes SET qtd_atual = ? WHERE id = ?",
            (nova_qtd, item_id),
        )
        await conn.execute(
            "INSERT INTO sobressalentes_movimentos "
            "(item_id, tipo, quantidade, motivo, obs, operador) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (item_id, body.tipo, body.quantidade, body.motivo, body.obs, operador),
        )

        # 4. Commit único — garante atomicidade (T-03-03)
        await conn.commit()

    return {"qtd_atual": nova_qtd}


@router.get("/sobressalentes/{item_id}/movimentos")
async def listar_movimentos(
    item_id: int,
    limit: int = Query(default=50, ge=1, le=200),
    authorization: str | None = Header(None),
):
    """Retorna o histórico de movimentos de uma peça, mais recentes primeiro.

    Parâmetros:
      limit — máx de linhas retornadas (padrão 50, min 1, max 200)
    Mitigações STRIDE: T-03-01 (params), _require_auth (T-03-04).
    """
    await _require_auth(authorization)
    db = _db()
    rows = await db.fetch_all(
        "SELECT * FROM sobressalentes_movimentos "
        "WHERE item_id = ? "
        "ORDER BY created_at DESC LIMIT ?",
        (item_id, limit),
    )
    return rows
