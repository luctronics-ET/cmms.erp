"""Tests for /api/docs/* endpoints — DOC-01, DOC-02, DOC-03.

Coverage:
  DOC-01  ajuda upsert persists: create → update same chave → same id, updated fields
  DOC-02  documento create + versioned upload: v1 → v2, history preserved (autor+data)
  DOC-03  list by categoria + tipo browsing
  SEC     extension rejected (400), oversize rejected (413),
          path traversal / bad categoria rejected (400),
          visualizador write → 403
  MAINT   db.init() twice idempotent; UNIQUE(documento_id,versao) present in schema

Isolation:
  - monkeypatch DB_PATH to tmp_path (no real data/core.db writes)
  - monkeypatch backend.docs._DATA_DOCS to tmp_path/documentos (no real data/documentos writes)

Test fixture style mirrors tests/test_manutencao.py and tests/test_catalogo.py.
"""
from __future__ import annotations

import importlib
import io
import os
import sqlite3
import sys

import pytest
from fastapi.testclient import TestClient


# ──────────────────────────────────────────────────────────────────────────────
# Fixture: fresh app + isolated DB + isolated docs dir per test
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def docs_client(tmp_path, monkeypatch):
    """Fresh app + DB + docs dir per test.

    Monkeypatches:
      - DB_PATH env var → tmp_path/test_docs.db
      - backend.docs._DATA_DOCS → tmp_path/documentos
    """
    db_path = tmp_path / "test_docs.db"
    docs_dir = tmp_path / "documentos"
    docs_dir.mkdir(parents=True, exist_ok=True)

    # 1. Point the app at an isolated DB
    monkeypatch.setenv("DB_PATH", str(db_path))

    # 2. Reload app modules so they pick up the new DB_PATH
    for mod in (
        "backend.main",
        "backend.db_core",
        "backend.grama",
        "backend.sync",
        "backend.manutencao",
        "backend.docs",
    ):
        sys.modules.pop(mod, None)

    import backend.docs  # imported fresh after pop
    main = importlib.import_module("backend.main")

    # 3. Re-import docs module (now loaded) and redirect its _DATA_DOCS
    docs_mod = sys.modules["backend.docs"]
    monkeypatch.setattr(docs_mod, "_DATA_DOCS", str(docs_dir))

    with TestClient(main.app) as client:
        yield client, main, docs_dir


# ──────────────────────────────────────────────────────────────────────────────
# DB / auth helpers (identical pattern to test_manutencao.py)
# ──────────────────────────────────────────────────────────────────────────────


def _query(main, sql, params=()):
    conn = sqlite3.connect(main.db.db_path)
    conn.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


def _exec(main, sql, params=()):
    conn = sqlite3.connect(main.db.db_path)
    try:
        conn.execute(sql, params)
        conn.commit()
    finally:
        conn.close()


def _seed_user(main, uid: int = 1, role: str = "admin") -> int:
    mat = f"00000{uid}"
    _exec(
        main,
        "INSERT OR IGNORE INTO usuarios (id, nome, mat, pw_hash, role, ativo) "
        "VALUES (?, ?, ?, 'hash', ?, 1)",
        (uid, f"User{uid}", mat, role),
    )
    return uid


def _seed_sessao(main, uid: int = 1, token: str = "test-token-docs") -> str:
    _exec(
        main,
        "INSERT OR IGNORE INTO sessoes (token, usuario_id, expira_em) "
        "VALUES (?, ?, datetime('now', '+8 hours'))",
        (token, uid),
    )
    return token


def _auth_operador(main) -> dict:
    """Admin token — has write access."""
    uid = _seed_user(main, uid=1, role="admin")
    token = _seed_sessao(main, uid=uid, token="ops-token-docs")
    return {"Authorization": f"Bearer {token}"}


def _auth_visualizador(main) -> dict:
    """Visualizador token — read-only; write endpoints must return 403."""
    _seed_user(main, uid=50, role="visualizador")
    token = _seed_sessao(main, uid=50, token="vis-token-docs")
    return {"Authorization": f"Bearer {token}"}


# ──────────────────────────────────────────────────────────────────────────────
# Helper: tiny in-memory file upload
# ──────────────────────────────────────────────────────────────────────────────

_PDF_BYTES = b"%PDF-1.4 tiny test file"
_PDF2_BYTES = b"%PDF-1.4 tiny test file v2 different content"


