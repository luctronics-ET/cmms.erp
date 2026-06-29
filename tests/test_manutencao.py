"""Tests for GET /api/manutencao/plano-ativo and POST /api/manutencao/registro (IMP-02).

Covers:
  - test_plano_no_ativo        : anti-double-count invariant (advances uso between two POSTs)
  - test_registro_exige_responsavel : 422 on blank/missing responsavel; zero audit rows
  - test_registro_atomico      : 422 on bad item_id; zero rows in BOTH tables (atomic rollback)
  - test_plano_ativo_requires_auth  : 401 without Bearer token
"""
from __future__ import annotations

import sqlite3
import uuid


# ──────────────────────────── DB helpers (copied from test_catalogo.py) ───────


def _query(main, sql, params=()):
    """Consulta síncrona ao DB de teste."""
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


# ──────────────────────────── auth helpers ────────────────────────────────────


def _seed_user(main) -> int:
    """Insere usuário mínimo no DB de teste e retorna o id."""
    _exec(
        main,
        "INSERT OR IGNORE INTO usuarios (id, nome, mat, pw_hash, role, ativo) "
        "VALUES (1, 'Admin', '000001', 'hash', 'admin', 1)",
    )
    return 1


def _seed_sessao(main, uid: int = 1) -> str:
    """Insere sessão válida e retorna o token."""
    token = "test-token-123"
    _exec(
        main,
        "INSERT OR IGNORE INTO sessoes (token, usuario_id, expira_em) "
        "VALUES (?, ?, datetime('now', '+8 hours'))",
        (token, uid),
    )
    return token


def _auth(main) -> dict:
    uid = _seed_user(main)
    token = _seed_sessao(main, uid)
    return {"Authorization": f"Bearer {token}"}


# ──────────────────────────── seed helper ────────────────────────────────────


def _seed_plano(main, ativo_id: str = "ativo-001", uso_inicial: float = 1000.0) -> dict:
    """Seeds ativo + catalogo entries and returns IDs.

    Returns dict with keys: ativo_id, servico_id, plano_id, item_id.

    Plano frequência = {"tipo":"por_uso","valor":250,"unidade":"h"} (item inherits plan default).
    ativo tipo = 'AC_SPLIT', matching plano tipo_codigo.
    """
    # Ativo
    _exec(
        main,
        "INSERT OR IGNORE INTO ativos "
        "(id, nome, tipo, categoria, uso_atual, unidade_uso, ativo) "
        "VALUES (?, ?, 'AC_SPLIT', 'refrigeracao', ?, 'h', 1)",
        (ativo_id, f"Split Teste {ativo_id}", uso_inicial),
    )

    # Serviço
    servico_id = str(uuid.uuid4())
    _exec(
        main,
        "INSERT INTO catalogo_servicos "
        "(id, codigo, nome, escopo, criado_por_modulo, ativo) "
        "VALUES (?, 'LIMP_SPLIT', 'Limpeza Split', 'central', 'manutencao', 1)",
        (servico_id,),
    )

    # Plano (frequência default do pacote; item sem override herda esse valor)
    plano_id = str(uuid.uuid4())
    _exec(
        main,
        "INSERT INTO catalogo_planos "
        "(id, codigo, nome, categoria, tipo_codigo, ativo, frequencia) "
        "VALUES (?, 'G-TEST', 'Plano Teste AC_SPLIT', 'climatizacao', 'AC_SPLIT', 1, ?)",
        (plano_id, '{"tipo":"por_uso","valor":250,"unidade":"h"}'),
    )

    # Item do plano (frequencia=NULL → herda do plano)
    _exec(
        main,
        "INSERT INTO catalogo_plano_itens "
        "(plano_id, servico_id, seq, classe) "
        "VALUES (?, ?, 0, 'prev')",
        (plano_id, servico_id),
    )

    rows = _query(main, "SELECT id FROM catalogo_plano_itens WHERE plano_id = ?", (plano_id,))
    item_id = rows[0]["id"]

    return {
        "ativo_id": ativo_id,
        "servico_id": servico_id,
        "plano_id": plano_id,
        "item_id": item_id,
    }


# ──────────────────────────── Tests ──────────────────────────────────────────


