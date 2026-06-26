"""
API de Catálogo de Serviços, Planos de Manutenção e Qualificações.

Referências: Rules.md §§10-15, schema_catalogo.sql.

Versionamento de serviços: cada PUT cria nova linha com versao+1 em vez de
atualizar in-place — garantindo rastreabilidade de snapshot nas OS.
Queries de listagem retornam apenas a versão mais recente por código.
"""
from __future__ import annotations

import json
import sys
import uuid as _uuid_mod
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Header, Query
from pydantic import BaseModel, field_validator

router = APIRouter(prefix="/api/catalogo", tags=["catalogo"])


def _db():
    return sys.modules["backend.main"].db


def _new_uuid() -> str:
    return str(_uuid_mod.uuid4())


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds")


async def _require_auth(authorization: str | None) -> dict:
    from fastapi import HTTPException as _HTTPException
    if not authorization or not authorization.startswith("Bearer "):
        raise _HTTPException(401, "Token ausente")
    token = authorization[7:]
    row = await _db().fetch_one(
        "SELECT s.usuario_id, u.nome, u.role FROM sessoes s JOIN usuarios u ON u.id = s.usuario_id "
        "WHERE s.token = ? AND s.expira_em > datetime('now')",
        (token,),
    )
    if not row:
        raise _HTTPException(401, "Token inválido ou expirado")
    return row


# ── Models ────────────────────────────────────────────────────────────────────

class ServicoIn(BaseModel):
    codigo: str
    nome: str
    descricao: Optional[str] = None
    escopo: str = "central"
    pop_doc_id: Optional[str] = None
    tempo_estimado_min: Optional[int] = None
    servico_pai_id: Optional[str] = None
    aplicavel_a: Optional[dict[str, Any]] = None  # {"categorias": [...], "tipos": [...]}
    criado_por_modulo: str = "manutencao"

    @field_validator("escopo")
    @classmethod
    def escopo_valido(cls, v: str) -> str:
        if v not in ("central", "local"):
            raise ValueError("escopo deve ser 'central' ou 'local'")
        return v


class PlanoIn(BaseModel):
    servico_id: str
    servico_versao_pin: Optional[int] = None
    ativo_id: Optional[str] = None
    tipo_codigo: Optional[str] = None
    frequencia: dict[str, Any]           # {"tipo": "periodica", "valor": "P1M"}
    criticidade_override: Optional[str] = None
    janela_permitida: Optional[dict[str, Any]] = None
    proxima_execucao: Optional[str] = None
    ultima_execucao: Optional[str] = None
    responsavel_pmoc: Optional[str] = None
    obs: Optional[str] = None
    criado_por_modulo: str = "manutencao"

    @field_validator("criticidade_override")
    @classmethod
    def crit_valida(cls, v: str | None) -> str | None:
        valid = {None, "admin", "operacional", "critico_24x7"}
        if v not in valid:
            raise ValueError(f"criticidade_override deve ser um de {valid - {None}}")
        return v


class QualificacaoIn(BaseModel):
    codigo: str
    nome: str
    descricao: Optional[str] = None
    requer_validade: int = 1


class UsuarioQualificacaoIn(BaseModel):
    qualificacao_codigo: str
    obtida_em: Optional[str] = None
    valida_ate: Optional[str] = None
    doc_id: Optional[str] = None
    status: str = "valida"
    obs: Optional[str] = None

    @field_validator("status")
    @classmethod
    def status_valido(cls, v: str) -> str:
        if v not in ("valida", "vencida", "suspensa"):
            raise ValueError("status deve ser valida|vencida|suspensa")
        return v


# ── Serviços ──────────────────────────────────────────────────────────────────