def _pdf_file(content: bytes = _PDF_BYTES, filename: str = "doc.pdf"):
    """Returns the `files` dict accepted by TestClient multipart."""
    return {"file": (filename, io.BytesIO(content), "application/pdf")}


# ──────────────────────────────────────────────────────────────────────────────
# DOC-01: Ajuda upsert
# ──────────────────────────────────────────────────────────────────────────────


def test_ajuda_upsert_persists(docs_client):
    """PUT /api/docs/ajuda/{chave} creates; second PUT updates same id (DOC-01).

    Asserts:
    - First PUT → 200, returns row with id and conteudo_md.
    - Second PUT same chave → same id (ON CONFLICT DO UPDATE, no duplicate row).
    - GET /api/docs/ajuda?chave=manutencao returns the updated titulo/conteudo_md.
    - Only ONE row exists in ajuda_topicos for that chave.
    """
    client, main, _ = docs_client
    headers = _auth_operador(main)

    chave = "manutencao"
    payload_v1 = {"titulo": "Manutenção v1", "conteudo_md": "# Conteúdo inicial"}
    payload_v2 = {"titulo": "Manutenção v2", "conteudo_md": "# Conteúdo atualizado"}

    # Create
    r1 = client.put(f"/api/docs/ajuda/{chave}", json=payload_v1, headers=headers)
    assert r1.status_code == 200, f"PUT v1 failed: {r1.status_code} {r1.text}"
    body1 = r1.json()
    assert body1["chave"] == chave
    assert body1["conteudo_md"] == payload_v1["conteudo_md"]
    original_id = body1["id"]

    # Update same chave
    r2 = client.put(f"/api/docs/ajuda/{chave}", json=payload_v2, headers=headers)
    assert r2.status_code == 200, f"PUT v2 failed: {r2.status_code} {r2.text}"
    body2 = r2.json()

    # Same id preserved (ON CONFLICT DO UPDATE, not INSERT new row)
    assert body2["id"] == original_id, (
        f"id changed on update — UPSERT must preserve original id; "
        f"v1 id={original_id}, v2 id={body2['id']}"
    )
    assert body2["titulo"] == payload_v2["titulo"]
    assert body2["conteudo_md"] == payload_v2["conteudo_md"]

    # GET returns updated content
    r_get = client.get(f"/api/docs/ajuda?chave={chave}", headers=headers)
    assert r_get.status_code == 200, f"GET ajuda failed: {r_get.status_code}"
    got = r_get.json()
    assert got["conteudo_md"] == payload_v2["conteudo_md"]
    assert got["titulo"] == payload_v2["titulo"]

    # DB: exactly ONE row for this chave
    rows = _query(main, "SELECT id FROM ajuda_topicos WHERE chave = ?", (chave,))
    assert len(rows) == 1, f"Expected 1 row after upsert, got {len(rows)}"
    assert rows[0]["id"] == original_id


# ──────────────────────────────────────────────────────────────────────────────
# DOC-02 / DOC-03: Documento create and list by categoria
# ──────────────────────────────────────────────────────────────────────────────


def test_documento_create_and_list_by_categoria(docs_client):
    """POST /api/docs/documentos + GET list with categoria filter (DOC-02, DOC-03).

    Asserts:
    - POST returns 201 with id and categoria.
    - GET ?categoria=geral returns the new document.
    - GET ?categoria=refrigeracao does NOT return it (isolation).
    """
    client, main, _ = docs_client
    headers = _auth_operador(main)

    payload = {
        "categoria": "geral",
        "tipo": "guia",
        "titulo": "Guia Geral de Uso",
        "descricao": "Descrição do guia",
    }

    r = client.post("/api/docs/documentos", json=payload, headers=headers)
    assert r.status_code == 201, f"POST documentos failed: {r.status_code} {r.text}"
    created = r.json()
    assert "id" in created
    doc_id = created["id"]
    assert created["categoria"] == "geral"
    assert created["titulo"] == payload["titulo"]

    # GET by correct categoria returns it
    r_list = client.get("/api/docs/documentos?categoria=geral", headers=headers)
    assert r_list.status_code == 200, f"GET list failed: {r_list.status_code}"
    items = r_list.json()
    found = [d for d in items if d["id"] == doc_id]
    assert len(found) == 1, f"Document {doc_id} not found in categoria=geral listing"

    # GET by different categoria does NOT return it
    r_other = client.get("/api/docs/documentos?categoria=refrigeracao", headers=headers)
    assert r_other.status_code == 200
    other_items = r_other.json()
    leaked = [d for d in other_items if d["id"] == doc_id]
    assert len(leaked) == 0, (
        f"Document {doc_id} (categoria=geral) leaked into categoria=refrigeracao listing"
    )


