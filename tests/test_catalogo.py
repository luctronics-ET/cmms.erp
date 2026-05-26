"""Tests for /api/catalogo/* endpoints (serviços, planos, qualificações, usuário-qualificações)."""
from __future__ import annotations

import sqlite3


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


# ──────────────────────────── helpers ────────────────────────────────────────


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


def _servico_payload(**kwargs):
    base = {
        "codigo": "SV001",
        "nome": "Inspecao Visual",
        "escopo": "central",
        "criado_por_modulo": "manutencao",
    }
    base.update(kwargs)
    return base


# ──────────────────────────── Serviços ───────────────────────────────────────


def test_list_servicos_empty(app_client):
    client, _ = app_client
    r = client.get("/api/catalogo/servicos")
    assert r.status_code == 200
    assert r.json() == []


def test_create_servico_requires_auth(app_client):
    client, _ = app_client
    r = client.post("/api/catalogo/servicos", json=_servico_payload())
    assert r.status_code == 401


def test_create_servico_success(app_client):
    client, main = app_client
    headers = _auth(main)
    r = client.post("/api/catalogo/servicos", json=_servico_payload(), headers=headers)
    assert r.status_code == 201
    data = r.json()
    assert data["codigo"] == "SV001"
    assert data["versao"] == 1
    assert data["ativo"] == 1


def test_create_servico_duplicate_codigo_rejected(app_client):
    client, main = app_client
    headers = _auth(main)
    client.post("/api/catalogo/servicos", json=_servico_payload(), headers=headers)
    r = client.post("/api/catalogo/servicos", json=_servico_payload(), headers=headers)
    assert r.status_code == 409


def test_list_servicos_shows_latest_version_only(app_client):
    client, main = app_client
    headers = _auth(main)
    r1 = client.post("/api/catalogo/servicos", json=_servico_payload(), headers=headers)
    sid = r1.json()["id"]
    # PUT cria versão 2
    client.put(
        f"/api/catalogo/servicos/{sid}",
        json=_servico_payload(nome="Inspecao Visual Atualizada"),
        headers=headers,
    )
    r = client.get("/api/catalogo/servicos")
    data = r.json()
    # Deve aparecer apenas 1 entrada (versao mais recente)
    assert len(data) == 1
    assert data[0]["versao"] == 2
    assert data[0]["nome"] == "Inspecao Visual Atualizada"


def test_put_servico_creates_new_version(app_client):
    client, main = app_client
    headers = _auth(main)
    r1 = client.post("/api/catalogo/servicos", json=_servico_payload(), headers=headers)
    sid = r1.json()["id"]
    r2 = client.put(
        f"/api/catalogo/servicos/{sid}",
        json=_servico_payload(nome="Atualizado"),
        headers=headers,
    )
    assert r2.status_code == 200
    new_data = r2.json()
    assert new_data["versao"] == 2
    assert new_data["id"] != sid  # novo UUID

    # Versão antiga ainda existe no DB
    rows = _query(main, "SELECT versao FROM catalogo_servicos WHERE codigo = 'SV001' ORDER BY versao")
    assert [r["versao"] for r in rows] == [1, 2]


def test_get_servico_by_id(app_client):
    client, main = app_client
    headers = _auth(main)
    r1 = client.post("/api/catalogo/servicos", json=_servico_payload(), headers=headers)
    sid = r1.json()["id"]
    r = client.get(f"/api/catalogo/servicos/{sid}")
    assert r.status_code == 200
    assert r.json()["id"] == sid


def test_get_servico_not_found(app_client):
    client, _ = app_client
    r = client.get("/api/catalogo/servicos/naoexiste")
    assert r.status_code == 404


def test_arquivar_servico(app_client):
    client, main = app_client
    headers = _auth(main)
    r1 = client.post("/api/catalogo/servicos", json=_servico_payload(), headers=headers)
    sid = r1.json()["id"]
    r = client.patch(f"/api/catalogo/servicos/{sid}/arquivar", headers=headers)
    assert r.status_code == 200
    assert r.json() == {"ok": True}
    # Deve sumir do listing padrão (ativo=1)
    r_list = client.get("/api/catalogo/servicos")
    assert all(s["id"] != sid for s in r_list.json())