@router.get("/servicos")
async def list_servicos(
    escopo: str | None = None,
    categoria: str | None = None,
    codigo: str | None = None,
    ativo: int = 1,
    materiais: int = 0,
):
    """Retorna a versão mais recente de cada serviço (último versao por codigo)."""
    db = _db()
    clauses = ["s.ativo = ?"]
    params: list[Any] = [ativo]
    if escopo:
        clauses.append("s.escopo = ?")
        params.append(escopo)
    if codigo:
        clauses.append("s.codigo = ?")
        params.append(codigo)
    where = "WHERE " + " AND ".join(clauses)
    rows = await db.fetch_all(
        f"""SELECT s.*
            FROM catalogo_servicos s
            INNER JOIN (
                SELECT codigo, MAX(versao) AS versao_max
                FROM catalogo_servicos
                WHERE ativo = ?
                GROUP BY codigo
            ) latest ON s.codigo = latest.codigo AND s.versao = latest.versao_max
            {where}
            ORDER BY s.codigo""",
        (ativo, *params),
    )
    if categoria:
        def _match(row: dict) -> bool:
            try:
                aplic = json.loads(row.get("aplicavel_a") or "{}")
            except (ValueError, TypeError):
                return True
            cats = aplic.get("categorias") or []
            return not cats or categoria in cats
        rows = [r for r in rows if _match(r)]
    for row in rows:
        try:
            row["aplicavel_a"] = json.loads(row["aplicavel_a"] or "{}")
        except (ValueError, TypeError):
            row["aplicavel_a"] = {}
    if materiais and rows:
        ids = [r["id"] for r in rows]
        ph = ",".join("?" * len(ids))
        mats = await db.fetch_all(
            f"""SELECT m.servico_id, m.qtd, m.unidade, m.obrigatorio, m.nome_livre,
                       e.codigo AS estoque_codigo, e.nome AS estoque_nome,
                       e.qtd_atual, e.qtd_minima
                FROM catalogo_servico_materiais m
                LEFT JOIN estoque e ON e.id = m.material_id
                WHERE m.servico_id IN ({ph})""",
            ids,
        )
        by_svc: dict[str, list] = {}
        for m in mats:
            by_svc.setdefault(m["servico_id"], []).append(m)
        for row in rows:
            row["materiais"] = by_svc.get(row["id"], [])
    return rows


@router.get("/servicos/{sid}")
async def get_servico(sid: str):
    db = _db()
    row = await db.fetch_one("SELECT * FROM catalogo_servicos WHERE id = ?", (sid,))
    if not row:
        raise HTTPException(404, "Serviço não encontrado")
    try:
        row["aplicavel_a"] = json.loads(row["aplicavel_a"] or "{}")
    except (ValueError, TypeError):
        row["aplicavel_a"] = {}
    materiais = await db.fetch_all(
        "SELECT * FROM catalogo_servico_materiais WHERE servico_id = ?", (sid,)
    )
    ferramentas = await db.fetch_all(
        "SELECT * FROM catalogo_servico_ferramentas WHERE servico_id = ?", (sid,)
    )
    pessoal = await db.fetch_all(
        "SELECT * FROM catalogo_servico_pessoal WHERE servico_id = ?", (sid,)
    )
    return {**row, "materiais": materiais, "ferramentas": ferramentas, "pessoal": pessoal}


@router.post("/servicos", status_code=201)
async def create_servico(body: ServicoIn, authorization: str | None = Header(None)):
    await _require_auth(authorization)
    db = _db()
    # Verifica se já existe alguma versão com esse código
    existing = await db.fetch_one(
        "SELECT MAX(versao) AS v FROM catalogo_servicos WHERE codigo = ?", (body.codigo,)
    )
    if existing and existing["v"] is not None:
        raise HTTPException(409, f"Código '{body.codigo}' já existe. Use PUT para criar nova versão.")
    sid = _new_uuid()
    aplic_json = json.dumps(body.aplicavel_a) if body.aplicavel_a is not None else None
    await db.execute(
        "INSERT INTO catalogo_servicos (id, codigo, nome, descricao, escopo, versao, "
        "pop_doc_id, tempo_estimado_min, servico_pai_id, aplicavel_a, criado_por_modulo) "
        "VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?)",
        (sid, body.codigo, body.nome, body.descricao, body.escopo,
         body.pop_doc_id, body.tempo_estimado_min, body.servico_pai_id,
         aplic_json, body.criado_por_modulo),
    )
    return await get_servico(sid)


