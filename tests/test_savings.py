"""Regresión del cálculo de escenarios, sin LangChain ni LLM."""

from dataclasses import replace
from datetime import date
from decimal import Decimal
import unittest

from energia_ai.data.tariff_catalog import CATALOGO_EDEMSA_221_2026
from energia_ai.services.consumption import Electrodomestico
from energia_ai.services.savings import simular_ahorro_escenarios
from energia_ai.services.tariffs import consultar_tarifa_catalogo


class TestSimulador(unittest.TestCase):
    def setUp(self):
        self.catalogo = replace(CATALOGO_EDEMSA_221_2026,
                                estado_revision="CONTRASTADO_CON_PDF_LOCAL")
        self.tarifa = consultar_tarifa_catalogo(
            distribuidora="EDEMSA", fecha=date(2026, 11, 15),
            consumo_kwh_bimestral=350, regimen="SIN_SEF", catalogo=self.catalogo,
        )
        self.actual = Electrodomestico(
            id="aire_1", nombre="Aire acondicionado", potencia_watts="1500",
            horas_efectivas_por_dia="5", dias_de_uso=10,
        )
        self.propuesto = replace(self.actual, horas_efectivas_por_dia=Decimal("3"))

    def calcular(self, **overrides):
        argumentos = dict(
            periodo_dias=60, equipos_actuales=[self.actual],
            equipos_propuestos=[self.propuesto],
            consumo_hogar_bimestral_kwh=350, tarifa_consultada=self.tarifa,
            catalogo=self.catalogo,
        )
        argumentos.update(overrides)
        return simular_ahorro_escenarios(**argumentos)

    def test_ahorro_energetico(self):
        r = self.calcular()
        self.assertEqual(r["escenario_actual"]["consumo_total_kwh"], "75.0000")
        self.assertEqual(r["escenario_propuesto"]["consumo_total_kwh"], "45.0000")
        self.assertEqual(r["ahorro_kwh"], "30.0000")
        self.assertEqual(r["ahorro_porcentual_equipos"], "40.00")

    def test_componente_variable_misma_categoria(self):
        r = self.calcular()
        self.assertTrue(r["estimacion_monetaria_disponible"])
        self.assertEqual(r["ahorro_componente_variable_estimado_ars"], "8682.95")
        self.assertEqual((r["categoria_actual"], r["categoria_proyectada"]), ("R2", "R2"))
        self.assertEqual(r["consumo_hogar_bimestral_proyectado_kwh"], "320.0000")
        self.assertEqual(r["fuente_tarifa"]["resolucion"], "EPRE 221/2026")

    def test_sin_tarifa_solo_energia(self):
        r = self.calcular(tarifa_consultada=None)
        self.assertEqual(r["ahorro_kwh"], "30.0000")
        self.assertFalse(r["estimacion_monetaria_disponible"])
        self.assertIsNone(r["ahorro_componente_variable_estimado_ars"])

    def test_sin_facturacion_bimestral_solo_energia(self):
        r = self.calcular(consumo_hogar_bimestral_kwh=None)
        self.assertFalse(r["estimacion_monetaria_disponible"])

    def test_si_aumenta_el_consumo_ahorro_negativo(self):
        r = self.calcular(equipos_actuales=[self.propuesto], equipos_propuestos=[self.actual])
        self.assertEqual(r["ahorro_kwh"], "-30.0000")
        self.assertEqual(r["ahorro_componente_variable_estimado_ars"], "-8682.95")

    def test_cambio_de_categoria_impide_estimar_monto(self):
        propuesta = replace(self.actual, horas_efectivas_por_dia=Decimal("1"))
        r = self.calcular(equipos_propuestos=[propuesta])
        self.assertEqual(r["ahorro_kwh"], "60.0000")
        self.assertEqual(r["categoria_proyectada"], "R1")
        self.assertIsNone(r["ahorro_componente_variable_estimado_ars"])
        self.assertIn("cambia", r["motivo_sin_estimacion_monetaria"])

    def test_sef_no_monetiza_sin_modelar_cupos(self):
        sef = consultar_tarifa_catalogo(
            distribuidora="EDEMSA", fecha=date(2026, 11, 15),
            consumo_kwh_bimestral=350, regimen="CON_SEF", catalogo=self.catalogo,
        )
        r = self.calcular(tarifa_consultada=sef)
        self.assertFalse(r["estimacion_monetaria_disponible"])

    def test_tarifa_modificada_no_monetiza(self):
        tarifa = {**self.tarifa, "cargos_principales": {
            **self.tarifa["cargos_principales"], "variable_ars_por_kwh": "1.0"
        }}
        r = self.calcular(tarifa_consultada=tarifa)
        self.assertFalse(r["estimacion_monetaria_disponible"])
        self.assertIn("no coincide", r["motivo_sin_estimacion_monetaria"])

    def test_catalogo_pendiente_no_monetiza(self):
        pendiente = replace(
            CATALOGO_EDEMSA_221_2026,
            estado_revision="PENDIENTE_CONTRASTE_CON_PDF_LOCAL",
        )
        tarifa = consultar_tarifa_catalogo(
            distribuidora="EDEMSA", fecha=date(2026, 11, 15),
            consumo_kwh_bimestral=350, regimen="SIN_SEF", catalogo=pendiente,
        )
        r = self.calcular(catalogo=pendiente, tarifa_consultada=tarifa)
        self.assertFalse(r["estimacion_monetaria_disponible"])
        self.assertIn("contrastado", r["motivo_sin_estimacion_monetaria"])

    def test_periodo_no_bimestral_no_monetiza(self):
        r = self.calcular(periodo_dias=30)
        self.assertEqual(r["ahorro_kwh"], "30.0000")
        self.assertFalse(r["estimacion_monetaria_disponible"])

    def test_equipo_nuevo_no_permitido(self):
        with self.assertRaisesRegex(ValueError, "mismos IDs"):
            self.calcular(equipos_propuestos=[replace(self.propuesto, id="estufa_1")])

    def test_no_modificar_potencia_en_esta_etapa(self):
        with self.assertRaisesRegex(ValueError, "solo se pueden modificar"):
            self.calcular(equipos_propuestos=[replace(self.propuesto, potencia_watts=Decimal("900"))])

    def test_rechaza_consumo_hogar_menor_que_equipos(self):
        r = self.calcular(consumo_hogar_bimestral_kwh=30)
        self.assertFalse(r["estimacion_monetaria_disponible"])

    def test_rechaza_consumo_hogar_no_entero(self):
        for valor in (True, -1, 350.5):
            with self.subTest(valor=valor), self.assertRaises(ValueError):
                self.calcular(consumo_hogar_bimestral_kwh=valor)

    def test_sin_ahorro_cero(self):
        r = self.calcular(equipos_propuestos=[self.actual])
        self.assertEqual(r["ahorro_kwh"], "0.0000")
        self.assertEqual(r["ahorro_componente_variable_estimado_ars"], "0.00")

    def test_rechaza_cerca_de_umbral_ambiguo(self):
        # Ahorro 50.5 kWh => 350 - 50.5 = 299.5, umbral R1/R2 ambiguo.
        propuesta = replace(self.actual, horas_efectivas_por_dia=Decimal("1.633333333333333333333"))
        r = self.calcular(equipos_propuestos=[propuesta])
        self.assertFalse(r["estimacion_monetaria_disponible"])
        self.assertIn("límite", r["motivo_sin_estimacion_monetaria"])

    def test_escenario_horas_cero_base_cero(self):
        nulo = replace(self.actual, horas_efectivas_por_dia=Decimal("0"))
        r = self.calcular(equipos_actuales=[nulo], equipos_propuestos=[nulo])
        self.assertIsNone(r["ahorro_porcentual_equipos"])


if __name__ == "__main__":
    unittest.main()
