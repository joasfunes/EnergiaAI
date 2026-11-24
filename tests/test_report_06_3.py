"""Pruebas sin Ollama, Streamlit ni LangChain: datos estructurados y PDF."""
from __future__ import annotations
from dataclasses import dataclass
from copy import deepcopy
from decimal import Decimal
from io import BytesIO
import json
import unittest

from energia_ai.reporting.extraction import (
    InformeNoDisponible, FUENTES_APROBADAS, extraer_ultimo_analisis, _validar_simulacion)
from energia_ai.reporting.pdf_report import generar_informe_pdf


@dataclass
class Msg:
    type: str
    content: str
    name: str = ''


def sim_ok():
    def escenario(c):
        return {'estado':'ok','consumo_total_kwh':str(c),'equipos':[
            {'id':'aire_1','nombre':'Aire acondicionado','consumo_kwh':str(c),'cantidad':1}]}
    return {'estado':'ok','tipo_resultado':'comparacion_de_escenarios_no_factura',
        'periodo_dias':60,'escenario_actual':escenario('75.0000'),
        'escenario_propuesto':escenario('45.0000'),'ahorro_kwh':'30.0000',
        'ahorro_porcentual_equipos':'40.00','estimacion_monetaria_disponible':False,
        'ahorro_componente_variable_estimado_ars':None,
        'motivo_sin_estimacion_monetaria':'No aplica la categoría',
        'advertencias':['No es una factura'], 'fuente_tarifa':None}


def test_mensajes(sim=None):
    sim = sim or sim_ok()
    return [Msg('human','consulta'),Msg('tool',json.dumps(sim),name='simular_ahorro'),
            Msg('ai','Respuesta con kWh')]