@router.put("/servicos/{sid}")
async def update_servico(sid: str, body: ServicoIn, authorization: str | None = Header(None)):
    """Cria nova versão imutável do serviço (versao += 1). Retorna o novo registro."""
    await _require_auth(authorization)
    db = _db()
    old = await db.fetch_one("SELECT codigo, versao FROM catalogo_servicos WHERE id = ?", (sid,))
    if not old:
        raise HTTPException(404, "Serviço não encontrado")
    next_versao = old["versao"] + 1
    new_id = _new_uuid()
    aplic_json = json.dumps(body.aplicavel_a) if body.aplicavel_a is not None else None
    await db.execute(
        "INSERT INTO catalogo_servicos (id, codigo, nome, descricao, escopo, versao, "
        "pop_doc_id, tempo_estimado_min, servico_pai_id, aplicavel_a, criado_por_modulo) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (new_id, old["codigo"], body.nome, body.descricao, body.escopo, next_versao,
         body.pop_doc_id, body.tempo_estimado_min, body.servico_pai_id,
         aplic_json, body.criado_por_modulo),
    )
    return await get_servico(new_id)


@router.patch("/servicos/{sid}/arquivar")
async def arquivar_servico(sid: str, authorization: str | None = Header(None)):
    await _require_auth(authorization)
    row = await _db().fetch_one("SELECT id FROM catalogo_servicos WHERE id = ?", (sid,))
    if not row:
        raise HTTPException(404, "Serviço não encontrado")
    await _db().execute(
        "UPDATE catalogo_servicos SET ativo = 0, atualizado_em = ? WHERE id = ?",
        (_utc_now(), sid),
    )
    return {"ok": True}


# ── Planos de Manutenção ──────────────────────────────────────────────────────

async def _get_plano(pid: str) -> dict:
    row = await _db().fetch_one("SELECT * FROM planos_manutencao WHERE id = ?", (pid,))
    if not row:
        raise HTTPException(404, "Plano não encontrado")
    for col in ("frequencia", "janela_permitida"):
        try:
            row[col] = json.loads(row[col] or "null")
        except (ValueError, TypeError):
            row[col] = None
    return row


@router.get("/planos")
async def list_planos(
    ativo_id: str | None = None,
    servico_id: str | None = None,
    tipo_codigo: str | None = None,
    ativo: int = 1,
):
    db = _db()
    clauses = ["p.ativo = ?"]
    params: list[Any] = [ativo]
    if ativo_id:
        clauses.append("p.ativo_id = ?")
        params.append(ativo_id)
    if servico_id:
        clauses.append("p.servico_id = ?")
        params.append(servico_id)
    if tipo_codigo:
        clauses.append("p.tipo_codigo = ?")
        params.append(tipo_codigo)
    where = "WHERE " + " AND ".join(clauses)
    rows = await db.fetch_all(
        f"""SELECT p.*, s.codigo AS servico_codigo, s.nome AS servico_nome,
                   a.nome AS ativo_nome, a.categoria AS ativo_categoria
            FROM planos_manutencao p
            LEFT JOIN catalogo_servicos s ON s.id = p.servico_id
            LEFT JOIN ativos a ON a.id = p.ativo_id
            {where}
            ORDER BY p.proxima_execucao""",
        tuple(params),
    )
    for row in rows:
        for col in ("frequencia", "janela_permitida"):
            try:
                row[col] = json.loads(row[col] or "null")
            except (ValueError, TypeError):
                row[col] = None
    return rows


@router.get("/planos/{pid}")
async def get_plano(pid: str):
    return await _get_plano(pid)


