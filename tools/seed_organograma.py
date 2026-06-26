#!/usr/bin/env python3
"""Popula `estrutura` (organograma, 79 nós) de .docs_cmasm/cmasm_backup.json.

Aditivo e cirúrgico: só mexe em `estrutura` (INSERT OR IGNORE). NÃO toca em
ativos/locais/usuarios/cargos. cargos já existem (12) mas estão órfãos pois a FK
aponta para estrutura, que estava vazia — isto religa a árvore.

ponytail: INSERT OR IGNORE pela PK (id) — idempotente, re-rodar não duplica.
"""
import json, sqlite3, os, shutil, datetime

ROOT = os.path.join(os.path.dirname(__file__), '..')
DB = os.path.join(ROOT, 'data', 'core.db')
BACKUP = os.path.join(ROOT, '.docs_cmasm', 'cmasm_backup.json')

def main():
    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    bak = os.path.join(os.path.dirname(DB), f'core.backup_{ts}.db')
    shutil.copy(DB, bak)
    print(f"backup -> {bak}")

    nodes = json.load(open(BACKUP, encoding='utf-8'))['estrutura']
    print(f"backup: {len(nodes)} nós estrutura")

    c = sqlite3.connect(DB)
    before = c.execute("SELECT count(*) FROM estrutura").fetchone()[0]
    for n in nodes:
        c.execute(
            "INSERT OR IGNORE INTO estrutura (id, tipo, nome, pai, cargo, ct) VALUES (?,?,?,?,?,?)",
            (n['id'], n.get('tipo'), n.get('nome'), n.get('pai'), n.get('cargo'), n.get('ct')),
        )
    c.commit()
    after = c.execute("SELECT count(*) FROM estrutura").fetchone()[0]
    print(f"estrutura: {before} -> {after} (+{after - before})")

    # verifica cargos órfãos religados
    orf = c.execute(
        "SELECT count(*) FROM cargos cg WHERE NOT EXISTS (SELECT 1 FROM estrutura e WHERE e.id = cg.unidade_id)"
    ).fetchone()[0]
    print(f"cargos órfãos (sem nó estrutura): {orf}")
    raiz = c.execute("SELECT count(*) FROM estrutura WHERE pai IS NULL").fetchone()[0]
    print(f"nós raiz: {raiz}")
    assert after == len(nodes), "contagem estrutura divergente"
    c.close()
    print("OK")

if __name__ == '__main__':
    main()