# ──────────────────────────────────────────────────────────────────────────────
# DOC-02: Version upload — history preserved, autor + data recorded
# ──────────────────────────────────────────────────────────────────────────────


def test_upload_versao_increments_and_preserves_history(docs_client):
    """Upload v1 → versao=1; upload v2 → versao=2; v1 still exists (DOC-02).

    Asserts:
    - First upload returns versao=1.
    - Second upload returns versao=2.
    - GET /{id} lists both versions ordered ascending.
    - Both entries have autor and criado_em (data) recorded.
    - v1 row is NOT deleted or overwritten.
    """
    client, main, _ = docs_client
    headers = _auth_operador(main)

    # Create the document first
    r_doc = client.post(
        "/api/docs/documentos",
        json={"categoria": "geral", "tipo": "norma", "titulo": "Norma de Teste"},
        headers=headers,
    )
    assert r_doc.status_code == 201
    doc_id = r_doc.json()["id"]

    # Upload version 1
    r_v1 = client.post(
        f"/api/docs/documentos/{doc_id}/versoes",
        files=_pdf_file(_PDF_BYTES, "versao1.pdf"),
        headers=headers,
    )
    assert r_v1.status_code == 201, f"Upload v1 failed: {r_v1.status_code} {r_v1.text}"
    v1 = r_v1.json()
    assert v1["versao"] == 1, f"Expected versao=1, got {v1['versao']}"
    assert v1["documento_id"] == doc_id

    # Upload version 2
    r_v2 = client.post(
        f"/api/docs/documentos/{doc_id}/versoes",
        files=_pdf_file(_PDF2_BYTES, "versao2.pdf"),
        headers=headers,
    )
    assert r_v2.status_code == 201, f"Upload v2 failed: {r_v2.status_code} {r_v2.text}"
    v2 = r_v2.json()
    assert v2["versao"] == 2, f"Expected versao=2, got {v2['versao']}"

    # GET detail: must return both versions
    r_detail = client.get(f"/api/docs/documentos/{doc_id}", headers=headers)
    assert r_detail.status_code == 200, f"GET detail failed: {r_detail.status_code}"
    detail = r_detail.json()
    versoes = detail.get("versoes", [])
    assert len(versoes) == 2, f"Expected 2 versions in history, got {len(versoes)}: {versoes}"

    # Versions sorted ascending (v1 first)
    assert versoes[0]["versao"] == 1
    assert versoes[1]["versao"] == 2

    # Both have autor and data (creation timestamp) recorded (not null)
    for v in versoes:
        assert v.get("autor") is not None and v["autor"] != "", (
            f"autor must be set for versao={v['versao']}; got {v}"
        )
        # The docs_versoes schema uses 'data' column for the creation timestamp
        assert v.get("data") is not None, (
            f"data (creation timestamp) must be recorded for versao={v['versao']}; got {v}"
        )

    # DB confirms both rows exist
    db_rows = _query(
        main,
        "SELECT versao, autor FROM docs_versoes WHERE documento_id = ? ORDER BY versao",
        (doc_id,),
    )
    assert len(db_rows) == 2, f"DB should have 2 version rows, got {len(db_rows)}"
    assert db_rows[0]["versao"] == 1
    assert db_rows[1]["versao"] == 2


# ──────────────────────────────────────────────────────────────────────────────
# DOC-02: Download returns exact bytes uploaded for the requested version
# ──────────────────────────────────────────────────────────────────────────────


