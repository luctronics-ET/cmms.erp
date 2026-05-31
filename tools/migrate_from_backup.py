#!/usr/bin/env python3
"""
Migra o backup JSON do ERP_core → xCore SQLite.

Uso:
  python migrate_from_backup.py cmasm_erp_backup.json [--db ../data/core.db]

O JSON é gerado pelo botão "Backup completo (JSON)" no cmasm-erp.html.
"""
import argparse
import json
import os
import sqlite3
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("backup", help="Caminho para cmasm_erp_backup.json")
    ap.add_argument("--db", default=os.path.join(os.path.dirname(__file__), "..", "data", "core.db"))
    args = ap.parse_args()

    with open(args.backup, encoding="utf-8") as f:
        data = json.load(f)

    schema_path = os.path.join(os.path.dirname(__file__), "..", "data", "schema_core.sql")
    os.makedirs(os.path.dirname(args.db), exist_ok=True)

    con = sqlite3.connect(args.db)
    with open(schema_path) as f:
        con.executescript(f.read())

    users     = data.get("users", [])
    cargos    = data.get("cargos", {})
    estrutura = data.get("estrutura", [])

    # Usuários
    for u in users:
        con.execute(
            """INSERT OR REPLACE INTO usuarios (id, nome, posto, mat, email, tel, tipo, role, pw_hash, ativo)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
            (u["id"], u.get("nome",""), u.get("posto",""), u.get("mat",""),
             u.get("email",""), u.get("tel",""), u.get("tipo","militar"),
             u.get("role","operador"), u.get("pw_hash","")),
        )

    # Estrutura
    for e in estrutura:
        con.execute(
            "INSERT OR REPLACE INTO estrutura (id, tipo, nome, pai, cargo, ct) VALUES (?,?,?,?,?,?)",
            (e["id"], e.get("tipo",""), e.get("nome",""), e.get("pai"),
             e.get("cargo",""), e.get("ct","")),
        )

    # Cargos
    for unidade_id, c in cargos.items():
        con.execute(
            "INSERT OR REPLACE INTO cargos (unidade_id, usuario_id, obs) VALUES (?,?,?)",
            (unidade_id, c.get("usuario_id"), c.get("obs","")),
        )

    con.commit()
    con.close()

    print(f"✓ Migração concluída → {args.db}")
    print(f"  Usuários:  {len(users)}")
    print(f"  Estrutura: {len(estrutura)} nós")
    print(f"  Cargos:    {len(cargos)}")


if __name__ == "__main__":
    main()