@router.post("/planos", status_code=201)
async def create_plano(body: PlanoIn, authorization: str | None = Header(None)):
    await _require_auth(authorization)
    db = _db()
    if not body.ativo_id and not body.tipo_codigo:
        raise HTTPException(422, "Plano exige 'ativo_id' ou 'tipo_codigo' (apenas um)")
    if body.ativo_id and body.tipo_codigo:
        raise HTTPException(422, "Plano não pode ter ambos 'ativo_id' e 'tipo_codigo'")
    # Validate FK
    svc = await db.fetch_one("SELECT id FROM catalogo_servicos WHERE id = ?", (body.servico_id,))
    if not svc:
        raise HTTPException(404, f"Serviço '{body.servico_id}' não encontrado")
    if body.ativo_id:
        ativo = await db.fetch_one("SELECT id FROM ativos WHERE id = ?", (body.ativo_id,))
        if not ativo:
            raise HTTPException(404, f"Ativo '{body.ativo_id}' não encontrado")
    pid = _new_uuid()
    freq_json = json.dumps(body.frequencia)
    janela_json = json.dumps(body.janela_permitida) if body.janela_permitida is not None else None
    await db.execute(
        "INSERT INTO planos_manutencao (id, servico_id, servico_versao_pin, ativo_id, tipo_codigo, "
        "frequencia, criticidade_override, janela_permitida, proxima_execucao, ultima_execucao, "
        "responsavel_pmoc, obs, criado_por_modulo) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (pid, body.servico_id, body.servico_versao_pin, body.ativo_id, body.tipo_codigo,
         freq_json, body.criticidade_override, janela_json,
         body.proxima_execucao, body.ultima_execucao,
         body.responsavel_pmoc, body.obs, body.criado_por_modulo),
    )
    return await _get_plano(pid)


@router.put("/planos/{pid}")
async def update_plano(pid: str, body: PlanoIn, authorization: str | None = Header(None)):
    await _require_auth(authorization)
    db = _db()
    row = await db.fetch_one("SELECT id FROM planos_manutencao WHERE id = ?", (pid,))
    if not row:
        raise HTTPException(404, "Plano não encontrado")
    if not body.ativo_id and not body.tipo_codigo:
        raise HTTPException(422, "Plano exige 'ativo_id' ou 'tipo_codigo' (apenas um)")
    if body.ativo_id and body.tipo_codigo:
        raise HTTPException(422, "Plano não pode ter ambos 'ativo_id' e 'tipo_codigo'")
    freq_json = json.dumps(body.frequencia)
    janela_json = json.dumps(body.janela_permitida) if body.janela_permitida is not None else None
    await db.execute(
        "UPDATE planos_manutencao SET servico_id=?, servico_versao_pin=?, ativo_id=?, tipo_codigo=?, "
        "frequencia=?, criticidade_override=?, janela_permitida=?, proxima_execucao=?, "
        "ultima_execucao=?, responsavel_pmoc=?, obs=?, atualizado_em=? WHERE id=?",
        (body.servico_id, body.servico_versao_pin, body.ativo_id, body.tipo_codigo,
         freq_json, body.criticidade_override, janela_json,
         body.proxima_execucao, body.ultima_execucao,
         body.responsavel_pmoc, body.obs, _utc_now(), pid),
    )
    return await _get_plano(pid)


@router.patch("/planos/{pid}/arquivar")
async def arquivar_plano(pid: str, authorization: str | None = Header(None)):
    await _require_auth(authorization)
    row = await _db().fetch_one("SELECT id FROM planos_manutencao WHERE id = ?", (pid,))
    if not row:
        raise HTTPException(404, "Plano não encontrado")
    await _db().execute(
        "UPDATE planos_manutencao SET ativo = 0, atualizado_em = ? WHERE id = ?",
        (_utc_now(), pid),
    )
    return {"ok": True}


# ── Qualificações ─────────────────────────────────────────────────────────────

@router.get("/qualificacoes")
async def list_qualificacoes(ativo: int = 1):
    return await _db().fetch_all(
        "SELECT * FROM qualificacoes_catalogo WHERE ativo = ? ORDER BY codigo", (ativo,)
    )


@router.get("/qualificacoes/{codigo}")
async def get_qualificacao(codigo: str):
    row = await _db().fetch_one(
        "SELECT * FROM qualificacoes_catalogo WHERE codigo = ?", (codigo,)
    )
    if not row:
        raise HTTPException(404, "Qualificação não encontrada")
    return row


