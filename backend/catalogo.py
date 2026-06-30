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
    categoria: Optional[str] = None        # taxonomia de serviço (TRANSPORTE|MANUTENCAO|CONTROLE VEGETAL|CONTROLE BIOLOGICO)
    subcategoria: Optional[str] = None     # subcategoria (ex.: REFRIGERACAO, LIXO)
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
        "pop_doc_id, tempo_estimado_min, servico_pai_id, aplicavel_a, categoria, subcategoria, criado_por_modulo) "
        "VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?)",
        (sid, body.codigo, body.nome, body.descricao, body.escopo,
         body.pop_doc_id, body.tempo_estimado_min, body.servico_pai_id,
         aplic_json, body.categoria, body.subcategoria, body.criado_por_modulo),
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
        "pop_doc_id, tempo_estimado_min, servico_pai_id, aplicavel_a, categoria, subcategoria, criado_por_modulo) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (new_id, old["codigo"], body.nome, body.descricao, body.escopo, next_versao,
         body.pop_doc_id, body.tempo_estimado_min, body.servico_pai_id,
         aplic_json, body.categoria, body.subcategoria, body.criado_por_modulo),
    )
    return await get_servico(new_id)


class ServicoMaterialIn(BaseModel):
    material_id: Optional[int] = None   # estoque.id; ou nome_livre
    nome_livre: Optional[str] = None
    qtd: float
    unidade: str
    obrigatorio: int = 1
    obs: Optional[str] = None


async def _materiais_do_servico(sid: str):
    return await _db().fetch_all(
        """SELECT m.id, m.material_id, m.nome_livre, m.qtd, m.unidade, m.obrigatorio,
                  e.codigo AS estoque_codigo, e.nome AS estoque_nome
           FROM catalogo_servico_materiais m
           LEFT JOIN estoque e ON e.id = m.material_id
           WHERE m.servico_id = ?""",
        (sid,),
    )


@router.get("/servicos/{sid}/materiais")
async def list_servico_materiais(sid: str):
    return await _materiais_do_servico(sid)


@router.post("/servicos/{sid}/materiais", status_code=201)
async def add_servico_material(sid: str, body: ServicoMaterialIn, authorization: str | None = Header(None)):
    await _require_auth(authorization)
    db = _db()
    if not await db.fetch_one("SELECT id FROM catalogo_servicos WHERE id = ?", (sid,)):
        raise HTTPException(404, "Serviço não encontrado")
    if body.material_id is None and not body.nome_livre:
        raise HTTPException(400, "Informe material_id ou nome_livre")
    await db.execute(
        "INSERT INTO catalogo_servico_materiais (servico_id, material_id, nome_livre, qtd, unidade, obrigatorio, obs) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (sid, body.material_id, body.nome_livre, body.qtd, body.unidade, body.obrigatorio, body.obs),
    )
    return await _materiais_do_servico(sid)


@router.delete("/servicos/{sid}/materiais/{mid}")
async def del_servico_material(sid: str, mid: int, authorization: str | None = Header(None)):
    await _require_auth(authorization)
    await _db().execute(
        "DELETE FROM catalogo_servico_materiais WHERE id = ? AND servico_id = ?", (mid, sid)
    )
    return {"ok": True}


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


# ── Planos de Manutenção (planos_manutencao) — APOSENTADO ──────────────────────
# Substituído por catalogo_planos (/planos-catalogo). Mantidos como stubs para não
# quebrar clientes antigos: GET retorna vazio; escrita responde 410 Gone.
_DEPRECATED = "planos_manutencao foi aposentado; use /api/catalogo/planos-catalogo"


@router.get("/planos")
async def list_planos(ativo_id: str | None = None, servico_id: str | None = None,
                      tipo_codigo: str | None = None, ativo: int = 1):
    return []


@router.get("/planos/{pid}")
async def get_plano(pid: str):
    raise HTTPException(410, _DEPRECATED)


@router.post("/planos", status_code=410)
async def create_plano(body: dict, authorization: str | None = Header(None)):
    raise HTTPException(410, _DEPRECATED)


@router.put("/planos/{pid}")
async def update_plano(pid: str, body: dict, authorization: str | None = Header(None)):
    raise HTTPException(410, _DEPRECATED)


@router.patch("/planos/{pid}/arquivar")
async def arquivar_plano(pid: str, authorization: str | None = Header(None)):
    raise HTTPException(410, _DEPRECATED)


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


# ── Planos nomeados (modelo unificado, qualquer categoria) ──────────────────────
# catalogo_planos = plano nomeado (pacote de serviços + disparo + tipos aplicáveis).
# Disparo por serviço (catalogo_plano_itens.frequencia) com default no plano.
@router.get("/planos-catalogo")
async def list_planos_catalogo(
    categoria: str | None = Query(None),
    tipo: str | None = Query(None, description="tipo_codigo aplicável"),
):
    where, params = ["p.ativo = 1"], []
    if categoria:
        where.append("p.categoria = ?"); params.append(categoria)
    if tipo:
        # casa tipo_codigo legado OU presença na lista aplicavel_tipos (JSON)
        where.append("(p.tipo_codigo = ? OR p.aplicavel_tipos LIKE ?)")
        params.extend([tipo, f'%"{tipo}"%'])
    rows = await _db().fetch_all(
        "SELECT p.*, "
        " (SELECT COUNT(*) FROM catalogo_plano_itens i WHERE i.plano_id = p.id) AS n_servicos, "
        " (SELECT COUNT(*) FROM catalogo_plano_itens i WHERE i.plano_id = p.id AND i.classe='prev') AS n_preventivos "
        f"FROM catalogo_planos p WHERE {' AND '.join(where)} ORDER BY p.categoria, p.codigo",
        tuple(params),
    )
    return rows


