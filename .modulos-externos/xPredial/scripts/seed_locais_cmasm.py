from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
CSV_PATH = BASE.parents[1] / ".docs_cmasm" / "cmasm_cargos.csv"
DB_PATH = BASE / "data" / "predial.db"
SCHEMA_PATH = BASE / "database" / "schema_predial.sql"


def _normalize_text(value: str) -> str:
    return (
        value.lower()
        .replace("á", "a")
        .replace("à", "a")
        .replace("â", "a")
        .replace("ã", "a")
        .replace("é", "e")
        .replace("ê", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ô", "o")
        .replace("õ", "o")
        .replace("ú", "u")
        .replace("ç", "c")
    )


def _classify_tipo(codigo: str, nome: str) -> str:
    n = _normalize_text(nome)
    code = codigo.replace("CMASM-", "")
    depth = len([p for p in code.split(".") if p])

    if "paiol" in n:
        return "paiol"
    if "banheiro" in n or "sanitario" in n:
        return "banheiro"
    if "copa" in n:
        return "sala"
    if (
        "oficina" in n
        or "manutenc" in n
        or "torpedo" in n
        or "missil" in n
        or "foguete" in n
    ):
        return "oficina"
    if (
        "cais" in n
        or "campo" in n
        or "quadra" in n
        or "pista" in n
        or "ilha" in n
        or "preservacao" in n
        or "mata" in n
        or "apa" in n
    ):
        return "area_externa"
    if "gerador" in n or "bombas" in n or "tecnica" in n:
        return "area_tecnica"
    if "secao" in n or "gabinete" in n or "assessoria" in n:
        return "sala"
    if "divisao" in n or "departamento" in n:
        return "edificio"
    if depth <= 2:
        return "edificio"
    return "sala"


def load_csv_nodes() -> list[tuple[str, str, str, str]]:
    rows: list[tuple[str, str, str, str]] = []
    with CSV_PATH.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            norm = {(k or "").strip().upper(): (v or "").strip() for k, v in r.items()}
            codigo = norm.get("CODIGO", "")
            nome = norm.get("UNIDADE", "")
            if not codigo or not nome:
                continue

            code_part = codigo.replace("CMASM-", "")
            parent_codigo = (
                "CMASM-" + ".".join(code_part.split(".")[:-1]) if "." in code_part else "CMASM-ROOT"
            )
            tipo = _classify_tipo(codigo, nome)
            rows.append((codigo, nome, tipo, parent_codigo))

    parent_override = {
        "CMASM-01": "CMASM-CMD-DIR",
        "CMASM-02": "CMASM-CMD-VDIR",
        "CMASM-09": "CMASM-CMD-SECOM",
        "CMASM-10": "CMASM-CMD-DEPT",
        "CMASM-20": "CMASM-CMD-DEPT",
        "CMASM-30": "CMASM-CMD-DEPT",
        "CMASM-31": "CMASM-CMD-PESS",
        "CMASM-35": "CMASM-CMD-OBT",
    }

    adjusted: list[tuple[str, str, str, str]] = []
    for codigo, nome, tipo, parent_codigo in rows:
        adjusted.append((codigo, nome, tipo, parent_override.get(codigo, parent_codigo)))

    grouped: list[tuple[str, str, str, str]] = []
    for codigo, nome, tipo, parent_codigo in adjusted:
        if parent_codigo == "CMASM-ROOT":
            grouped.append((codigo, nome, tipo, _area_group_code(_resolve_area(codigo))))
        else:
            grouped.append((codigo, nome, tipo, parent_codigo))

    # Em cada divisao, cria 1 banheiro e 1 copa como salas filhas.
    divisions = [item for item in grouped if "divisao" in _normalize_text(item[1])]
    for codigo, nome, _tipo, _parent_codigo in divisions:
        grouped.append((f"{codigo}.BAN", f"Banheiro - {nome}", "banheiro", codigo))
        grouped.append((f"{codigo}.COPA", f"Copa - {nome}", "sala", codigo))

    return grouped


# Codes (first segment) that belong to OPE by business exception.
# ADM contains buildings, except these groups (and paiois) which are OPE.
_OPE_PREFIXES = {"21", "22", "23"}


def _resolve_area(codigo: str) -> str | None:
    """Return 'ADM', 'OPE', or 'APA' for a given CMASM codigo."""
    # Special extras
    if codigo in ("CMASM-PAIOIS",) or codigo.startswith("CMASM-PAIOL-"):
        return "OPE"
    if codigo.startswith("CMASM-APA"):
        return "APA"
    if codigo in (
        "CMASM-ROOT",
        "CMASM-AREA-ADM",
        "CMASM-AREA-OPE",
        "CMASM-AREA-APA",
    ):
        return None  # root / geographic node — no single area

    code_part = codigo.replace("CMASM-", "")
    # Use the first numeric segment for prefix lookup
    first_segment = code_part.split(".")[0]
    if first_segment in _OPE_PREFIXES:
        return "OPE"
    # LOC extras that are ADM by nature
    if codigo.startswith("CMASM-LOC-"):
        return "ADM"
    return "ADM"


def _area_group_code(area: str | None) -> str:
    if area == "OPE":
        return "CMASM-AREA-OPE"
    if area == "APA":
        return "CMASM-AREA-APA"
    return "CMASM-AREA-ADM"


def _resolve_neo(codigo: str) -> str:
    if codigo == "CMASM-ROOT":
        return "44033"
    return codigo.replace("CMASM-", "") if codigo.startswith("CMASM-") else codigo


def _resolve_endereco(parent_name: str | None, area: str | None) -> str | None:
    if not parent_name and not area:
        return None
    if parent_name and area:
        return f"{parent_name}, {area}"
    return parent_name or area


def _resolve_restricao(codigo: str, area: str | None, tipo: str) -> str | None:
    if codigo.startswith("CMASM-PAIOL-") or codigo in {"CMASM-PAIOIS"}:
        return "secreto"
    if area == "OPE":
        return "militar"
    if area == "APA":
        return "proibido"
    if codigo in {"CMASM-ROOT", "CMASM-AREA-ADM", "CMASM-AREA-OPE", "CMASM-AREA-APA"}:
        return "militar"
    if tipo == "edificio":
        return "militar"
    return "civil"


def extra_nodes() -> list[tuple[str, str, str, str]]:
    extras: list[tuple[str, str, str, str]] = [
        ("CMASM-AREA-ADM", "Area Administrativa (ADM)", "area_externa", "CMASM-ROOT"),
        ("CMASM-AREA-OPE", "Area Operativa (OPE)", "area_externa", "CMASM-ROOT"),
        ("CMASM-AREA-APA", "Area Verde (APA)", "area_externa", "CMASM-ROOT"),
        ("CMASM-CMD", "Predio do Comando", "edificio", "CMASM-AREA-ADM"),
        ("CMASM-CMD-DIR", "Direcao", "edificio", "CMASM-CMD"),
        ("CMASM-CMD-VDIR", "Vice-direcao", "edificio", "CMASM-CMD"),
        ("CMASM-CMD-SECOM", "SECOM", "edificio", "CMASM-CMD"),
        ("CMASM-CMD-DEPT", "Departamentos", "edificio", "CMASM-CMD"),
        ("CMASM-CMD-PESS", "Pessoal", "edificio", "CMASM-CMD"),
        ("CMASM-CMD-OBT", "Obtencao", "edificio", "CMASM-CMD"),
        ("CMASM-LOC-02", "Cais Administrativo", "area_externa", "CMASM-AREA-ADM"),
        ("CMASM-LOC-03", "Campo de Futebol", "area_externa", "CMASM-AREA-ADM"),
        ("CMASM-LOC-04", "Quadra de Volei", "area_externa", "CMASM-AREA-ADM"),
        ("CMASM-LOC-05", "Casa de Bombas", "area_tecnica", "CMASM-AREA-ADM"),
        ("CMASM-LOC-06", "Cais Operativo", "area_externa", "CMASM-AREA-OPE"),
        ("CMASM-LOC-07", "Pista de Pouso de Helicoptero", "area_externa", "CMASM-AREA-OPE"),
        ("CMASM-LOC-08", "Estande de Tiro", "area_externa", "CMASM-AREA-ADM"),
        ("CMASM-PAIOIS", "Complexo de Paiois de Armamento", "edificio", "CMASM-AREA-OPE"),
        ("CMASM-APA-01", "Area de Preservacao Ambiental (APA)", "area_externa", "CMASM-AREA-APA"),
    ]

    for i in range(1, 66):
        extras.append(
            (
                f"CMASM-PAIOL-{i:02d}",
                f"Paiol de Armamento {i:02d}",
                "paiol",
                "CMASM-PAIOIS",
            )
        )
    return extras


def seed() -> tuple[int, int]:
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))

        # Migration safety for existing databases created before codigo/neo.
        cols = {row[1] for row in conn.execute("PRAGMA table_info(locais)").fetchall()}
        if "codigo" not in cols:
            conn.execute("ALTER TABLE locais ADD COLUMN codigo TEXT")
        if "neo" not in cols:
            conn.execute("ALTER TABLE locais ADD COLUMN neo TEXT")
        if "area" not in cols:
            conn.execute("ALTER TABLE locais ADD COLUMN area TEXT")
        if "endereco" not in cols:
            conn.execute("ALTER TABLE locais ADD COLUMN endereco TEXT")
        if "restricao" not in cols:
            conn.execute("ALTER TABLE locais ADD COLUMN restricao TEXT")

        conn.execute("CREATE INDEX IF NOT EXISTS idx_locais_codigo ON locais(codigo)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_locais_neo ON locais(neo)")

        nodes = [
            ("CMASM-ROOT", "Centro de Misseis e Armas Submarinas (CMASM)", "OM", None),
            *load_csv_nodes(),
            *extra_nodes(),
        ]

        # Reset in FK-safe order because inspecoes reference locais.
        conn.executescript(
            """
            DELETE FROM inspecao_anexos;
            DELETE FROM workflow_events;
            DELETE FROM inspecao_itens;
            DELETE FROM inspecoes;
            DELETE FROM locais;
            """
        )

        pending = {codigo: (nome, tipo, parent) for codigo, nome, tipo, parent in nodes}
        id_map: dict[str, int] = {}
        name_map: dict[str, str] = {}

        while pending:
            progress = False
            for codigo, (nome, tipo, parent_codigo) in list(pending.items()):
                if parent_codigo is None or parent_codigo in id_map:
                    parent_id = id_map.get(parent_codigo)
                    parent_name = name_map.get(parent_codigo)
                    neo = _resolve_neo(codigo)
                    area = _resolve_area(codigo)
                    endereco = _resolve_endereco(parent_name, area)
                    restricao = _resolve_restricao(codigo, area, tipo)
                    cur = conn.execute(
                        "INSERT INTO locais(codigo, neo, area, endereco, restricao, nome, tipo, parent_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (codigo, neo, area, endereco, restricao, nome, tipo, parent_id),
                    )
                    id_map[codigo] = int(cur.lastrowid)
                    name_map[codigo] = nome
                    del pending[codigo]
                    progress = True
            if not progress:
                raise RuntimeError(
                    f"Nao foi possivel resolver hierarquia para os codigos: {list(pending)[:10]}"
                )

        conn.commit()

        total = int(conn.execute("SELECT COUNT(*) FROM locais").fetchone()[0])
        paiois = int(conn.execute("SELECT COUNT(*) FROM locais WHERE tipo='paiol'").fetchone()[0])
        return total, paiois
    finally:
        conn.close()


if __name__ == "__main__":
    total, paiois = seed()
    print(f"Banco preenchido: {total} locais, {paiois} paiois")
