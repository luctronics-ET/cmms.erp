#!/usr/bin/env python3
"""Gera planos preventivos POR MÁQUINA para refrigeração — fecha o ciclo
serviço→plano→OS. Liga cada ativo climatizacao ao serviço preventivo do seu
tipo (AC_PREVENTIVA_*), com frequência calendário pela criticidade (PMOC_INT).

Criticidade via autoCrit (porta do refrig-engine.js): permanência, paióis,
servidor, saúde/segurança/comando, NOK, estado.

ponytail: INSERT OR IGNORE por id (plan-refrig-<ativo>). Re-rodar não duplica.
"""
import json, sqlite3, os, shutil, datetime, unicodedata

ROOT = os.path.join(os.path.dirname(__file__), '..')
DB = os.path.join(ROOT, 'data', 'core.db')

# AC tipo (subtipo do ativo) -> (codigo AC, id do serviço preventivo)
TIPO_MAP = {
    'SPLIT': ('AC_SPLIT', 'svc_ac_preventiva_ac_split'),
    'PISO/TETO': ('AC_PISO_TETO', 'svc_ac_preventiva_ac_piso_teto'),
    'JANELA': ('AC_JANELA', 'svc_ac_preventiva_ac_janela'),
    'SELF CONTAINED': ('AC_SELF', 'svc_ac_preventiva_ac_self'),
}
# intervalo preventiva (dias) por criticidade — PMOC_INT do refrig-engine
PREVENT_DIAS = {'CRÍTICA': 90, 'ALTA': 180, 'MÉDIA': 365, 'BAIXA': 365}

def _u(s):
    s = (s or '').upper()
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')

def auto_crit(perm, predio, local, funciona, estado):
    p, l = _u(predio), _u(local)
    if perm:
        return 'CRÍTICA'
    if any(x in l for x in ['SERVIDOR', 'INFORMATICA']):
        return 'CRÍTICA'
    if any(x in p for x in ['EXOCET', 'ASPIDE', 'F21', 'MK48', 'PCI', 'MISTRAL']):
        return 'CRÍTICA'
    if any(x in p for x in ['SAUDE', 'SEGURANCA', 'COMANDO']):
        return 'ALTA'
    if funciona == 'NOK':
        return 'ALTA'
    if estado in ('NOVA', 'SEMI'):
        return 'MÉDIA'
    return 'BAIXA'

def main():
    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    bak = os.path.join(os.path.dirname(DB), f'core.backup_{ts}.db')
    shutil.copy(DB, bak)
    print(f"backup -> {bak}")

    c = sqlite3.connect(DB)
    rows = c.execute(
        """
        SELECT a.id, a.subtipo,
               p.permanencia, p.funciona, p.estado_conservacao, p.ultima_manutencao,
               l.nome AS local_nome, lp.nome AS predio_nome
        FROM ativos a
        LEFT JOIN pmoc_refrigeracao p ON p.ativo_id = a.id
        LEFT JOIN locais l  ON l.id = p.local_id
        LEFT JOIN locais lp ON lp.id = l.parent_id
        WHERE a.categoria = 'climatizacao'
        """
    ).fetchall()
    print(f"climatizacao: {len(rows)} máquinas")

    before = c.execute("SELECT count(*) FROM planos_manutencao").fetchone()[0]
    ins = 0
    dist = {}
    for aid, subtipo, perm, funciona, estado, ultima, local_nome, predio_nome in rows:
        ac = TIPO_MAP.get(subtipo)
        if not ac:
            print(f"  ! {aid}: subtipo desconhecido '{subtipo}', pulado")
            continue
        ac_code, svc_id = ac
        predio = predio_nome or local_nome
        crit = auto_crit(bool(perm), predio, local_nome, funciona, estado)
        dist[crit] = dist.get(crit, 0) + 1
        dias = PREVENT_DIAS[crit]
        freq = json.dumps({"tipo": "calendario", "valor": dias, "unidade": "dias"})
        prox = None
        if ultima:
            try:
                d = datetime.date.fromisoformat(str(ultima)[:10]) + datetime.timedelta(days=dias)
                prox = d.isoformat()
            except Exception:
                prox = None
        # per-máquina: ativo_id setado, tipo_codigo NULL (CHECK XOR).
        # criticidade_override só aceita classe operacional — PMOC crit vai em obs.
        c.execute(
            """INSERT OR IGNORE INTO planos_manutencao
               (id, servico_id, ativo_id, tipo_codigo, frequencia,
                proxima_execucao, ultima_execucao, responsavel_pmoc, obs, ativo, criado_por_modulo)
               VALUES (?,?,?,NULL,?,?,?,?,?,1,'refrigeracao')""",
            (f"plan-refrig-{aid}", svc_id, aid, freq,
             prox, ultima, 'refrigeracao',
             f"Preventiva PMOC {crit} ({ac_code}) · a cada {dias}d — gerado de refrigeração."),
        )
        if c.execute("SELECT changes()").fetchone()[0]:
            ins += 1
    c.commit()
    after = c.execute("SELECT count(*) FROM planos_manutencao").fetchone()[0]
    print(f"planos_manutencao: {before} -> {after} (+{ins})")
    print("distribuição criticidade:", dist)
    # verifica
    nclim = c.execute(
        "SELECT count(*) FROM planos_manutencao WHERE criado_por_modulo='refrigeracao'"
    ).fetchone()[0]
    print(f"planos refrigeração: {nclim}")
    assert nclim == len([r for r in rows if r[1] in TIPO_MAP]), "contagem divergente"
    c.close()
    print("OK")

if __name__ == '__main__':
    main()
