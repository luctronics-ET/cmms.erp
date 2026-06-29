#!/usr/bin/env python3
"""
seed_from_backup.py — Importação limpa do xCMASM

Ordem de importação:
  1. estrutura  — organograma (79 nós do backup JSON)
  2. cargos     — quem ocupa cada posição
  3. usuarios   — 12 militares + enriquecimento TMFT + pw_hash padrão
  4. locais     — espaços físicos (paiois, galpões, blocos, áreas)
  5. ativos     — mantém seed existente (não apaga)

Execução:
  python3 tools/seed_from_backup.py [--clean-ativos]
"""

from __future__ import annotations
import csv, json, os, re, sys, sqlite3
from argon2 import PasswordHasher

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(BASE, "..")
DB   = os.path.join(ROOT, "data", "core.db")
SCH  = os.path.join(ROOT, "data", "schema_core.sql")
BCK  = os.path.join(ROOT, ".docs_cmasm", "cmasm_backup.json")
TMFT = os.path.join(ROOT, ".docs_cmasm", "TMFT - CMASM-10.csv")

# Senha de bootstrap — deve ser alterada no primeiro login.
INITIAL_PW = "ChangeMe@Boot"
_ph_seed = PasswordHasher()
DEFAULT_PW = _ph_seed.hash(INITIAL_PW)

# ── helpers ────────────────────────────────────────────────────────────────
def normalize_nome(s: str) -> str:
    """'CC (EN) PATRÍCIA YARA'  →  'Patricia Yara'"""
    # remove posto/corpo entre parênteses: CC (EN), 1T (RM2-EN), etc.
    s = re.sub(r"^[A-Z0-9]+ \([^)]+\)\s*", "", s.strip())
    return s.title()

def extract_posto(s: str) -> str:
    """'CC (EN) PATRÍCIA YARA' → 'CC'"""
    m = re.match(r"^([A-Z0-9]+)\s*\(", s.strip())
    return m.group(1) if m else ""

# ── carregar dados de referência ────────────────────────────────────────────
with open(BCK, encoding="utf-8") as f:
    backup = json.load(f)

estrutura_data = backup["estrutura"]   # 79 nós
cargos_data    = backup["cargos"]      # dict {unidade_id: {usuario_id, obs}}
users_data     = backup["users"]       # 12 usuários

