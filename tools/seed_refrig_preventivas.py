#!/usr/bin/env python3
"""Importa as 4 preventivas PMOC do app de campo (CHECKLIST por tipo de AC) para
catalogo_servicos do core. Complementa as 30 corretivas/peças da ARP — o core
não tinha preventivas de refrigeração (0 planos climatização).

1 serviço preventivo por tipo (Split/Piso-Teto/Janela/Self), com as tarefas do
checklist em descricao, tempo estimado (mesma fórmula do refrig-engine) e
aplicavel_a apontando o tipo de AC.

ponytail: INSERT OR IGNORE pelo id — idempotente. Tarefas em descricao (texto),
não como sub-serviços, até precisar de granularidade por item.
"""
import re, json, sqlite3, os, shutil, datetime

ROOT = os.path.join(os.path.dirname(__file__), '..')
DB = os.path.join(ROOT, 'data', 'core.db')
HTML = os.path.join(ROOT, '.docs_cmasm', 'cmasm13-govbr-v8_3 (1).html')

TIPO_MAP = {'SPLIT': ('AC_SPLIT', 'Split'), 'PISO/TETO': ('AC_PISO_TETO', 'Piso/Teto'),
            'JANELA': ('AC_JANELA', 'Janela'), 'SELF CONTAINED': ('AC_SELF', 'Self Contained')}
FATOR_EQ = {'SPLIT': 1.0, 'PISO/TETO': 1.15, 'JANELA': 0.7, 'SELF CONTAINED': 1.6}
MIN_ITEM, SETUP = 10, 15  # mesma fórmula do refrig-engine (preventiva fM=1.0)

def parse_checklists():
    src = open(HTML, encoding='utf-8').read()
    blk = re.search(r'var CHECKLIST = (\{.*?\n\});', src, re.S).group(1)
    out = {}
    for km in re.finditer(r"'([A-ZÇÃ/ ]+)':\s*\[(.*?)\]", blk, re.S):
        out[km.group(1)] = [x for x in re.findall(r"'([^']+)'", km.group(2))]
    return out

def main():
    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    bak = os.path.join(os.path.dirname(DB), f'core.backup_{ts}.db')
    shutil.copy(DB, bak)
    print(f"backup -> {bak}")

    cls = parse_checklists()
    c = sqlite3.connect(DB)
    before = c.execute("SELECT count(*) FROM catalogo_servicos").fetchone()[0]
    ins = 0
    for tipo, itens in cls.items():
        ac_code, label = TIPO_MAP.get(tipo, (None, tipo))
        if not ac_code:
            continue
        tempo = round(len(itens) * MIN_ITEM * FATOR_EQ.get(tipo, 1.0) + SETUP)
        sid = f"svc_ac_preventiva_{ac_code.lower()}"
        codigo = f"AC_PREVENTIVA_{ac_code}"
        nome = f"Preventiva PMOC — {label}"
        descricao = " ; ".join(itens)
        aplicavel = json.dumps({"categorias": ["climatizacao"], "tipos": [ac_code]}, ensure_ascii=False)
        c.execute(
            """INSERT OR IGNORE INTO catalogo_servicos
               (id, codigo, nome, descricao, escopo, tempo_estimado_min,
                aplicavel_a, criado_por_modulo, ativo)
               VALUES (?,?,?,?,?,?,?,?,1)""",
            (sid, codigo, nome, descricao, 'local', tempo, aplicavel, 'refrigeracao'),
        )
        if c.execute("SELECT changes()").fetchone()[0]:
            ins += 1
            print(f"  + {codigo} ({len(itens)} tarefas, {tempo}min)")
        else:
            print(f"  = {codigo} já existe")
    c.commit()
    after = c.execute("SELECT count(*) FROM catalogo_servicos").fetchone()[0]
    prev = c.execute("SELECT count(*) FROM catalogo_servicos WHERE upper(nome) LIKE '%PREVENT%'").fetchone()[0]
    print(f"catalogo_servicos: {before} -> {after} (+{ins}); preventivas agora: {prev}")
    c.close()
    print("OK")

if __name__ == '__main__':
    main()
