import sqlite3
import re
import os

DB_PATH = os.path.abspath("xCore/data/core.db")
JS_PATH = "ERP_core/gestao-ativos-data.js"

def migrate():
    print(f"Usando DB: {DB_PATH}")
    if not os.path.exists(JS_PATH):
        print(f"Erro: {JS_PATH} não encontrado.")
        return

    with open(JS_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    unidades_match = re.search(r"const UNIDADES_DEFAULT = \[(.*?)\];", content, re.DOTALL)
    if not unidades_match:
        print("Erro: UNIDADES_DEFAULT não encontrado no JS.")
        return
    
    unidades_raw = unidades_match.group(1)
    unidades = []
    pattern_unidade = re.compile(r"\{id:\s*'(.*?)',\s*tipo:\s*'(.*?)',\s*nome:\s*'(.*?)',\s*pat:\s*'(.*?)',\s*obs:\s*'(.*?)',\s*loc:\s*'(.*?)',\s*ativo:\s*(.*?)\}")
    for m in pattern_unidade.finditer(unidades_raw):
        unidades.append(m.groups())

    pecas_match = re.search(r"const PECAS_DEFAULT = \[(.*?)\];", content, re.DOTALL)
    if not pecas_match:
        print("Erro: PECAS_DEFAULT não encontrado no JS.")
        return
    
    pecas_raw = pecas_match.group(1)
    pecas = []
    pattern_peca = re.compile(r"\{id:\s*'(.*?)',\s*d:\s*'(.*?)',.*?un:\s*'(.*?)',\s*cat:\s*'(.*?)',\s*pr:\s*(.*?)\}")
    for m in pattern_peca.finditer(pecas_raw):
        pecas.append(m.groups())

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print(f"Migrando {len(unidades)} ativos...")
    for u in unidades:
        aid, atipo, anome, apat, aobs, aloc, aativo = u
        categoria = "outros"
        if atipo in ["FS220", "GAR", "MS650", "TS114", "SOL"]: categoria = "maquinas_corte"
        elif "VTR" in atipo: categoria = "viaturas"
        elif "EMB" in atipo: categoria = "embarcacoes"
        elif "AC" in atipo: categoria = "climatizacao"
        elif "GERADOR" in atipo: categoria = "eletrica"

        unidade_uso = "h"
        if "VTR" in atipo: unidade_uso = "km"
        if "AC" in atipo: unidade_uso = "meses"

        cursor.execute(
            """INSERT OR REPLACE INTO ativos (id, tipo, categoria, nome, pat, loc, obs, ativo, unidade_uso) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (aid, atipo, categoria, anome, apat, aloc, aobs, 1 if aativo == 'true' else 0, unidade_uso)
        )

    print(f"Migrando {len(pecas)} itens de estoque...")
    for p in pecas:
        pid, pnome, pun, pcat, ppreco = p
        cursor.execute(
            """INSERT OR REPLACE INTO estoque (codigo, nome, categoria, unidade, qtd_atual, preco_unitario) 
               VALUES (?, ?, ?, ?, ?, ?)""",
            (pid, pnome, pcat, pun, 10.0, float(ppreco))
        )

    conn.commit()
    # Verificar inserção imediata
    cursor.execute("SELECT COUNT(*) FROM ativos")
    count = cursor.fetchone()[0]
    print(f"Verificação após commit: {count} ativos no DB.")
    
    conn.close()
    print("Migração concluída com sucesso!")

if __name__ == "__main__":
    migrate()
