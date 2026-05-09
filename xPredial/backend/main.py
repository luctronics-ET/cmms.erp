from __future__ import annotations

import os
from typing import Literal

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .db_predial import PredialDB

# --- Configuração de Integração ---
XCORE_URL = os.getenv("XCORE_URL", "http://localhost:8010")

StatusType = Literal["planejada", "em_execucao", "aguardando_aprovacao", "aprovada", "reprovada", "concluida"]
CondicaoType = Literal["ok", "atencao", "critico"]
PrioridadeType = Literal["baixa", "media", "alta"]

VALID_TRANSITIONS: dict[str, set[str]] = {
    "planejada": {"em_execucao"},
    "em_execucao": {"aguardando_aprovacao"},
    "aguardando_aprovacao": {"aprovada", "reprovada"},
    "aprovada": {"concluida"},
    "reprovada": {"em_execucao"},
    "concluida": set(),
}

BASE_CHECKLIST_ITEMS = [
    ("pintura_fachada", "Pintura de fachada externa"),
    ("pintura_interior", "Pintura interior"),
    ("iluminacao", "Verificacao de iluminacao"),
    ("piso", "Piso"),
    ("portas", "Portas"),
    ("janelas", "Janelas"),
    ("mobiliario", "Estado do mobiliario"),
    ("infiltracoes", "Infiltracoes"),
    ("banheiros_sanitarios", "Banheiros - sanitarios"),
    ("banheiros_pias", "Banheiros - pias"),
    ("banheiros_vazamentos", "Banheiros - vazamentos"),
]


class LocalCreate(BaseModel):
    codigo: str | None = None
    nome: str
    tipo: str
    area: str | None = None  # ADM | OPE | APA
    restricao: str | None = None
    parent_id: int | None = None
    area_m2: float | None = None


class TemplateCreate(BaseModel):
    nome: str
    tipo_local: str
    itens: list[str] = Field(default_factory=list)


class InspecaoCreate(BaseModel):
    local_id: int
    template_id: int | None = None
    servico_id: str | None = None
    titulo: str
    data_planejada: str | None = None
    executante_id: int | None = None  # FK para xCore usuarios
    observacoes: str | None = None
    degradacao_desc: str | None = None
    perda_desempenho_estimada: str | None = None


class InspecaoItemUpsert(BaseModel):
    codigo: str
    titulo: str
    norma_id: int | None = None
    condicao: CondicaoType
    observacao: str | None = None
    prioridade_reparo: PrioridadeType | None = None


class NormaCreate(BaseModel):
    codigo: str
    titulo: str
    descricao: str | None = None
    link_documento: str | None = None


class LaudoCreate(BaseModel):
    local_id: int
    inspecao_id: int | None = None
    titulo: str
    tipo: str
    arquivo_path: str | None = None
    data_emissao: str | None = None
    validade: str | None = None


class TransitionRequest(BaseModel):
    para_status: StatusType
    usuario: str | None = None
    comentario: str | None = None
    degradacao_desc: str | None = None
    perda_desempenho_estimada: str | None = None


app = FastAPI(title="xPredial API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = os.getenv("PREDIAL_DB_PATH")
db = PredialDB(DB_PATH)


@app.on_event("startup")
async def startup() -> None:
    await db.init()
    existing = await db.fetch_all("SELECT id FROM checklist_templates LIMIT 1")
    if not existing:
        template_id = await db.execute(
            "INSERT INTO checklist_templates(nome, tipo_local) VALUES (?, ?)",
            ("Checklist predial padrao", "geral"),
        )
        for idx, (codigo, titulo) in enumerate(BASE_CHECKLIST_ITEMS):
            await db.execute(
                "INSERT INTO checklist_template_items(template_id, codigo, titulo, obrigatorio, ordem) VALUES (?, ?, ?, 1, ?)",
                (template_id, codigo, titulo, idx),
            )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/usuarios")
async def proxy_usuarios():
    """Proxy para o xCore para obter lista de usuários."""
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{XCORE_URL}/api/usuarios")
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            # Fallback ou erro detalhado
            return []


@app.get("/api/v1/locais")
async def list_locais() -> list[dict]:
    return await db.fetch_all(
        "SELECT * FROM locais ORDER BY CASE WHEN neo IS NULL OR neo = '' THEN 1 ELSE 0 END, neo, nome"
    )


@app.post("/api/v1/locais")
async def create_local(payload: LocalCreate) -> dict:
    parent_name: str | None = None
    if payload.parent_id:
        parent = await db.fetch_one("SELECT id, nome, area FROM locais WHERE id = ?", (payload.parent_id,))
        if not parent:
            raise HTTPException(status_code=404, detail="Parent local not found")
        parent_name = parent["nome"]

    area = payload.area
    if area is None and payload.parent_id:
        parent_area = await db.fetch_one("SELECT area FROM locais WHERE id = ?", (payload.parent_id,))
        area = parent_area["area"] if parent_area else None

    neo = payload.codigo.replace("CMASM-", "") if payload.codigo else None
    endereco = f"{parent_name or 'CMASM'} - {area}" if area else (parent_name or None)
    local_id = await db.execute(
        "INSERT INTO locais(codigo, neo, area, endereco, restricao, nome, tipo, parent_id, area_m2) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            payload.codigo,
            neo,
            area,
            endereco,
            payload.restricao,
            payload.nome,
            payload.tipo,
            payload.parent_id,
            payload.area_m2,
        ),
    )
    created = await db.fetch_one("SELECT * FROM locais WHERE id = ?", (local_id,))
    return created or {}


