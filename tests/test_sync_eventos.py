"""
Tests para o processamento de side-effects dos eventos canônicos.

Cada evento aceito deve produzir o efeito documentado em
MODULOS_EXTERNOS.md §3.4. Eventos com erro de domínio (FK inexistente,
delta inválido, etc.) vão para `rejeitados` e gravam status='rejeitado'.
"""
from __future__ import annotations

import sqlite3
import uuid


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


def _push(client, eventos, modulo="pmoc_refrigeracao", device="dev-A"):
    return client.post("/api/sync/push", json={
        "modulo": modulo, "device_id": device, "eventos": eventos,
    })


def _ev(tipo, payload, eid=None, ts="2026-05-18T10:00:00"):
    return {"id": eid or str(uuid.uuid4()), "tipo": tipo, "ts": ts, "payload": payload}


# ────────────────────────── uso_atual_inc ──────────────────────────


def test_uso_atual_inc_atualiza_ativo(app_client):
    client, main = app_client
    _exec(main, "INSERT INTO ativos (id, tipo, categoria, nome, uso_atual, ativo) "
                "VALUES ('a1', 'AC_SPLIT', 'climatizacao', 'AC 1', 100, 1)")
    r = _push(client, [_ev("uso_atual_inc", {"ativo_id": "a1", "delta": 25.5})])
    assert r.status_code == 200
    assert len(r.json()["aceitos"]) == 1
    rows = _query(main, "SELECT uso_atual FROM ativos WHERE id=?", ("a1",))
    assert rows[0]["uso_atual"] == 125.5


def test_uso_atual_inc_rejeita_ativo_inexistente(app_client):
    client, main = app_client
    eid = str(uuid.uuid4())
    r = _push(client, [_ev("uso_atual_inc", {"ativo_id": "naoexiste", "delta": 5}, eid=eid)])
    body = r.json()
    assert body["aceitos"] == []
    assert len(body["rejeitados"]) == 1
    assert "ativo" in body["rejeitados"][0]["motivo"].lower()
    rows = _query(main, "SELECT status, motivo_rejeicao FROM sync_eventos WHERE id=?", (eid,))
    assert rows[0]["status"] == "rejeitado"
    assert rows[0]["motivo_rejeicao"]


def test_uso_atual_inc_rejeita_delta_negativo(app_client):
    client, main = app_client
    _exec(main, "INSERT INTO ativos (id, tipo, categoria, nome, uso_atual, ativo) "
                "VALUES ('a2', 'AC_SPLIT', 'climatizacao', 'AC 2', 100, 1)")
    r = _push(client, [_ev("uso_atual_inc", {"ativo_id": "a2", "delta": -5})])
    body = r.json()
    assert body["aceitos"] == []
    assert "delta" in body["rejeitados"][0]["motivo"].lower()
    # Ativo não foi alterado
    rows = _query(main, "SELECT uso_atual FROM ativos WHERE id=?", ("a2",))
    assert rows[0]["uso_atual"] == 100


def test_uso_atual_inc_rejeita_ativo_arquivado(app_client):
    client, main = app_client
    _exec(main, "INSERT INTO ativos (id, tipo, categoria, nome, uso_atual, ativo) "
                "VALUES ('a3', 'AC_SPLIT', 'climatizacao', 'AC 3', 50, 0)")
    r = _push(client, [_ev("uso_atual_inc", {"ativo_id": "a3", "delta": 10})])
    assert r.json()["aceitos"] == []
    assert "arquivado" in r.json()["rejeitados"][0]["motivo"].lower()


def test_uso_atual_inc_idempotente_nao_aplica_duas_vezes(app_client):
    client, main = app_client
    _exec(main, "INSERT INTO ativos (id, tipo, categoria, nome, uso_atual, ativo) "
                "VALUES ('a4', 'AC_SPLIT', 'climatizacao', 'AC 4', 0, 1)")
    eid = str(uuid.uuid4())
    _push(client, [_ev("uso_atual_inc", {"ativo_id": "a4", "delta": 7}, eid=eid)])
    _push(client, [_ev("uso_atual_inc", {"ativo_id": "a4", "delta": 7}, eid=eid)])
    rows = _query(main, "SELECT uso_atual FROM ativos WHERE id=?", ("a4",))
    assert rows[0]["uso_atual"] == 7  # não duplicou


# ────────────────────────── estoque_mov ──────────────────────────


