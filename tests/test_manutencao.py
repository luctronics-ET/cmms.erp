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


# ──────────────────────────── Fase 04: Equipe Técnica ────────────────────────


def test_equipe_tecnica(app_client):
    """CRUD de membros + config singleton + capacidade derivada para /equipe/*.

    Covers (per IMP-04 plan):
      1. Auth: GET /equipe/membros sem Bearer → 401.
      2. CRUD: POST membro → 201 + id; GET lista contém membro ativo.
      3. Edit: PUT /{id} {especialidade:"X"} → 200; GET reflete mudança.
      4. Soft-delete: PUT /{id} {ativo:0} → 200; ausente do GET default;
         presente em ?incluir_inativos=1; row ainda existe no DB (nunca hard-delete).
      5. Config default: GET /equipe/config em banco limpo →
         capacidade == {h_dia_equipe:4, h_dia_total:4, h_semana:20, h_ano:1040}.
      6. Config save + recompute: PUT /equipe/config {num_equipes:2, 5 dias, turnos 4h+4h}
         → 200 e capacidade == {h_dia_equipe:8, h_dia_total:16, h_semana:80, h_ano:4160};
         re-GET retorna a mesma config + capacidade (persistência singleton id=1).
      7. Capacity independence: adicionar/desativar membros NÃO altera capacidade da config.
    """
    client, main = app_client
    headers = _auth(main)

    # ── 1. Auth: GET sem Bearer → 401 ────────────────────────────────────────
    r_unauth = client.get("/api/manutencao/equipe/membros")
    assert r_unauth.status_code == 401, f"Expected 401, got {r_unauth.status_code}"

    # ── 2. CRUD: POST membro → 201 + id ──────────────────────────────────────
    r_create = client.post(
        "/api/manutencao/equipe/membros",
        json={"nome": "João Silva", "posto_grad": "SGT", "especialidade": "Refrigeração"},
        headers=headers,
    )
    assert r_create.status_code == 201, f"Expected 201, got {r_create.status_code}: {r_create.text}"
    membro_id = r_create.json()["id"]
    assert isinstance(membro_id, int) and membro_id > 0

    # GET default list contains the new member (ativo=1)
    r_list = client.get("/api/manutencao/equipe/membros", headers=headers)
    assert r_list.status_code == 200
    membros = r_list.json()
    found = [m for m in membros if m["id"] == membro_id]
    assert len(found) == 1, f"Membro {membro_id} not found in roster: {membros}"
    assert found[0]["nome"] == "João Silva"
    assert found[0]["posto_grad"] == "SGT"
    assert found[0]["ativo"] == 1

    # ── 3. Edit: PUT /{id} → 200; GET reflete mudança ────────────────────────
    r_edit = client.put(
        f"/api/manutencao/equipe/membros/{membro_id}",
        json={"especialidade": "Elétrica"},
        headers=headers,
    )
    assert r_edit.status_code == 200, f"Expected 200, got {r_edit.status_code}: {r_edit.text}"
    assert r_edit.json().get("ok") is True

    r_after_edit = client.get("/api/manutencao/equipe/membros", headers=headers)
    edited = next(m for m in r_after_edit.json() if m["id"] == membro_id)
    assert edited["especialidade"] == "Elétrica", f"especialidade not updated: {edited}"

    # ── 4. Soft-delete: PUT /{id} {ativo:0} ──────────────────────────────────
    r_delete = client.put(
        f"/api/manutencao/equipe/membros/{membro_id}",
        json={"ativo": 0},
        headers=headers,
    )
    assert r_delete.status_code == 200, f"Expected 200, got {r_delete.status_code}: {r_delete.text}"

    # Absent from default GET (ativo=1 only)
    r_default = client.get("/api/manutencao/equipe/membros", headers=headers)
    ids_ativo = [m["id"] for m in r_default.json()]
    assert membro_id not in ids_ativo, f"Deactivated member {membro_id} still in default list: {ids_ativo}"

    # Present in ?incluir_inativos=1
    r_all = client.get("/api/manutencao/equipe/membros?incluir_inativos=1", headers=headers)
    ids_all = [m["id"] for m in r_all.json()]
    assert membro_id in ids_all, f"Deactivated member {membro_id} missing from incluir_inativos list"

    # Row still exists in DB (never hard-deleted — T-04-05)
    db_rows = _query(main, "SELECT id, ativo FROM equipe_membros WHERE id = ?", (membro_id,))
    assert len(db_rows) == 1, f"Row deleted from DB — must be soft-delete only (T-04-05)"
    assert db_rows[0]["ativo"] == 0, f"Expected ativo=0, got {db_rows[0]['ativo']}"

    # ── 5. Config default: GET /equipe/config em banco limpo ─────────────────
    # (banco é limpo — fixture; equipe_config vazia → defaults do schema)
    r_cfg_default = client.get("/api/manutencao/equipe/config", headers=headers)
    assert r_cfg_default.status_code == 200, f"Expected 200, got {r_cfg_default.status_code}"
    body_default = r_cfg_default.json()
    assert "config" in body_default
    assert "capacidade" in body_default

    cap_default = body_default["capacidade"]
    # Legacy defaults: num_equipes=1, 5 dias, turnos=[2h,2h] → h_dia_equipe=4, h_dia_total=4, h_semana=20, h_ano=1040
    assert cap_default["h_dia_equipe"] == 4, f"h_dia_equipe: expected 4, got {cap_default['h_dia_equipe']}"
    assert cap_default["h_dia_total"] == 4, f"h_dia_total: expected 4, got {cap_default['h_dia_total']}"
    assert cap_default["h_semana"] == 20, f"h_semana: expected 20, got {cap_default['h_semana']}"
    assert cap_default["h_ano"] == 1040, f"h_ano: expected 1040, got {cap_default['h_ano']}"

    # ── 6. Config save + recompute ────────────────────────────────────────────
    # {num_equipes:2, dias_semana:seg-sex (5 dias), turnos:[4h+4h]} →
    # h_dia_equipe=8, h_dia_total=16, h_semana=80, h_ano=4160
    r_put = client.put(
        "/api/manutencao/equipe/config",
        json={
            "num_equipes": 2,
            "dias_semana": ["seg", "ter", "qua", "qui", "sex"],
            "turnos": [{"nome": "Manhã", "horas": 4}, {"nome": "Tarde", "horas": 4}],
        },
        headers=headers,
    )
    assert r_put.status_code == 200, f"Expected 200, got {r_put.status_code}: {r_put.text}"
    body_put = r_put.json()
    cap_put = body_put["capacidade"]
    assert cap_put["h_dia_equipe"] == 8, f"h_dia_equipe: expected 8, got {cap_put['h_dia_equipe']}"
    assert cap_put["h_dia_total"] == 16, f"h_dia_total: expected 16, got {cap_put['h_dia_total']}"
    assert cap_put["h_semana"] == 80, f"h_semana: expected 80, got {cap_put['h_semana']}"
    assert cap_put["h_ano"] == 4160, f"h_ano: expected 4160, got {cap_put['h_ano']}"

    # Re-GET → mesma config + capacidade (persistence singleton id=1)
    r_reget = client.get("/api/manutencao/equipe/config", headers=headers)
    assert r_reget.status_code == 200
    body_reget = r_reget.json()
    cap_reget = body_reget["capacidade"]
    assert cap_reget["h_dia_equipe"] == 8, f"Persisted h_dia_equipe: expected 8, got {cap_reget['h_dia_equipe']}"
    assert cap_reget["h_dia_total"] == 16
    assert cap_reget["h_semana"] == 80
    assert cap_reget["h_ano"] == 4160

    # Verify singleton: exactly 1 row with id=1
    cfg_rows = _query(main, "SELECT id, num_equipes FROM equipe_config")
    assert len(cfg_rows) == 1, f"Expected exactly 1 row in equipe_config, got {len(cfg_rows)}"
    assert cfg_rows[0]["id"] == 1
    assert cfg_rows[0]["num_equipes"] == 2

    # ── 7. Capacity independence from members ─────────────────────────────────
    # Adding another member and deactivating should NOT change config capacidade
    r_new_member = client.post(
        "/api/manutencao/equipe/membros",
        json={"nome": "Maria Souza", "posto_grad": "2ºT", "especialidade": "Elétrica"},
        headers=headers,
    )
    assert r_new_member.status_code == 201
    new_id = r_new_member.json()["id"]

    # Deactivate this member too
    client.put(f"/api/manutencao/equipe/membros/{new_id}", json={"ativo": 0}, headers=headers)

    # Capacidade must still be the same config-only numbers (legacy formula — config-only)
    r_cfg_final = client.get("/api/manutencao/equipe/config", headers=headers)
    cap_final = r_cfg_final.json()["capacidade"]
    assert cap_final["h_dia_equipe"] == 8, "Capacity must not change when members added/deactivated"
    assert cap_final["h_dia_total"] == 16
    assert cap_final["h_semana"] == 80


