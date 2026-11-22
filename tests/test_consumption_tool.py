"""Pruebas del adaptador LangChain; requieren instalar requirements-tools.txt."""

import importlib.util
import unittest

if importlib.util.find_spec("langchain_core"):
    from energia_ai.agent.consumption_tool import calcular_consumo


@unittest.skipUnless(importlib.util.find_spec("langchain_core"),
                     "Falta langchain-core: instalar requirements-tools.txt")
class TestConsumoTool(unittest.TestCase):
    def test_tool_name_and_invoke(self):
        self.assertEqual(calcular_consumo.name, "calcular_consumo")
        response = calcular_consumo.invoke({"periodo_dias": 30, "equipos": [
            {"id": "tv_1", "nombre": "TV", "potencia_watts": 100,
             "horas_efectivas_por_dia": 5, "dias_de_uso": 20, "cantidad": 1}
        ]})
        self.assertEqual(response["estado"], "ok")
        self.assertEqual(response["consumo_total_kwh"], "10.0000")

    def test_rejects_duplicate_id(self):
        obj = {"id": "tv_1", "nombre": "TV", "potencia_watts": 100,
               "horas_efectivas_por_dia": 5, "dias_de_uso": 20}
        response = calcular_consumo.invoke({"periodo_dias": 30, "equipos": [obj, obj]})
        self.assertEqual(response["estado"], "error")
        self.assertEqual(response["codigo"], "DATOS_INVALIDOS")


if __name__ == "__main__":
    unittest.main()
