#!/usr/bin/env python3
"""Importa serviços + planos de climatização da ATA2 Carioca (HTML) p/ o catálogo.

Fonte: .docs_cmasm/ata2_carioca_solution.html  (const ATA2 embutida no <script>).
Modelo (conforme regra de negócio):
  - SERVIÇO  = unidade reusável, atribuível a vários tipos de máquina.
               Ex: "Desmontagem parcial" serve split/janela/self/chiller.
               → catalogo_servicos (codigo AC_*, aplicavel_a = todos AC).
  - PLANO    = conjunto de serviços para um tipo/variante de máquina.
               Ex: "Split 18.000 BTU — até 3m" (G1) com seus 29 serviços.
               → catalogo_planos (cabeçalho) + catalogo_plano_itens (serviços).
               classe prev = preventivo recorrente; corr = corretivo sob demanda.

Os 30 serviços distintos são deduplicados por descrição; cada um dos 12 grupos
ATA2 vira um plano com seus itens (valores/qtds da ata preservados no item).

Destrutivo+idempotente p/ climatização: apaga import anterior (svc-arp-*/plan-arp-*
legados + catalogo_planos de climatização) e reimporta do HTML.

Uso:  python tools/import_ata2_climatizacao.py [--dry]
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
import unicodedata

_ROOT = os.path.join(os.path.dirname(__file__), "..")
DB_PATH = os.environ.get("DB_PATH", os.path.join(_ROOT, "data", "core.db"))
HTML = os.path.join(_ROOT, ".docs_cmasm", "ata2_carioca_solution.html")

# serviço de climatização é reusável em todo o parque
TIPOS_AC = ["AC_SPLIT", "AC_JANELA", "AC_SELF", "AC_CHILLER"]
APLICAVEL = json.dumps({"categorias": ["climatizacao"], "tipos": TIPOS_AC})

DDL = """
CREATE TABLE IF NOT EXISTS catalogo_planos (
  id TEXT PRIMARY KEY, codigo TEXT UNIQUE NOT NULL, nome TEXT NOT NULL,
  categoria TEXT NOT NULL DEFAULT 'climatizacao', tipo_codigo TEXT, btu INTEGER,
  inverter INTEGER NOT NULL DEFAULT 0, altura_max_m REAL, fonte TEXT,
  ativo INTEGER NOT NULL DEFAULT 1, criado_em DATETIME DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS catalogo_plano_itens (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  plano_id TEXT NOT NULL REFERENCES catalogo_planos(id) ON DELETE CASCADE,
  servico_id TEXT NOT NULL REFERENCES catalogo_servicos(id),
  seq INTEGER NOT NULL DEFAULT 0, classe TEXT NOT NULL DEFAULT 'prev', item_arp INTEGER,
  valor_unit REAL, qtd_ata REAL, lim_adesao REAL, qtd_cmasm REAL,
  UNIQUE (plano_id, servico_id));
"""


def slug(desc: str) -> str:
    """Descrição -> código estável (sem acento, MAIÚSCULO, _-separado)."""
    s = unicodedata.normalize("NFKD", desc).encode("ascii", "ignore").decode()
    s = re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_").upper()
    return s[:48]


def parse_ata2() -> list[dict]:
    html = open(HTML, encoding="utf-8").read()
    m = re.search(r"const ATA2\s*=\s*(\[.*?\])\s*;", html, re.S)
    if not m:
        sys.exit("ERRO: const ATA2 não encontrada no HTML.")
    return json.loads(m.group(1))


def variante(nome: str) -> dict:
    """Extrai btu/inverter/altura do nome do grupo ATA2."""
    btu = re.search(r"([\d.]+)\s*BTU", nome)
    alt = re.search(r"até\s*(\d+)m", nome)
    return {
        "btu": int(btu.group(1).replace(".", "")) if btu else None,
        "inverter": 1 if "INVERTER" in nome.upper() else 0,
        "altura_max_m": float(alt.group(1)) if alt else None,
    }


def run(dry: bool = False) -> dict:
    grupos = parse_ata2()
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(DDL)

    # wipe import anterior de climatização (legado flat + planos-conjunto)
    conn.execute("DELETE FROM catalogo_plano_itens WHERE plano_id IN "
                 "(SELECT id FROM catalogo_planos WHERE categoria='climatizacao')")
    conn.execute("DELETE FROM catalogo_planos WHERE categoria='climatizacao'")
    conn.execute("DELETE FROM planos_manutencao WHERE id LIKE 'plan-arp-%'")
    conn.execute("DELETE FROM catalogo_servicos WHERE id LIKE 'svc-arp-%'")  # cascateia materiais

    stats = {"servicos": 0, "planos": 0, "itens": 0}
    svc_ids: dict[str, str] = {}  # desc -> servico_id (dedup)

    def get_servico(desc: str, classe: str) -> str:
        if desc in svc_ids:
            return svc_ids[desc]
        cod = "AC_" + slug(desc)
        sid = "svc-clima-" + cod.lower().replace("_", "-")
        conn.execute(
            "INSERT INTO catalogo_servicos (id, codigo, nome, descricao, escopo, versao, "
            "aplicavel_a, criado_por_modulo) VALUES (?,?,?,?,?,?,?,?) "
            "ON CONFLICT(id) DO UPDATE SET nome=excluded.nome, aplicavel_a=excluded.aplicavel_a",
            (sid, cod, desc, desc, "central", 1, APLICAVEL, "manutencao"),
        )
        svc_ids[desc] = sid
        stats["servicos"] += 1
        return sid

    for g in grupos:
        v = variante(g["nome"])
        pid = "plano-clima-" + g["id"].lower()
        conn.execute(
            "INSERT INTO catalogo_planos (id, codigo, nome, categoria, tipo_codigo, btu, "
            "inverter, altura_max_m, fonte) VALUES (?,?,?,?,?,?,?,?,?)",
            (pid, g["id"], g["nome"], "climatizacao", "AC_SPLIT", v["btu"],
             v["inverter"], v["altura_max_m"], "ATA2 Carioca Solution — Pregão 90026/2024 CMRJ"),
        )
        stats["planos"] += 1
        for it in g["itens"]:
            sid = get_servico(it["desc"], it["tipo"])
            conn.execute(
                "INSERT OR IGNORE INTO catalogo_plano_itens (plano_id, servico_id, seq, classe, "
                "item_arp, valor_unit, qtd_ata, lim_adesao, qtd_cmasm) VALUES (?,?,?,?,?,?,?,?,?)",
                (pid, sid, it.get("seq", 0), it["tipo"], it.get("num"),
                 it.get("vunit"), it.get("qtd_ata"), it.get("lim_adesao"), it.get("qtd_cmasm")),
            )
            stats["itens"] += 1

    if dry:
        conn.rollback()
        print("[DRY-RUN] rollback — nada gravado")
    else:
        conn.commit()
    conn.close()
    return stats


if __name__ == "__main__":
    s = run(dry="--dry" in sys.argv)
    print(f"serviços distintos: {s['servicos']}")
    print(f"planos (variantes): {s['planos']}")
    print(f"itens de plano:     {s['itens']}")
