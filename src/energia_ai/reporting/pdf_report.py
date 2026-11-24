"""Generador de PDF reproducible sin LLM ni escrituras a disco.

ReportLab Platypus construye el informe y gráficos vectoriales en memoria.
Usar solo datos validados del servicio de simulación y fuentes RAG permitidas.
"""
from __future__ import annotations
from decimal import Decimal, InvalidOperation
from html import escape
from io import BytesIO


def _num(texto: str | int | float | None, decimales: int = 2) -> str:
    try:
        numero = Decimal(str(texto))
        if not numero.is_finite():
            return 'No disponible'
        return f'{numero:,.{decimales}f}'.replace(',', '_').replace('.', ',').replace('_', '.')
    except (InvalidOperation, TypeError, ValueError):
        return 'No disponible'


def _p(s: object, limite: int = 550) -> str:
    """Escapar texto externo: las evidencias RAG son contenido NO confiable."""
    txt = str(s)[:limite] if s is not None else ''
    return escape(' '.join(txt.split()), quote=True)


def _comparacion_dibujo(actual: Decimal, propuesto: Decimal):
    from reportlab.graphics.shapes import Drawing, Rect, String
    from reportlab.lib.colors import HexColor
    d = Drawing(490, 116)
    maximo = max(actual, propuesto, Decimal('1'))
    for y, etiqueta, valor, color in [
        (74, 'Actual', actual, HexColor('#334155')),
        (23, 'Propuesto', propuesto, HexColor('#0d9488')),
    ]:
        d.add(String(12, y + 8, etiqueta, fontSize=11, fillColor=HexColor('#0f172a')))
        ancho = float(valor / maximo * 305)
        d.add(Rect(110, y, max(ancho, 0), 28, rx=3, fillColor=color, strokeColor=None))
        d.add(String(min(425, 120 + ancho), y + 8, f'{_num(valor, 2)} kWh',
                     fontSize=9, fillColor=HexColor('#0f172a')))
    return d


def _grafico_equipos(actuales: list[dict], propuestos: list[dict]):
    from reportlab.graphics.shapes import Drawing, Rect, String
    from reportlab.lib.colors import HexColor
    por_id = {x['id']: Decimal(x['consumo_kwh']) for x in propuestos}
    pares = [(x['nombre'], Decimal(x['consumo_kwh']), por_id[x['id']]) for x in actuales]
    pares.sort(key=lambda x: max(x[1], x[2]), reverse=True)
    pares = pares[:8]
    alto = 29 * len(pares) + 38
    d = Drawing(490, alto)
    techo = max((max(x[1], x[2]) for x in pares), default=Decimal('1')) or Decimal('1')
    d.add(String(11, alto - 15, 'Gris: actual', fontSize=9, fillColor=HexColor('#334155')))
    d.add(String(102, alto - 15, 'Verde: propuesto', fontSize=9, fillColor=HexColor('#0d9488')))
    for i, (nombre, a, b) in enumerate(pares):
        y = alto - 42 - 29 * i
        d.add(String(9, y + 5, str(nombre)[:20], fontSize=9, fillColor=HexColor('#0f172a')))
        d.add(Rect(143, y + 10, float(a / techo * 265), 9,
                   fillColor=HexColor('#334155'), strokeColor=None))
        d.add(Rect(143, y - 2, float(b / techo * 265), 9,
                   fillColor=HexColor('#0d9488'), strokeColor=None))
        d.add(String(422, y + 2, f'{_num(a,1)} / {_num(b,1)}', fontSize=8,
                     fillColor=HexColor('#334155')))
    return d