def test_servico_filtro_escopo(app_client):
    client, main = app_client
    headers = _auth(main)
    client.post("/api/catalogo/servicos", json=_servico_payload(codigo="SV001", escopo="central"), headers=headers)
    client.post("/api/catalogo/servicos", json=_servico_payload(codigo="SV002", escopo="local"), headers=headers)
    r = client.get("/api/catalogo/servicos", params={"escopo": "local"})
    data = r.json()
    assert len(data) == 1
    assert data[0]["codigo"] == "SV002"


def test_servico_aplicavel_a_parsed_as_dict(app_client):
    client, main = app_client
    headers = _auth(main)
    payload = _servico_payload(aplicavel_a={"categorias": ["climatizacao"]})
    r = client.post("/api/catalogo/servicos", json=payload, headers=headers)
    assert r.status_code == 201
    assert r.json()["aplicavel_a"] == {"categorias": ["climatizacao"]}


# ──────────────────────────── Planos ─────────────────────────────────────────


def _seed_servico(client, main, codigo="SV001") -> str:
    headers = _auth(main)
    r = client.post("/api/catalogo/servicos", json=_servico_payload(codigo=codigo), headers=headers)
    return r.json()["id"]


def _plano_payload(servico_id: str, **kwargs) -> dict:
    base = {
        "servico_id": servico_id,
        "tipo_codigo": "climatizacao",
        "frequencia": {"tipo": "periodica", "valor": "P1M"},
        "criado_por_modulo": "pmoc_refrigeracao",
    }
    base.update(kwargs)
    return base


def test_list_planos_empty(app_client):
    client, _ = app_client
    r = client.get("/api/catalogo/planos")
    assert r.status_code == 200
    assert r.json() == []


def test_create_plano_requires_auth(app_client):
    client, main = app_client
    sid = _seed_servico(client, main)
    r = client.post("/api/catalogo/planos", json=_plano_payload(sid))
    assert r.status_code == 401


def test_create_plano_success_with_tipo_codigo(app_client):
    client, main = app_client
    headers = _auth(main)
    sid = _seed_servico(client, main)
    r = client.post("/api/catalogo/planos", json=_plano_payload(sid), headers=headers)
    assert r.status_code == 201
    data = r.json()
    assert data["tipo_codigo"] == "climatizacao"
    assert data["ativo_id"] is None


def test_create_plano_success_with_ativo_id(app_client):
    client, main = app_client
    headers = _auth(main)
    # Insere ativo direto no DB
    _exec(
        main,
        "INSERT INTO ativos (id, nome, categoria, tipo) VALUES ('ativo-1', 'Ar-cond Central', 'climatizacao', 'split')",
    )
    sid = _seed_servico(client, main)
    r = client.post(
        "/api/catalogo/planos",
        json=_plano_payload(sid, ativo_id="ativo-1", tipo_codigo=None),
        headers=headers,
    )
    assert r.status_code == 201
    assert r.json()["ativo_id"] == "ativo-1"


def test_create_plano_xor_constraint_neither(app_client):
    client, main = app_client
    headers = _auth(main)
    sid = _seed_servico(client, main)
    payload = _plano_payload(sid)
    del payload["tipo_codigo"]  # sem ativo_id nem tipo_codigo
    r = client.post("/api/catalogo/planos", json=payload, headers=headers)
    assert r.status_code == 422


def test_create_plano_xor_constraint_both(app_client):
    client, main = app_client
    headers = _auth(main)
    _exec(
        main,
        "INSERT INTO ativos (id, nome, categoria, tipo) VALUES ('ativo-2', 'Bomba', 'hidraulica', 'bomba')",
    )
    sid = _seed_servico(client, main)
    r = client.post(
        "/api/catalogo/planos",
        json=_plano_payload(sid, ativo_id="ativo-2"),  # tem tipo_codigo E ativo_id
        headers=headers,
    )
    assert r.status_code == 422


def test_create_plano_invalid_servico_fk(app_client):
    client, main = app_client
    headers = _auth(main)
    r = client.post(
        "/api/catalogo/planos",
        json=_plano_payload("naoexiste-id"),
        headers=headers,
    )
    assert r.status_code == 404


def test_create_plano_invalid_ativo_fk(app_client):
    client, main = app_client
    headers = _auth(main)
    sid = _seed_servico(client, main)
    r = client.post(
        "/api/catalogo/planos",
        json=_plano_payload(sid, ativo_id="naoexiste", tipo_codigo=None),
        headers=headers,
    )
    assert r.status_code == 404