@router.post("/qualificacoes", status_code=201)
async def create_qualificacao(body: QualificacaoIn, authorization: str | None = Header(None)):
    await _require_auth(authorization)
    db = _db()
    existing = await db.fetch_one(
        "SELECT codigo FROM qualificacoes_catalogo WHERE codigo = ?", (body.codigo,)
    )
    if existing:
        raise HTTPException(409, f"Qualificação '{body.codigo}' já existe")
    await db.execute(
        "INSERT INTO qualificacoes_catalogo (codigo, nome, descricao, requer_validade) VALUES (?, ?, ?, ?)",
        (body.codigo, body.nome, body.descricao, body.requer_validade),
    )
    return await get_qualificacao(body.codigo)


@router.put("/qualificacoes/{codigo}")
async def update_qualificacao(codigo: str, body: QualificacaoIn, authorization: str | None = Header(None)):
    await _require_auth(authorization)
    db = _db()
    row = await db.fetch_one("SELECT codigo FROM qualificacoes_catalogo WHERE codigo = ?", (codigo,))
    if not row:
        raise HTTPException(404, "Qualificação não encontrada")
    await db.execute(
        "UPDATE qualificacoes_catalogo SET nome=?, descricao=?, requer_validade=? WHERE codigo=?",
        (body.nome, body.descricao, body.requer_validade, codigo),
    )
    return await get_qualificacao(codigo)


# ── Qualificações por usuário ─────────────────────────────────────────────────

@router.get("/usuarios/{uid}/qualificacoes")
async def list_usuario_qualificacoes(uid: int):
    db = _db()
    user = await db.fetch_one("SELECT id FROM usuarios WHERE id = ?", (uid,))
    if not user:
        raise HTTPException(404, "Usuário não encontrado")
    return await db.fetch_all(
        """SELECT uq.*, q.nome AS qualificacao_nome, q.requer_validade
           FROM usuario_qualificacoes uq
           JOIN qualificacoes_catalogo q ON q.codigo = uq.qualificacao_codigo
           WHERE uq.usuario_id = ?
           ORDER BY uq.valida_ate DESC""",
        (uid,),
    )


@router.post("/usuarios/{uid}/qualificacoes", status_code=201)
async def add_usuario_qualificacao(
    uid: int, body: UsuarioQualificacaoIn, authorization: str | None = Header(None)
):
    await _require_auth(authorization)
    db = _db()
    user = await db.fetch_one("SELECT id FROM usuarios WHERE id = ?", (uid,))
    if not user:
        raise HTTPException(404, "Usuário não encontrado")
    qual = await db.fetch_one(
        "SELECT codigo FROM qualificacoes_catalogo WHERE codigo = ?", (body.qualificacao_codigo,)
    )
    if not qual:
        raise HTTPException(404, f"Qualificação '{body.qualificacao_codigo}' não encontrada")
    existing = await db.fetch_one(
        "SELECT id FROM usuario_qualificacoes WHERE usuario_id = ? AND qualificacao_codigo = ?",
        (uid, body.qualificacao_codigo),
    )
    if existing:
        raise HTTPException(
            409,
            f"Usuário já possui a qualificação '{body.qualificacao_codigo}'. Use PUT para atualizar.",
        )
    qid = await db.execute(
        "INSERT INTO usuario_qualificacoes (usuario_id, qualificacao_codigo, obtida_em, valida_ate, "
        "doc_id, status, obs) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (uid, body.qualificacao_codigo, body.obtida_em, body.valida_ate,
         body.doc_id, body.status, body.obs),
    )
    row = await db.fetch_one(
        """SELECT uq.*, q.nome AS qualificacao_nome, q.requer_validade
           FROM usuario_qualificacoes uq
           JOIN qualificacoes_catalogo q ON q.codigo = uq.qualificacao_codigo
           WHERE uq.id = ?""",
        (qid,),
    )
    return row


