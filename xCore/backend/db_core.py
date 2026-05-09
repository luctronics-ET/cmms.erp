from __future__ import annotations

import os
import aiosqlite

_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
_SCHEMAS = [
    os.path.join(_DATA_DIR, "schema_core.sql"),
    os.path.join(_DATA_DIR, "schema_grama.sql"),
]


class CoreDB:
    def __init__(self, db_path: str):
        self.db_path = db_path

    async def init(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        async with aiosqlite.connect(self.db_path) as db:
            for schema_path in _SCHEMAS:
                if os.path.exists(schema_path):
                    with open(schema_path) as f:
                        await db.executescript(f.read())
            # Migrações aditivas — adiciona colunas se ainda não existirem
            existing = {row[1] async for row in await db.execute("PRAGMA table_info(ativos)")}
            for col, ddl in [
                ("subtipo", "ALTER TABLE ativos ADD COLUMN subtipo TEXT"),
                ("placa",   "ALTER TABLE ativos ADD COLUMN placa   TEXT"),
            ]:
                if col not in existing:
                    await db.execute(ddl)
            locais_existing = {row[1] async for row in await db.execute("PRAGMA table_info(locais)")}
            for col, ddl in [
                ("neo", "ALTER TABLE locais ADD COLUMN neo TEXT"),
                ("restricao", "ALTER TABLE locais ADD COLUMN restricao TEXT DEFAULT ''"),
                ("estrutura_id", "ALTER TABLE locais ADD COLUMN estrutura_id TEXT REFERENCES estrutura(id)"),
            ]:
                if col not in locais_existing:
                    await db.execute(ddl)
            mov_existing = {row[1] async for row in await db.execute("PRAGMA table_info(estoque_movimentos)")}
            for col, ddl in [
                ("documento",  "ALTER TABLE estoque_movimentos ADD COLUMN documento  TEXT"),
                ("fornecedor", "ALTER TABLE estoque_movimentos ADD COLUMN fornecedor TEXT"),
            ]:
                if col not in mov_existing:
                    await db.execute(ddl)
            await db.commit()

    async def fetch_one(self, sql: str, params=()) -> dict | None:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(sql, params) as cur:
                row = await cur.fetchone()
                return dict(row) if row else None

    async def fetch_all(self, sql: str, params=()) -> list[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(sql, params) as cur:
                rows = await cur.fetchall()
                return [dict(r) for r in rows]

    async def execute(self, sql: str, params=()) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute(sql, params)
            await db.commit()
            return cur.lastrowid

    async def executemany(self, sql: str, data: list) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.executemany(sql, data)
            await db.commit()
