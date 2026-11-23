"""Prueba del nuevo evento de solicitud con stream real simulado."""
import unittest
from dataclasses import dataclass
from energia_ai.agent.streaming import transmitir_turno


@dataclass
class Msg:
    type: str
    content: str
    name: str = ''
    tool_calls: list | None = None


class Agente:
    def stream(self, _payload, *, config, stream_mode, version):
        yield ('updates', {'model': {'messages':[Msg('ai','',tool_calls=[{
            'name':'consultar_tarifa','args':{'distribuidora':'EDEMSA',
             'regimen':'SIN_SEF','hogar_id':'NO'}}])]}})
        yield ('updates', {'tools':{'messages':[Msg('tool','{"estado":"ok"}', name='consultar_tarifa')]}})
        yield ('messages', (Msg('AIMessageChunk','Tarifa R2'),{}))


class TestStreamingUI(unittest.TestCase):
    def test_solicitud_ejecucion_y_texto_en_orden(self):
        ev=[]
        transmitir_turno(Agente(), consulta='hola', thread_id='t1', notificar=ev.append)
        self.assertEqual([x['tipo'] for x in ev], ['tool_solicitada','tool','texto','fin'])
        self.assertNotIn('hogar_id',ev[0]['argumentos'])
        self.assertEqual(ev[0]['argumentos']['regimen'],'SIN_SEF')


if __name__ == '__main__':
    unittest.main()