def test_download_returns_correct_bytes(docs_client):
    """GET /{id}/versoes/{versao}/download returns exact bytes for that version.

    After uploading v1 (content A) and v2 (content B):
    - Download v1 returns content A (not B).
    - Download v2 returns content B.
    - Response includes Content-Disposition: attachment.
    """
    client, main, _ = docs_client
    headers = _auth_operador(main)

    # Create document
    r_doc = client.post(
        "/api/docs/documentos",
        json={"categoria": "geral", "tipo": "modelo", "titulo": "Doc Download Test"},
        headers=headers,
    )
    assert r_doc.status_code == 201
    doc_id = r_doc.json()["id"]

    bytes_v1 = b"Version 1 content bytes AAAA"
    bytes_v2 = b"Version 2 content bytes BBBB"

    # Upload v1 and v2
    client.post(
        f"/api/docs/documentos/{doc_id}/versoes",
        files=_pdf_file(bytes_v1, "v1.pdf"),
        headers=headers,
    )
    client.post(
        f"/api/docs/documentos/{doc_id}/versoes",
        files=_pdf_file(bytes_v2, "v2.pdf"),
        headers=headers,
    )

    # Download v1: must return bytes_v1 exactly
    r_dl1 = client.get(
        f"/api/docs/documentos/{doc_id}/versoes/1/download",
        headers=headers,
    )
    assert r_dl1.status_code == 200, f"Download v1 failed: {r_dl1.status_code} {r_dl1.text}"
    assert r_dl1.content == bytes_v1, (
        f"Download v1 returned wrong bytes; expected {bytes_v1!r}, got {r_dl1.content!r}"
    )
    # Content-Disposition: attachment neutralizes XSS in .html files
    cd = r_dl1.headers.get("content-disposition", "")
    assert "attachment" in cd, f"Expected Content-Disposition: attachment; got: {cd!r}"

    # Download v2: must return bytes_v2 exactly (not v1 bytes)
    r_dl2 = client.get(
        f"/api/docs/documentos/{doc_id}/versoes/2/download",
        headers=headers,
    )
    assert r_dl2.status_code == 200, f"Download v2 failed: {r_dl2.status_code} {r_dl2.text}"
    assert r_dl2.content == bytes_v2, (
        f"Download v2 returned wrong bytes; expected {bytes_v2!r}, got {r_dl2.content!r}"
    )


# ──────────────────────────────────────────────────────────────────────────────
# Security: Extension rejected
# ──────────────────────────────────────────────────────────────────────────────


def test_extension_rejected(docs_client):
    """Uploading a disallowed extension (.exe, .sh, .zip) returns 400.

    File must NOT be written to the docs dir.
    """
    client, main, docs_dir = docs_client
    headers = _auth_operador(main)

    # Create document
    r_doc = client.post(
        "/api/docs/documentos",
        json={"categoria": "geral", "tipo": "modelo", "titulo": "Doc Ext Test"},
        headers=headers,
    )
    assert r_doc.status_code == 201
    doc_id = r_doc.json()["id"]

    # Count files in docs_dir before the bad upload
    files_before = list(docs_dir.rglob("*"))
    file_count_before = sum(1 for f in files_before if f.is_file())

    for bad_ext in [".exe", ".sh", ".zip"]:
        bad_filename = f"malware{bad_ext}"
        r = client.post(
            f"/api/docs/documentos/{doc_id}/versoes",
            files={"file": (bad_filename, io.BytesIO(b"bad content"), "application/octet-stream")},
            headers=headers,
        )
        assert r.status_code == 400, (
            f"Extension {bad_ext!r} should be rejected with 400, got {r.status_code}: {r.text}"
        )

    # No file should have been written to docs_dir
    files_after = list(docs_dir.rglob("*"))
    file_count_after = sum(1 for f in files_after if f.is_file())
    assert file_count_after == file_count_before, (
        f"Bad extension upload wrote {file_count_after - file_count_before} file(s) to disk — "
        f"expected 0 writes for rejected uploads"
    )


# ──────────────────────────────────────────────────────────────────────────────
# Security: Oversize rejected (413) — use small monkeypatched cap
# ──────────────────────────────────────────────────────────────────────────────


