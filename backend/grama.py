"""
Rotas /api/grama/* — Controle Vegetal
Portado de xGrama/controle-vegetal/backend/routes/*.js
"""
from __future__ import annotations

import json
import time
from datetime import date
from typing import Optional, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/grama", tags=["grama"])

# db é injetado pelo main.py via app.state.db
_db = None


def _get_db():
    if _db is None:
        raise RuntimeError("grama router not initialized — call init_grama(db) first")
    return _db


def init_grama(db) -> None:
    global _db
    _db = db


# ── Utilitários ───────────────────────────────────────────────────────────────

def _uid(prefix: str) -> str:
    return f"{prefix}-{int(time.time() * 1000)}"


def _calc_compatibilidade(flora: Optional[str], inclinacao: Optional[str], limpeza: Optional[str]) -> Optional[str]:
    """Retorna JSON array de tipos de máquina compatíveis com os atributos da área."""
    if not any([flora, inclinacao, limpeza]):
        return None

    tipos: list[str] = []
    emergencia: list[str] = []

    if flora == "mata_fechada":
        return json.dumps(["motosserra", "roçadeira"])

    if inclinacao == "acentuado":
        if limpeza == "densa":
            emergencia.append("roçadeira")
        else:
            tipos.append("roçadeira")
        return json.dumps(tipos + emergencia) if (tipos or emergencia) else None

    if flora == "gramado":
        if inclinacao == "plano" and limpeza == "limpa":
            tipos.append("cortador_grama")
        elif inclinacao == "plano":
            tipos += ["cortador_grama", "roçadeira"]
        else:
            tipos.append("roçadeira")

    if flora == "capim_colonial":
        if inclinacao == "plano" and limpeza == "limpa":
            tipos += ["cortador_grama", "roçadeira"]
        elif limpeza in ("media", "densa"):
            emergencia.append("roçadeira")
        else:
            tipos.append("roçadeira")

    result = tipos + emergencia
    return json.dumps(result) if result else None


def _json_list(value: Any) -> list[dict]:
    if value is None:
        return []
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return [item for item in parsed if isinstance(item, dict)]
        except json.JSONDecodeError:
            return []
    return []


# ── Pydantic models ───────────────────────────────────────────────────────────

class AreaIn(BaseModel):
    nome: str
    descricao: Optional[str] = None
    tipo: str
    area_m2: float
    localizacao_gps: Optional[str] = None
    coords_json: Optional[str] = None
    flora: Optional[str] = None
    inclinacao: Optional[str] = None
    limpeza: Optional[str] = None
    grupo_nome: Optional[str] = None
    visivel: Optional[int] = 1
    cor_hex: Optional[str] = None
    opacidade: Optional[float] = 0.24


class AreaUpdate(BaseModel):
    nome: Optional[str] = None
    descricao: Optional[str] = None
    tipo: Optional[str] = None
    area_m2: Optional[float] = None
    localizacao_gps: Optional[str] = None
    ativa: Optional[int] = None
    coords_json: Optional[str] = None
    flora: Optional[str] = None
    inclinacao: Optional[str] = None
    limpeza: Optional[str] = None
    grupo_nome: Optional[str] = None
    visivel: Optional[int] = None
    cor_hex: Optional[str] = None
    opacidade: Optional[float] = None


class PosicaoUpdate(BaseModel):
    coords_json: str
    area_m2: Optional[float] = None


class MaquinaIn(BaseModel):
    nome: str
    modelo: str
    tipo: str
    numero_serie: Optional[str] = None
    fabricante: Optional[str] = None
    ano_fabricacao: Optional[int] = None
    status: str = "operacional"
    combustivel_tipo: Optional[str] = None
    combustivel_capacidade: Optional[float] = None
    valor_aquisicao: Optional[float] = None
    data_aquisicao: Optional[str] = None
    observacoes: Optional[str] = None


class MaquinaUpdate(BaseModel):
    nome: Optional[str] = None
    modelo: Optional[str] = None
    tipo: Optional[str] = None
    numero_serie: Optional[str] = None
    fabricante: Optional[str] = None
    ano_fabricacao: Optional[int] = None
    status: Optional[str] = None
    combustivel_tipo: Optional[str] = None
    combustivel_capacidade: Optional[float] = None
    combustivel_atual: Optional[float] = None
    horas_uso: Optional[float] = None
    valor_aquisicao: Optional[float] = None
    data_aquisicao: Optional[str] = None
    observacoes: Optional[str] = None


