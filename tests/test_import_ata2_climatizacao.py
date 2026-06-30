"""ATA2 climatização: helpers de parsing + modelo serviço-reusável / plano-conjunto.

A fonte HTML (.docs_cmasm/ata2_carioca_solution.html) foi removida do repo após a
importação ser concluída — os dados já estão no DB de produção (catalogo_planos /
catalogo_plano_itens).  O teste test_parse_ata2_estrutura é ignorado quando o arquivo
fonte não existe.  Os dois primeiros testes (slug/variante) usam apenas funções puras e
continuam rodando sempre.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from tools.import_ata2_climatizacao import slug, variante, HTML  # noqa: E402

_HTML_AVAILABLE = os.path.isfile(HTML)


def test_slug_sem_acento():
    assert slug("Desmontagem parcial do equipamento") == "DESMONTAGEM_PARCIAL_DO_EQUIPAMENTO"
    assert slug("Revisão elétrica (aperto e limpeza dos terminais)") == "REVISAO_ELETRICA_APERTO_E_LIMPEZA_DOS_TERMINAIS"
    assert slug("Carga de gás 4 kg") == "CARGA_DE_GAS_4_KG"


def test_variante():
    v = variante("Split 18.000 BTU INVERTER — até 10m")
    assert v == {"btu": 18000, "inverter": 1, "altura_max_m": 10.0}
    v2 = variante("Split 24.000 BTU — até 3m")
    assert v2 == {"btu": 24000, "inverter": 0, "altura_max_m": 3.0}


@pytest.mark.skipif(not _HTML_AVAILABLE, reason="fonte HTML retirada do repo; ATA2 já importada para o DB")
def test_parse_ata2_estrutura():
    from tools.import_ata2_climatizacao import parse_ata2  # noqa: E402
    grupos = parse_ata2()
    assert len(grupos) == 12                       # 18/22/24k × padrão/inverter × 3/10m
    descs = {it["desc"] for g in grupos for it in g["itens"]}
    assert len(descs) == 30                         # serviços distintos reusáveis
    prev = {it["desc"] for g in grupos for it in g["itens"] if it["tipo"] == "prev"}
    assert len(prev) == 9                           # conjunto preventivo