def test_oversize_rejected(docs_client, monkeypatch):
    """Uploading bytes > MAX_UPLOAD_BYTES returns 413.

    Monkeypatches MAX_UPLOAD_BYTES to 16 (bytes) to keep the test fast.
    An upload of 17 bytes is over the cap → 413 before any disk write.
    An upload of 16 bytes (at-limit) succeeds → 201.
    """
    client, main, docs_dir = docs_client
    headers = _auth_operador(main)

    docs_mod = sys.modules["backend.docs"]
    monkeypatch.setattr(docs_mod, "MAX_UPLOAD_BYTES", 16)

    # Create document
    r_doc = client.post(
        "/api/docs/documentos",
        json={"categoria": "geral", "tipo": "modelo", "titulo": "Doc Oversize Test"},
        headers=headers,
    )
    assert r_doc.status_code == 201
    doc_id = r_doc.json()["id"]

    # Exactly 16 bytes → should succeed
    ok_bytes = b"A" * 16
    r_ok = client.post(
        f"/api/docs/documentos/{doc_id}/versoes",
        files=_pdf_file(ok_bytes, "ok.pdf"),
        headers=headers,
    )
    assert r_ok.status_code == 201, (
        f"At-limit upload (16 bytes) should succeed (201), got {r_ok.status_code}: {r_ok.text}"
    )

    # 17 bytes → over the cap → 413
    over_bytes = b"A" * 17
    files_before = sum(1 for f in docs_dir.rglob("*") if f.is_file())
    r_over = client.post(
        f"/api/docs/documentos/{doc_id}/versoes",
        files=_pdf_file(over_bytes, "oversize.pdf"),
        headers=headers,
    )
    assert r_over.status_code == 413, (
        f"Oversize upload (17 bytes with cap=16) should be rejected with 413, "
        f"got {r_over.status_code}: {r_over.text}"
    )

    # No file written to disk for the rejected upload
    files_after = sum(1 for f in docs_dir.rglob("*") if f.is_file())
    assert files_after == files_before, (
        f"Oversize upload wrote {files_after - files_before} file(s) — expected 0 writes"
    )


# ──────────────────────────────────────────────────────────────────────────────
# Security: Path traversal via invalid categoria → 400
# ──────────────────────────────────────────────────────────────────────────────


def test_path_traversal_defense(docs_client):
    """Creating a documento with a disallowed categoria returns 400 (T-08-01).

    ALLOWED_CATS frozenset is the first line of defense — _validate_cat() is called
    BEFORE any os.path.join with categoria, so no traversal path is ever constructed.
    """
    client, main, docs_dir = docs_client
    headers = _auth_operador(main)

    bad_categorias = [
        "../../etc",
        "../geral",
        "/etc/passwd",
        "unknown_cat",
        "",
    ]

    for bad_cat in bad_categorias:
        r = client.post(
            "/api/docs/documentos",
            json={"categoria": bad_cat, "tipo": "modelo", "titulo": "Traversal Test"},
            headers=headers,
        )
        assert r.status_code in (400, 422), (
            f"Categoria {bad_cat!r} should be rejected with 400/422, got {r.status_code}: {r.text}"
        )

    # No document created and no files written (docs_dir should be empty)
    files = list(docs_dir.rglob("*"))
    written_files = [f for f in files if f.is_file()]
    assert len(written_files) == 0, (
        f"No files should be written for rejected uploads; found: {written_files}"
    )


# ──────────────────────────────────────────────────────────────────────────────
# Security: Visualizador → 403 on write endpoints (RES-05)
# ──────────────────────────────────────────────────────────────────────────────


def test_visualizador_write_403(docs_client):
    """Visualizador token on PUT ajuda / POST documentos / POST versoes → 403 each.

    GET endpoints must still return 200 (read allowed).
    """
    client, main, _ = docs_client
    ops_headers = _auth_operador(main)
    vis_headers = _auth_visualizador(main)

    # 1. PUT /api/docs/ajuda/{chave} → 403 for visualizador
    r = client.put(
        "/api/docs/ajuda/test_vis",
        json={"titulo": "T", "conteudo_md": "# T"},
        headers=vis_headers,
    )
    assert r.status_code == 403, (
        f"visualizador PUT ajuda should be 403, got {r.status_code}: {r.text}"
    )

    # 2. POST /api/docs/documentos → 403 for visualizador
    r = client.post(
        "/api/docs/documentos",
        json={"categoria": "geral", "tipo": "guia", "titulo": "Vis Test"},
        headers=vis_headers,
    )
    assert r.status_code == 403, (
        f"visualizador POST documentos should be 403, got {r.status_code}: {r.text}"
    )

    # 3. Create a real document with operador, then test versoes as visualizador
    r_doc = client.post(
        "/api/docs/documentos",
        json={"categoria": "geral", "tipo": "modelo", "titulo": "Doc for Vis Test"},
        headers=ops_headers,
    )
    assert r_doc.status_code == 201
    doc_id = r_doc.json()["id"]

    r = client.post(
        f"/api/docs/documentos/{doc_id}/versoes",
        files=_pdf_file(_PDF_BYTES, "v.pdf"),
        headers=vis_headers,
    )
    assert r.status_code == 403, (
        f"visualizador POST versoes should be 403, got {r.status_code}: {r.text}"
    )

    # 4. GET endpoints ARE accessible to visualizador
    # First upsert a topic as operador so there is something to GET
    client.put(
        "/api/docs/ajuda/vis_read_test",
        json={"titulo": "Readable", "conteudo_md": "# Readable"},
        headers=ops_headers,
    )
    r_get = client.get("/api/docs/ajuda?chave=vis_read_test", headers=vis_headers)
    assert r_get.status_code == 200, (
        f"visualizador GET ajuda should be 200, got {r_get.status_code}"
    )

    r_list = client.get("/api/docs/documentos", headers=vis_headers)
    assert r_list.status_code == 200, (
        f"visualizador GET documentos should be 200, got {r_list.status_code}"
    )


