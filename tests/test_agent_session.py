"""Tests de sesiones sin modelo, GPU, Chroma ni LangChain."""
from __future__ import annotations

from dataclasses import dataclass
import unittest

from energia_ai.agent.session import (
    analizar_ejecuciones, configuracion_thread, ejecutar_turno, tools_ejecutadas,
)


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


class Estado:
    def __init__(self, messages):
        self.values = {"messages": messages}


class AgenteFalso:
    def __init__(self):
        self.messages = []
        self.thread_ids = []

    def get_state(self, config):
        self.thread_ids.append(config["configurable"]["thread_id"])
        return Estado(list(self.messages))

    def invoke(self, payload, *, config):
        self.thread_ids.append(config["configurable"]["thread_id"])
        self.messages.extend([
            HumanMessage(payload["messages"][0]["content"]),
            ToolMessage("calcular_consumo", '{"estado": "ok"}'),
            AIMessage("Se calcularon 10 kWh"),
        ])
        return {"messages": list(self.messages)}


class TestSesion(unittest.TestCase):
    def test_thread_id_admitido(self):
        c = configuracion_thread("casa_1-2026")
        self.assertEqual(c["configurable"]["thread_id"], "casa_1-2026")

    def test_thread_id_invalido(self):
        for invalid in ("", "espacio en id", "../ruta", "a" * 81, "ñ"):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                configuracion_thread(invalid)

    def test_limites_de_recursion(self):
        for invalid in (5, 81, True, "20"):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                configuracion_thread("abc", recursion_limit=invalid)

    def test_identifica_estado_ok(self):
        events = analizar_ejecuciones([{"tool": "calcular_consumo", "contenido": '{"estado":"ok"}'}])
        self.assertEqual(events[0]["estado"], "ok")

    def test_no_finge_estado_ante_json_invalido(self):
        events = analizar_ejecuciones([{"tool": "simular_ahorro", "contenido": "invalido"}])
        self.assertEqual(events[0]["estado"], "desconocido")

    def test_ejecuciones_solo_del_turno_actual(self):
        agente = AgenteFalso()
        t1 = ejecutar_turno(agente, consulta="primera", thread_id="casa1")
        t2 = ejecutar_turno(agente, consulta="segunda", thread_id="casa1")
        self.assertEqual(len(t1["ejecuciones"]), 1)
        self.assertEqual(len(t2["ejecuciones"]), 1)
        self.assertEqual(tools_ejecutadas(t2), {"calcular_consumo"})
        self.assertEqual(set(agente.thread_ids), {"casa1"})

    def test_rechaza_consulta_vacia(self):
        with self.assertRaises(ValueError):
            ejecutar_turno(AgenteFalso(), consulta="   ", thread_id="t1")

    def test_detecta_mensajes_reducidos(self):
        agente = AgenteFalso()
        agente.messages = [HumanMessage("uno"), AIMessage("dos")]
        def broken_invoke(*args, **kwargs):
            return {"messages": [AIMessage("solo")]} 
        agente.invoke = broken_invoke
        with self.assertRaises(RuntimeError):
            ejecutar_turno(agente, consulta="hola", thread_id="casa1")


if __name__ == "__main__":
    unittest.main()
