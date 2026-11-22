"""Pruebas sin LLM ni dependencias de LangChain."""

from dataclasses import FrozenInstanceError
from decimal import Decimal
import unittest

from energia_ai.services.consumption import Electrodomestico, calcular_consumo_equipos


def equipo(**overrides):
    base = {
        "id": "tv_1", "nombre": "Televisor", "potencia_watts": Decimal("100"),
        "horas_efectivas_por_dia": Decimal("5"), "dias_de_uso": 20,
    }
    base.update(overrides)
    return Electrodomestico(**base)


class TestConsumo(unittest.TestCase):
    def test_calculo_basico(self):
        result = calcular_consumo_equipos(periodo_dias=30, equipos=[equipo()])
        self.assertEqual(result["consumo_total_kwh"], "10.0000")
        self.assertEqual(result["equipos"][0]["consumo_kwh"], "10.0000")

    def test_multiples_equipos(self):
        segundo = equipo(id="aire_1", nombre="Aire", potencia_watts="1500",
                         horas_efectivas_por_dia="4", dias_de_uso=20)
        result = calcular_consumo_equipos(periodo_dias=30, equipos=[equipo(), segundo])
        self.assertEqual(result["consumo_total_kwh"], "130.0000")

    def test_cantidad(self):
        result = calcular_consumo_equipos(periodo_dias=30, equipos=[equipo(cantidad=3)])
        self.assertEqual(result["consumo_total_kwh"], "30.0000")

    def test_decimales_exacto(self):
        obj = equipo(potencia_watts="100.1", horas_efectivas_por_dia="0.3", dias_de_uso=1)
        res = calcular_consumo_equipos(periodo_dias=1, equipos=[obj])
        self.assertEqual(res["consumo_total_kwh"], "0.0300")

    def test_redondeo_solo_salida(self):
        e1 = equipo(potencia_watts="1", horas_efectivas_por_dia="0.01", dias_de_uso=1)
        e2 = equipo(id="x2", potencia_watts="1", horas_efectivas_por_dia="0.01", dias_de_uso=1)
        result = calcular_consumo_equipos(periodo_dias=1, equipos=[e1, e2])
        self.assertEqual(result["consumo_total_kwh"], "0.0000")

    def test_cero_horas(self):
        result = calcular_consumo_equipos(periodo_dias=30, equipos=[equipo(horas_efectivas_por_dia="0")])
        self.assertEqual(result["consumo_total_kwh"], "0.0000")

    def test_dias_fuera_periodo(self):
        with self.assertRaisesRegex(ValueError, "supera periodo"):
            calcular_consumo_equipos(periodo_dias=10, equipos=[equipo()])

    def test_rechaza_id_duplicado(self):
        with self.assertRaisesRegex(ValueError, "duplicado"):
            calcular_consumo_equipos(periodo_dias=30, equipos=[equipo(), equipo()])

    def test_rechaza_lista_vacia(self):
        with self.assertRaises(ValueError):
            calcular_consumo_equipos(periodo_dias=30, equipos=[])

    def test_rechaza_cantidad_fraccionaria(self):
        with self.assertRaises(ValueError):
            equipo(cantidad=1.5)

    def test_rechaza_negativos(self):
        for key, value in (("potencia_watts", "-1"),
                           ("horas_efectivas_por_dia", "-2"), ("dias_de_uso", -1)):
            with self.subTest(key=key), self.assertRaises(ValueError):
                equipo(**{key: value})

    def test_rechaza_horas_25(self):
        with self.assertRaises(ValueError):
            equipo(horas_efectivas_por_dia="25")

    def test_rechaza_nan_e_infinito(self):
        for value in ("NaN", "Infinity"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                equipo(potencia_watts=value)

    def test_no_bool(self):
        with self.assertRaises(ValueError):
            equipo(potencia_watts=True)
        with self.assertRaises(ValueError):
            calcular_consumo_equipos(periodo_dias=True, equipos=[equipo()])

    def test_id_valido(self):
        with self.assertRaises(ValueError):
            equipo(id="tv 1")

    def test_solo_equipo_validado(self):
        with self.assertRaises(ValueError):
            calcular_consumo_equipos(periodo_dias=30, equipos=[{"id": "tv_1"}])

    def test_inmutable(self):
        with self.assertRaises(FrozenInstanceError):
            equipo().cantidad = 99

    def test_no_costos(self):
        res = calcular_consumo_equipos(periodo_dias=30, equipos=[equipo()])
        self.assertNotIn("costo_ars", res)
        self.assertIn("No se calculó costo", " ".join(res["advertencias"]))


if __name__ == "__main__":
    unittest.main()