class ManutencaoIn(BaseModel):
    maquina_id: str
    tipo: str = "preventiva"
    pop_id: Optional[str] = None
    usuario_id: Optional[str] = None
    descricao: Optional[str] = None
    data_agendada: str
    custo_estimado: Optional[float] = None


class ManutencaoStatusIn(BaseModel):
    status: str
    horas_utilizadas: Optional[float] = None
    materiais_utilizados: Optional[str] = None
    custo_real: Optional[float] = None
    observacoes: Optional[str] = None


class OperacaoIn(BaseModel):
    maquina_id: str
    area_id: str
    usuario_id: Optional[str] = None
    tipo_servico: str = "corte_grama"
    data_agendada: str
    observacoes: Optional[str] = None


class OperacaoStatusIn(BaseModel):
    status: str
    horas_utilizadas: Optional[float] = None
    combustivel_utilizado: Optional[float] = None
    observacoes: Optional[str] = None


class CombustivelIn(BaseModel):
    maquina_id: str
    tipo: str
    quantidade_adicionada: float
    custo: Optional[float] = None
    usuario_id: Optional[str] = None
    data: Optional[str] = None
    observacoes: Optional[str] = None


class PlanoAreaIn(BaseModel):
    area_id: str
    nome: str
    periodicidade_dias: int
    prioridade: str = "media"
    servicos_json: Any
    materiais_json: Optional[Any] = None
    custo_estimado_ciclo: float = 0
    custo_estimado_mensal: float = 0
    observacoes: Optional[str] = None


class PlanoAreaUpdate(BaseModel):
    nome: Optional[str] = None
    periodicidade_dias: Optional[int] = None
    prioridade: Optional[str] = None
    servicos_json: Optional[Any] = None
    materiais_json: Optional[Any] = None
    custo_estimado_ciclo: Optional[float] = None
    custo_estimado_mensal: Optional[float] = None
    observacoes: Optional[str] = None
    ativo: Optional[int] = None


class PlanoExecIn(BaseModel):
    os_id: Optional[str] = None
    usuario_id: Optional[str] = None
    materiais_json: Optional[Any] = None
    observacoes: Optional[str] = None


class KanbanTarefaIn(BaseModel):
    titulo: str
    descricao: Optional[str] = None
    coluna: str = "backlog"
    prioridade: str = "media"
    usuario_id: Optional[str] = None
    maquina_id: Optional[str] = None
    area_id: Optional[str] = None
    data_vencimento: Optional[str] = None


class KanbanMoverIn(BaseModel):
    coluna: str
    ordem_display: int = 0


class CalendarioEventoIn(BaseModel):
    titulo: str
    descricao: Optional[str] = None
    tipo: str
    data_inicio: str
    data_fim: Optional[str] = None
    local: Optional[str] = None
    maquina_id: Optional[str] = None
    area_id: Optional[str] = None


# ── Áreas ─────────────────────────────────────────────────────────────────────

@router.get("/areas")
async def list_areas(ativa: int = 1):
    return await _get_db().fetch_all(
        "SELECT * FROM grama_areas WHERE ativa=? ORDER BY COALESCE(NULLIF(TRIM(grupo_nome), ''), 'Sem grupo'), nome", (ativa,)
    )


@router.get("/areas/{area_id}")
async def get_area(area_id: str):
    row = await _get_db().fetch_one("SELECT * FROM grama_areas WHERE id=?", (area_id,))
    if not row:
        raise HTTPException(404, "Área não encontrada")
    return row


