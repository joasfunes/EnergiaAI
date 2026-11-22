"""Etapa 03.4: pruebas reales de integración de tres tools LangChain.

No necesitan un LLM. Ejercitan .invoke() y el contrato entre las herramientas.
"""

from __future__ import annotations

from decimal import Decimal
import unittest

try:
    from scripts.demo_tools_integration import ejecutar_flujo
    from energia_ai.agent.consumption_tool import calcular_consumo
    from energia_ai.agent.tariff_tool import consultar_tarifa
    from energia_ai.agent.savings_tool import simular_ahorro
    from langchain_core.tools import BaseTool
    DISPONIBLE = True
except ImportError:
    DISPONIBLE = False


@unittest.skipUnless(DISPONIBLE, "Requiere langchain-core y paquete energia_ai instalados")
class TestIntegracionHerramientas(unittest.TestCase):
    def test_registro_de_las_tres_tools(self):
        for tool in (calcular_consumo, consultar_tarifa, simular_ahorro):
            self.assertIsInstance(tool, BaseTool)
        self.assertEqual(
            [t.name for t in (calcular_consumo, consultar_tarifa, simular_ahorro)],
            ["calcular_consumo", "consultar_tarifa", "simular_ahorro"],
        )

    def test_flujo_basico_reutiliza_los_resultados(self):
        r = ejecutar_flujo()
        self.assertEqual(r["estado"], "ok")
        self.assertEqual(r["consumo"]["consumo_total_kwh"], "75.0000")
        self.assertEqual(r["tarifa"]["categoria"], "R2")
        self.assertEqual(r["simulacion"]["ahorro_kwh"], "30.0000")
        self.assertEqual(r["simulacion"]["consumo_hogar_bimestral_proyectado_kwh"], "320.0000")
        self.assertEqual(r["verificaciones"]["linea_base_coincide"], True)
        self.assertEqual(r["verificaciones"]["ahorro_kwh_coincide"], True)

    def test_salida_tarifaria_pasa_intacta_a_simulacion(self):
        r = ejecutar_flujo()
        self.assertEqual(r["pasos"][2]["argumentos"]["tarifa_consultada"], r["tarifa"])
        self.assertIs(r["pasos"][2]["argumentos"]["tarifa_consultada"], r["tarifa"])

    def test_traza_muestra_orden_y_argumentos(self):
        r = ejecutar_flujo()
        self.assertEqual(
            [p["tool"] for p in r["pasos"]],
            ["calcular_consumo", "consultar_tarifa", "simular_ahorro"],
        )
        self.assertEqual(r["pasos"][1]["argumentos"]["consumo_kwh_bimestral"], 350)
        self.assertEqual(r["pasos"][0]["argumentos"]["periodo_dias"], 60)

    def test_monto_solo_si_catalogo_contrastado(self):
        r = ejecutar_flujo()
        verificado = r["tarifa"]["datos_contrastados_para_informe"]
        disponible = r["simulacion"]["estimacion_monetaria_disponible"]
        self.assertEqual(disponible, verificado)
        if verificado:
            self.assertEqual(r["simulacion"]["ahorro_componente_variable_estimado_ars"], "8682.95")
        else:
            self.assertIsNone(r["simulacion"]["ahorro_componente_variable_estimado_ars"])

    def test_sef_no_se_monetiza(self):
        r = ejecutar_flujo(regimen="CON_SEF")
        self.assertEqual(r["estado"], "ok")
        self.assertEqual(r["tarifa"]["regimen"], "CON_SEF")
        self.assertEqual(r["simulacion"]["ahorro_kwh"], "30.0000")
        self.assertFalse(r["simulacion"]["estimacion_monetaria_disponible"])

    def test_cambio_de_categoria_no_monetiza(self):
        r = ejecutar_flujo(horas_propuestas="1")
        self.assertEqual(r["simulacion"]["ahorro_kwh"], "60.0000")
        if r["tarifa"]["datos_contrastados_para_informe"]:
            self.assertEqual(r["simulacion"]["categoria_proyectada"], "R1")
        self.assertFalse(r["simulacion"]["estimacion_monetaria_disponible"])

    def test_tarifa_fuera_de_vigencia_conserva_energia(self):
        r = ejecutar_flujo(fecha="2025-11-15")
        self.assertEqual(r["estado"], "ok")
        self.assertEqual(r["tarifa"]["estado"], "error")
        self.assertEqual(r["simulacion"]["ahorro_kwh"], "30.0000")
        self.assertFalse(r["simulacion"]["estimacion_monetaria_disponible"])

    def test_sin_datos_de_factura_no_consulta_tarifa(self):
        r = ejecutar_flujo(consumo_hogar_bimestral_kwh=None)
        self.assertEqual([p["tool"] for p in r["pasos"]],
                         ["calcular_consumo", "simular_ahorro"])
        self.assertIsNone(r["tarifa"])
        self.assertEqual(r["simulacion"]["ahorro_kwh"], "30.0000")
        self.assertFalse(r["simulacion"]["estimacion_monetaria_disponible"])

    def test_aumento_de_consumo_se_informa_como_negativo(self):
        r = ejecutar_flujo(horas_propuestas="7")
        self.assertEqual(r["simulacion"]["ahorro_kwh"], "-30.0000")
        self.assertEqual(r["simulacion"]["consumo_hogar_bimestral_proyectado_kwh"], "380.0000")
        self.assertEqual(Decimal(r["consumo"]["consumo_total_kwh"]), Decimal("75"))


if __name__ == "__main__":
    unittest.main()
