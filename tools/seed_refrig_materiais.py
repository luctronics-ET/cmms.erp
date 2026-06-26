#!/usr/bin/env python3
"""Liga materiais (estoque refrigeração) aos serviços do catálogo
(catalogo_servico_materiais) — define o consumo de cada serviço. Antes: 0 para
climatização.

ponytail: idempotente — pula par (servico, material) já existente. material_id
referencia estoque.id (resolvido por codigo REF-*).
"""
import sqlite3, os, shutil, datetime, uuid

DB = os.path.join(os.path.dirname(__file__), '..', 'data', 'core.db')

# serviço (codigo) -> lista de (estoque codigo, qtd, unidade)
LINKS = {
    'AC_PREVENTIVA_AC_SPLIT':      [('REF-LIMP', 0.2, 'L'), ('REF-FAR', 1, 'un')],
    'AC_PREVENTIVA_AC_PISO_TETO':  [('REF-LIMP', 0.3, 'L'), ('REF-FAR', 1, 'un')],
    'AC_PREVENTIVA_AC_SELF':       [('REF-LIMP', 0.5, 'L'), ('REF-FAR', 2, 'un')],
    'AC_PREVENTIVA_AC_JANELA':     [('REF-LIMP', 0.1, 'L'), ('REF-FAR', 1, 'un')],
    'AC_CARGA_DE_GAS_2_KG':        [('REF-G410', 2, 'kg')],
    'AC_CARGA_DE_GAS_4_KG':        [('REF-G410', 4, 'kg')],
    'AC_PRESSURIZACAO_COM_NITROGENIO_VAZAMENTO': [('REF-N2', 1, 'un')],
    'AC_VACUO_NO_SISTEMA_BOMBA_DE_VACUO':        [('REF-OLEO', 0.2, 'L')],
    'AC_AJUSTES_E_SOLDA_PARA_SANAR_VAZAMENTO_DE_GAS': [('REF-SOLDA', 2, 'un')],
    'AC_SUBST_CAPACITOR':          [('REF-CAP', 1, 'un')],
    'AC_SUBST_CONJUNTO_DOS_FILTROS_DE_AR': [('REF-FAR', 1, 'un')],
    'AC_SUBST_SENSOR_DE_TEMPERATURA': [('REF-SENS', 1, 'un')],
    'AC_SUBST_PLACA_ELETRONICA_DA_EVAPORADORA': [('REF-PLEV', 1, 'un')],
    'AC_SUBST_PLACA_ELETRONICA_DA_CONDENSADORA': [('REF-PLCD', 1, 'un')],
    'AC_SUBST_BOMBA_DE_DRENO_34_L_H': [('REF-BDRE', 1, 'un')],
    'AC_SUBST_CONTROLE_REMOTO':    [('REF-CTRL', 1, 'un')],
    'AC_SUBST_MOTOR_VENTILADOR_DA_CONDENSADORA': [('REF-MVENT', 1, 'un')],
    'AC_SUBST_2M_CABO_PP_5_VIAS':  [('REF-CABO', 2, 'm')],
    'AC_SUBST_2M_ISOLAMENTO_BAIXA_E_ALTA_PRESSAO': [('REF-ISOL', 2, 'm')],
}

def main():
    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    bak = os.path.join(os.path.dirname(DB), f'core.backup_{ts}.db')
    shutil.copy(DB, bak)
    print(f"backup -> {bak}")

    c = sqlite3.connect(DB)
    # resolve ids
    svc = {r[1]: r[0] for r in c.execute(
        "SELECT id, codigo FROM catalogo_servicos s WHERE versao = (SELECT MAX(versao) FROM catalogo_servicos x WHERE x.codigo = s.codigo)")}
    est = {r[1]: r[0] for r in c.execute("SELECT id, codigo FROM estoque")}

    before = c.execute("SELECT count(*) FROM catalogo_servico_materiais").fetchone()[0]
    ins, miss = 0, []
    for scod, mats in LINKS.items():
        sid = svc.get(scod)
        if not sid:
            miss.append(scod); continue
        for mcod, qtd, un in mats:
            mid = est.get(mcod)
            if not mid:
                miss.append(mcod); continue
            ja = c.execute(
                "SELECT 1 FROM catalogo_servico_materiais WHERE servico_id=? AND material_id=?",
                (sid, mid)).fetchone()
            if ja:
                continue
            c.execute(
                "INSERT INTO catalogo_servico_materiais (servico_id, material_id, qtd, unidade, obrigatorio) VALUES (?,?,?,?,1)",
                (sid, mid, qtd, un))
            ins += 1
    c.commit()
    after = c.execute("SELECT count(*) FROM catalogo_servico_materiais").fetchone()[0]
    print(f"catalogo_servico_materiais: {before} -> {after} (+{ins})")
    clim = c.execute(
        "SELECT count(*) FROM catalogo_servico_materiais m JOIN catalogo_servicos s ON s.id=m.servico_id WHERE s.aplicavel_a LIKE '%climatizacao%'").fetchone()[0]
    print(f"materiais de serviços climatização: {clim}")
    if miss: print("não resolvidos:", sorted(set(miss)))
    c.close()
    print("OK")

if __name__ == '__main__':
    main()
