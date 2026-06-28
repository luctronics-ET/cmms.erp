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

import httpx
import pytest
import pytest_asyncio
from asgi_lifespan import LifespanManager
from fastapi.testclient import TestClient


@pytest.fixture
def app_client(tmp_path, monkeypatch):
    """Fresh app + DB per test."""
    db_path = tmp_path / "test_core.db"
    monkeypatch.setenv("DB_PATH", str(db_path))
    # Reload main to pick up new DB_PATH
    for mod in ("backend.main", "backend.db_core", "backend.grama", "backend.sync", "backend.manutencao"):
        sys.modules.pop(mod, None)
    main = importlib.import_module("backend.main")
    # TestClient triggers startup/shutdown lifespan
    with TestClient(main.app) as client:
        yield client, main


@pytest_asyncio.fixture
async def async_app_client(tmp_path, monkeypatch):
    """Async fixture: fresh DB + startup lifespan (db.init()) via LifespanManager."""
    db_path = tmp_path / "test_async_core.db"
    monkeypatch.setenv("DB_PATH", str(db_path))
    # Reload to capture the new DB_PATH (same pattern as sync app_client)
    for mod in ("backend.main", "backend.db_core", "backend.grama", "backend.sync", "backend.manutencao"):
        sys.modules.pop(mod, None)
    main = importlib.import_module("backend.main")
    async with LifespanManager(main.app) as manager:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=manager.app),
            base_url="http://test",
        ) as client:
            yield client, main
