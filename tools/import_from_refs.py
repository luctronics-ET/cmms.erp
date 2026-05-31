#!/usr/bin/env python3
"""
Importa/sincroniza dados de referência para o core.db do cmasm.erp.

Fontes:
  pmoc.refs/cmasm_cargos.csv     → estrutura + cargos (bindings de ocupantes)
  pmoc.refs/cmasm_usuarios*.csv  → usuários (se tiver dados)

Execução:
  cd cmasm.erp
  python3 tools/import_from_refs.py
"""
from __future__ import annotations

import csv
import os
import sqlite3

BASE_DIR = os.path.dirname(__file__)
DB_PATH   = os.path.join(BASE_DIR, "..", "data", "core.db")
SCHEMA    = os.path.join(BASE_DIR, "..", "data", "schema_core.sql")
REFS_DIR  = os.path.join(BASE_DIR, "..", "..", "pmoc.refs")

CARGOS_CSV  = os.path.join(REFS_DIR, "cmasm_cargos.csv")
USUARIOS_CSV = os.path.join(REFS_DIR, "cmasm_usuarios (1).csv")

# Hash djb2 hex de '1234' (padrão do sistema)
DEFAULT_PW = "170842"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def infer_pai(codigo: str) -> str | None:
    """Deriva o pai de um CODIGO CMASM-XX.YY.ZZ."""
    parts = codigo.split("-", 1)
    if len(parts) < 2:
        return None
    sub = parts[1]
    segments = sub.split(".")
    if len(segments) <= 1:
        return "CMASM"
    parent_sub = ".".join(segments[:-1])
    return f"CMASM-{parent_sub}"


