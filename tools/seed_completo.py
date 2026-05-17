#!/usr/bin/env python3
"""
seed_completo.py — Importação completa de dados do CMASM
Fontes:
  - .docs_cmasm/cmasm_cargos.csv         → 79 cargos + ocupantes
  - .docs_cmasm/cmasm_backup.json         → estrutura org (79 nós) + 12 users base
  - .docs_cmasm/TMFT - CMASM-10.csv      → postos dos militares (CMASM-10)
  - .docs_cmasm/Mapa de VTR e EMB ATU 20FEV26.csv → viaturas e embarcações
  - xCMASM/.delete/.old/CMASM_Gestao_v2.html → máquinas xGrama + materiais
"""

import csv
import json
import os
import re
import sqlite3
import sys
import time

BASE = os.path.join(os.path.dirname(__file__), "..")
DOCS = os.path.join(BASE, "..", "xCMASM", ".docs_cmasm")
if not os.path.isdir(DOCS):
    DOCS = os.path.join(BASE, ".docs_cmasm")
DB_PATH = os.path.join(BASE, "data", "core.db")
LEGACY_HTML = os.path.join(BASE, "..", "xCMASM", ".delete", ".old", "CMASM_Gestao_v2.html")

DEFAULT_PW = "170842"  # hashPw('1234') djb2 hex

def djb2_hex(s: str) -> str:
    """Mesmo algoritmo do backend (main.py _djb2)."""
    h = 0
    for c in s:
        h = ((h << 5) - h + ord(c)) & 0xFFFFFFFF
        if h >= 0x80000000:
            h -= 0x100000000
    return format(h, 'x') if h >= 0 else format(h & 0xFFFFFFFF, 'x')

assert djb2_hex('1234') == DEFAULT_PW, f"hash check failed: {djb2_hex('1234')} != {DEFAULT_PW}"

def read_csv(path, encoding='utf-8-sig'):
    if not os.path.exists(path):
        print(f"  [SKIP] {path} não encontrado")
        return []
    with open(path, encoding=encoding, errors='replace') as f:
        return list(csv.DictReader(f))


# ── 1. Ler todos os documentos ──────────────────────────────────────────────

print("=" * 60)
print("Lendo documentos...")

# 1a. cmasm_cargos.csv — 79 cargos com ocupantes
cargos_rows = read_csv(os.path.join(DOCS, "cmasm_cargos.csv"))
print(f"  cmasm_cargos.csv: {len(cargos_rows)} cargos")

# 1b. cmasm_backup.json — estrutura + users base
with open(os.path.join(DOCS, "cmasm_backup.json")) as f:
    backup = json.load(f)
estrutura_nodes = backup["estrutura"]
backup_users = backup["users"]
print(f"  cmasm_backup.json: {len(estrutura_nodes)} nós estrutura, {len(backup_users)} users")

# 1c. TMFT CMASM-10 — postos por nome
tmft_rows = read_csv(os.path.join(DOCS, "TMFT - CMASM-10.csv"))
print(f"  TMFT CMASM-10.csv: {len(tmft_rows)} linhas")

# 1d. Mapa VTR/EMB
mapa_rows = read_csv(os.path.join(DOCS, "Mapa de VTR e EMB ATU 20FEV26.csv"))
print(f"  Mapa VTR/EMB: {len(mapa_rows)} linhas")

# 1e. Legacy HTML — máquinas + peças xGrama
grama_unidades = []
grama_pecas = []
if os.path.exists(LEGACY_HTML):
    with open(LEGACY_HTML) as f:
        html = f.read()
    # Extract UNIDADES_DEFAULT
    m = re.search(r'const UNIDADES_DEFAULT = \[(.*?)\];', html, re.DOTALL)
    if m:
        for item in re.finditer(r'\{id:\'(\w+)\',tipo:\'(\w+)\',\s*nome:\'([^\']+)\'', m.group(1)):
            grama_unidades.append({'id': item.group(1), 'tipo': item.group(2), 'nome': item.group(3)})
    # Extract PECAS_DEFAULT
    m = re.search(r'const PECAS_DEFAULT = \[(.*?)\];', html, re.DOTALL)
    if m:
        for item in re.finditer(r"\{id:'(\w+)',d:'([^']+)',\s*un:'([^']+)',\s*cat:'([^']+)',\s*pr:([\d.]+)\}", m.group(1)):
            grama_pecas.append({
                'id': item.group(1), 'nome': item.group(2),
                'un': item.group(3), 'cat': item.group(4), 'preco': float(item.group(5))
            })
    print(f"  CMASM_Gestao_v2.html: {len(grama_unidades)} máquinas, {len(grama_pecas)} peças")
