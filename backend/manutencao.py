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
from datetime import date, timedelta  # timedelta needed by _vencimentos_para_ativo (por_tempo branch)
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
                if f.get("tipo") == "por_tempo":
                    valor = f.get("valor")
                    if not valor:
                        continue
                    ultima = await db.fetch_one(
                        "SELECT MAX(data) AS d FROM manut_registros WHERE ativo_id = ?",
                        (ativo_id,),
                    )
                    ultima_data = ultima["d"] if ultima and ultima["d"] else None
                    if not ultima_data:
                        continue  # sem base de data → sem alerta
                    try:
                        dt_ultima = date.fromisoformat(ultima_data)
                    except ValueError:
                        continue
                    dt_prox = dt_ultima + timedelta(days=int(valor))
                    falta_dias = (dt_prox - date.today()).days
                    if falta_dias <= int(valor) * 0.15:
                        out.append({
                            "ativo_id": ativo_id,
                            "ativo_nome": ativo["nome"],
                            "plano_id": p["id"],
                            "plano_nome": p["nome"],
                            "servico_id": it["servico_id"],
                            "servico": it["nome"],
                            "intervalo": int(valor),
                            "unidade": "dias",
                            "uso_atual": None,
                            "proximo": dt_prox.isoformat(),
                            "falta": falta_dias,
                            "pct": None,
                        })
                    continue  # por_tempo never falls into por_uso path
                elif f.get("tipo") != "por_uso" or not f.get("valor"):
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

    tipo: str      # entrada | saida | ajuste — declarado antes de quantidade para info.data
    quantidade: float
    motivo: Optional[str] = None
    obs: Optional[str] = None

    @field_validator("tipo")
    @classmethod
    def tipo_valido(cls, v: str) -> str:
        if v not in TIPOS_MOVIMENTO:
            raise ValueError(f"tipo deve ser um de {sorted(TIPOS_MOVIMENTO)}")
        return v

    @field_validator("quantidade")
    @classmethod
    def quantidade_positiva(cls, v: float, info) -> float:
        # "ajuste" permite negativo (delta bidirecional).
        # "entrada" e "saida" exigem quantidade > 0 — sinal é implícito pelo tipo.
        tipo = (info.data or {}).get("tipo")
        if tipo in ("entrada", "saida") and v <= 0:
            raise ValueError("quantidade deve ser positiva (> 0) para entrada/saida")
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

    # Collapse existence check + UPDATE into a single connection (no TOCTOU gap — WR-02).
    # WHERE includes ativo=1 so soft-deleted rows produce rowcount=0 → 404, not silent no-op.
    db_path = _db().db_path
    async with aiosqlite.connect(db_path) as conn:
        cur = await conn.execute(
            f"UPDATE sobressalentes SET {set_clause} WHERE id = ? AND ativo = 1",  # noqa: S608 — set_clause is from hardcoded keys
            values,
        )
        if cur.rowcount == 0:
            raise HTTPException(404, "Peça não encontrada")
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

    # Consistent with other endpoints: 404 for non-existent / soft-deleted item (IN-01).
    row = await db.fetch_one(
        "SELECT id FROM sobressalentes WHERE id = ? AND ativo = 1", (item_id,)
    )
    if not row:
        raise HTTPException(404, "Peça não encontrada")

    rows = await db.fetch_all(
        "SELECT * FROM sobressalentes_movimentos "
        "WHERE item_id = ? "
        "ORDER BY created_at DESC LIMIT ?",
        (item_id, limit),
    )
    return rows


# ── Fase 04 — Equipe Técnica (IMP-04) ────────────────────────────────────────
#
# Endpoints:
#   GET  /equipe/membros                  — lista roster (ativo=1 por default)
#   POST /equipe/membros                  — cria membro (201)
#   PUT  /equipe/membros/{id}             — edita / soft-delete (ativo=0); nunca hard-delete
#   GET  /equipe/config                   — config singleton + capacidade derivada
#   PUT  /equipe/config                   — salva config singleton + resposta com capacidade
#
# Mitigações STRIDE: T-04-01 (SQL parameterizado), T-04-02 (_require_auth + role check),
# T-04-04 (validação de ConfigIn), T-04-05 (só soft-delete, nunca DELETE).
# Capacidade: config-only (não multiplica por membros — algoritmo do app de campo legado).
# ─────────────────────────────────────────────────────────────────────────────


