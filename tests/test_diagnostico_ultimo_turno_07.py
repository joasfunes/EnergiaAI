"""Pruebas puras del diagnóstico. No hacen inferencias ni acceden a SQLite."""
from __future__ import annotations
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace as Msg

# El archivo se ejecuta desde el raíz del repositorio con unittest discover -s tests.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from diagnosticar_ultimo_turno_07 import analizar_mensajes

class TestDiagnosticoUltimoTurno(unittest.TestCase):
    def test_01_reporta_stop_sin_fingir_completitud(self):
        mensajes=[Msg(type='human',content='pregunta'),Msg(type='ai',content='Título sin terminar',
                    tool_calls=[],response_metadata={'done_reason':'stop','eval_count':81},additional_kwargs={})]
        reporte, texto = analizar_mensajes(mensajes)
        self.assertEqual(reporte['estado'],'respuesta_con_texto')
        self.assertEqual(reporte['respuesta_final_guardada_caracteres'],len('Título sin terminar'))
        self.assertIn('no prueba',reporte['mensaje'])
        self.assertEqual(texto,'Título sin terminar')

    def test_02_reporta_length(self):
        mensajes=[Msg(type='human'),Msg(type='ai',content='Parcial',tool_calls=[],
                    response_metadata={'done_reason':'length','eval_count':2048})]
        reporte,_=analizar_mensajes(mensajes)
        self.assertEqual(reporte['estado'],'limite_de_generacion_reportado')
        self.assertEqual(reporte['generaciones_modelo'][0]['metadata']['eval_count'],2048)

    def test_03_registra_tools_y_no_finge_respuesta(self):
        mensajes=[Msg(type='human'),Msg(type='ai',content='',tool_calls=[{'name':'buscar_consejos'}]),
                  Msg(type='tool',name='buscar_consejos'),Msg(type='ai',content='',tool_calls=[],response_metadata={'done_reason':'stop'})]
        reporte, texto=analizar_mensajes(mensajes)
        self.assertEqual(reporte['tools_ejecutadas_en_el_turno'],['buscar_consejos'])
        self.assertEqual(reporte['estado'],'sin_respuesta_final')
        self.assertEqual(texto,'')

    def test_04_solo_ultimo_turno(self):
        mensajes=[Msg(type='human'),Msg(type='tool',name='vieja'),Msg(type='human'),
                 Msg(type='tool',name='nueva'),Msg(type='ai',content='OK',tool_calls=[],response_metadata={})]
        reporte,_=analizar_mensajes(mensajes)
        self.assertEqual(reporte['tools_ejecutadas_en_el_turno'],['nueva'])

    def test_05_sin_turnos(self):
        reporte,_=analizar_mensajes([])
        self.assertEqual(reporte['estado'],'sin_turno')

    def test_06_no_muestra_textos_sensibles_en_json(self):
        prompt='token secreto de prueba 1234'
        mensaje='Dato privado 98476'
        mensajes=[Msg(type='human',content=prompt),Msg(type='ai',content=mensaje,tool_calls=[],
                    response_metadata={'model':'interno','done_reason':'stop'},additional_kwargs={'reasoning_content':'detalle secreto'})]
        reporte,_=analizar_mensajes(mensajes)
        import json
        txt=json.dumps(reporte)
        self.assertNotIn(prompt,txt)
        self.assertNotIn(mensaje,txt)
        self.assertNotIn('detalle secreto',txt)

if __name__=='__main__':unittest.main()
