"""Pruebas de la tool LangChain; requiere requirements-tools.txt."""

import importlib.util
import json
import unittest

if importlib.util.find_spec("langchain_core"):
    from energia_ai.agent.tariff_tool import consultar_tarifa


@unittest.skipUnless(importlib.util.find_spec("langchain_core"),
                     "Instalar langchain-core antes de validar el adaptador")
class TestTariffTool(unittest.TestCase):
    def args(self, **kwargs):
        a = {
            "distribuidora": "EDEMSA",
            "fecha": "2026-11-15",
            "consumo_kwh_bimestral": 350,
            "regimen": "SIN_SEF",
        }
        a.update(kwargs)
        return a

    def test_nombre_y_ejecucion_de_tool(self):
        self.assertEqual(consultar_tarifa.name, "consultar_tarifa")
        result = consultar_tarifa.invoke(self.args())
        self.assertEqual(result["estado"], "ok")
        self.assertEqual(result["categoria"], "R2")

    def test_regimen_sef(self):
        result = consultar_tarifa.invoke(self.args(regimen="CON_SEF"))
        self.assertEqual(result["estado"], "ok")
        self.assertIsNotNone(result["cargos_excedente"])

    def test_fecha_fuera_de_cobertura_error_controlado(self):
        result = consultar_tarifa.invoke(self.args(fecha="2025-11-15"))
        self.assertEqual(result["estado"], "error")
        self.assertEqual(result["codigo"], "TARIFA_NO_DISPONIBLE")

    def test_validacion_de_parametros_no_interrumpe_invocacion(self):
        for args in (
            self.args(regimen="DESCONOCIDO"),
            self.args(consumo_kwh_bimestral="350"),
            self.args(fecha="fecha-mala"),
        ):
            with self.subTest(args=args):
                result = consultar_tarifa.invoke(args)
                self.assertEqual(json.loads(result)["codigo"], "PARAMETROS_INVALIDOS")

    def test_faltan_datos_no_rompe_agente(self):
        result = consultar_tarifa.invoke({"distribuidora": "EDEMSA"})
        self.assertEqual(json.loads(result)["estado"], "error")


if __name__ == "__main__":
    unittest.main()
