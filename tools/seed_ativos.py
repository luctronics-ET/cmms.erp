"""
Seed de ativos reais do CMASM.

Usa INSERT OR REPLACE para ser idempotente — pode rodar quantas vezes quiser.
Ativos com ID fixo (u01..u51) mantêm o ID histórico do gestao-ativos-data.js.
Novos ativos de VTR/EMB reais recebem IDs descritivos.

Uso:
    cd xCore
    python tools/seed_ativos.py
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.db_core import CoreDB

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "core.db")

# (id, tipo, categoria, nome, placa, pat, loc, subtipo, obs, uso_atual, unidade_uso)
ATIVOS = [
    # ── MÁQUINAS DE CORTE ──────────────────────────────────────────────────────
    ("u01","FS220","maquinas_corte","FS220-01",     None,None,"Galpão Manutenção",None,None,0,"h"),
    ("u02","FS220","maquinas_corte","FS220-02",     None,None,"Galpão Manutenção",None,None,0,"h"),
    ("u03","FS220","maquinas_corte","FS220-03",     None,None,"Galpão Manutenção",None,None,0,"h"),
    ("u04","FS220","maquinas_corte","FS220-04",     None,None,"Galpão Manutenção",None,None,0,"h"),
    ("u05","FS220","maquinas_corte","FS220-05",     None,None,"Galpão Manutenção",None,None,0,"h"),
    ("u06","GAR",  "maquinas_corte","GAR-01",       None,None,"Galpão Manutenção",None,None,0,"h"),
    ("u07","GAR",  "maquinas_corte","GAR-02",       None,None,"Galpão Manutenção",None,None,0,"h"),
    ("u08","GAR",  "maquinas_corte","GAR-03",       None,None,"Galpão Manutenção",None,None,0,"h"),
    ("u09","MS650","maquinas_corte","MS650-01",     None,None,"Galpão Manutenção",None,None,0,"h"),
    ("u10","TS114","maquinas_corte","TS114-01",     None,None,"Galpão Manutenção",None,None,0,"h"),
    ("u11","TS114","maquinas_corte","TS114-02",     None,None,"Galpão Manutenção",None,None,0,"h"),
    ("u12","SOL",  "maquinas_corte","Trator Solis 90",None,None,"Galpão Manutenção",None,"Trator Agrícola Solis 90",0,"h"),

    # ── VIATURAS INTERNAS (Ilha do Engenho) ────────────────────────────────────
    ("vtr01","VTR_CARGA",  "viaturas","MUNK (Basculante)",  "KPJ-8385",None,"Garagem CMASM","vtr_int","Recolhimento de lixo / transporte interno",0,"km"),
    ("vtr02","VTR_PICKUP", "viaturas","S-10 Picape",        "LRZ-5099",None,"Garagem CMASM","vtr_int",None,0,"km"),
    ("vtr03","VTR_PICKUP", "viaturas","Ambulância",         None,      None,"Garagem CMASM","vtr_int","Viatura de saúde",0,"km"),
    ("vtr04","VTR_CARGA",  "viaturas","Caminhão Constellation",None,   None,"Garagem CMASM","vtr_int","Transporte de material pesado",0,"km"),
    ("vtr05","VTR_CARGA",  "viaturas","XCMG (Guindaste)",   None,      None,"Garagem CMASM","vtr_int","Guindaste / faina de armamento",0,"h"),

    # ── VIATURAS EXTERNAS (Ilha das Flores — uso fora do CMASM) ───────────────
    ("vtr10","VTR_PICKUP", "viaturas","Doblô 1.4",          None,      None,"Ilha das Flores","vtr_ext","Transporte de pessoal externo",0,"km"),

    # ── EMBARCAÇÕES DE ROTINA ──────────────────────────────────────────────────
    ("emb01","EMB_LANCHA","embarcacoes","ETPM Fátima",      "CMASM-08",None,"Cais CMASM","emb_rot","Translado Ilha do Engenho ↔ Ilha das Flores (~12 viagens/dia)",0,"h"),

    # ── EMBARCAÇÕES DE PATRULHA / SOBREAVISO ──────────────────────────────────
    ("emb02","EMB_LANCHA","embarcacoes","Lancha Natal",     "CMASM-05",None,"Cais CMASM","emb_pat","Sobreaviso 18h–06h",0,"h"),
    ("emb03","EMB_LANCHA","embarcacoes","Sargento Freitas", "CMASM-10",None,"Cais CMASM","emb_pat","Embarcação de apoio a fainas",0,"h"),

    # ── CLIMATIZAÇÃO ───────────────────────────────────────────────────────────
    ("u40","AC_SPLIT",  "climatizacao","AC Sala Comando",     None,"",      "Bloco Admin",      None,"24.000 BTU",0,"meses"),
    ("u41","AC_SPLIT",  "climatizacao","AC Sala Servidores",  None,"",      "Bloco TI",         None,"36.000 BTU",0,"meses"),
    ("u42","AC_SPLIT",  "climatizacao","AC Oficina Eletrônica",None,"",     "Galpão Armas",     None,"18.000 BTU",0,"meses"),
    ("u43","AC_CENTRAL","climatizacao","Chiller Bloco Admin", None,"PAT-4521","Casa de Máquinas",None,"Chiller 20TR",0,"meses"),

    # ── GERADORES ──────────────────────────────────────────────────────────────
    ("u50","GERADOR","eletrica","GMG-01 Gerador Principal", None,"PAT-7810","Casa de Força",None,"150 kVA diesel",0,"h"),
    ("u51","GERADOR","eletrica","GMG-02 Gerador Emergência",None,"PAT-7811","Bloco Admin",  None,"75 kVA diesel", 0,"h"),
]


async def seed():
    db = CoreDB(DB_PATH)
    await db.init()

    inserted = updated = 0
    for row in ATIVOS:
        aid, tipo, cat, nome, placa, pat, loc, subtipo, obs, uso, unidade = row
        exists = await db.fetch_one("SELECT id FROM ativos WHERE id = ?", (aid,))
        if exists:
            await db.execute(
                """UPDATE ativos SET tipo=?, categoria=?, nome=?, placa=?, pat=?,
                   loc=?, subtipo=?, obs=?, unidade_uso=?
                   WHERE id=?""",
                (tipo, cat, nome, placa, pat, loc, subtipo, obs, unidade, aid),
            )
            updated += 1
        else:
            await db.execute(
                """INSERT INTO ativos
                   (id, tipo, categoria, nome, placa, pat, loc, subtipo, obs, uso_atual, unidade_uso, ativo)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,1)""",
                (aid, tipo, cat, nome, placa, pat, loc, subtipo, obs, uso, unidade),
            )
            inserted += 1

    print(f"Seed concluído: {inserted} inseridos, {updated} atualizados.")
    print(f"Total: {len(ATIVOS)} ativos")


if __name__ == "__main__":
    asyncio.run(seed())
