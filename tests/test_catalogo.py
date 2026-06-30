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


def test_list_servicos_baseline_seeded(app_client):
    # startup semeia o catálogo de manutenção; SV001 (de teste) não existe ainda
    client, _ = app_client
    r = client.get("/api/catalogo/servicos")
    assert r.status_code == 200
    codigos = {s["codigo"] for s in r.json()}
    assert "SV001" not in codigos


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
    # Deve aparecer apenas 1 entrada para SV001 (versao mais recente), ignorando seed
    sv001 = [s for s in r.json() if s["codigo"] == "SV001"]
    assert len(sv001) == 1
    assert sv001[0]["versao"] == 2
    assert sv001[0]["nome"] == "Inspecao Visual Atualizada"


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


# ──────────────────────────── Planos (deprecação) ────────────────────────────
#
# /api/catalogo/planos foi APOSENTADO (ver backend/catalogo.py ~318-347).
# Substituído por /api/catalogo/planos-catalogo (modelo catalogo_planos).
# Os testes abaixo documentam o CONTRATO DE DEPRECAÇÃO: GET retorna []
# e qualquer escrita (POST/PUT/PATCH arquivar) retorna 410 Gone.
#
# Para cobertura real de planos, ver testes de /planos-catalogo (a adicionar).
#


def _seed_servico(client, main, codigo="SV001") -> str:
    headers = _auth(main)
    r = client.post("/api/catalogo/servicos", json=_servico_payload(codigo=codigo), headers=headers)
    return r.json()["id"]


def test_planos_deprecated_list_returns_empty(app_client):
    """GET /api/catalogo/planos retorna [] (endpoint aposentado, não 404)."""
    client, _ = app_client
    r = client.get("/api/catalogo/planos")
    assert r.status_code == 200
    assert r.json() == []


def test_planos_deprecated_get_by_id_returns_410(app_client):
    """GET /api/catalogo/planos/{id} retorna 410 Gone."""
    client, _ = app_client
    r = client.get("/api/catalogo/planos/qualquer-id")
    assert r.status_code == 410


def test_planos_deprecated_post_returns_410(app_client):
    """POST /api/catalogo/planos retorna 410 Gone (sem exigir auth primeiro)."""
    client, main = app_client
    headers = _auth(main)
    r = client.post("/api/catalogo/planos", json={"qualquer": "dado"}, headers=headers)
    assert r.status_code == 410


def test_planos_deprecated_put_returns_410(app_client):
    """PUT /api/catalogo/planos/{id} retorna 410 Gone."""
    client, main = app_client
    headers = _auth(main)
    r = client.put("/api/catalogo/planos/qualquer-id", json={"qualquer": "dado"}, headers=headers)
    assert r.status_code == 410


def test_planos_deprecated_arquivar_returns_410(app_client):
    """PATCH /api/catalogo/planos/{id}/arquivar retorna 410 Gone."""
    client, main = app_client
    headers = _auth(main)
    r = client.patch("/api/catalogo/planos/qualquer-id/arquivar", headers=headers)
    assert r.status_code == 410


def test_planos_deprecated_list_ignores_filters(app_client):
    """GET /api/catalogo/planos com filtros ainda retorna [] (não 422)."""
    client, _ = app_client
    r = client.get("/api/catalogo/planos", params={"tipo_codigo": "climatizacao"})
    assert r.status_code == 200
    assert r.json() == []


def test_planos_catalogo_list_smoke(app_client):
    """Smoke: GET /api/catalogo/planos-catalogo existe e retorna lista (pode ser vazia)."""
    client, _ = app_client
    r = client.get("/api/catalogo/planos-catalogo")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


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
