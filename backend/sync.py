"""
Endpoints de sincronização PMOC ↔ núcleo.

Contrato em MODULOS_EXTERNOS.md §3. Schema em data/schema_catalogo.sql.
Processamento de eventos: side-effects documentados em MODULOS_EXTERNOS.md §3.4.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from typing import Any, Awaitable, Callable

import aiosqlite
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/sync", tags=["sync"])


def _db():
    """Resolve `db` dinamicamente: re-imports de testes ficam corretos."""
    return sys.modules["backend.main"].db


# Tipos canônicos (MODULOS_EXTERNOS.md §3.4) — também são as chaves de HANDLERS.
TIPOS_VALIDOS = {
    "ps_criada",
    "os_criada",
    "os_status",
    "os_executada",
    "uso_atual_inc",
    "estoque_mov",
    "documento_anexo",
    "inspecao_concluida",
    "plano_adiado",
    "qualificacao_uso",
}


class EventoIn(BaseModel):
    id: str = Field(..., min_length=1)
    tipo: str
    ts: str
    payload: dict[str, Any] = {}


class PushIn(BaseModel):
    modulo: str
    device_id: str
    eventos: list[EventoIn]


async def _modulo_existe(nome: str) -> bool:
    row = await _db().fetch_one(
        "SELECT 1 FROM modulos_registrados WHERE nome=? AND ativo=1", (nome,)
    )
    return row is not None


# ───────────────────────── Handlers de eventos ─────────────────────────
#
# Cada handler recebe a conexão aiosqlite aberta + o payload do evento e
# retorna `None` quando o efeito foi aplicado, ou uma string com o motivo
# da rejeição.
#
# Convenções:
#   - Handlers só aplicam o efeito; o INSERT em sync_eventos é feito pelo loop
#     externo, com `status` decidido pelo retorno.
#   - Eventos sem efeito colateral além da auditoria (`plano_adiado`,
#     `qualificacao_uso`) têm handler que retorna None imediatamente.

EventHandler = Callable[[aiosqlite.Connection, dict[str, Any]], Awaitable[str | None]]


async def _h_uso_atual_inc(conn: aiosqlite.Connection, payload: dict) -> str | None:
    ativo_id = payload.get("ativo_id")
    delta = payload.get("delta")
    if not ativo_id:
        return "payload exige 'ativo_id'"
    if not isinstance(delta, (int, float)):
        return "payload exige 'delta' numérico"
    if delta < 0:
        return f"delta inválido (negativo): {delta}"
    async with conn.execute("SELECT ativo FROM ativos WHERE id=?", (ativo_id,)) as cur:
        row = await cur.fetchone()
    if row is None:
        return f"ativo desconhecido: {ativo_id}"
    if row[0] != 1:
        return f"ativo arquivado: {ativo_id}"
    await conn.execute(
        "UPDATE ativos SET uso_atual = COALESCE(uso_atual, 0) + ? WHERE id=?",
        (delta, ativo_id),
    )
    return None


async def _h_estoque_mov(conn: aiosqlite.Connection, payload: dict) -> str | None:
    item_id = payload.get("item_id")
    tipo = payload.get("tipo")
    qtd = payload.get("quantidade")
    if not isinstance(item_id, int):
        return "payload exige 'item_id' inteiro"
    if tipo not in ("entrada", "saida", "ajuste"):
        return f"tipo de movimento inválido: {tipo!r} (use entrada|saida|ajuste)"
    if not isinstance(qtd, (int, float)) or qtd < 0:
        return f"quantidade inválida: {qtd}"
    async with conn.execute(
        "SELECT qtd_atual, ativo FROM estoque WHERE id=?", (item_id,)
    ) as cur:
        row = await cur.fetchone()
    if row is None:
        return f"item de estoque desconhecido: {item_id}"
    if row[1] != 1:
        return f"item de estoque arquivado: {item_id}"
    atual = row[0] or 0
    if tipo == "entrada":
        nova = atual + qtd
    elif tipo == "saida":
        nova = atual - qtd
        if nova < 0:
            return f"saída produziria saldo negativo (atual={atual}, saída={qtd})"
    else:  # ajuste
        nova = qtd
    await conn.execute(
        "INSERT INTO estoque_movimentos (item_id, tipo, quantidade, os_id, usuario_id, obs) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (item_id, tipo, qtd, payload.get("os_id"), payload.get("usuario_id"),
         payload.get("obs")),
    )
    await conn.execute("UPDATE estoque SET qtd_atual=? WHERE id=?", (nova, item_id))
    return None


async def _h_documento_anexo(conn: aiosqlite.Connection, payload: dict) -> str | None:
    doc_id = payload.get("id") or _new_uuid()
    nome = payload.get("nome")
    if not nome:
        return "payload exige 'nome'"
    await conn.execute(
        "INSERT INTO documentos (id, nome, tipo, mime, tamanho_bytes, sha256, "
        "storage_path, conteudo_inline, vinculo_tipo, vinculo_id, criado_por) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (doc_id, nome, payload.get("tipo"), payload.get("mime"),
         payload.get("tamanho_bytes"), payload.get("sha256"),
         payload.get("storage_path"), payload.get("conteudo_inline"),
         payload.get("vinculo_tipo"), payload.get("vinculo_id"),
         payload.get("criado_por")),
    )
    return None


# Status canônicos do ciclo OS (Rules.md §4)
OS_STATUS_VALIDOS = {
    "aberta", "autorizada", "iniciada", "em_execucao",
    "espera", "pronto", "concluida", "cancelada",
    # Legados ainda em uso no ERP — aceitar até consolidação
    "em_andamento", "aguardando",
}


async def _inserir_os(
    conn: aiosqlite.Connection, payload: dict, modulo: str,
    default_status: str = "aberta", default_tipo: str = "corretiva",
    exigir_servico: bool = False,
) -> str | None:
    """Insere OS/PS em `ordens_servico`. Retorna motivo de rejeição ou None."""
    os_id = payload.get("id") or _new_uuid()
    titulo = payload.get("titulo")
    if not titulo:
        return "payload exige 'titulo'"
    ativo_id = payload.get("ativo_id")
    if ativo_id:
        async with conn.execute("SELECT 1 FROM ativos WHERE id=?", (ativo_id,)) as cur:
            if not await cur.fetchone():
                return f"ativo desconhecido: {ativo_id}"
    servico_id = payload.get("servico_id")
    snapshot = payload.get("servico_snapshot")
    if exigir_servico and not servico_id and not snapshot:
        return "ps_criada exige 'servico_id' (central) ou 'servico_snapshot' (local)"
    codigo = payload.get("codigo") or f"OS-{os_id[:8]}"
    tipo = payload.get("tipo", default_tipo)
    prioridade = payload.get("prioridade", "media")
    status = payload.get("status", default_status)
    if status not in OS_STATUS_VALIDOS:
        return f"status inválido: {status}"
    snapshot_json = json.dumps(snapshot) if snapshot is not None else None
    def _list_json(key):
        v = payload.get(key)
        if v is None:
            return None
        return v if isinstance(v, str) else json.dumps(v)
    servicos_json = _list_json("servicos")
    veiculos_json = _list_json("veiculos")
    await conn.execute(
        "INSERT INTO ordens_servico (id, codigo, titulo, descricao, tipo, status, "
        "prioridade, categoria, subcategoria, servicos, veiculos, modulo_origem, solicitante_id, responsavel_id, local_id, ativo_id, "
        "servico_id, servico_versao_snapshot, servico_snapshot, "
        "data_prevista, observacoes) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (os_id, codigo, titulo, payload.get("descricao"), tipo, status, prioridade,
         payload.get("categoria"), payload.get("subcategoria"), servicos_json, veiculos_json,
         modulo, payload.get("solicitante_id"), payload.get("responsavel_id"),
         payload.get("local_id"), ativo_id,
         servico_id, payload.get("servico_versao_snapshot"), snapshot_json,
         payload.get("data_prevista"), payload.get("observacoes")),
    )
    await conn.execute(
        "INSERT INTO os_historico (os_id, status_de, status_para, obs, usuario_id) "
        "VALUES (?, NULL, ?, ?, ?)",
        (os_id, status, payload.get("obs"), payload.get("solicitante_id")),
    )
    return None


async def _h_os_criada(conn: aiosqlite.Connection, payload: dict, modulo: str) -> str | None:
    return await _inserir_os(conn, payload, modulo)


async def _h_ps_criada(conn: aiosqlite.Connection, payload: dict, modulo: str) -> str | None:
    return await _inserir_os(conn, payload, modulo,
                             default_status="aberta",
                             default_tipo="preventiva",
                             exigir_servico=True)


async def _h_os_executada(conn: aiosqlite.Connection, payload: dict) -> str | None:
    os_id = payload.get("os_id")
    if not os_id:
        return "payload exige 'os_id'"
    async with conn.execute(
        "SELECT status, tipo FROM ordens_servico WHERE id=?", (os_id,)
    ) as cur:
        row = await cur.fetchone()
    if row is None:
        return f"OS desconhecida: {os_id}"
    status_atual = row[0]

    materiais = payload.get("materiais_usados", [])
    if not isinstance(materiais, list):
        return "'materiais_usados' deve ser lista"

    novo_status = payload.get("status_para", "pronto")
    if novo_status not in OS_STATUS_VALIDOS:
        return f"status_para inválido: {novo_status}"

    # Pré-validação atômica: saldos suficientes antes de qualquer mutação.
    # Agrega por item_id para detectar dois consumos do mesmo material no mesmo evento.
    consumo_total: dict[Any, float] = {}
    for mat in materiais:
        if not isinstance(mat, dict) or "item_id" not in mat or "qtd" not in mat:
            return "cada material exige 'item_id' e 'qtd'"
        consumo_total[mat["item_id"]] = consumo_total.get(mat["item_id"], 0) + mat["qtd"]
    for item_id, total in consumo_total.items():
        async with conn.execute(
            "SELECT qtd_atual FROM estoque WHERE id=? AND ativo=1", (item_id,)
        ) as cur:
            irow = await cur.fetchone()
        if irow is None:
            return f"item de estoque desconhecido: {item_id}"
        if (irow[0] or 0) - total < 0:
            return f"saída produziria saldo negativo no item {item_id}"

    # Aplica baixas
    for mat in materiais:
        await conn.execute(
            "INSERT INTO estoque_movimentos (item_id, tipo, quantidade, os_id, usuario_id, obs) "
            "VALUES (?, 'saida', ?, ?, ?, ?)",
            (mat["item_id"], mat["qtd"], os_id, payload.get("usuario_id"),
             mat.get("obs") or "consumo OS"),
        )
        await conn.execute(
            "UPDATE estoque SET qtd_atual = qtd_atual - ? WHERE id=?",
            (mat["qtd"], mat["item_id"]),
        )

    await conn.execute(
        "UPDATE ordens_servico SET status=?, hora_inicio=?, hora_fim=?, "
        "observacoes=COALESCE(?, observacoes), atualizado_em=CURRENT_TIMESTAMP "
        "WHERE id=?",
        (novo_status, payload.get("hora_inicio"), payload.get("hora_fim"),
         payload.get("observacoes"), os_id),
    )
    await conn.execute(
        "INSERT INTO os_historico (os_id, status_de, status_para, obs, usuario_id) "
        "VALUES (?, ?, ?, ?, ?)",
        (os_id, status_atual, novo_status,
         f"executada: {payload.get('observacoes','')}".strip(),
         payload.get("usuario_id")),
    )
    return None


async def _h_inspecao_concluida(conn: aiosqlite.Connection, payload: dict) -> str | None:
    os_id = payload.get("os_id")
    if not os_id:
        return "payload exige 'os_id'"
    async with conn.execute(
        "SELECT status, tipo FROM ordens_servico WHERE id=?", (os_id,)
    ) as cur:
        row = await cur.fetchone()
    if row is None:
        return f"OS desconhecida: {os_id}"
    if row[1] != "inspecao":
        return f"inspecao_concluida só aceita OS tipo=inspecao (recebido: {row[1]!r})"
    anterior = row[0]
    await conn.execute(
        "UPDATE ordens_servico SET status='concluida', "
        "data_conclusao=date('now'), observacoes=COALESCE(?, observacoes), "
        "atualizado_em=CURRENT_TIMESTAMP WHERE id=?",
        (payload.get("observacoes"), os_id),
    )
    await conn.execute(
        "INSERT INTO os_historico (os_id, status_de, status_para, obs, usuario_id) "
        "VALUES (?, ?, 'concluida', ?, ?)",
        (os_id, anterior, payload.get("observacoes"), payload.get("usuario_id")),
    )
    return None


async def _h_os_status(conn: aiosqlite.Connection, payload: dict) -> str | None:
    os_id = payload.get("os_id")
    novo = payload.get("status_para")
    if not os_id:
        return "payload exige 'os_id'"
    if novo not in OS_STATUS_VALIDOS:
        return f"status_para inválido: {novo}"
    async with conn.execute(
        "SELECT status FROM ordens_servico WHERE id=?", (os_id,)
    ) as cur:
        row = await cur.fetchone()
    if row is None:
        return f"OS desconhecida: {os_id}"
    anterior = row[0]
    await conn.execute(
        "UPDATE ordens_servico SET status=?, atualizado_em=CURRENT_TIMESTAMP WHERE id=?",
        (novo, os_id),
    )
    await conn.execute(
        "INSERT INTO os_historico (os_id, status_de, status_para, obs, usuario_id) "
        "VALUES (?, ?, ?, ?, ?)",
        (os_id, anterior, novo, payload.get("obs"), payload.get("usuario_id")),
    )
    return None


async def _h_auditoria(conn: aiosqlite.Connection, payload: dict) -> str | None:
    """Eventos puramente auditáveis: o registro em sync_eventos basta."""
    return None


def _new_uuid() -> str:
    import uuid as _uuid
    return str(_uuid.uuid4())


# Handlers que precisam do nome do módulo recebem-no via wrapper no push loop.
HANDLERS: dict[str, EventHandler] = {
    "uso_atual_inc": _h_uso_atual_inc,
    "estoque_mov": _h_estoque_mov,
    "documento_anexo": _h_documento_anexo,
    "os_status": _h_os_status,
    "os_executada": _h_os_executada,
    "inspecao_concluida": _h_inspecao_concluida,
    "plano_adiado": _h_auditoria,
    "qualificacao_uso": _h_auditoria,
    # `os_criada` e `ps_criada` são tratados fora de HANDLERS (precisam do modulo)
}


# ───────────────────────────── Endpoints ─────────────────────────────


@router.get("/cursor")
async def get_cursor(
    modulo: str = Query(..., min_length=1),
    device: str = Query(..., min_length=1),
):
    if not await _modulo_existe(modulo):
        raise HTTPException(status_code=404, detail=f"Módulo desconhecido: {modulo}")
    row = await _db().fetch_one(
        "SELECT ultimo_evento_id, ultimo_push_em, ultimo_pull_em "
        "FROM sync_cursor WHERE modulo=? AND device_id=?",
        (modulo, device),
    )
    return {
        "modulo": modulo,
        "device_id": device,
        "ultimo_evento_id": row["ultimo_evento_id"] if row else None,
        "ultimo_push_em": row["ultimo_push_em"] if row else None,
        "ultimo_pull_em": row["ultimo_pull_em"] if row else None,
    }


@router.post("/push")
async def push(body: PushIn):
    if not await _modulo_existe(body.modulo):
        raise HTTPException(status_code=404, detail=f"Módulo desconhecido: {body.modulo}")

    aceitos: list[str] = []
    rejeitados: list[dict[str, str]] = []
    agora = datetime.utcnow().isoformat(timespec="seconds")
    ultimo_evento_id: str | None = None

    async with aiosqlite.connect(_db().db_path) as conn:
        for ev in body.eventos:
            if ev.tipo not in TIPOS_VALIDOS:
                rejeitados.append({"id": ev.id, "motivo": f"tipo desconhecido: {ev.tipo}"})
                continue

            # Idempotência: evento já visto retorna em aceitos sem reprocessar
            async with conn.execute(
                "SELECT 1 FROM sync_eventos WHERE id=?", (ev.id,)
            ) as cur:
                if await cur.fetchone():
                    aceitos.append(ev.id)
                    ultimo_evento_id = ev.id
                    continue

            motivo: str | None = None
            try:
                if ev.tipo == "os_criada":
                    motivo = await _h_os_criada(conn, ev.payload, body.modulo)
                elif ev.tipo == "ps_criada":
                    motivo = await _h_ps_criada(conn, ev.payload, body.modulo)
                else:
                    handler = HANDLERS.get(ev.tipo)
                    if handler is not None:
                        motivo = await handler(conn, ev.payload)
                    # Tipos sem handler: aceitos como auditoria (a evoluir)
            except Exception as e:  # pragma: no cover — falha inesperada
                motivo = f"erro interno: {type(e).__name__}: {e}"

            status = "rejeitado" if motivo else "processado"
            await conn.execute(
                "INSERT INTO sync_eventos (id, modulo, device_id, tipo, payload, "
                "ts_origem, status, motivo_rejeicao, processado_em) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (ev.id, body.modulo, body.device_id, ev.tipo,
                 json.dumps(ev.payload), ev.ts, status, motivo, agora),
            )
            if motivo:
                rejeitados.append({"id": ev.id, "motivo": motivo})
            else:
                aceitos.append(ev.id)
                ultimo_evento_id = ev.id

        if ultimo_evento_id is not None:
            await conn.execute(
                "INSERT INTO sync_cursor (modulo, device_id, ultimo_evento_id, ultimo_push_em, atualizado_em) "
                "VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(modulo, device_id) DO UPDATE SET "
                "ultimo_evento_id=excluded.ultimo_evento_id, "
                "ultimo_push_em=excluded.ultimo_push_em, "
                "atualizado_em=excluded.atualizado_em",
                (body.modulo, body.device_id, ultimo_evento_id, agora, agora),
            )
        await conn.commit()

    return {"aceitos": aceitos, "rejeitados": rejeitados, "cursor": agora}


@router.get("/manifest")
async def manifest(
    modulo: str = Query(..., min_length=1),
    since: str | None = Query(default=None),
):
    if not await _modulo_existe(modulo):
        raise HTTPException(status_code=404, detail=f"Módulo desconhecido: {modulo}")

    db = _db()
    mod = await db.fetch_one(
        "SELECT categorias_atend FROM modulos_registrados WHERE nome=?", (modulo,)
    )
    try:
        categorias: list[str] = json.loads(mod["categorias_atend"] or "[]")
    except (ValueError, TypeError):
        categorias = []
    cat_ph = ",".join("?" for _ in categorias) if categorias else ""

    ativos: list[dict] = []
    if categorias:
        ativos = await db.fetch_all(
            f"SELECT * FROM ativos WHERE ativo=1 AND categoria IN ({cat_ph})",
            tuple(categorias),
        )

    usuarios = await db.fetch_all(
        "SELECT id, nome, posto, mat, tipo, role FROM usuarios WHERE ativo=1"
    )

    locais = await db.fetch_all(
        "SELECT id, codigo, nome, tipo, area, estrutura_id FROM locais WHERE ativo=1"
    )

    estoque_catalogo = await db.fetch_all(
        "SELECT id, codigo, nome, categoria, unidade, qtd_minima FROM estoque WHERE ativo=1"
    )

    todos_servicos = await db.fetch_all(
        "SELECT * FROM catalogo_servicos WHERE escopo='central' AND ativo=1"
    )
    catalogo_servicos = []
    for s in todos_servicos:
        try:
            aplic = json.loads(s.get("aplicavel_a") or "{}")
        except (ValueError, TypeError):
            aplic = {}
        cats_serv = set(aplic.get("categorias") or [])
        if not cats_serv or cats_serv & set(categorias):
            s["aplicavel_a"] = aplic
            catalogo_servicos.append(s)

    # planos_manutencao APOSENTADO — derivado de catalogo_planos + itens.
    # Mantém a chave/shape ({tipo_codigo, intervalo, servico_id}) que o app PMOC já consome.
    planos: list[dict] = []
    srv_ids = {s["id"] for s in catalogo_servicos}
    cat_planos = await db.fetch_all(
        "SELECT id, categoria, tipo_codigo, aplicavel_tipos, frequencia FROM catalogo_planos WHERE ativo = 1"
    )
    for p in cat_planos:
        if categorias and p["categoria"] not in categorias:
            continue
        tipos = []
        try:
            tipos = json.loads(p["aplicavel_tipos"] or "[]")
        except Exception:
            tipos = []
        if p["tipo_codigo"] and p["tipo_codigo"] not in tipos:
            tipos.append(p["tipo_codigo"])
        itens = await db.fetch_all(
            "SELECT servico_id, frequencia FROM catalogo_plano_itens WHERE plano_id = ?", (p["id"],)
        )
        for it in itens:
            if srv_ids and it["servico_id"] not in srv_ids:
                continue
            raw = it["frequencia"] or p["frequencia"]
            intervalo = None
            try:
                f = json.loads(raw) if raw else None
                intervalo = f.get("valor") if f else None
            except Exception:
                pass
            for t in (tipos or [None]):
                planos.append({
                    "id": f"{p['id']}::{t}::{it['servico_id']}",
                    "plano_id": p["id"], "servico_id": it["servico_id"],
                    "tipo_codigo": t, "ativo_id": None,
                    "intervalo": intervalo, "frequencia": raw, "ativo": 1,
                })

    qualificacoes = await db.fetch_all(
        "SELECT codigo, nome, descricao, requer_validade FROM qualificacoes_catalogo WHERE ativo=1"
    )

    documentos_pop: list[dict] = []
    pop_ids = [s.get("pop_doc_id") for s in catalogo_servicos if s.get("pop_doc_id")]
    if pop_ids:
        ph = ",".join("?" for _ in pop_ids)
        documentos_pop = await db.fetch_all(
            f"SELECT id, nome, tipo, mime, sha256, versao FROM documentos "
            f"WHERE id IN ({ph}) AND ativo=1",
            tuple(pop_ids),
        )

    return {
        "updated_at": datetime.utcnow().isoformat(timespec="seconds"),
        "ativos": ativos,
        "usuarios": usuarios,
        "locais": locais,
        "estoque_catalogo": estoque_catalogo,
        "catalogo_servicos": catalogo_servicos,
        "planos_manutencao": planos,
        "qualificacoes_catalogo": qualificacoes,
        "documentos_pop": documentos_pop,
    }