else:
    print("  [SKIP] CMASM_Gestao_v2.html não encontrado")

# ── 2. Montar mapa de postos a partir do TMFT ─────────────────────────────

print("\nMontando mapa de postos (TMFT)...")
# Extrair posto do campo "TITULAR" e "SUBSTITUTO" que vêm no formato "POSTO NOME" ou "POSTO (CORP) NOME"
def parse_posto_nome(s):
    """Ex: 'CC (EN) PATRÍCIA YARA' → ('CC(EN)', 'Patricia Yara')"""
    if not s or s.strip() in ('', '-', 'VAGO'):
        return None, None
    s = s.strip()
    # "SO RM1 OLAVO" → posto=SO, nome=OLAVO
    # "CB DEOMAR" → posto=CB, nome=DEOMAR
    # "CC (EN) PATRÍCIA YARA" → posto=CC(EN), nome=PATRÍCIA YARA
    m = re.match(r'^(\d?[A-Z]+(?:\s*\([\w-]+\))?(?:\s+RM[-\d]+)?)\s+(.+)$', s)
    if m:
        posto = re.sub(r'\s+', '', m.group(1))  # remove spaces inside posto
        nome = m.group(2).strip().title()
        return posto, nome
    return None, s.strip().title()

posto_map = {}  # nome_normalizado → posto
for row in tmft_rows:
    for field in ('TITULAR', 'SUBSTITUTO'):
        val = row.get(field, '').strip()
        posto, nome = parse_posto_nome(val)
        if nome and posto:
            key = nome.lower().strip()
            if key not in posto_map:
                posto_map[key] = posto

# Adicionar postos conhecidos do backup/TMFT
POSTOS_CONHECIDOS = {
    'patricia yara': 'CC(EN)',
    'geovanio': 'CT(AA)',
    'suellen': 'CT(RM2-EN)',
    'luciano ferreira': '1T(RM2-EN)',
    'bernardo maia': 'CT',
    'perozzi': 'CT',
    'bianca': 'CC',
    'pimentel': 'CT',
    'tarik': 'CC',
    'thomas baptista': 'CF',
    'ramalho': 'CMG',
    'vanessa': '1TEN',
}
for k, v in POSTOS_CONHECIDOS.items():
    posto_map.setdefault(k, v)

print(f"  Postos mapeados: {len(posto_map)}")

# ── 3. Construir lista de usuários a partir dos cargos ───────────────────

print("\nMontando usuários a partir de cmasm_cargos.csv...")
# Mapear por nome normalizado
users_by_nome = {}
for u in backup_users:
    key = u['nome'].lower().strip()
    users_by_nome[key] = u

# Percorrer cargos e coletar todos os ocupantes únicos
ocupantes = {}  # nome → {nome, posto, cargo_id, cargo_titulo}
for row in cargos_rows:
    ocu = row.get('OCUPANTE', '').strip()
    if not ocu or ocu.upper() in ('', '-', 'VAGO', 'N/A'):
        continue
    key = ocu.lower()
    if key not in ocupantes:
        posto = row.get('POSTO', '').strip() or posto_map.get(key, '')
        ocupantes[key] = {
            'nome': ocu,
            'posto': posto,
            'cargo_id': row['CODIGO'],
            'cargo_titulo': row['CARGO'],
            'tipo': 'militar',
            'role': 'gestor',
        }

# Enriquecer com postos do mapa
for key, ocu in ocupantes.items():
    if not ocu['posto']:
        ocu['posto'] = posto_map.get(key, '')

print(f"  Ocupantes únicos encontrados: {len(ocupantes)}")
for k, v in ocupantes.items():
    print(f"    {v['nome']:<22} posto={v['posto']:<12} cargo={v['cargo_id']}")

# ── 4. Conectar ao banco ──────────────────────────────────────────────────

print("\nConectando ao banco...")
db = sqlite3.connect(DB_PATH)
db.row_factory = sqlite3.Row

# ── 5. Limpar tabelas (exceto estrutura que já está correta) ──────────────

print("Limpando tabelas...")
db.execute("DELETE FROM cargos")
db.execute("DELETE FROM usuarios")
# Não apaga ativos e estoque completamente — remove só os seeds genéricos
db.execute("DELETE FROM ativos WHERE categoria='viaturas' OR categoria='embarcacoes'")
db.commit()

# ── 6. Inserir usuários ───────────────────────────────────────────────────

