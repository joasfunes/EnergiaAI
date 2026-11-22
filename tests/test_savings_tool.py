"""Regresión de la tool LangChain de ahorro."""

import json
import unittest
from datetime import date

try:
    from energia_ai.agent.savings_tool import simular_ahorro
    from energia_ai.services.tariffs import consultar_tarifa_catalogo
    from langchain_core.tools import BaseTool
    DISPONIBLE = True
except ImportError:
    DISPONIBLE = False


@unittest.skipUnless(DISPONIBLE, "Se requiere langchain-core instalado")
class TestToolAhorro(unittest.TestCase):
    def setUp(self):
        self.actual = {
            "id": "tv_1", "nombre": "Televisor", "potencia_watts": "100",
            "horas_efectivas_por_dia": "5", "dias_de_uso": 20, "cantidad": 1,
        }
        self.propuesto = {**self.actual, "horas_efectivas_por_dia": "3"}

    def args(self, **overrides):
        data = {"periodo_dias": 60, "equipos_actuales": [self.actual],
                "equipos_propuestos": [self.propuesto]}
        data.update(overrides)
        return data

    def test_es_tool_real(self):
        self.assertIsInstance(simular_ahorro, BaseTool)
        self.assertEqual(simular_ahorro.name, "simular_ahorro")

    def test_invoca_calculo_energetico(self):
        r = simular_ahorro.invoke(self.args())
        self.assertEqual(r["ahorro_kwh"], "4.0000")
        self.assertFalse(r["estimacion_monetaria_disponible"])

    def test_error_controlado_horarios_invalidos(self):
        malo = {**self.propuesto, "horas_efectivas_por_dia": "25"}
        r = simular_ahorro.invoke(self.args(equipos_propuestos=[malo]))
        self.assertEqual(r["estado"], "error")
        self.assertEqual(r["codigo"], "ESCENARIO_INVALIDO")

    def test_error_pydantic_no_rompe(self):
        out = simular_ahorro.invoke(self.args(periodo_dias="no-numero"))
        if isinstance(out, str):
            out = json.loads(out)
        self.assertEqual(out["estado"], "error")
        self.assertEqual(out["codigo"], "PARAMETROS_INVALIDOS")

    def test_rechaza_cambios_de_ids(self):
        nuevo = {**self.propuesto, "id": "otro_1"}
        r = simular_ahorro.invoke(self.args(equipos_propuestos=[nuevo]))
        self.assertEqual(r["estado"], "error")


if __name__ == "__main__":
    unittest.main()
