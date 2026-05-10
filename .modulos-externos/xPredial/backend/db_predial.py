from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import aiosqlite

DEFAULT_DB_PATH = Path(__file__).resolve().parents[1] / "data" / "predial.db"
SCHEMA_PATH = Path(__file__).resolve().parents[1] / "database" / "schema_predial.sql"


class PredialDB:
    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH

    async def init(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        schema = SCHEMA_PATH.read_text(encoding="utf-8")
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.executescript(schema)
            # Migrações para locais
            cur = await conn.execute("PRAGMA table_info(locais)")
            cols = {row[1] for row in await cur.fetchall()}
            if "codigo" not in cols:
                await conn.execute("ALTER TABLE locais ADD COLUMN codigo TEXT")
            if "neo" not in cols:
                await conn.execute("ALTER TABLE locais ADD COLUMN neo TEXT")
            if "area" not in cols:
                await conn.execute("ALTER TABLE locais ADD COLUMN area TEXT CHECK(area IS NULL OR area IN ('ADM','OPE','APA'))")
            if "endereco" not in cols:
                await conn.execute("ALTER TABLE locais ADD COLUMN endereco TEXT")
            if "restricao" not in cols:
                await conn.execute(
                    "ALTER TABLE locais ADD COLUMN restricao TEXT CHECK(restricao IS NULL OR restricao IN ('', 'civil', 'militar', 'reservado', 'secreto', 'proibido'))"
                )

            # Migrações para inspecoes
            cur = await conn.execute("PRAGMA table_info(inspecoes)")
            cols = {row[1] for row in await cur.fetchall()}
            if "servico_id" not in cols:
                await conn.execute("ALTER TABLE inspecoes ADD COLUMN servico_id TEXT")
            if "degradacao_desc" not in cols:
                await conn.execute("ALTER TABLE inspecoes ADD COLUMN degradacao_desc TEXT")
            if "perda_desempenho_estimada" not in cols:
                await conn.execute("ALTER TABLE inspecoes ADD COLUMN perda_desempenho_estimada TEXT")
            if "executante_id" not in cols:
                await conn.execute("ALTER TABLE inspecoes ADD COLUMN executante_id INTEGER")

            # Migrações para inspecao_itens
            cur = await conn.execute("PRAGMA table_info(inspecao_itens)")
            cols = {row[1] for row in await cur.fetchall()}
            if "norma_id" not in cols:
                await conn.execute("ALTER TABLE inspecao_itens ADD COLUMN norma_id INTEGER REFERENCES normas(id) ON DELETE SET NULL")

            # Migrações para checklist_template_items
            cur = await conn.execute("PRAGMA table_info(checklist_template_items)")
            cols = {row[1] for row in await cur.fetchall()}
            if "norma_id" not in cols:
                await conn.execute("ALTER TABLE checklist_template_items ADD COLUMN norma_id INTEGER REFERENCES normas(id) ON DELETE SET NULL")

            await conn.execute("CREATE INDEX IF NOT EXISTS idx_locais_codigo ON locais(codigo)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_locais_neo ON locais(neo)")
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

    async def execute_transaction(self, statements: list[tuple[str, tuple[Any, ...]]]) -> None:
        async with aiosqlite.connect(self.db_path) as conn:
            try:
                await conn.execute("BEGIN")
                for query, params in statements:
                    await conn.execute(query, params)
                await conn.commit()
            except sqlite3.Error:
                await conn.rollback()
                raise