@router.post("/areas", status_code=201)
async def create_area(body: AreaIn):
    db = _get_db()
    aid = _uid("area")
    compat = _calc_compatibilidade(body.flora, body.inclinacao, body.limpeza)
    await db.execute(
        """INSERT INTO grama_areas
           (id,nome,descricao,tipo,area_m2,localizacao_gps,coords_json,
                        flora,inclinacao,limpeza,maquinas_compativeis,grupo_nome,visivel,cor_hex,opacidade)
                     VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (aid, body.nome, body.descricao, body.tipo, body.area_m2,
         body.localizacao_gps, body.coords_json,
                 body.flora, body.inclinacao, body.limpeza, compat,
                 body.grupo_nome, body.visivel if body.visivel is not None else 1,
                 body.cor_hex, body.opacidade if body.opacidade is not None else 0.24),
    )
    return await _get_db().fetch_one("SELECT * FROM grama_areas WHERE id=?", (aid,))


@router.put("/areas/{area_id}")
async def update_area(area_id: str, body: AreaUpdate):
    db = _get_db()
    existing = await db.fetch_one("SELECT * FROM grama_areas WHERE id=?", (area_id,))
    if not existing:
        raise HTTPException(404, "Área não encontrada")

    updated = {**existing, **{k: v for k, v in body.model_dump().items() if v is not None}}
    veg_alterada = any(k in body.model_fields_set for k in ("flora", "inclinacao", "limpeza"))
    compat = (
        _calc_compatibilidade(updated["flora"], updated["inclinacao"], updated["limpeza"])
        if veg_alterada else existing["maquinas_compativeis"]
    )

    await db.execute(
        """UPDATE grama_areas SET
           nome=?,descricao=?,tipo=?,area_m2=?,localizacao_gps=?,ativa=?,
           coords_json=?,flora=?,inclinacao=?,limpeza=?,maquinas_compativeis=?,grupo_nome=?,visivel=?,cor_hex=?,opacidade=?,
           ultima_atualizacao=CURRENT_TIMESTAMP
           WHERE id=?""",
        (updated["nome"], updated["descricao"], updated["tipo"], updated["area_m2"],
         updated["localizacao_gps"], updated.get("ativa", 1),
         updated["coords_json"], updated["flora"], updated["inclinacao"], updated["limpeza"],
         compat, updated.get("grupo_nome"), updated.get("visivel", existing.get("visivel", 1)),
         updated.get("cor_hex"), updated.get("opacidade", existing.get("opacidade", 0.24)), area_id),
    )
    return await db.fetch_one("SELECT * FROM grama_areas WHERE id=?", (area_id,))


@router.patch("/areas/{area_id}/posicao")
async def update_posicao(area_id: str, body: PosicaoUpdate):
    db = _get_db()
    if not await db.fetch_one("SELECT id FROM grama_areas WHERE id=?", (area_id,)):
        raise HTTPException(404, "Área não encontrada")
    await db.execute(
        "UPDATE grama_areas SET coords_json=?,area_m2=COALESCE(?,area_m2),ultima_atualizacao=CURRENT_TIMESTAMP WHERE id=?",
        (body.coords_json, body.area_m2, area_id),
    )
    return await db.fetch_one("SELECT * FROM grama_areas WHERE id=?", (area_id,))


# ── Planos de Rotina Vegetal ────────────────────────────────────────────────

@router.get("/planos")
async def list_planos(area_id: Optional[str] = None, ativo: int = 1):
    sql = """SELECT p.*, a.nome AS area_nome
             FROM grama_planos_area p
             LEFT JOIN grama_areas a ON a.id = p.area_id
             WHERE p.ativo=?"""
    params: list = [ativo]
    if area_id:
        sql += " AND p.area_id=?"
        params.append(area_id)
    sql += " ORDER BY p.ultima_atualizacao DESC"
    rows = await _get_db().fetch_all(sql, tuple(params))
    for row in rows:
        row["servicos_json"] = _json_list(row.get("servicos_json"))
        row["materiais_json"] = _json_list(row.get("materiais_json"))
    return rows


@router.get("/planos/{plano_id}")
async def get_plano(plano_id: str):
    row = await _get_db().fetch_one(
        """SELECT p.*, a.nome AS area_nome
           FROM grama_planos_area p
           LEFT JOIN grama_areas a ON a.id = p.area_id
           WHERE p.id=?""",
        (plano_id,),
    )
    if not row:
        raise HTTPException(404, "Plano não encontrado")
    row["servicos_json"] = _json_list(row.get("servicos_json"))
    row["materiais_json"] = _json_list(row.get("materiais_json"))
    execs = await _get_db().fetch_all(
        "SELECT * FROM grama_planos_execucoes WHERE plano_id=? ORDER BY data_execucao DESC LIMIT 20",
        (plano_id,),
    )
    for ex in execs:
        ex["materiais_json"] = _json_list(ex.get("materiais_json"))
    row["execucoes"] = execs
    return row


@router.post("/planos", status_code=201)
async def create_plano(body: PlanoAreaIn):
    db = _get_db()
    if body.periodicidade_dias <= 0:
        raise HTTPException(422, "periodicidade_dias deve ser maior que zero")
    area = await db.fetch_one("SELECT id FROM grama_areas WHERE id=?", (body.area_id,))
    if not area:
        raise HTTPException(404, "Área não encontrada")
    pid = _uid("plano")
    await db.execute(
        """INSERT INTO grama_planos_area
           (id,area_id,nome,periodicidade_dias,prioridade,servicos_json,materiais_json,
            custo_estimado_ciclo,custo_estimado_mensal,observacoes)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (
            pid,
            body.area_id,
            body.nome,
            body.periodicidade_dias,
            body.prioridade,
            json.dumps(_json_list(body.servicos_json), ensure_ascii=False),
            json.dumps(_json_list(body.materiais_json), ensure_ascii=False),
            body.custo_estimado_ciclo,
            body.custo_estimado_mensal,
            body.observacoes,
        ),
    )
    return await get_plano(pid)