# ──────────────────────────── Cronograma tests (IMP-05) ──────────────────────


def _seed_cronograma_fixture(main, ativo_ids_crit_tipo: list, cap_h: float = 4.0) -> None:
    """Seed ativos + ativo_plano_estado + equipe_config for cronograma tests.

    ativo_ids_crit_tipo: list of (ativo_id, criticidade, tipo, falta)
      falta = proximo_uso - uso_atual; we set uso_atual=1000 and proximo_uso=1000+falta.
    cap_h: daily capacity in hours (controls cap_dia_min = cap_h * 60).
    """
    import json as _json

    # Seed equipe_config id=1 with Mon–Fri and a single turno of cap_h hours
    dias_json = _json.dumps(["seg", "ter", "qua", "qui", "sex"])
    turnos_json = _json.dumps([{"nome": "Turno", "horas": cap_h}])
    _exec(
        main,
        "INSERT OR REPLACE INTO equipe_config (id, num_equipes, dias_semana, turnos, updated_at) "
        "VALUES (1, 1, ?, ?, datetime('now'))",
        (dias_json, turnos_json),
    )

    # Seed a minimal catalogo_plano_itens entry for plan-state rows
    _exec(
        main,
        "INSERT OR IGNORE INTO catalogo_servicos "
        "(id, codigo, nome, escopo, criado_por_modulo, ativo) "
        "VALUES ('svc-crono', 'PREV', 'Preventiva', 'central', 'manutencao', 1)",
    )
    _exec(
        main,
        "INSERT OR IGNORE INTO catalogo_planos "
        "(id, codigo, nome, categoria, tipo_codigo, ativo, frequencia) "
        "VALUES ('pln-crono', 'PLN', 'Plano Crono', 'climatizacao', 'SPLIT', 1, ?)",
        ('{"tipo":"por_uso","valor":250,"unidade":"h"}',),
    )
    # One plan item per seeding session (shared across assets)
    rows = _query(main, "SELECT id FROM catalogo_plano_itens WHERE plano_id='pln-crono'")
    if not rows:
        _exec(
            main,
            "INSERT INTO catalogo_plano_itens (plano_id, servico_id, seq, classe) "
            "VALUES ('pln-crono', 'svc-crono', 0, 'prev')",
        )
    item_rows = _query(main, "SELECT id FROM catalogo_plano_itens WHERE plano_id='pln-crono'")
    item_id = item_rows[0]["id"]

    for ativo_id, criticidade, tipo, falta in ativo_ids_crit_tipo:
        uso_atual = 1000.0
        proximo_uso = uso_atual + falta

        _exec(
            main,
            "INSERT OR IGNORE INTO ativos "
            "(id, nome, tipo, categoria, uso_atual, unidade_uso, criticidade, ativo) "
            "VALUES (?, ?, ?, 'climatizacao', ?, 'h', ?, 1)",
            (ativo_id, f"AC {ativo_id}", tipo, uso_atual, criticidade),
        )
        _exec(
            main,
            "INSERT OR REPLACE INTO ativo_plano_estado "
            "(ativo_id, catalogo_plano_item_id, ultimo_uso, proximo_uso) "
            "VALUES (?, ?, ?, ?)",
            (ativo_id, item_id, uso_atual - 250, proximo_uso),
        )


