"""Pruebas sin LangChain, Ollama ni Chroma de los eventos de streaming."""
from dataclasses import dataclass
import unittest

from energia_ai.agent.streaming import texto_del_chunk, eventos_de_actualizacion, transmitir_turno


@dataclass
class Mensaje:
    type: str
    content: object
    name: str = ''


class AgenteFake:
    def __init__(self):
        self.config = None
    def stream(self, payload, *, config, stream_mode, version):
        self.config = config
        assert version == 'v1'
        assert stream_mode == ['messages', 'updates']
        yield ('messages', (Mensaje('AIMessageChunk', 'Respuesta '), {}))
        yield ('messages', (Mensaje('AIMessageChunk', [{'type':'text','text':'final'}]), {}))
        yield ('updates', {'tools': {'messages': [Mensaje('tool', '{"estado":"ok"}', 'consultar_inventario')]}})


class TestStreaming(unittest.TestCase):
    def test_texto_cadena(self):
        self.assertEqual(texto_del_chunk(Mensaje('AIMessageChunk', 'hola')), 'hola')

    def test_texto_partes(self):
        self.assertEqual(texto_del_chunk(Mensaje('AIMessageChunk', [{'type':'text','text':'uno'}, {'type':'image','text':'oculto'}])), 'uno')

    def test_sin_contenido(self):
        self.assertEqual(texto_del_chunk(Mensaje('AIMessageChunk', None)), '')

    def test_tool_message(self):
        evento = eventos_de_actualizacion({'tools': {'messages': [Mensaje('tool','{"estado":"ok"}', 'guardar')]}})
        self.assertEqual(evento, [{'tipo':'tool', 'nombre':'guardar', 'estado':'ok'}])

    def test_no_fingir_tools(self):
        self.assertEqual(eventos_de_actualizacion({'model': {'messages': [Mensaje('tool', '{}', 'fake')]}}), [])

    def test_json_invalido(self):
        evento = eventos_de_actualizacion({'tools': {'messages': [Mensaje('tool', '---', 'guardar')]}})
        self.assertEqual(evento[0]['estado'], 'desconocido')

    def test_stream_completo(self):
        agent = AgenteFake()
        eventos = []
        transmitir_turno(agent, consulta='Consulta', thread_id='casa1', notificar=eventos.append)
        self.assertEqual([x['tipo'] for x in eventos], ['texto','texto','tool','fin'])
        self.assertEqual(agent.config['configurable']['thread_id'], 'casa1')

    def test_consulta_vacia(self):
        with self.assertRaises(ValueError):
            transmitir_turno(AgenteFake(), consulta='  ', thread_id='casa1', notificar=lambda x: None)

    def test_callback_invalido(self):
        with self.assertRaises(TypeError):
            transmitir_turno(AgenteFake(), consulta='hola', thread_id='casa1', notificar=None)


if __name__ == '__main__':
    unittest.main()