def test_plano_no_ativo(app_client):
    """GET returns plan with status; POST advances proximo_uso; anti-double-count proven."""
    client, main = app_client
    headers = _auth(main)
    ids = _seed_plano(main, ativo_id="ativo-001", uso_inicial=1000.0)
    ativo_id = ids["ativo_id"]
    item_id = ids["item_id"]

    # ── GET returns items with status fields ──────────────────────────────────
    r = client.get(f"/api/manutencao/plano-ativo?ativo_id={ativo_id}", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["ativo_id"] == ativo_id
    assert data["uso_atual"] == 1000.0
    assert len(data["itens"]) >= 1
    item = next(i for i in data["itens"] if i["item_id"] == item_id)
    assert item["status"] in ("VENCIDA", "URGENTE", "PROXIMA", "EM_DIA")
    assert item["falta"] is not None
    assert item["pct"] is not None
    assert item["por_tempo"] is False

    # ── POST 1: uso=1000 → proximo_uso should be 1000 + 250 = 1250 ──────────
    r1 = client.post(
        "/api/manutencao/registro",
        json={"ativo_id": ativo_id, "responsavel": "Técnico A", "itens": [item_id]},
        headers=headers,
    )
    assert r1.status_code == 201
    assert r1.json()["ok"] is True

    estado1 = _query(
        main,
        "SELECT proximo_uso FROM ativo_plano_estado WHERE ativo_id=? AND catalogo_plano_item_id=?",
        (ativo_id, item_id),
    )
    assert len(estado1) == 1
    assert estado1[0]["proximo_uso"] == 1250.0, f"Expected 1250, got {estado1[0]['proximo_uso']}"

    # ── EXPLICIT uso advance: UPDATE to 1100 (MANDATORY — proves invariant not trivially idempotent)
    _exec(main, "UPDATE ativos SET uso_atual=1100 WHERE id=?", (ativo_id,))

    # ── POST 2: uso=1100 → proximo_uso should be 1100 + 250 = 1350 (NOT 1000+2×250=1500)
    r2 = client.post(
        "/api/manutencao/registro",
        json={"ativo_id": ativo_id, "responsavel": "Técnico A", "itens": [item_id]},
        headers=headers,
    )
    assert r2.status_code == 201

    estado2 = _query(
        main,
        "SELECT proximo_uso FROM ativo_plano_estado WHERE ativo_id=? AND catalogo_plano_item_id=?",
        (ativo_id, item_id),
    )
    assert estado2[0]["proximo_uso"] == 1350.0, (
        f"Anti-double-count FAILED: expected 1350 (uso_at_second_registration=1100 + iv=250), "
        f"got {estado2[0]['proximo_uso']}. If 1500 was returned, proximo_uso accumulated instead of resetting."
    )

    # ── Atomicity: exactly 2 audit rows for this ativo (one per successful POST)
    audit_rows = _query(main, "SELECT id FROM manut_registros WHERE ativo_id=?", (ativo_id,))
    assert len(audit_rows) == 2, f"Expected 2 audit rows, got {len(audit_rows)}"


def test_registro_exige_responsavel(app_client):
    """POST with blank or missing responsavel returns 422; zero audit rows written."""
    client, main = app_client
    headers = _auth(main)
    ids = _seed_plano(main, ativo_id="ativo-002", uso_inicial=500.0)
    ativo_id = ids["ativo_id"]
    item_id = ids["item_id"]

    # Blank responsavel (RegistroIn.resp_nao_vazio validator)
    r1 = client.post(
        "/api/manutencao/registro",
        json={"ativo_id": ativo_id, "responsavel": "", "itens": [item_id]},
        headers=headers,
    )
    assert r1.status_code == 422, f"Expected 422, got {r1.status_code}"

    # Missing responsavel key entirely
    r2 = client.post(
        "/api/manutencao/registro",
        json={"ativo_id": ativo_id, "itens": [item_id]},
        headers=headers,
    )
    assert r2.status_code == 422, f"Expected 422, got {r2.status_code}"

    # Whitespace-only responsavel
    r3 = client.post(
        "/api/manutencao/registro",
        json={"ativo_id": ativo_id, "responsavel": "   ", "itens": [item_id]},
        headers=headers,
    )
    assert r3.status_code == 422, f"Expected 422, got {r3.status_code}"

    # Zero audit rows written (rejected payloads must leave no audit row)
    audit_rows = _query(main, "SELECT id FROM manut_registros WHERE ativo_id=?", (ativo_id,))
    assert len(audit_rows) == 0, f"Rejected payloads should not write audit rows; got {len(audit_rows)}"


def test_registro_atomico(app_client):
    """POST with nonexistent item_id returns 422; zero rows in BOTH tables (atomic rollback)."""
    client, main = app_client
    headers = _auth(main)
    ids = _seed_plano(main, ativo_id="ativo-003", uso_inicial=200.0)
    ativo_id = ids["ativo_id"]

    nonexistent_item_id = 999999  # certainly does not exist

    r = client.post(
        "/api/manutencao/registro",
        json={"ativo_id": ativo_id, "responsavel": "Técnico B", "itens": [nonexistent_item_id]},
        headers=headers,
    )
    assert r.status_code == 422, f"Expected 422, got {r.status_code}"

    # Atomic rollback: no partial audit row
    audit_rows = _query(main, "SELECT id FROM manut_registros WHERE ativo_id=?", (ativo_id,))
    assert len(audit_rows) == 0, f"Atomic rollback FAILED: found {len(audit_rows)} audit rows"

    # Atomic rollback: no partial estado upsert
    estado_rows = _query(
        main,
        "SELECT ativo_id FROM ativo_plano_estado WHERE ativo_id=?",
        (ativo_id,),
    )
    assert len(estado_rows) == 0, f"Atomic rollback FAILED: found {len(estado_rows)} estado rows"


def test_plano_ativo_requires_auth(app_client):
    """GET /plano-ativo without Bearer token returns 401."""
    client, main = app_client
    ids = _seed_plano(main, ativo_id="ativo-004", uso_inicial=100.0)
    r = client.get(f"/api/manutencao/plano-ativo?ativo_id={ids['ativo_id']}")
    assert r.status_code == 401, f"Expected 401, got {r.status_code}"