def test_cronograma(app_client):
    """GET /cronograma with fixed 3-asset dataset + injected today → exact 2-day packing + KPIs.

    Fixture (RESEARCH "Deterministic Test Dataset"):
      a01  SPLIT  CRÍTICA  falta=-5  → 105 min
      a02  SPLIT  ALTA     falta=10  → 105 min
      a03  JANELA MÉDIA    falta=20  → 57 min
    Crew: Mon–Fri, 4h/day (cap_dia_min=240 min).
    Today: 2026-07-06 (Monday).

    Expected packing:
      Day 1 (2026-07-06 Seg): a01(105) + a02(105) = 210 min (restante=30); a03(57)>30 → overflow
      Day 2 (2026-07-07 Ter): a03(57) = 57 min
    """
    client, main = app_client
    headers = _auth(main)

    _seed_cronograma_fixture(
        main,
        ativo_ids_crit_tipo=[
            ("a01", "CRÍTICA", "SPLIT",  -5.0),
            ("a02", "ALTA",    "SPLIT",   10.0),
            ("a03", "MÉDIA",   "JANELA",  20.0),
        ],
        cap_h=4.0,
    )

    r = client.get(
        "/api/manutencao/cronograma?today=2026-07-06&categoria=climatizacao",
        headers=headers,
    )
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    data = r.json()

    dias = data["dias"]
    kpis = data["kpis"]

    # ── Day structure ────────────────────────────────────────────────────────
    assert len(dias) == 2, f"Expected 2 days, got {len(dias)}: {dias}"

    day0 = dias[0]
    assert day0["data"] == "2026-07-06", f"Day0 date wrong: {day0['data']}"
    assert day0["dia_semana"] == "Seg", f"Day0 dia_semana wrong: {day0['dia_semana']}"
    assert len(day0["itens"]) == 2, f"Day0 should have 2 items: {day0['itens']}"
    assert day0["itens"][0]["ativo_id"] == "a01", "Day0 item0 should be a01 (CRÍTICA)"
    assert day0["itens"][1]["ativo_id"] == "a02", "Day0 item1 should be a02 (ALTA)"

    day1 = dias[1]
    assert day1["data"] == "2026-07-07", f"Day1 date wrong: {day1['data']}"
    assert day1["dia_semana"] == "Ter", f"Day1 dia_semana wrong: {day1['dia_semana']}"
    assert len(day1["itens"]) == 1, f"Day1 should have 1 item: {day1['itens']}"
    assert day1["itens"][0]["ativo_id"] == "a03", "Day1 item0 should be a03 (MÉDIA)"

    # ── Item fields ──────────────────────────────────────────────────────────
    item_a01 = day0["itens"][0]
    assert item_a01["criticidade"] == "CRÍTICA"
    assert item_a01["duracao_min"] == 105
    assert item_a01["status"] == "VENCIDA"   # falta=-5 ≤ 0

    item_a02 = day0["itens"][1]
    assert item_a02["criticidade"] == "ALTA"
    assert item_a02["duracao_min"] == 105
    assert item_a02["status"] == "PRÓXIMA"   # falta=10 > 0

    item_a03 = day1["itens"][0]
    assert item_a03["criticidade"] == "MÉDIA"
    assert item_a03["duracao_min"] == 57
    assert item_a03["status"] == "PRÓXIMA"   # falta=20 > 0

    # ── KPIs (exact values — Python round() with banker's rounding) ──────────
    # total_min = 105 + 105 + 57 = 267; cap_dia_min = 240; dias_uteis = 2
    assert kpis["total_os"] == 3, f"total_os wrong: {kpis}"
    assert kpis["dias_uteis"] == 2, f"dias_uteis wrong: {kpis}"
    assert kpis["data_conclusao"] == "2026-07-07", f"data_conclusao wrong: {kpis}"
    assert kpis["alerta"] is False, f"alerta should be False (267 < 480): {kpis}"

    # horas_pessoa = round(267/60, 1) = round(4.45, 1) = 4.5 (IEEE 754 — 4.45 is slightly > midpoint)
    expected_horas_pessoa = round(267 / 60, 1)
    assert kpis["horas_pessoa"] == expected_horas_pessoa, (
        f"horas_pessoa expected {expected_horas_pessoa}, got {kpis['horas_pessoa']}"
    )

    # pct_utilizacao = round(267 / (240*2) * 100, 1) = round(55.625, 1) = 55.6
    expected_pct = round(267 / (240 * 2) * 100, 1)
    assert kpis["pct_utilizacao"] == expected_pct, (
        f"pct_utilizacao expected {expected_pct}, got {kpis['pct_utilizacao']}"
    )


