"""Pruebas de orquestación, sin descargar Qwen ni indexar documentos."""
from __future__ import annotations

import sys
import types
import unittest
from unittest.mock import MagicMock, patch

from energia_ai.agent.full_agent import (
    SYSTEM_PROMPT, TOOL_NAMES, crear_agente_completo, verificar_herramientas,
)


def tools_falsas():
    return [types.SimpleNamespace(name=name, invoke=lambda x: x) for name in TOOL_NAMES]


def modulos_falsos():
    def fake_module(name):
        m = types.ModuleType(name)
        m.__path__ = []
        return m

    d = {name: fake_module(name) for name in (
        "langchain", "langchain.agents", "langgraph", "langgraph.checkpoint",
        "langgraph.checkpoint.memory",
    )}
    d["langchain.agents"].create_agent = MagicMock(return_value="AGENTE_CREADO")
    d["langgraph.checkpoint.memory"].InMemorySaver = MagicMock(return_value="MEMORIA")
    return d


class TestRegistroHerramientas(unittest.TestCase):
    def test_cuatro_nombres(self):
        self.assertEqual(len(TOOL_NAMES), 4)

    def test_validacion_cuatro(self):
        self.assertEqual(verificar_herramientas(tools_falsas()), TOOL_NAMES)

    def test_rechaza_orden_distinto(self):
        tools = tools_falsas()
        tools[0], tools[1] = tools[1], tools[0]
        with self.assertRaises(ValueError):
            verificar_herramientas(tools)

    def test_rechaza_duplicados(self):
        tools = tools_falsas()
        tools[-1].name = "calcular_consumo"
        with self.assertRaises(ValueError):
            verificar_herramientas(tools)

    def test_rechaza_objetos_sin_invoke(self):
        tools = tools_falsas()
        tools[2].invoke = None
        with self.assertRaises(TypeError):
            verificar_herramientas(tools)

    def test_prompt_cuatro_tools_y_restricciones(self):
        for name in TOOL_NAMES:
            self.assertIn(name, SYSTEM_PROMPT)
        for control in ("SIN_SEF", "CON_SEF", "datos", "instrucciones", "COMPONENTE"):
            self.assertIn(control, SYSTEM_PROMPT)

    def test_create_agent_inyeccion_modelo_y_memoria(self):
        fake_modules = modulos_falsos()
        with patch.dict(sys.modules, fake_modules), patch(
            "energia_ai.agent.full_agent.herramientas_energia_ai", return_value=tools_falsas()
        ), patch("energia_ai.agent.full_agent.crear_modelo") as factory:
            resultado = crear_agente_completo(model="MODELO", checkpointer="CHECKPOINTER")
            self.assertEqual(resultado, "AGENTE_CREADO")
            fake_modules["langchain.agents"].create_agent.assert_called_once()
            kwargs = fake_modules["langchain.agents"].create_agent.call_args.kwargs
            self.assertEqual(kwargs["model"], "MODELO")
            self.assertEqual(kwargs["checkpointer"], "CHECKPOINTER")
            self.assertEqual(len(kwargs["tools"]), 4)
            factory.assert_not_called()

    def test_create_agent_crea_memoria_y_modelo_si_no_se_inyectan(self):
        fake_modules = modulos_falsos()
        with patch.dict(sys.modules, fake_modules), patch(
            "energia_ai.agent.full_agent.herramientas_energia_ai", return_value=tools_falsas()
        ), patch("energia_ai.agent.full_agent.crear_modelo", return_value="QWEN") as factory:
            crear_agente_completo()
            kwargs = fake_modules["langchain.agents"].create_agent.call_args.kwargs
            self.assertEqual(kwargs["model"], "QWEN")
            self.assertEqual(kwargs["checkpointer"], "MEMORIA")
            factory.assert_called_once()


if __name__ == "__main__":
    unittest.main()