def _seed_item(main, item_id=1, nome="Óleo SAE 30", qtd=100, qtd_min=10):
    _exec(main, "INSERT INTO estoque (id, codigo, nome, unidade, qtd_atual, qtd_minima, ativo) "
                "VALUES (?, ?, ?, 'L', ?, ?, 1)",
          (item_id, f"COD-{item_id}", nome, qtd, qtd_min))


def test_estoque_mov_saida_decrementa_qtd(app_client):
    client, main = app_client
    _seed_item(main, item_id=10, qtd=50)
    r = _push(client, [_ev("estoque_mov", {
        "item_id": 10, "tipo": "saida", "quantidade": 15, "obs": "consumo OS-1"
    })])
    assert r.json()["aceitos"] and not r.json()["rejeitados"]
    rows = _query(main, "SELECT qtd_atual FROM estoque WHERE id=10")
    assert rows[0]["qtd_atual"] == 35
    movs = _query(main, "SELECT tipo, quantidade, obs FROM estoque_movimentos WHERE item_id=10")
    assert movs == [{"tipo": "saida", "quantidade": 15, "obs": "consumo OS-1"}]


def test_estoque_mov_entrada_incrementa_qtd(app_client):
    client, main = app_client
    _seed_item(main, item_id=11, qtd=20)
    _push(client, [_ev("estoque_mov", {"item_id": 11, "tipo": "entrada", "quantidade": 30})])
    rows = _query(main, "SELECT qtd_atual FROM estoque WHERE id=11")
    assert rows[0]["qtd_atual"] == 50


def test_estoque_mov_ajuste_seta_valor(app_client):
    client, main = app_client
    _seed_item(main, item_id=12, qtd=75)
    _push(client, [_ev("estoque_mov", {"item_id": 12, "tipo": "ajuste", "quantidade": 100})])
    rows = _query(main, "SELECT qtd_atual FROM estoque WHERE id=12")
    assert rows[0]["qtd_atual"] == 100  # ajuste = valor absoluto


def test_estoque_mov_rejeita_item_inexistente(app_client):
    client, _ = app_client
    r = _push(client, [_ev("estoque_mov", {"item_id": 999, "tipo": "saida", "quantidade": 1})])
    assert r.json()["aceitos"] == []
    assert "item" in r.json()["rejeitados"][0]["motivo"].lower()


def test_estoque_mov_rejeita_saida_que_zera_negativo(app_client):
    client, main = app_client
    _seed_item(main, item_id=13, qtd=5)
    r = _push(client, [_ev("estoque_mov", {"item_id": 13, "tipo": "saida", "quantidade": 10})])
    assert r.json()["aceitos"] == []
    assert "negativ" in r.json()["rejeitados"][0]["motivo"].lower()
    rows = _query(main, "SELECT qtd_atual FROM estoque WHERE id=13")
    assert rows[0]["qtd_atual"] == 5  # inalterado


def test_estoque_mov_rejeita_tipo_invalido(app_client):
    client, main = app_client
    _seed_item(main, item_id=14)
    r = _push(client, [_ev("estoque_mov", {"item_id": 14, "tipo": "voodoo", "quantidade": 1})])
    assert r.json()["aceitos"] == []
    assert "tipo" in r.json()["rejeitados"][0]["motivo"].lower()


# ────────────────────────── documento_anexo ──────────────────────────


def test_documento_anexo_insere_documento(app_client):
    client, main = app_client
    doc_id = str(uuid.uuid4())
    r = _push(client, [_ev("documento_anexo", {
        "id": doc_id,
        "nome": "Foto AC após limpeza",
        "tipo": "foto",
        "mime": "image/jpeg",
        "vinculo_tipo": "os",
        "vinculo_id": "os-123",
        "sha256": "abc123",
    })])
    assert r.json()["aceitos"] and not r.json()["rejeitados"]
    rows = _query(main, "SELECT nome, tipo, vinculo_tipo, vinculo_id, sha256 FROM documentos WHERE id=?", (doc_id,))
    assert rows == [{
        "nome": "Foto AC após limpeza", "tipo": "foto",
        "vinculo_tipo": "os", "vinculo_id": "os-123", "sha256": "abc123",
    }]


def test_documento_anexo_rejeita_sem_nome(app_client):
    client, _ = app_client
    r = _push(client, [_ev("documento_anexo", {"id": str(uuid.uuid4()), "tipo": "foto"})])
    assert r.json()["aceitos"] == []
    assert "nome" in r.json()["rejeitados"][0]["motivo"].lower()


# ────────────────────────── os_criada ──────────────────────────


def _seed_usuario(main, uid=1, nome="Op", mat="0001"):
    _exec(main, "INSERT INTO usuarios (id, nome, mat, ativo) VALUES (?, ?, ?, 1)",
          (uid, nome, mat))


