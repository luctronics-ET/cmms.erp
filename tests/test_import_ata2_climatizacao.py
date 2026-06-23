"""ATA2 climatização: parse do HTML + modelo serviço-reusável / plano-conjunto."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from tools.import_ata2_climatizacao import slug, variante, parse_ata2  # noqa: E402


def test_slug_sem_acento():
    assert slug("Desmontagem parcial do equipamento") == "DESMONTAGEM_PARCIAL_DO_EQUIPAMENTO"
    assert slug("Revisão elétrica (aperto e limpeza dos terminais)") == "REVISAO_ELETRICA_APERTO_E_LIMPEZA_DOS_TERMINAIS"
    assert slug("Carga de gás 4 kg") == "CARGA_DE_GAS_4_KG"


def test_variante():
    v = variante("Split 18.000 BTU INVERTER — até 10m")
    assert v == {"btu": 18000, "inverter": 1, "altura_max_m": 10.0}
    v2 = variante("Split 24.000 BTU — até 3m")
    assert v2 == {"btu": 24000, "inverter": 0, "altura_max_m": 3.0}


def test_parse_ata2_estrutura():
    grupos = parse_ata2()
    assert len(grupos) == 12                       # 18/22/24k × padrão/inverter × 3/10m
    descs = {it["desc"] for g in grupos for it in g["itens"]}
    assert len(descs) == 30                         # serviços distintos reusáveis
    prev = {it["desc"] for g in grupos for it in g["itens"] if it["tipo"] == "prev"}
    assert len(prev) == 9                           # conjunto preventivo
