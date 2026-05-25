"""
Gera os JSONs de seed do PMOC único.

Lê:
  - tools/seed_ativos.py            → lista ATIVOS (cadastro autoritativo do núcleo)
  - pmoc.refs/CMASM_PMOC_REFRIG*.csv → 171 ativos de refrigeração com detalhes
  - pmoc.refs/pmoc_maq-agricola_dados.csv → catálogo de peças de máquinas

Escreve em pmoc/seeds/:
  - ativos.json                     (apenas 4 categorias da 1ª entrega)
  - refrigeracao-detalhe.json       (BTU, gás, criticidade, etc.)
  - locais.json                     (derivado dos locais únicos dos ativos)
  - estoque-catalogo.json           (peças de máquinas + materiais básicos refrig.)
  - planos.json                     (intervalos por tipo, extraídos de Regras §3)

Idempotente. Rodar quando seeds precisarem ser atualizados.

Uso:
    cd cmasm.erp
    python pmoc/tools/gen_seeds.py
"""
import csv
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PMOC_REFS = ROOT.parent / "pmoc.refs"
SEEDS_DIR = ROOT / "pmoc" / "seeds"

# Importa ATIVOS de tools/seed_ativos.py sem rodar o seed
sys.path.insert(0, str(ROOT))
from tools.seed_ativos import ATIVOS  # noqa: E402

CATEGORIAS_ENTREGA = {"climatizacao", "maquinas_corte", "viaturas", "embarcacoes"}


def gen_ativos():
    out = []
    for row in ATIVOS:
        aid, tipo, cat, nome, placa, pat, loc, subtipo, obs, uso, unidade = row
        if cat not in CATEGORIAS_ENTREGA:
            continue
        out.append({
            "id": aid,
            "tipo": tipo,
            "categoria": cat,
            "nome": nome,
            "placa": placa,
            "pat": pat,
            "loc": loc,
            "subtipo": subtipo,
            "obs": obs,
            "uso_atual": uso,
            "unidade_uso": unidade,
            "ativo": 1,
            "criticidade": "operacional",
        })
    return out


def gen_locais(ativos):
    nomes = sorted({a["loc"] for a in ativos if a.get("loc")})
    return [{"id": f"loc_{i+1:03d}", "nome": n} for i, n in enumerate(nomes)]


def _num(v):
    if v is None or v == "":
        return None
    try:
        return float(str(v).replace(",", "."))
    except ValueError:
        return None