def test_os_criada_insere_ordem_servico(app_client):
    client, main = app_client
    _exec(main, "INSERT INTO ativos (id, tipo, categoria, nome, ativo) "
                "VALUES ('aOS', 'AC_SPLIT', 'climatizacao', 'AC', 1)")
    _seed_usuario(main, uid=10)
    os_id = str(uuid.uuid4())
    r = _push(client, [_ev("os_criada", {
        "id": os_id,
        "codigo": "OS-001",
        "titulo": "Limpeza AC sala 201",
        "tipo": "preventiva",
        "prioridade": "media",
        "ativo_id": "aOS",
        "solicitante_id": 10,
    })])
    assert r.json()["aceitos"] and not r.json()["rejeitados"]
    rows = _query(main, "SELECT titulo, tipo, status, modulo_origem FROM ordens_servico WHERE id=?", (os_id,))
    assert rows == [{
        "titulo": "Limpeza AC sala 201", "tipo": "preventiva",
        "status": "aberta", "modulo_origem": "pmoc_refrigeracao",
    }]
    # Histórico inicial registrado
    hist = _query(main, "SELECT status_de, status_para FROM os_historico WHERE os_id=?", (os_id,))
    assert hist == [{"status_de": None, "status_para": "aberta"}]


def test_os_criada_rejeita_titulo_ausente(app_client):
    client, _ = app_client
    r = _push(client, [_ev("os_criada", {"id": str(uuid.uuid4()), "tipo": "corretiva"})])
    assert r.json()["aceitos"] == []
    assert "titulo" in r.json()["rejeitados"][0]["motivo"].lower()


def test_os_criada_rejeita_ativo_inexistente(app_client):
    client, _ = app_client
    r = _push(client, [_ev("os_criada", {
        "id": str(uuid.uuid4()), "titulo": "X", "ativo_id": "fantasma"
    })])
    assert r.json()["aceitos"] == []
    assert "ativo" in r.json()["rejeitados"][0]["motivo"].lower()


# ────────────────────────── os_status ──────────────────────────


def test_os_status_atualiza_e_registra_historico(app_client):
    client, main = app_client
    _exec(main, "INSERT INTO ordens_servico (id, codigo, titulo, status, tipo, modulo_origem) "
                "VALUES ('os-1', 'OS-001', 'X', 'aberta', 'corretiva', 'manual')")
    r = _push(client, [_ev("os_status", {
        "os_id": "os-1", "status_para": "em_execucao", "obs": "iniciado por João"
    })])
    assert r.json()["aceitos"] and not r.json()["rejeitados"]
    rows = _query(main, "SELECT status FROM ordens_servico WHERE id='os-1'")
    assert rows[0]["status"] == "em_execucao"
    hist = _query(main, "SELECT status_de, status_para, obs FROM os_historico WHERE os_id='os-1'")
    assert hist[-1] == {"status_de": "aberta", "status_para": "em_execucao", "obs": "iniciado por João"}


def test_os_status_rejeita_os_inexistente(app_client):
    client, _ = app_client
    r = _push(client, [_ev("os_status", {"os_id": "fantasma", "status_para": "concluida"})])
    assert r.json()["aceitos"] == []
    assert "os" in r.json()["rejeitados"][0]["motivo"].lower()


def test_os_status_rejeita_status_invalido(app_client):
    client, main = app_client
    _exec(main, "INSERT INTO ordens_servico (id, codigo, titulo, status, tipo, modulo_origem) "
                "VALUES ('os-2', 'OS-002', 'X', 'aberta', 'corretiva', 'manual')")
    r = _push(client, [_ev("os_status", {"os_id": "os-2", "status_para": "voodoo"})])
    assert r.json()["aceitos"] == []
    assert "status" in r.json()["rejeitados"][0]["motivo"].lower()


def test_os_criada_persiste_ativo_id_e_servico(app_client):
    client, main = app_client
    _exec(main, "INSERT INTO ativos (id, tipo, categoria, nome, ativo) "
                "VALUES ('a-os-2', 'AC_SPLIT', 'climatizacao', 'AC', 1)")
    _exec(main, "INSERT INTO catalogo_servicos (id, codigo, nome, escopo, versao) "
                "VALUES ('s-ref', 'LIMP', 'Limp', 'central', 3)")
    os_id = str(uuid.uuid4())
    r = _push(client, [_ev("os_criada", {
        "id": os_id, "titulo": "Limpeza", "ativo_id": "a-os-2",
        "servico_id": "s-ref", "servico_versao_snapshot": 3,
    })])
    assert r.json()["aceitos"] == [_id for _id in r.json()["aceitos"]] and not r.json()["rejeitados"]
    rows = _query(main, "SELECT ativo_id, servico_id, servico_versao_snapshot FROM ordens_servico WHERE id=?", (os_id,))
    assert rows == [{"ativo_id": "a-os-2", "servico_id": "s-ref", "servico_versao_snapshot": 3}]