def generar_informe_pdf(analisis: dict) -> bytes:
    """Devuelve PDF en bytes. No debe ser llamado con texto libre del LLM."""
    if not isinstance(analisis, dict) or not analisis.get('equipos_actuales') or not analisis.get('equipos_propuestos'):
        raise ValueError('Faltan escenarios estructurados')
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
                                    KeepTogether, HRFlowable)
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.colors import HexColor

    actual = Decimal(analisis['consumo_actual_kwh'])
    propuesto = Decimal(analisis['consumo_propuesto_kwh'])
    ahorro = Decimal(analisis['ahorro_kwh'])
    if abs(actual - propuesto - ahorro) > Decimal('0.001'):
        raise ValueError('Incoherencia de consumos: se rechazó el PDF')
    if {x['id'] for x in analisis['equipos_actuales']} != {x['id'] for x in analisis['equipos_propuestos']}:
        raise ValueError('Los escenarios no contienen los mismos equipos')
    memoria = BytesIO()
    doc = SimpleDocTemplate(memoria, pagesize=A4, leftMargin=45, rightMargin=45,
                            topMargin=39, bottomMargin=40,
                            title='EnergiaAI | Informe energético estimativo',
                            author='EnergiaAI (prototipo académico)')
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='EA_Title', parent=styles['Title'], fontName='Helvetica-Bold',
                              textColor=HexColor('#0f766e'), fontSize=20, leading=25, spaceAfter=10))
    styles.add(ParagraphStyle(name='EA_Head', parent=styles['Heading2'], textColor=HexColor('#0f766e'),
                              fontSize=12, leading=17, spaceBefore=11, spaceAfter=5))
    styles.add(ParagraphStyle(name='EA_Body', parent=styles['BodyText'], fontSize=9.5,
                              leading=14, spaceAfter=5, alignment=TA_LEFT))
    styles.add(ParagraphStyle(name='EA_Foot', parent=styles['BodyText'], fontSize=8,
                              textColor=HexColor('#64748b'), leading=11))
    story = [Paragraph('EnergiaAI | Informe energético', styles['EA_Title']),
             Paragraph('Estimación de consumo y escenarios · Documento NO equivalente a una factura oficial.',
                       styles['EA_Body']),
             Paragraph('Generado: ' + _p(analisis.get('generado_en', ''), 60) +
                       ' · Período analizado: ' + str(analisis['periodo_dias']) + ' días', styles['EA_Foot']),
             Spacer(1, 9), HRFlowable(width='100%', thickness=1, color=HexColor('#cbd5e1')),
             Paragraph('1. Resumen de los escenarios', styles['EA_Head'])]
    filas = [
        ['Consumo estimado actual', f'{_num(actual)} kWh'],
        ['Consumo estimado propuesto', f'{_num(propuesto)} kWh'],
        ['Ahorro energético' if ahorro >= 0 else 'Aumento energético', f'{_num(abs(ahorro))} kWh'],
        ['Variación porcentual', f"{_num(analisis.get('ahorro_porcentual'))} %"],
    ]
    t = Table(filas, colWidths=[270, 214], hAlign='LEFT')
    t.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,-1),HexColor('#f1f5f9')),
        ('ROWBACKGROUNDS',(0,0),(-1,-1),[HexColor('#f8fafc'),colors.white]),
        ('TEXTCOLOR',(0,0),(-1,-1),HexColor('#0f172a')),
        ('FONTNAME',(0,0),(0,-1),'Helvetica-Bold'),
        ('FONTSIZE',(0,0),(-1,-1),9), ('BOTTOMPADDING',(0,0),(-1,-1),7),
        ('TOPPADDING',(0,0),(-1,-1),7), ('LEFTPADDING',(0,0),(-1,-1),12),
    ]))
    story.extend([t, Spacer(1, 8), _comparacion_dibujo(actual, propuesto),
                  Paragraph('2. Consumo por electrodoméstico (kWh)',styles['EA_Head']),
                  _grafico_equipos(analisis['equipos_actuales'], analisis['equipos_propuestos'])])
    if len(analisis['equipos_actuales']) > 8:
        story.append(Paragraph('El gráfico muestra los ocho equipos con mayor consumo.', styles['EA_Foot']))
    story.append(Paragraph('3. Interpretación económica', styles['EA_Head']))
    if analisis.get('monetario_disponible') is True and analisis.get('ahorro_variable_ars') is not None:
        story.append(Paragraph('Diferencia estimada del <b>componente variable</b>: ARS '
                    + _num(analisis['ahorro_variable_ars']) + '.', styles['EA_Body']))
        fuente = analisis.get('fuente_tarifa') or {}
        story.append(Paragraph('Fuente tarifaria indicada por la simulación: '
                    + _p(fuente.get('organismo','EPRE Mendoza'), 60) + ' · '
                    + _p(fuente.get('resolucion',''), 70) + ' · '
                    + _p(fuente.get('anexo',''), 40) + '.', styles['EA_Body']))
        if isinstance(fuente.get('url'), str) and fuente['url'].startswith('https://epremendoza.gob.ar/'):
            url = escape(fuente['url'], quote=True)
            story.append(Paragraph(f'<link href="{url}" color="#0f766e">Documento tarifario oficial</link>', styles['EA_Foot']))
    else:
        story.append(Paragraph('No se informa ahorro en ARS. ' +
            _p(analisis.get('motivo_sin_dinero') or 'Los datos no permiten una estimación monetaria válida.'),
            styles['EA_Body']))
    story.append(Paragraph('No se incluyen impuestos, tasas, cargos fijos, prorrateos ni una factura completa.',
                           styles['EA_Foot']))
    story.append(Paragraph('4. Evidencia documental recuperada', styles['EA_Head']))
    evidencia = analisis.get('evidencias_rag') or []
    if not evidencia:
        story.append(Paragraph('Este análisis no incluyó una recuperación RAG verificable en el mismo turno. '
               'El informe no agrega consejos ni fuentes que el agente no haya consultado.', styles['EA_Body']))
    else:
        story.append(Paragraph('Extractos documentales recuperados; no equivalen a porcentajes de ahorro verificados '
                               'para este hogar.',styles['EA_Foot']))
        for i, e in enumerate(evidencia[:3], 1):
            titular = f"{i}. {_p(e.get('documento','Fuente oficial'),120)}"
            if e.get('pagina'):
                titular += f" (p. {int(e['pagina'])})"
            parrafos = [Paragraph('<b>' + titular + '</b>', styles['EA_Body']),
                        Paragraph('Extracto: ' + _p(e.get('texto',''),480), styles['EA_Body'])]
            url = e.get('url')
            if isinstance(url, str) and url.startswith('https://') and len(url) < 250:
                parrafos.append(Paragraph('<link href="' + escape(url,quote=True)
                    + '" color="#0f766e">Consultar fuente oficial</link>',styles['EA_Foot']))
            story.append(KeepTogether(parrafos))
            story.append(Spacer(1, 8))
    story.append(Paragraph('5. Advertencias y supuestos', styles['EA_Head']))
    for nota in (analisis.get('advertencias') or [])[:8]:
        story.append(Paragraph('• ' + _p(nota, 300), styles['EA_Foot']))
    story.append(Paragraph('Los valores provienen de resultados estructurados de las tools, no de cálculos '
                           'nuevos generados por el LLM. Este documento es un informe orientativo.',styles['EA_Foot']))
    def footer(canvas, pdf):
        canvas.saveState()
        canvas.setStrokeColor(HexColor('#cbd5e1'))
        canvas.line(45, 38, A4[0]-45, 38)
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(HexColor('#64748b'))
        canvas.drawString(45, 25, 'EnergiaAI · Mendoza · Prototipo académico local')
        canvas.drawRightString(A4[0]-45,25, f'Página {pdf.page}')
        canvas.restoreState()
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return memoria.getvalue()