def test_update_plano(app_client):
    client, main = app_client
    headers = _auth(main)
    sid = _seed_servico(client, main)
    r1 = client.post("/api/catalogo/planos", json=_plano_payload(sid), headers=headers)
    pid = r1.json()["id"]
    updated = _plano_payload(sid, obs="revisado")
    r2 = client.put(f"/api/catalogo/planos/{pid}", json=updated, headers=headers)
    assert r2.status_code == 200
    assert r2.json()["obs"] == "revisado"


def test_arquivar_plano(app_client):
    client, main = app_client
    headers = _auth(main)
    sid = _seed_servico(client, main)
    r1 = client.post("/api/catalogo/planos", json=_plano_payload(sid), headers=headers)
    pid = r1.json()["id"]
    r = client.patch(f"/api/catalogo/planos/{pid}/arquivar", headers=headers)
    assert r.status_code == 200
    # Não aparece no listing padrão
    r_list = client.get("/api/catalogo/planos")
    assert all(p["id"] != pid for p in r_list.json())


def test_list_planos_filter_by_tipo_codigo(app_client):
    client, main = app_client
    headers = _auth(main)
    sid = _seed_servico(client, main)
    client.post("/api/catalogo/planos", json=_plano_payload(sid, tipo_codigo="climatizacao"), headers=headers)
    # Segundo serviço + plano diferente
    sid2 = _seed_servico(client, main, codigo="SV002")
    client.post("/api/catalogo/planos", json=_plano_payload(sid2, tipo_codigo="predial"), headers=headers)

    r = client.get("/api/catalogo/planos", params={"tipo_codigo": "predial"})
    data = r.json()
    assert len(data) == 1
    assert data[0]["tipo_codigo"] == "predial"


# ──────────────────────────── Qualificações ──────────────────────────────────


def _qual_payload(**kwargs):
    base = {"codigo": "NR10", "nome": "NR-10 Segurança em Instalações Elétricas", "requer_validade": 1}
    base.update(kwargs)
    return base


def test_list_qualificacoes_returns_seeded(app_client):
    """Schema semeia 8 qualificações."""
    client, _ = app_client
    r = client.get("/api/catalogo/qualificacoes")
    assert r.status_code == 200
    assert len(r.json()) >= 8


def test_create_qualificacao_requires_auth(app_client):
    client, _ = app_client
    r = client.post("/api/catalogo/qualificacoes", json=_qual_payload(codigo="NOVO"))
    assert r.status_code == 401


def test_create_qualificacao_success(app_client):
    client, main = app_client
    headers = _auth(main)
    r = client.post("/api/catalogo/qualificacoes", json=_qual_payload(codigo="CERT_NOVO"), headers=headers)
    assert r.status_code == 201
    assert r.json()["codigo"] == "CERT_NOVO"


def test_create_qualificacao_duplicate_rejected(app_client):
    client, main = app_client
    headers = _auth(main)
    client.post("/api/catalogo/qualificacoes", json=_qual_payload(codigo="DUP"), headers=headers)
    r = client.post("/api/catalogo/qualificacoes", json=_qual_payload(codigo="DUP"), headers=headers)
    assert r.status_code == 409


def test_update_qualificacao(app_client):
    client, main = app_client
    headers = _auth(main)
    client.post("/api/catalogo/qualificacoes", json=_qual_payload(codigo="Q1"), headers=headers)
    r = client.put(
        "/api/catalogo/qualificacoes/Q1",
        json=_qual_payload(codigo="Q1", nome="Nome Atualizado"),
        headers=headers,
    )
    assert r.status_code == 200
    assert r.json()["nome"] == "Nome Atualizado"


def test_get_qualificacao_not_found(app_client):
    client, _ = app_client
    r = client.get("/api/catalogo/qualificacoes/NAOEXISTE")
    assert r.status_code == 404


# ──────────────────────────── Usuário-Qualificações ──────────────────────────


def _seed_qualificacao(main, codigo="CERT_TEST"):
    _exec(
        main,
        "INSERT OR IGNORE INTO qualificacoes_catalogo (codigo, nome, requer_validade, ativo) "
        "VALUES (?, 'Certificação Teste', 1, 1)",
        (codigo,),
    )
    return codigo


