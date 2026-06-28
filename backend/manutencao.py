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
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, field_validator

router = APIRouter(prefix="/api/manutencao", tags=["manutencao"])


# ── DB / Auth helpers (copied verbatim from catalogo.py pattern) ──────────────

def _db():
    """Acessa o singleton CoreDB de main.py sem importação circular."""
    return sys.modules["backend.main"].db


async def _require_auth(authorization: str | None) -> dict:
    from fastapi import HTTPException as _HTTPException
    if not authorization or not authorization.startswith("Bearer "):
        raise _HTTPException(401, "Token ausente")
    token = authorization[7:]
    row = await _db().fetch_one(
        "SELECT s.usuario_id, u.nome, u.mat, u.role "
        "FROM sessoes s JOIN usuarios u ON u.id = s.usuario_id "
        "WHERE s.token = ? AND s.expira_em > datetime('now')",
        (token,),
    )
    if not row:
        raise _HTTPException(401, "Token inválido ou expirado")
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
async def listar_uso(ativo_id: Optional[str] = None, limit: int = 20):
    """Retorna registros de uso recentes, ordenados mais novos primeiro.

    Parâmetros:
      ativo_id — filtra por ativo específico (opcional)
      limit    — máx de linhas retornadas (padrão 20)
    """
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