class TestsInformes(unittest.TestCase):
    def test_extraccion_ultimo_turno(self):
        r=extraer_ultimo_analisis(test_mensajes())
        self.assertEqual(r['ahorro_kwh'],'30.0000')
        self.assertEqual(r['origen'],'resultados reales de tools de un mismo turno')

    def test_no_crea_pdf_sin_simulacion(self):
        with self.assertRaises(InformeNoDisponible):
            extraer_ultimo_analisis([Msg('human','Hola'),Msg('ai','Ahorrás 100 kWh')])

    def test_turno_antiguo_valido_no_se_mezcla_con_rag_posterior(self):
        msgs=test_mensajes()+[Msg('human','Después pregunté por la luz'),
            Msg('tool',json.dumps({'estado':'ok','resultados':[{'fuente_id':'ARG-RES-2024',
                'url':FUENTES_APROBADAS['ARG-RES-2024'],'texto':'LED'}]}),name='buscar_consejos')]
        r=extraer_ultimo_analisis(msgs)
        self.assertEqual(r['evidencias_rag'],[])

    def test_rechaza_resultado_de_tool_error(self):
        m=test_mensajes({'estado':'error'})
        with self.assertRaises(InformeNoDisponible): extraer_ultimo_analisis(m)

    def test_rechaza_delta_incoherente(self):
        s=sim_ok();s['ahorro_kwh']='35.0000'
        with self.assertRaises(InformeNoDisponible): extraer_ultimo_analisis(test_mensajes(s))

    def test_rechaza_total_equipos_incoherente(self):
        s=sim_ok();s['escenario_actual']['consumo_total_kwh']='78'
        with self.assertRaises(InformeNoDisponible): extraer_ultimo_analisis(test_mensajes(s))

    def test_rechaza_equipos_diferentes(self):
        s=sim_ok();s['escenario_propuesto']['equipos'][0]['id']='otro'
        with self.assertRaises(InformeNoDisponible):extraer_ultimo_analisis(test_mensajes(s))

    def test_rechaza_porcentaje_incoherente(self):
        s=sim_ok();s['ahorro_porcentual_equipos']='75'
        with self.assertRaises(InformeNoDisponible):extraer_ultimo_analisis(test_mensajes(s))

    def test_sin_rag_no_inventa_documentos(self):
        r=extraer_ultimo_analisis(test_mensajes());self.assertEqual(r['evidencias_rag'],[])

    def test_rag_mismo_turno_documentado(self):
        rag={'estado':'ok','resultados':[{'fuente_id':'EPRE-VER-2025',
            'url':FUENTES_APROBADAS['EPRE-VER-2025'],'texto':'Mantener filtros limpios',
            'documento':'EPRE verano','pagina':None}]}
        m=[test_mensajes()[0],Msg('tool',json.dumps(rag),name='buscar_consejos')]+test_mensajes()[1:]
        r=extraer_ultimo_analisis(m)
        self.assertEqual(r['evidencias_rag'][0]['texto'],'Mantener filtros limpios')

    def test_rechaza_url_no_aprobada(self):
        rag={'estado':'ok','resultados':[{'fuente_id':'EPRE-VER-2025',
            'url':'https://no-oficial.example/','texto':'Publicidad'}]}
        m=[Msg('human','consulta'),Msg('tool',json.dumps(rag),name='buscar_consejos'),
           Msg('tool',json.dumps(sim_ok()),name='simular_ahorro')]
        r=extraer_ultimo_analisis(m)
        self.assertEqual(r['evidencias_rag'],[])

    def test_no_monetiza_si_estado_no_contrastado(self):
        s=sim_ok();s['estimacion_monetaria_disponible']=True
        s['ahorro_componente_variable_estimado_ars']='8682.95'
        s['fuente_tarifa']={'estado_revision':'PENDIENTE_CONTRASTE_CON_PDF_LOCAL'}
        r=extraer_ultimo_analisis(test_mensajes(s));self.assertFalse(r['monetario_disponible'])

    def test_monetiza_solo_si_contrastado(self):
        s=sim_ok();s['estimacion_monetaria_disponible']=True
        s['ahorro_componente_variable_estimado_ars']='8682.95'
        s['fuente_tarifa']={'estado_revision':'CONTRASTADO_CON_PDF_LOCAL','organismo':'EPRE Mendoza',
            'resolucion':'EPRE 221/2026', 'url':'https://epremendoza.gob.ar/2019/resoluciones-anexos/Res%20221-2026.pdf'}
        r=extraer_ultimo_analisis(test_mensajes(s));self.assertEqual(r['ahorro_variable_ars'],'8682.95')

    def test_pdf_valido_en_memoria(self):
        r=extraer_ultimo_analisis(test_mensajes())
        b=generar_informe_pdf(r)
        self.assertGreater(len(b),3000)
        self.assertTrue(b.startswith(b'%PDF-'))

    def test_pdf_sin_llm_ni_plantilla_hardcodeada(self):
        r=extraer_ultimo_analisis(test_mensajes())
        b=generar_informe_pdf(r)
        from pypdf import PdfReader
        texto='\n'.join(p.extract_text() or '' for p in PdfReader(BytesIO(b)).pages)
        self.assertIn('30,00 kWh',texto)
        self.assertIn('No se informa ahorro en ARS',texto)
        self.assertIn('Este análisis no incluyó una recuperación RAG',texto)

    def test_pdf_con_fuente_oficial_real(self):
        rag={'estado':'ok','resultados':[{'fuente_id':'EPRE-VER-2025',
            'url':FUENTES_APROBADAS['EPRE-VER-2025'],
            'texto':'Mantener los filtros limpios', 'documento':'EPRE verano'}]}
        msgs=[Msg('human','analisis'),Msg('tool',json.dumps(sim_ok()),name='simular_ahorro'),
              Msg('tool',json.dumps(rag),name='buscar_consejos')]
        r=extraer_ultimo_analisis(msgs)
        b=generar_informe_pdf(r)
        from pypdf import PdfReader
        contenido='\n'.join(p.extract_text() or '' for p in PdfReader(BytesIO(b)).pages)
        self.assertIn('Mantener los filtros limpios',contenido)


if __name__ == '__main__':unittest.main()