@router.put("/planos/{plano_id}")
async def update_plano(plano_id: str, body: PlanoAreaUpdate):
    db = _get_db()
    existing = await db.fetch_one("SELECT * FROM grama_planos_area WHERE id=?", (plano_id,))
    if not existing:
        raise HTTPException(404, "Plano não encontrado")

    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        return await get_plano(plano_id)

    merged = {**existing, **updates}
    if int(merged.get("periodicidade_dias") or 0) <= 0:
        raise HTTPException(422, "periodicidade_dias deve ser maior que zero")

    await db.execute(
        """UPDATE grama_planos_area SET
           nome=?,periodicidade_dias=?,prioridade=?,servicos_json=?,materiais_json=?,
           custo_estimado_ciclo=?,custo_estimado_mensal=?,observacoes=?,ativo=?,
           ultima_atualizacao=CURRENT_TIMESTAMP
           WHERE id=?""",
        (
            merged.get("nome"),
            merged.get("periodicidade_dias"),
            merged.get("prioridade"),
            json.dumps(_json_list(merged.get("servicos_json")), ensure_ascii=False),
            json.dumps(_json_list(merged.get("materiais_json")), ensure_ascii=False),
            merged.get("custo_estimado_ciclo") or 0,
            merged.get("custo_estimado_mensal") or 0,
            merged.get("observacoes"),
            merged.get("ativo", 1),
            plano_id,
        ),
    )
    return await get_plano(plano_id)


@router.post("/planos/{plano_id}/executar")
async def executar_plano(plano_id: str, body: PlanoExecIn):
    db = _get_db()
    plano = await db.fetch_one("SELECT * FROM grama_planos_area WHERE id=? AND ativo=1", (plano_id,))
    if not plano:
        raise HTTPException(404, "Plano não encontrado")

    materiais = _json_list(body.materiais_json) if body.materiais_json is not None else _json_list(plano.get("materiais_json"))

    resolvidos: list[dict] = []
    custo_real = 0.0
    for material in materiais:
        qtd = float(material.get("quantidade") or 0)
        if qtd <= 0:
            continue
        item = None
        if material.get("item_id") is not None:
            item = await db.fetch_one(
                "SELECT id, codigo, nome, qtd_atual, preco_unitario FROM estoque WHERE id=? AND ativo=1",
                (material.get("item_id"),),
            )
        elif material.get("codigo"):
            item = await db.fetch_one(
                "SELECT id, codigo, nome, qtd_atual, preco_unitario FROM estoque WHERE codigo=? AND ativo=1",
                (material.get("codigo"),),
            )
        if not item:
            raise HTTPException(404, f"Item de estoque não encontrado para material: {material}")
        if float(item.get("qtd_atual") or 0) < qtd:
            raise HTTPException(400, f"Saldo insuficiente para {item.get('codigo')} ({item.get('nome')})")
        resolvidos.append({"item": item, "quantidade": qtd, "obs": material.get("obs")})

    for entry in resolvidos:
        item = entry["item"]
        qtd = entry["quantidade"]
        await db.execute("UPDATE estoque SET qtd_atual=qtd_atual-? WHERE id=?", (qtd, item["id"]))
        await db.execute(
            """INSERT INTO estoque_movimentos
               (item_id, tipo, quantidade, os_id, usuario_id, obs, documento, fornecedor)
               VALUES (?,?,?,?,?,?,?,?)""",
            (
                item["id"],
                "saida",
                qtd,
                body.os_id,
                body.usuario_id,
                entry.get("obs") or f"Baixa automática plano vegetal {plano_id}",
                "PLANO-VEGETAL",
                "Controle Vegetal",
            ),
        )
        custo_real += qtd * float(item.get("preco_unitario") or 0)

    exec_id = _uid("exec")
    await db.execute(
        """INSERT INTO grama_planos_execucoes
           (id,plano_id,area_id,os_id,usuario_id,materiais_json,custo_real_materiais,observacoes)
           VALUES (?,?,?,?,?,?,?,?)""",
        (
            exec_id,
            plano_id,
            plano.get("area_id"),
            body.os_id,
            body.usuario_id,
            json.dumps([
                {
                    "item_id": entry["item"]["id"],
                    "codigo": entry["item"].get("codigo"),
                    "nome": entry["item"].get("nome"),
                    "quantidade": entry["quantidade"],
                }
                for entry in resolvidos
            ], ensure_ascii=False),
            round(custo_real, 2),
            body.observacoes,
        ),
    )

    return {
        "ok": True,
        "execucao_id": exec_id,
        "plano_id": plano_id,
        "itens_baixados": len(resolvidos),
        "custo_real_materiais": round(custo_real, 2),
    }


