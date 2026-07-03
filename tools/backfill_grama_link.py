"""backfill_grama_link.py — CON-04/D-01/D-02: liga ativos.grama_maquina_id
apenas aos casamentos inequívocos (1:1) entre grama_maquinas e ativos.

grama_maquinas foi aposentada como cadastro-mestre (D-01) — a identidade e
uso_atual (fonte única de horas, Rules.md §3) vivem em ativos (categoria
maquinas_corte); grama_maquinas permanece satélite de metadados (fabricante,
número de série, combustível), ligada pela coluna aditiva
ativos.grama_maquina_id (criada no plano 10-01).

Critério de "inequívoco" (D-02): agrupa grama_maquinas por um candidato de
tipo derivado de `modelo` e conta quantos ativos (categoria maquinas_corte)
existem com aquele mesmo `tipo`. Só linka quando AMBOS os lados têm
EXATAMENTE 1 linha — nunca por atribuição ordinal. Nos dados reais isso casa
apenas MS650 e SOL (RESEARCH §1.2/§1.3). Grupos ambíguos (FS220, GAR, TS114)
e máquinas sem ativo correspondente (BR600/soprador) NÃO recebem link:
uso_atual começa em 0 e o histórico de horas em grama_maquinas.horas_uso
fica arquival, exatamente como travado em D-02/CONTEXT.md.

Normalização modelo -> candidato de tipo: `grama_maquinas.modelo` às vezes
carrega um sufixo de variante separado por hífen que não existe em
ativos.tipo (ex. "GAR-53" -> tipo "GAR"; "SOL-1200" -> tipo "SOL"). Usamos o
prefixo antes do primeiro hífen/espaço como candidato — modelos sem hífen
usam o valor completo (ex. "FS220" -> "FS220", "MS650" -> "MS650",
"TS114" -> "TS114"). É o único critério estável observado nos dados reais
(RESEARCH §1.2), não uma suposição de negócio.

Idempotente: só atualiza ativos.grama_maquina_id IS NULL; reexecutar não
duplica nem sobrescreve link manual. NUNCA faz DROP/DELETE em grama_maquinas
— a tabela satélite permanece intacta (12 linhas hoje).

Uso:
    python3 tools/backfill_grama_link.py
    python3 tools/backfill_grama_link.py /caminho/alternativo/core.db
"""
from __future__ import annotations

import os
import re
import sqlite3
import sys
from collections import defaultdict


def _db_path() -> str:
    """Resolve o caminho do banco: argv[1] > DB_PATH env > ./data/core.db (relativo à raiz do repo)."""
    if len(sys.argv) > 1 and sys.argv[1]:
        return sys.argv[1]
    env = os.environ.get("DB_PATH", "")
    if env:
        return env
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(root, "data", "core.db")


def _tipo_candidate(modelo: str) -> str:
    """Deriva o candidato de ativos.tipo a partir de grama_maquinas.modelo.

    Regra: prefixo antes do primeiro '-' ou espaço (ex. 'GAR-53' -> 'GAR',
    'SOL-1200' -> 'SOL'); modelos sem hífen usam o valor completo
    (ex. 'FS220' -> 'FS220', 'MS650' -> 'MS650', 'TS114' -> 'TS114').
    """
    return re.split(r"[-\s]", modelo.strip(), maxsplit=1)[0]


def run_backfill(db_path: str) -> dict:
    """Executa o backfill e retorna o resumo: novos links, já linkados,
    ambíguos pulados e sem-equivalente."""
    result = {
        "novos": [],
        "ja_linkados": [],
        "ambiguos": [],
        "sem_equivalente": [],
    }
    if not os.path.exists(db_path):
        print(f"  DB não encontrado em {db_path!r} — nada a fazer.")
        return result

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        if "grama_maquinas" not in tables or "ativos" not in tables:
            print("  Tabela grama_maquinas ou ativos ausente — backfill ignorado.")
            return result

        gmaq_rows = conn.execute("SELECT id, modelo FROM grama_maquinas").fetchall()
        ativos_rows = conn.execute(
            "SELECT id, tipo, grama_maquina_id FROM ativos WHERE categoria='maquinas_corte'"
        ).fetchall()

        gmaq_by_tipo: dict[str, list[str]] = defaultdict(list)
        for row in gmaq_rows:
            gmaq_by_tipo[_tipo_candidate(row["modelo"])].append(row["id"])

        ativos_by_tipo: dict[str, list[sqlite3.Row]] = defaultdict(list)
        for row in ativos_rows:
            ativos_by_tipo[row["tipo"]].append(row)

        for tipo, gmaq_ids in sorted(gmaq_by_tipo.items()):
            ativos_grupo = ativos_by_tipo.get(tipo, [])

            if not ativos_grupo:
                result["sem_equivalente"].append((tipo, gmaq_ids))
                continue

            if len(gmaq_ids) != 1 or len(ativos_grupo) != 1:
                result["ambiguos"].append((tipo, gmaq_ids, [a["id"] for a in ativos_grupo]))
                continue

            # Match inequívoco (1 grama_maquina, 1 ativo) — único caso linkável (D-02).
            gmaq_id = gmaq_ids[0]
            ativo = ativos_grupo[0]

            if ativo["grama_maquina_id"] == gmaq_id:
                result["ja_linkados"].append((tipo, gmaq_id, ativo["id"]))
                continue

            if ativo["grama_maquina_id"] is not None:
                # Já linkado a outra coisa manualmente — nunca sobrescrever.
                result["ja_linkados"].append((tipo, ativo["grama_maquina_id"], ativo["id"]))
                continue

            conn.execute(
                "UPDATE ativos SET grama_maquina_id=? WHERE id=? AND grama_maquina_id IS NULL",
                (gmaq_id, ativo["id"]),
            )
            result["novos"].append((tipo, gmaq_id, ativo["id"]))

        conn.commit()
    finally:
        conn.close()

    return result


def _print_summary(result: dict) -> None:
    print(f"  Novos links criados nesta execução: {len(result['novos'])}")
    for tipo, gmaq_id, ativo_id in result["novos"]:
        print(f"    - {tipo}: {gmaq_id} -> {ativo_id}")
    if result["ja_linkados"]:
        print(f"  Já linkados (idempotente, sem alteração): {len(result['ja_linkados'])}")
        for tipo, gmaq_id, ativo_id in result["ja_linkados"]:
            print(f"    - {tipo}: {gmaq_id} -> {ativo_id}")
    print(f"  Ambíguos pulados (D-02 — sem pareamento ordinal): {len(result['ambiguos'])}")
    for tipo, gmaq_ids, ativo_ids in result["ambiguos"]:
        print(
            f"    - {tipo}: {len(gmaq_ids)} grama_maquinas vs {len(ativo_ids)} ativos"
            " — uso_atual começa em 0; histórico de grama_maquinas.horas_uso fica arquival"
        )
    print(f"  Sem equivalente em ativos: {len(result['sem_equivalente'])}")
    for tipo, gmaq_ids in result["sem_equivalente"]:
        print(f"    - {tipo}: {gmaq_ids} — permanece só satélite (grama_maquinas), nunca DROP")


if __name__ == "__main__":
    path = _db_path()
    print(f"Backfill grama_maquina_id — DB: {path!r}")
    resultado = run_backfill(path)
    _print_summary(resultado)
    if not resultado["novos"] and (resultado["ja_linkados"] or resultado["ambiguos"] or resultado["sem_equivalente"]):
        print("  (idempotente: nenhum novo link — dataset já processado nesta execução)")
