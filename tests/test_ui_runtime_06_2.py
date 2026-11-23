"""Integración del puente con componentes falsos, sin Streamlit/Ollama."""
from contextlib import contextmanager
import unittest
from unittest.mock import patch

from energia_ai.ui.runtime import ejecutar_stream_ui, recuperar_historial


class AgenteFalso:
    pass


@contextmanager
def runtime_falso(**kwargs):
    class R:
        agente = AgenteFalso()
    yield R()


class TestRuntimeUI(unittest.TestCase):
    def test_stream_produce_eventos_y_resumen(self):
        def ejecutar(agente, *, consulta, thread_id, notificar):
            notificar({'tipo':'tool_fin', 'nombre':'calcular_consumo','estado':'ok'})
            notificar({'tipo':'texto','texto':'10 kWh'})
            return {'duracion_total_s':2.0}
        with patch('energia_ai.ui.runtime.abrir_runtime_persistente', runtime_falso), patch(
             'energia_ai.ui.runtime.ejecutar_turno_medido', ejecutar):
            res=list(ejecutar_stream_ui(hogar_id='casa', thread_id='thread', consulta='calcular'))
        self.assertEqual([a for a,_ in res],['evento','evento','resumen'])
        self.assertEqual(res[-1][1]['duracion_total_s'],2.0)

    def test_stream_no_revela_mensaje_crudo_de_error(self):
        def fallar(*args, **kwargs):
            raise RuntimeError('clave_privada_no_debe_salir')
        with patch('energia_ai.ui.runtime.abrir_runtime_persistente', runtime_falso), patch(
             'energia_ai.ui.runtime.ejecutar_turno_medido', fallar):
            res=list(ejecutar_stream_ui(hogar_id='casa', thread_id='thread', consulta='hola'))
        self.assertEqual(res, [('error','RuntimeError')])
        self.assertNotIn('clave_privada',str(res))

    def test_consulta_vacia(self):
        with self.assertRaises(ValueError):
            list(ejecutar_stream_ui(hogar_id='casa',thread_id='thread',consulta='  '))

    def test_reabre_historico(self):
        with patch('energia_ai.ui.runtime.abrir_runtime_persistente', runtime_falso), patch(
             'energia_ai.ui.runtime.historial_visible', return_value=[{'role':'user','content':'hola'}]) as read:
            r=recuperar_historial(hogar_id='casa',thread_id='thread')
        self.assertEqual(r[0]['content'],'hola')
        read.assert_called_once()

    def test_stream_eventos_separados_de_st(self):
        import sys
        self.assertNotIn('streamlit',__import__('energia_ai.ui.runtime',fromlist=['x']).__dict__)


if __name__ == '__main__':
    unittest.main()
