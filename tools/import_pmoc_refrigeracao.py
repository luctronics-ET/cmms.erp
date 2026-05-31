#!/usr/bin/env python3
"""
Importa dados do PMOC de Refrigeração (CSV) para o core.db do cmasm.erp.

Cria/atualiza:
  - locais: zona (AZUL/VERMELHA) → prédio (EDIFICIO) → ambiente (AMBIENTE)
  - ativos: cada equipamento de climatização (categoria=climatizacao)
  - pmoc_refrigeracao: dados PMOC/operacionais de cada unidade

Execução:
  cd cmasm.erp
  python3 tools/import_pmoc_refrigeracao.py [--dry-run]
"""
from __future__ import annotations

import csv
import os
import re
import sqlite3
import sys
import unicodedata

BASE_DIR = os.path.dirname(__file__)
DB_PATH  = os.path.join(BASE_DIR, "..", "data", "core.db")
SCHEMA   = os.path.join(BASE_DIR, "..", "data", "schema_core.sql")
REFS_DIR = os.path.join(BASE_DIR, "..", "..", "pmoc.refs")
PMOC_CSV = os.path.join(REFS_DIR, "CMASM_PMOC_REFRIG - CMASM_PMOC_REFRI.csv")

CMASM_ROOT_LOCAL_ID = 309  # "Centro de Mísseis e Armas Submarinas" (instalacao)

DRY_RUN = "--dry-run" in sys.argv


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def slugify(text: str) -> str:
    """Texto → slug maiúsculo para uso em códigos."""
    text = unicodedata.normalize("NFD", text.upper().strip())
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = re.sub(r"[^A-Z0-9]", "-", text)
    text = re.sub(r"-{2,}", "-", text).strip("-")
    return text[:20]


def floatn(v: str) -> float | None:
    v = v.strip().replace(",", ".")
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def intn(v: str) -> int | None:
    v = v.strip()
    try:
        return int(v)
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Local upsert
# ---------------------------------------------------------------------------