def infer_tipo(ct: str) -> str:
    """Mapeia ct (chave de cargo) para tipo de nó na estrutura."""
    mapping = {
        "direcao":           "direcao",
        "vice_direcao":      "vice_direcao",
        "chefe_departamento":"departamento",
        "secretario_depto":  "secretaria",
        "encarregado_divisao":"divisao",
        "encarregado_grupo": "grupo",
        "encarregado_secao": "secao",
        "encarregado_servico":"servico",
        "chefe_gabinete":    "gabinete",
        "assessor":          "assessoria",
        "organizacao":       "organizacao",
    }
    return mapping.get(ct, "secao")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    if not os.path.exists(CARGOS_CSV):
        raise SystemExit(f"Arquivo não encontrado: {CARGOS_CSV}")

    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row

    # Garante schema
    with open(SCHEMA, encoding="utf-8") as f:
        con.executescript(f.read())

    # -----------------------------------------------------------------------
    # 1. Ler CSV de cargos
    # -----------------------------------------------------------------------
    with open(CARGOS_CSV, encoding="utf-8-sig") as f:
        cargos_rows = list(csv.DictReader(f))

    # -----------------------------------------------------------------------
    # 2. Upsert raiz CMASM se não existir
    # -----------------------------------------------------------------------
    con.execute("""
        INSERT OR IGNORE INTO estrutura (id, tipo, nome, pai, cargo, ct)
        VALUES ('CMASM', 'organizacao',
                'Centro de Mísseis e Armas Submarinas da Marinha',
                NULL, 'Organização', 'organizacao')
    """)

    # -----------------------------------------------------------------------
    # 3. Upsert estrutura com dados do CSV
    # -----------------------------------------------------------------------
    updated_estrutura = 0
    inserted_estrutura = 0

    estrutura_by_id = {
        r["id"]: r
        for r in con.execute("SELECT id, nome, cargo, ct FROM estrutura").fetchall()
    }

    for row in cargos_rows:
        cod   = row["CODIGO"].strip()
        nome  = row["UNIDADE"].strip()
        cargo = row["CARGO"].strip()
        ct    = row["TIPO"].strip()
        tipo  = infer_tipo(ct)
        pai   = infer_pai(cod)

        existing = estrutura_by_id.get(cod)

        if existing is None:
            con.execute(
                "INSERT INTO estrutura (id, tipo, nome, pai, cargo, ct) VALUES (?,?,?,?,?,?)",
                (cod, tipo, nome, pai, cargo, ct),
            )
            inserted_estrutura += 1
            print(f"  + estrutura INSERT: {cod} — {nome}")
        else:
            changes = []
            if existing["nome"] != nome:
                changes.append(f'nome: "{existing["nome"]}" → "{nome}"')
            if (existing["cargo"] or "") != cargo:
                changes.append(f'cargo: "{existing["cargo"]}" → "{cargo}"')
            if (existing["ct"] or "") != ct:
                changes.append(f'ct: "{existing["ct"]}" → "{ct}"')
            if changes:
                con.execute(
                    "UPDATE estrutura SET nome=?, cargo=?, ct=?, tipo=?, pai=? WHERE id=?",
                    (nome, cargo, ct, tipo, pai, cod),
                )
                updated_estrutura += 1
                print(f"  ~ estrutura UPDATE {cod}: {', '.join(changes)}")

    # -----------------------------------------------------------------------
    # 4. Upsert cargos (bindings de ocupantes)
    # -----------------------------------------------------------------------
    # Ensure every estrutura node has a cargos row
    all_estrutura = [r["id"] for r in con.execute("SELECT id FROM estrutura").fetchall()]
    for eid in all_estrutura:
        con.execute("INSERT OR IGNORE INTO cargos (unidade_id) VALUES (?)", (eid,))

    # Link ocupantes por nome
    linked = 0
    usuarios_by_nome = {
        r["nome"]: r["id"]
        for r in con.execute("SELECT id, nome FROM usuarios WHERE ativo = 1").fetchall()
    }
    for row in cargos_rows:
        cod     = row["CODIGO"].strip()
        ocupante = row["OCUPANTE"].strip()
        if not ocupante:
            continue
        uid = usuarios_by_nome.get(ocupante)
        if uid is not None:
            con.execute(
                "UPDATE cargos SET usuario_id = ? WHERE unidade_id = ?",
                (uid, cod),
            )
            linked += 1
        else:
            print(f"  ⚠ Ocupante não encontrado como usuário: '{ocupante}' ({cod})")

    # -----------------------------------------------------------------------
    # 5. Ler CSV de usuários (se tiver dados)
    # -----------------------------------------------------------------------
    inserted_users = 0
    if os.path.exists(USUARIOS_CSV):
        with open(USUARIOS_CSV, encoding="utf-8-sig") as f:
            user_rows = list(csv.DictReader(f))

        next_uid = (con.execute("SELECT COALESCE(MAX(id), 0) FROM usuarios").fetchone()[0] or 0) + 1

        for row in user_rows:
            nome  = (row.get("NOME") or "").strip()
            posto = (row.get("POSTO") or "").strip() or None
            mat   = (row.get("MATRICULA") or "").strip() or None
            email = (row.get("EMAIL") or "").strip() or None
            tel   = (row.get("TELEFONE") or "").strip() or None
            tipo  = (row.get("TIPO") or "militar").strip().lower()
            role  = (row.get("PERFIL") or "operador").strip().lower()
            cargo_id = (row.get("CARGO_ID") or "").strip() or None

            if not nome:
                continue

            # Valida campos enum
            if tipo not in ("militar", "civil"):
                tipo = "militar"
            if role not in ("admin", "gestor", "operador", "visualizador"):
                role = "operador"

            existing = con.execute(
                "SELECT id FROM usuarios WHERE nome = ?", (nome,)
            ).fetchone()

            if existing:
                con.execute(
                    "UPDATE usuarios SET posto=COALESCE(?,posto), mat=COALESCE(?,mat), "
                    "email=COALESCE(?,email), tel=COALESCE(?,tel) WHERE id=?",
                    (posto, mat, email, tel, existing["id"]),
                )
            else:
                uid = next_uid
                next_uid += 1
                con.execute(
                    "INSERT INTO usuarios (id, nome, posto, mat, email, tel, tipo, role, pw_hash, ativo)"
                    " VALUES (?,?,?,?,?,?,?,?,?,1)",
                    (uid, nome, posto, mat, email, tel, tipo, role, DEFAULT_PW),
                )
                inserted_users += 1
                print(f"  + usuario INSERT: {nome}")

                if cargo_id:
                    con.execute(
                        "UPDATE cargos SET usuario_id=? WHERE unidade_id=?",
                        (uid, cargo_id),
                    )

    con.commit()
    con.close()

    # -----------------------------------------------------------------------
    # Resumo
    # -----------------------------------------------------------------------
    print()
    print("✓ Importação concluída")
    print(f"  estrutura: {inserted_estrutura} inseridos, {updated_estrutura} atualizados")
    print(f"  cargos ligados: {linked}")
    if inserted_users:
        print(f"  usuários inseridos: {inserted_users}")
    else:
        print("  usuários CSV vazio — nenhum usuário importado")


if __name__ == "__main__":
    main()
