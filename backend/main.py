from __future__ import annotations

import csv
import io
import os
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException, Header, Query
from fastapi import Request, Response
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .db_core import CoreDB
from .grama import router as grama_router, init_grama

# ── Config ────────────────────────────────────────────────────────────────────
DB_PATH   = os.getenv("DB_PATH",   os.path.join(os.path.dirname(__file__), "..", "data", "core.db"))
TOKEN_TTL = int(os.getenv("TOKEN_TTL_HOURS", "8"))
XPREDIAL_URL   = os.getenv("XPREDIAL_URL",   "http://127.0.0.1:8002").rstrip("/")
XAGUADA_URL    = os.getenv("XAGUADA_URL",    "http://127.0.0.1:8001").rstrip("/")
XPAIOL_URL     = os.getenv("XPAIOL_URL",     "http://127.0.0.1:8003").rstrip("/")
XCALIBRACAO_URL = os.getenv("XCALIBRACAO_URL", "http://127.0.0.1:8004").rstrip("/")

_SATELLITES = [
    {"id": "xpredial",   "name": "xPredial",   "url": XPREDIAL_URL,   "port": 8002},
    {"id": "xaguada",    "name": "xAguada",     "url": XAGUADA_URL,    "port": 8001},
    {"id": "xpaiol",     "name": "xPaiol",      "url": XPAIOL_URL,     "port": 8003},
    {"id": "xcalibracao","name": "xCalibracao", "url": XCALIBRACAO_URL,"port": 8004},
]

app = FastAPI(title="xCore API", version="1.0.0", docs_url="/docs")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

db = CoreDB(DB_PATH)
app.include_router(grama_router)

# Serve xCore frontend files (HTMLs, JS, CSS, assets)
_FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..")
_SHARED_ASSETS_DIR = os.path.join(_FRONTEND_DIR, "assets")
app.mount("/static", StaticFiles(directory=_FRONTEND_DIR), name="static")
app.mount("/assets", StaticFiles(directory=_SHARED_ASSETS_DIR), name="assets")


@app.get("/")
async def root():
    return FileResponse(os.path.join(_FRONTEND_DIR, "cmasm_erp.html"))


@app.get("/{filename:path}.html")
async def serve_html(filename: str):
    path = os.path.join(_FRONTEND_DIR, f"{filename}.html")
    if os.path.isfile(path):
        return FileResponse(path)
    raise HTTPException(404, "Página não encontrada")


async def _proxy_xpredial(path: str, request: Request) -> Response:
    target_path = path.lstrip("/")
    target_url = f"{XPREDIAL_URL}/{target_path}" if target_path else XPREDIAL_URL
    if request.url.query:
        target_url = f"{target_url}?{request.url.query}"

    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in {"host", "content-length", "connection"}
    }
    body = await request.body()

    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            upstream = await client.request(
                request.method,
                target_url,
                headers=headers,
                content=body or None,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(502, f"xPredial indisponível: {exc}") from exc

    response_headers = {
        key: value
        for key, value in upstream.headers.items()
        if key.lower() not in {"content-length", "connection", "transfer-encoding", "content-encoding"}
    }
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=response_headers,
    )


