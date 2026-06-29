"""backfill_local_id.py — RES-03: copia pmoc_refrigeracao.local_id → ativos.local_id.

Executa apenas onde ativos.local_id IS NULL e pmoc_refrigeracao.local_id IS NOT NULL.
Nunca sobrescreve valores existentes e nunca limpa/zera nenhum campo.

Idempotente: a segunda execução atualiza 0 linhas porque a primeira já preencheu os NULLs.

Categorias não-refrigeração (transportes, corte, fonoclama) ficam com local_id NULL
e são atribuíveis manualmente pela ficha de ativo no ERP.

Uso:
    python tools/backfill_local_id.py
    python tools/backfill_local_id.py  # segunda vez → "0 ativos atualizados"
"""
from __future__ import annotations

import os
import sqlite3


def _db_path() -> str:
    """Resolve o caminho do banco seguindo a mesma lógica do backend (DB_PATH env / data/core.db)."""
    env = os.environ.get("DB_PATH", "")
    if env:
        return env
    # Calcula relativo à raiz do repo (este script vive em tools/)
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(root, "data", "core.db")


def run_backfill(db_path: str) -> int:
    """Executa o backfill e retorna o número de linhas atualizadas."""
    if not os.path.exists(db_path):
        print(f"  DB não encontrado em {db_path!r} — nada a fazer.")
        return 0

    conn = sqlite3.connect(db_path)
    try:
        # Verifica se pmoc_refrigeracao existe; pula graciosamente se não existir.
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        if "pmoc_refrigeracao" not in tables:
            print("  Tabela pmoc_refrigeracao ausente — backfill ignorado.")
            return 0

        # Atualiza ativos.local_id somente onde:
        #   (a) ativos.local_id IS NULL  — nunca sobrescreve
        #   (b) pmoc_refrigeracao.local_id IS NOT NULL  — só quando há fonte válida
        cur = conn.execute(
            """
            UPDATE ativos
            SET local_id = (
                SELECT pr.local_id
                FROM pmoc_refrigeracao pr
                WHERE pr.ativo_id = ativos.id
                  AND pr.local_id IS NOT NULL
                LIMIT 1
            )
            WHERE ativos.local_id IS NULL
              AND ativos.id IN (
                SELECT pr2.ativo_id
                FROM pmoc_refrigeracao pr2
                WHERE pr2.local_id IS NOT NULL
            )
            """
        )
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()


if __name__ == "__main__":
    path = _db_path()
    print(f"Backfill local_id — DB: {path!r}")
    n = run_backfill(path)
    print(f"  {n} ativo(s) atualizado(s) com local_id de pmoc_refrigeracao.")
    if n == 0:
        print("  (idempotente: nenhum ativo com local_id NULL e fonte disponível encontrado)")
