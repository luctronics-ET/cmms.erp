#!/usr/bin/env python3
"""Importa o CSV de mapeamento da refrigeração p/ o core.db (fonte única).

Fonte: .docs_cmasm/Mapeamento da Refrigeração ATU em 29 DE ABRIL 2026.csv
(aba 'Relação de Maquinas' exportada). 162 máquinas.

Estrutura de LOCAIS (hierarquia área → prédio → local), nomes mantidos verbatim:
  - ÁREA  -> atributo locais.area (ADMINISTRATIVA | OPERATIVA | PAIOL)
  - PRÉDIO-> local tipo='predio'  (pai)
  - LOCAL -> local tipo='sala'    (filho, parent_id=prédio) — sala/ambiente
  AREA_M2 e ALTURA_M são propriedades do LOCAL (insumo do cálculo de BTU do
  ambiente). Vêm 100% vazias na planilha → ficam NULL (cálculo não é possível
  agora; colunas existem p/ quando houver levantamento).

ATIVOS (categoria=climatizacao), 1 máquina = 1 ativo + 1 linha pmoc_refrigeracao:
  MÁQUINA, FABRICANTE, BTU, FUNCIONA, ESTADO(conservação), FUNCAO, CRITICO,
  AUTOMACAO, DIAS SEMANA, HORAS, PRIORIDADE, RISCO, OBSERVAÇÕES.
  horas_uso_estimado = HORAS/dia × DIAS/semana × 52  (h/ano estimado).
  ponytail: 52 semanas/ano fixo; ajustar se houver calendário de parada real.

Destrutivo+idempotente: APAGA o import anterior (pmoc_refrigeracao, ativos
categoria climatizacao, locais REFRI-*) e reimporta do zero a cada execução.

Uso:  python tools/import_refrigeracao_csv.py [--dry]
"""
from __future__ import annotations

import csv
import os
import re
import sqlite3
import sys

_ROOT = os.path.join(os.path.dirname(__file__), "..")
DB_PATH = os.environ.get("DB_PATH", os.path.join(_ROOT, "data", "core.db"))
CSV_PATH = os.path.join(_ROOT, ".docs_cmasm", "Mapeamento da Refrigeração ATU em 29 DE ABRIL 2026.csv")

# MÁQUINA -> tipo de ativo (inverter é variante de split p/ manutenção)
TIPO_MAP = {
    "SPLIT": "AC_SPLIT", "SPLIT INVERTER": "AC_SPLIT", "SELF CONTAINED": "AC_SELF",
    "JANELA": "AC_JANELA", "CHILLER": "AC_CHILLER",
}

# colunas novas (migração aditiva, PRAGMA antes do ALTER)
COLS_LOCAIS = {"altura_m": "REAL"}
COLS_PMOC = {
    "fabricante": "TEXT", "btu": "INTEGER", "funciona": "TEXT", "estado_conservacao": "TEXT",
    "funcao": "TEXT", "critico": "INTEGER", "automacao": "INTEGER", "prioridade": "INTEGER",
    "risco": "INTEGER", "horas_uso_estimado": "REAL",
}

I = {  # índice de coluna no CSV
    "area": 0, "predio": 1, "local": 2, "maquina": 3, "fabricante": 4, "btu": 5,
    "funciona": 6, "estado": 7, "funcao": 8, "critico": 9, "automacao": 10,
    "dias": 11, "horas": 12, "prioridade": 13, "risco": 14, "area_m2": 15,
    "altura": 16, "volume": 17, "obs": 21,
}


def txt(v):
    s = (v or "").strip()
    return s or None


def inteiro(v):
    """Int tolerante: remove separador de milhar ('48,000'→48000); lixo→None."""
    s = (v or "").strip().replace(".", "").replace(",", "")
    if not s:
        return None
    try:
        return int(s)
    except ValueError:
        return None


def real(v):
    s = (v or "").strip().replace(",", ".")
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def flag_x(v):
    return 1 if (v or "").strip().upper() == "X" else 0


def slug(*parts: str) -> str:
    base = "-".join(p for p in parts if p)
    base = re.sub(r"[^A-Za-z0-9]+", "-", base.upper()).strip("-")
    return ("REFRI-" + base)[:60]


def ensure_schema(conn: sqlite3.Connection) -> None:
    for tabela, cols in (("locais", COLS_LOCAIS), ("pmoc_refrigeracao", COLS_PMOC)):
        existentes = {r[1] for r in conn.execute(f"PRAGMA table_info({tabela})")}
        for nome, tipo in cols.items():
            if nome not in existentes:
                conn.execute(f"ALTER TABLE {tabela} ADD COLUMN {nome} {tipo}")


