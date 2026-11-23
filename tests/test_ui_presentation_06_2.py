"""Pruebas de sanitización, historial y lectura de métricas."""
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from energia_ai.ui.presentation import (argumentos_para_ui, historial_visible,
    solicitudes_en_update, cargar_medicion_06_1)


@dataclass
class Mensaje:
    type: str
    content: str
    tool_calls: list | None = None


class Estado:
    def __init__(self, ms):
        self.values = {'messages': ms}


class Agente:
    def __init__(self, ms):
        self.m = ms
    def get_state(self, config):
        assert config['configurable']['thread_id'] == 'mi_chat'
        return Estado(self.m)


class TestPresentacion(unittest.TestCase):
    def test_argumentos_num_y_consulta(self):
        r = argumentos_para_ui('buscar_consejos', {'consulta':'¿Consejos de verano?', 'hogar_id':'privado', 'api_key':'secreta'})
        self.assertEqual(r, {'consulta':'¿Consejos de verano?'})

    def test_argumentos_equipos_listas_limitadas(self):
        r = argumentos_para_ui('calcular_consumo', {
            'equipos': [{'id':'tv_1', 'nombre':'Televisor', 'potencia_watts':100, 'password':'NO'}],
            'periodo_dias':20})
        self.assertEqual(r['equipos'][0]['id'], 'tv_1')
        self.assertNotIn('password', str(r))

    def test_argumentos_sin_infinitos_ni_objetos_peligrosos(self):
        r = argumentos_para_ui('simular_ahorro', {'periodo_dias':float('inf'),
            'hogar_id':'privado', 'tarifa_consultada':{'estado':'ok', 'token':'oculto'}})
        self.assertEqual(r, {'tarifa_consultada':{'estado':'ok'}})

    def test_solicitudes_separadas_de_ejecuciones(self):
        solicitud = Mensaje('ai','', tool_calls=[{'name':'calcular_consumo',
            'args':{'periodo_dias':20, 'equipos':[{'nombre':'Televisor'}]}}])
        r = solicitudes_en_update({'model':{'messages':[solicitud]},
                                   'tools':{'messages':[Mensaje('tool','{"estado":"ok"}')]}})
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0]['tipo'], 'tool_solicitada')
        self.assertEqual(r[0]['nombre'], 'calcular_consumo')

    def test_mensajes_visibles_omiten_tool_calls_y_resultados(self):
        m = [Mensaje('human','Tengo televisor'),
             Mensaje('ai','', tool_calls=[{'name':'calcular_consumo','args':{}}]),
             Mensaje('tool','{"estado":"ok"}'),
             Mensaje('ai','El resultado es **10 kWh**')]
        r = historial_visible(Agente(m),'mi_chat')
        self.assertEqual([x['role'] for x in r], ['user','assistant'])
        self.assertIn('10 kWh',r[1]['content'])

    def test_faltantes_no_inventan_metricas(self):
        with TemporaryDirectory() as d:
            self.assertIsNone(cargar_medicion_06_1(Path(d)/'falta.json'))

    def test_lectura_resumen_telemetria(self):
        with TemporaryDirectory() as d:
            p = Path(d)/'m.json'
            p.write_text(json.dumps({'duracion_total_s':151.3, 'duracion_modelo_observada_s':120.0,
                'tiempo_primera_salida_s':3.12, 'llamadas_modelo':3}), encoding='utf-8')
            r = cargar_medicion_06_1(p)
            self.assertEqual(r['duracion_total_s'],151.3)
            self.assertEqual(r['llamadas_modelo'],3)

    def test_metrica_corrupta_no_se_muestra(self):
        with TemporaryDirectory() as d:
            p = Path(d)/'m.json'; p.write_text('{no-json', encoding='utf-8')
            self.assertIsNone(cargar_medicion_06_1(p))


if __name__ == '__main__':
    unittest.main()
