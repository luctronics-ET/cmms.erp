"""
Garante que db.init() pode ser chamado duas vezes no mesmo banco sem erro.
Verifica que CREATE TABLE IF NOT EXISTS + PRAGMA migrations são idempotentes.
Satisfaz QA-02: esquema carrega do zero e é idempotente (sem "duplicate column name").
"""
from __future__ import annotations

import importlib
import sys

import pytest


@pytest.fixture
def fresh_db(tmp_path, monkeypatch):
    """CoreDB inicializado em um DB temporário isolado."""
    db_path = tmp_path / "idempotencia.db"
    monkeypatch.setenv("DB_PATH", str(db_path))
    for mod in ("backend.main", "backend.db_core", "backend.grama",
                "backend.sync", "backend.manutencao"):
        sys.modules.pop(mod, None)
    db_core = importlib.import_module("backend.db_core")
    return db_core.CoreDB(str(db_path))


async def test_init_twice_sem_erro(fresh_db):
    """Roda db.init() duas vezes no mesmo banco — nenhuma exceção deve ser lançada."""
    await fresh_db.init()
    await fresh_db.init()  # segunda chamada deve ser silenciosa


async def test_uso_registros_criada_apos_init(fresh_db):
    """Confirma que uso_registros existe após init() e tem as colunas esperadas."""
    await fresh_db.init()
    cols = {r["name"] for r in await fresh_db.fetch_all("PRAGMA table_info(uso_registros)")}
    assert "id" in cols
    assert "ativo_id" in cols
    assert "delta" in cols
    assert "valor_anterior" in cols
    assert "valor_novo" in cols
    assert "data" in cols
    assert "operador" in cols
