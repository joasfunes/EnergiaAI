"""Gestión manual del inventario: validación y guardado atómico sin Ollama/Streamlit."""
from pathlib import Path
import tempfile
import unittest

from energia_ai.services.home_inventory import InventarioHogar
from energia_ai.ui.inventory_editor import normalizar_tabla


def fila(id='pava', nombre='Pava eléctrica', potencia_watts=1800, horas_efectivas_por_dia=0.15,
         dias_de_uso=50, cantidad=1):
    return locals()


class TestInventarioEditor(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name)/'inventario.sqlite3'
        self.repo = InventarioHogar(self.path)
        self.repo.asegurar_hogar('casa_demo', periodo_dias=60)

    def guardar(self, filas, hogar='casa_demo', version=None):
        base = self.repo.consultar(hogar)
        valores = normalizar_tabla(filas, periodo_dias=base['periodo_dias'])
        return self.repo.reemplazar_equipos(hogar, equipos=valores,
                                            version_esperada=version or base['version'])

    def test_01_alta_ocho_en_una_sola_operacion(self):
        # Caso completo del plan de pruebas: no depende del modelo Qwen.
        datos = [
            fila(id='micro_01', nombre='Microondas', potencia_watts=1200, horas_efectivas_por_dia=.2, dias_de_uso=45),
            fila(id='pava_01', potencia_watts=1800, horas_efectivas_por_dia=.15, dias_de_uso=50),
            fila(id='lavarropas_01', nombre='Lavarropas', potencia_watts=500, horas_efectivas_por_dia=1.25, dias_de_uso=12),
            fila(id='lavavajillas_01', nombre='Lavavajillas', potencia_watts=1500, horas_efectivas_por_dia=1.25, dias_de_uso=16),
            fila(id='horno_01', nombre='Horno eléctrico', potencia_watts=2000, horas_efectivas_por_dia=.75, dias_de_uso=16),
            fila(id='pc_01', nombre='Computadora', potencia_watts=180, horas_efectivas_por_dia=4, dias_de_uso=40),
            fila(id='aspiradora_01', nombre='Aspiradora', potencia_watts=900, horas_efectivas_por_dia=.5, dias_de_uso=8),
            fila(id='secador_01', nombre='Secador', potencia_watts=1400, horas_efectivas_por_dia=.15, dias_de_uso=30),
        ]
        self.guardar(datos)
        self.assertEqual(self.repo.consultar('casa_demo')['cantidad_equipos'], 8)
        self.assertEqual(self.repo.consumo_inventario('casa_demo')['consumo_total_kwh'], '124.5000')

    def test_02_datos_invalidos_no_guardan_filas_validas(self):
        with self.assertRaises(ValueError):
            self.guardar([fila(id='ok'), fila(id='mal', potencia_watts=-1)])
        self.assertEqual(self.repo.consultar('casa_demo')['cantidad_equipos'], 0)

    def test_03_editando_equipo_existente(self):
        self.guardar([fila()])
        self.guardar([fila(potencia_watts=2100, nombre='Pava nueva')])
        datos = self.repo.consultar('casa_demo')
        self.assertEqual(datos['cantidad_equipos'], 1)
        self.assertEqual(datos['equipos'][0]['potencia_watts'], '2100')

    def test_04_eliminar_fila(self):
        self.guardar([fila(), fila(id='horno')])
        self.guardar([fila(id='horno')])
        self.assertEqual(self.repo.consultar('casa_demo')['equipos'][0]['id'], 'horno')
        self.guardar([])
        self.assertEqual(self.repo.consultar('casa_demo')['cantidad_equipos'], 0)

    def test_05_detectar_version_obsoleta(self):
        original = self.repo.consultar('casa_demo')['version']
        self.guardar([fila()])
        with self.assertRaisesRegex(ValueError, 'otra sesión'):
            self.guardar([fila(id='horno')], version=original)
        self.assertEqual(self.repo.consultar('casa_demo')['equipos'][0]['id'], 'pava')

    def test_06_ids_duplicados(self):
        with self.assertRaisesRegex(ValueError, 'duplicado'):
            self.guardar([fila(), fila(nombre='Otra')])
        self.assertEqual(self.repo.consultar('casa_demo')['cantidad_equipos'], 0)

    def test_07_rechaza_mas_de_treinta(self):
        with self.assertRaisesRegex(ValueError, '30'):
            self.guardar([fila(id=f'e{i}') for i in range(31)])

    def test_08_aislamiento_hogares(self):
        self.repo.asegurar_hogar('otra_casa')
        self.guardar([fila()])
        self.guardar([fila(id='horno')], hogar='otra_casa')
        self.assertEqual(self.repo.consultar('casa_demo')['equipos'][0]['id'], 'pava')
        self.assertEqual(self.repo.consultar('otra_casa')['equipos'][0]['id'], 'horno')

    def test_09_persistencia_despues_de_reabrir(self):
        self.guardar([fila()])
        self.assertEqual(InventarioHogar(self.path).consultar('casa_demo')['cantidad_equipos'], 1)

    def test_10_normalizacion_decimal_y_enteros(self):
        [x] = normalizar_tabla([fila(potencia_watts='1800,5', horas_efectivas_por_dia='0,25',
                                    dias_de_uso=50.0, cantidad='1')], periodo_dias=60)
        self.assertEqual(x['potencia_watts'], '1800.5')
        self.assertEqual(x['horas_efectivas_por_dia'], '0.25')
        with self.assertRaises(ValueError):
            normalizar_tabla([fila(dias_de_uso=1.5)], periodo_dias=60)


if __name__ == '__main__':
    unittest.main()
