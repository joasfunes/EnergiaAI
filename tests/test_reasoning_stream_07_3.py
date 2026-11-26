"""Canales de razonamiento de Ollama, con fakes: sin Ollama ni GPU."""
from __future__ import annotations

import sys
import types
import unittest
from dataclasses import dataclass, field
from unittest.mock import patch

from energia_ai.agent.local_llm import crear_modelo
from energia_ai.agent.streaming import (
    razonamiento_del_chunk, texto_del_chunk, transmitir_turno,
)


@dataclass
class FakeAIChunk:
    type: str = "AIMessageChunk"
    content: str | list = ""
    additional_kwargs: dict = field(default_factory=dict)
    content_blocks: list | None = None


class FakeAgent:
    def __init__(self, chunks):
        self.chunks = chunks

    def stream(self, _incoming, *, config, stream_mode, version):
        assert version == "v1"
        assert stream_mode == ["messages", "updates"]
        for chunk in self.chunks:
            yield ("messages", (chunk, {"langgraph_node": "model"}))


class TestReasoningStream(unittest.TestCase):
    def test_01_ollama_additional_kwargs(self):
        chunk = FakeAIChunk(content="La respuesta", additional_kwargs={"reasoning_content": "Evaluando..."})
        self.assertEqual(razonamiento_del_chunk(chunk), "Evaluando...")
        self.assertEqual(texto_del_chunk(chunk), "La respuesta")

    def test_02_razonamiento_en_bloques_normalizados(self):
        chunk = FakeAIChunk(content="OK", content_blocks=[{"type": "reasoning", "reasoning": "Paso"}])
        self.assertEqual(razonamiento_del_chunk(chunk), "Paso")

    def test_03_no_duplica_bloques_y_kwargs(self):
        chunk = FakeAIChunk(content="OK", additional_kwargs={"reasoning_content": "Uno"},
                            content_blocks=[{"type": "reasoning", "reasoning": "Uno"}])
        self.assertEqual(razonamiento_del_chunk(chunk), "Uno")

    def test_04_content_bloques_separados(self):
        chunk = FakeAIChunk(content=[{"type": "reasoning", "reasoning": "Pensando"},
                                     {"type": "text", "text": "Respuesta"}])
        self.assertEqual(razonamiento_del_chunk(chunk), "Pensando")
        self.assertEqual(texto_del_chunk(chunk), "Respuesta")

    def test_05_sin_razonamiento_no_inventa(self):
        self.assertEqual(razonamiento_del_chunk(FakeAIChunk(content="hola")), "")

    def test_06_stream_separa_razonamiento_y_final(self):
        events = []
        agente = FakeAgent([
            FakeAIChunk(content="", additional_kwargs={"reasoning_content": "Primer "}),
            FakeAIChunk(content="", additional_kwargs={"reasoning_content": "paso"}),
            FakeAIChunk(content="Resultado."),
        ])
        transmitir_turno(agente, consulta="hola", thread_id="prueba", notificar=events.append)
        self.assertEqual([event["tipo"] for event in events],
                         ["razonamiento", "razonamiento", "texto", "fin"])
        self.assertEqual("".join(e["texto"] for e in events if e["tipo"] == "texto"), "Resultado.")
        self.assertEqual("".join(e["texto"] for e in events if e["tipo"] == "razonamiento"), "Primer paso")

    def test_07_stream_no_muestra_razonamiento_como_respuesta(self):
        events = []
        transmitir_turno(FakeAgent([FakeAIChunk(content="", additional_kwargs={"reasoning_content": "solo thinking"})]),
                        consulta="hola", thread_id="p2", notificar=events.append)
        self.assertEqual([e["tipo"] for e in events], ["razonamiento", "fin"])

    def test_08_modelo_configurado_con_thinking_explicito(self):
        capturado = {}
        fake = types.ModuleType("langchain_ollama")
        def chat_ollama(**kwargs):
            capturado.update(kwargs)
            return object()
        fake.ChatOllama = chat_ollama
        with patch.dict(sys.modules, {"langchain_ollama": fake}):
            crear_modelo()
        self.assertIs(capturado["reasoning"], True)
        self.assertEqual(capturado["num_ctx"], 16384)
        self.assertEqual(capturado["model"], "qwen3.5:9b")

    def test_09_no_emite_razonamiento_para_human(self):
        events = []
        transmitir_turno(FakeAgent([FakeAIChunk(type="human", content="hola",
                                               additional_kwargs={"reasoning_content": "NO"})]),
                        consulta="hola", thread_id="p3", notificar=events.append)
        self.assertEqual([e["tipo"] for e in events], ["fin"])


if __name__ == "__main__":
    unittest.main()
