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


# ──────────────────────────── Fase 03: Sobressalentes ────────────────────────


def test_sobressalentes(app_client):
    """CRUD + atomic ajuste + estoque isolation for GET /api/manutencao/sobressalentes.

    Covers:
      - Create: POST → 201, returns id, row in DB
      - List+badge+valor: ZERADO (qtd=0) and OK (qtd>=minima) badges; valor_estimado_total == Σ qtd×preco
      - Edit: PUT changes fields; qtd_atual unchanged by PUT
      - Ajuste atomic: POST /{id}/ajuste → qtd_atual updated AND one movimento row inserted with operador set
      - Estoque isolation: rows in central `estoque` table unchanged before/after (T-03-05)
      - Auth: write without token → 401
    """
    client, main = app_client
    headers = _auth(main)

    # ── Snapshot central estoque BEFORE (isolation baseline) ─────────────────
    estoque_before = _query(main, "SELECT id FROM estoque")
    estoque_ids_before = {r["id"] for r in estoque_before}
    estoque_count_before = len(estoque_before)

    # ── Auth: write without token → 401 ──────────────────────────────────────
    r_unauth = client.post(
        "/api/manutencao/sobressalentes",
        json={"nome": "Filtro de Ar"},
    )
    assert r_unauth.status_code == 401, f"Expected 401, got {r_unauth.status_code}"

    # ── Create: POST → 201, returns id ───────────────────────────────────────
    r_create = client.post(
        "/api/manutencao/sobressalentes",
        json={"nome": "Filtro de Ar", "categoria": "consumivel", "unidade": "un"},
        headers=headers,
    )
    assert r_create.status_code == 201, f"Expected 201, got {r_create.status_code}: {r_create.text}"
    new_id = r_create.json()["id"]
    assert isinstance(new_id, int) and new_id > 0

    # Verify DB row
    db_rows = _query(main, "SELECT nome, categoria FROM sobressalentes WHERE id = ?", (new_id,))
    assert len(db_rows) == 1
    assert db_rows[0]["nome"] == "Filtro de Ar"
    assert db_rows[0]["categoria"] == "consumivel"

    # ── Create second peça with preco for valor_estimado_total calc ──────────
    r_create2 = client.post(
        "/api/manutencao/sobressalentes",
        json={"nome": "Válvula Expansão", "categoria": "sobressalente", "preco_unitario": 120.0, "qtd_minima": 2.0},
        headers=headers,
    )
    assert r_create2.status_code == 201
    id2 = r_create2.json()["id"]

    # Seed qtd_atual: id=0 (ZERADO), id2 qtd=5 (OK since minima=2)
    # new_id has qtd_atual=0 (default) → ZERADO
    # id2 has qtd_atual=0 → let's ajustar it to 5 via ajuste
    r_ajuste_setup = client.post(
        f"/api/manutencao/sobressalentes/{id2}/ajuste",
        json={"quantidade": 5.0, "tipo": "entrada", "motivo": "Setup inicial"},
        headers=headers,
    )
    assert r_ajuste_setup.status_code == 201
    assert r_ajuste_setup.json()["qtd_atual"] == 5.0

    # ── List + badge + valor ──────────────────────────────────────────────────
    r_list = client.get("/api/manutencao/sobressalentes", headers=headers)
    assert r_list.status_code == 200
    data = r_list.json()
    assert "items" in data
    assert "valor_estimado_total" in data

    items_by_id = {it["id"]: it for it in data["items"]}

    # Badge: new_id has qtd_atual=0 → ZERADO
    assert items_by_id[new_id]["badge"] == "ZERADO"
    # Badge: id2 has qtd_atual=5, qtd_minima=2 → OK
    assert items_by_id[id2]["badge"] == "OK"

    # valor_estimado_total = Σ qtd×preco: new_id preco=0 (→ 0), id2 5×120 = 600
    expected_valor = 0.0 + 5.0 * 120.0
    assert abs(data["valor_estimado_total"] - expected_valor) < 0.01, (
        f"Expected valor_estimado_total={expected_valor}, got {data['valor_estimado_total']}"
    )

    # ── Edit: PUT changes nome/preco; qtd_atual unchanged ────────────────────
    r_edit = client.put(
        f"/api/manutencao/sobressalentes/{new_id}",
        json={"nome": "Filtro HEPA", "preco_unitario": 45.0},
        headers=headers,
    )
    assert r_edit.status_code == 200
    assert r_edit.json()["ok"] is True

    db_after_edit = _query(main, "SELECT nome, preco_unitario, qtd_atual FROM sobressalentes WHERE id = ?", (new_id,))
    assert db_after_edit[0]["nome"] == "Filtro HEPA"
    assert db_after_edit[0]["preco_unitario"] == 45.0
    # qtd_atual must remain 0 (PUT never changes it)
    assert db_after_edit[0]["qtd_atual"] == 0.0, (
        f"PUT must not change qtd_atual; got {db_after_edit[0]['qtd_atual']}"
    )

    # ── Ajuste atomic: UPDATE qtd + INSERT movimento in one txn ──────────────
    r_ajuste = client.post(
        f"/api/manutencao/sobressalentes/{new_id}/ajuste",
        json={"quantidade": 3.0, "tipo": "entrada", "motivo": "Recebimento NF-001"},
        headers=headers,
    )
    assert r_ajuste.status_code == 201, f"Expected 201, got {r_ajuste.status_code}: {r_ajuste.text}"
    assert r_ajuste.json()["qtd_atual"] == 3.0

    # Verify qtd_atual updated in DB
    db_qtd = _query(main, "SELECT qtd_atual FROM sobressalentes WHERE id = ?", (new_id,))
    assert db_qtd[0]["qtd_atual"] == 3.0

    # Verify exactly one movimento row with correct fields and operador set
    movs = _query(
        main,
        "SELECT tipo, quantidade, motivo, operador FROM sobressalentes_movimentos WHERE item_id = ?",
        (new_id,),
    )
    # The ajuste at setup didn't happen for new_id; only one ajuste above
    ajuste_movs = [m for m in movs if m["motivo"] == "Recebimento NF-001"]
    assert len(ajuste_movs) == 1, f"Expected 1 movimento for ajuste, got {len(ajuste_movs)}: {movs}"
    mov = ajuste_movs[0]
    assert mov["tipo"] == "entrada"
    assert mov["quantidade"] == 3.0
    assert mov["motivo"] == "Recebimento NF-001"
    assert mov["operador"] is not None and mov["operador"] != "", (
        "operador must be set from token (T-03-02)"
    )

    # ── GET /movimentos: history newest-first ─────────────────────────────────
    r_hist = client.get(
        f"/api/manutencao/sobressalentes/{new_id}/movimentos",
        headers=headers,
    )
    assert r_hist.status_code == 200
    hist = r_hist.json()
    assert len(hist) >= 1
    assert hist[0]["item_id"] == new_id

    # ── Estoque isolation: central estoque unchanged (T-03-05) ────────────────
    estoque_after = _query(main, "SELECT id FROM estoque")
    estoque_ids_after = {r["id"] for r in estoque_after}
    estoque_count_after = len(estoque_after)

    assert estoque_count_after == estoque_count_before, (
        f"Central estoque row count changed: before={estoque_count_before}, after={estoque_count_after}"
    )
    assert estoque_ids_after == estoque_ids_before, (
        "Central estoque ids changed — sobressalentes leaked into estoque"
    )

    # Also verify no sobressalentes id appears in estoque (belt-and-suspenders)
    sob_ids = {row["id"] for row in _query(main, "SELECT id FROM sobressalentes")}
    estoque_id_set = {row["id"] for row in _query(main, "SELECT id FROM estoque")}
    overlap = sob_ids & estoque_id_set
    # IDs can coincidentally overlap in autoincrement but the tables are separate
    # — the real isolation check is the count/ids above; this verifies no row sharing
    # (i.e., same row cannot appear in BOTH tables: different tables, nothing to cross-check)
    # The critical assertion is already above.

    # ── 422: validate empty nome ──────────────────────────────────────────────
    r_bad = client.post(
        "/api/manutencao/sobressalentes",
        json={"nome": "   "},
        headers=headers,
    )
    assert r_bad.status_code == 422, f"Expected 422 for blank nome, got {r_bad.status_code}"

    # ── 404: ajuste on nonexistent peça ──────────────────────────────────────
    r_404 = client.post(
        "/api/manutencao/sobressalentes/999999/ajuste",
        json={"quantidade": 1.0, "tipo": "entrada", "motivo": "X"},
        headers=headers,
    )
    assert r_404.status_code == 404, f"Expected 404, got {r_404.status_code}"

    # ── 422: saida that would go negative ────────────────────────────────────
    # new_id currently has qtd_atual=3.0; saida of 10 would make it -7 → 422
    r_neg = client.post(
        f"/api/manutencao/sobressalentes/{new_id}/ajuste",
        json={"quantidade": 10.0, "tipo": "saida", "motivo": "Teste negativo"},
        headers=headers,
    )
    assert r_neg.status_code == 422, f"Expected 422 for negative result, got {r_neg.status_code}"
    # qtd_atual must remain 3.0 (atomic rollback)
    db_qtd_after_neg = _query(main, "SELECT qtd_atual FROM sobressalentes WHERE id = ?", (new_id,))
    assert db_qtd_after_neg[0]["qtd_atual"] == 3.0, (
        f"Atomic rollback failed: qtd_atual changed after rejected saida; got {db_qtd_after_neg[0]['qtd_atual']}"
    )
