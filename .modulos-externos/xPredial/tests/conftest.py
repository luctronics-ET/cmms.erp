from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path: Path):
    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    db_path = tmp_path / "predial-test.db"
    os.environ["PREDIAL_DB_PATH"] = str(db_path)

    module = importlib.import_module("backend.main")
    module = importlib.reload(module)

    with TestClient(module.app) as c:
        yield c