def test_list_usuario_qualificacoes_empty(app_client):
    client, main = app_client
    _seed_user(main)
    r = client.get("/api/catalogo/usuarios/1/qualificacoes")
    assert r.status_code == 200
    assert r.json() == []


def test_list_usuario_qualificacoes_unknown_user(app_client):
    client, _ = app_client
    r = client.get("/api/catalogo/usuarios/9999/qualificacoes")
    assert r.status_code == 404


def test_add_usuario_qualificacao_requires_auth(app_client):
    client, main = app_client
    _seed_user(main)
    qual = _seed_qualificacao(main)
    r = client.post(
        "/api/catalogo/usuarios/1/qualificacoes",
        json={"qualificacao_codigo": qual, "status": "valida"},
    )
    assert r.status_code == 401


def test_add_usuario_qualificacao_success(app_client):
    client, main = app_client
    headers = _auth(main)
    qual = _seed_qualificacao(main)
    r = client.post(
        "/api/catalogo/usuarios/1/qualificacoes",
        json={"qualificacao_codigo": qual, "status": "valida"},
        headers=headers,
    )
    assert r.status_code == 201
    assert r.json()["qualificacao_codigo"] == qual
    assert r.json()["qualificacao_nome"] == "Certificação Teste"


def test_add_usuario_qualificacao_duplicate_rejected(app_client):
    client, main = app_client
    headers = _auth(main)
    qual = _seed_qualificacao(main)
    client.post(
        "/api/catalogo/usuarios/1/qualificacoes",
        json={"qualificacao_codigo": qual, "status": "valida"},
        headers=headers,
    )
    r = client.post(
        "/api/catalogo/usuarios/1/qualificacoes",
        json={"qualificacao_codigo": qual, "status": "valida"},
        headers=headers,
    )
    assert r.status_code == 409


def test_add_usuario_qualificacao_invalid_status(app_client):
    client, main = app_client
    headers = _auth(main)
    qual = _seed_qualificacao(main)
    r = client.post(
        "/api/catalogo/usuarios/1/qualificacoes",
        json={"qualificacao_codigo": qual, "status": "invalido"},
        headers=headers,
    )
    assert r.status_code == 422


def test_update_usuario_qualificacao(app_client):
    client, main = app_client
    headers = _auth(main)
    qual = _seed_qualificacao(main)
    client.post(
        "/api/catalogo/usuarios/1/qualificacoes",
        json={"qualificacao_codigo": qual, "status": "valida"},
        headers=headers,
    )
    r = client.put(
        f"/api/catalogo/usuarios/1/qualificacoes/{qual}",
        json={"qualificacao_codigo": qual, "status": "vencida", "obs": "venceu em jan"},
        headers=headers,
    )
    assert r.status_code == 200
    assert r.json()["status"] == "vencida"


def test_delete_usuario_qualificacao(app_client):
    client, main = app_client
    headers = _auth(main)
    qual = _seed_qualificacao(main)
    client.post(
        "/api/catalogo/usuarios/1/qualificacoes",
        json={"qualificacao_codigo": qual, "status": "valida"},
        headers=headers,
    )
    r = client.delete(f"/api/catalogo/usuarios/1/qualificacoes/{qual}", headers=headers)
    assert r.status_code == 200
    assert r.json() == {"ok": True}

    r_list = client.get("/api/catalogo/usuarios/1/qualificacoes")
    assert r_list.json() == []


def test_delete_usuario_qualificacao_not_found(app_client):
    client, main = app_client
    headers = _auth(main)
    _seed_user(main)
    r = client.delete("/api/catalogo/usuarios/1/qualificacoes/NAOEXISTE", headers=headers)
    assert r.status_code == 404


# ──────────────────────────── Auth rejeita token inválido ────────────────────


def test_write_endpoints_reject_invalid_token(app_client):
    """Garante que endpoints de escrita retornam 401 com token falso."""
    client, main = app_client
    headers = {"Authorization": "Bearer token-falso"}
    sid = _seed_servico(client, main)  # usa auth válida internamente
    assert client.post("/api/catalogo/servicos", json=_servico_payload(codigo="X"), headers=headers).status_code == 401
    assert client.put(f"/api/catalogo/servicos/{sid}", json=_servico_payload(), headers=headers).status_code == 401
    assert client.patch(f"/api/catalogo/servicos/{sid}/arquivar", headers=headers).status_code == 401