@app.get("/api/v1/templates")
async def list_templates(tipo_local: str | None = None) -> list[dict]:
    if tipo_local:
        templates = await db.fetch_all(
            "SELECT * FROM checklist_templates WHERE tipo_local = ? OR tipo_local = 'geral' ORDER BY nome",
            (tipo_local,),
        )
    else:
        templates = await db.fetch_all("SELECT * FROM checklist_templates ORDER BY nome")

    for template in templates:
        items = await db.fetch_all(
            "SELECT * FROM checklist_template_items WHERE template_id = ? ORDER BY ordem, id",
            (template["id"],),
        )
        template["itens"] = items
    return templates


@app.post("/api/v1/templates")
async def create_template(payload: TemplateCreate) -> dict:
    template_id = await db.execute(
        "INSERT INTO checklist_templates(nome, tipo_local) VALUES (?, ?)",
        (payload.nome, payload.tipo_local),
    )
    items = payload.itens or [item[1] for item in BASE_CHECKLIST_ITEMS]
    for idx, title in enumerate(items):
        code = (
            title.lower()
            .replace("-", " ")
            .replace("/", " ")
            .replace("  ", " ")
            .strip()
            .replace(" ", "_")
        )
        await db.execute(
            "INSERT INTO checklist_template_items(template_id, codigo, titulo, ordem) VALUES (?, ?, ?, ?)",
            (template_id, code, title, idx),
        )
    return {"id": template_id}


@app.get("/api/v1/inspecoes")
async def list_inspecoes(status: str | None = None, local_id: int | None = None) -> list[dict]:
    query = (
        "SELECT i.*, l.nome AS local_nome, t.nome AS template_nome "
        "FROM inspecoes i "
        "JOIN locais l ON l.id = i.local_id "
        "LEFT JOIN checklist_templates t ON t.id = i.template_id"
    )
    params: list = []
    clauses: list[str] = []
    if status:
        clauses.append("i.status = ?")
        params.append(status)
    if local_id:
        clauses.append("i.local_id = ?")
        params.append(local_id)
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY i.id DESC"
    return await db.fetch_all(query, tuple(params))


@app.post("/api/v1/inspecoes")
async def create_inspecao(payload: InspecaoCreate) -> dict:
    local = await db.fetch_one("SELECT * FROM locais WHERE id = ?", (payload.local_id,))
    if not local:
        raise HTTPException(status_code=404, detail="Local not found")

    template_id = payload.template_id
    if not template_id:
        template = await db.fetch_one(
            "SELECT * FROM checklist_templates WHERE tipo_local = ? OR tipo_local = 'geral' ORDER BY CASE WHEN tipo_local = ? THEN 0 ELSE 1 END, id LIMIT 1",
            (local["tipo"], local["tipo"]),
        )
        if not template:
            raise HTTPException(status_code=400, detail="No checklist template available")
        template_id = template["id"]

    inspecao_id = await db.execute(
        "INSERT INTO inspecoes(local_id, template_id, servico_id, titulo, data_planejada, executante_id, observacoes, degradacao_desc, perda_desempenho_estimada) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            payload.local_id,
            template_id,
            payload.servico_id,
            payload.titulo,
            payload.data_planejada,
            payload.executante_id,
            payload.observacoes,
            payload.degradacao_desc,
            payload.perda_desempenho_estimada,
        ),
    )

    items = await db.fetch_all(
        "SELECT codigo, titulo, norma_id FROM checklist_template_items WHERE template_id = ? ORDER BY ordem, id",
        (template_id,),
    )
    for item in items:
        await db.execute(
            "INSERT INTO inspecao_itens(inspecao_id, codigo, titulo, norma_id) VALUES (?, ?, ?, ?)",
            (inspecao_id, item["codigo"], item["titulo"], item["norma_id"]),
        )

    await db.execute(
        "INSERT INTO workflow_events(inspecao_id, de_status, para_status, comentario) VALUES (?, NULL, 'planejada', ?)",
        (inspecao_id, "Inspecao criada"),
    )

    created = await db.fetch_one("SELECT * FROM inspecoes WHERE id = ?", (inspecao_id,))
    return created or {}


