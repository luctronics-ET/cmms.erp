"""
CMASM — Gerador de Pedidos de Serviço (PS) de Calibração
Formato baseado nos PS reais: PS-CMS-25-001 a PS-CMS-25-NNN
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import KeepTogether
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.platypus import BaseDocTemplate, PageTemplate, Frame
import os, datetime

# ── Paleta ────────────────────────────────────────────────────────────────────
AZUL_MARINHA  = colors.HexColor('#0A1931')
AZUL_MEDIO    = colors.HexColor('#1A3A6B')
AZUL_CLARO    = colors.HexColor('#2D6A9F')
CINZA_TITULO  = colors.HexColor('#2C3E50')
CINZA_LINHA   = colors.HexColor('#D5DCE4')
CINZA_ALT     = colors.HexColor('#EEF2F7')
VERDE_OK      = colors.HexColor('#1D9E75')
VERMELHO_NOK  = colors.HexColor('#C0392B')
AMARELO_WARN  = colors.HexColor('#D4AC0D')
BRANCO        = colors.white

W, H = A4  # 210 x 297 mm


# ── Estilos de parágrafo ──────────────────────────────────────────────────────
def estilos():
    return {
        'titulo_ps': ParagraphStyle('titulo_ps',
            fontName='Helvetica-Bold', fontSize=13,
            textColor=BRANCO, alignment=TA_CENTER, leading=16),
        'subtitulo': ParagraphStyle('subtitulo',
            fontName='Helvetica-Bold', fontSize=8,
            textColor=BRANCO, alignment=TA_CENTER, leading=10),
        'campo_label': ParagraphStyle('campo_label',
            fontName='Helvetica-Bold', fontSize=7,
            textColor=CINZA_TITULO, leading=9),
        'campo_valor': ParagraphStyle('campo_valor',
            fontName='Helvetica', fontSize=8,
            textColor=colors.black, leading=10),
        'campo_valor_b': ParagraphStyle('campo_valor_b',
            fontName='Helvetica-Bold', fontSize=8,
            textColor=colors.black, leading=10),
        'tabela_header': ParagraphStyle('tabela_header',
            fontName='Helvetica-Bold', fontSize=7,
            textColor=BRANCO, alignment=TA_CENTER, leading=9),
        'tabela_cel': ParagraphStyle('tabela_cel',
            fontName='Helvetica', fontSize=7,
            textColor=colors.black, leading=9),
        'tabela_cel_c': ParagraphStyle('tabela_cel_c',
            fontName='Helvetica', fontSize=7,
            textColor=colors.black, alignment=TA_CENTER, leading=9),
        'rodape': ParagraphStyle('rodape',
            fontName='Helvetica', fontSize=6,
            textColor=colors.grey, alignment=TA_CENTER, leading=8),
        'obs': ParagraphStyle('obs',
            fontName='Helvetica-Oblique', fontSize=7,
            textColor=colors.HexColor('#555555'), leading=9),
        'status_ok': ParagraphStyle('status_ok',
            fontName='Helvetica-Bold', fontSize=7,
            textColor=VERDE_OK, alignment=TA_CENTER, leading=9),
        'status_nok': ParagraphStyle('status_nok',
            fontName='Helvetica-Bold', fontSize=7,
            textColor=VERMELHO_NOK, alignment=TA_CENTER, leading=9),
        'status_warn': ParagraphStyle('status_warn',
            fontName='Helvetica-Bold', fontSize=7,
            textColor=AMARELO_WARN, alignment=TA_CENTER, leading=9),
        'secao': ParagraphStyle('secao',
            fontName='Helvetica-Bold', fontSize=8,
            textColor=AZUL_MEDIO, leading=10),
    }


# ── Cabeçalho do PS ──────────────────────────────────────────────────────────
def bloco_cabecalho(ps, est):
    numero_ps = ps['numero']
    data_emissao = ps.get('data_emissao', datetime.date.today().strftime('%d/%m/%Y'))
    laboratorio = ps.get('laboratorio', 'CMS')
    prioridade = ps.get('prioridade', '12 meses')
    divisao = ps.get('divisao', '')

    # Linha 1: Número do PS (fundo azul escuro)
    row1 = [[
        Paragraph('MARINHA DO BRASIL — CMASM', est['subtitulo']),
        Paragraph('PEDIDO DE SERVIÇO DE CALIBRAÇÃO', est['subtitulo']),
        Paragraph(numero_ps, est['titulo_ps']),
    ]]
    t1 = Table(row1, colWidths=[60*mm, 90*mm, 40*mm])
    t1.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), AZUL_MARINHA),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LINEBELOW', (0,0), (-1,-1), 0.5, AZUL_CLARO),
    ]))

    # Linha 2: Metadados do PS
    def campo(label, valor, bold=False):
        st = est['campo_valor_b'] if bold else est['campo_valor']
        return [Paragraph(label, est['campo_label']), Paragraph(valor, st)]

    row2 = [[
        Table([campo('Laboratório / Empresa:', laboratorio)],
              colWidths=[28*mm, 30*mm]),
        Table([campo('Divisão / Setor:', divisao)],
              colWidths=[25*mm, 30*mm]),
        Table([campo('Periodicidade:', prioridade)],
              colWidths=[22*mm, 22*mm]),
        Table([campo('Data de Emissão:', data_emissao, bold=True)],
              colWidths=[25*mm, 18*mm]),
    ]]
    t2 = Table(row2, colWidths=[58*mm, 55*mm, 44*mm, 43*mm])
    t2.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), CINZA_ALT),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ('LINEBELOW', (0,0), (-1,-1), 0.5, CINZA_LINHA),
    ]))

    return KeepTogether([t1, t2])


# ── Tabela de instrumentos ────────────────────────────────────────────────────
def tabela_instrumentos(itens, est):
    headers = ['#', 'Cat.', 'Instrumento / Tipo', 'Fabricante', 'Modelo',
               'Faixa / Tolerância', 'Último Certif.', 'Prazo Cal.', 'Status', 'Val. Max (R$)']
    col_w = [8*mm, 8*mm, 38*mm, 22*mm, 20*mm, 22*mm, 17*mm, 17*mm, 18*mm, 17*mm]

    head_row = [Paragraph(h, est['tabela_header']) for h in headers]
    rows = [head_row]

    for i, it in enumerate(itens):
        status = it.get('status', '')
        if status == 'CALIBRADO':
            st_p = Paragraph(status, est['status_ok'])
        elif status in ('DESCALIBRADO', 'EM REPARO'):
            st_p = Paragraph(status, est['status_nok'])
        elif 'certif' in status.lower() or status == 'falta certificado':
            st_p = Paragraph('SEM CERT.', est['status_warn'])
        else:
            st_p = Paragraph(status, est['tabela_cel_c'])

        custo = it.get('custo', 0)
        custo_str = f"R$ {custo:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.') if custo > 0 else '—'

        row = [
            Paragraph(str(i+1), est['tabela_cel_c']),
            Paragraph(it.get('cat', ''), est['tabela_cel_c']),
            Paragraph(it.get('tipo', ''), est['tabela_cel']),
            Paragraph(it.get('fabricante', '—'), est['tabela_cel']),
            Paragraph(it.get('modelo', '—'), est['tabela_cel']),
            Paragraph(it.get('faixa', '—'), est['tabela_cel_c']),
            Paragraph(it.get('ult_cal', '—'), est['tabela_cel_c']),
            Paragraph(it.get('prazo', '—'), est['tabela_cel_c']),
            st_p,
            Paragraph(custo_str, est['tabela_cel_c']),
        ]
        rows.append(row)

    t = Table(rows, colWidths=col_w, repeatRows=1)
    style = [
        ('BACKGROUND', (0,0), (-1,0), AZUL_MEDIO),
        ('TEXTCOLOR', (0,0), (-1,0), BRANCO),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 7),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (2,0), (2,-1), 4),
        ('LEFTPADDING', (3,0), (3,-1), 4),
        ('LEFTPADDING', (4,0), (4,-1), 4),
        ('GRID', (0,0), (-1,-1), 0.3, CINZA_LINHA),
        ('LINEBELOW', (0,0), (-1,0), 0.8, AZUL_CLARO),
    ]
    # Linhas alternadas
    for r in range(1, len(rows)):
        if r % 2 == 0:
            style.append(('BACKGROUND', (0,r), (-1,r), CINZA_ALT))
    t.setStyle(TableStyle(style))
    return t


# ── Bloco de assinaturas e controle ─────────────────────────────────────────
def bloco_assinaturas(ps, est):
    total = ps.get('valor_total', 0)
    total_str = f"R$ {total:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.') if total > 0 else '—'
    obs = ps.get('observacoes', '')

    # Resumo financeiro
    fin_data = [
        [Paragraph('RESUMO FINANCEIRO', est['campo_label']),
         Paragraph('OBSERVAÇÕES E RESTRIÇÕES', est['campo_label'])],
        [
            Table([
                [Paragraph('Qtd. instrumentos:', est['campo_label']),
                 Paragraph(str(ps.get('qtd_itens', 0)), est['campo_valor_b'])],
                [Paragraph('Valor máximo total:', est['campo_label']),
                 Paragraph(total_str, est['campo_valor_b'])],
                [Paragraph('Contrato / ATA:', est['campo_label']),
                 Paragraph(ps.get('contrato', '—'), est['campo_valor'])],
                [Paragraph('NUP Processo:', est['campo_label']),
                 Paragraph(ps.get('nup', '—'), est['campo_valor'])],
            ], colWidths=[32*mm, 35*mm]),
            Paragraph(obs if obs else 'Sem observações especiais.', est['obs'])
        ]
    ]
    tf = Table(fin_data, colWidths=[67*mm, 120*mm])
    tf.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), CINZA_ALT),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('LINEBELOW', (0,0), (-1,0), 0.5, CINZA_LINHA),
        ('BOX', (0,0), (-1,-1), 0.5, CINZA_LINHA),
        ('INNERGRID', (0,0), (-1,-1), 0.3, CINZA_LINHA),
    ]))

    # Assinaturas
    data_hoje = datetime.date.today().strftime('%d/%m/%Y')
    sig_data = [[
        Table([
            [Paragraph('Elaborado por:', est['campo_label'])],
            [Paragraph('', est['campo_valor'])],
            [Paragraph('_' * 28, est['campo_valor'])],
            [Paragraph('Encarregado de Metrologia / CMASM', est['rodape'])],
            [Paragraph(f'Data: {data_hoje}', est['rodape'])],
        ], colWidths=[55*mm]),
        Table([
            [Paragraph('Aprovado por:', est['campo_label'])],
            [Paragraph('', est['campo_valor'])],
            [Paragraph('_' * 28, est['campo_valor'])],
            [Paragraph('Chefe da Divisão Técnica', est['rodape'])],
            [Paragraph('Data: ___/___/______', est['rodape'])],
        ], colWidths=[55*mm]),
        Table([
            [Paragraph('Recebido pelo laboratório:', est['campo_label'])],
            [Paragraph('', est['campo_valor'])],
            [Paragraph('_' * 28, est['campo_valor'])],
            [Paragraph('Representante / ' + ps.get('laboratorio', 'Lab'), est['rodape'])],
            [Paragraph('Data: ___/___/______', est['rodape'])],
        ], colWidths=[60*mm]),
    ]]
    ts = Table(sig_data, colWidths=[67*mm, 67*mm, 66*mm])
    ts.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('LINEABOVE', (0,0), (-1,0), 0.5, CINZA_LINHA),
    ]))

    return KeepTogether([Spacer(1, 6), tf, Spacer(1, 8), ts])


# ── Rodapé de página ─────────────────────────────────────────────────────────
class PaginaComRodape(BaseDocTemplate):
    def __init__(self, filename, ps_numero, **kwargs):
        self.ps_numero = ps_numero
        BaseDocTemplate.__init__(self, filename, **kwargs)
        frame = Frame(15*mm, 20*mm, 180*mm, 257*mm, id='normal')
        template = PageTemplate(id='main', frames=[frame],
                                onPage=self._rodape)
        self.addPageTemplates([template])

    def _rodape(self, canv, doc):
        canv.saveState()
        canv.setFont('Helvetica', 6)
        canv.setFillColor(colors.grey)
        # Linha separadora
        canv.setStrokeColor(CINZA_LINHA)
        canv.setLineWidth(0.5)
        canv.line(15*mm, 18*mm, 195*mm, 18*mm)
        # Texto rodapé
        canv.drawString(15*mm, 13*mm,
            f'CMASM — Sistema de Controle de Calibração | {self.ps_numero}')
        canv.drawRightString(195*mm, 13*mm,
            f'Página {doc.page} | Gerado em {datetime.date.today().strftime("%d/%m/%Y")}')
        canv.restoreState()


# ── Gerador principal ─────────────────────────────────────────────────────────
def gerar_ps(ps: dict, caminho_saida: str) -> str:
    """
    Gera um PDF de Pedido de Serviço de Calibração.

    Args:
        ps: dicionário com dados do PS (ver exemplo abaixo)
        caminho_saida: caminho do arquivo PDF a gerar

    Campos do dict ps:
        numero       : str   — ex. 'PS-CMS-25-001'
        laboratorio  : str   — ex. 'CMS' ou 'EMPRESA MV'
        divisao      : str   — ex. 'MK-46' ou 'F-21'
        prioridade   : str   — ex. '12 meses'
        data_emissao : str   — ex. '27/03/2025'
        contrato     : str   — ex. 'ATA-001/2025'
        nup          : str   — ex. '123456/2025'
        observacoes  : str   — texto livre
        valor_total  : float — valor total máximo do PS
        qtd_itens    : int
        itens        : list[dict] — lista de instrumentos (ver abaixo)

    Campos de cada item:
        cat       : str   — 'ELE' ou 'MEC'
        tipo      : str   — ex. 'Multímetro'
        fabricante: str
        modelo    : str
        faixa     : str   — ex. '0-1000V / 0.1%'
        ult_cal   : str   — data última calibração 'DD/MM/AAAA'
        prazo     : str   — data próxima calibração 'DD/MM/AAAA'
        status    : str   — 'CALIBRADO' | 'DESCALIBRADO' | 'falta certificado' | 'EM REPARO'
        custo     : float — valor máximo unitário
    """
    est = estilos()
    itens = ps.get('itens', [])
    ps['qtd_itens'] = len(itens)
    ps['valor_total'] = sum(i.get('custo', 0) for i in itens)

    doc = PaginaComRodape(
        caminho_saida,
        ps_numero=ps['numero'],
        pagesize=A4,
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=12*mm, bottomMargin=22*mm,
    )

    story = []
    story.append(bloco_cabecalho(ps, est))
    story.append(Spacer(1, 5))
    story.append(Paragraph(
        f"Instrumentos de medição da {ps.get('divisao','—')} encaminhados para calibração — "
        f"Lote: {ps.get('lote', ps['numero'])}",
        est['secao']
    ))
    story.append(Spacer(1, 4))
    story.append(tabela_instrumentos(itens, est))
    story.append(Spacer(1, 6))
    story.append(bloco_assinaturas(ps, est))

    doc.build(story)
    return caminho_saida


# ── Gerador em lote — agrupa por laboratório/divisão ─────────────────────────
def gerar_ps_lote(equipamentos: list, ano: int = 2025,
                  dir_saida: str = '/mnt/user-data/outputs') -> list:
    """
    Agrupa equipamentos por laboratório e divisão e gera um PS para cada grupo.
    Retorna lista de caminhos dos PDFs gerados.
    """
    from collections import defaultdict
    grupos = defaultdict(list)
    for eq in equipamentos:
        lab = eq.get('lab', 'CMS').strip()
        div = eq.get('div', 'GERAL').strip()
        chave = f"{lab}||{div}"
        grupos[chave].append(eq)

    arquivos = []
    seq = 1
    for chave, itens in sorted(grupos.items()):
        lab, div = chave.split('||')
        numero = f"PS-CMS-{str(ano)[2:]}-{seq:03d}"

        ps = {
            'numero': numero,
            'laboratorio': lab,
            'divisao': div,
            'prioridade': '12 meses',
            'data_emissao': datetime.date.today().strftime('%d/%m/%Y'),
            'contrato': 'ATA-Pregão/2025 (a definir)',
            'nup': '—',
            'lote': f'LOTE {seq:02d}',
            'observacoes': _obs_especiais(lab, div, itens),
            'itens': _converter_itens(itens),
        }

        nome_arquivo = f"{numero.replace('/', '-')}__{lab.replace(' ', '_')}__{div}.pdf"
        caminho = os.path.join(dir_saida, nome_arquivo)
        gerar_ps(ps, caminho)
        arquivos.append(caminho)
        seq += 1

    return arquivos


def _obs_especiais(lab, div, itens):
    obs = []
    if 'AMETEK SIGTON' in lab.upper() or 'AMETEK' in lab.upper():
        obs.append('ATENCAO: Calibracao exclusiva empresa autorizada AMETEK Sigton (SP). Nao pode ser encaminhado ao CMS ou outros laboratorios do pregao.')
    if 'IPT' in lab.upper() or 'NI ' in lab.upper():
        obs.append('ATENCAO: Instrumentos NI exigem NI Certified Center. Unico habilitado no Brasil: IPT Sao Paulo.')
    descs = [i for i in itens if i.get('status', '') == 'DESCALIBRADO']
    if descs:
        obs.append(f'{len(descs)} instrumento(s) nesta OS com status DESCALIBRADO — verificar viabilidade de calibracao antes do envio.')
    sem_cert = [i for i in itens if 'certif' in i.get('status', '').lower()]
    if sem_cert:
        obs.append(f'{len(sem_cert)} instrumento(s) sem certificado fisico — solicitar emissao ao laboratorio executante.')
    nao_util = [i for i in itens if 'nao utilizada' in str(i.get('obs', '')).lower() or 'ferramenta nao' in str(i.get('obs', '')).lower()]
    if nao_util:
        obs.append(f'{len(nao_util)} ferramenta(s) marcada(s) como nao utilizada — avaliar descarte ou manutencao antes de calibrar.')
    return ' | '.join(obs) if obs else 'Calibracao de rotina conforme plano anual CMASM.'


def _converter_itens(equipamentos):
    itens = []
    for eq in equipamentos:
        itens.append({
            'cat':        eq.get('cat', '—'),
            'tipo':       eq.get('tipo', '—'),
            'fabricante': eq.get('fab', '—'),
            'modelo':     eq.get('modelo', '—'),
            'faixa':      eq.get('faixa', eq.get('modelo', '—')),
            'ult_cal':    eq.get('ult', '—'),
            'prazo':      eq.get('prox', '—'),
            'status':     eq.get('status', '—'),
            'custo':      float(eq.get('custo', 0) or 0),
        })
    return itens


# ── Dados reais extraídos do PDF CMASM ───────────────────────────────────────
EQUIPAMENTOS_REAIS = [
    # === F-21 / CMS ===
    {'cat':'ELE','tipo':'Differential Probe','fab':'TESTEC','modelo':'TT-SI 9001','div':'F-21','ult':'12/03/24','prox':'12/03/25','status':'CALIBRADO','custo':373.83,'lab':'CMS','ps_orig':'PS-CMS-25-001'},
    {'cat':'ELE','tipo':'Fonte DC','fab':'AMETEK','modelo':'XG 300-2.8','div':'F-21','ult':'12/12/24','prox':'12/12/25','status':'CALIBRADO','custo':1164.35,'lab':'EMPRESA MQT','ps_orig':'PS-CMS-25-006'},
    {'cat':'ELE','tipo':'Fonte DC','fab':'BK PRECISION','modelo':'BK9801','div':'F-21','ult':'10/05/23','prox':'10/05/25','status':'CALIBRADO','custo':1000.56,'lab':'CMS'},
    {'cat':'ELE','tipo':'Fonte DC','fab':'TDK-LAMBDA','modelo':'Z1020 LAN','div':'F-21','ult':'10/05/23','prox':'10/05/25','status':'CALIBRADO','custo':1000.56,'lab':'CMS'},
    {'cat':'ELE','tipo':'Fonte DC','fab':'TDK-LAMBDA','modelo':'GENH30-25 LAN','div':'F-21','ult':'09/05/23','prox':'09/05/25','status':'CALIBRADO','custo':1000.56,'lab':'CMS'},
    {'cat':'ELE','tipo':'Fonte DC','fab':'TDK-LAMBDA','modelo':'GENH300-2.5 LAN','div':'F-21','ult':'09/05/23','prox':'09/05/25','status':'CALIBRADO','custo':1000.56,'lab':'CMS'},
    {'cat':'ELE','tipo':'Megôhmetro','fab':'CA','modelo':'6541','div':'F-21','ult':'17/10/23','prox':'17/10/25','status':'CALIBRADO','custo':373.83,'lab':'CMS'},
    {'cat':'ELE','tipo':'Multímetro','fab':'FACOM','modelo':'711B','div':'F-21','ult':'12/12/24','prox':'12/12/25','status':'CALIBRADO','custo':1164.35,'lab':'CMS'},
    {'cat':'ELE','tipo':'Multímetro','fab':'FACOM','modelo':'711B','div':'F-21','ult':'','prox':'','status':'DESCALIBRADO','custo':776.23,'lab':'CMS','obs':'FERRAMENTA NAO UTILIZADA'},
    {'cat':'ELE','tipo':'Multímetro','fab':'FACOM','modelo':'711B','div':'F-21','ult':'27/09/23','prox':'27/09/25','status':'CALIBRADO','custo':776.23,'lab':'CMS'},
    {'cat':'ELE','tipo':'Multímetro','fab':'FACOM','modelo':'711B','div':'F-21','ult':'','prox':'','status':'DESCALIBRADO','custo':776.23,'lab':'CMS','obs':'FERRAMENTA NAO UTILIZADA'},
    {'cat':'ELE','tipo':'Multímetro','fab':'FLUKE','modelo':'17B+','div':'F-21','ult':'08/07/24','prox':'08/07/25','status':'CALIBRADO','custo':667.04,'lab':'CMS'},
    {'cat':'ELE','tipo':'Multímetro','fab':'FLUKE','modelo':'17B+','div':'F-21','ult':'04/02/25','prox':'04/02/26','status':'CALIBRADO','custo':776.23,'lab':'CMS'},
    {'cat':'ELE','tipo':'Multímetro','fab':'FLUKE','modelo':'17B+','div':'F-21','ult':'','prox':'','status':'DESCALIBRADO','custo':776.23,'lab':'CMS','obs':'FERRAMENTA NAO UTILIZADA'},
    {'cat':'ELE','tipo':'Multímetro 6 Dígitos','fab':'KEYSIGHT','modelo':'34461A','div':'F-21','ult':'12/05/23','prox':'12/05/25','status':'CALIBRADO','custo':667.04,'lab':'CMS'},
    {'cat':'ELE','tipo':'Multímetro 6 Dígitos','fab':'KEYSIGHT','modelo':'34461A','div':'F-21','ult':'12/05/23','prox':'12/05/25','status':'CALIBRADO','custo':667.04,'lab':'CMS'},
    {'cat':'ELE','tipo':'Ohmímetro','fab':'AOIP','modelo':'RN5306','div':'F-21','ult':'14/09/23','prox':'14/09/25','status':'CALIBRADO','custo':776.23,'lab':'CMS'},
    {'cat':'ELE','tipo':'Ohmímetro','fab':'AOIP','modelo':'RN5306','div':'F-21','ult':'','prox':'','status':'DESCALIBRADO','custo':776.23,'lab':'CMS','obs':'FERRAMENTA NAO UTILIZADA'},
    {'cat':'ELE','tipo':'Ohmímetro','fab':'AOIP','modelo':'RN5306','div':'F-21','ult':'11/02/25','prox':'11/02/26','status':'CALIBRADO','custo':776.23,'lab':'CMS'},
    # === F-21 / MQT ===
    {'cat':'ELE','tipo':'Megôhmetro','fab':'FLUKE','modelo':'1507','div':'F-21','ult':'03/10/24','prox':'03/10/25','status':'CALIBRADO','custo':373.83,'lab':'EMPRESA MQT'},
    {'cat':'ELE','tipo':'Megôhmetro','fab':'SEFELEC','modelo':'MXS500','div':'F-21','ult':'28/06/23','prox':'28/06/25','status':'CALIBRADO','custo':150.00,'lab':'EMPRESA MQT'},
    {'cat':'MEC','tipo':'Dinamômetro Digital','fab':'YALE','modelo':'TMC 1500','div':'F-21','ult':'01/10/24','prox':'01/10/25','status':'CALIBRADO','custo':338.69,'lab':'EMPRESA MQT'},
    {'cat':'MEC','tipo':'Manômetro Analógico','fab':'','modelo':'400 Bar','div':'F-21','ult':'','prox':'','status':'DESCALIBRADO','custo':90.00,'lab':'EMPRESA MQT'},
    {'cat':'MEC','tipo':'Micrometro Prof.','fab':'FACOM','modelo':'806.F','div':'F-21','ult':'30/09/24','prox':'30/09/25','status':'CALIBRADO','custo':84.33,'lab':'EMPRESA MQT'},
    {'cat':'MEC','tipo':'Micrometro Prof.','fab':'FACOM','modelo':'806.F','div':'F-21','ult':'01/10/24','prox':'01/10/25','status':'CALIBRADO','custo':84.33,'lab':'EMPRESA MQT'},
    {'cat':'MEC','tipo':'Micrometro Prof.','fab':'FACOM','modelo':'806.F','div':'F-21','ult':'','prox':'','status':'DESCALIBRADO','custo':84.33,'lab':'EMPRESA MQT','obs':'FERRAMENTA NAO UTILIZADA'},
    {'cat':'MEC','tipo':'Micrometro Prof.','fab':'FACOM','modelo':'806.F','div':'F-21','ult':'','prox':'','status':'DESCALIBRADO','custo':84.33,'lab':'EMPRESA MQT','obs':'FERRAMENTA NAO UTILIZADA'},
    # === F-21 / MV ===
    {'cat':'MEC','tipo':'Paquímetro','fab':'FACOM','modelo':'805.1','div':'F-21','ult':'22/10/24','prox':'22/10/25','status':'falta certificado','custo':84.33,'lab':'EMPRESA MV'},
    {'cat':'MEC','tipo':'Paquímetro','fab':'FACOM','modelo':'805.1','div':'F-21','ult':'22/10/24','prox':'22/10/25','status':'falta certificado','custo':84.33,'lab':'EMPRESA MV'},
    {'cat':'MEC','tipo':'Paquímetro','fab':'FACOM','modelo':'805.1','div':'F-21','ult':'','prox':'','status':'DESCALIBRADO','custo':84.33,'lab':'EMPRESA MV'},
    {'cat':'MEC','tipo':'Paquímetro','fab':'FACOM','modelo':'805.1','div':'F-21','ult':'22/10/24','prox':'22/10/25','status':'falta certificado','custo':84.33,'lab':'EMPRESA MV'},
    # === F-21 / AMETEK (empresa autorizada exclusiva) ===
    {'cat':'ELE','tipo':'Fonte DC','fab':'AMETEK','modelo':'SGA-600625D-1D-AA','div':'F-21','ult':'26/01/21','prox':'','status':'DESCALIBRADO','custo':560.75,'lab':'EMPRESA AMETEK SIGTON','obs':'Calibracao exclusiva AMETEK — empresa Sigton SP'},
    # === F-21 / IPT (NI Certified Center) ===
    {'cat':'ELE','tipo':'Multímetro NI','fab':'NATIONAL INSTRUMENTS','modelo':'PXIE-4080','div':'F-21','ult':'03/08/20','prox':'','status':'DESCALIBRADO','custo':560.75,'lab':'EMPRESA IPT','obs':'Calibracao somente NI Certified Center — IPT/SP'},
    {'cat':'ELE','tipo':'Osciloscópio PXI NI','fab':'NATIONAL INSTRUMENTS','modelo':'NI-PXI-5122','div':'F-21','ult':'27/09/22','prox':'','status':'DESCALIBRADO','custo':776.23,'lab':'EMPRESA IPT','obs':'Calibracao somente NI Certified Center — IPT/SP'},
    # === EXOCET / CMS ===
    {'cat':'ELE','tipo':'Analisador de Espectro','fab':'ROHDE&SCHWARZ','modelo':'FSL18','div':'EXOCET','ult':'13/09/24','prox':'13/09/25','status':'CALIBRADO','custo':3104.95,'lab':'CMS'},
    {'cat':'ELE','tipo':'Gerador de Funções','fab':'AGILENT','modelo':'33220A','div':'EXOCET','ult':'10/09/24','prox':'10/09/25','status':'CALIBRADO','custo':1552.47,'lab':'CMS'},
    {'cat':'ELE','tipo':'Multímetro','fab':'FLUKE','modelo':'179','div':'EXOCET','ult':'27/10/23','prox':'27/10/25','status':'CALIBRADO','custo':560.75,'lab':'CMS'},
    {'cat':'ELE','tipo':'Multímetro','fab':'FLUKE','modelo':'73','div':'EXOCET','ult':'01/11/23','prox':'01/11/25','status':'CALIBRADO','custo':560.75,'lab':'CMS'},
    {'cat':'ELE','tipo':'Multímetro','fab':'FLUKE','modelo':'73','div':'EXOCET','ult':'11/04/25','prox':'11/04/26','status':'CALIBRADO','custo':776.23,'lab':'CMS'},
    {'cat':'ELE','tipo':'Multímetro 6 Dígitos','fab':'AGILENT','modelo':'34401A','div':'EXOCET','ult':'05/02/25','prox':'05/02/26','status':'CALIBRADO','custo':1164.35,'lab':'CMS'},
    {'cat':'ELE','tipo':'Osciloscópio','fab':'TEKTRONIX','modelo':'TDS210','div':'EXOCET','ult':'10/11/23','prox':'10/11/25','status':'CALIBRADO','custo':747.66,'lab':'CMS'},
    {'cat':'ELE','tipo':'Osciloscópio','fab':'TEKTRONIX','modelo':'TBS1102B','div':'EXOCET','ult':'10/11/23','prox':'10/11/25','status':'CALIBRADO','custo':747.66,'lab':'CMS'},
    # === MK-46 / CMS ===
    {'cat':'ELE','tipo':'Contador','fab':'HP','modelo':'5328B','div':'MK-46','ult':'10/08/23','prox':'10/08/25','status':'CALIBRADO','custo':1552.47,'lab':'CMS'},
    {'cat':'ELE','tipo':'Contador','fab':'HP','modelo':'5328B','div':'MK-46','ult':'','prox':'','status':'DESCALIBRADO','custo':4269.30,'lab':'CMS'},
    {'cat':'ELE','tipo':'Contador','fab':'HP','modelo':'5328B','div':'MK-46','ult':'','prox':'','status':'DESCALIBRADO','custo':1552.47,'lab':'CMS'},
    {'cat':'ELE','tipo':'Gerador de Funções','fab':'HP','modelo':'3325B','div':'MK-46','ult':'14/11/23','prox':'14/11/25','status':'CALIBRADO','custo':1869.16,'lab':'CMS'},
    {'cat':'ELE','tipo':'Multímetro','fab':'FLUKE','modelo':'87 V','div':'MK-46','ult':'08/08/24','prox':'08/08/25','status':'CALIBRADO','custo':1164.35,'lab':'CMS'},
    {'cat':'ELE','tipo':'Multímetro','fab':'ICEL','modelo':'6300','div':'MK-46','ult':'13/08/24','prox':'13/08/25','status':'CALIBRADO','custo':1164.35,'lab':'CMS'},
    {'cat':'ELE','tipo':'Multímetro','fab':'FLUKE','modelo':'87','div':'MK-46','ult':'08/08/24','prox':'08/08/25','status':'CALIBRADO','custo':1164.35,'lab':'CMS'},
    {'cat':'ELE','tipo':'Multímetro','fab':'FLUKE','modelo':'87','div':'MK-46','ult':'20/10/23','prox':'20/10/25','status':'CALIBRADO','custo':560.75,'lab':'CMS'},
    {'cat':'ELE','tipo':'Multímetro 6 Dígitos','fab':'HP','modelo':'3456A','div':'MK-46','ult':'11/02/25','prox':'11/02/26','status':'CALIBRADO','custo':1164.35,'lab':'CMS'},
    {'cat':'ELE','tipo':'Multímetro 6 Dígitos','fab':'HP','modelo':'3456A','div':'MK-46','ult':'11/02/25','prox':'11/02/26','status':'CALIBRADO','custo':1164.35,'lab':'CMS'},
    {'cat':'ELE','tipo':'Osciloscópio','fab':'KEYSIGHT','modelo':'DSO5034A','div':'MK-46','ult':'15/08/23','prox':'15/08/25','status':'CALIBRADO','custo':1552.47,'lab':'CMS'},
    {'cat':'ELE','tipo':'Osciloscópio','fab':'KEYSIGHT','modelo':'DSO5034A','div':'MK-46','ult':'20/10/23','prox':'20/10/25','status':'CALIBRADO','custo':747.66,'lab':'CMS'},
    # === MK-46 / MQT (CMS não calibra ou RACAL) ===
    {'cat':'ELE','tipo':'Gerador de Funções','fab':'RACAL','modelo':'3152B VXI','div':'MK-46','ult':'','prox':'','status':'DESCALIBRADO','custo':1552.47,'lab':'EMPRESA MQT','obs':'CMS NAO CALIBRA — encaminhar para MQT'},
    {'cat':'ELE','tipo':'Gerador de Funções','fab':'RACAL','modelo':'3152B VXI','div':'MK-46','ult':'','prox':'','status':'DESCALIBRADO','custo':1552.47,'lab':'EMPRESA MQT','obs':'CMS NAO CALIBRA — encaminhar para MQT'},
    {'cat':'ELE','tipo':'Contador','fab':'ASTRONICS','modelo':'2461-CD','div':'MK-46','ult':'','prox':'','status':'DESCALIBRADO','custo':1552.47,'lab':'EMPRESA MQT','obs':'Nao foi possivel calibrar — verificar viabilidade'},
    {'cat':'ELE','tipo':'Contador','fab':'ASTRONICS','modelo':'2461-CD','div':'MK-46','ult':'','prox':'','status':'DESCALIBRADO','custo':1552.47,'lab':'EMPRESA MQT','obs':'Nao foi possivel calibrar — verificar viabilidade'},
    # === MK-48 / CMS ===
    {'cat':'ELE','tipo':'Calibrador Multifunção','fab':'FLUKE','modelo':'5100B','div':'MK-48','ult':'10/01/25','prox':'10/01/26','status':'CALIBRADO','custo':3104.95,'lab':'CMS'},
    {'cat':'ELE','tipo':'Calibrador Multifunção','fab':'FLUKE','modelo':'5100B','div':'MK-48','ult':'08/11/24','prox':'08/11/25','status':'CALIBRADO','custo':3104.95,'lab':'CMS'},
    {'cat':'ELE','tipo':'Calibrador Multifunção','fab':'FLUKE','modelo':'5100B','div':'MK-48','ult':'19/01/23','prox':'19/01/25','status':'DESCALIBRADO','custo':3104.95,'lab':'CMS'},
    {'cat':'ELE','tipo':'Megôhmetro','fab':'TEGAM','modelo':'R1M-A','div':'MK-48','ult':'07/02/25','prox':'07/02/26','status':'CALIBRADO','custo':674.72,'lab':'CMS'},
    {'cat':'ELE','tipo':'Multímetro','fab':'SIMPSON','modelo':'260-6XLPM','div':'MK-48','ult':'21/11/24','prox':'21/11/25','status':'CALIBRADO','custo':776.23,'lab':'CMS'},
    {'cat':'ELE','tipo':'Multímetro','fab':'FLUKE','modelo':'77','div':'MK-48','ult':'21/03/24','prox':'21/03/25','status':'DESCALIBRADO','custo':776.23,'lab':'CMS'},
    {'cat':'ELE','tipo':'Multímetro','fab':'FLUKE','modelo':'83-V','div':'MK-48','ult':'25/03/24','prox':'25/03/25','status':'DESCALIBRADO','custo':560.75,'lab':'CMS'},
    {'cat':'ELE','tipo':'Osciloscópio','fab':'TEKTRONIX','modelo':'THS730A','div':'MK-48','ult':'18/08/22','prox':'18/08/24','status':'DESCALIBRADO','custo':747.66,'lab':'CMS'},
    {'cat':'ELE','tipo':'Osciloscópio','fab':'TEKTRONIX','modelo':'TBS1102B','div':'MK-48','ult':'08/04/24','prox':'08/04/25','status':'DESCALIBRADO','custo':747.66,'lab':'CMS'},
    {'cat':'ELE','tipo':'Amplificador Transcondutância','fab':'FLUKE','modelo':'5220A','div':'MK-48','ult':'24/11/23','prox':'24/11/25','status':'CALIBRADO','custo':776.23,'lab':'CMS'},
    {'cat':'ELE','tipo':'Amplificador Transcondutância','fab':'FLUKE','modelo':'5220A','div':'MK-48','ult':'12/06/24','prox':'12/06/26','status':'CALIBRADO','custo':373.86,'lab':'CMS'},
    # === MK-48 / AMETEK Sigton ===
    {'cat':'MEC','tipo':'Hydraulic Deadweight Tester','fab':'AMETEK','modelo':'DM-T-100/C','div':'MK-48','ult':'18/10/17','prox':'','status':'DESCALIBRADO','custo':84.33,'lab':'EMPRESA AMETEK SIGTON','obs':'Calibracao exclusiva AMETEK — empresa Sigton SP'},
    {'cat':'MEC','tipo':'Hydraulic Deadweight Tester','fab':'AMETEK','modelo':'DM-T-100/C','div':'MK-48','ult':'04/04/17','prox':'','status':'DESCALIBRADO','custo':84.33,'lab':'EMPRESA AMETEK SIGTON','obs':'Calibracao exclusiva AMETEK — empresa Sigton SP'},
    # === MK-48 / MV ===
    {'cat':'ELE','tipo':'Ground Strap Tester','fab':'','modelo':'253A','div':'MK-48','ult':'25/08/20','prox':'','status':'DESCALIBRADO','custo':0,'lab':'EMPRESA MV'},
    {'cat':'ELE','tipo':'Igniter Circuit Test','fab':'','modelo':'101-5BFAA','div':'MK-48','ult':'22/10/24','prox':'22/10/25','status':'falta certificado','custo':776.23,'lab':'EMPRESA MV'},
    {'cat':'ELE','tipo':'Igniter Circuit Test','fab':'','modelo':'101-5BFAA','div':'MK-48','ult':'22/10/24','prox':'22/10/25','status':'falta certificado','custo':776.23,'lab':'EMPRESA MV'},
    {'cat':'ELE','tipo':'Igniter Circuit Test','fab':'','modelo':'101-5BFAA','div':'MK-48','ult':'26/05/22','prox':'26/05/24','status':'DESCALIBRADO','custo':776.23,'lab':'EMPRESA MV','obs':'nao calibrar em 2024'},
    {'cat':'ELE','tipo':'Igniter Circuit Test','fab':'','modelo':'101-5BFAA','div':'MK-48','ult':'24/02/23','prox':'24/02/25','status':'DESCALIBRADO','custo':776.23,'lab':'EMPRESA MV','obs':'nao calibrar em 2024'},
    # === MISTRAL / CMS ===
    {'cat':'ELE','tipo':'Fonte DC','fab':'HP','modelo':'6255A','div':'MISTRAL','ult':'18/12/24','prox':'18/12/25','status':'CALIBRADO','custo':560.75,'lab':'CMS'},
    {'cat':'ELE','tipo':'Multímetro 6 Dígitos','fab':'KEYSIGHT','modelo':'34461A','div':'MISTRAL','ult':'05/10/17','prox':'','status':'EM REPARO','custo':776.23,'lab':'CMS','obs':'EM REPARO CMS desde 2017'},
    # === MINAS E BOMBAS ===
    {'cat':'ELE','tipo':'Multímetro','fab':'FLUKE','modelo':'77DMM','div':'MINAS E BOMBAS','ult':'09/11/23','prox':'09/11/25','status':'CALIBRADO','custo':776.23,'lab':'CMS'},
    {'cat':'MEC','tipo':'Manômetro Analógico','fab':'FAMABRAS','modelo':'0-3 kgf/cm2','div':'MINAS E BOMBAS','ult':'24/01/24','prox':'24/01/26','status':'CALIBRADO','custo':90.00,'lab':'EMPRESA MQT'},
    {'cat':'MEC','tipo':'Manômetro Analógico','fab':'FAMABRAS','modelo':'0-30 kgf/cm2','div':'MINAS E BOMBAS','ult':'24/01/24','prox':'24/01/26','status':'CALIBRADO','custo':90.00,'lab':'EMPRESA MQT'},
]

# ── CLI ───────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    import sys
    os.makedirs('/mnt/user-data/outputs', exist_ok=True)

    modo = sys.argv[1] if len(sys.argv) > 1 else 'lote'

    if modo == 'exemplo':
        # Gera um PS de exemplo único
        ps_exemplo = {
            'numero': 'PS-CMS-25-001',
            'laboratorio': 'CMS — Centro de Metrologia da Marinha',
            'divisao': 'MK-46',
            'prioridade': '12 meses',
            'data_emissao': datetime.date.today().strftime('%d/%m/%Y'),
            'contrato': 'ATA-Pregão/2025',
            'nup': '0801/2025/CMASM',
            'lote': 'LOTE 01',
            'observacoes': 'Instrumentos de medição elétrica da divisão MK-46. Prioridade: Contadores HP 5328B (descalibrados). Verificar estado dos equipamentos antes do envio.',
            'itens': _converter_itens([e for e in EQUIPAMENTOS_REAIS if e['div'] == 'MK-46' and e['lab'] == 'CMS']),
        }
        saida = '/mnt/user-data/outputs/PS-CMS-25-001__CMS__MK-46.pdf'
        gerar_ps(ps_exemplo, saida)
        print(f'PS gerado: {saida}')

    else:
        # Gera todos os PS agrupados por lab/divisão
        print('Gerando todos os PS do plano anual CMASM 2025...')
        arquivos = gerar_ps_lote(EQUIPAMENTOS_REAIS, ano=2025,
                                  dir_saida='/mnt/user-data/outputs')
        print(f'\n{len(arquivos)} PS gerados:')
        for a in arquivos:
            print(f'  {os.path.basename(a)}')
