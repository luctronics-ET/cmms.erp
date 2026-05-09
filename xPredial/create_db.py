#!/usr/bin/env python3
"""
create_db.py — xPredial
=======================
Cria e popula o banco data/predial.db do zero.
Executa: schema + seed_normas + seed_locais + seed_checklist

Uso:
    cd /home/luciano/DEV/cmasm.erp/xPredial
    python create_db.py
    python create_db.py --db data/predial.db   # caminho alternativo
    python create_db.py --force                # recria do zero (DESTRÓI dados)
"""

import sqlite3
import argparse
import sys
import os
from pathlib import Path

BASE = Path(__file__).parent
DB_DEFAULT = BASE / "data" / "predial.db"

# ─── SEED DOS CHECKLIST TEMPLATES ─────────────────────────────────────────────
# (inline para não depender de arquivo externo)

TEMPLATES = [
    (100, "Inspeção Predial Completa — NBR 5674/16747", None,
     "Template completo baseado na ABNT NBR 5674:2012 e NBR 16747:2020. "
     "Todos os sistemas construtivos com Matriz GUT.",
     "NBR 5674:2012 · NBR 16747:2020 · IBAPE/NA 2012"),
    (101, "Inspeção de Paiol — Estrutura e Segurança", "paiol",
     "Template focado para paióis de armamento: estrutura, cobertura, "
     "vedação, instalação elétrica (Ex/ATEX), SPDA e combate a incêndio.",
     "NBR 5674:2012 · NR-19 · ABNT NBR IEC 60079"),
    (102, "Inspeção de Área Externa e Infraestrutura", "area_externa",
     "Template para áreas externas, cais e infraestruturas: "
     "pavimentação, drenagem, muros e iluminação.",
     "NBR 5674:2012 · NBR 9050:2020"),
]