def get_or_create_local(con: sqlite3.Connection, codigo: str, nome: str,
                         tipo: str, parent_id: int | None) -> int:
    row = con.execute("SELECT id FROM locais WHERE codigo = ?", (codigo,)).fetchone()
    if row:
        return row[0]
    cur = con.execute(
        "INSERT INTO locais (codigo, nome, tipo, parent_id, ativo) VALUES (?,?,?,?,1)",
        (codigo, nome, tipo, parent_id),
    )
    return cur.lastrowid


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    if not os.path.exists(PMOC_CSV):
        raise SystemExit(f"CSV não encontrado: {PMOC_CSV}")

    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row

    # Apply schema (creates pmoc_refrigeracao if not exists)
    with open(SCHEMA, encoding="utf-8") as f:
        con.executescript(f.read())

    # -----------------------------------------------------------------------
    # Read CSV
    # -----------------------------------------------------------------------
    with open(PMOC_CSV, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    print(f"CSV: {len(rows)} equipamentos lidos")

    # -----------------------------------------------------------------------
    # 1. Build local hierarchy: zona → prédio → ambiente
    # -----------------------------------------------------------------------
    zona_cache: dict[str, int] = {}
    predio_cache: dict[tuple, int] = {}
    ambiente_cache: dict[tuple, int] = {}

    zona_nomes = {"AZUL": "Área Azul", "VERMELHA": "Área Vermelha"}

    for row in rows:
        area = row["LOCAL.AREA"].strip()
        edificio = row["LOCAL.EDIFICIO"].strip()
        ambiente = row["LOCAL.AMBIENTE"].strip()

        # --- Zona ---
        if area not in zona_cache:
            cod = f"CMASM-ZONA-{slugify(area)[:3]}"
            nome = zona_nomes.get(area, f"Área {area.title()}")
            lid = get_or_create_local(con, cod, nome, "zona", CMASM_ROOT_LOCAL_ID)
            zona_cache[area] = lid

        zona_id = zona_cache[area]

        # --- Prédio ---
        key_pred = (area, edificio)
        if key_pred not in predio_cache:
            slug = slugify(edificio)[:15]
            cod = f"CMASM-{area[:3]}-{slug}"
            lid = get_or_create_local(con, cod, edificio.title(), "predio", zona_id)
            predio_cache[key_pred] = lid

        predio_id = predio_cache[key_pred]

        # --- Ambiente ---
        key_amb = (area, edificio, ambiente)
        if key_amb not in ambiente_cache:
            slug_amb = slugify(ambiente)[:12]
            slug_pred = slugify(edificio)[:8]
            cod = f"CMASM-{area[:3]}-{slug_pred[:8]}-{slug_amb[:8]}"
            # Update area_m2 if available
            area_m2 = floatn(row.get("LOCAL.AMB.AREA (M2)", ""))
            desc = f"Vol: {row.get('LOCAL.AMB.VOL (M3)', '').strip()} m³" if row.get("LOCAL.AMB.VOL (M3)", "").strip() else None
            existing = con.execute("SELECT id FROM locais WHERE codigo = ?", (cod,)).fetchone()
            if existing:
                lid = existing[0]
            else:
                cur = con.execute(
                    "INSERT INTO locais (codigo, nome, tipo, parent_id, area_m2, descricao, ativo)"
                    " VALUES (?,?,?,?,?,?,1)",
                    (cod, ambiente.title(), "sala", predio_id, area_m2, desc),
                )
                lid = cur.lastrowid
            ambiente_cache[key_amb] = lid

    n_locais = len(zona_cache) + len(predio_cache) + len(ambiente_cache)
    print(f"Locais: {len(zona_cache)} zonas, {len(predio_cache)} prédios, {len(ambiente_cache)} ambientes")

    # -----------------------------------------------------------------------
    # 2. Upsert ativos + pmoc_refrigeracao
    # -----------------------------------------------------------------------
    existing_by_csv_id = {
        r[0]: r[1]
        for r in con.execute(
            "SELECT pmoc_csv_id, ativo_id FROM pmoc_refrigeracao WHERE pmoc_csv_id IS NOT NULL"
        ).fetchall()
    }

    tipo_map = {"SPLIT": "AC_SPLIT", "JANELA": "AC_JANELA", "PISO/TETO": "AC_PISO_TETO"}

    ins_ativos = 0
    ins_pmoc = 0
    upd_pmoc = 0

    for row in rows:
        csv_id = intn(row["ID"])
        area = row["LOCAL.AREA"].strip()
        edificio = row["LOCAL.EDIFICIO"].strip()
        ambiente_txt = row["LOCAL.AMBIENTE"].strip()

        local_id = ambiente_cache.get((area, edificio, ambiente_txt))

        # AC asset
        tipo_raw = row["ATIVO.TIPO"].strip()
        tipo = tipo_map.get(tipo_raw, "AC_SPLIT")
        marca = row["ATIVO.MARCA"].strip()
        modelo = row["ATIVO.MODELO"].strip()
        btu = row["ATIVO.BTU"].strip()
        estado_op = row["ATIVO.EST.OPERACIONAL"].strip()  # OP | INOP
        patrimonio = row["PATRIMÔNIO"].strip() or None

        nome_ativo = f"AC {marca} {btu} BTU – {ambiente_txt.title()}" if marca and btu else \
                     f"AC {tipo_raw} – {ambiente_txt.title()}"
        nome_ativo = nome_ativo.strip(" –")

        ativo_id = existing_by_csv_id.get(csv_id)

        if ativo_id is None:
            seq = csv_id
            ativo_id = f"hvac-{seq:03d}"
            # Make unique if collision
            while con.execute("SELECT 1 FROM ativos WHERE id=?", (ativo_id,)).fetchone():
                seq += 1000
                ativo_id = f"hvac-{seq:03d}"

            loc_ref = f"CMASM-{area[:3]}-{slugify(edificio)[:15]}"
            con.execute(
                "INSERT INTO ativos (id, tipo, subtipo, categoria, nome, pat, loc, obs, ativo)"
                " VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    ativo_id, tipo, marca or None, "climatizacao",
                    nome_ativo, patrimonio, loc_ref,
                    row["ATIVO.REFRI.OBS"].strip() or None,
                    1 if estado_op == "OP" else 0,
                ),
            )
            ins_ativos += 1
        else:
            # Update name/patrimonio if changed
            con.execute(
                "UPDATE ativos SET nome=?, pat=COALESCE(?,pat), ativo=? WHERE id=?",
                (nome_ativo, patrimonio, 1 if estado_op == "OP" else 0, ativo_id),
            )

        # PMOC row
        pmoc_data = {
            "ativo_id":           ativo_id,
            "local_id":           local_id,
            "estado_operacional": estado_op or "OP",
            "est_idade":          row["ATIVO.EST.IDADE"].strip() or None,
            "obs":                row["ATIVO.REFRI.OBS"].strip() or None,
            "permanencia":        1 if row["REFRIG.PERM"].strip() == "X" else 0,
            "criticidade":        row["REFRI.CRITICIDADE"].strip() or "MÉDIA",
            "horas_dia":          floatn(row["ATIVO.REFRI.H/DIA"]),
            "dias_semana":        intn(row["REFRI.D/SEM"]),
            "tensao_nominal":     floatn(row["ATIVO.ELE.TENSÃO"]),
            "tensao_medida":      floatn(row["ATIVO.ELE.TENSAO.MEDIDA"]),
            "corrente_nominal":   floatn(row["CORRENTE(A)"]),
            "corrente_medida":    floatn(row["CORRENTE.MEDIDA"]),
            "potencia_kw":        floatn(row["POTÊNCIA(kW)"]),
            "quadro":             row["QUADRO"].strip() or None,
            "disjuntor":          row["DISJUNTOR"].strip() or None,
            "cabo":               row["CABO"].strip() or None,
            "gas_tipo":           row["GÁS EST."].strip() or None,
            "carga_g":            floatn(row["CARGA EST.(g)"]),
            "pressao_padrao":     row["PRESSAO.PADRAO"].strip() or None,
            "pressao_medida":     row["PRESSAO.MEDIDA"].strip() or None,
            "pressao_data":       row["PRESSAO.MEDIDA.DATA"].strip() or None,
            "temp_evaporadora":   row["TEMPERATURA.EVAPORADORA"].strip() or None,
            "temp_evaporadora_m": row["TEMP.EVAPORADORA.MEDIDA"].strip() or None,
            "temp_centro":        row["TEMP. CENTRO"].strip() or None,
            "temp_longe":         row["TEMP.LONGE"].strip() or None,
            "patrimonio":         patrimonio,
            "data_instalacao":    row["DATA INSTAL."].strip() or None,
            "ultima_manutencao":  row["ÚLTIMA MANUT."].strip() or None,
            "pmoc_csv_id":        csv_id,
        }

        if csv_id in existing_by_csv_id:
            fields = [f"{k}=?" for k in pmoc_data if k != "pmoc_csv_id"]
            vals = [pmoc_data[k] for k in pmoc_data if k != "pmoc_csv_id"]
            con.execute(
                f"UPDATE pmoc_refrigeracao SET {', '.join(fields)}, atualizado_em=CURRENT_TIMESTAMP"
                f" WHERE pmoc_csv_id=?",
                vals + [csv_id],
            )
            upd_pmoc += 1
        else:
            cols = ", ".join(pmoc_data.keys())
            phs  = ", ".join(["?"] * len(pmoc_data))
            con.execute(
                f"INSERT INTO pmoc_refrigeracao ({cols}) VALUES ({phs})",
                list(pmoc_data.values()),
            )
            existing_by_csv_id[csv_id] = ativo_id
            ins_pmoc += 1

    if DRY_RUN:
        con.rollback()
        print("\n[DRY-RUN] Nenhuma alteração salva.")
    else:
        con.commit()

    con.close()

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------
    print()
    print("✓ Importação PMOC Refrigeração concluída")
    print(f"  Locais criados: {n_locais} "
          f"({len(zona_cache)} zonas + {len(predio_cache)} prédios + {len(ambiente_cache)} ambientes)")
    print(f"  Ativos inseridos: {ins_ativos}")
    print(f"  PMOC inseridos: {ins_pmoc} | atualizados: {upd_pmoc}")
    if DRY_RUN:
        print("  *** DRY-RUN — banco não foi alterado ***")


if __name__ == "__main__":
    main()