# ── Máquinas ──────────────────────────────────────────────────────────────────

@router.get("/maquinas")
async def list_maquinas(status: Optional[str] = None, tipo: Optional[str] = None):
    sql = "SELECT * FROM grama_maquinas WHERE 1=1"
    params: list = []
    if status:
        sql += " AND status=?"; params.append(status)
    if tipo:
        sql += " AND tipo=?"; params.append(tipo)
    sql += " ORDER BY nome"
    return await _get_db().fetch_all(sql, tuple(params))


@router.get("/maquinas/{maq_id}")
async def get_maquina(maq_id: str):
    row = await _get_db().fetch_one("SELECT * FROM grama_maquinas WHERE id=?", (maq_id,))
    if not row:
        raise HTTPException(404, "Máquina não encontrada")
    return row


@router.post("/maquinas", status_code=201)
async def create_maquina(body: MaquinaIn):
    db = _get_db()
    mid = _uid("maq")
    await db.execute(
        """INSERT INTO grama_maquinas
           (id,nome,modelo,tipo,numero_serie,fabricante,ano_fabricacao,status,
            combustivel_tipo,combustivel_capacidade,combustivel_atual,valor_aquisicao,data_aquisicao,observacoes)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (mid, body.nome, body.modelo, body.tipo, body.numero_serie, body.fabricante,
         body.ano_fabricacao, body.status, body.combustivel_tipo, body.combustivel_capacidade,
         body.combustivel_capacidade or 0, body.valor_aquisicao, body.data_aquisicao, body.observacoes),
    )
    return await db.fetch_one("SELECT * FROM grama_maquinas WHERE id=?", (mid,))


@router.put("/maquinas/{maq_id}")
async def update_maquina(maq_id: str, body: MaquinaUpdate):
    db = _get_db()
    existing = await db.fetch_one("SELECT * FROM grama_maquinas WHERE id=?", (maq_id,))
    if not existing:
        raise HTTPException(404, "Máquina não encontrada")
    u = {**existing, **{k: v for k, v in body.model_dump().items() if v is not None}}
    await db.execute(
        """UPDATE grama_maquinas SET
           nome=?,modelo=?,tipo=?,numero_serie=?,fabricante=?,ano_fabricacao=?,status=?,
           combustivel_tipo=?,combustivel_capacidade=?,combustivel_atual=?,horas_uso=?,
           valor_aquisicao=?,data_aquisicao=?,observacoes=?,ultima_atualizacao=CURRENT_TIMESTAMP
           WHERE id=?""",
        (u["nome"], u["modelo"], u["tipo"], u["numero_serie"], u["fabricante"], u["ano_fabricacao"],
         u["status"], u["combustivel_tipo"], u["combustivel_capacidade"], u["combustivel_atual"],
         u["horas_uso"], u["valor_aquisicao"], u["data_aquisicao"], u["observacoes"], maq_id),
    )
    return await db.fetch_one("SELECT * FROM grama_maquinas WHERE id=?", (maq_id,))


@router.delete("/maquinas/{maq_id}")
async def delete_maquina(maq_id: str):
    await _get_db().execute(
        "UPDATE grama_maquinas SET status='inativo',ultima_atualizacao=CURRENT_TIMESTAMP WHERE id=?",
        (maq_id,),
    )
    return {"ok": True}


# ── Manutenção ────────────────────────────────────────────────────────────────

@router.get("/manutencao/pops")
async def list_pops():
    return await _get_db().fetch_all("SELECT * FROM grama_manutencoes_pop ORDER BY nome")


@router.get("/manutencao/alertas")
async def alertas_manutencao():
    hoje = date.today().isoformat()
    return await _get_db().fetch_all(
        """SELECT om.*,m.nome AS maquina_nome
           FROM grama_operacoes_manutencao om
           JOIN grama_maquinas m ON m.id=om.maquina_id
           WHERE om.data_agendada < ? AND om.status NOT IN ('concluida','cancelada')
           ORDER BY om.data_agendada""",
        (hoje,),
    )


@router.get("/manutencao")
async def list_manutencao(status: Optional[str] = None, maquina_id: Optional[str] = None):
    sql = """SELECT om.*,m.nome AS maquina_nome
             FROM grama_operacoes_manutencao om
             LEFT JOIN grama_maquinas m ON m.id=om.maquina_id WHERE 1=1"""
    params: list = []
    if status:
        sql += " AND om.status=?"; params.append(status)
    if maquina_id:
        sql += " AND om.maquina_id=?"; params.append(maquina_id)
    sql += " ORDER BY om.data_agendada"
    return await _get_db().fetch_all(sql, tuple(params))


@router.post("/manutencao", status_code=201)
async def create_manutencao(body: ManutencaoIn):
    db = _get_db()
    mid = _uid("man")
    await db.execute(
        """INSERT INTO grama_operacoes_manutencao
           (id,maquina_id,tipo,pop_id,usuario_id,descricao,data_agendada,custo_estimado)
           VALUES (?,?,?,?,?,?,?,?)""",
        (mid, body.maquina_id, body.tipo, body.pop_id, body.usuario_id,
         body.descricao, body.data_agendada, body.custo_estimado),
    )
    return await db.fetch_one("SELECT * FROM grama_operacoes_manutencao WHERE id=?", (mid,))


@router.put("/manutencao/{man_id}/status")
async def update_manutencao_status(man_id: str, body: ManutencaoStatusIn):
    db = _get_db()
    from datetime import datetime
    now = datetime.utcnow().isoformat()
    extra_col = ""
    extra_val: list = []
    if body.status == "em_progresso":
        extra_col = ",data_inicio=?"; extra_val = [now]
    elif body.status == "concluida":
        extra_col = ",data_conclusao=?"; extra_val = [now]
    await db.execute(
        f"""UPDATE grama_operacoes_manutencao
            SET status=?,horas_utilizadas=?,materiais_utilizados=?,custo_real=?,observacoes=?{extra_col}
            WHERE id=?""",
        (body.status, body.horas_utilizadas, body.materiais_utilizados,
         body.custo_real, body.observacoes, *extra_val, man_id),
    )
    return await db.fetch_one("SELECT * FROM grama_operacoes_manutencao WHERE id=?", (man_id,))


# ── Operações de serviço ──────────────────────────────────────────────────────

@router.get("/operacoes")
async def list_operacoes(
    status: Optional[str] = None,
    maquina_id: Optional[str] = None,
    area_id: Optional[str] = None,
):
    sql = """SELECT os.*,m.nome AS maquina_nome,a.nome AS area_nome
             FROM grama_operacoes_servico os
             LEFT JOIN grama_maquinas m ON m.id=os.maquina_id
             LEFT JOIN grama_areas a ON a.id=os.area_id WHERE 1=1"""
    params: list = []
    if status:
        sql += " AND os.status=?"; params.append(status)
    if maquina_id:
        sql += " AND os.maquina_id=?"; params.append(maquina_id)
    if area_id:
        sql += " AND os.area_id=?"; params.append(area_id)
    sql += " ORDER BY os.data_agendada DESC"
    return await _get_db().fetch_all(sql, tuple(params))


@router.get("/operacoes/{op_id}")
async def get_operacao(op_id: str):
    row = await _get_db().fetch_one(
        """SELECT os.*,m.nome AS maquina_nome,a.nome AS area_nome
           FROM grama_operacoes_servico os
           LEFT JOIN grama_maquinas m ON m.id=os.maquina_id
           LEFT JOIN grama_areas a ON a.id=os.area_id WHERE os.id=?""",
        (op_id,),
    )
    if not row:
        raise HTTPException(404, "Operação não encontrada")
    return row


@router.post("/operacoes", status_code=201)
async def create_operacao(body: OperacaoIn):
    db = _get_db()
    oid = _uid("op")
    await db.execute(
        """INSERT INTO grama_operacoes_servico
           (id,maquina_id,area_id,usuario_id,tipo_servico,data_agendada,observacoes)
           VALUES (?,?,?,?,?,?,?)""",
        (oid, body.maquina_id, body.area_id, body.usuario_id,
         body.tipo_servico, body.data_agendada, body.observacoes),
    )
    return await db.fetch_one("SELECT * FROM grama_operacoes_servico WHERE id=?", (oid,))


@router.put("/operacoes/{op_id}/status")
async def update_operacao_status(op_id: str, body: OperacaoStatusIn):
    db = _get_db()
    from datetime import datetime
    now = datetime.utcnow().isoformat()
    extra_col = ""
    extra_val: list = []
    if body.status == "em_progresso":
        extra_col = ",data_inicio=?"; extra_val = [now]
    elif body.status == "concluido":
        extra_col = ",data_conclusao=?"; extra_val = [now]
    await db.execute(
        f"""UPDATE grama_operacoes_servico
            SET status=?,horas_utilizadas=?,combustivel_utilizado=?,observacoes=?{extra_col}
            WHERE id=?""",
        (body.status, body.horas_utilizadas, body.combustivel_utilizado,
         body.observacoes, *extra_val, op_id),
    )
    if body.status == "concluido" and body.horas_utilizadas:
        await db.execute(
            """UPDATE grama_maquinas
               SET horas_uso=horas_uso+?,
                   combustivel_atual=MAX(0,combustivel_atual-?)
               WHERE id=(SELECT maquina_id FROM grama_operacoes_servico WHERE id=?)""",
            (body.horas_utilizadas, body.combustivel_utilizado or 0, op_id),
        )
    return await db.fetch_one("SELECT * FROM grama_operacoes_servico WHERE id=?", (op_id,))


# ── Combustível ──────────────────────────────────────────────────────────────

@router.get("/combustivel")
async def list_combustivel(
    maquina_id: Optional[str] = None,
    inicio: Optional[str] = None,
    fim: Optional[str] = None,
):
    sql = """SELECT cl.*, m.nome AS maquina_nome
             FROM grama_combustivel_log cl
             LEFT JOIN grama_maquinas m ON m.id = cl.maquina_id
             WHERE 1=1"""
    params: list = []
    if maquina_id:
        sql += " AND cl.maquina_id=?"
        params.append(maquina_id)
    if inicio:
        sql += " AND date(cl.data) >= date(?)"
        params.append(inicio)
    if fim:
        sql += " AND date(cl.data) <= date(?)"
        params.append(fim)
    sql += " ORDER BY cl.data DESC, cl.id DESC"
    return await _get_db().fetch_all(sql, tuple(params))


@router.get("/combustivel/{log_id}")
async def get_combustivel(log_id: str):
    row = await _get_db().fetch_one(
        """SELECT cl.*, m.nome AS maquina_nome
           FROM grama_combustivel_log cl
           LEFT JOIN grama_maquinas m ON m.id = cl.maquina_id
           WHERE cl.id=?""",
        (log_id,),
    )
    if not row:
        raise HTTPException(404, "Abastecimento não encontrado")
    return row


@router.post("/combustivel", status_code=201)
async def create_combustivel(body: CombustivelIn):
    db = _get_db()
    maq = await db.fetch_one(
        "SELECT id, combustivel_capacidade, combustivel_atual FROM grama_maquinas WHERE id=?",
        (body.maquina_id,),
    )
    if not maq:
        raise HTTPException(404, "Máquina não encontrada")
    if body.quantidade_adicionada <= 0:
        raise HTTPException(422, "quantidade_adicionada deve ser maior que zero")

    cid = _uid("comb")
    data_log = body.data or date.today().isoformat()
    await db.execute(
        """INSERT INTO grama_combustivel_log
           (id, maquina_id, data, tipo, quantidade_adicionada, custo, usuario_id, observacoes)
           VALUES (?,?,?,?,?,?,?,?)""",
        (
            cid,
            body.maquina_id,
            data_log,
            body.tipo,
            body.quantidade_adicionada,
            body.custo,
            body.usuario_id,
            body.observacoes,
        ),
    )

    capacidade = maq.get("combustivel_capacidade") or 0
    atual = maq.get("combustivel_atual") or 0
    novo_nivel = atual + body.quantidade_adicionada
    if capacidade > 0:
        novo_nivel = min(capacidade, novo_nivel)
    await db.execute(
        "UPDATE grama_maquinas SET combustivel_atual=?, ultima_atualizacao=CURRENT_TIMESTAMP WHERE id=?",
        (novo_nivel, body.maquina_id),
    )
    return await get_combustivel(cid)


# ── Kanban ────────────────────────────────────────────────────────────────────

@router.get("/kanban")
async def get_kanban():
    db = _get_db()
    colunas = ["backlog", "agendado", "em_progresso", "concluido", "bloqueado"]
    result = {}
    for col in colunas:
        result[col] = await db.fetch_all(
            """SELECT kt.*,m.nome AS maquina_nome,a.nome AS area_nome
               FROM grama_kanban_tarefas kt
               LEFT JOIN grama_maquinas m ON m.id=kt.maquina_id
               LEFT JOIN grama_areas a ON a.id=kt.area_id
               WHERE kt.coluna=? ORDER BY kt.ordem_display,kt.data_criacao""",
            (col,),
        )
    return result


@router.post("/kanban", status_code=201)
async def create_kanban_tarefa(body: KanbanTarefaIn):
    db = _get_db()
    kid = _uid("kt")
    await db.execute(
        """INSERT INTO grama_kanban_tarefas
           (id,titulo,descricao,coluna,prioridade,usuario_id,maquina_id,area_id,data_vencimento)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (kid, body.titulo, body.descricao, body.coluna, body.prioridade,
         body.usuario_id, body.maquina_id, body.area_id, body.data_vencimento),
    )
    return await db.fetch_one("SELECT * FROM grama_kanban_tarefas WHERE id=?", (kid,))


