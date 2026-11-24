"""Etapa 06.1: pruebas deterministas sin Ollama ni dependencia de LangChain."""
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

from energia_ai.agent.telemetry import (
    RegistroRendimiento, crear_callback_rendimiento, ejecutar_turno_medido, resumen_permitido,
)
from energia_ai.agent.persistent_runtime import PROMPT_INVENTARIO
from energia_ai.agent.inventory_tools import crear_tools_inventario
from energia_ai.services.home_inventory import InventarioHogar
from scripts.benchmark_agent_06_1 import guardar_resumen


class Clock:
    def __init__(self):
        self.value = 100.0
    def __call__(self):
        return self.value
    def avanzar(self, segundos):
        self.value += segundos


class Msg:
    def __init__(self, type, content, name=""):
        self.type = type
        self.content = content
        self.name = name


class AgentFake:
    def stream(self, _payload, *, config, stream_mode, version):
        assert stream_mode == ["messages", "updates"] and version == "v1"
        handler = config["callbacks"][0]
        handler.on_chat_model_start({}, [], run_id="modelo1")
        handler.on_tool_start({"name": "calcular_consumo"},
                              '{"periodo_dias":20, "consulta":"privada"}', run_id="t1")
        handler.on_tool_end(Msg("tool", '{"estado":"ok", "consumo_total_kwh":"10.0000"}'),
                            run_id="t1")
        handler.on_llm_end(None, run_id="modelo1")
        yield ("messages", (Msg("AIMessageChunk", "Consumo: 10 kWh"), {}))
        yield ("updates", {"tools": {"messages": [Msg("tool", '{"estado":"ok"}', "calcular_consumo")]}})


