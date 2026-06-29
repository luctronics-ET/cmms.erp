"""
Router de Ajuda & Documentação — DOC-01, DOC-02, DOC-03.

Endpoints:
  GET  /api/docs/ajuda?chave=       — tópico de ajuda contextual (DOC-01)
  GET  /api/docs/ajuda              — lista todos os tópicos
  PUT  /api/docs/ajuda/{chave}      — upsert conteúdo (ON CONFLICT preserva id)

  GET  /api/docs/documentos?categoria=&tipo=  — lista docs com última versão (DOC-02, DOC-03)
  POST /api/docs/documentos                   — cria documento
  GET  /api/docs/documentos/{doc_id}          — detalhe + versões
  POST /api/docs/documentos/{doc_id}/versoes  — upload nova versão (UploadFile)
  GET  /api/docs/documentos/{doc_id}/versoes/{versao}/download — stream arquivo

Segurança:
  - _require_auth em todos os endpoints (GET inclusive)
  - _require_escrita (403 visualizador) em PUT ajuda, POST documentos, POST versoes
  - categoria validada contra ALLOWED_CATS frozenset ANTES de qualquer uso em path
  - extensão derivada de file.filename, validada contra ALLOWED_EXTS whitelist
  - path em disco = <CMASM_DOCS_DIR>/<categoria>/<doc_id>_v<versao><ext>
    NUNCA usa o nome original do cliente; NUNCA dentro da árvore /static/ (CR-01)
  - arquivo_nome = nome original (apenas metadado para Content-Disposition)
  - tamanho checado ANTES de gravar em disco (413 se > MAX_UPLOAD_BYTES)
  - download: os.path.normpath + abspath prefix check (2ª linha de defesa)
  - Content-Disposition: attachment (não inline)
  - versão atômica: SELECT COALESCE(MAX(versao),0)+1 + INSERT em UMA conexão aiosqlite

Referências: CONTEXT.md Phase 8, Rules.md (aditivo), REQUISITOS.md DOC-01/DOC-02/DOC-03,
             08-RESEARCH.md Patterns 1-5, data/schema_docs.sql.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime
from typing import Optional

import aiofiles
import aiosqlite
from fastapi import APIRouter, File, Header, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

router = APIRouter(prefix="/api/docs", tags=["docs"])

# ── Security constants ────────────────────────────────────────────────────────

ALLOWED_CATS: frozenset[str] = frozenset({
    "geral",
    "refrigeracao",
    "predial",
    "paiois",
    "transportes",
    "grama",
    "eletrica",
    "calibracao",
})

ALLOWED_EXTS: frozenset[str] = frozenset({
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".odt",
    ".ods",
    ".txt",
    ".md",
    ".csv",
    ".png",
    ".jpg",
    ".jpeg",
    ".html",
})

MAX_UPLOAD_BYTES: int = 25 * 1024 * 1024  # 25 MB

# Absolute path to the document storage root — MUST be outside the /static/ web-served
# tree to prevent unauthenticated access (CR-01).  Configurable via CMASM_DOCS_DIR env
# var so deployments can choose the location.  Defaults to ~/.cmasm/docs which is
# sibling to (i.e. entirely outside) the repo root that StaticFiles exposes.
_DATA_DOCS: str = os.path.normpath(
    os.environ.get("CMASM_DOCS_DIR") or os.path.expanduser("~/.cmasm/docs")
)
os.makedirs(_DATA_DOCS, exist_ok=True)  # ensure root exists at import time

# ── DB / Auth helpers (copied from manutencao.py pattern — no circular import) ─

def _db():
    """Acessa o singleton CoreDB de main.py sem importação circular."""
    return sys.modules["backend.main"].db


async def _require_auth(authorization: str | None) -> dict:
    """Valida Bearer token; levanta 401 se ausente/inválido/expirado."""
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


def _require_escrita(user: dict) -> None:
    """RES-05: levanta 403 se role == 'visualizador'. Chamar APÓS _require_auth."""
    if user.get("role") == "visualizador":
        raise HTTPException(403, "Visualizadores não têm permissão de escrita")


# ── Path helpers ──────────────────────────────────────────────────────────────

def _validate_cat(categoria: str) -> str:
    """Valida categoria contra ALLOWED_CATS. Levanta 400 se inválida.
    DEVE ser chamada ANTES de qualquer uso de categoria em path de arquivo.
    """
    if categoria not in ALLOWED_CATS:
        raise HTTPException(400, f"Categoria inválida: {categoria!r}. "
                                 f"Permitidas: {sorted(ALLOWED_CATS)}")
    return categoria


def _validate_ext(filename: str) -> str:
    """Extrai extensão em lowercase do filename; levanta 400 se não permitida.
    Decisão de segurança usa a EXTENSÃO (não o Content-Type do cliente).
    """
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTS:
        raise HTTPException(400, f"Extensão não permitida: {ext!r}. "
                                 f"Permitidas: {sorted(ALLOWED_EXTS)}")
    return ext


def _make_safe_path(categoria: str, doc_id: int, versao: int, ext: str) -> str:
    """Gera path absoluto a partir exclusivamente de dados server-controlled.
    NUNCA usa o nome original do arquivo do cliente — previne path traversal.
    Exemplo: /…/data/documentos/geral/42_v3.pdf
    """
    cat_dir = os.path.join(_DATA_DOCS, categoria)
    os.makedirs(cat_dir, exist_ok=True)
    filename = f"{doc_id}_v{versao}{ext}"
    return os.path.join(cat_dir, filename)


# ── Pydantic models ───────────────────────────────────────────────────────────

class AjudaIn(BaseModel):
    titulo: str
    conteudo_md: str
    categoria: Optional[str] = None


class DocumentoIn(BaseModel):
    categoria: str
    tipo: str = "modelo"
    titulo: str
    descricao: Optional[str] = None


# ── Ajuda endpoints (DOC-01) ──────────────────────────────────────────────────

@router.get("/ajuda")
async def list_ajuda(
    chave: Optional[str] = Query(None),
    authorization: str | None = Header(None),
):
    """Lista todos os tópicos de ajuda ou retorna um tópico por chave."""
    await _require_auth(authorization)
    if chave:
        row = await _db().fetch_one(
            "SELECT * FROM ajuda_topicos WHERE chave = ?", (chave,)
        )
        if not row:
            raise HTTPException(404, f"Tópico de ajuda não encontrado: {chave!r}")
        return row
    return await _db().fetch_all(
        "SELECT * FROM ajuda_topicos ORDER BY chave"
    )


@router.put("/ajuda/{chave}")
async def upsert_ajuda(
    chave: str,
    body: AjudaIn,
    authorization: str | None = Header(None),
):
    """Upsert de tópico de ajuda por chave. Preserva o id original (ON CONFLICT DO UPDATE).
    Requer _require_escrita — visualizadores recebem 403.
    """
    user = await _require_auth(authorization)
    _require_escrita(user)
    now = datetime.utcnow().isoformat()
    await _db().execute(
        """INSERT INTO ajuda_topicos (chave, categoria, titulo, conteudo_md, updated_at, updated_by)
           VALUES (?, ?, ?, ?, ?, ?)
           ON CONFLICT(chave) DO UPDATE SET
             titulo      = excluded.titulo,
             conteudo_md = excluded.conteudo_md,
             updated_at  = excluded.updated_at,
             updated_by  = excluded.updated_by""",
        (chave, body.categoria, body.titulo, body.conteudo_md, now, user["nome"]),
    )
    return await _db().fetch_one(
        "SELECT * FROM ajuda_topicos WHERE chave = ?", (chave,)
    )


# ── Documentos endpoints (DOC-02, DOC-03) ────────────────────────────────────

@router.get("/documentos")
async def list_documentos(
    categoria: Optional[str] = Query(None),
    tipo: Optional[str] = Query(None),
    authorization: str | None = Header(None),
):
    """Lista documentos ativos com sua última versão.
    Filtra por categoria e/ou tipo (modelo|formulario|guia|norma).
    Suporta DOC-03: tipo=norma ou tipo=guia para navegação de normas técnicas.
    """
    await _require_auth(authorization)
    conditions = ["d.ativo = 1"]
    params: list = []
    if categoria:
        conditions.append("d.categoria = ?")
        params.append(categoria)
    if tipo:
        conditions.append("d.tipo = ?")
        params.append(tipo)
    where = " AND ".join(conditions)
    sql = f"""
        SELECT d.*,
               COALESCE((
                   SELECT MAX(v.versao)
                   FROM docs_versoes v
                   WHERE v.documento_id = d.id AND v.ativo = 1
               ), 0) AS ultima_versao,
               (
                   SELECT v.arquivo_nome
                   FROM docs_versoes v
                   WHERE v.documento_id = d.id AND v.ativo = 1
                   ORDER BY v.versao DESC LIMIT 1
               ) AS ultimo_arquivo_nome
        FROM docs_documentos d
        WHERE {where}
        ORDER BY d.criado_em DESC
    """
    return await _db().fetch_all(sql, tuple(params))


@router.post("/documentos", status_code=201)
async def create_documento(
    body: DocumentoIn,
    authorization: str | None = Header(None),
):
    """Cria um novo documento. Requer _require_escrita.
    Categoria validada contra ALLOWED_CATS antes de qualquer uso em path.
    """
    user = await _require_auth(authorization)
    _require_escrita(user)
    _validate_cat(body.categoria)  # T-08-01: whitelist antes de usar categoria
    now = datetime.utcnow().isoformat()
    doc_id = await _db().execute(
        "INSERT INTO docs_documentos (categoria, tipo, titulo, descricao, criado_em, criado_por) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (body.categoria, body.tipo, body.titulo, body.descricao, now, user["nome"]),
    )
    return await _db().fetch_one(
        "SELECT * FROM docs_documentos WHERE id = ?", (doc_id,)
    )


@router.get("/documentos/{doc_id}")
async def get_documento(
    doc_id: int,
    authorization: str | None = Header(None),
):
    """Retorna detalhe do documento mais a lista completa de versões (ordenada)."""
    await _require_auth(authorization)
    doc = await _db().fetch_one(
        "SELECT * FROM docs_documentos WHERE id = ? AND ativo = 1", (doc_id,)
    )
    if not doc:
        raise HTTPException(404, "Documento não encontrado")
    versoes = await _db().fetch_all(
        "SELECT * FROM docs_versoes WHERE documento_id = ? ORDER BY versao ASC",
        (doc_id,),
    )
    return {**doc, "versoes": versoes}


@router.post("/documentos/{doc_id}/versoes", status_code=201)
async def upload_versao(
    doc_id: int,
    file: UploadFile = File(...),
    authorization: str | None = Header(None),
):
    """Faz upload de uma nova versão de documento.

    Defesas de segurança (T-08-01 a T-08-06):
    - _require_escrita: visualizadores recebem 403 (T-08-05)
    - Lê MAX_UPLOAD_BYTES+1 e retorna 413 ANTES de gravar em disco (T-08-04)
    - Extensão derivada de file.filename, validada contra ALLOWED_EXTS (T-08-03)
    - categoria do documento validada via ALLOWED_CATS (T-08-01)
    - path = data/documentos/<categoria>/<doc_id>_v<versao><ext> — server-controlled (T-08-01)
    - arquivo_nome = nome original armazenado APENAS como metadado (T-08-01)
    - SELECT COALESCE(MAX(versao),0)+1 + INSERT em UMA conexão aiosqlite (T-08-06)
    - UNIQUE(documento_id,versao) é o backstop de integridade (T-08-06)
    """
    user = await _require_auth(authorization)
    _require_escrita(user)

    # T-08-04: ler no máximo MAX_UPLOAD_BYTES+1 bytes — retorna 413 ANTES de gravar
    contents = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, f"Arquivo excede o limite de {MAX_UPLOAD_BYTES // (1024*1024)} MB")

    # T-08-03: validar extensão pelo filename, nunca pelo Content-Type do cliente
    ext = _validate_ext(file.filename or "")

    # Verificar que o documento existe e está ativo
    doc = await _db().fetch_one(
        "SELECT id, categoria FROM docs_documentos WHERE id = ? AND ativo = 1", (doc_id,)
    )
    if not doc:
        raise HTTPException(404, "Documento não encontrado")

    # T-08-01: whitelist categoria antes de usar em path (mesmo valor já gravado no INSERT)
    _validate_cat(doc["categoria"])

    # T-08-06: versão atômica — SELECT MAX + INSERT em UMA conexão aiosqlite, commit único
    async with aiosqlite.connect(_db().db_path) as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute(
            "SELECT COALESCE(MAX(versao), 0) + 1 AS next_v "
            "FROM docs_versoes WHERE documento_id = ?",
            (doc_id,),
        )
        row = await cur.fetchone()
        next_v = row["next_v"]

        # T-08-01: path gerado exclusivamente de dados server-controlled (doc_id, next_v, ext)
        abs_path = _make_safe_path(doc["categoria"], doc_id, next_v, ext)
        # Caminho relativo para armazenar no DB (relativo a _DATA_DOCS, nunca a data/)
        rel_path = os.path.relpath(abs_path, start=_DATA_DOCS)

        # CR-02: write file first, then INSERT+commit; on any DB failure remove the
        # orphaned file before re-raising so no dangling bytes are left on disk.
        async with aiofiles.open(abs_path, "wb") as f:
            await f.write(contents)

        try:
            await conn.execute(
                "INSERT INTO docs_versoes "
                "(documento_id, versao, arquivo_path, arquivo_nome, mime, tamanho, autor) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    doc_id,
                    next_v,
                    rel_path,
                    file.filename,              # original filename — metadata only
                    file.content_type,          # client mime — metadata only, not trusted
                    len(contents),
                    user["nome"],
                ),
            )
            await conn.commit()
        except Exception:
            # INSERT or commit failed (e.g. UNIQUE constraint, I/O error).
            # Remove the just-written file so no orphan bytes survive on disk.
            try:
                os.remove(abs_path)
            except OSError:
                pass
            raise

    return {
        "documento_id": doc_id,
        "versao": next_v,
        "arquivo_path": rel_path,
        "arquivo_nome": file.filename,
        "tamanho": len(contents),
    }


@router.get("/documentos/{doc_id}/versoes/{versao}/download")
async def download_versao(
    doc_id: int,
    versao: int,
    authorization: str | None = Header(None),
):
    """Faz download de uma versão específica do documento.

    Defesas de segurança:
    - _require_auth: download requer autenticação (T-08-02 / ASVS V4)
    - os.path.normpath + abspath prefix check: segunda linha de defesa contra
      path traversal (T-08-02) — mesmo que arquivo_path no DB fosse corrompido,
      um path fora de _DATA_DOCS retorna 403 antes de servir qualquer arquivo
    - Content-Disposition: attachment (não inline) — neutraliza XSS em .html
    """
    await _require_auth(authorization)
    row = await _db().fetch_one(
        "SELECT arquivo_path, arquivo_nome, mime "
        "FROM docs_versoes "
        "WHERE documento_id = ? AND versao = ? AND ativo = 1",
        (doc_id, versao),
    )
    if not row:
        raise HTTPException(404, "Versão não encontrada")

    # T-08-02: resolver path absoluto e verificar que permanece dentro de _DATA_DOCS.
    # arquivo_path é relativo a _DATA_DOCS (nunca a data/) — ver upload_versao.
    data_docs_abs = os.path.abspath(_DATA_DOCS)
    abs_path = os.path.normpath(os.path.join(data_docs_abs, row["arquivo_path"]))

    # Garantir separador de diretório após o prefixo para evitar falso-positivo
    # (ex: abspath '/data/documentos_evil' não deve passar no check de '/data/documentos')
    if not (abs_path == data_docs_abs or abs_path.startswith(data_docs_abs + os.sep)):
        raise HTTPException(403, "Acesso negado: path fora da área de documentos")

    if not os.path.isfile(abs_path):
        raise HTTPException(404, "Arquivo físico não encontrado no servidor")

    # Content-Disposition: attachment — neutraliza XSS em arquivos .html
    return FileResponse(
        path=abs_path,
        filename=row["arquivo_nome"],  # nome original para Content-Disposition
        media_type=row["mime"] or "application/octet-stream",
    )
