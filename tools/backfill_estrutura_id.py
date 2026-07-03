"""backfill_estrutura_id.py — CON-01: mapeia locais.codigo → estrutura.id.

Popula locais.estrutura_id apenas nas linhas cujo codigo casa exatamente com
um estrutura.id existente, pulando (sem falhar) as demais (D-04).

IMPORTANTE (D-04b): hoje locais.codigo está no formato REFRI-<AREA>-<NOME>
(gerado por um import de climatização anterior — ver tools/backfill_local_id.py)
enquanto estrutura.id está no formato CMASM-XX.Y. Como consequência, 0 de 163
locais casam por igualdade de string HOJE — isso é o resultado CORRETO e
esperado desta fase (CON-01/D-04b), não uma falha de execução. O mecanismo
fica pronto: se locais.codigo receber valores CMASM-XX.Y no futuro, o backfill
passa a popular sem qualquer mudança de código.

Nunca sobrescreve estrutura_id já preenchido (WHERE estrutura_id IS NULL) e
nunca cria nós sintéticos em estrutura para casar órfãos — locais sem match
ficam com estrutura_id NULL e entram no relatório de integridade (CON-06).

Idempotente: reexecutar o script não altera linhas já linkadas nem duplica
trabalho — a segunda execução reporta o mesmo número de populados (0 novas
alterações).

Uso:
    python3 tools/backfill_estrutura_id.py
    python3 tools/backfill_estrutura_id.py /caminho/alternativo/core.db
"""
from __future__ import annotations

import os
import sqlite3
import sys


def _db_path() -> str:
    """Resolve o caminho do banco: argv[1] > DB_PATH env > ./data/core.db (relativo à raiz do repo)."""
    if len(sys.argv) > 1 and sys.argv[1]:
        return sys.argv[1]
    env = os.environ.get("DB_PATH", "")
    if env:
        return env
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(root, "data", "core.db")


def run_backfill(db_path: str) -> dict:
    """Executa o backfill e retorna contagens (total, populados, orfaos, atualizados_agora)."""
    if not os.path.exists(db_path):
        print(f"  DB não encontrado em {db_path!r} — nada a fazer.")
        return {"total": 0, "populados": 0, "orfaos": 0, "atualizados_agora": 0}

    conn = sqlite3.connect(db_path)
    try:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        if "locais" not in tables or "estrutura" not in tables:
            print("  Tabela locais ou estrutura ausente — backfill ignorado.")
            return {"total": 0, "populados": 0, "orfaos": 0, "atualizados_agora": 0}

        # Idempotente: só toca linhas ainda não linkadas (estrutura_id IS NULL);
        # nunca sobrescreve valores manuais já preenchidos.
        cur = conn.execute(
            """
            UPDATE locais
            SET estrutura_id = codigo
            WHERE estrutura_id IS NULL
              AND codigo IN (SELECT id FROM estrutura)
            """
        )
        conn.commit()
        atualizados_agora = cur.rowcount

        total = conn.execute("SELECT COUNT(*) FROM locais").fetchone()[0]
        populados = conn.execute(
            "SELECT COUNT(*) FROM locais WHERE estrutura_id IS NOT NULL"
        ).fetchone()[0]
        orfaos = conn.execute(
            "SELECT COUNT(*) FROM locais WHERE estrutura_id IS NULL"
        ).fetchone()[0]

        return {
            "total": total,
            "populados": populados,
            "orfaos": orfaos,
            "atualizados_agora": atualizados_agora,
        }
    finally:
        conn.close()


if __name__ == "__main__":
    path = _db_path()
    print(f"Backfill estrutura_id — DB: {path!r}")
    resultado = run_backfill(path)
    print(f"  total de locais: {resultado['total']}")
    print(f"  locais com estrutura_id populado: {resultado['populados']}")
    print(f"  locais orfaos (estrutura_id NULL, dependem do fallback codigo): {resultado['orfaos']}")
    print(f"  atualizados nesta execucao: {resultado['atualizados_agora']}")
    if resultado["populados"] == 0:
        print(
            "  NOTA (D-04b): 0 matches hoje é o resultado CORRETO e esperado — "
            "locais.codigo está em formato REFRI-<AREA>-<NOME> e estrutura.id em "
            "formato CMASM-XX.Y, então nenhum casa por igualdade de string ainda. "
            "O mecanismo está pronto para quando locais.codigo passar a usar o "
            "formato CMASM-XX.Y. Os orfaos ficam visiveis no relatorio de "
            "integridade (CON-06)."
        )
    if resultado["atualizados_agora"] == 0 and resultado["populados"] > 0:
        print("  (idempotente: nenhum local com estrutura_id NULL e match disponivel encontrado)")