class TestTelemetry(unittest.TestCase):
    def test_filtro_argumentos_no_revela_texto(self):
        res = resumen_permitido({"consulta": "contraseña", "hogar_id": "privado",
                                "id": "tv_1", "potencia_watts": "100", "periodo_dias": 20})
        self.assertEqual(res, {"potencia_watts": "100", "periodo_dias": 20})

    def test_no_revela_texto_en_campos_que_deberian_ser_numericos(self):
        self.assertEqual(resumen_permitido({"potencia_watts":"clave_privada", "estado":"clave_privada"}), {})

    def test_filtro_recursivo_no_expone_datos_personales(self):
        self.assertEqual(resumen_permitido({"estado": "ok", "equipos": [{"nombre": "privado"}],
                                            "cantidad_equipos": 2}),
                         {"estado": "ok", "cantidad_equipos": 2})

    def test_json_objeto_y_objeto_toolmessage(self):
        self.assertEqual(resumen_permitido(Msg("tool", '{"estado":"ok", "ahorro_kwh":"30.00"}')),
                         {"estado": "ok", "ahorro_kwh": "30.00"})

    def test_texto_invalido_no_se_guarda(self):
        self.assertEqual(resumen_permitido("token=privado"), {})

    def test_tiempo_y_primer_texto(self):
        clock = Clock()
        reg = RegistroRendimiento(reloj=clock)
        clock.avanzar(4)
        reg.marcar_primer_texto()
        clock.avanzar(2)
        reg.finalizar()
        self.assertEqual(reg.resumen()["duracion_total_s"], 6)
        self.assertEqual(reg.resumen()["tiempo_primera_salida_s"], 4)

    def test_tool_inicia_y_termina_y_modelo(self):
        clock = Clock()
        reg = RegistroRendimiento(reloj=clock)
        reg.iniciar_modelo("m1")
        clock.avanzar(2)
        reg.iniciar_tool("t1", "registrar_electrodomestico", {"cantidad": 1, "nombre": "secreto"})
        clock.avanzar(1.5)
        reg.terminar_tool("t1", {"estado": "ok", "cantidad_equipos": 2})
        reg.terminar_modelo("m1")
        reg.finalizar()
        r = reg.resumen()
        self.assertEqual(r["llamadas_modelo"], 1)
        self.assertEqual(r["herramientas"][0]["duracion_s"], 1.5)
        self.assertNotIn("nombre", r["herramientas"][0]["argumentos"])
        self.assertEqual(r["duracion_total_s"], 3.5)

    def test_tool_update_sin_callback_registra_ejecucion_no_temporizada(self):
        registro = RegistroRendimiento()
        registro.observar_tool_stream("buscar_consejos", "ok")
        dato = registro.resumen()["herramientas"][0]
        self.assertIsNone(dato["duracion_s"])
        self.assertEqual(dato["origen"], "stream_updates_sin_tiempo")

    def test_llamadas_paralelas_sin_mezcla(self):
        clock = Clock()
        reg = RegistroRendimiento(reloj=clock)
        reg.iniciar_tool("t1", "calcular_consumo")
        clock.avanzar(1)
        reg.iniciar_tool("t2", "consultar_tarifa")
        clock.avanzar(2)
        reg.terminar_tool("t2", {"estado": "ok"})
        clock.avanzar(1)
        reg.terminar_tool("t1", {"estado": "ok"})
        self.assertEqual([x["nombre"] for x in reg.resumen()["herramientas"]],
                         ["consultar_tarifa", "calcular_consumo"])

    def test_error_no_guarda_mensaje_privado(self):
        reg = RegistroRendimiento()
        reg.finalizar(ValueError("DNI privado"))
        self.assertEqual(reg.resumen()["tipo_error"], "ValueError")
        self.assertNotIn("DNI", json.dumps(reg.resumen()))

    def test_callback_via_modulo_simulado(self):
        module = types.ModuleType("langchain_core.callbacks")
        module.BaseCallbackHandler = type("BaseCallbackHandler", (), {})
        with patch.dict(sys.modules, {"langchain_core": types.ModuleType("langchain_core"),
                                      "langchain_core.callbacks": module}):
            reg = RegistroRendimiento()
            handler = crear_callback_rendimiento(reg)
            handler.on_tool_start({"name": "consultar_tarifa"},
                                  '{"regimen":"SIN_SEF"}', run_id="a")
            handler.on_tool_end(Msg("tool", '{"estado":"ok"}'), run_id="a")
            self.assertEqual(reg.resumen()["herramientas"][0]["nombre"], "consultar_tarifa")

    def test_ejecucion_stream_con_callback(self):
        module = types.ModuleType("langchain_core.callbacks")
        module.BaseCallbackHandler = type("BaseCallbackHandler", (), {})
        eventos = []
        with patch.dict(sys.modules, {"langchain_core": types.ModuleType("langchain_core"),
                                      "langchain_core.callbacks": module}):
            metrica = ejecutar_turno_medido(AgentFake(), consulta="Calcular", thread_id="casa_demo",
                                           notificar=eventos.append)
        self.assertEqual(metrica["llamadas_modelo"], 1)
        self.assertEqual(metrica["herramientas"][0]["resultado"]["consumo_total_kwh"], "10.0000")
        self.assertEqual(metrica["estado"], "ok")
        self.assertIsNotNone(metrica["tiempo_primera_salida_s"])
        self.assertIn("tool_fin", [e["tipo"] for e in eventos])
        self.assertNotIn("privada", json.dumps(metrica))

    def test_guardar_json_sin_credenciales(self):
        with tempfile.TemporaryDirectory() as folder:
            ruta = Path(folder) / "processed" / "medicion.json"
            guardar_resumen(ruta, {"duracion_total_s": 17.2})
            self.assertEqual(json.loads(ruta.read_text(encoding="utf-8"))["duracion_total_s"], 17.2)

    def test_prompt_deriva_registros_a_interfaz(self):
        self.assertIn('Mis electrodomésticos', PROMPT_INVENTARIO)
        self.assertIn('No disponés de herramientas', PROMPT_INVENTARIO)

    def test_lectura_refleja_cambios_de_servicio(self):
        with tempfile.TemporaryDirectory() as folder:
            repo = InventarioHogar(Path(folder) / 'inv.sqlite3')
            repo.asegurar_hogar('casa_demo')
            module = types.ModuleType('langchain_core.tools')
            module.tool = lambda fn: fn
            with patch.dict(sys.modules, {'langchain_core': types.ModuleType('langchain_core'),
                                         'langchain_core.tools': module}):
                (consultar,) = crear_tools_inventario(repo, 'casa_demo')
            self.assertEqual(consultar()['cantidad_equipos'], 0)
            repo.registrar_equipo('casa_demo', id='tv_1', nombre='Televisor',
                                 potencia_watts='100', horas_efectivas_por_dia='5', dias_de_uso=20)
            self.assertEqual(consultar()['cantidad_equipos'], 1)

    def test_agente_no_puede_registrar(self):
        with tempfile.TemporaryDirectory() as folder:
            repo = InventarioHogar(Path(folder) / 'inv.sqlite3')
            repo.asegurar_hogar('casa_demo')
            module = types.ModuleType('langchain_core.tools')
            module.tool = lambda fn: fn
            with patch.dict(sys.modules, {'langchain_core': types.ModuleType('langchain_core'),
                                         'langchain_core.tools': module}):
                tools = crear_tools_inventario(repo, 'casa_demo')
            self.assertEqual(len(tools), 1)
            self.assertNotIn('registrar_electrodomestico', [t.__name__ for t in tools])


if __name__ == "__main__":
    unittest.main()
