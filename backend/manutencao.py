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