print("\nInserindo usuários...")
user_id_map = {}  # nome_lower → id
# Papel admin para chefes de departamento e direção
ADMIN_CARGOS = {'CMASM-01','CMASM-02','CMASM-10','CMASM-20','CMASM-30','CMASM-13.2','CMASM-13'}

# Incluir usuário admin padrão
admin_id = 1775404932719
db.execute("""
    INSERT OR IGNORE INTO usuarios(id,nome,posto,mat,email,tel,tipo,role,pw_hash)
    VALUES(?,?,?,?,?,?,?,?,?)
""", (admin_id, 'Administrador', '', 'ADM', '', '', 'civil', 'admin', DEFAULT_PW))

for key, ocu in ocupantes.items():
    # Reaproveitar ID do backup se existir
    base = users_by_nome.get(key)
    uid = base['id'] if base else int(time.time() * 1000) % (2**31) + hash(key) % 10000

    cargo_id = ocu['cargo_id']
    role = 'admin' if cargo_id in ADMIN_CARGOS or 'CHEFE' in ocu['cargo_titulo'].upper() else 'gestor'
    tipo = 'civil' if 'RJU' in str(ocu.get('cargo_titulo','')) else 'militar'

    mat = base['mat'] if base and base.get('mat') else None
    email = base['email'] if base and base.get('email') else None

    try:
        db.execute("""
            INSERT OR REPLACE INTO usuarios(id,nome,posto,mat,email,tel,tipo,role,pw_hash)
            VALUES(?,?,?,?,?,?,?,?,?)
        """, (uid, ocu['nome'], ocu['posto'], mat, email, '', tipo, role, DEFAULT_PW))
        user_id_map[key] = uid
        print(f"  ✓ {ocu['nome']:<22} ({ocu['posto']}) [{role}]")
    except Exception as e:
        print(f"  ✗ {ocu['nome']}: {e}")

db.commit()
print(f"  Total usuários inseridos: {len(user_id_map) + 1}")

# ── 7. Inserir cargos (todos os 79) ──────────────────────────────────────

print("\nInserindo cargos (todos os 79 posições)...")
cnt_cargos = 0
for row in cargos_rows:
    codigo = row['CODIGO'].strip()
    ocu = row.get('OCUPANTE', '').strip()
    obs = row.get('CARGO', '').strip()  # armazena o título do cargo em obs
    uid = None
    if ocu and ocu.upper() not in ('', '-', 'VAGO', 'N/A'):
        uid = user_id_map.get(ocu.lower())

    try:
        db.execute("""
            INSERT OR REPLACE INTO cargos(unidade_id, usuario_id, obs)
            VALUES(?,?,?)
        """, (codigo, uid, obs))
        cnt_cargos += 1
    except Exception as e:
        print(f"  ✗ cargo {codigo}: {e}")

db.commit()
print(f"  Total cargos inseridos: {cnt_cargos}")

# ── 8. Importar viaturas e embarcações ───────────────────────────────────

print("\nImportando viaturas e embarcações...")

VIATURAS = [
    # Do Mapa VTR/EMB (Mapa de VTR e EMB ATU 20FEV26.csv)
    {'id': 'vtr-munk',     'tipo': 'Caminhão MUNK',         'subtipo': 'caminhao',       'nome': 'MUNK',            'placa': 'KPJ-8385', 'unidade_uso': 'km', 'categoria': 'viaturas'},
    {'id': 'vtr-s10',      'tipo': 'Pickup S-10',           'subtipo': 'pickup',         'nome': 'S-10',            'placa': 'LRZ-5099', 'unidade_uso': 'km', 'categoria': 'viaturas'},
    {'id': 'vtr-amb',      'tipo': 'Ambulância',            'subtipo': 'ambulancia',     'nome': 'Ambulância',      'placa': '',         'unidade_uso': 'km', 'categoria': 'viaturas'},
    {'id': 'vtr-doblo',    'tipo': 'Fiat Doblô 1.4',        'subtipo': 'utilitario',     'nome': 'Doblô 1.4',       'placa': '',         'unidade_uso': 'km', 'categoria': 'viaturas'},
    {'id': 'vtr-const',    'tipo': 'Caminhão Constellation', 'subtipo': 'caminhao',      'nome': 'Constellation',   'placa': '',         'unidade_uso': 'km', 'categoria': 'viaturas'},
    {'id': 'vtr-xcmg',     'tipo': 'Guindaste XCMG',        'subtipo': 'guindaste',      'nome': 'XCMG (Guindaste)','placa': '',         'unidade_uso': 'h',  'categoria': 'viaturas'},
    # Embarcações
    {'id': 'emb-fatima',   'tipo': 'ETPM',                  'subtipo': 'lancha_pessoal', 'nome': 'ETPM FÁTIMA',     'placa': 'CMASM-08', 'unidade_uso': 'h',  'categoria': 'embarcacoes'},
    {'id': 'emb-natal',    'tipo': 'Lancha',                'subtipo': 'lancha',         'nome': 'LANCHA NATAL',    'placa': 'CMASM-05', 'unidade_uso': 'h',  'categoria': 'embarcacoes'},
    {'id': 'emb-sgt-frei', 'tipo': 'Embarcação de Apoio',   'subtipo': 'apoio',          'nome': 'Sargento Freitas','placa': 'CMASM-10', 'unidade_uso': 'h',  'categoria': 'embarcacoes'},
]