@router.put("/kanban/{tarefa_id}/mover")
async def mover_kanban(tarefa_id: str, body: KanbanMoverIn):
    db = _get_db()
    await db.execute(
        "UPDATE grama_kanban_tarefas SET coluna=?,ordem_display=? WHERE id=?",
        (body.coluna, body.ordem_display, tarefa_id),
    )
    return await db.fetch_one("SELECT * FROM grama_kanban_tarefas WHERE id=?", (tarefa_id,))


@router.delete("/kanban/{tarefa_id}")
async def delete_kanban_tarefa(tarefa_id: str):
    await _get_db().execute("DELETE FROM grama_kanban_tarefas WHERE id=?", (tarefa_id,))
    return {"ok": True}


# ── Calendário ────────────────────────────────────────────────────────────────

@router.get("/calendario")
async def list_calendario(
    inicio: Optional[str] = None,
    fim: Optional[str] = None,
    tipo: Optional[str] = None,
):
    sql = """SELECT ce.*,m.nome AS maquina_nome,a.nome AS area_nome
             FROM grama_calendario_eventos ce
             LEFT JOIN grama_maquinas m ON m.id=ce.maquina_id
             LEFT JOIN grama_areas a ON a.id=ce.area_id WHERE 1=1"""
    params: list = []
    if inicio:
        sql += " AND ce.data_inicio >= ?"; params.append(inicio)
    if fim:
        sql += " AND ce.data_inicio <= ?"; params.append(fim)
    if tipo:
        sql += " AND ce.tipo=?"; params.append(tipo)
    sql += " ORDER BY ce.data_inicio"
    return await _get_db().fetch_all(sql, tuple(params))