def gen_refrig_detalhe():
    src = PMOC_REFS / "CMASM_PMOC_REFRIG - CMASM_PMOC_REFRI.csv"
    out = []
    with src.open(encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for r in reader:
            if not r.get("ID"):
                continue
            out.append({
                "id": f"refr_{int(r['ID']):03d}",
                "area": r.get("LOCAL.AREA") or None,
                "edificio": r.get("LOCAL.EDIFICIO") or None,
                "ambiente": r.get("LOCAL.AMBIENTE") or None,
                "tipo": r.get("ATIVO.TIPO") or None,
                "marca": r.get("ATIVO.MARCA") or None,
                "modelo": r.get("ATIVO.MODELO") or None,
                "btu": _num(r.get("ATIVO.BTU")),
                "estado_operacional": r.get("ATIVO.EST.OPERACIONAL") or None,
                "idade": r.get("ATIVO.EST.IDADE") or None,
                "criticidade": r.get("REFRI.CRITICIDADE") or None,
                "horas_dia": _num(r.get("ATIVO.REFRI.H/DIA")),
                "dias_semana": _num(r.get("REFRI.D/SEM")),
                "tensao": _num(r.get("ATIVO.ELE.TENSÃO")),
                "corrente_a": _num(r.get("CORRENTE(A)")),
                "potencia_kw": _num(r.get("POTÊNCIA(kW)")),
                "gas": r.get("GÁS EST.") or None,
                "carga_g": _num(r.get("CARGA EST.(g)")),
                "patrimonio": r.get("PATRIMÔNIO") or None,
                "obs": r.get("ATIVO.REFRI.OBS") or None,
            })
    return out


def gen_pecas_maq_corte():
    src = PMOC_REFS / "pmoc_maq-agricola_dados.csv"
    out = []
    with src.open(encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for r in reader:
            num = r.get("#") or r.get("﻿#") or ""
            num = num.strip()
            if not num or not num.isdigit():
                continue
            out.append({
                "id": f"peca_corte_{int(num):03d}",
                "descricao": r.get("Descrição"),
                "unidade": r.get("UN"),
                "preco_unit": _num(r.get("Preço Unit (R$)")),
                "intervalo_h": _num(r.get("Intervalo (h)")),
                "vida_util_h": _num(r.get("Vida Útil (h)")),
                "categoria": r.get("Categoria"),
                "essencial": r.get("Essencial") == "S",
                "regular": r.get("Regular") == "S",
                "otimo": r.get("Ótimo") == "S",
                "aplicavel_a": "maquinas_corte",
            })
    return out


def gen_estoque_catalogo():
    pecas_corte = gen_pecas_maq_corte()
    # Materiais básicos de refrigeração (extraídos do Guia Normativo e do POP)
    refrig = [
        {"id": "mat_gas_r410a", "descricao": "Gás R-410A", "unidade": "kg",
         "preco_unit": 350.0, "categoria": "refrigeracao", "aplicavel_a": "climatizacao"},
        {"id": "mat_gas_r22",   "descricao": "Gás R-22",   "unidade": "kg",
         "preco_unit": 280.0, "categoria": "refrigeracao", "aplicavel_a": "climatizacao"},
        {"id": "mat_solucao_limpeza_ac", "descricao": "Solução de limpeza para serpentina",
         "unidade": "L", "preco_unit": 45.0, "categoria": "refrigeracao",
         "aplicavel_a": "climatizacao"},
        {"id": "mat_filtro_ar_split", "descricao": "Filtro de ar split (genérico)",
         "unidade": "un", "preco_unit": 28.0, "categoria": "refrigeracao",
         "aplicavel_a": "climatizacao"},
    ]
    # Materiais básicos de viaturas
    vtr = [
        {"id": "mat_oleo_5w30_4l", "descricao": "Óleo 5W-30 sintético 4L",
         "unidade": "L", "preco_unit": 180.0, "categoria": "lubrificante",
         "aplicavel_a": "viaturas"},
        {"id": "mat_filtro_oleo_vtr", "descricao": "Filtro de óleo (genérico viatura)",
         "unidade": "un", "preco_unit": 35.0, "categoria": "filtro",
         "aplicavel_a": "viaturas"},
        {"id": "mat_pastilha_freio", "descricao": "Pastilha de freio (jogo)",
         "unidade": "jg", "preco_unit": 120.0, "categoria": "freio",
         "aplicavel_a": "viaturas"},
    ]
    # Materiais básicos de embarcações
    emb = [
        {"id": "mat_oleo_nautico_2t", "descricao": "Óleo náutico 2T 1L",
         "unidade": "L", "preco_unit": 75.0, "categoria": "lubrificante",
         "aplicavel_a": "embarcacoes"},
        {"id": "mat_anodo_zinco", "descricao": "Ânodo de zinco",
         "unidade": "un", "preco_unit": 60.0, "categoria": "nautico",
         "aplicavel_a": "embarcacoes"},
        {"id": "mat_tinta_anti_incrust", "descricao": "Tinta anti-incrustante 1L",
         "unidade": "L", "preco_unit": 220.0, "categoria": "nautico",
         "aplicavel_a": "embarcacoes"},
    ]
    return pecas_corte + refrig + vtr + emb


def gen_planos():
    """Planos por tipo extraídos de Regras de Negocio e Fluxos.md §3."""
    return [
        # Máquinas de corte
        {"id": "plano_gar_oleo", "tipo_codigo": "GAR",
         "nome": "Troca de óleo 4T", "intervalo": 50, "unidade": "h",
         "materiais": [{"descricao": "Óleo SAE 30 1L", "qtd": 1}]},
        {"id": "plano_sol_oleo", "tipo_codigo": "SOL",
         "nome": "Troca óleo + filtro diesel", "intervalo": 50, "unidade": "h",
         "materiais": [
            {"descricao": "Óleo 15W-40", "qtd": 4},
            {"descricao": "Filtro óleo Solis", "qtd": 1},
         ]},
        {"id": "plano_fs220_lubrif", "tipo_codigo": "FS220",
         "nome": "Lubrificação geral", "intervalo": 25, "unidade": "h"},
        {"id": "plano_ts114_inspecao", "tipo_codigo": "TS114",
         "nome": "Inspeção de disco e correias", "intervalo": 30, "unidade": "h"},

        # Viaturas
        {"id": "plano_vtr_pickup_oleo", "tipo_codigo": "VTR_PICKUP",
         "nome": "Troca de óleo + filtro", "intervalo": 5000, "unidade": "km",
         "materiais": [
            {"descricao": "Óleo 5W-30 sint. 4L", "qtd": 1},
            {"descricao": "Filtro de óleo", "qtd": 1},
         ]},
        {"id": "plano_vtr_pickup_freios", "tipo_codigo": "VTR_PICKUP",
         "nome": "Inspeção de freios", "intervalo": 10000, "unidade": "km",
         "materiais": [{"descricao": "Pastilhas de freio", "qtd": 1}]},
        {"id": "plano_vtr_carga_oleo", "tipo_codigo": "VTR_CARGA",
         "nome": "Troca de óleo + filtro (carga)", "intervalo": 10000, "unidade": "km",
         "materiais": [
            {"descricao": "Óleo diesel 15W-40", "qtd": 8},
            {"descricao": "Filtro de óleo pesado", "qtd": 1},
         ]},

        # Embarcações
        {"id": "plano_emb_lancha_oleo", "tipo_codigo": "EMB_LANCHA",
         "nome": "Troca de óleo motor de popa", "intervalo": 50, "unidade": "h",
         "materiais": [
            {"descricao": "Óleo náutico 2T", "qtd": 2},
            {"descricao": "Filtro de óleo", "qtd": 1},
         ]},
        {"id": "plano_emb_lancha_anodo", "tipo_codigo": "EMB_LANCHA",
         "nome": "Troca de ânodo de zinco", "intervalo": 12, "unidade": "meses",
         "materiais": [{"descricao": "Ânodo de zinco", "qtd": 2}]},

        # Climatização (Split)
        {"id": "plano_ac_split_limpeza", "tipo_codigo": "AC_SPLIT",
         "nome": "Limpeza de filtros", "intervalo": 1, "unidade": "meses"},
        {"id": "plano_ac_split_gas", "tipo_codigo": "AC_SPLIT",
         "nome": "Verificação de gás", "intervalo": 12, "unidade": "meses",
         "materiais": [{"descricao": "Gás R-410A (se necessário)", "qtd": 0}]},
        {"id": "plano_ac_central_limpeza", "tipo_codigo": "AC_CENTRAL",
         "nome": "Limpeza completa + verificação", "intervalo": 3, "unidade": "meses"},
    ]


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  → {path.relative_to(ROOT)} ({len(data)} entradas)")


def main():
    SEEDS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Gerando seeds em {SEEDS_DIR.relative_to(ROOT)}/")

    ativos = gen_ativos()
    write_json(SEEDS_DIR / "ativos.json", ativos)

    write_json(SEEDS_DIR / "locais.json", gen_locais(ativos))
    write_json(SEEDS_DIR / "refrigeracao-detalhe.json", gen_refrig_detalhe())
    write_json(SEEDS_DIR / "estoque-catalogo.json", gen_estoque_catalogo())
    write_json(SEEDS_DIR / "planos.json", gen_planos())

    print("Concluído.")


if __name__ == "__main__":
    main()
