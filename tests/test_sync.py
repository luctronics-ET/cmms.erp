"""Tests for /api/sync/* and /api/modulos endpoints."""
from __future__ import annotations

import sqlite3


def _query(main, sql, params=()):
    """Consulta síncrona ao DB de teste (TestClient gerencia seu próprio loop async)."""
    conn = sqlite3.connect(main.db.db_path)
    conn.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


def test_list_modulos_returns_seeded_pmocs(app_client):
    client, _ = app_client
    r = client.get("/api/modulos")
    assert r.status_code == 200
    data = r.json()
    nomes = sorted(m["nome"] for m in data)
    assert nomes == [
        "pmoc_calibracao",
        "pmoc_eletrica",
        "pmoc_grama",
        "pmoc_paiois",
        "pmoc_predial",
        "pmoc_refrigeracao",
        "pmoc_transportes",
    ]


def test_list_modulos_parses_categorias_atend_as_list(app_client):
    client, _ = app_client
    r = client.get("/api/modulos")
    refrig = next(m for m in r.json() if m["nome"] == "pmoc_refrigeracao")
    assert refrig["categorias_atend"] == ["climatizacao"]
    transp = next(m for m in r.json() if m["nome"] == "pmoc_transportes")
    assert set(transp["categorias_atend"]) == {"frota_terrestre", "frota_naval"}


# ────────────────────────── /api/sync/cursor ──────────────────────────


def test_cursor_returns_null_when_no_record(app_client):
    client, _ = app_client
    r = client.get("/api/sync/cursor", params={"modulo": "pmoc_refrigeracao", "device": "dev-A"})
    assert r.status_code == 200
    assert r.json() == {
        "modulo": "pmoc_refrigeracao",
        "device_id": "dev-A",
        "ultimo_evento_id": None,
        "ultimo_push_em": None,
        "ultimo_pull_em": None,
    }


def test_cursor_requires_modulo_and_device(app_client):
    client, _ = app_client
    r = client.get("/api/sync/cursor", params={"modulo": "pmoc_refrigeracao"})
    assert r.status_code == 422  # FastAPI validation


def test_cursor_rejects_unknown_modulo(app_client):
    client, _ = app_client
    r = client.get("/api/sync/cursor", params={"modulo": "naoexiste", "device": "dev-A"})
    assert r.status_code == 404


# ────────────────────────── /api/sync/push ──────────────────────────


def _push_body(eventos, modulo="pmoc_refrigeracao", device="dev-A"):
    return {"modulo": modulo, "device_id": device, "eventos": eventos}


def _evento(eid, tipo="plano_adiado", payload=None, ts="2026-05-18T10:00:00"):
    """Helper default usa `plano_adiado` (auditoria, sem precondições de FK)."""
    return {"id": eid, "tipo": tipo, "ts": ts, "payload": payload or {}}


def test_push_empty_eventos_returns_empty_aceitos(app_client):
    client, _ = app_client
    r = client.post("/api/sync/push", json=_push_body(eventos=[]))
    assert r.status_code == 200
    body = r.json()
    assert body["aceitos"] == []
    assert body["rejeitados"] == []
    assert "cursor" in body


def test_push_stores_valid_event_and_returns_in_aceitos(app_client):
    client, main = app_client
    eid = "00000000-0000-0000-0000-000000000001"
    r = client.post("/api/sync/push", json=_push_body([
        _evento(eid, "plano_adiado", {"plano_id": "p-X", "motivo": "chuva"})
    ]))
    assert r.status_code == 200
    assert r.json()["aceitos"] == [eid]
    rows = _query(main, "SELECT tipo, status FROM sync_eventos WHERE id=?", (eid,))
    assert rows == [{"tipo": "plano_adiado", "status": "processado"}]


def test_push_is_idempotent_on_same_event_id(app_client):
    client, main = app_client
    eid = "00000000-0000-0000-0000-000000000002"
    payload = _evento(eid, "plano_adiado", {"plano_id": "p-Y"})
    r1 = client.post("/api/sync/push", json=_push_body([payload]))
    r2 = client.post("/api/sync/push", json=_push_body([payload]))
    assert r1.json()["aceitos"] == [eid]
    assert r2.json()["aceitos"] == [eid]  # ainda retorna como aceito (idempotente)
    rows = _query(main, "SELECT id FROM sync_eventos WHERE id=?", (eid,))
    assert len(rows) == 1


def test_push_rejects_unknown_event_tipo(app_client):
    client, _ = app_client
    eid = "00000000-0000-0000-0000-000000000003"
    r = client.post("/api/sync/push", json=_push_body([
        {"id": eid, "tipo": "tipo_inexistente", "ts": "2026-05-18T10:00:00", "payload": {}}
    ]))
    assert r.status_code == 200
    body = r.json()
    assert body["aceitos"] == []
    assert len(body["rejeitados"]) == 1
    assert body["rejeitados"][0]["id"] == eid
    assert "tipo" in body["rejeitados"][0]["motivo"].lower()


def test_push_updates_sync_cursor(app_client):
    client, _ = app_client
    eid = "00000000-0000-0000-0000-000000000004"
    client.post("/api/sync/push", json=_push_body([_evento(eid)]))
    r = client.get("/api/sync/cursor", params={"modulo": "pmoc_refrigeracao", "device": "dev-A"})
    body = r.json()
    assert body["ultimo_evento_id"] == eid
    assert body["ultimo_push_em"] is not None


