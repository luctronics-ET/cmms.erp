"""
Seed de materiais/peças do estoque — migrado de PECAS_DEFAULT do gestao-ativos-data.js.
Idempotente: usa INSERT OR IGNORE por código.

Uso:
    cd xCore
    python tools/seed_estoque.py
"""
import asyncio, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from backend.db_core import CoreDB

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "core.db")

# (codigo, nome, categoria, unidade, qtd_minima, preco_unitario)
ITENS = [
    # ── Máquinas de corte — óleos e graxas
    ("PE-01","Óleo 2T STIHL HP Ultra 50mL",         "consumivel","un", 5,  8.50),
    ("PE-02","Óleo SAE 30 / 10W-30 — 1L",           "consumivel","L",  4, 25.00),
    ("PE-03","Óleo 15W-40 diesel — 1L",             "consumivel","L",  8, 20.00),
    ("PE-04","Graxa STIHL engrenagem 80g",           "consumivel","un", 2, 35.00),
    ("PE-05","Graxa NLGI 2 cartucho 400g",           "consumivel","un", 2, 28.00),
    # ── Filtros — máquinas de corte
    ("PE-06","Filtro de ar FS220",                   "sobressalente","un", 5, 38.00),
    ("PE-07","Filtro de ar LTH 1738 (TS114)",        "sobressalente","un", 2, 55.00),
    ("PE-08","Filtro combustível motor 4T",          "sobressalente","un", 5, 22.00),
    # ── Velas e peças — corte
    ("PE-09","Vela HQT-9 (Husqvarna)",               "sobressalente","un", 4, 47.40),
    ("PE-10","Vela NGK BPMR7A (STIHL)",              "sobressalente","un", 6, 22.00),
    ("PE-11","Lâmina de corte TS114",                "sobressalente","un", 4,107.00),
    ("PE-12","Correia A-78 (TS114)",                 "sobressalente","un", 2, 75.00),
    ("PE-13","Carretel nylon FS220",                 "sobressalente","un", 6, 22.00),
    # ── Veículos — óleos e filtros
    ("PE-20","Óleo 5W-30 sintético 4L",              "consumivel","un", 4,120.00),
    ("PE-21","Filtro de óleo veicular",              "sobressalente","un", 4, 35.00),
    ("PE-22","Filtro de ar veicular",                "sobressalente","un", 3, 45.00),
    ("PE-23","Pastilhas de freio (jogo)",            "sobressalente","un", 2,180.00),
    ("PE-24","Filtro diesel veicular",               "sobressalente","un", 3, 55.00),
    ("PE-25","Fluido DOT-4 500ml",                   "consumivel","un", 2, 45.00),
    # ── Embarcações
    ("PE-30","Óleo náutico 2T — 1L",                "consumivel","L",  4, 65.00),
    ("PE-31","Anodo de zinco motor de popa",         "sobressalente","un", 2, 85.00),
    ("PE-32","Impeller kit bomba d'água",            "sobressalente","un", 2,220.00),
    ("PE-33","Tinta anti-incrustante 3.6L",          "consumivel","un", 1,380.00),
    # ── Climatização
    ("PE-40","Spray bactericida AC 300ml",           "consumivel","un", 3, 32.00),
    ("PE-41","Capacitor ar-condicionado",            "sobressalente","un", 2, 45.00),
    ("PE-42","Sensor NTC evaporadora",               "sobressalente","un", 2, 25.00),
    ("PE-43","Filtro G4 (central de ar)",            "sobressalente","un", 4, 35.00),
    # ── Geradores
    ("PE-50","Filtro de óleo gerador",               "sobressalente","un", 2, 95.00),
    ("PE-51","Filtro diesel gerador",                "sobressalente","un", 2, 75.00),
    ("PE-52","Filtro de ar gerador",                 "sobressalente","un", 2, 85.00),
]


async def seed():
    db = CoreDB(DB_PATH)
    await db.init()
    inserted = skipped = 0
    for codigo, nome, cat, un, qtd_min, preco in ITENS:
        exists = await db.fetch_one("SELECT id FROM estoque WHERE codigo = ?", (codigo,))
        if exists:
            skipped += 1
            continue
        await db.execute(
            "INSERT INTO estoque (codigo, nome, categoria, unidade, qtd_atual, qtd_minima, preco_unitario, ativo) "
            "VALUES (?,?,?,?,0,?,?,1)",
            (codigo, nome, cat, un, qtd_min, preco),
        )
        inserted += 1
    print(f"Seed estoque: {inserted} inseridos, {skipped} já existiam. Total: {len(ITENS)} itens.")


if __name__ == "__main__":
    asyncio.run(seed())
