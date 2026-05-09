#!/usr/bin/env python3
"""Importa a árvore de locais do xPredial para o banco central do xCore."""

from __future__ import annotations

import os
import sqlite3


BASE_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(BASE_DIR, "..", "data", "core.db")
SCHEMA_PATH = os.path.join(BASE_DIR, "..", "data", "schema_core.sql")
SEED_PATH = os.path.join(BASE_DIR, "..", "..", "xPredial", "seed_locais_cmasm.sql")


def ensure_column(con: sqlite3.Connection, table: str, column: str, ddl: str) -> None:
    cols = {row[1] for row in con.execute(f"PRAGMA table_info({table})")}
    if column not in cols:
        con.execute(ddl)


def main() -> None:
    if not os.path.exists(SEED_PATH):
        raise SystemExit(f"Seed não encontrada: {SEED_PATH}")

    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    with open(SCHEMA_PATH, encoding="utf-8") as schema_file:
        con.executescript(schema_file.read())

    ensure_column(con, "locais", "neo", "ALTER TABLE locais ADD COLUMN neo TEXT")
    ensure_column(con, "locais", "restricao", "ALTER TABLE locais ADD COLUMN restricao TEXT DEFAULT ''")
    ensure_column(con, "locais", "estrutura_id", "ALTER TABLE locais ADD COLUMN estrutura_id TEXT REFERENCES estrutura(id)")

    with open(SEED_PATH, encoding="utf-8") as seed_file:
        con.executescript(seed_file.read())

    con.execute(
        """UPDATE locais
           SET estrutura_id = codigo
           WHERE (estrutura_id IS NULL OR estrutura_id = '')
             AND codigo IN (
                 SELECT id FROM estrutura
                 UNION
                 SELECT unidade_id FROM cargos WHERE unidade_id IS NOT NULL AND unidade_id != ''
             )"""
    )
    con.commit()

    total = con.execute("SELECT COUNT(*) FROM locais WHERE ativo = 1").fetchone()[0]
    vinculados = con.execute("SELECT COUNT(*) FROM locais WHERE estrutura_id IS NOT NULL AND estrutura_id != ''").fetchone()[0]
    print(f"✓ Locais importados no xCore: {total}")
    print(f"  Vínculos com estrutura/cargos: {vinculados}")
    print(f"  Banco: {DB_PATH}")
    con.close()


if __name__ == "__main__":
    main()