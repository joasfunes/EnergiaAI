"""Regresión del servicio de tarifas (sin dependencias de IA)."""

import unittest
from dataclasses import replace
from datetime import date, datetime

from energia_ai.data.tariff_catalog import CATALOGO_EDEMSA_221_2026 as C
from energia_ai.services.tariffs import consultar_tarifa_catalogo


class TestConsultaTarifas(unittest.TestCase):
    def query(self, **overrides):
        args = {
            "distribuidora": "EDEMSA",
            "fecha": date(2026, 11, 15),
            "consumo_kwh_bimestral": 350,
            "regimen": "SIN_SEF",
        }
        args.update(overrides)
        return consultar_tarifa_catalogo(**args)

    def test_r2_y_cargos_exactos_sin_sef(self):
        r = self.query()
        self.assertEqual(r["categoria"], "R2")
        self.assertEqual(r["cargos_principales"]["fijo_ars_por_bimestre"], "9299.861")
        self.assertEqual(r["cargos_principales"]["variable_ars_por_kwh"], "289.4315")
        self.assertIsNone(r["cargos_excedente"])

    def test_limites_bandas(self):
        for consumo, banda in [(0, "R1"), (299, "R1"), (300, "R2"), (599, "R2"), (600, "R3")]:
            with self.subTest(consumo=consumo):
                self.assertEqual(self.query(consumo_kwh_bimestral=consumo)["categoria"], banda)

    def test_con_sef_muestra_base_y_excedente_sin_aplicarlos(self):
        r = self.query(regimen="CON_SEF")
        self.assertEqual(r["cargos_principales"]["variable_ars_por_kwh"], "182.3271")
        self.assertEqual(r["cargos_excedente"]["variable_ars_por_kwh"], "289.4315")
        self.assertIsNotNone(r["nota_sef"])
        self.assertTrue(any("NO se" in x for x in r["advertencias"]))

    def test_r1_no_presume_excedente_cero(self):
        r = self.query(consumo_kwh_bimestral=150, regimen="CON_SEF")
        self.assertIsNone(r["cargos_excedente"])
        self.assertTrue(any("no se interpreta" in x for x in r["advertencias"]))

    def test_fuente_y_vigencia(self):
        r = self.query()
        self.assertEqual(r["fuente"]["resolucion"], C.resolucion)
        self.assertEqual(r["fuente"]["url"], C.fuente_url)
        self.assertEqual(r["fecha_consultada"], "2026-11-15")
        self.assertEqual(r["fuente"]["cobertura_desde"], "2026-11-01")

    def test_fuera_de_cobertura_no_inventa_tarifas(self):
        for fecha in (date(2026, 10, 31), date(2027, 2, 1)):
            with self.subTest(fecha=fecha), self.assertRaises(ValueError):
                self.query(fecha=fecha)

    def test_distribuidora_ajena_rechazada(self):
        with self.assertRaises(ValueError):
            self.query(distribuidora="EDENOR")

    def test_regimen_desconocido_rechazado(self):
        with self.assertRaises(ValueError):
            self.query(regimen="NO_SE")

    def test_consumo_invalido(self):
        for kwh in (-1, 350.5, True, "350"):
            with self.subTest(kwh=kwh), self.assertRaises(ValueError):
                self.query(consumo_kwh_bimestral=kwh)

    def test_fecha_invalida(self):
        with self.assertRaises(ValueError):
            self.query(fecha=datetime(2026, 11, 15))

    def test_estado_revision_influye_en_aptitud_sin_modificar_original(self):
        estado_original = C.estado_revision
        verificado = replace(C, estado_revision="CONTRASTADO_CON_PDF_LOCAL")
        r = self.query(catalogo=verificado)
        self.assertTrue(r["datos_contrastados_para_informe"])
        self.assertEqual(C.estado_revision, estado_original)

    def test_salida_json_compatible_y_sin_total_factura(self):
        import json
        r = self.query()
        self.assertIn('"categoria": "R2"', json.dumps(r))
        self.assertNotIn("factura_total", r)
        self.assertEqual(r["tipo_resultado"], "consulta_de_cargos_no_factura")


if __name__ == "__main__":
    unittest.main()
