"""Pruebas determinísticas de SQLite, sin LLM ni red."""
from __future__ import annotations
import tempfile
from pathlib import Path
import unittest

from energia_ai.services.home_inventory import InventarioHogar, validar_hogar_id


class TestInventarioHogar(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'data' / 'inventario.sqlite3'
        self.repo = InventarioHogar(self.path)
        self.repo.asegurar_hogar('casa1', periodo_dias=60)

    def agregar(self, repo=None, casa='casa1', **kwargs):
        args = dict(id='tv_1', nombre='Televisor', potencia_watts='100',
                    horas_efectivas_por_dia='5', dias_de_uso=20, cantidad=1)
        args.update(kwargs)
        return (repo or self.repo).registrar_equipo(casa, **args)

    def test_crea_archivo(self):
        self.assertTrue(self.path.is_file())

    def test_registro_y_lectura(self):
        self.assertEqual(self.agregar()['estado'], 'ok')
        res = self.repo.consultar('casa1')
        self.assertEqual(res['cantidad_equipos'], 1)
        self.assertEqual(res['equipos'][0]['potencia_watts'], '100')

    def test_persistencia_reinicio(self):
        self.agregar()
        reabierto = InventarioHogar(self.path)
        self.assertEqual(reabierto.consultar('casa1')['equipos'][0]['nombre'], 'Televisor')

    def test_suma_consumo(self):
        self.agregar()
        self.agregar(id='aire_1', nombre='Aire', potencia_watts='1500',
                    horas_efectivas_por_dia='4', dias_de_uso=20)
        self.assertEqual(self.repo.consumo_inventario('casa1')['consumo_total_kwh'], '130.0000')

    def test_no_duplicar_registros(self):
        self.agregar()
        with self.assertRaisesRegex(ValueError, 'existe'):
            self.agregar(nombre='Nombre alterado')
        self.assertEqual(self.repo.consultar('casa1')['equipos'][0]['nombre'], 'Televisor')

    def test_aislamiento_hogares(self):
        self.repo.asegurar_hogar('casa2', periodo_dias=60)
        self.agregar()
        self.assertEqual(self.repo.consultar('casa2')['cantidad_equipos'], 0)
        self.agregar(casa='casa2')
        self.assertEqual(self.repo.consultar('casa2')['cantidad_equipos'], 1)

    def test_rechaza_periodo_diferente(self):
        with self.assertRaisesRegex(ValueError, 'otro periodo'):
            self.repo.asegurar_hogar('casa1', periodo_dias=30)

    def test_rechaza_dias_fuera_de_periodo(self):
        with self.assertRaises(ValueError):
            self.agregar(dias_de_uso=61)

    def test_rechaza_potencia_invalida(self):
        for value in ('-1', 'NaN', '0', 'inf'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.agregar(potencia_watts=value)

    def test_rechaza_horas_invalidas(self):
        with self.assertRaises(ValueError):
            self.agregar(horas_efectivas_por_dia='25')

    def test_rechaza_hogar_invalido(self):
        for value in ('', '../otro', 'dos casas', 'ñ', 'a'*81):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validar_hogar_id(value)

    def test_hogar_desconocido(self):
        self.assertEqual(self.repo.consultar('no_existe')['codigo'], 'HOGAR_DESCONOCIDO')
        with self.assertRaises(ValueError):
            self.agregar(casa='no_existe')

    def test_ningun_equipo(self):
        res = self.repo.consumo_inventario('casa1')
        self.assertEqual(res['estado'], 'sin_equipos')
        self.assertIsNone(res['consumo_total_kwh'])

    def test_orden_estable(self):
        self.agregar(id='z')
        self.agregar(id='a')
        self.assertEqual([e['id'] for e in self.repo.consultar('casa1')['equipos']], ['a', 'z'])

    def test_no_bool_para_periodo(self):
        with self.assertRaises(ValueError):
            self.repo.asegurar_hogar('casa_nueva', periodo_dias=True)


if __name__ == '__main__':
    unittest.main()