# (template_id, sistema, subsistema, descricao, ordem)
ITEMS = [
    # ─ TEMPLATE 100 — COMPLETO ────────────────────────────────────────────────
    # Documentação
    (100,"documentacao",None,"Alvará de construção",1),
    (100,"documentacao",None,"Projeto de sondagem do solo",2),
    (100,"documentacao",None,"Projeto de fundação + ART/RRT",3),
    (100,"documentacao",None,"Projeto de estruturas + ART/RRT",4),
    (100,"documentacao",None,"Projeto arquitetônico executivo + ART/RRT",5),
    (100,"documentacao",None,"Projeto hidráulico-sanitário + ART/RRT",6),
    (100,"documentacao",None,"Projeto elétrico + ART/RRT",7),
    (100,"documentacao",None,"Memorial descritivo dos sistemas construtivos",8),
    (100,"documentacao",None,"Habite-se / Auto de Vistoria",9),
    (100,"documentacao",None,"Manual de Uso, Operação e Manutenção (MOM)",10),
    (100,"documentacao",None,"Plano de Manutenção Preventiva (PMP) atualizado",11),
    (100,"documentacao",None,"Registro de reformas realizadas",12),
    (100,"documentacao",None,"Registro de manutenções executadas (livro de manutenção)",13),
    (100,"documentacao",None,"Laudos de inspeções prediais anteriores",14),
    (100,"documentacao",None,"Atestado de Regularidade do Corpo de Bombeiros (AVCB/CLCB)",15),
    (100,"documentacao",None,"Certificado de recarga e manutenção dos extintores",16),
    (100,"documentacao",None,"Relatório de Inspeção de Mangueiras dos Hidrantes",17),
    (100,"documentacao",None,"Atestado SPDA — medição ôhmica (máx. 5 anos)",18),
    (100,"documentacao",None,"Certificado de limpeza e desinfecção dos reservatórios (6 meses)",19),
    (100,"documentacao",None,"Apólice de seguro de incêndio vigente",20),
    # Fundação
    (100,"fundacao",None,"Erosão ou carreamento do solo na base da edificação",1),
    (100,"fundacao",None,"Recalque diferencial (desníveis visíveis em pisos/paredes)",2),
    (100,"fundacao",None,"Anomalias do solo (bombeamento, contaminação, umidade ascendente)",3),
    (100,"fundacao",None,"Falha na execução da fundação (bicheiras, armadura exposta)",4),
    (100,"fundacao",None,"Vegetação com raízes agressivas junto à fundação",5),
    # Estrutura
    (100,"estrutura",None,"Exposição de armadura (cobrimento insuficiente)",1),
    (100,"estrutura",None,"Corrosão de armaduras (manchas ferruginosas, expansão do cobrimento)",2),
    (100,"estrutura",None,"Deformação excessiva de vigas, lajes ou pilares",3),
    (100,"estrutura",None,"Deterioração ou degradação de materiais estruturais",4),
    (100,"estrutura",None,"Eflorescência / manchas de carbonatação",5),
    (100,"estrutura",None,"Fissuras, trincas ou rachaduras em elementos estruturais",6),
    (100,"estrutura",None,"Infiltração por fissuras na estrutura",7),
    (100,"estrutura",None,"Falha de concretagem (bicheiras, ninhos, falhas de forma)",8),
    (100,"estrutura",None,"Recalques em elementos estruturais",9),
    (100,"estrutura",None,"Segregação do concreto (separação de agregados)",10),
    (100,"estrutura",None,"Desagregação ou desplacamento de concreto",11),
    (100,"estrutura",None,"Lixiviação (lavagem de cimento pela água)",12),
    (100,"estrutura",None,"Irregularidades geométricas (prumo, nível, alinhamento)",13),
    # Vedação
    (100,"vedacao",None,"Fissura / trinca / rachadura em alvenaria de vedação",1),
    (100,"vedacao",None,"Eflorescência em alvenaria",2),
    (100,"vedacao",None,"Infiltração pela alvenaria",3),
    (100,"vedacao",None,"Irregularidades geométricas (esquadro / prumo / nível)",4),
    (100,"vedacao",None,"Desagregação de elementos de alvenaria (soltos, quebrados)",5),
    (100,"vedacao",None,"Fungos / bolor / mofo em superfícies de vedação",6),
    (100,"vedacao",None,"Pulverulência (pó superficial, argamassa fraca)",7),
    (100,"vedacao",None,"Gretamento (fissuras em teia na argamassa/pintura)",8),
    (100,"vedacao",None,"Falhas na amarração entre alvenarias (interfaces)",9),
    (100,"vedacao",None,"Ausência de verga e/ou contra-verga em aberturas",10),
    (100,"vedacao",None,"Descascamento de pintura / bolhas / descoloração",11),
    (100,"vedacao",None,"Abertura improvisada para passagem de cabos/tubos",12),
    # Revestimento — Forro
    (100,"revestimento","forro","Deformação excessiva do forro",1),
    (100,"revestimento","forro","Fissura no forro",2),
    (100,"revestimento","forro","Desencaixe de placas / módulos de forro",3),
    (100,"revestimento","forro","Utilização de material sujeito a corrosão em área úmida",4),
    (100,"revestimento","forro","Abaulamento / empenamento do forro",5),
    (100,"revestimento","forro","Deficiência no dimensionamento ou inexistência de alçapão",6),
    (100,"revestimento","forro","Infiltração ou manchas de umidade visíveis no forro",7),
    # Revestimento — Paredes
    (100,"revestimento","paredes","Fissuras em revestimento de paredes internas",1),
    (100,"revestimento","paredes","Destacamento / desagregação / descolamento de revestimento",2),
    (100,"revestimento","paredes","Infiltração em paredes internas",3),
    (100,"revestimento","paredes","Eflorescência / manchas de mofo / bolor em paredes",4),
    (100,"revestimento","paredes","Falha em rejuntes de revestimento cerâmico",5),
    (100,"revestimento","paredes","Bolhas / enrugamento em pintura de paredes",6),
    (100,"revestimento","paredes","Som cavo ao percutir revestimento (descolamento oculto)",7),
    (100,"revestimento","paredes","Abertura improvisada para passagem de cabos/tubos",8),
    # Revestimento — Piso
    (100,"revestimento","piso","Caimento inadequado em áreas molhadas / laváveis",1),
    (100,"revestimento","piso","Fissuras em revestimento de piso",2),
    (100,"revestimento","piso","Falha em rejuntes de piso",3),
    (100,"revestimento","piso","Som cavo ao percutir o piso (descolamento)",4),
    (100,"revestimento","piso","Abatimento / afundamento do piso",5),
    (100,"revestimento","piso","Pisos externos escorregadios / sem proteção antiderrapante",6),
    (100,"revestimento","piso","Desgaste anormal ou deterioração do piso",7),
    (100,"revestimento","piso","Destacamento / descolamento de piso",8),
    # Revestimento — Fachada
    (100,"revestimento","fachada","Fissuras em revestimento de fachada",1),
    (100,"revestimento","fachada","Destacamento / desagregação / descolamento de fachada",2),
    (100,"revestimento","fachada","Bolhas / enrugamento em pintura de fachada",3),
    (100,"revestimento","fachada","Eflorescência / manchas de mofo / bolor em fachada",4),
    (100,"revestimento","fachada","Falha em rejuntes de fachada",5),
    (100,"revestimento","fachada","Deficiência pintura / oxidação / corrosão de elementos metálicos",6),
    (100,"revestimento","fachada","Vidros soltos ou quebrados em esquadrias de fachada",7),
    (100,"revestimento","fachada","Descolamento de material selante em fachada",8),
    (100,"revestimento","fachada","Ataque de pragas / bioincrustação em fachada",9),
    # Esquadrias
    (100,"esquadrias",None,"Deficiência na pintura / oxidação / corrosão de esquadrias",1),
    (100,"esquadrias",None,"Ataque de pragas (cupins) em esquadrias de madeira",2),
    (100,"esquadrias",None,"Deficiência na abertura / fechamento (travamento, folga)",3),
    (100,"esquadrias",None,"Folga na fixação dos vidros",4),
    (100,"esquadrias",None,"Vidros soltos ou quebrados",5),
    (100,"esquadrias",None,"Rompimento ou descolamento do material selante / infiltração",6),
    (100,"esquadrias",None,"Componentes danificados (ferragens, fechos, dobradiças)",7),
    # Impermeabilização
    (100,"impermeabilizacao",None,"Infiltração por falha no sistema de impermeabilização",1),
    (100,"impermeabilizacao",None,"Descolamento de manta impermeabilizante",2),
    (100,"impermeabilizacao",None,"Sistema de impermeabilização perfurado ou rasgado",3),
    (100,"impermeabilizacao",None,"Ressecamento / craqueamento do sistema impermeabilizante",4),
    (100,"impermeabilizacao",None,"Falta de junta de dilatação em proteção mecânica",5),
    (100,"impermeabilizacao",None,"Falta de caimento para os ralos (acúmulo de água)",6),
    (100,"impermeabilizacao",None,"Falta de impermeabilização no teto dos reservatórios",7),
    (100,"impermeabilizacao",None,"Proteção mecânica danificada ou ausente",8),
    # Cobertura
    (100,"cobertura",None,"Deformações excessivas na estrutura da cobertura",1),
    (100,"cobertura",None,"Abertura de frestas entre telhas / rufos",2),
    (100,"cobertura",None,"Umidade na estrutura da cobertura (madeiramento, metálica)",3),
    (100,"cobertura",None,"Deslocamento / desalinhamento / quebra de telhas",4),
    (100,"cobertura",None,"Corrosão de parafusos de fixação / rufo metálico / calha metálica",5),
    (100,"cobertura",None,"Ressecamento de borrachas de vedação / vedantes de rufos",6),
    (100,"cobertura",None,"Entupimento de calhas e ralos",7),
    (100,"cobertura",None,"Caimento do telhado insuficiente (água represada)",8),
    (100,"cobertura",None,"Ausência da grelha do ralo ou extravasor de calha",9),
    (100,"cobertura",None,"Falta de condições de segurança para acesso (guarda-corpo)",10),
    # Instalação Hidrossanitária
    (100,"instalacao_hidrossanitaria",None,"Vazamento em tubulações / conexões hidráulicas",1),
    (100,"instalacao_hidrossanitaria",None,"Deterioração / deformação nas tubulações",2),
    (100,"instalacao_hidrossanitaria",None,"Tampas de reservatórios inadequadas ou danificadas",3),
    (100,"instalacao_hidrossanitaria",None,"Não conformidade na pintura de identificação das tubulações",4),
    (100,"instalacao_hidrossanitaria",None,"Falta de identificação nos registros do barrilete",5),
    (100,"instalacao_hidrossanitaria",None,"Tubulações obstruídas (entupimento)",6),
    (100,"instalacao_hidrossanitaria",None,"Entupimento / extravasamento de calhas e ralos pluviais",7),
    (100,"instalacao_hidrossanitaria",None,"Corrosão de tubulações de ferro galvanizado",8),
    (100,"instalacao_hidrossanitaria",None,"Reservatórios sem limpeza / desinfecção no prazo",9),
    # Instalação Elétrica
    (100,"instalacao_eletrica",None,"Lâmpadas queimadas / ausência de lâmpadas",1),
    (100,"instalacao_eletrica",None,"Pragas urbanas em quadros elétricos / de telefonia",2),
    (100,"instalacao_eletrica",None,"Improvisos nas instalações elétricas (gambiarras)",3),
    (100,"instalacao_eletrica",None,"Superaquecimento de condutores ou equipamentos",4),
    (100,"instalacao_eletrica",None,"Fiações aparentes / com muitas emendas / partes vivas expostas",5),
    (100,"instalacao_eletrica",None,"Curto-circuito identificado ou evidências de arco elétrico",6),
    (100,"instalacao_eletrica",None,"Quadro de distribuição obstruído / sem identificação de circuitos",7),
    (100,"instalacao_eletrica",None,"Ausência de proteção de barramento (tampa de quadro)",8),
    (100,"instalacao_eletrica",None,"Falha de tomada / interruptor",9),
    (100,"instalacao_eletrica",None,"Cerca elétrica danificada / sem manutenção",10),
    (100,"instalacao_eletrica",None,"Corrosão / deterioração de eletrodutos",11),
    (100,"instalacao_eletrica",None,"Ausência de aterramento em equipamentos / quadros",12),
    # Instalação Gás
    (100,"instalacao_gas",None,"Vazamento em tubulação ou conexões de gás",1),
    (100,"instalacao_gas",None,"Deterioração / corrosão de tubulações de gás",2),
    (100,"instalacao_gas",None,"Não conformidade na pintura de identificação (amarelo)",3),
    (100,"instalacao_gas",None,"Não conformidade nas dimensões mínimas do abrigo de gás",4),
    (100,"instalacao_gas",None,"Ausência de ventilação inferior no abrigo de gás (GLP)",5),
    (100,"instalacao_gas",None,"Ausência de dispositivo de segurança (válvula corta-gás)",6),
    (100,"instalacao_gas",None,"Espaçamento insuficiente entre recipientes e parede da central",7),
    # Extintores
    (100,"extintores",None,"Extintor descarregado ou com prazo de validade vencido",1),
    (100,"extintores",None,"Lacre violado ou vencido",2),
    (100,"extintores",None,"Sem indicação da classe / sinalização incorreta",3),
    (100,"extintores",None,"Quadro de instruções ilegível ou inexistente",4),
    (100,"extintores",None,"Mangueira de descarga com danos / deformação / ressecamento",5),
    (100,"extintores",None,"Quantidade insuficiente ou altura de instalação irregular",6),
    # Hidrantes
    (100,"hidrantes",None,"Falta de conservação / sinalização da bomba de incêndio",1),
    (100,"hidrantes",None,"Dispositivo de comando da bomba quebrado ou danificado",2),
    (100,"hidrantes",None,"Mau estado de conservação das caixas de hidrantes",3),
    (100,"hidrantes",None,"Mangueira do hidrante danificada / ressecada / ausente",4),
    (100,"hidrantes",None,"Registro emperrado / com vazamento",5),
    (100,"hidrantes",None,"Ausência de mangueira ou esguicho",6),
    # Saída de Emergência
    (100,"saida_emergencia",None,"Ausência de sinalização das rotas de fuga e saídas de emergência",1),
    (100,"saida_emergencia",None,"Portas de emergência obstruídas",2),
    (100,"saida_emergencia",None,"Portas corta-fogo em mau estado / fechaduras com defeito",3),
    (100,"saida_emergencia",None,"Portas corta-fogo abertas e travadas com objetos",4),
    (100,"saida_emergencia",None,"Falha na iluminação autônoma de emergência",5),
    (100,"saida_emergencia",None,"Escada sem corrimão ou guarda-corpo inadequado",6),
    (100,"saida_emergencia",None,"Largura de saída inferior a 1,20 m",7),
    # SPDA
    (100,"spda",None,"Ausência do sistema SPDA (obrigatório A>1500m² ou H>12m)",1),
    (100,"spda",None,"Queda de haste ou antenas do SPDA",2),
    (100,"spda",None,"Corrosão em cabos / conexões / hastes do SPDA",3),
    (100,"spda",None,"Descidas insuficientes (1 descida a cada 20m de perímetro)",4),
    (100,"spda",None,"Ausência de luz de topo na haste do SPDA",5),
    (100,"spda",None,"Medição ôhmica com prazo vencido (> 5 anos)",6),

    # ─ TEMPLATE 101 — PAIOL ───────────────────────────────────────────────────
    (101,"estrutura",None,"Exposição de armadura ou fissuras estruturais",1),
    (101,"estrutura",None,"Corrosão de armaduras (manchas ferruginosas)",2),
    (101,"estrutura",None,"Fissuras / trincas em paredes ou laje",3),
    (101,"estrutura",None,"Infiltração por estrutura ou cobertura",4),
    (101,"vedacao",None,"Fissuras em alvenaria",1),
    (101,"vedacao",None,"Infiltração pela alvenaria",2),
    (101,"vedacao",None,"Ausência de verga / contra-verga",3),
    (101,"cobertura",None,"Deformação ou abertura de frestas na cobertura",1),
    (101,"cobertura",None,"Deslocamento / quebra de telhas",2),
    (101,"cobertura",None,"Entupimento de calhas — risco de inundação",3),
    (101,"cobertura",None,"Corrosão de elementos metálicos da cobertura",4),
    (101,"instalacao_eletrica",None,"Instalação elétrica à prova de explosão (Ex/ATEX) danificada",1),
    (101,"instalacao_eletrica",None,"Fiações aparentes ou improvisos",2),
    (101,"instalacao_eletrica",None,"Quadro elétrico sem identificação / obstruído",3),
    (101,"instalacao_eletrica",None,"Ausência de aterramento de equipamentos",4),
    (101,"instalacao_eletrica",None,"Lâmpadas sem proteção antiexplosiva",5),
    (101,"spda",None,"Ausência ou dano no sistema SPDA",1),
    (101,"spda",None,"Corrosão em cabos / hastes do SPDA",2),
    (101,"spda",None,"Medição ôhmica com prazo vencido",3),
    (101,"extintores",None,"Extintor com prazo vencido ou lacre violado",1),
    (101,"extintores",None,"Extintor sem indicação de classe adequada",2),
    (101,"extintores",None,"Quantidade de extintores insuficiente para a área",3),
    (101,"impermeabilizacao",None,"Infiltração no piso ou paredes do paiol",1),
    (101,"impermeabilizacao",None,"Caimento insuficiente para escoamento pluvial",2),

    # ─ TEMPLATE 102 — ÁREA EXTERNA ────────────────────────────────────────────
    (102,"pavimentacao",None,"Fissuras / trincas em pavimento rígido (concreto)",1),
    (102,"pavimentacao",None,"Afundamento / recalque de pavimento",2),
    (102,"pavimentacao",None,"Desagregação de pavimento (paralelepípedo, asfalto, pedra)",3),
    (102,"pavimentacao",None,"Superfície escorregadia / sem antiderrapante em acesso",4),
    (102,"pavimentacao",None,"Caimento inadequado (acúmulo de água)",5),
    (102,"drenagem",None,"Entupimento de ralos / caixas de drenagem",1),
    (102,"drenagem",None,"Erosão do solo por escoamento superficial",2),
    (102,"drenagem",None,"Ausência de canaleta de drenagem em área operacional",3),
    (102,"drenagem",None,"Boca de lobo obstruída ou danificada",4),
    (102,"muros_cercas",None,"Fissuras / trincas em muro de alvenaria",1),
    (102,"muros_cercas",None,"Recalque diferencial de muro / cerca",2),
    (102,"muros_cercas",None,"Corrosão de elementos metálicos de cerca / portão",3),
    (102,"muros_cercas",None,"Vegetação com raízes danificando muro / fundação",4),
    (102,"muros_cercas",None,"Cerca elétrica danificada ou sem manutenção",5),
    (102,"iluminacao_externa",None,"Luminárias externas danificadas ou ausentes",1),
    (102,"iluminacao_externa",None,"Postes com corrosão ou inclinação anormal",2),
    (102,"iluminacao_externa",None,"Cabos elétricos expostos em área externa",3),
    (102,"iluminacao_externa",None,"Ausência de iluminação em área de acesso controlado",4),
    (102,"vegetacao",None,"Vegetação invasora sobre estruturas / pisos",1),
    (102,"vegetacao",None,"Raízes causando levantamento de pavimento",2),
    (102,"vegetacao",None,"Acúmulo de vegetação seca (risco de incêndio)",3),
    (102,"vegetacao",None,"Árvore com risco de queda sobre edificação / via",4),
]


