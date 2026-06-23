"""Parsers do importador CSV de refrigeração — onde a planilha suja quebra."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from tools.import_refrigeracao_csv import inteiro, real, flag_x, slug, TIPO_MAP  # noqa: E402


def test_inteiro_milhar():
    assert inteiro("48,000") == 48000      # separador de milhar BR
    assert inteiro("12,000") == 12000
    assert inteiro("3") == 3
    assert inteiro("") is None
    assert inteiro("texto") is None


def test_real_e_flag():
    assert real("8") == 8.0
    assert real("2,5") == 2.5
    assert real("") is None
    assert flag_x("X") == 1
    assert flag_x("x") == 1
    assert flag_x("") == 0


def test_slug_e_tipos():
    assert slug("ADMINISTRATIVA", "ACADEMIA", "BARBEARIA") == "REFRI-ADMINISTRATIVA-ACADEMIA-BARBEARIA"
    assert slug("PAIOL", "", "PAIOL 1") == "REFRI-PAIOL-PAIOL-1"
    assert TIPO_MAP["SPLIT INVERTER"] == "AC_SPLIT"   # inverter = variante de split
    assert TIPO_MAP["SELF CONTAINED"] == "AC_SELF"