@app.get("/api/v1/inspecoes/{inspecao_id}")
async def get_inspecao(inspecao_id: int) -> dict:
    inspecao = await db.fetch_one(
        "SELECT i.*, l.nome AS local_nome "
        "FROM inspecoes i "
        "JOIN locais l ON l.id = i.local_id "
        "WHERE i.id = ?",
        (inspecao_id,),
    )
    # Nota: No futuro, executante_nome viria de um JOIN com xCore se fosse a mesma DB,
    # ou populado via API. Por enquanto, retornamos o ID e o frontend resolve ou fazemos o join se for local.
    # Como os usuários estão no xCore, o ideal é o frontend buscar pelo ID ou o backend fazer a consulta.
    
    if not inspecao:
        raise HTTPException(status_code=404, detail="Inspecao not found")

    # Tenta buscar nome do executante se houver executante_id
    inspecao["executante_nome"] = "Não atribuído"
    if inspecao.get("executante_id"):
        async with httpx.AsyncClient() as client:
            try:
                r = await client.get(f"{XCORE_URL}/api/usuarios/{inspecao['executante_id']}")
                if r.status_code == 200:
                    user = r.json()
                    inspecao["executante_nome"] = f"{user.get('posto', '')} {user.get('nome', '')}".strip()
            except:
                pass

    inspecao["itens"] = await db.fetch_all(
        "SELECT it.*, n.codigo AS norma_codigo, n.titulo AS norma_titulo "
        "FROM inspecao_itens it "
        "LEFT JOIN normas n ON n.id = it.norma_id "
        "WHERE it.inspecao_id = ? ORDER BY it.id",
        (inspecao_id,),
    )
    inspecao["anexos"] = await db.fetch_all(
        "SELECT * FROM inspecao_anexos WHERE inspecao_id = ? ORDER BY id DESC",
        (inspecao_id,),
    )
    inspecao["workflow"] = await db.fetch_all(
        "SELECT * FROM workflow_events WHERE inspecao_id = ? ORDER BY id DESC",
        (inspecao_id,),
    )
    inspecao["laudos"] = await db.fetch_all(
        "SELECT * FROM laudos WHERE inspecao_id = ? ORDER BY id DESC",
        (inspecao_id,),
    )
    return inspecao


@app.put("/api/v1/inspecoes/{inspecao_id}/itens")
async def upsert_inspecao_item(inspecao_id: int, payload: InspecaoItemUpsert) -> dict:
    inspecao = await db.fetch_one("SELECT id FROM inspecoes WHERE id = ?", (inspecao_id,))
    if not inspecao:
        raise HTTPException(status_code=404, detail="Inspecao not found")

    existing = await db.fetch_one(
        "SELECT id FROM inspecao_itens WHERE inspecao_id = ? AND codigo = ?",
        (inspecao_id, payload.codigo),
    )

    if existing:
        await db.execute(
            "UPDATE inspecao_itens SET titulo = ?, norma_id = ?, condicao = ?, observacao = ?, prioridade_reparo = ?, updated_at = datetime('now') WHERE id = ?",
            (
                payload.titulo,
                payload.norma_id,
                payload.condicao,
                payload.observacao,
                payload.prioridade_reparo,
                existing["id"],
            ),
        )
    else:
        await db.execute(
            "INSERT INTO inspecao_itens(inspecao_id, codigo, titulo, norma_id, condicao, observacao, prioridade_reparo) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                inspecao_id,
                payload.codigo,
                payload.titulo,
                payload.norma_id,
                payload.condicao,
                payload.observacao,
                payload.prioridade_reparo,
            ),
        )

    row = await db.fetch_one(
        "SELECT * FROM inspecao_itens WHERE inspecao_id = ? AND codigo = ?",
        (inspecao_id, payload.codigo),
    )
    return row or {}