def test_cronograma_alerta(app_client):
    """GET /cronograma with demand > capacity → kpis.alerta is True.

    Fixture: 3 SELF CONTAINED assets (207 min each = 621 min total).
    Crew: Mon–Fri, 2h/day (cap_dia_min=120 min).
    With cap=120: each asset (207) exceeds daily cap → 3 days used.
    cap_total = 120 × 3 = 360 min.
    alerta = 621 > 360 → True.
    pct_utilizacao = round(621/360*100, 1) = 172.5%.
    """
    client, main = app_client
    headers = _auth(main)

    _seed_cronograma_fixture(
        main,
        ativo_ids_crit_tipo=[
            ("sc01", "ALTA",  "SELF CONTAINED", 5.0),
            ("sc02", "ALTA",  "SELF CONTAINED", 10.0),
            ("sc03", "MÉDIA", "SELF CONTAINED", 15.0),
        ],
        cap_h=2.0,   # 2h/day = 120 min — ensures 207>120 → each asset overflows
    )

    r = client.get(
        "/api/manutencao/cronograma?today=2026-07-06&categoria=climatizacao",
        headers=headers,
    )
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    data = r.json()
    kpis = data["kpis"]

    assert kpis["alerta"] is True, (
        f"alerta should be True when total demand (621 min) exceeds cap_total (360 min): {kpis}"
    )
    assert kpis["total_os"] == 3, f"total_os wrong: {kpis}"


