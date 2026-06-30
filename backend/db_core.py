from __future__ import annotations

import os
import aiosqlite

_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
_SCHEMAS = [
    os.path.join(_DATA_DIR, "schema_core.sql"),
    os.path.join(_DATA_DIR, "schema_grama.sql"),
    os.path.join(_DATA_DIR, "schema_catalogo.sql"),
    os.path.join(_DATA_DIR, "schema_manutencao.sql"),   # fase 01 — uso_registros
    os.path.join(_DATA_DIR, "schema_docs.sql"),          # fase 08 — ajuda + documentos
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
                # núcleo magro v2 — campos exigidos pelo motor de manutenção (Rules.md §15)
                ("criticidade",       "ALTER TABLE ativos ADD COLUMN criticidade TEXT DEFAULT 'operacional'"),
                ("responsavel_pmoc",  "ALTER TABLE ativos ADD COLUMN responsavel_pmoc TEXT"),
                ("janela_default",    "ALTER TABLE ativos ADD COLUMN janela_default TEXT"),
                # RES-03 — local onde o ativo está instalado (backfill via tools/backfill_local_id.py)
                ("local_id", "ALTER TABLE ativos ADD COLUMN local_id INTEGER REFERENCES locais(id)"),
            ]:
                if col not in existing:
                    await db.execute(ddl)
            locais_existing = {row[1] async for row in await db.execute("PRAGMA table_info(locais)")}
            for col, ddl in [
                ("neo", "ALTER TABLE locais ADD COLUMN neo TEXT"),
                ("restricao", "ALTER TABLE locais ADD COLUMN restricao TEXT DEFAULT ''"),
                ("estrutura_id", "ALTER TABLE locais ADD COLUMN estrutura_id TEXT REFERENCES estrutura(id)"),
                ("altura_m", "ALTER TABLE locais ADD COLUMN altura_m REAL"),
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
            # núcleo magro v2 — ordens_servico precisa vincular ativo + snapshot de serviço (Rules.md §10)
            os_existing = {row[1] async for row in await db.execute("PRAGMA table_info(ordens_servico)")}
            for col, ddl in [
                ("ativo_id",                "ALTER TABLE ordens_servico ADD COLUMN ativo_id TEXT"),
                ("servico_id",              "ALTER TABLE ordens_servico ADD COLUMN servico_id TEXT"),
                ("servico_versao_snapshot", "ALTER TABLE ordens_servico ADD COLUMN servico_versao_snapshot INTEGER"),
                ("servico_snapshot",        "ALTER TABLE ordens_servico ADD COLUMN servico_snapshot TEXT"),
                ("hora_inicio",             "ALTER TABLE ordens_servico ADD COLUMN hora_inicio TEXT"),
                ("hora_fim",                "ALTER TABLE ordens_servico ADD COLUMN hora_fim TEXT"),
                ("categoria",               "ALTER TABLE ordens_servico ADD COLUMN categoria TEXT"),
                ("subcategoria",            "ALTER TABLE ordens_servico ADD COLUMN subcategoria TEXT"),
                ("servicos",                "ALTER TABLE ordens_servico ADD COLUMN servicos TEXT"),
                ("veiculos",                "ALTER TABLE ordens_servico ADD COLUMN veiculos TEXT"),
                # RES-02 — lotação/departamento da OS (opcional; clientes antigos não precisam enviar)
                ("departamento",            "ALTER TABLE ordens_servico ADD COLUMN departamento TEXT"),
            ]:
                if col not in os_existing:
                    await db.execute(ddl)
            grama_existing = {row[1] async for row in await db.execute("PRAGMA table_info(grama_areas)")}
            for col, ddl in [
                ("grupo_nome", "ALTER TABLE grama_areas ADD COLUMN grupo_nome TEXT"),
                ("visivel", "ALTER TABLE grama_areas ADD COLUMN visivel INTEGER DEFAULT 1"),
                ("cor_hex", "ALTER TABLE grama_areas ADD COLUMN cor_hex TEXT"),
                ("opacidade", "ALTER TABLE grama_areas ADD COLUMN opacidade REAL DEFAULT 0.24"),
            ]:
                if col not in grama_existing:
                    await db.execute(ddl)
            # Docs — vincular documento a uma pasta da árvore (docs_pastas já criada acima)
            ddoc_existing = {row[1] async for row in await db.execute("PRAGMA table_info(docs_documentos)")}
            for col, ddl in [
                ("pasta_id", "ALTER TABLE docs_documentos ADD COLUMN pasta_id INTEGER REFERENCES docs_pastas(id)"),
            ]:
                if col not in ddoc_existing:
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
