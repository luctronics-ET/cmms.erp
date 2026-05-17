#!/usr/bin/env python3
"""Sincroniza usuarios, estrutura e cargos do xCMASM de referência para o xCore consolidado."""

from __future__ import annotations

import os
import sqlite3


BASE_DIR = os.path.dirname(__file__)
TARGET_DB = os.path.join(BASE_DIR, "..", "data", "core.db")
SOURCE_DB = os.path.join(BASE_DIR, "..", "..", "..", "xCMASM", "xCore", "data", "core.db")
SCHEMA_PATH = os.path.join(BASE_DIR, "..", "data", "schema_core.sql")


def main() -> None:
    if not os.path.exists(SOURCE_DB):
        raise SystemExit(f"Banco de referência não encontrado: {SOURCE_DB}")

    os.makedirs(os.path.dirname(TARGET_DB), exist_ok=True)
    target = sqlite3.connect(TARGET_DB)
    with open(SCHEMA_PATH, encoding="utf-8") as schema_file:
        target.executescript(schema_file.read())

    source = sqlite3.connect(SOURCE_DB)
    source.row_factory = sqlite3.Row

    usuarios = source.execute(
        "SELECT id, nome, posto, mat, email, tel, tipo, role, pw_hash, ativo FROM usuarios"
    ).fetchall()
    estrutura = source.execute("SELECT id, tipo, nome, pai, cargo, ct FROM estrutura").fetchall()
    cargos = source.execute("SELECT unidade_id, usuario_id, obs FROM cargos").fetchall()

    target.executemany(
        """INSERT OR REPLACE INTO usuarios
           (id, nome, posto, mat, email, tel, tipo, role, pw_hash, ativo)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [tuple(row) for row in usuarios],
    )
    target.executemany(
        "INSERT OR REPLACE INTO estrutura (id, tipo, nome, pai, cargo, ct) VALUES (?, ?, ?, ?, ?, ?)",
        [tuple(row) for row in estrutura],
    )
    target.executemany(
        "INSERT OR REPLACE INTO cargos (unidade_id, usuario_id, obs) VALUES (?, ?, ?)",
        [tuple(row) for row in cargos],
    )
    target.commit()

    print(f"✓ Estrutura importada do xCMASM: {len(estrutura)} nós")
    print(f"  Usuários: {len(usuarios)}")
    print(f"  Cargos: {len(cargos)}")
    print(f"  Origem: {SOURCE_DB}")
    print(f"  Destino: {TARGET_DB}")

    source.close()
    target.close()


if __name__ == "__main__":
    main()