def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_full_flow(client):
    local_res = client.post(
        "/api/v1/locais",
        json={"nome": "Predio A", "tipo": "predio", "parent_id": None, "area_m2": 1200},
    )
    assert local_res.status_code == 200
    local_id = local_res.json()["id"]

    create = client.post(
        "/api/v1/inspecoes",
        json={
            "local_id": local_id,
            "titulo": "Inspecao mensal Predio A",
            "data_planejada": "2026-04-25",
            "executante": "Equipe 1",
        },
    )
    assert create.status_code == 200
    inspecao = create.json()
    inspecao_id = inspecao["id"]

    detail = client.get(f"/api/v1/inspecoes/{inspecao_id}")
    assert detail.status_code == 200
    assert len(detail.json()["itens"]) >= 11

    update_item = client.put(
        f"/api/v1/inspecoes/{inspecao_id}/itens",
        json={
            "codigo": "infiltracoes",
            "titulo": "Infiltracoes",
            "condicao": "critico",
            "observacao": "Vazamento no teto corredor",
            "prioridade_reparo": "alta",
        },
    )
    assert update_item.status_code == 200

    t1 = client.put(
        f"/api/v1/inspecoes/{inspecao_id}/status",
        json={"para_status": "em_execucao", "usuario": "executor"},
    )
    assert t1.status_code == 200

    t2 = client.put(
        f"/api/v1/inspecoes/{inspecao_id}/status",
        json={"para_status": "aguardando_aprovacao", "usuario": "executor"},
    )
    assert t2.status_code == 200

    t3 = client.put(
        f"/api/v1/inspecoes/{inspecao_id}/status",
        json={"para_status": "aprovada", "usuario": "aprovador"},
    )
    assert t3.status_code == 200

    t4 = client.put(
        f"/api/v1/inspecoes/{inspecao_id}/status",
        json={"para_status": "concluida", "usuario": "aprovador"},
    )
    assert t4.status_code == 200

    history = client.get("/api/v1/historico")
    assert history.status_code == 200
    assert len(history.json()) >= 1

    summary = client.get("/api/v1/relatorio/resumo")
    assert summary.status_code == 200
    assert "itens_criticos" in summary.json()