# Enriquecer usuários com dados do TMFT
# Mapeamento nome_normalizado → {posto, neo_ids}
tmft_map: dict[str, dict] = {}
with open(TMFT, encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        for field in ("TITULAR", "SUBSTITUTO"):
            val = row.get(field, "").strip()
            if not val:
                continue
            nome = normalize_nome(val)
            posto = extract_posto(val)
            neo   = row.get("NEO – num ELEMENTO ORGANIZACIONAL", "").strip()
            if nome not in tmft_map:
                tmft_map[nome] = {"posto": posto, "neo": [neo]}
            else:
                if neo not in tmft_map[nome]["neo"]:
                    tmft_map[nome]["neo"].append(neo)

# ── conectar ao banco ───────────────────────────────────────────────────────
os.makedirs(os.path.dirname(DB), exist_ok=True)
db = sqlite3.connect(DB)
db.execute("PRAGMA foreign_keys = OFF")

with open(SCH, encoding="utf-8") as f:
    db.executescript(f.read())

# ── 1. ESTRUTURA — limpar e reimportar ────────────────────────────────────
db.execute("DELETE FROM cargos")
db.execute("DELETE FROM estrutura")

for e in estrutura_data:
    db.execute(
        "INSERT OR REPLACE INTO estrutura (id, tipo, nome, pai, cargo, ct) VALUES (?,?,?,?,?,?)",
        (e["id"], e["tipo"], e["nome"], e.get("pai"), e.get("cargo",""), e.get("ct","")),
    )
print(f"✓ estrutura: {len(estrutura_data)} nós importados")

# ── 2. CARGOS ──────────────────────────────────────────────────────────────
cargo_count = 0
for unidade_id, info in cargos_data.items():
    uid = info.get("usuario_id")
    if uid:
        db.execute(
            "INSERT OR REPLACE INTO cargos (unidade_id, usuario_id, obs) VALUES (?,?,?)",
            (unidade_id, int(uid), info.get("obs", "")),
        )
        cargo_count += 1
print(f"✓ cargos: {cargo_count} atribuições importadas")

# ── 3. USUARIOS ────────────────────────────────────────────────────────────
# Preservar usuários existentes, atualizar / inserir do backup
ucount = 0
for u in users_data:
    nome   = u["nome"]
    posto  = u.get("posto", "")
    # tentar enriquecer do TMFT
    nome_norm = nome.title()
    tmft = tmft_map.get(nome_norm, {})
    if not posto and tmft.get("posto"):
        posto = tmft["posto"]

    # gerar mat simples se não existir: primeiras letras do nome
    mat = u.get("mat") or ""
    if not mat:
        partes = nome.split()
        mat = "".join(p[0].upper() for p in partes) + str(u["id"])[-4:]

    db.execute(
        """INSERT OR REPLACE INTO usuarios
           (id, nome, posto, mat, email, tel, tipo, role, pw_hash, ativo)
           VALUES (?,?,?,?,?,?,?,?,?,1)""",
        (
            int(u["id"]), nome, posto, mat,
            u.get("email",""), u.get("tel",""),
            u.get("tipo","militar"), u.get("role","operador"),
            DEFAULT_PW,
        ),
    )
    ucount += 1
print(f"✓ usuarios: {ucount} importados (senha bootstrap: {INITIAL_PW!r} — ALTERE APÓS O PRIMEIRO LOGIN)")

# ── 4. LOCAIS — limpar org units, preservar físicos ───────────────────────
# Tipos que são unidades organizacionais (não locais físicos)
ORG_TIPOS = {
    "organizacao_raiz","organizacao","direcao","vice_direcao","assessoria","assessor",
    "chefe_gabinete","departamento","chefe_departamento","secretaria","secretario_depto",
    "divisao","encarregado_divisao","secao","encarregado_secao","grupo","encarregado_grupo",
    "servico","encarregado_servico","infraestrutura_org",
}
# Tipos que são locais físicos (manter/importar)
PHYS_TIPOS = {
    "predio","bloco","sala","area_externa","area","garagem","galp_armas",
    "galp_manutencao","complexo_paiol","paiol","infraestrutura","localizacao","instalacao",
}

# Remove apenas os org-units da tabela locais
placeholders = ",".join("?" * len(ORG_TIPOS))
deleted = db.execute(
    f"DELETE FROM locais WHERE tipo IN ({placeholders})", list(ORG_TIPOS)
).rowcount
print(f"✓ locais: {deleted} unidades organizacionais removidas da tabela errada")

# Inserir locais físicos que ainda não existem (idempotente por codigo UNIQUE)
LOCAIS_FISICOS = [
    # (codigo, neo, nome, tipo, area, restricao, parent_codigo, descricao)
    # ── Raiz física ───────────────────────────────────────────────────────
    ("CMASM",        "CMASM",   "Centro de Mísseis e Armas Submarinas",       "instalacao",     "OPE", "",         None,             "Instalação CMASM — Rio de Janeiro"),
    # ── Áreas externas ───────────────────────────────────────────────────
    ("CMASM-AE-CAI", "CAI",     "Cais Administrativo",                        "area_externa",   "ADM", "",         "CMASM",          ""),
    ("CMASM-AE-FUT", "FUT",     "Campo de Futebol",                           "area_externa",   "OPE", "",         "CMASM",          ""),
    ("CMASM-AE-EST", "EST",     "Estacionamento",                             "area_externa",   "ADM", "",         "CMASM",          ""),
    # ── Infraestrutura ───────────────────────────────────────────────────
    ("CMASM-INF-BOM","BOM",     "Casa de Bombas",                             "infraestrutura", "OPE", "",         "CMASM",          ""),
    ("CMASM-INF-ETA","ETA",     "Estação de Tratamento de Água (ETA)",        "infraestrutura", "OPE", "",         "CMASM",          ""),
    ("CMASM-INF-ETE","ETE",     "Estação de Tratamento de Esgoto (ETE)",      "infraestrutura", "OPE", "",         "CMASM",          ""),
    ("CMASM-INF-GER","GER",     "Casa de Geradores",                          "infraestrutura", "OPE", "",         "CMASM",          ""),
    # ── Garagem ──────────────────────────────────────────────────────────
    ("CMASM-GAR",    "GAR",     "Garagem de Viaturas",                        "garagem",        "OPE", "",         "CMASM",          ""),
    # ── Galpões ──────────────────────────────────────────────────────────
    ("CMASM-GAL-MAN","GALMAN",  "Galpão de Manutenção",                       "galp_manutencao","OPE", "",         "CMASM",          ""),
    ("CMASM-GAL-ARM","GALARMAS","Galpão de Armas",                            "galp_armas",     "OPE", "militar",  "CMASM",          ""),
    # ── Blocos ───────────────────────────────────────────────────────────
    ("CMASM-BLK-ADM","BLKADM",  "Bloco Administrativo",                       "bloco",          "ADM", "",         "CMASM",          "Prédio principal — Direção, Depto. Adm., Pessoal"),
    ("CMASM-BLK-TEC","BLKTEC",  "Bloco Técnico",                              "bloco",          "OPE", "militar",  "CMASM",          "Deptos. Armas e Infraestrutura"),
    ("CMASM-BLK-SAU","BLKSAU",  "Bloco de Saúde / Enfermaria",                "bloco",          "ADM", "",         "CMASM",          ""),
    ("CMASM-BLK-ALM","BLKALM",  "Almoxarifado",                               "bloco",          "OPE", "",         "CMASM",          ""),
    # ── Complexo de Paiois ───────────────────────────────────────────────
    ("CMASM-PAIOIS",  "PAIOIS", "Complexo de Paiois de Armamento",            "complexo_paiol", "OPE", "reservado","CMASM",          ""),
]
# Gerar 65 paiois individualmente
for n in range(1, 66):
    cod = f"CMASM-PAIOL-{n:02d}"
    neo = f"PAIOL-{n:02d}"
    LOCAIS_FISICOS.append((cod, neo, f"Paiol de Armamento {n:02d}", "paiol", "OPE", "reservado", "CMASM-PAIOIS", ""))

# Resolver parent_id por codigo
def get_local_id(db, codigo):
    row = db.execute("SELECT id FROM locais WHERE codigo=?", (codigo,)).fetchone()
    return row[0] if row else None

# Inserir em ordem (raiz primeiro, depois filhos)
inserted = 0
for rec in LOCAIS_FISICOS:
    codigo, neo, nome, tipo, area, restricao, parent_cod, descricao = rec
    parent_id = get_local_id(db, parent_cod) if parent_cod else None
    try:
        db.execute(
            """INSERT OR IGNORE INTO locais
               (codigo, neo, nome, tipo, area, restricao, parent_id, descricao, ativo)
               VALUES (?,?,?,?,?,?,?,?,1)""",
            (codigo, neo, nome, tipo, area, restricao, parent_id, descricao),
        )
        inserted += db.execute("SELECT changes()").fetchone()[0]
    except Exception as e:
        print(f"  WARN locais insert {codigo}: {e}")

print(f"✓ locais: {inserted} locais físicos inseridos")

# ── 5. ATIVOS — apenas estatísticas ───────────────────────────────────────
n_ativos = db.execute("SELECT COUNT(*) FROM ativos").fetchone()[0]
print(f"  ativos: {n_ativos} já presentes (não alterados)")

# ── Finalizar ──────────────────────────────────────────────────────────────
db.execute("PRAGMA foreign_keys = ON")
db.commit()
db.close()

print()
print("══ Resumo do banco ══")
db2 = sqlite3.connect(DB)
for table in ("estrutura","cargos","usuarios","locais","ativos","estoque"):
    try:
        n = db2.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"  {table:20}: {n:4} rows")
    except: pass
db2.close()
print()
print(f"✓ Importação concluída. Login: qualquer nome · senha bootstrap: {INITIAL_PW!r} — ALTERE APÓS O PRIMEIRO LOGIN")