def wipe(conn: sqlite3.Connection) -> None:
    """Apaga o import anterior (ordem respeita FK: pmoc → ativos → salas → prédios)."""
    conn.execute("DELETE FROM pmoc_refrigeracao")
    conn.execute("DELETE FROM ativos WHERE categoria='climatizacao'")
    conn.execute("DELETE FROM locais WHERE codigo LIKE 'REFRI-%' AND tipo='sala'")
    conn.execute("DELETE FROM locais WHERE codigo LIKE 'REFRI-%' AND tipo='predio'")


def run(dry: bool = False) -> dict:
    with open(CSV_PATH, encoding="utf-8") as fh:
        rows = [r for r in csv.reader(fh)][1:]
    data = [r for r in rows if any(c.strip() for c in r)]

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys=ON")
    ensure_schema(conn)
    wipe(conn)

    stats = {"predios": 0, "salas": 0, "ativos": 0, "pmoc": 0, "tipos": {}}
    predio_cache: dict[str, int] = {}
    sala_cache: dict[str, int] = {}

    def get_predio(area, predio) -> int:
        cod = slug(area, predio)
        if cod in predio_cache:
            return predio_cache[cod]
        cur = conn.execute(
            "INSERT INTO locais (codigo, nome, tipo, area, descricao) VALUES (?,?,?,?,?)",
            (cod, predio or area, "predio", area, f"Área {area}"),
        )
        predio_cache[cod] = cur.lastrowid
        stats["predios"] += 1
        return cur.lastrowid

    def get_sala(area, predio, local, area_m2, altura) -> int:
        cod = slug(area, predio, local)
        if cod in sala_cache:
            return sala_cache[cod]
        pai = get_predio(area, predio)
        cur = conn.execute(
            "INSERT INTO locais (codigo, nome, tipo, area, parent_id, descricao, area_m2, altura_m) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (cod, local or predio, "sala", area, pai, f"{area} / {predio}", real(area_m2), real(altura)),
        )
        sala_cache[cod] = cur.lastrowid
        stats["salas"] += 1
        return cur.lastrowid

    for n, r in enumerate(data, start=1):
        g = lambda k: r[I[k]] if I[k] < len(r) else ""  # noqa: E731
        maquina = (txt(g("maquina")) or "").upper()
        tipo = TIPO_MAP.get(maquina, "AC_OUTRO")
        stats["tipos"][tipo] = stats["tipos"].get(tipo, 0) + 1

        sala_id = get_sala(txt(g("area")), txt(g("predio")), txt(g("local")), g("area_m2"), g("altura"))

        ativo_id = f"refri{n:03d}"
        btu = inteiro(g("btu"))
        fab = txt(g("fabricante"))
        nome = " ".join(p for p in [maquina or "AC", fab or "", f"{btu}BTU" if btu else ""] if p)[:120]
        conn.execute(
            "INSERT INTO ativos (id, tipo, categoria, nome, loc, obs, ativo, uso_atual, unidade_uso) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (ativo_id, tipo, "climatizacao", nome,
             f"{txt(g('predio')) or ''}/{txt(g('local')) or ''}".strip("/"), txt(g("obs")), 1, 0, "h"),
        )
        stats["ativos"] += 1

        horas, dias = real(g("horas")), inteiro(g("dias"))
        uso_est = round(horas * dias * 52, 1) if (horas and dias) else None
        funciona = txt(g("funciona"))
        conn.execute(
            """INSERT INTO pmoc_refrigeracao
               (ativo_id, local_id, estado_operacional, est_idade, obs, horas_dia, dias_semana,
                fabricante, btu, funciona, estado_conservacao, funcao, critico, automacao,
                prioridade, risco, horas_uso_estimado, pmoc_csv_id)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (ativo_id, sala_id,
             "OP" if funciona == "OK" else ("INOP" if funciona == "NOK" else None),
             txt(g("estado")), txt(g("obs")), horas, dias,
             fab, btu, funciona, txt(g("estado")), txt(g("funcao")),
             flag_x(g("critico")), flag_x(g("automacao")), inteiro(g("prioridade")),
             inteiro(g("risco")), uso_est, n),
        )
        stats["pmoc"] += 1

    if dry:
        conn.rollback()
        print("[DRY-RUN] rollback — nada gravado")
    else:
        conn.commit()
    conn.close()
    return stats


if __name__ == "__main__":
    s = run(dry="--dry" in sys.argv)
    print(f"locais: {s['predios']} prédios + {s['salas']} salas")
    print(f"ativos: {s['ativos']}  por tipo: {s['tipos']}")
    print(f"pmoc_refrigeracao: {s['pmoc']}")
