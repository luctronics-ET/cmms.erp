"""Endpoint /api/catalogo/planos-climatizacao — rota + SQL (DB de teste vazio)."""


def test_lista_vazia_ok(app_client):
    client, _ = app_client
    r = client.get("/api/catalogo/planos-climatizacao")
    assert r.status_code == 200
    assert isinstance(r.json(), list)   # vazio em DB de teste (import é manual)


def test_filtros_aceitos(app_client):
    client, _ = app_client
    r = client.get("/api/catalogo/planos-climatizacao", params={"btu": 18000, "inverter": 0, "tipo": "AC_SPLIT"})
    assert r.status_code == 200


def test_plano_inexistente_404(app_client):
    client, _ = app_client
    r = client.get("/api/catalogo/planos-climatizacao/nao-existe")
    assert r.status_code == 404