@router.get("/planos-catalogo/{pid}")
async def get_plano_catalogo(pid: str):
    plano = await _db().fetch_one("SELECT * FROM catalogo_planos WHERE id = ?", (pid,))
    if not plano:
        raise HTTPException(404, "Plano não encontrado")
    itens = await _db().fetch_all(
        "SELECT i.seq, i.classe, i.frequencia, i.item_arp, i.valor_unit, i.qtd_cmasm, "
        "       s.id AS servico_id, s.codigo, s.nome, s.tempo_estimado_min "
        "FROM catalogo_plano_itens i JOIN catalogo_servicos s ON s.id = i.servico_id "
        "WHERE i.plano_id = ? ORDER BY i.seq",
        (pid,),
    )
    # materiais por serviço do item (display)
    for it in itens:
        it["materiais"] = await _db().fetch_all(
            "SELECT m.material_id, m.nome_livre, m.qtd, m.unidade, e.nome AS material_nome "
            "FROM catalogo_servico_materiais m LEFT JOIN estoque e ON e.id = m.material_id "
            "WHERE m.servico_id = ?",
            (it["servico_id"],),
        )
        if not it.get("frequencia"):
            it["frequencia"] = plano.get("frequencia")  # fallback ao default do plano
    plano["itens"] = itens
    return plano


# ── CRUD do plano nomeado ───────────────────────────────────────────────────────
class PlanoCatalogoIn(BaseModel):
    nome: str
    categoria: str = "climatizacao"
    codigo: Optional[str] = None
    aplicavel_tipos: list[str] = []
    frequencia: Optional[dict] = None    # {tipo:por_uso|por_tempo, valor, unidade}


class PlanoItemIn(BaseModel):
    servico_id: str
    frequencia: Optional[dict] = None
    classe: str = "prev"
    seq: int = 0


@router.post("/planos-catalogo", status_code=201)
async def create_plano_catalogo(body: PlanoCatalogoIn):
    pid = "plano-" + _uuid_mod.uuid4().hex[:10]
    codigo = body.codigo or pid[-6:].upper()
    await _db().execute(
        "INSERT INTO catalogo_planos (id, codigo, nome, categoria, aplicavel_tipos, frequencia, fonte, ativo) "
        "VALUES (?,?,?,?,?,?, 'manual', 1)",
        (pid, codigo, body.nome, body.categoria,
         json.dumps(body.aplicavel_tipos),
         json.dumps(body.frequencia) if body.frequencia else None),
    )
    return await _db().fetch_one("SELECT * FROM catalogo_planos WHERE id = ?", (pid,))


@router.put("/planos-catalogo/{pid}")
async def update_plano_catalogo(pid: str, body: PlanoCatalogoIn):
    row = await _db().fetch_one("SELECT id FROM catalogo_planos WHERE id = ?", (pid,))
    if not row:
        raise HTTPException(404, "Plano não encontrado")
    await _db().execute(
        "UPDATE catalogo_planos SET nome=?, categoria=?, codigo=COALESCE(?,codigo), aplicavel_tipos=?, frequencia=? WHERE id=?",
        (body.nome, body.categoria, body.codigo,
         json.dumps(body.aplicavel_tipos),
         json.dumps(body.frequencia) if body.frequencia else None, pid),
    )
    return await _db().fetch_one("SELECT * FROM catalogo_planos WHERE id = ?", (pid,))


@router.delete("/planos-catalogo/{pid}")
async def delete_plano_catalogo(pid: str):
    row = await _db().fetch_one("SELECT id FROM catalogo_planos WHERE id = ?", (pid,))
    if not row:
        raise HTTPException(404, "Plano não encontrado")
    await _db().execute("UPDATE catalogo_planos SET ativo = 0 WHERE id = ?", (pid,))  # soft delete
    return {"ok": True}


@router.post("/planos-catalogo/{pid}/itens", status_code=201)
async def add_plano_item(pid: str, body: PlanoItemIn):
    plano = await _db().fetch_one("SELECT id FROM catalogo_planos WHERE id = ?", (pid,))
    if not plano:
        raise HTTPException(404, "Plano não encontrado")
    svc = await _db().fetch_one("SELECT id FROM catalogo_servicos WHERE id = ?", (body.servico_id,))
    if not svc:
        raise HTTPException(400, "Serviço inexistente")
    await _db().execute(
        "INSERT OR IGNORE INTO catalogo_plano_itens (plano_id, servico_id, seq, classe, frequencia) VALUES (?,?,?,?,?)",
        (pid, body.servico_id, body.seq, body.classe,
         json.dumps(body.frequencia) if body.frequencia else None),
    )
    return {"ok": True}


@router.delete("/planos-catalogo/{pid}/itens/{servico_id}")
async def del_plano_item(pid: str, servico_id: str):
    await _db().execute(
        "DELETE FROM catalogo_plano_itens WHERE plano_id = ? AND servico_id = ?", (pid, servico_id))
    return {"ok": True}