# ──────────────────────────────────────────────────────────────────────────────
# Migration idempotency: db.init() twice raises no error; tables exist
# ──────────────────────────────────────────────────────────────────────────────


def test_migracoes_idempotentes(tmp_path, monkeypatch):
    """db.init() called twice on the same DB raises no error (idempotent migrations).

    Verifies that ajuda_topicos, docs_documentos, docs_versoes all exist after double init,
    and that UNIQUE(documento_id, versao) is present in the docs_versoes DDL.
    """
    db_path = tmp_path / "test_idempotent.db"
    monkeypatch.setenv("DB_PATH", str(db_path))

    # Reload modules to get clean state
    for mod in (
        "backend.main",
        "backend.db_core",
        "backend.grama",
        "backend.sync",
        "backend.manutencao",
        "backend.docs",
    ):
        sys.modules.pop(mod, None)

    import asyncio

    main = importlib.import_module("backend.main")

    async def _run():
        # First init (called by TestClient lifespan too; here we call it directly twice)
        await main.db.init()
        # Second init — must not raise (uses IF NOT EXISTS + PRAGMA checks)
        await main.db.init()

    asyncio.run(_run())

    # Verify tables exist
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        tables = {r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        for expected in ("ajuda_topicos", "docs_documentos", "docs_versoes"):
            assert expected in tables, (
                f"Table {expected!r} not found after double init; tables: {tables}"
            )

        # Verify UNIQUE(documento_id, versao) constraint on docs_versoes
        indexes = conn.execute(
            "SELECT name, sql FROM sqlite_master WHERE type='index' AND tbl_name='docs_versoes'"
        ).fetchall()
        unique_on_versao = any(
            idx["sql"] and "UNIQUE" in idx["sql"].upper()
            and "versao" in idx["sql"].lower()
            for idx in indexes
            if idx["sql"]
        )
        # Also check table DDL for inline UNIQUE constraint
        tbl_ddl = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='docs_versoes'"
        ).fetchone()
        ddl_has_unique = (
            tbl_ddl and "UNIQUE" in tbl_ddl["sql"].upper()
            and "versao" in tbl_ddl["sql"].lower()
        )
        assert unique_on_versao or ddl_has_unique, (
            "UNIQUE(documento_id, versao) not found in docs_versoes schema or indexes. "
            f"DDL: {tbl_ddl['sql'] if tbl_ddl else 'N/A'}, "
            f"Indexes: {[dict(i) for i in indexes]}"
        )
    finally:
        conn.close()


# ──────────────────────────────────────────────────────────────────────────────
# Bonus: GET /api/docs/ajuda (no chave) returns list of all topics
# ──────────────────────────────────────────────────────────────────────────────


def test_ajuda_list_all(docs_client):
    """GET /api/docs/ajuda without chave param returns a list of all topics."""
    client, main, _ = docs_client
    headers = _auth_operador(main)

    # Upsert two topics
    client.put("/api/docs/ajuda/chave_a", json={"titulo": "A", "conteudo_md": "# A"}, headers=headers)
    client.put("/api/docs/ajuda/chave_b", json={"titulo": "B", "conteudo_md": "# B"}, headers=headers)

    r = client.get("/api/docs/ajuda", headers=headers)
    assert r.status_code == 200
    items = r.json()
    assert isinstance(items, list), f"Expected list, got {type(items)}"
    chaves = [i["chave"] for i in items]
    assert "chave_a" in chaves, f"chave_a not found in list: {chaves}"
    assert "chave_b" in chaves, f"chave_b not found in list: {chaves}"