@router.put("/usuarios/{uid}/qualificacoes/{codigo}")
async def update_usuario_qualificacao(
    uid: int, codigo: str, body: UsuarioQualificacaoIn, authorization: str | None = Header(None)
):
    await _require_auth(authorization)
    db = _db()
    row = await db.fetch_one(
        "SELECT id FROM usuario_qualificacoes WHERE usuario_id = ? AND qualificacao_codigo = ?",
        (uid, codigo),
    )
    if not row:
        raise HTTPException(404, "Qualificação do usuário não encontrada")
    await db.execute(
        "UPDATE usuario_qualificacoes SET obtida_em=?, valida_ate=?, doc_id=?, status=?, obs=? "
        "WHERE usuario_id=? AND qualificacao_codigo=?",
        (body.obtida_em, body.valida_ate, body.doc_id, body.status, body.obs, uid, codigo),
    )
    return await db.fetch_one(
        """SELECT uq.*, q.nome AS qualificacao_nome, q.requer_validade
           FROM usuario_qualificacoes uq
           JOIN qualificacoes_catalogo q ON q.codigo = uq.qualificacao_codigo
           WHERE uq.usuario_id = ? AND uq.qualificacao_codigo = ?""",
        (uid, codigo),
    )


@router.delete("/usuarios/{uid}/qualificacoes/{codigo}")
async def remove_usuario_qualificacao(
    uid: int, codigo: str, authorization: str | None = Header(None)
):
    await _require_auth(authorization)
    db = _db()
    row = await db.fetch_one(
        "SELECT id FROM usuario_qualificacoes WHERE usuario_id = ? AND qualificacao_codigo = ?",
        (uid, codigo),
    )
    if not row:
        raise HTTPException(404, "Qualificação do usuário não encontrada")
    await db.execute(
        "DELETE FROM usuario_qualificacoes WHERE usuario_id = ? AND qualificacao_codigo = ?",
        (uid, codigo),
    )
    return {"ok": True}


# ── Planos de climatização (template = conjunto de serviços por variante) ───────
# catalogo_planos + catalogo_plano_itens (ver tools/import_ata2_climatizacao.py).
# Difere de /planos (planos_manutencao = agendamento por ativo).

@router.get("/planos-climatizacao")
async def list_planos_climatizacao(
    tipo: str | None = Query(None, description="tipo_codigo (ex AC_SPLIT)"),
    btu: int | None = Query(None),
    inverter: int | None = Query(None, ge=0, le=1),
):
    where, params = ["categoria = 'climatizacao'", "ativo = 1"], []
    if tipo:
        where.append("tipo_codigo = ?"); params.append(tipo)
    if btu is not None:
        where.append("btu = ?"); params.append(btu)
    if inverter is not None:
        where.append("inverter = ?"); params.append(inverter)
    rows = await _db().fetch_all(
        "SELECT p.*, "
        " (SELECT COUNT(*) FROM catalogo_plano_itens i WHERE i.plano_id = p.id) AS n_servicos, "
        " (SELECT COUNT(*) FROM catalogo_plano_itens i WHERE i.plano_id = p.id AND i.classe='prev') AS n_preventivos "
        f"FROM catalogo_planos p WHERE {' AND '.join(where)} ORDER BY p.codigo",
        tuple(params),
    )
    return rows


@router.get("/planos-climatizacao/{pid}")
async def get_plano_climatizacao(pid: str):
    plano = await _db().fetch_one("SELECT * FROM catalogo_planos WHERE id = ?", (pid,))
    if not plano:
        raise HTTPException(404, "Plano não encontrado")
    plano["itens"] = await _db().fetch_all(
        "SELECT i.seq, i.classe, i.item_arp, i.valor_unit, i.qtd_ata, i.lim_adesao, i.qtd_cmasm, "
        "       s.id AS servico_id, s.codigo, s.nome "
        "FROM catalogo_plano_itens i JOIN catalogo_servicos s ON s.id = i.servico_id "
        "WHERE i.plano_id = ? ORDER BY i.seq",
        (pid,),
    )
    return plano