# Viaturas adicionais conhecidas do CMASM (frota típica naval)
VIATURAS += [
    {'id': 'vtr-onibus',   'tipo': 'Ônibus',               'subtipo': 'onibus',         'nome': 'Ônibus de Pessoal', 'placa': '',       'unidade_uso': 'km', 'categoria': 'viaturas'},
    {'id': 'vtr-kombi',    'tipo': 'Kombi / Van',          'subtipo': 'van',            'nome': 'Van de Pessoal',  'placa': '',         'unidade_uso': 'km', 'categoria': 'viaturas'},
]

cnt_vtr = 0
for v in VIATURAS:
    try:
        db.execute("""
            INSERT OR IGNORE INTO ativos(id, tipo, subtipo, categoria, nome, placa, unidade_uso, obs)
            VALUES(?,?,?,?,?,?,?,?)
        """, (v['id'], v['tipo'], v.get('subtipo',''), v['categoria'],
              v['nome'], v.get('placa',''), v['unidade_uso'], ''))
        cnt_vtr += 1
        print(f"  ✓ {v['nome']:<25} [{v['categoria']}] placa={v.get('placa','')}")
    except Exception as e:
        print(f"  ✗ {v['nome']}: {e}")

db.commit()
print(f"  Total viaturas/embarcações: {cnt_vtr}")

# ── 9. Máquinas xGrama (se não existirem) ────────────────────────────────

if grama_unidades:
    print("\nVerificando máquinas xGrama...")
    existentes = {r[0] for r in db.execute("SELECT id FROM ativos WHERE categoria='maquinas_corte'")}
    cnt_g = 0
    for u in grama_unidades:
        if u['id'] not in existentes:
            db.execute("""
                INSERT OR IGNORE INTO ativos(id, tipo, categoria, nome, unidade_uso)
                VALUES(?,?,?,?,?)
            """, (u['id'], u['tipo'], 'maquinas_corte', u['nome'], 'h'))
            cnt_g += 1
    db.commit()
    print(f"  {cnt_g} máquinas adicionadas ({len(existentes)} já existiam)")

# ── 10. Materiais xGrama no estoque ──────────────────────────────────────

if grama_pecas:
    print("\nImportando materiais xGrama para o estoque...")
    existentes = {r[0] for r in db.execute("SELECT codigo FROM estoque WHERE codigo LIKE 'GR-%'")}
    cnt_e = 0
    for p in grama_pecas:
        cod = f"GR-{p['id'].upper()}"
        if cod in existentes:
            continue
        cat_map = {
            'oleo': 'lubrificantes', 'graxa': 'lubrificantes',
            'filtro': 'filtros', 'motor': 'pecas_motor',
            'corte': 'consumiveis', 'correia': 'pecas_motor',
            'pneu': 'consumiveis', 'eletric': 'eletrica',
        }
        categoria = cat_map.get(p['cat'], 'material')
        try:
            db.execute("""
                INSERT INTO estoque(codigo, nome, categoria, unidade, qtd_atual, qtd_minima, preco_unitario, obs)
                VALUES(?,?,?,?,?,?,?,?)
            """, (cod, p['nome'], categoria, p['un'], 0, 2, p['preco'], 'Insumo xGrama'))
            cnt_e += 1
        except Exception as e:
            print(f"  ✗ {p['nome']}: {e}")
    db.commit()
    print(f"  {cnt_e} itens adicionados ao estoque")

# ── 11. Resumo final ──────────────────────────────────────────────────────

print("\n" + "=" * 60)
print("RESUMO FINAL")
print("=" * 60)
for t in ['usuarios', 'cargos', 'estrutura', 'locais', 'ativos', 'estoque']:
    n = db.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
    print(f"  {t:<15}: {n}")

print()
print("✅ Importação completa!")
print()
print("Login: qualquer nome da lista acima + senha '1234'")
print(f"       Ex: Ramalho / 1234")
db.close()
