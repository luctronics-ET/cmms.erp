"""
Test fixtures for backend tests.

Each test gets a fresh SQLite DB at a tmp path. We force-reimport
`backend.main` per session so the module-level DB_PATH picks up the env var,
then invoke FastAPI's startup hook manually (TestClient does it on enter).
"""
from __future__ import annotations

import importlib
import os
import sys

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def app_client(tmp_path, monkeypatch):
    """Fresh app + DB per test."""
    db_path = tmp_path / "test_core.db"
    monkeypatch.setenv("DB_PATH", str(db_path))
    monkeypatch.setenv("SYNC_AUTH_BYPASS", "1")
    # Reload main to pick up new DB_PATH
    for mod in ("backend.main", "backend.db_core", "backend.grama", "backend.sync", "backend.catalogo"):
        sys.modules.pop(mod, None)
    main = importlib.import_module("backend.main")
    # TestClient triggers startup/shutdown lifespan
    with TestClient(main.app) as client:
        yield client, main