# ────────────────────────── ps_criada ──────────────────────────


def test_ps_criada_armazena_snapshot_de_servico_local(app_client):
    client, main = app_client
    _exec(main, "INSERT INTO ativos (id, tipo, categoria, nome, ativo) "
                "VALUES ('a-ps', 'AC_SPLIT', 'climatizacao', 'AC', 1)")
    ps_id = str(uuid.uuid4())
    snapshot = {
        "codigo": "LIMP_LOCAL_X",
        "nome": "Limpeza caso especial",
        "versao": 1,
        "escopo": "local",
        "materiais": [{"nome_livre": "Detergente", "qtd": 1, "unidade": "L"}],
        "pessoal": [{"qualificacao": "tec_refrig", "qtd": 1}],
    }
    r = _push(client, [_ev("ps_criada", {
        "id": ps_id,
        "titulo": "Limpeza especial AC",
        "ativo_id": "a-ps",
        "tipo": "preventiva",
        "servico_id": None,
        "servico_snapshot": snapshot,
    })])
    assert r.json()["aceitos"] and not r.json()["rejeitados"]
    import json as _json
    rows = _query(main, "SELECT titulo, ativo_id, servico_snapshot, status FROM ordens_servico WHERE id=?", (ps_id,))
    assert rows[0]["titulo"] == "Limpeza especial AC"
    assert rows[0]["ativo_id"] == "a-ps"
    assert rows[0]["status"] == "aberta"
    assert _json.loads(rows[0]["servico_snapshot"]) == snapshot


def test_ps_criada_aceita_referencia_a_servico_central(app_client):
    client, main = app_client
    _exec(main, "INSERT INTO catalogo_servicos (id, codigo, nome, escopo, versao) "
                "VALUES ('sc1', 'LIMP', 'Limp', 'central', 2)")
    ps_id = str(uuid.uuid4())
    r = _push(client, [_ev("ps_criada", {
        "id": ps_id, "titulo": "Manutenção mensal",
        "servico_id": "sc1", "servico_versao_snapshot": 2,
    })])
    assert r.json()["aceitos"] and not r.json()["rejeitados"]
    rows = _query(main, "SELECT servico_id, servico_versao_snapshot, servico_snapshot FROM ordens_servico WHERE id=?", (ps_id,))
    assert rows == [{"servico_id": "sc1", "servico_versao_snapshot": 2, "servico_snapshot": None}]


def test_ps_criada_rejeita_sem_servico_nem_snapshot(app_client):
    client, _ = app_client
    r = _push(client, [_ev("ps_criada", {
        "id": str(uuid.uuid4()), "titulo": "T"
    })])
    assert r.json()["aceitos"] == []
    assert "servico" in r.json()["rejeitados"][0]["motivo"].lower()


# ────────────────────────── os_executada ──────────────────────────


def test_os_executada_move_status_para_pronto(app_client):
    client, main = app_client
    _exec(main, "INSERT INTO ordens_servico (id, codigo, titulo, status, tipo, modulo_origem) "
                "VALUES ('os-exec', 'OS-X', 'T', 'em_execucao', 'preventiva', 'pmoc_refrigeracao')")
    r = _push(client, [_ev("os_executada", {
        "os_id": "os-exec",
        "hora_inicio": "08:00",
        "hora_fim": "10:30",
        "observacoes": "tudo ok",
    })])
    assert r.json()["aceitos"] and not r.json()["rejeitados"]
    rows = _query(main, "SELECT status, hora_inicio, hora_fim FROM ordens_servico WHERE id='os-exec'")
    assert rows[0] == {"status": "pronto", "hora_inicio": "08:00", "hora_fim": "10:30"}