def test_cronograma_requires_auth(app_client):
    """GET /cronograma without Authorization header → 401."""
    client, _main = app_client
    r = client.get("/api/manutencao/cronograma")
    assert r.status_code == 401, f"Expected 401 without auth, got {r.status_code}: {r.text}"


# ──────────────────────────── Fase 06: RES-01 por_tempo vencimentos ──────────


def _seed_por_tempo_plano(main, ativo_id: str = "pt-001", intervalo_dias: int = 90) -> dict:
    """Seeds ativo + catalogo entries for a por_tempo plan.

    Returns dict with keys: ativo_id, servico_id, plano_id, item_id.
    """
    _exec(
        main,
        "INSERT OR IGNORE INTO ativos "
        "(id, nome, tipo, categoria, uso_atual, unidade_uso, ativo) "
        "VALUES (?, ?, 'AC_SPLIT', 'refrigeracao', 0, 'h', 1)",
        (ativo_id, f"Ativo PorTempo {ativo_id}"),
    )

    servico_id = f"svc-pt-{ativo_id}"
    _exec(
        main,
        "INSERT OR IGNORE INTO catalogo_servicos "
        "(id, codigo, nome, escopo, criado_por_modulo, ativo) "
        "VALUES (?, 'LIMP_PT', 'Limpeza PorTempo', 'central', 'manutencao', 1)",
        (servico_id,),
    )

    plano_id = f"pln-pt-{ativo_id}"
    frequencia = f'{{"tipo":"por_tempo","valor":{intervalo_dias},"unidade":"dias"}}'
    _exec(
        main,
        "INSERT OR IGNORE INTO catalogo_planos "
        "(id, codigo, nome, categoria, tipo_codigo, ativo, frequencia) "
        "VALUES (?, 'PT-TEST', 'Plano PorTempo', 'climatizacao', 'AC_SPLIT', 1, ?)",
        (plano_id, frequencia),
    )

    _exec(
        main,
        "INSERT OR IGNORE INTO catalogo_plano_itens "
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


def test_por_tempo_alerta_por_data(app_client):
    """por_tempo plan fires an alert when last execution >= intervalo days ago.

    Seeds a manut_registro dated 91 days ago (past the 90-day interval) and verifies
    that GET /api/manutencao/vencimentos returns an alert entry for this ativo.
    """
    import datetime
    client, main = app_client
    headers = _auth(main)

    ids = _seed_por_tempo_plano(main, ativo_id="pt-002", intervalo_dias=90)
    ativo_id = ids["ativo_id"]

    # Seed a manut_registro 91 days ago (past threshold)
    data_antiga = (datetime.date.today() - datetime.timedelta(days=91)).isoformat()
    _exec(
        main,
        "INSERT INTO manut_registros (ativo_id, responsavel, data, uso_no_momento, itens_json) "
        "VALUES (?, 'Tecnico', ?, 0, '[]')",
        (ativo_id, data_antiga),
    )

    r = client.get("/api/manutencao/vencimentos?categoria=refrigeracao", headers=headers)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    data = r.json()

    # Find alert entry for this ativo
    alertas = [e for e in data if e.get("ativo_id") == ativo_id]
    assert len(alertas) >= 1, (
        f"Expected at least 1 alert for por_tempo ativo {ativo_id} with 91-day-old registro; "
        f"got 0 from response: {data}"
    )
    alerta = alertas[0]
    assert alerta.get("unidade") == "dias", f"Expected unidade='dias', got {alerta}"
    assert "proximo" in alerta, f"por_tempo alert must include 'proximo' key: {alerta}"
    assert "falta" in alerta, f"por_tempo alert must include 'falta' key: {alerta}"


def test_por_tempo_sem_registro_nao_alerta(app_client):
    """por_tempo plan with NO manut_registros does NOT alert and does NOT crash."""
    client, main = app_client
    headers = _auth(main)

    ids = _seed_por_tempo_plano(main, ativo_id="pt-003", intervalo_dias=90)
    ativo_id = ids["ativo_id"]
    # No manut_registros seeded for this ativo

    r = client.get("/api/manutencao/vencimentos?categoria=refrigeracao", headers=headers)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    data = r.json()

    alertas = [e for e in data if e.get("ativo_id") == ativo_id]
    assert len(alertas) == 0, (
        f"Expected 0 alerts for por_tempo ativo with no manut_registros; got {alertas}"
    )


def test_por_tempo_recente_nao_alerta(app_client):
    """por_tempo plan does NOT alert when last execution is recent (well within interval)."""
    import datetime
    client, main = app_client
    headers = _auth(main)

    ids = _seed_por_tempo_plano(main, ativo_id="pt-004", intervalo_dias=90)
    ativo_id = ids["ativo_id"]

    # Seed a registro from just 5 days ago (far from the 90-day threshold)
    data_recente = (datetime.date.today() - datetime.timedelta(days=5)).isoformat()
    _exec(
        main,
        "INSERT INTO manut_registros (ativo_id, responsavel, data, uso_no_momento, itens_json) "
        "VALUES (?, 'Tecnico', ?, 0, '[]')",
        (ativo_id, data_recente),
    )

    r = client.get("/api/manutencao/vencimentos?categoria=refrigeracao", headers=headers)
    assert r.status_code == 200
    data = r.json()

    alertas = [e for e in data if e.get("ativo_id") == ativo_id]
    assert len(alertas) == 0, (
        f"Expected 0 alerts for por_tempo with recent execution (5 days ago / 90-day interval); "
        f"got {alertas}"
    )


def test_por_uso_nao_afetado_por_por_tempo(app_client):
    """por_uso plan remains unaffected when por_tempo branch is added.

    Verifies that a por_uso plan entry:
    - Has unidade != 'dias' (not contaminated by por_tempo branch)
    - Has uso_atual set (por_tempo sets uso_atual=None)
    - Has pct set (por_tempo sets pct=None)
    """
    client, main = app_client
    headers = _auth(main)

    ids = _seed_plano(main, ativo_id="pu-001", uso_inicial=1000.0)
    ativo_id = ids["ativo_id"]

    r = client.get("/api/manutencao/vencimentos", headers=headers)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    data = r.json()

    # por_uso entry: must be present with por_uso-specific fields intact
    por_uso_entries = [e for e in data if e.get("ativo_id") == ativo_id]
    assert len(por_uso_entries) >= 1, f"por_uso entry missing from response: {data}"
    entry = por_uso_entries[0]

    # por_tempo branch must NOT have contaminated this entry
    assert entry.get("unidade") != "dias", (
        f"por_uso entry should not have unidade='dias'; got {entry}"
    )
    assert entry.get("uso_atual") is not None, (
        f"por_uso entry must have uso_atual set (por_tempo sets None); got {entry}"
    )
    assert entry.get("pct") is not None, (
        f"por_uso entry must have pct set (por_tempo sets None); got {entry}"
    )