@router.post("/calendario", status_code=201)
async def create_evento(body: CalendarioEventoIn):
    db = _get_db()
    eid = _uid("ev")
    await db.execute(
        """INSERT INTO grama_calendario_eventos
           (id,titulo,descricao,tipo,data_inicio,data_fim,local,maquina_id,area_id)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (eid, body.titulo, body.descricao, body.tipo, body.data_inicio,
         body.data_fim, body.local, body.maquina_id, body.area_id),
    )
    return await db.fetch_one("SELECT * FROM grama_calendario_eventos WHERE id=?", (eid,))


# ── Relatórios ────────────────────────────────────────────────────────────────

@router.get("/relatorios/resumo")
async def relatorio_resumo():
    db = _get_db()
    maq_op  = await db.fetch_one("SELECT COUNT(*) AS n FROM grama_maquinas WHERE status='operacional'")
    maq_man = await db.fetch_one("SELECT COUNT(*) AS n FROM grama_maquinas WHERE status='em_manutencao'")
    ops_mes = await db.fetch_one(
        "SELECT COUNT(*) AS n FROM grama_operacoes_servico WHERE strftime('%Y-%m',data_agendada)=strftime('%Y-%m','now')"
    )
    man_venc = await db.fetch_one(
        "SELECT COUNT(*) AS n FROM grama_operacoes_manutencao WHERE data_agendada<date('now') AND status NOT IN ('concluida','cancelada')"
    )
    areas = await db.fetch_one(
        "SELECT COUNT(*) AS n, SUM(area_m2) AS total_m2 FROM grama_areas WHERE ativa=1"
    )
    return {
        "maquinas_operacionais": maq_op["n"],
        "em_manutencao": maq_man["n"],
        "operacoes_mes": ops_mes["n"],
        "manutencoes_vencidas": man_venc["n"],
        "areas": areas["n"],
        "area_total_m2": areas["total_m2"],
    }


@router.get("/relatorios/combustivel")
async def relatorio_combustivel():
    return await _get_db().fetch_all(
        """SELECT m.nome,SUM(cl.quantidade_adicionada) AS total_abastecido,SUM(cl.custo) AS custo_total
           FROM grama_combustivel_log cl JOIN grama_maquinas m ON m.id=cl.maquina_id
           GROUP BY cl.maquina_id ORDER BY total_abastecido DESC"""
    )
