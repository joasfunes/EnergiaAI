"""Pruebas sin Ollama, sin GPU y sin descargar modelos."""
from __future__ import annotations
import unittest
from dataclasses import dataclass
from unittest.mock import patch
from energia_ai.agent.local_llm import (
    comprobar_modelo_disponible, config_local, validar_url_local,
)
from energia_ai.agent.tool_trace import resumir_ejecuciones, ultimo_mensaje_asistente


@dataclass
class ToolMessage:
    name: str
    content: str


@dataclass
class AIMessage:
    content: str


@dataclass
class HumanMessage:
    content: str


class TestLocalLLM(unittest.TestCase):
    def test_url_predeterminada(self):
        self.assertEqual(validar_url_local('http://127.0.0.1:11434'), 'http://127.0.0.1:11434')

    def test_url_localhost(self):
        self.assertEqual(validar_url_local('http://localhost:11434/'), 'http://localhost:11434')

    def test_rechaza_servidor_externo(self):
        with self.assertRaises(ValueError):
            validar_url_local('http://example.com:11434')

    def test_rechaza_https_en_mvp(self):
        with self.assertRaises(ValueError):
            validar_url_local('https://localhost:11434')

    def test_rechaza_ruta(self):
        with self.assertRaises(ValueError):
            validar_url_local('http://127.0.0.1:11434/api/tags')

    def test_no_acepta_modelo_distinto(self):
        self.assertFalse(comprobar_modelo_disponible('qwen3.5:9b', ['embeddinggemma:300m']))

    def test_modelo_exacto(self):
        self.assertTrue(comprobar_modelo_disponible('qwen3.5:9b', ['qwen3.5:9b']))

    def test_config_por_defecto(self):
        with patch.dict('os.environ', {}, clear=True):
            c = config_local()
        self.assertEqual(c['model'], 'qwen3.5:9b')
        self.assertEqual(c['num_ctx'], 8192)

    def test_resumen_identifica_ejecucion_real(self):
        ms = [HumanMessage('hola'), AIMessage('solicito tool'), ToolMessage('calcular_consumo', '{"total":"10"}')]
        self.assertEqual(len(resumir_ejecuciones(ms)), 1)
        self.assertEqual(resumir_ejecuciones(ms)[0]['tool'], 'calcular_consumo')

    def test_ignora_intencion_sin_ejecucion(self):
        self.assertEqual(resumir_ejecuciones([AIMessage('Voy a llamar la tool')]), [])

    def test_ultimo_mensaje(self):
        self.assertEqual(ultimo_mensaje_asistente([AIMessage('uno'), ToolMessage('t', 'x'), AIMessage('dos')]), 'dos')


if __name__ == '__main__':
    unittest.main()
