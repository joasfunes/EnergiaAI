"""Pruebas de integridad y regresión del catálogo EPRE 221/2026.

No sustituyen el contraste humano contra el anexo oficial.
"""

import unittest
from dataclasses import FrozenInstanceError
from datetime import date
from decimal import Decimal

from energia_ai.data.tariff_catalog import (
    CATALOGO_EDEMSA_221_2026 as C,
    BandaResidencial,
    CatalogoTarifario,
    Cargos,
)


class TestCatalogoTarifario(unittest.TestCase):
    FECHA = date(2026, 11, 15)

    def test_limites_de_categorias(self):
        esperados = {0: "R1", 299: "R1", 300: "R2", 599: "R2",
                     600: "R3", 1000: "R3"}
        for consumo, esperado in esperados.items():
            with self.subTest(consumo=consumo):
                self.assertEqual(C.obtener_banda(consumo, self.FECHA).codigo, esperado)

    def test_importes_sin_sef_contrastables(self):
        # Valores transcritos del Anexo I; comprobar además visualmente PDF.
        esperado = {
            "R1": (Decimal("8526.621"), Decimal("297.8234")),
            "R2": (Decimal("9299.861"), Decimal("289.4315")),
            "R3": (Decimal("54659.736"), Decimal("259.3782")),
        }
        for banda in C.bandas:
            self.assertEqual(
                (banda.sin_sef.fijo_por_bimestre_ars,
                 banda.sin_sef.variable_por_kwh_ars),
                esperado[banda.codigo],
            )

    def test_importes_con_sef_y_excedente(self):
        self.assertEqual(C.bandas[0].con_sef_o_base.variable_por_kwh_ars,
                         Decimal("182.8933"))
        self.assertIsNone(C.bandas[0].con_sef_excedente)
        self.assertEqual(C.bandas[1].con_sef_o_base.fijo_por_bimestre_ars,
                         Decimal("7640.151"))
        self.assertEqual(C.bandas[1].con_sef_excedente.variable_por_kwh_ars,
                         Decimal("289.4315"))
        self.assertEqual(C.bandas[2].con_sef_o_base.variable_por_kwh_ars,
                         Decimal("165.1047"))

    def test_rechaza_fecha_fuera_de_cobertura(self):
        for fecha in (date(2026, 10, 31), date(2027, 2, 1)):
            with self.subTest(fecha=fecha), self.assertRaises(ValueError):
                C.obtener_banda(250, fecha)

    def test_rechaza_consumo_invalido(self):
        for consumo in (-1, 299.5, True, "300"):
            with self.subTest(consumo=consumo), self.assertRaises((ValueError, TypeError)):
                C.obtener_banda(consumo, self.FECHA)

    def test_importes_no_negativos(self):
        with self.assertRaises(ValueError):
            Cargos(Decimal("-1"), Decimal("150"))
        with self.assertRaises(ValueError):
            Cargos(Decimal("NaN"), Decimal("150"))

    def test_datos_inmutables(self):
        with self.assertRaises(FrozenInstanceError):
            C.bandas[0].codigo = "OTRA"

    def test_codigo_fuente_y_unidades(self):
        self.assertEqual(C.distribuidora, "EDEMSA")
        self.assertEqual(C.facturacion_minima_kwh_bimestral, 45)
        self.assertIn("221/2026", C.resolucion)
        self.assertTrue(C.fuente_url.startswith("https://epremendoza.gob.ar/"))
        self.assertEqual(len(C.bandas), 3)

    def test_no_permite_huecos(self):
        r1, r2, r3 = C.bandas
        rota = BandaResidencial("R2", 301, 599, r2.sin_sef,
                               r2.con_sef_o_base, r2.con_sef_excedente)
        with self.assertRaises(ValueError):
            CatalogoTarifario(
                distribuidora=C.distribuidora, resolucion=C.resolucion,
                anexo=C.anexo, fuente_url=C.fuente_url,
                cobertura_desde=C.cobertura_desde,
                cobertura_hasta=C.cobertura_hasta,
                bandas=(r1, rota, r3),
                estado_revision=C.estado_revision,
                facturacion_minima_kwh_bimestral=45,
                nota_sef=C.nota_sef,
            )


if __name__ == "__main__":
    unittest.main()
