from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import aiosqlite

DEFAULT_DB_PATH = Path(__file__).resolve().parents[1] / "data" / "calibracao.db"
SCHEMA_PATH = Path(__file__).resolve().parents[1] / "database" / "schema_calibracao.sql"


class CalibracaoDB:
    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH

    async def init(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        schema = SCHEMA_PATH.read_text(encoding="utf-8")
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.executescript(schema)
            await conn.commit()

    async def execute(self, query: str, params: tuple[Any, ...] = ()) -> int:
        async with aiosqlite.connect(self.db_path) as conn:
            cur = await conn.execute(query, params)
            await conn.commit()
            return cur.lastrowid

    async def fetch_all(self, query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cur = await conn.execute(query, params)
            rows = await cur.fetchall()
            return [dict(row) for row in rows]

    async def fetch_one(self, query: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cur = await conn.execute(query, params)
            row = await cur.fetchone()
            return dict(row) if row else None
