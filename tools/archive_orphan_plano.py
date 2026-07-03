"""archive_orphan_plano.py — CON-05/D-07: arquiva o plano de climatização órfão via flag.

Contexto (RESEARCH §6.1): existe um único plano em `catalogo_planos` com
`id='plano-3c349c22f4'` cujo `aplicavel_tipos='[]'` (JSON de lista vazia) —
ou seja, aplicável a NENHUM tipo de ativo. Isso é semanticamente diferente
de `aplicavel_tipos IS NULL`, que os 12 planos `plano-clima-g1..g12` usam
para significar "não restringido" (aplicável a qualquer tipo da categoria).
Por isso este script NUNCA toca em `plano-clima-g1..g12` — só no id fixo
do plano órfão.

Ação (D-07, Opção B recomendada — RESEARCH §6.2): marca o plano como
arquivado via flag dupla, nunca via DROP/DELETE:
    UPDATE catalogo_planos
    SET ativo = 0, arquivado_motivo = '<motivo>'
    WHERE id = 'plano-3c349c22f4' AND arquivado_motivo IS NULL

A cláusula `arquivado_motivo IS NULL` garante idempotência: uma segunda
execução não altera nada (rowcount=0) porque a condição já não é satisfeita.

A coluna `catalogo_planos.arquivado_motivo` já foi criada pelo plano 10-01
(migração aditiva em `backend/db_core.py`) — este script NÃO re-migra o
schema, apenas consome a coluna existente.

Efeito colateral esperado: como `ativo=0`, `backend/sync.py` (linha ~519,
`WHERE ativo = 1`) deixa de incluir este plano no manifest do PMOC.

Uso:
    python3 tools/archive_orphan_plano.py
    python3 tools/archive_orphan_plano.py  # segunda vez → "já estava arquivado"
"""
from __future__ import annotations

import os
import sqlite3

PLANO_ID = "plano-3c349c22f4"
MOTIVO = "CON-05: aplicavel_tipos=[] — sem ativos correspondentes"


def _db_path() -> str:
    """Resolve o caminho do banco seguindo a mesma lógica do backend (DB_PATH env / data/core.db)."""
    env = os.environ.get("DB_PATH", "")
    if env:
        return env
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(root, "data", "core.db")


def archive_orphan_plano(db_path: str) -> bool:
    """Arquiva o plano órfão via flag (ativo=0 + arquivado_motivo). Retorna True se arquivou agora."""
    if not os.path.exists(db_path):
        print(f"  DB não encontrado em {db_path!r} — nada a fazer.")
        return False

    conn = sqlite3.connect(db_path)
    try:
        cur = conn.execute(
            """
            UPDATE catalogo_planos
            SET ativo = 0, arquivado_motivo = ?
            WHERE id = ? AND arquivado_motivo IS NULL
            """,
            (MOTIVO, PLANO_ID),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


if __name__ == "__main__":
    path = _db_path()
    print(f"Arquivamento de plano órfão (CON-05) — DB: {path!r}")
    arquivado_agora = archive_orphan_plano(path)
    if arquivado_agora:
        print(f"  Plano {PLANO_ID!r} arquivado agora (ativo=0, arquivado_motivo preenchido).")
    else:
        print(f"  Plano {PLANO_ID!r} já estava arquivado (idempotente — nenhuma linha alterada).")
