#!/usr/bin/env python3
"""Insere os usuários seed diretamente do ERP_core (sem precisar de exportação JSON)."""
import os, sqlite3, sys

SEED = [
    {"id": 1775404932660, "nome": "Ramalho",         "role": "admin",  "cargo_id": "CMASM-01"},
    {"id": 1775404932665, "nome": "Thomas Baptista",  "role": "admin",  "cargo_id": "CMASM-02"},
    {"id": 1775404932674, "nome": "Patricia Yara",    "role": "admin",  "cargo_id": "CMASM-10"},
    {"id": 1775404932676, "nome": "Geovanio",         "role": "gestor", "cargo_id": "CMASM-11"},
    {"id": 1775404932677, "nome": "Vanessa",          "role": "gestor", "cargo_id": "CMASM-11.1"},
    {"id": 1775404932678, "nome": "Bernardo Maia",    "role": "gestor", "cargo_id": "CMASM-11.2"},
    {"id": 1775404932679, "nome": "Perozzi",          "role": "gestor", "cargo_id": "CMASM-12"},
    {"id": 1775404932684, "nome": "Suellen",          "role": "gestor", "cargo_id": "CMASM-13"},
    {"id": 1775404932686, "nome": "Luciano Ferreira", "role": "admin",  "cargo_id": "CMASM-13.2"},
    {"id": 1775404932687, "nome": "Bianca",           "role": "admin",  "cargo_id": "CMASM-20"},
    {"id": 1775404932696, "nome": "Pimentel",         "role": "gestor", "cargo_id": "CMASM-22"},
    {"id": 1775404932718, "nome": "Tarik",            "role": "admin",  "cargo_id": "CMASM-30"},
]

# Hash djb2 de '1234' (mesmo que o ERP_core) = "170842" (hex com sinal)
DEFAULT_PW = "170842"

db_path = os.path.join(os.path.dirname(__file__), "..", "data", "core.db")
schema   = os.path.join(os.path.dirname(__file__), "..", "data", "schema_core.sql")

os.makedirs(os.path.dirname(db_path), exist_ok=True)
con = sqlite3.connect(db_path)
with open(schema) as f:
    con.executescript(f.read())

for u in SEED:
    con.execute(
        "INSERT OR REPLACE INTO usuarios (id, nome, tipo, role, pw_hash, ativo) VALUES (?,?,?,?,?,1)",
        (u["id"], u["nome"], "militar", u["role"], DEFAULT_PW),
    )
    con.execute(
        "INSERT OR REPLACE INTO cargos (unidade_id, usuario_id) VALUES (?,?)",
        (u["cargo_id"], u["id"]),
    )

con.commit()
con.close()
print(f"✓ {len(SEED)} usuários seed inseridos → {db_path}")
print("  Senha padrão: 1234")