def run(db_path: Path, force: bool = False) -> None:
    if force and db_path.exists():
        print(f"[--force] Removendo {db_path}")
        db_path.unlink()

    db_path.parent.mkdir(parents=True, exist_ok=True)
    exists = db_path.exists()
    print(f"[db] {'Abrindo' if exists else 'Criando'} banco: {db_path}")

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    cur = conn.cursor()

    # ── 1. Schema ─────────────────────────────────────────────────────────────
    schema_file = BASE / "database" / "schema.sql"
    if schema_file.exists():
        print("[db] Aplicando schema.sql ...")
        conn.executescript(schema_file.read_text())
    else:
        print(f"[ERRO] schema.sql não encontrado em {schema_file}")
        sys.exit(1)

    # ── 2. Seed normas ────────────────────────────────────────────────────────
    normas_file = BASE / "database" / "seed_normas.sql"
    if normas_file.exists():
        print("[db] Seed normas ...")
        conn.executescript(normas_file.read_text())

    # ── 3. Seed locais ────────────────────────────────────────────────────────
    locais_file = BASE / "database" / "seed_locais_cmasm.sql"
    if locais_file.exists():
        print("[db] Seed locais CMASM ...")
        conn.executescript(locais_file.read_text())

    # ── 4. Seed templates de checklist ────────────────────────────────────────
    print("[db] Seed checklist_templates ...")
    for row in TEMPLATES:
        cur.execute("""
            INSERT OR IGNORE INTO checklist_templates (id, nome, tipo_local, descricao, norma_ref)
            VALUES (?, ?, ?, ?, ?)
        """, row)

    print("[db] Seed checklist_template_items ...")
    inseridos = 0
    for tpl_id, sistema, subsistema, descricao, ordem in ITEMS:
        cur.execute("""
            SELECT id FROM checklist_template_items
            WHERE template_id=? AND sistema=? AND descricao=?
        """, (tpl_id, sistema, descricao))
        if not cur.fetchone():
            cur.execute("""
                INSERT INTO checklist_template_items
                    (template_id, sistema, subsistema, descricao, ordem)
                VALUES (?, ?, ?, ?, ?)
            """, (tpl_id, sistema, subsistema, descricao, ordem))
            inseridos += 1

    conn.commit()

    # ── 5. Relatório ──────────────────────────────────────────────────────────
    stats = {}
    for table in ["normas","locais","checklist_templates","checklist_template_items",
                  "inspecoes","inspecao_itens","laudos","workflow_events"]:
        try:
            n = cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            stats[table] = n
        except Exception:
            stats[table] = "—"

    conn.close()

    print("\n" + "─"*50)
    print(f"{'Banco':30s} {db_path}")
    print(f"{'Tamanho':30s} {db_path.stat().st_size / 1024:.1f} KB")
    print("─"*50)
    for t, n in stats.items():
        print(f"  {t:35s} {n:>6} registros")
    print("─"*50)
    print("OK — banco criado com sucesso\n")
    print("Próximo passo:")
    print("  uvicorn backend.main:app --host 127.0.0.1 --port 8002 --reload")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="xPredial — criar banco predial.db")
    parser.add_argument("--db",    default=str(DB_DEFAULT), help="Caminho do banco SQLite")
    parser.add_argument("--force", action="store_true",     help="Recriar do zero (DESTRÓI dados)")
    args = parser.parse_args()
    run(Path(args.db), args.force)