def test_os_executada_baixa_materiais_usados(app_client):
    client, main = app_client
    _exec(main, "INSERT INTO ordens_servico (id, codigo, titulo, status, tipo, modulo_origem) "
                "VALUES ('os-mat', 'OS-Y', 'T', 'em_execucao', 'preventiva', 'pmoc_refrigeracao')")
    _seed_item(main, item_id=20, qtd=10)
    _seed_item(main, item_id=21, qtd=5)
    r = _push(client, [_ev("os_executada", {
        "os_id": "os-mat",
        "materiais_usados": [
            {"item_id": 20, "qtd": 3},
            {"item_id": 21, "qtd": 2},
        ],
    })])
    assert r.json()["aceitos"] and not r.json()["rejeitados"]
    assert _query(main, "SELECT qtd_atual FROM estoque WHERE id=20")[0]["qtd_atual"] == 7
    assert _query(main, "SELECT qtd_atual FROM estoque WHERE id=21")[0]["qtd_atual"] == 3
    movs = _query(main, "SELECT item_id, tipo, quantidade, os_id FROM estoque_movimentos WHERE os_id='os-mat' ORDER BY item_id")
    assert movs == [
        {"item_id": 20, "tipo": "saida", "quantidade": 3, "os_id": "os-mat"},
        {"item_id": 21, "tipo": "saida", "quantidade": 2, "os_id": "os-mat"},
    ]


def test_os_executada_rejeita_material_insuficiente_sem_efeito(app_client):
    client, main = app_client
    _exec(main, "INSERT INTO ordens_servico (id, codigo, titulo, status, tipo, modulo_origem) "
                "VALUES ('os-fail', 'OS-Z', 'T', 'em_execucao', 'preventiva', 'pmoc_refrigeracao')")
    _seed_item(main, item_id=30, qtd=2)
    r = _push(client, [_ev("os_executada", {
        "os_id": "os-fail",
        "materiais_usados": [{"item_id": 30, "qtd": 5}],
    })])
    assert r.json()["aceitos"] == []
    assert "negativ" in r.json()["rejeitados"][0]["motivo"].lower()
    # Estoque NÃO foi alterado, status NÃO foi alterado
    assert _query(main, "SELECT qtd_atual FROM estoque WHERE id=30")[0]["qtd_atual"] == 2
    assert _query(main, "SELECT status FROM ordens_servico WHERE id='os-fail'")[0]["status"] == "em_execucao"


def test_os_executada_rejeita_os_inexistente(app_client):
    client, _ = app_client
    r = _push(client, [_ev("os_executada", {"os_id": "fantasma"})])
    assert r.json()["aceitos"] == []


def test_os_executada_agrega_consumo_repetido_do_mesmo_item(app_client):
    """Dois lançamentos do mesmo item_id devem ser somados na checagem de saldo."""
    client, main = app_client
    _exec(main, "INSERT INTO ordens_servico (id, codigo, titulo, status, tipo, modulo_origem) "
                "VALUES ('os-agg', 'O-A', 'T', 'em_execucao', 'preventiva', 'pmoc_refrigeracao')")
    _seed_item(main, item_id=40, qtd=3)
    # Duas entradas de 2 cada → total 4 > saldo 3 → rejeita ANTES de aplicar nada
    r = _push(client, [_ev("os_executada", {
        "os_id": "os-agg",
        "materiais_usados": [{"item_id": 40, "qtd": 2}, {"item_id": 40, "qtd": 2}],
    })])
    assert r.json()["aceitos"] == []
    assert "negativ" in r.json()["rejeitados"][0]["motivo"].lower()
    assert _query(main, "SELECT qtd_atual FROM estoque WHERE id=40")[0]["qtd_atual"] == 3


# ────────────────────────── inspecao_concluida ──────────────────────────


def test_inspecao_concluida_marca_os_como_concluida(app_client):
    client, main = app_client
    _exec(main, "INSERT INTO ordens_servico (id, codigo, titulo, status, tipo, modulo_origem) "
                "VALUES ('insp-1', 'INS-1', 'Inspeção mensal', 'em_execucao', 'inspecao', 'pmoc_refrigeracao')")
    r = _push(client, [_ev("inspecao_concluida", {
        "os_id": "insp-1", "observacoes": "tudo conforme"
    })])
    assert r.json()["aceitos"] and not r.json()["rejeitados"]
    rows = _query(main, "SELECT status FROM ordens_servico WHERE id='insp-1'")
    assert rows[0]["status"] == "concluida"


def test_inspecao_concluida_rejeita_se_tipo_nao_for_inspecao(app_client):
    client, main = app_client
    _exec(main, "INSERT INTO ordens_servico (id, codigo, titulo, status, tipo, modulo_origem) "
                "VALUES ('os-corr', 'C-1', 'X', 'em_execucao', 'corretiva', 'manual')")
    r = _push(client, [_ev("inspecao_concluida", {"os_id": "os-corr"})])
    assert r.json()["aceitos"] == []
    assert "inspec" in r.json()["rejeitados"][0]["motivo"].lower()