@app.api_route("/api/predial", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
async def proxy_xpredial_root(request: Request):
    return await _proxy_xpredial("", request)


@app.api_route("/api/predial/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
async def proxy_xpredial(path: str, request: Request):
    return await _proxy_xpredial(path, request)


@app.get("/api/modulos")
async def list_modulos():
    """Lista os módulos satélite registrados com status de saúde."""
    results = []
    async with httpx.AsyncClient(timeout=3.0) as client:
        for sat in _SATELLITES:
            try:
                r = await client.get(f"{sat['url']}/health")
                status = "online" if r.status_code == 200 else "error"
            except Exception:
                status = "offline"
            results.append({**sat, "status": status})
    return results


@app.on_event("startup")
async def startup():
    await db.init()
    init_grama(db)


# ── Auth helpers ──────────────────────────────────────────────────────────────
def _djb2(pw: str) -> str:
    """Mesmo algoritmo do ERP_core (hashPw) para compatibilidade."""
    h = 0
    for ch in pw:
        h = ((h << 5) - h + ord(ch)) & 0xFFFFFFFF
        if h >= 0x80000000:
            h -= 0x100000000
    return format(h, "x") if h >= 0 else format(h & 0xFFFFFFFF, "x")


async def _require_auth(authorization: str | None) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Token ausente")
    token = authorization[7:]
    row = await db.fetch_one(
        "SELECT s.usuario_id, u.nome, u.role FROM sessoes s JOIN usuarios u ON u.id = s.usuario_id "
        "WHERE s.token = ? AND s.expira_em > datetime('now')",
        (token,),
    )
    if not row:
        raise HTTPException(401, "Token inválido ou expirado")
    return row


# ── Models ────────────────────────────────────────────────────────────────────
class LoginIn(BaseModel):
    mat: str
    senha: str


class UsuarioIn(BaseModel):
    nome: str
    posto: Optional[str] = None
    mat: Optional[str] = None
    email: Optional[str] = None
    tel: Optional[str] = None
    tipo: str = "militar"
    role: str = "operador"
    senha: Optional[str] = None


class SyncIn(BaseModel):
    """Payload do backup JSON exportado pelo ERP_core (botão 'Backup completo')."""
    users: list[dict]
    cargos: dict
    estrutura: list[dict]


class AtivosIn(BaseModel):
    """Payload do backup de gestao-ativos.html."""
    unidades: list[dict]


class AtivoIn(BaseModel):
    tipo: str
    categoria: str
    nome: str
    pat: Optional[str] = None
    placa: Optional[str] = None
    subtipo: Optional[str] = None   # vtr_int | vtr_ext | emb_rot | emb_pat
    loc: Optional[str] = None
    obs: Optional[str] = None
    uso_atual: float = 0
    unidade_uso: str = "h"


# ── Locais ────────────────────────────────────────────────────────────────────
class LocalIn(BaseModel):
    codigo: Optional[str] = None
    neo: Optional[str] = None
    nome: str
    tipo: str = "sala"
    area: str = "OPE"
    restricao: Optional[str] = None
    parent_id: Optional[int] = None
    estrutura_id: Optional[str] = None
    descricao: Optional[str] = None
    area_m2: Optional[float] = None


# ── Ordens de Serviço ─────────────────────────────────────────────────────────
class OSIn(BaseModel):
    titulo: str
    descricao: Optional[str] = None
    tipo: str = "corretiva"
    prioridade: str = "media"
    modulo_origem: Optional[str] = None
    solicitante_id: Optional[int] = None
    responsavel_id: Optional[int] = None
    local_id: Optional[int] = None
    data_prevista: Optional[str] = None
    custo_estimado: Optional[float] = None
    observacoes: Optional[str] = None


class OSStatusIn(BaseModel):
    para_status: str
    obs: Optional[str] = None
    usuario_id: Optional[int] = None


class EtapaIn(BaseModel):
    titulo: str
    ordem: int = 0


# ── Estoque ───────────────────────────────────────────────────────────────────
class EstoqueIn(BaseModel):
    codigo: Optional[str] = None
    nome: str
    categoria: str = "material"
    unidade: str = "un"
    qtd_atual: float = 0
    qtd_minima: float = 0
    preco_unitario: float = 0
    local_id: Optional[int] = None
    obs: Optional[str] = None


class MovimentoIn(BaseModel):
    tipo: str   # entrada | saida | ajuste
    quantidade: float
    os_id: Optional[str] = None
    usuario_id: Optional[int] = None
    obs: Optional[str] = None
    documento: Optional[str] = None   # NF, requisição, nº doc
    fornecedor: Optional[str] = None  # fornecedor (entrada) ou requisitante (saída)


# ── Auth ──────────────────────────────────────────────────────────────────────
@app.post("/api/auth/login")
async def login(body: LoginIn):
    # Aceita login por matrícula OU por nome (compatibilidade ERP)
    user = await db.fetch_one(
        "SELECT * FROM usuarios WHERE (mat = ? OR nome = ?) AND ativo = 1",
        (body.mat, body.mat),
    )
    if not user:
        raise HTTPException(401, "Usuário não encontrado")

    expected = user.get("pw_hash") or _djb2("1234")
    given    = _djb2(body.senha)
    # Aceita também comparação direta (hash já armazenado como djb2 hex)
    if given != expected:
        raise HTTPException(401, "Senha incorreta")

    token = secrets.token_urlsafe(32)
    expira = datetime.utcnow() + timedelta(hours=TOKEN_TTL)
    await db.execute(
        "INSERT INTO sessoes (token, usuario_id, expira_em) VALUES (?, ?, ?)",
        (token, user["id"], expira.isoformat()),
    )
    return {
        "token": token,
        "expira_em": expira.isoformat(),
        "usuario": {k: v for k, v in user.items() if k != "pw_hash"},
    }


@app.post("/api/auth/logout")
async def logout(authorization: str | None = Header(None)):
    if authorization and authorization.startswith("Bearer "):
        await db.execute("DELETE FROM sessoes WHERE token = ?", (authorization[7:],))
    return {"ok": True}


@app.get("/api/auth/me")
async def me(authorization: str | None = Header(None)):
    sess = await _require_auth(authorization)
    user = await db.fetch_one(
        "SELECT id, nome, posto, mat, email, tel, tipo, role FROM usuarios WHERE id = ?",
        (sess["usuario_id"],),
    )
    return user


@app.get("/health")
async def health():
    # Retorna contagem de usuários e ativos para o portal
    import aiosqlite
    async with aiosqlite.connect(DB_PATH) as db_conn:
        async with db_conn.execute("SELECT COUNT(*) FROM usuarios") as cur:
            usuarios = (await cur.fetchone())[0]
        async with db_conn.execute("SELECT COUNT(*) FROM ativos") as cur:
            ativos = (await cur.fetchone())[0]
    return {"status": "ok", "usuarios": usuarios, "ativos": ativos}


# ── Usuários ──────────────────────────────────────────────────────────────────
@app.get("/api/usuarios")
async def list_usuarios(ativo: int = 1):
    return await db.fetch_all(
        "SELECT id, nome, posto, mat, email, tel, tipo, role, ativo FROM usuarios WHERE ativo = ?",
        (ativo,),
    )


@app.get("/api/usuarios/{uid}")
async def get_usuario(uid: int):
    row = await db.fetch_one(
        "SELECT id, nome, posto, mat, email, tel, tipo, role, ativo FROM usuarios WHERE id = ?",
        (uid,),
    )
    if not row:
        raise HTTPException(404, "Usuário não encontrado")
    return row


@app.post("/api/usuarios", status_code=201)
async def create_usuario(body: UsuarioIn):
    pw = _djb2(body.senha) if body.senha else _djb2("1234")
    uid = await db.execute(
        "INSERT INTO usuarios (nome, posto, mat, email, tel, tipo, role, pw_hash) VALUES (?,?,?,?,?,?,?,?)",
        (body.nome, body.posto, body.mat, body.email, body.tel, body.tipo, body.role, pw),
    )
    return await get_usuario(uid)


@app.put("/api/usuarios/{uid}")
async def update_usuario(uid: int, body: UsuarioIn):
    row = await get_usuario(uid)
    pw = _djb2(body.senha) if body.senha else row.get("pw_hash", _djb2("1234"))
    await db.execute(
        "UPDATE usuarios SET nome=?, posto=?, mat=?, email=?, tel=?, tipo=?, role=?, pw_hash=? WHERE id=?",
        (body.nome, body.posto, body.mat, body.email, body.tel, body.tipo, body.role, pw, uid),
    )
    return await get_usuario(uid)


# ── Estrutura / Organograma ───────────────────────────────────────────────────
@app.get("/api/estrutura")
async def list_estrutura():
    return await db.fetch_all("SELECT * FROM estrutura ORDER BY id")


@app.get("/api/unidades")
async def list_unidades():
    """Estrutura enriquecida com ocupante atual."""
    rows = await db.fetch_all(
        """SELECT e.*, c.usuario_id, u.nome AS ocupante_nome, u.posto AS ocupante_posto
           FROM estrutura e
           LEFT JOIN cargos c ON c.unidade_id = e.id
           LEFT JOIN usuarios u ON u.id = c.usuario_id
           ORDER BY e.id""",
    )
    return rows


# ── Ativos ────────────────────────────────────────────────────────────────────
@app.get("/api/ativos")
async def list_ativos(categoria: str | None = None, ativo: int = 1):
    if categoria:
        return await db.fetch_all(
            "SELECT * FROM ativos WHERE categoria = ? AND ativo = ? ORDER BY nome",
            (categoria, ativo),
        )
    return await db.fetch_all("SELECT * FROM ativos WHERE ativo = ? ORDER BY categoria, nome", (ativo,))


@app.get("/api/ativos/{aid}")
async def get_ativo(aid: str):
    row = await db.fetch_one("SELECT * FROM ativos WHERE id = ?", (aid,))
    if not row:
        raise HTTPException(404, "Ativo não encontrado")
    return row


@app.post("/api/ativos", status_code=201)
async def create_ativo(body: AtivoIn):
    aid = str(uuid.uuid4())[:8]
    await db.execute(
        "INSERT INTO ativos (id, tipo, categoria, nome, pat, placa, subtipo, loc, obs, uso_atual, unidade_uso, ativo) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)",
        (aid, body.tipo, body.categoria, body.nome, body.pat, body.placa, body.subtipo,
         body.loc, body.obs, body.uso_atual, body.unidade_uso),
    )
    return await db.fetch_one("SELECT * FROM ativos WHERE id = ?", (aid,))


@app.put("/api/ativos/{aid}")
async def update_ativo(aid: str, body: AtivoIn):
    row = await db.fetch_one("SELECT id FROM ativos WHERE id = ?", (aid,))
    if not row:
        raise HTTPException(404, "Ativo não encontrado")
    await db.execute(
        "UPDATE ativos SET tipo=?, categoria=?, nome=?, pat=?, placa=?, subtipo=?, "
        "loc=?, obs=?, uso_atual=?, unidade_uso=? WHERE id=?",
        (body.tipo, body.categoria, body.nome, body.pat, body.placa, body.subtipo,
         body.loc, body.obs, body.uso_atual, body.unidade_uso, aid),
    )
    return await db.fetch_one("SELECT * FROM ativos WHERE id = ?", (aid,))


@app.patch("/api/ativos/{aid}/arquivar")
async def arquivar_ativo(aid: str):
    row = await db.fetch_one("SELECT id FROM ativos WHERE id = ?", (aid,))
    if not row:
        raise HTTPException(404, "Ativo não encontrado")
    await db.execute("UPDATE ativos SET ativo = 0 WHERE id = ?", (aid,))
    return {"ok": True}


@app.patch("/api/ativos/{aid}/restaurar")
async def restaurar_ativo(aid: str):
    row = await db.fetch_one("SELECT id FROM ativos WHERE id = ?", (aid,))
    if not row:
        raise HTTPException(404, "Ativo não encontrado")
    await db.execute("UPDATE ativos SET ativo = 1 WHERE id = ?", (aid,))
    return {"ok": True}


@app.post("/api/ativos/importar-csv")
async def importar_ativos_csv(body: dict):
    """
    Recebe {csv: "<conteudo>"} e faz bulk upsert.
    Colunas obrigatórias: nome, tipo, categoria
    Colunas opcionais: pat, loc, obs, uso_atual, unidade_uso, id
    """
    raw = body.get("csv", "")
    if not raw:
        raise HTTPException(400, "Campo 'csv' ausente")
    reader = csv.DictReader(io.StringIO(raw))
    inserted = 0
    for row in reader:
        nome = row.get("nome", "").strip()
        tipo = row.get("tipo", "").strip()
        categoria = row.get("categoria", "").strip()
        if not nome or not tipo or not categoria:
            continue
        aid = row.get("id", "").strip() or str(uuid.uuid4())[:8]
        pat = row.get("pat", "").strip() or None
        loc = row.get("loc", "").strip() or None
        obs = row.get("obs", "").strip() or None
        try:
            uso_atual = float(row.get("uso_atual", 0) or 0)
        except ValueError:
            uso_atual = 0
        unidade_uso = row.get("unidade_uso", "h").strip() or "h"
        if unidade_uso not in ("h", "km", "meses"):
            unidade_uso = "h"
        await db.execute(
            "INSERT OR REPLACE INTO ativos (id, tipo, categoria, nome, pat, loc, obs, uso_atual, unidade_uso, ativo) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)",
            (aid, tipo, categoria, nome, pat, loc, obs, uso_atual, unidade_uso),
        )
        inserted += 1
    return {"ok": True, "inseridos": inserted}


@app.get("/api/ativos/exportar/csv")
async def exportar_ativos_csv(categoria: str | None = None, ativo: int = 1):
    if categoria:
        rows = await db.fetch_all(
            "SELECT * FROM ativos WHERE categoria = ? AND ativo = ? ORDER BY nome",
            (categoria, ativo),
        )
    else:
        rows = await db.fetch_all(
            "SELECT * FROM ativos WHERE ativo = ? ORDER BY categoria, nome", (ativo,)
        )
    buf = io.StringIO()
    cols = ["id", "tipo", "categoria", "nome", "pat", "loc", "obs", "uso_atual", "unidade_uso"]
    writer = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore")
    writer.writeheader()
    for r in rows:
        writer.writerow({k: r[k] for k in cols if k in r})
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=ativos.csv"},
    )


# ── Sync: importa backup do ERP_core ─────────────────────────────────────────
@app.post("/api/sync/erp")
async def sync_erp(body: SyncIn):
    """
    Recebe o JSON exportado pelo botão 'Backup completo' do cmasm-erp.html
    e sincroniza usuários, estrutura e cargos no SQLite.
    Não destrói dados existentes — usa INSERT OR REPLACE.
    """
    # Usuários
    for u in body.users:
        await db.execute(
            """INSERT OR REPLACE INTO usuarios (id, nome, posto, mat, email, tel, tipo, role, pw_hash, ativo)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
            (u["id"], u.get("nome",""), u.get("posto",""), u.get("mat",""),
             u.get("email",""), u.get("tel",""), u.get("tipo","militar"),
             u.get("role","operador"), u.get("pw_hash","")),
        )

    # Estrutura (organograma)
    for e in body.estrutura:
        await db.execute(
            "INSERT OR REPLACE INTO estrutura (id, tipo, nome, pai, cargo, ct) VALUES (?,?,?,?,?,?)",
            (e["id"], e.get("tipo",""), e.get("nome",""), e.get("pai"),
             e.get("cargo",""), e.get("ct","")),
        )

    # Cargos
    for unidade_id, c in body.cargos.items():
        uid = c.get("usuario_id")
        obs = c.get("obs","")
        await db.execute(
            "INSERT OR REPLACE INTO cargos (unidade_id, usuario_id, obs) VALUES (?,?,?)",
            (unidade_id, uid, obs),
        )

    return {"ok": True, "usuarios": len(body.users), "estrutura": len(body.estrutura), "cargos": len(body.cargos)}


@app.post("/api/sync/ativos")
async def sync_ativos(body: AtivosIn):
    """
    Recebe o JSON exportado pelo gestao-ativos.html e sincroniza ativos.
    """
    # TIPOS → categoria (duplica lógica do gestao-ativos-data.js)
    CAT_MAP = {
        "FS220":"maquinas_corte","GAR":"maquinas_corte","MS650":"maquinas_corte",
        "TS114":"maquinas_corte","SOL":"maquinas_corte",
        "VTR_PICKUP":"viaturas","VTR_CARGA":"viaturas",
        "EMB_LANCHA":"embarcacoes","EMB_BOTE":"embarcacoes",
        "AC_SPLIT":"climatizacao","AC_CENTRAL":"climatizacao",
        "GERADOR":"eletrica",
    }
    UNIT_MAP = {"FS220":"h","GAR":"h","MS650":"h","TS114":"h","SOL":"h",
                "VTR_PICKUP":"km","VTR_CARGA":"km",
                "EMB_LANCHA":"h","EMB_BOTE":"h",
                "AC_SPLIT":"meses","AC_CENTRAL":"meses","GERADOR":"h"}

    for u in body.unidades:
        tid  = u.get("tipo","")
        cat  = CAT_MAP.get(tid, "outros")
        unit = UNIT_MAP.get(tid, "h")
        await db.execute(
            """INSERT OR REPLACE INTO ativos (id, tipo, categoria, nome, pat, loc, obs, ativo, unidade_uso)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (u["id"], tid, cat, u.get("nome",""), u.get("pat",""),
             u.get("loc",""), u.get("obs",""), 1 if u.get("ativo",True) else 0, unit),
        )

    return {"ok": True, "ativos": len(body.unidades)}


# ── Shared (compatibilidade ERP_core localStorage) ────────────────────────────
@app.get("/api/shared")
async def shared():
    """Retorna o mesmo formato que o ERP_core publica em localStorage.cmasm_shared."""
    users = await db.fetch_all(
        "SELECT id, nome, posto, mat, email, tel, tipo, role FROM usuarios WHERE ativo = 1"
    )
    cargos_rows = await db.fetch_all("SELECT unidade_id, usuario_id, obs FROM cargos")
    estrutura   = await db.fetch_all("SELECT id, tipo, nome, pai, cargo, ct FROM estrutura")
    cargos = {r["unidade_id"]: {"usuario_id": r["usuario_id"], "obs": r["obs"]} for r in cargos_rows}
    return {
        "v": 2,
        "ts": int(datetime.utcnow().timestamp() * 1000),
        "org": "CMASM",
        "users": users,
        "cargos": cargos,
        "estrutura": estrutura,
    }


# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/api/health")
async def health():
    n_users = await db.fetch_one("SELECT COUNT(*) AS n FROM usuarios")
    n_ativos = await db.fetch_one("SELECT COUNT(*) AS n FROM ativos")
    return {"status": "ok", "usuarios": n_users["n"], "ativos": n_ativos["n"]}


# ── Locais ────────────────────────────────────────────────────────────────────
@app.get("/api/locais")
async def list_locais(parent_id: int | None = None, tipo: str | None = None):
    clauses, params = ["l.ativo = 1"], []
    if parent_id is not None:
        clauses.append("l.parent_id = ?")
        params.append(parent_id)
    if tipo:
        clauses.append("l.tipo = ?")
        params.append(tipo)
    where = " AND ".join(clauses)
    return await db.fetch_all(
        f"""SELECT l.*,
                   e.nome AS estrutura_nome,
                   c.usuario_id AS ocupante_id,
                   u.nome AS ocupante_nome,
                   u.role AS ocupante_role,
                   (SELECT COUNT(*) FROM ativos a WHERE a.loc = l.codigo OR a.loc = l.nome) AS ativos_count,
                   (SELECT COUNT(*) FROM ordens_servico o WHERE o.local_id = l.id) AS os_count
            FROM locais l
            LEFT JOIN estrutura e ON e.id = COALESCE(l.estrutura_id, l.codigo)
            LEFT JOIN cargos c ON c.unidade_id = COALESCE(l.estrutura_id, l.codigo)
            LEFT JOIN usuarios u ON u.id = c.usuario_id
            WHERE {where}
            ORDER BY l.codigo, l.nome""",
        tuple(params),
    )


@app.get("/api/locais/{lid}")
async def get_local(lid: int):
    row = await db.fetch_one(
        """SELECT l.*,
                  e.nome AS estrutura_nome,
                  c.usuario_id AS ocupante_id,
                  u.nome AS ocupante_nome,
                  u.role AS ocupante_role,
                  (SELECT COUNT(*) FROM ativos a WHERE a.loc = l.codigo OR a.loc = l.nome) AS ativos_count,
                  (SELECT COUNT(*) FROM ordens_servico o WHERE o.local_id = l.id) AS os_count
           FROM locais l
           LEFT JOIN estrutura e ON e.id = COALESCE(l.estrutura_id, l.codigo)
           LEFT JOIN cargos c ON c.unidade_id = COALESCE(l.estrutura_id, l.codigo)
           LEFT JOIN usuarios u ON u.id = c.usuario_id
           WHERE l.id = ?""",
        (lid,),
    )
    if not row:
        raise HTTPException(404, "Local não encontrado")
    filhos = await db.fetch_all(
        "SELECT id, codigo, neo, nome, tipo, area, restricao, estrutura_id FROM locais WHERE parent_id = ? AND ativo = 1 ORDER BY codigo, nome",
        (lid,),
    )
    return {**row, "filhos": filhos}


@app.post("/api/locais", status_code=201)
async def create_local(body: LocalIn):
    lid = await db.execute(
        "INSERT INTO locais (codigo, neo, nome, tipo, area, restricao, parent_id, estrutura_id, descricao, area_m2) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (body.codigo, body.neo, body.nome, body.tipo, body.area, body.restricao, body.parent_id, body.estrutura_id, body.descricao, body.area_m2),
    )
    return await get_local(lid)


@app.put("/api/locais/{lid}")
async def update_local(lid: int, body: LocalIn):
    await get_local(lid)
    await db.execute(
        "UPDATE locais SET codigo=?, neo=?, nome=?, tipo=?, area=?, restricao=?, parent_id=?, estrutura_id=?, descricao=?, area_m2=? WHERE id=?",
        (body.codigo, body.neo, body.nome, body.tipo, body.area, body.restricao, body.parent_id, body.estrutura_id, body.descricao, body.area_m2, lid),
    )
    return await get_local(lid)


# ── Ordens de Serviço ─────────────────────────────────────────────────────────
async def _gen_os_codigo() -> str:
    ano = datetime.utcnow().year
    row = await db.fetch_one(
        "SELECT COUNT(*) AS n FROM ordens_servico WHERE codigo LIKE ?", (f"OS-{ano}-%",)
    )
    return f"OS-{ano}-{(row['n'] + 1):03d}"


@app.get("/api/os/kpis")
async def os_kpis(modulo: str | None = None):
    params: list = []
    where = ""
    if modulo:
        where = "WHERE modulo_origem = ?"
        params.append(modulo)
    rows = await db.fetch_all(
        f"SELECT status, COUNT(*) AS n FROM ordens_servico {where} GROUP BY status", tuple(params)
    )
    return {r["status"]: r["n"] for r in rows}


@app.get("/api/os/kanban")
async def os_kanban(modulo: str | None = None):
    """Retorna OS agrupadas por status para view kanban."""
    colunas = ["aberta", "em_andamento", "aguardando", "concluida", "cancelada"]
    params: list = []
    where = ""
    if modulo:
        where = "WHERE modulo_origem = ?"
        params.append(modulo)
    rows = await db.fetch_all(
        f"""SELECT o.*, l.nome AS local_nome,
                   u1.nome AS solicitante_nome, u2.nome AS responsavel_nome
            FROM ordens_servico o
            LEFT JOIN locais l ON l.id = o.local_id
            LEFT JOIN usuarios u1 ON u1.id = o.solicitante_id
            LEFT JOIN usuarios u2 ON u2.id = o.responsavel_id
            {where} ORDER BY o.criado_em DESC""",
        tuple(params),
    )
    result = {col: [] for col in colunas}
    for row in rows:
        col = row.get("status", "aberta")
        if col not in result:
            result[col] = []
        result[col].append(row)
    return result


@app.get("/api/os")
async def list_os(
    status: str | None = None,
    modulo: str | None = None,
    local_id: int | None = None,
    limit: int = Query(50, le=200),
):
    clauses, params = [], []
    if status:
        clauses.append("o.status = ?"); params.append(status)
    if modulo:
        clauses.append("o.modulo_origem = ?"); params.append(modulo)
    if local_id is not None:
        clauses.append("o.local_id = ?"); params.append(local_id)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    params.append(limit)
    return await db.fetch_all(
        f"""SELECT o.*, l.nome AS local_nome,
                   u1.nome AS solicitante_nome, u2.nome AS responsavel_nome
            FROM ordens_servico o
            LEFT JOIN locais l ON l.id = o.local_id
            LEFT JOIN usuarios u1 ON u1.id = o.solicitante_id
            LEFT JOIN usuarios u2 ON u2.id = o.responsavel_id
            {where} ORDER BY o.criado_em DESC LIMIT ?""",
        tuple(params),
    )


@app.get("/api/os/{oid}")
async def get_os(oid: str):
    row = await db.fetch_one(
        """SELECT o.*, l.nome AS local_nome,
                  u1.nome AS solicitante_nome, u2.nome AS responsavel_nome
           FROM ordens_servico o
           LEFT JOIN locais l ON l.id = o.local_id
           LEFT JOIN usuarios u1 ON u1.id = o.solicitante_id
           LEFT JOIN usuarios u2 ON u2.id = o.responsavel_id
           WHERE o.id = ?""",
        (oid,),
    )
    if not row:
        raise HTTPException(404, "OS não encontrada")
    etapas = await db.fetch_all("SELECT * FROM os_etapas WHERE os_id = ? ORDER BY ordem", (oid,))
    historico = await db.fetch_all(
        "SELECT h.*, u.nome AS usuario_nome FROM os_historico h LEFT JOIN usuarios u ON u.id = h.usuario_id WHERE h.os_id = ? ORDER BY h.criado_em",
        (oid,),
    )
    return {**row, "etapas": etapas, "historico": historico}


@app.post("/api/os", status_code=201)
async def create_os(body: OSIn):
    oid = str(uuid.uuid4())
    codigo = await _gen_os_codigo()
    await db.execute(
        """INSERT INTO ordens_servico
           (id, codigo, titulo, descricao, tipo, prioridade, modulo_origem,
            solicitante_id, responsavel_id, local_id, data_prevista, custo_estimado, observacoes)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (oid, codigo, body.titulo, body.descricao, body.tipo, body.prioridade,
         body.modulo_origem, body.solicitante_id, body.responsavel_id,
         body.local_id, body.data_prevista, body.custo_estimado, body.observacoes),
    )
    await db.execute(
        "INSERT INTO os_historico (os_id, status_de, status_para, obs) VALUES (?,?,?,?)",
        (oid, None, "aberta", "OS criada"),
    )
    return await get_os(oid)


@app.put("/api/os/{oid}/status")
async def update_os_status(oid: str, body: OSStatusIn):
    row = await db.fetch_one("SELECT status FROM ordens_servico WHERE id = ?", (oid,))
    if not row:
        raise HTTPException(404, "OS não encontrada")
    extra: dict = {}
    if body.para_status == "concluida":
        extra["data_conclusao"] = date_now = datetime.utcnow().strftime("%Y-%m-%d")
    updates = "status = ?, atualizado_em = CURRENT_TIMESTAMP"
    params: list = [body.para_status]
    if extra.get("data_conclusao"):
        updates += ", data_conclusao = ?"
        params.append(extra["data_conclusao"])
    params.append(oid)
    await db.execute(f"UPDATE ordens_servico SET {updates} WHERE id = ?", tuple(params))
    await db.execute(
        "INSERT INTO os_historico (os_id, status_de, status_para, obs, usuario_id) VALUES (?,?,?,?,?)",
        (oid, row["status"], body.para_status, body.obs, body.usuario_id),
    )
    return await get_os(oid)


@app.post("/api/os/{oid}/etapas", status_code=201)
async def add_etapa(oid: str, body: EtapaIn):
    row = await db.fetch_one("SELECT id FROM ordens_servico WHERE id = ?", (oid,))
    if not row:
        raise HTTPException(404, "OS não encontrada")
    eid = await db.execute(
        "INSERT INTO os_etapas (os_id, titulo, ordem) VALUES (?,?,?)",
        (oid, body.titulo, body.ordem),
    )
    return await db.fetch_one("SELECT * FROM os_etapas WHERE id = ?", (eid,))


@app.patch("/api/os/{oid}/etapas/{eid}")
async def toggle_etapa(oid: str, eid: int, concluida: int = Query(..., ge=0, le=1)):
    row = await db.fetch_one("SELECT id FROM os_etapas WHERE id = ? AND os_id = ?", (eid, oid))
    if not row:
        raise HTTPException(404, "Etapa não encontrada")
    await db.execute("UPDATE os_etapas SET concluida = ? WHERE id = ?", (concluida, eid))
    return await db.fetch_one("SELECT * FROM os_etapas WHERE id = ?", (eid,))


# ── Estoque ───────────────────────────────────────────────────────────────────
@app.get("/api/estoque")
async def list_estoque(categoria: str | None = None, abaixo_minimo: int = 0):
    clauses, params = ["ativo = 1"], []
    if categoria:
        clauses.append("categoria = ?"); params.append(categoria)
    if abaixo_minimo:
        clauses.append("qtd_atual < qtd_minima")
    where = " AND ".join(clauses)
    return await db.fetch_all(f"SELECT * FROM estoque WHERE {where} ORDER BY categoria, nome", tuple(params))


@app.get("/api/estoque/{iid}")
async def get_estoque_item(iid: int):
    row = await db.fetch_one("SELECT * FROM estoque WHERE id = ?", (iid,))
    if not row:
        raise HTTPException(404, "Item não encontrado")
    movs = await db.fetch_all(
        "SELECT m.*, u.nome AS usuario_nome FROM estoque_movimentos m LEFT JOIN usuarios u ON u.id = m.usuario_id WHERE m.item_id = ? ORDER BY m.criado_em DESC LIMIT 50",
        (iid,),
    )
    return {**row, "movimentos": movs}


@app.post("/api/estoque", status_code=201)
async def create_estoque(body: EstoqueIn):
    iid = await db.execute(
        "INSERT INTO estoque (codigo, nome, categoria, unidade, qtd_atual, qtd_minima, preco_unitario, local_id, obs) VALUES (?,?,?,?,?,?,?,?,?)",
        (body.codigo, body.nome, body.categoria, body.unidade, body.qtd_atual, body.qtd_minima, body.preco_unitario, body.local_id, body.obs),
    )
    return await get_estoque_item(iid)


@app.put("/api/estoque/{iid}")
async def update_estoque(iid: int, body: EstoqueIn):
    await get_estoque_item(iid)
    await db.execute(
        "UPDATE estoque SET codigo=?, nome=?, categoria=?, unidade=?, qtd_minima=?, preco_unitario=?, local_id=?, obs=? WHERE id=?",
        (body.codigo, body.nome, body.categoria, body.unidade, body.qtd_minima, body.preco_unitario, body.local_id, body.obs, iid),
    )
    return await get_estoque_item(iid)


@app.get("/api/estoque/exportar/csv")
async def exportar_estoque_csv():
    rows = await db.fetch_all("SELECT * FROM estoque WHERE ativo = 1 ORDER BY categoria, nome")
    buf = io.StringIO()
    cols = ["id","codigo","nome","categoria","unidade","qtd_atual","qtd_minima","preco_unitario","obs"]
    writer = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore")
    writer.writeheader()
    for r in rows:
        writer.writerow({k: r.get(k,"") for k in cols})
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]), media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=estoque.csv"},
    )


# ── PMOC Refrigeração ─────────────────────────────────────────────────────────
class PmocRefrigIn(BaseModel):
    estado_operacional: str = "OP"
    obs: Optional[str] = None
    permanencia: int = 0
    criticidade: str = "MÉDIA"
    horas_dia: Optional[float] = None
    dias_semana: Optional[int] = None
    tensao_medida: Optional[float] = None
    corrente_medida: Optional[float] = None
    potencia_kw: Optional[float] = None
    quadro: Optional[str] = None
    disjuntor: Optional[str] = None
    cabo: Optional[str] = None
    gas_tipo: Optional[str] = None
    carga_g: Optional[float] = None
    pressao_medida: Optional[str] = None
    pressao_data: Optional[str] = None
    temp_evaporadora_m: Optional[str] = None
    temp_centro: Optional[str] = None
    temp_longe: Optional[str] = None
    ultima_manutencao: Optional[str] = None


_PMOC_REFRIG_SELECT = """
    SELECT p.*,
           a.nome AS ativo_nome, a.tipo AS ativo_tipo, a.subtipo AS ativo_marca,
           a.pat AS ativo_pat, a.uso_atual,
           l.nome AS local_nome, l.codigo AS local_codigo, l.area_m2,
           lp.nome AS predio_nome, lp.id AS predio_id
    FROM pmoc_refrigeracao p
    LEFT JOIN ativos a ON a.id = p.ativo_id
    LEFT JOIN locais l ON l.id = p.local_id
    LEFT JOIN locais lp ON lp.id = l.parent_id
"""


@app.get("/api/pmoc/refrigeracao/kpis")
async def pmoc_refrig_kpis():
    total = await db.fetch_one("SELECT COUNT(*) AS n FROM pmoc_refrigeracao")
    op    = await db.fetch_one("SELECT COUNT(*) AS n FROM pmoc_refrigeracao WHERE estado_operacional = 'OP'")
    inop  = await db.fetch_one("SELECT COUNT(*) AS n FROM pmoc_refrigeracao WHERE estado_operacional = 'INOP'")
    crits = await db.fetch_all("SELECT criticidade, COUNT(*) AS n FROM pmoc_refrigeracao GROUP BY criticidade ORDER BY n DESC")
    return {
        "total": total["n"],
        "op": op["n"],
        "inop": inop["n"],
        "por_criticidade": {r["criticidade"]: r["n"] for r in crits},
    }


@app.get("/api/pmoc/refrigeracao")
async def list_pmoc_refrig(
    estado: str | None = None,
    criticidade: str | None = None,
    local_id: int | None = None,
    inop: int = 0,
):
    clauses, params = [], []
    if estado:
        clauses.append("p.estado_operacional = ?"); params.append(estado)
    elif inop:
        clauses.append("p.estado_operacional = 'INOP'")
    if criticidade:
        clauses.append("p.criticidade = ?"); params.append(criticidade)
    if local_id is not None:
        clauses.append("p.local_id = ?"); params.append(local_id)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    return await db.fetch_all(
        f"{_PMOC_REFRIG_SELECT} {where} ORDER BY l.nome, a.nome",
        tuple(params),
    )


@app.get("/api/pmoc/refrigeracao/{pid}")
async def get_pmoc_refrig(pid: int):
    row = await db.fetch_one(
        f"{_PMOC_REFRIG_SELECT} WHERE p.id = ?", (pid,)
    )
    if not row:
        raise HTTPException(404, "Registro PMOC não encontrado")
    return row


@app.put("/api/pmoc/refrigeracao/{pid}")
async def update_pmoc_refrig(pid: int, body: PmocRefrigIn):
    row = await db.fetch_one("SELECT id, ativo_id FROM pmoc_refrigeracao WHERE id = ?", (pid,))
    if not row:
        raise HTTPException(404, "Registro PMOC não encontrado")
    await db.execute(
        """UPDATE pmoc_refrigeracao SET
               estado_operacional=?, obs=?, permanencia=?, criticidade=?,
               horas_dia=?, dias_semana=?,
               tensao_medida=?, corrente_medida=?, potencia_kw=?,
               quadro=?, disjuntor=?, cabo=?,
               gas_tipo=?, carga_g=?, pressao_medida=?, pressao_data=?,
               temp_evaporadora_m=?, temp_centro=?, temp_longe=?,
               ultima_manutencao=?, atualizado_em=CURRENT_TIMESTAMP
           WHERE id=?""",
        (
            body.estado_operacional, body.obs, body.permanencia, body.criticidade,
            body.horas_dia, body.dias_semana,
            body.tensao_medida, body.corrente_medida, body.potencia_kw,
            body.quadro, body.disjuntor, body.cabo,
            body.gas_tipo, body.carga_g, body.pressao_medida, body.pressao_data,
            body.temp_evaporadora_m, body.temp_centro, body.temp_longe,
            body.ultima_manutencao, pid,
        ),
    )
    if row["ativo_id"]:
        await db.execute(
            "UPDATE ativos SET ativo = ? WHERE id = ?",
            (1 if body.estado_operacional == "OP" else 0, row["ativo_id"]),
        )
    return await get_pmoc_refrig(pid)


@app.post("/api/estoque/{iid}/movimentos", status_code=201)
async def create_movimento(iid: int, body: MovimentoIn):
    item = await db.fetch_one("SELECT qtd_atual FROM estoque WHERE id = ?", (iid,))
    if not item:
        raise HTTPException(404, "Item não encontrado")
    if body.tipo == "entrada":
        nova_qtd = item["qtd_atual"] + body.quantidade
    elif body.tipo == "saida":
        nova_qtd = item["qtd_atual"] - body.quantidade
        if nova_qtd < 0:
            raise HTTPException(400, "Quantidade insuficiente em estoque")
    else:  # ajuste
        nova_qtd = body.quantidade
    await db.execute("UPDATE estoque SET qtd_atual = ? WHERE id = ?", (nova_qtd, iid))
    mid = await db.execute(
        "INSERT INTO estoque_movimentos (item_id, tipo, quantidade, os_id, usuario_id, obs, documento, fornecedor) VALUES (?,?,?,?,?,?,?,?)",
        (iid, body.tipo, body.quantidade, body.os_id, body.usuario_id, body.obs, body.documento, body.fornecedor),
    )
    return await db.fetch_one("SELECT * FROM estoque_movimentos WHERE id = ?", (mid,))
