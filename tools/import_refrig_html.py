#!/usr/bin/env python3
"""Importa as 171 maquinas AC do app de campo (html) para o core como fonte
autoritativa de refrigeracao. Substitui o dataset climatizacao (162) — seguro
pois nenhuma OS referencia ativos climatizacao.

- backup do db antes
- add coluna ativos.local_id (aditivo)
- resolve local_id casando predio/local na arvore `locais` (substring bidirecional)
- substitui ativos climatizacao + pmoc_refrigeracao pelos 171 do html

Idempotente: re-rodar reconstroi os refri### a partir do html.

ponytail: matching por nome normalizado + substring. Cobre o ruido de
nomenclatura visto no diff; nao-casados ficam com local_id=NULL e sao logados.
"""
import re, json, sqlite3, sys, unicodedata, shutil, datetime, os

DB = os.path.join(os.path.dirname(__file__), '..', 'data', 'core.db')
HTML = os.path.join(os.path.dirname(__file__), '..', '.docs_cmasm', 'cmasm13-govbr-v8_3 (1).html')

TIPO_MAP = {'SPLIT': 'AC_SPLIT', 'PISO/TETO': 'AC_PISO_TETO',
            'JANELA': 'AC_JANELA', 'SELF CONTAINED': 'AC_SELF'}

def norm(s):
    s = (s or '').strip().upper()
    s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    return re.sub(r'\s+', ' ', s)

def submatch(a, b):
    """True se a e b 'casam' por igualdade ou substring em qualquer direcao."""
    return a == b or (len(a) >= 4 and a in b) or (len(b) >= 4 and b in a)

def load_html():
    src = open(HTML, encoding='utf-8').read()
    return json.loads(re.search(r'const INITIAL_DATA = (\[.*?\]);', src, re.S).group(1))

def ensure_local_id_col(c):
    cols = [d[1] for d in c.execute("PRAGMA table_info(ativos)")]
    if 'local_id' not in cols:
        c.execute("ALTER TABLE ativos ADD COLUMN local_id INTEGER REFERENCES locais(id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_ativos_local ON ativos(local_id)")
        print("  + coluna ativos.local_id criada")
    else:
        print("  = ativos.local_id ja existe")

def build_loc_index(c):
    predios = []   # (id, norm_nome)
    salas = {}     # parent_id -> list[(id, norm_nome)]
    for lid, nome, parent in c.execute("SELECT id, nome, parent_id FROM locais"):
        if parent is None:
            predios.append((lid, norm(nome)))
        else:
            salas.setdefault(parent, []).append((lid, norm(nome)))
    return predios, salas

def resolve_local(predio, local, predios, salas):
    npre, nloc = norm(predio), norm(local)
    pid = None
    for lid, nm in predios:
        if submatch(npre, nm):
            pid = lid; break
    if pid is None:
        return None, 'predio-nao-encontrado'
    # sala dentro do predio
    for lid, nm in salas.get(pid, []):
        if submatch(nloc, nm):
            return lid, 'ok'
    return pid, 'predio-only'   # anexa no nivel predio

def main():
    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    bak = os.path.join(os.path.dirname(DB), f'core.backup_{ts}.db')
    shutil.copy(DB, bak)
    print(f"backup -> {bak}")

    data = load_html()
    print(f"html: {len(data)} maquinas")

    c = sqlite3.connect(DB)
    ensure_local_id_col(c)
    predios, salas = build_loc_index(c)

    # resolve todos antes de mexer
    resolved = []
    stats = {'ok': 0, 'predio-only': 0, 'predio-nao-encontrado': 0}
    for m in data:
        lid, how = resolve_local(m['predio'], m['local'], predios, salas)
        stats[how] += 1
        resolved.append((m, lid, how))
    print("resolucao local_id:", stats)
    print("nao-casados (predio):")
    for m, lid, how in resolved:
        if how == 'predio-nao-encontrado':
            print(f"   id{m['id']:>3}  {m['predio']} / {m['local']}")

    # substitui dataset climatizacao
    old = c.execute("SELECT count(*) FROM ativos WHERE categoria='climatizacao'").fetchone()[0]
    c.execute("DELETE FROM pmoc_refrigeracao WHERE ativo_id IN (SELECT id FROM ativos WHERE categoria='climatizacao')")
    c.execute("DELETE FROM ativos WHERE categoria='climatizacao'")
    print(f"removidos {old} ativos climatizacao + pmoc_refrigeracao")

    ins_a = 0
    for m, lid, how in resolved:
        aid = f"refri{m['id']:03d}"
        tipo = TIPO_MAP.get(m['tipo'], 'AC_SPLIT')
        fab = m.get('fabricante') or ''
        nome = ' '.join(x for x in [m['tipo'], fab if fab != '-' else '', f"{m['btu']}BTU"] if x).strip()
        loc_txt = f"{m['predio']}/{m['local']}"
        crit = m.get('criticidade') or ''
        c.execute("""INSERT INTO ativos
            (id,tipo,categoria,nome,pat,loc,obs,ativo,uso_atual,unidade_uso,subtipo,criticidade,local_id)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (aid, tipo, 'climatizacao', nome, m.get('patrimonio') or None, loc_txt,
             m.get('obs') or None, 1, 0, 'h', m['tipo'], crit, lid))
        c.execute("""INSERT INTO pmoc_refrigeracao
            (ativo_id,local_id,estado_operacional,est_idade,obs,permanencia,criticidade,
             horas_dia,dias_semana,tensao_nominal,corrente_nominal,patrimonio,
             data_instalacao,ultima_manutencao,pmoc_csv_id,fabricante,btu,funciona,
             estado_conservacao,critico)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (aid, lid, 'OK' if m.get('funciona') == 'OK' else 'INOP', m.get('estado'),
             m.get('obs') or None, 1 if m.get('refrigPermanente') else 0, crit,
             m.get('horasDia'), m.get('diasSemana'), m.get('tensao'),
             m.get('correnteNominal'), m.get('patrimonio') or None,
             m.get('dataInstalacao') or None, m.get('ultimaManutencao') or None,
             m['id'], fab if fab != '-' else None, m.get('btu'), m.get('funciona'),
             m.get('estado'), 1 if crit == 'CRÍTICA' else 0))
        ins_a += 1
    c.commit()
    print(f"inseridos {ins_a} ativos + {ins_a} pmoc_refrigeracao")

    # verificacao
    na = c.execute("SELECT count(*) FROM ativos WHERE categoria='climatizacao'").fetchone()[0]
    np = c.execute("SELECT count(*) FROM pmoc_refrigeracao").fetchone()[0]
    nl = c.execute("SELECT count(*) FROM ativos WHERE categoria='climatizacao' AND local_id IS NOT NULL").fetchone()[0]
    print(f"VERIFY: ativos climatizacao={na} pmoc_refrigeracao={np} com local_id={nl}")
    assert na == len(data) and np == len(data), "contagem divergente!"
    c.close()
    print("OK")

if __name__ == '__main__':
    main()