def test_push_rejects_unknown_modulo(app_client):
    client, _ = app_client
    r = client.post("/api/sync/push", json={
        "modulo": "naoexiste", "device_id": "dev-A", "eventos": []
    })
    assert r.status_code == 404


# ────────────────────────── /api/sync/manifest ──────────────────────────


def _exec(main, sql, params=()):
    conn = sqlite3.connect(main.db.db_path)
    try:
        conn.execute(sql, params)
        conn.commit()
    finally:
        conn.close()


def test_manifest_rejects_unknown_modulo(app_client):
    client, _ = app_client
    r = client.get("/api/sync/manifest", params={"modulo": "naoexiste"})
    assert r.status_code == 404


def test_manifest_returns_required_keys(app_client):
    client, _ = app_client
    r = client.get("/api/sync/manifest", params={"modulo": "pmoc_refrigeracao"})
    assert r.status_code == 200
    body = r.json()
    for key in [
        "updated_at",
        "ativos",
        "usuarios",
        "estoque_catalogo",
        "catalogo_servicos",
        "planos_manutencao",
        "qualificacoes_catalogo",
        "documentos_pop",
        "locais",
    ]:
        assert key in body, f"manifest faltando '{key}'"
    # Núcleo recém-iniciado: qualificações já têm seed
    codigos = {q["codigo"] for q in body["qualificacoes_catalogo"]}
    assert "tec_refrig" in codigos


def test_manifest_filters_ativos_by_modulo_categorias(app_client):
    client, main = app_client
    # Seed: 2 ativos, um de climatização (relevante p/ pmoc_refrigeracao), outro não
    _exec(main, "INSERT INTO ativos (id, tipo, categoria, nome, ativo) VALUES (?, ?, ?, ?, 1)",
          ("a-clim-1", "AC_SPLIT", "climatizacao", "AC Sala 1"))
    _exec(main, "INSERT INTO ativos (id, tipo, categoria, nome, ativo) VALUES (?, ?, ?, ?, 1)",
          ("a-vtr-1", "VTR_PICKUP", "frota_terrestre", "S-10"))
    r = client.get("/api/sync/manifest", params={"modulo": "pmoc_refrigeracao"})
    ativos_ids = {a["id"] for a in r.json()["ativos"]}
    assert "a-clim-1" in ativos_ids
    assert "a-vtr-1" not in ativos_ids


def test_manifest_filters_catalogo_servicos_by_aplicavel_a(app_client):
    client, main = app_client
    # Serviço aplicável só a climatização
    _exec(main,
        "INSERT INTO catalogo_servicos (id, codigo, nome, escopo, versao, aplicavel_a) "
        "VALUES (?, ?, ?, 'central', 1, ?)",
        ("s1", "LIMP_SPLIT", "Limpeza", '{"categorias":["climatizacao"]}'))
    # Serviço aplicável só a frota
    _exec(main,
        "INSERT INTO catalogo_servicos (id, codigo, nome, escopo, versao, aplicavel_a) "
        "VALUES (?, ?, ?, 'central', 1, ?)",
        ("s2", "TROCA_OLEO", "Troca de óleo", '{"categorias":["frota_terrestre"]}'))
    r = client.get("/api/sync/manifest", params={"modulo": "pmoc_refrigeracao"})
    cods = {s["codigo"] for s in r.json()["catalogo_servicos"]}
    assert "LIMP_SPLIT" in cods
    assert "TROCA_OLEO" not in cods


def test_manifest_excludes_local_scope_servicos(app_client):
    client, main = app_client
    # Serviço LOCAL não deve aparecer no manifest (Rules.md §10)
    _exec(main,
        "INSERT INTO catalogo_servicos (id, codigo, nome, escopo, versao, aplicavel_a) "
        "VALUES (?, ?, ?, 'local', 1, ?)",
        ("s-local", "LIMP_LOCAL", "Local", '{"categorias":["climatizacao"]}'))
    r = client.get("/api/sync/manifest", params={"modulo": "pmoc_refrigeracao"})
    cods = {s["codigo"] for s in r.json()["catalogo_servicos"]}
    assert "LIMP_LOCAL" not in cods


def test_manifest_includes_planos_for_module_ativos(app_client):
    client, main = app_client
    _exec(main, "INSERT INTO ativos (id, tipo, categoria, nome, ativo) VALUES (?, ?, ?, ?, 1)",
          ("a-clim-2", "AC_SPLIT", "climatizacao", "AC 2"))
    _exec(main,
        "INSERT INTO catalogo_servicos (id, codigo, nome, escopo, versao) "
        "VALUES (?, ?, ?, 'central', 1)",
        ("s-clim", "LIMP", "Limp"))
    _exec(main,
        "INSERT INTO planos_manutencao (id, servico_id, ativo_id, frequencia) "
        "VALUES (?, ?, ?, ?)",
        ("p1", "s-clim", "a-clim-2", '{"tipo":"periodica","valor":"P1M"}'))
    r = client.get("/api/sync/manifest", params={"modulo": "pmoc_refrigeracao"})
    plano_ids = {p["id"] for p in r.json()["planos_manutencao"]}
    assert "p1" in plano_ids
