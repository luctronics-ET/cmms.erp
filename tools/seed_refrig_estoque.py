#!/usr/bin/env python3
"""Seed de estoque de refrigeração: consumíveis (gás, solda, limpa-serpentina),
sobressalentes (capacitor, contactor, filtro, compressor...) com estoque mínimo,
e ferramentas (manifold, bomba de vácuo, detector de vazamento...).

O html não tinha estoque — é conceito do core. Itens marcados com codigo REF-* e
obs 'refrigeracao' para a aba Estoque do módulo Refrigeração filtrar.

ponytail: INSERT OR IGNORE por codigo (UNIQUE). Re-rodar não duplica.
"""
import sqlite3, os, shutil, datetime

DB = os.path.join(os.path.dirname(__file__), '..', 'data', 'core.db')

# (codigo, nome, categoria, unidade, qtd_atual, qtd_minima, preco)
ITENS = [
    # consumíveis
    ('REF-G22',  'Gás refrigerante R-22 (cilindro 13,6kg)', 'consumivel', 'kg', 0, 14, 65.0),
    ('REF-G410', 'Gás refrigerante R-410A (cilindro 11,3kg)', 'consumivel', 'kg', 0, 11, 95.0),
    ('REF-G404', 'Gás refrigerante R-404A (cilindro 10,9kg)', 'consumivel', 'kg', 0, 5, 110.0),
    ('REF-N2',   'Nitrogênio (cilindro pressurização)', 'consumivel', 'un', 0, 1, 350.0),
    ('REF-OLEO', 'Óleo POE para compressor (1L)', 'consumivel', 'L', 0, 3, 45.0),
    ('REF-SOLDA','Vareta de solda foscoper 5%', 'consumivel', 'un', 0, 20, 6.5),
    ('REF-LIMP', 'Fluido limpa-serpentina (5L)', 'consumivel', 'L', 0, 4, 80.0),
    # sobressalentes (estoque mínimo)
    ('REF-CAP',  'Capacitor permanente (kit µF variados)', 'sobressalente', 'un', 0, 10, 22.0),
    ('REF-CONT', 'Contactor 2 polos 25A', 'sobressalente', 'un', 0, 6, 48.0),
    ('REF-FAR',  'Filtro de ar (conjunto split)', 'sobressalente', 'un', 0, 12, 18.0),
    ('REF-FSEC', 'Filtro secador', 'sobressalente', 'un', 0, 8, 15.0),
    ('REF-PLEV', 'Placa eletrônica evaporadora', 'sobressalente', 'un', 0, 2, 320.0),
    ('REF-PLCD', 'Placa eletrônica condensadora', 'sobressalente', 'un', 0, 2, 380.0),
    ('REF-MVENT','Motor ventilador condensadora', 'sobressalente', 'un', 0, 2, 210.0),
    ('REF-SENS', 'Sensor de temperatura', 'sobressalente', 'un', 0, 6, 28.0),
    ('REF-BDRE', 'Bomba de dreno 34 L/h', 'sobressalente', 'un', 0, 3, 95.0),
    ('REF-CTRL', 'Controle remoto universal', 'sobressalente', 'un', 0, 4, 35.0),
    ('REF-CABO', 'Cabo PP 5 vias (rolo)', 'sobressalente', 'm', 0, 50, 4.2),
    ('REF-ISOL', 'Isolamento térmico tubo cobre (baixa/alta)', 'sobressalente', 'm', 0, 30, 7.0),
    # ferramentas
    ('REF-MANIF','Manifold (manômetro alta/baixa)', 'ferramenta', 'un', 1, 1, 280.0),
    ('REF-VACUO','Bomba de vácuo', 'ferramenta', 'un', 1, 1, 650.0),
    ('REF-AMP',  'Alicate amperímetro', 'ferramenta', 'un', 1, 1, 180.0),
    ('REF-DETV', 'Detector de vazamento de gás', 'ferramenta', 'un', 0, 1, 420.0),
    ('REF-RECOL','Recolhedora de gás', 'ferramenta', 'un', 0, 1, 1900.0),
    ('REF-MACA', 'Maçarico de solda (kit)', 'ferramenta', 'un', 1, 1, 320.0),
]

def main():
    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    bak = os.path.join(os.path.dirname(DB), f'core.backup_{ts}.db')
    shutil.copy(DB, bak)
    print(f"backup -> {bak}")

    c = sqlite3.connect(DB)
    before = c.execute("SELECT count(*) FROM estoque").fetchone()[0]
    ins = 0
    for cod, nome, cat, un, qa, qm, pr in ITENS:
        c.execute(
            """INSERT OR IGNORE INTO estoque
               (codigo, nome, categoria, unidade, qtd_atual, qtd_minima, preco_unitario, obs, ativo)
               VALUES (?,?,?,?,?,?,?,?,1)""",
            (cod, nome, cat, un, qa, qm, pr, 'refrigeracao'),
        )
        if c.execute("SELECT changes()").fetchone()[0]:
            ins += 1
    c.commit()
    after = c.execute("SELECT count(*) FROM estoque").fetchone()[0]
    print(f"estoque: {before} -> {after} (+{ins})")
    refrig = c.execute("SELECT count(*) FROM estoque WHERE obs='refrigeracao'").fetchone()[0]
    baixo = c.execute("SELECT count(*) FROM estoque WHERE obs='refrigeracao' AND qtd_atual < qtd_minima").fetchone()[0]
    print(f"itens refrigeração: {refrig} (abaixo do mínimo: {baixo})")
    c.close()
    print("OK")

if __name__ == '__main__':
    main()