# ── Pydantic models ───────────────────────────────────────────────────────────

class MembroIn(BaseModel):
    """Payload para POST /equipe/membros."""

    nome: str
    posto_grad: Optional[str] = None
    especialidade: Optional[str] = None
    tem_login: Optional[int] = 0
    usuario_mat: Optional[str] = None

    @field_validator("nome")
    @classmethod
    def nome_nao_vazio(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("nome é obrigatório e não pode ser vazio")
        return v.strip()


class MembroUpdate(BaseModel):
    """Payload para PUT /equipe/membros/{id} — todos os campos opcionais (partial update)."""

    nome: Optional[str] = None
    posto_grad: Optional[str] = None
    especialidade: Optional[str] = None
    tem_login: Optional[int] = None
    usuario_mat: Optional[str] = None
    ativo: Optional[int] = None          # 0 = soft-delete, 1 = reativar

    @field_validator("nome")
    @classmethod
    def nome_nao_vazio(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("nome não pode ser vazio")
        return v.strip() if v else v

    @field_validator("ativo")
    @classmethod
    def ativo_valido(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v not in (0, 1):
            raise ValueError("ativo deve ser 0 (inativo) ou 1 (ativo)")
        return v


class _TurnoItem(BaseModel):
    """Item de turno dentro de ConfigIn.turnos."""

    nome: str
    horas: float

    @field_validator("horas")
    @classmethod
    def horas_nao_negativo(cls, v: float) -> float:
        if v < 0:
            raise ValueError("horas de turno não pode ser negativo")
        return v


class ConfigIn(BaseModel):
    """Payload para PUT /equipe/config."""

    num_equipes: int
    dias_semana: list[str]
    turnos: list[_TurnoItem]

    @field_validator("num_equipes")
    @classmethod
    def num_equipes_positivo(cls, v: int) -> int:
        if v < 1:
            raise ValueError("num_equipes deve ser >= 1")
        return v

    @field_validator("dias_semana")
    @classmethod
    def dias_nao_vazios(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("dias_semana não pode ser vazio")
        return v

    @field_validator("turnos")
    @classmethod
    def turnos_nao_vazios(cls, v: list[_TurnoItem]) -> list[_TurnoItem]:
        if not v:
            raise ValueError("turnos não pode ser vazio")
        return v


# ── Capacity helper ───────────────────────────────────────────────────────────

# Default config values (mirrors equipe_config table defaults).
_DEFAULT_CONFIG = {
    "id": 1,
    "num_equipes": 1,
    "dias_semana": ["seg", "ter", "qua", "qui", "sex"],
    "turnos": [{"nome": "Manhã", "horas": 2}, {"nome": "Tarde", "horas": 2}],
}


def _capacidade(config: dict) -> dict:
    """Calcula capacidade da equipe a partir da config (config-only, não usa membros).

    Fórmula exata do app de campo legado:
      h_dia_equipe = Σ turnos[i].horas
      h_dia_total  = h_dia_equipe × num_equipes
      h_semana     = h_dia_total × len(dias_semana)
      h_mes        = h_semana × 4.345
      h_ano        = h_semana × 52

    Parâmetros:
      config — dict com num_equipes (int), dias_semana (list|str), turnos (list|str).
               dias_semana e turnos são listas quando vindos de ConfigIn ou str JSON quando
               lidos do banco.

    Retorna dict com chaves: h_dia_equipe, h_dia_total, h_semana, h_mes, h_ano.
    Resultados inteiros quando os inputs são inteiros (não forçamos round).
    """
    num_equipes = int(config.get("num_equipes", 1))

    # dias_semana pode ser list (vindo de ConfigIn) ou str JSON (lido do banco)
    dias_semana = config.get("dias_semana", [])
    if isinstance(dias_semana, str):
        dias_semana = json.loads(dias_semana)

    # turnos pode ser list[dict] ou str JSON
    turnos = config.get("turnos", [])
    if isinstance(turnos, str):
        turnos = json.loads(turnos)

    h_dia_equipe = sum(float(t["horas"]) for t in turnos)
    h_dia_total = h_dia_equipe * num_equipes
    h_semana = h_dia_total * len(dias_semana)
    h_mes = h_semana * 4.345
    h_ano = h_semana * 52

    return {
        "h_dia_equipe": h_dia_equipe,
        "h_dia_total": h_dia_total,
        "h_semana": h_semana,
        "h_mes": h_mes,
        "h_ano": h_ano,
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/equipe/membros")
async def listar_membros(
    incluir_inativos: int = Query(default=0, ge=0, le=1),
    authorization: str | None = Header(None),
):
    """Lista membros do roster da equipe técnica.

    Parâmetros:
      incluir_inativos — 0 (default) retorna apenas ativo=1; 1 retorna todos.
    Ordem: nome ASC.
    Mitigações: T-04-01 (params), T-04-02 (_require_auth).
    """
    await _require_auth(authorization)
    db = _db()
    if incluir_inativos:
        rows = await db.fetch_all(
            "SELECT * FROM equipe_membros ORDER BY nome",
        )
    else:
        rows = await db.fetch_all(
            "SELECT * FROM equipe_membros WHERE ativo = 1 ORDER BY nome",
        )
    return [dict(r) for r in rows]


@router.post("/equipe/membros", status_code=201)
async def criar_membro(
    body: MembroIn,
    authorization: str | None = Header(None),
):
    """Cria um novo membro no roster da equipe técnica.

    Requer token não-visualizador (403 para role=visualizador — T-04-02).
    Mitigações: T-04-01 (SQL parameterizado), T-04-02 (role check).
    """
    user = await _require_auth(authorization)
    if user.get("role") == "visualizador":
        raise HTTPException(403, "Visualizadores não podem criar membros")

    db_path = _db().db_path
    async with aiosqlite.connect(db_path) as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute(
            "INSERT INTO equipe_membros "
            "(nome, posto_grad, especialidade, tem_login, usuario_mat) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                body.nome,
                body.posto_grad,
                body.especialidade,
                body.tem_login if body.tem_login is not None else 0,
                body.usuario_mat,
            ),
        )
        new_id = cur.lastrowid
        await conn.commit()

    return {"id": new_id}


@router.put("/equipe/membros/{membro_id}")
async def editar_membro(
    membro_id: int,
    body: MembroUpdate,
    authorization: str | None = Header(None),
):
    """Edita campos de um membro ou soft-deleta (ativo=0).

    Nunca apaga o row (T-04-05 — soft-delete only).
    404 se id não encontrado. 403 para visualizador.
    Mitigações: T-04-01 (SQL parameterizado), T-04-02 (role check), T-04-05 (sem DELETE).
    """
    user = await _require_auth(authorization)
    if user.get("role") == "visualizador":
        raise HTTPException(403, "Visualizadores não podem editar membros")

    # Build SET clause from provided fields only (partial update)
    updates: dict = {}
    if body.nome is not None:
        updates["nome"] = body.nome
    if body.posto_grad is not None:
        updates["posto_grad"] = body.posto_grad
    if body.especialidade is not None:
        updates["especialidade"] = body.especialidade
    if body.tem_login is not None:
        updates["tem_login"] = body.tem_login
    if body.usuario_mat is not None:
        updates["usuario_mat"] = body.usuario_mat
    if body.ativo is not None:
        updates["ativo"] = body.ativo

    if not updates:
        return {"ok": True, "message": "Nenhum campo para atualizar"}

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [membro_id]

    db_path = _db().db_path
    async with aiosqlite.connect(db_path) as conn:
        cur = await conn.execute(
            f"UPDATE equipe_membros SET {set_clause} WHERE id = ?",  # noqa: S608 — set_clause from hardcoded keys
            values,
        )
        if cur.rowcount == 0:
            raise HTTPException(404, "Membro não encontrado")
        await conn.commit()

    return {"ok": True}


@router.get("/equipe/config")
async def get_config(authorization: str | None = Header(None)):
    """Retorna a configuração singleton da equipe (id=1) + capacidade derivada.

    Se a tabela estiver vazia (primeira vez), retorna os defaults do schema.
    Nunca insere na leitura (GET é idempotente).
    Mitigações: T-04-02 (_require_auth).

    Resposta: {"config": {...}, "capacidade": {h_dia_equipe, h_dia_total, h_semana, h_mes, h_ano}}
    """
    await _require_auth(authorization)
    db = _db()
    row = await db.fetch_one("SELECT * FROM equipe_config WHERE id = 1")
    if row:
        config = dict(row)
        # Deserialize JSON fields stored as TEXT; fall back to defaults on corrupt row
        try:
            config["dias_semana"] = json.loads(config["dias_semana"])
            config["turnos"] = json.loads(config["turnos"])
        except (json.JSONDecodeError, TypeError):
            config["dias_semana"] = _DEFAULT_CONFIG["dias_semana"]
            config["turnos"] = _DEFAULT_CONFIG["turnos"]
    else:
        # Return schema defaults without inserting (idempotent GET)
        config = dict(_DEFAULT_CONFIG)

    return {"config": config, "capacidade": _capacidade(config)}


@router.put("/equipe/config")
async def put_config(
    body: ConfigIn,
    authorization: str | None = Header(None),
):
    """Salva a configuração singleton (id=1) via UPSERT e retorna a capacidade recomputada.

    Serializa dias_semana e turnos como JSON TEXT no banco.
    Requer token não-visualizador (403).
    Mitigações: T-04-01 (SQL parameterizado), T-04-02 (role check), T-04-04 (ConfigIn validators).

    Resposta: {"config": {...saved...}, "capacidade": {h_dia_equipe, h_dia_total, h_semana, h_mes, h_ano}}
    """
    user = await _require_auth(authorization)
    if user.get("role") == "visualizador":
        raise HTTPException(403, "Visualizadores não podem alterar a configuração")

    # Serialize lists to JSON TEXT for storage (T-04-01 — never string-interpolate)
    dias_json = json.dumps([d for d in body.dias_semana], ensure_ascii=False)
    turnos_json = json.dumps([{"nome": t.nome, "horas": t.horas} for t in body.turnos], ensure_ascii=False)

    db_path = _db().db_path
    async with aiosqlite.connect(db_path) as conn:
        await conn.execute(
            "INSERT OR REPLACE INTO equipe_config "
            "(id, num_equipes, dias_semana, turnos, updated_at) "
            "VALUES (1, ?, ?, ?, datetime('now'))",
            (body.num_equipes, dias_json, turnos_json),
        )
        await conn.commit()

    # Build the saved config dict (lists — not raw JSON strings) for the response + _capacidade
    saved = {
        "id": 1,
        "num_equipes": body.num_equipes,
        "dias_semana": body.dias_semana,
        "turnos": [{"nome": t.nome, "horas": t.horas} for t in body.turnos],
    }

    return {"config": saved, "capacidade": _capacidade(saved)}


# ── Cronograma Preventivo — scheduling helpers (IMP-05) ──────────────────────
# Porta exata de pmocCronograma() do app de campo legado
# linhas 1983-2086.

# Duration estimation constants (verbatim from legacy lines 911-917)
MIN_POR_ITEM = 10          # minutes per checklist item
SETUP_MIN    = 15          # setup / displacement overhead

FATOR_TIPO_EQUIP: dict[str, float] = {
    "SPLIT":          1.0,
    "PISO/TETO":      1.15,
    "JANELA":         0.7,
    "SELF CONTAINED": 1.6,
}

FATOR_MANUT: dict[str, float] = {
    "INSPEÇÃO":     0.4,
    "PREVENTIVA":   1.0,
    "REVISÃO":      1.6,
    "LIMPEZA":      0.6,
    "CORRETIVA":    1.3,
    "RECARGA GÁS":  0.8,
    "SUBSTITUIÇÃO": 2.0,
}

# Checklist item counts (verbatim from legacy CHECKLIST, lines 1012-1057)
N_CHECKLIST: dict[str, int] = {
    "SPLIT":          9,
    "PISO/TETO":      9,
    "SELF CONTAINED": 12,
    "JANELA":         6,
    "_DEFAULT":       9,   # SPLIT baseline for non-refrigeration types
}

# Sort-key order (criticidade ASC index — CRÍTICA=0 first)
CRIT_ORDER: dict[str, int] = {
    "CRÍTICA": 0,
    "ALTA":    1,
    "MÉDIA":   2,
    "BAIXA":   3,
}
_CRIT_VALID = frozenset(CRIT_ORDER.keys())

# DOW mapping: equipe_config stores pt-BR abbrevs; Python weekday() is Mon=0
# JS getDay() is Sun=0 — we use explicit map to avoid off-by-one (Pitfall 2)
_DOW_STR_TO_PY: dict[str, int] = {
    "seg": 0, "ter": 1, "qua": 2, "qui": 3,
    "sex": 4, "sab": 5, "dom": 6,
}

# Portuguese day-of-week abbreviations for response (Assumption A4)
_DOW_PY_TO_ABBR: dict[int, str] = {
    0: "Seg", 1: "Ter", 2: "Qua", 3: "Qui",
    4: "Sex", 5: "Sáb", 6: "Dom",
}

# Greedy packing guards (Pitfall 5 / T-05-03)
MAX_JOBS    = 5000
MAX_DAYS    = 365
DEFAULT_CAP = 240    # fallback capacity in minutes (= 4h, same as legacy line 2006)


def _est_duracao_min(tipo: str, tipo_manut: str = "PREVENTIVA") -> int:
    """Porta exata de estTempoServico(e, tipoManut) — JS lines 919-925.

    duration_min = round(n_checklist × MIN_POR_ITEM × FATOR_TIPO_EQUIP × FATOR_MANUT + SETUP_MIN)
    Non-refrigeration types fall back to _DEFAULT (SPLIT baseline, f_eq=1.0).
    """
    n    = N_CHECKLIST.get(tipo, N_CHECKLIST["_DEFAULT"])
    f_eq = FATOR_TIPO_EQUIP.get(tipo, 1.0)
    f_m  = FATOR_MANUT.get(tipo_manut, 1.0)
    return round(n * MIN_POR_ITEM * f_eq * f_m + SETUP_MIN)


def _normaliza_crit(raw: str | None) -> str:
    """Map stored criticidade to a canonical CRIT_ORDER key.

    The ativos.criticidade migration default is 'operacional' — not a valid
    scheduling criticidade. Treat it (and any unrecognized/None value) as 'MÉDIA'
    (sort rank 2). Exact Unicode match required (Pitfall 4).
    """
    if raw and raw in _CRIT_VALID:
        return raw
    return "MÉDIA"


def _dias_uteis_set(dias_semana: list) -> set:
    """Convert equipe_config dias_semana list to Python weekday integer set.

    Handles non-string / unrecognized entries defensively (constraint #2).
    Falls back to Mon–Fri ({0,1,2,3,4}) if the result would be empty.
    """
    result = set()
    for d in dias_semana:
        if isinstance(d, str) and d in _DOW_STR_TO_PY:
            result.add(_DOW_STR_TO_PY[d])
    return result if result else {0, 1, 2, 3, 4}


def _proximo_dia_util(cursor: date, dias_uteis_py: set) -> date:
    """Advance cursor forward until a working day (mirrors JS while-loop, lines 2010-2012)."""
    while cursor.weekday() not in dias_uteis_py:
        cursor += timedelta(days=1)
    return cursor


def computar_cronograma(
    fila: list,
    cap_dia_min: float,
    dias_uteis_py: set,
    today: "date | None" = None,
) -> tuple:
    """Greedy packing scheduler — porta exata de pmocCronograma() JS lines 2004-2034.

    Args:
        fila         — sorted demand list: [{ativo_id, nome, tipo, criticidade,
                        duracao_min, duracao_h, falta, status, ...}]
        cap_dia_min  — daily capacity in minutes (h_dia_total × 60)
        dias_uteis_py — working weekday integers in Python Mon=0 convention
        today         — schedule start date (injectable for determinism; defaults to date.today())

    Returns:
        (dias, kpis) where:
          dias  — list of day dicts {data, dia_semana, itens, horas_usadas, horas_disponiveis}
          kpis  — {total_os, horas_pessoa, dias_uteis, data_conclusao, pct_utilizacao, alerta}
    """
    if today is None:
        today = date.today()

    # Guard zero/negative capacity (Pitfall 5 / T-05-03)
    cap_dia_min = max(cap_dia_min, 1)

    dias: list = []
    cursor = today

    def novo_dia() -> tuple:
        """Open a new working day: advance cursor to next util day, record, then step forward."""
        nonlocal cursor
        cursor = _proximo_dia_util(cursor, dias_uteis_py)
        dia: dict = {
            "data": cursor.isoformat(),
            "dia_semana": _DOW_PY_TO_ABBR.get(cursor.weekday(), "?"),
            "itens": [],
            "horas_usadas": 0.0,
            "horas_disponiveis": round(cap_dia_min / 60, 2),
        }
        dias.append(dia)
        cursor += timedelta(days=1)   # advance AFTER recording (mirrors JS line 2019)
        restante = cap_dia_min
        return dia, restante

    dia_atual, restante = novo_dia()
    guard = 0

    for job in fila:
        if guard >= MAX_JOBS:
            break
        guard += 1

        job_min = job["duracao_min"]

        # Overflow only when current day already has at least 1 item (JS lines 2025-2027)
        if job_min > restante and len(dia_atual["itens"]) > 0:
            if len(dias) >= MAX_DAYS:
                guard -= 1   # undo: job was not scheduled
                break
            dia_atual, restante = novo_dia()

        dia_atual["itens"].append(job)
        dia_atual["horas_usadas"] = round(dia_atual["horas_usadas"] + job_min / 60, 2)
        restante -= job_min

        # Open next day after filling current (JS lines 2031-2032)
        if restante <= 0:
            if len(dias) >= MAX_DAYS:
                break
            dia_atual, restante = novo_dia()

    # Remove trailing empty day (JS lines 2033-2034)
    if dias and not dias[-1]["itens"]:
        dias.pop()

    # KPI computation — use guard to know how many jobs were actually processed
    processed = min(guard, len(fila))
    total_min    = sum(j["duracao_min"] for j in fila[:processed])
    total_os     = processed
    dias_uteis   = len(dias)
    cap_total    = cap_dia_min * dias_uteis
    horas_pessoa = round(total_min / 60, 1)           # true division (Pitfall 5)
    data_conclusao = dias[-1]["data"] if dias else None
    pct_utilizacao = round(total_min / cap_total * 100, 1) if cap_total > 0 else 0.0
    alerta = total_min > cap_total

    kpis = {
        "total_os":       total_os,
        "horas_pessoa":   horas_pessoa,
        "dias_uteis":     dias_uteis,
        "data_conclusao": data_conclusao,
        "pct_utilizacao": pct_utilizacao,
        "alerta":         alerta,
    }
    return dias, kpis


# ── GET /cronograma endpoint (IMP-05) ─────────────────────────────────────────

@router.get("/cronograma")
async def get_cronograma(
    categoria: Optional[str] = None,
    today: Optional[str] = None,   # YYYY-MM-DD; injectable for deterministic tests
    authorization: str | None = Header(None),
):
    """GET /api/manutencao/cronograma — cronograma preventivo computado (read-only).

    Parâmetros:
      categoria — filtro opcional por categoria de ativo
      today     — data de início YYYY-MM-DD (override; omitir em produção → date.today())

    Resposta: {dias:[{data, dia_semana, itens:[...], horas_usadas, horas_disponiveis}],
               kpis:{total_os, horas_pessoa, dias_uteis, data_conclusao, pct_utilizacao, alerta}}

    Mitigações: T-05-01 (SQL parameterizado), T-05-02 (_require_auth), T-05-03 (cap guard),
                T-05-04 (date.fromisoformat → 422 on bad input).
    """
    await _require_auth(authorization)

    # ── Parse today param (T-05-04) ──────────────────────────────────────────
    if today is not None:
        try:
            today_date = date.fromisoformat(today)
        except ValueError:
            raise HTTPException(422, f"Parâmetro 'today' inválido: '{today}'. Use YYYY-MM-DD.")
    else:
        today_date = date.today()

    # ── Load crew config + capacity (mirrors GET /equipe/config) ─────────────
    db = _db()
    row = await db.fetch_one("SELECT * FROM equipe_config WHERE id = 1")
    if row:
        config = dict(row)
        try:
            config["dias_semana"] = json.loads(config["dias_semana"])
            config["turnos"] = json.loads(config["turnos"])
        except (json.JSONDecodeError, TypeError):
            config["dias_semana"] = _DEFAULT_CONFIG["dias_semana"]
            config["turnos"] = _DEFAULT_CONFIG["turnos"]
    else:
        config = dict(_DEFAULT_CONFIG)

    capacidade = _capacidade(config)
    cap_dia_min = max(capacidade["h_dia_total"] * 60, 1)
    dias_uteis_py = _dias_uteis_set(config["dias_semana"])

    # ── Demand query (parameterized — T-05-01) ────────────────────────────────
    # UNION: ativos with plan state + ativos without (initial mobilization, falta=0)
    SQL = """
        SELECT
            a.id          AS ativo_id,
            a.nome,
            a.tipo,
            a.categoria,
            a.uso_atual,
            COALESCE(
                pr.criticidade, pt.criticidade, pc.criticidade, pf.criticidade,
                CASE WHEN a.criticidade IN ('CRÍTICA','ALTA','MÉDIA','BAIXA')
                     THEN a.criticidade ELSE NULL END
            ) AS criticidade_raw,
            ape.proximo_uso,
            (ape.proximo_uso - a.uso_atual) AS falta,
            ape.catalogo_plano_item_id      AS item_id
        FROM ativos a
        JOIN ativo_plano_estado ape ON ape.ativo_id = a.id
        LEFT JOIN pmoc_refrigeracao pr ON pr.ativo_id = a.id
        LEFT JOIN pmoc_transportes  pt ON pt.ativo_id = a.id
        LEFT JOIN pmoc_corte        pc ON pc.ativo_id = a.id
        LEFT JOIN pmoc_fonoclama    pf ON pf.ativo_id = a.id
        WHERE a.ativo = 1
          AND (? IS NULL OR a.categoria = ?)
          AND ape.proximo_uso <= a.uso_atual + 500

        UNION ALL

        SELECT
            a.id, a.nome, a.tipo, a.categoria, a.uso_atual,
            COALESCE(
                pr.criticidade, pt.criticidade, pc.criticidade, pf.criticidade,
                CASE WHEN a.criticidade IN ('CRÍTICA','ALTA','MÉDIA','BAIXA')
                     THEN a.criticidade ELSE NULL END
            ),
            NULL  AS proximo_uso,
            0.0   AS falta,
            NULL  AS item_id
        FROM ativos a
        LEFT JOIN ativo_plano_estado ape ON ape.ativo_id = a.id
        LEFT JOIN pmoc_refrigeracao  pr  ON pr.ativo_id = a.id
        LEFT JOIN pmoc_transportes   pt  ON pt.ativo_id = a.id
        LEFT JOIN pmoc_corte         pc  ON pc.ativo_id = a.id
        LEFT JOIN pmoc_fonoclama     pf  ON pf.ativo_id = a.id
        WHERE a.ativo = 1
          AND (? IS NULL OR a.categoria = ?)
          AND ape.ativo_id IS NULL
    """
    rows = await db.fetch_all(SQL, (categoria, categoria, categoria, categoria))

    # ── Dedup by ativo_id — keep most-urgent row (lowest falta; tie-break on item_id) ──
    seen: dict[str, dict] = {}
    for r in rows:
        row_dict = dict(r)
        aid = row_dict["ativo_id"]
        if aid not in seen:
            seen[aid] = row_dict
        else:
            existing = seen[aid]
            # min falta; stable tie-break on item_id (Pitfall 3)
            e_falta = existing.get("falta") or 0.0
            r_falta = row_dict.get("falta") or 0.0
            e_item  = existing.get("item_id") or 0
            r_item  = row_dict.get("item_id") or 0
            if (r_falta, r_item) < (e_falta, e_item):
                seen[aid] = row_dict

    # ── Build fila with computed fields ──────────────────────────────────────
    fila = []
    for row_dict in seen.values():
        crit_raw    = row_dict.get("criticidade_raw")
        criticidade = _normaliza_crit(crit_raw)
        falta       = row_dict.get("falta") or 0.0
        duracao_min = _est_duracao_min(row_dict.get("tipo") or "")
        status      = "VENCIDA" if falta <= 0 else "PRÓXIMA"
        fila.append({
            "ativo_id":    row_dict["ativo_id"],
            "nome":        row_dict.get("nome") or "",
            "tipo":        row_dict.get("tipo") or "",
            "criticidade": criticidade,
            "duracao_min": duracao_min,
            "duracao_h":   round(duracao_min / 60, 2),
            "falta":       falta,
            "status":      status,
        })

    # ── Sort: criticidade rank → falta ASC → ativo_id ASC (stable — Pitfall 2) ──
    fila.sort(key=lambda j: (
        CRIT_ORDER.get(j["criticidade"], 2),
        j["falta"],
        j["ativo_id"],
    ))

    # ── Pack greedy + compute KPIs ────────────────────────────────────────────
    dias, kpis = computar_cronograma(fila, cap_dia_min, dias_uteis_py, today_date)

    return {"dias": dias, "kpis": kpis}