@app.put("/api/v1/inspecoes/{inspecao_id}/status")
async def transition_status(inspecao_id: int, payload: TransitionRequest) -> dict:
    inspecao = await db.fetch_one("SELECT id, status FROM inspecoes WHERE id = ?", (inspecao_id,))
    if not inspecao:
        raise HTTPException(status_code=404, detail="Inspecao not found")

    current = inspecao["status"]
    allowed = VALID_TRANSITIONS.get(current, set())
    if payload.para_status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Transicao invalida: {current} -> {payload.para_status}",
        )

    await db.execute(
        "UPDATE inspecoes SET "
        "status = ?, "
        "data_execucao = CASE WHEN ? = 'em_execucao' THEN date('now') ELSE data_execucao END, "
        "degradacao_desc = COALESCE(?, degradacao_desc), "
        "perda_desempenho_estimada = COALESCE(?, perda_desempenho_estimada), "
        "updated_at = datetime('now') "
        "WHERE id = ?",
        (
            payload.para_status,
            payload.para_status,
            payload.degradacao_desc,
            payload.perda_desempenho_estimada,
            inspecao_id,
        ),
    )
    await db.execute(
        "INSERT INTO workflow_events(inspecao_id, de_status, para_status, usuario, comentario) VALUES (?, ?, ?, ?, ?)",
        (inspecao_id, current, payload.para_status, payload.usuario, payload.comentario),
    )
    updated = await db.fetch_one("SELECT * FROM inspecoes WHERE id = ?", (inspecao_id,))
    return updated or {}


@app.get("/api/v1/historico")
async def historico(local_id: int | None = None, status: str | None = None) -> list[dict]:
    query = (
        "SELECT i.id, i.titulo, i.status, i.data_planejada, i.data_execucao, i.updated_at, l.nome AS local_nome "
        "FROM inspecoes i JOIN locais l ON l.id = i.local_id"
    )
    params: list = []
    clauses: list[str] = []
    if local_id:
        clauses.append("i.local_id = ?")
        params.append(local_id)
    if status:
        clauses.append("i.status = ?")
        params.append(status)
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY i.updated_at DESC"
    return await db.fetch_all(query, tuple(params))


@app.get("/api/v1/relatorio/resumo")
async def relatorio_resumo() -> dict:
    status_rows = await db.fetch_all(
        "SELECT status, COUNT(*) AS total FROM inspecoes GROUP BY status ORDER BY status"
    )
    criticos = await db.fetch_one(
        "SELECT COUNT(*) AS total FROM inspecao_itens WHERE condicao = 'critico'"
    )
    laudos_count = await db.fetch_one("SELECT COUNT(*) AS total FROM laudos")
    return {
        "por_status": status_rows,
        "itens_criticos": criticos["total"] if criticos else 0,
        "total_laudos": laudos_count["total"] if laudos_count else 0,
    }


# --- NORMAS ---

@app.get("/api/v1/normas")
async def list_normas() -> list[dict]:
    return await db.fetch_all("SELECT * FROM normas ORDER BY codigo")


@app.post("/api/v1/normas")
async def create_norma(payload: NormaCreate) -> dict:
    norma_id = await db.execute(
        "INSERT INTO normas(codigo, titulo, descricao, link_documento) VALUES (?, ?, ?, ?)",
        (payload.codigo, payload.titulo, payload.descricao, payload.link_documento),
    )
    return {"id": norma_id}


# --- LAUDOS ---

@app.get("/api/v1/laudos")
async def list_laudos(local_id: int | None = None) -> list[dict]:
    query = (
        "SELECT la.*, l.nome AS local_nome "
        "FROM laudos la "
        "JOIN locais l ON l.id = la.local_id"
    )
    params = []
    if local_id:
        query += " WHERE la.local_id = ?"
        params.append(local_id)
    query += " ORDER BY la.id DESC"
    return await db.fetch_all(query, tuple(params))


@app.post("/api/v1/laudos")
async def create_laudo(payload: LaudoCreate) -> dict:
    laudo_id = await db.execute(
        "INSERT INTO laudos(local_id, inspecao_id, titulo, tipo, arquivo_path, data_emissao, validade) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            payload.local_id,
            payload.inspecao_id,
            payload.titulo,
            payload.tipo,
            payload.arquivo_path,
            payload.data_emissao,
            payload.validade,
        ),
    )
    return {"id": laudo_id}
