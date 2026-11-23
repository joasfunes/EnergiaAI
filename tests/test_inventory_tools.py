"""Pruebas de aislamiento por hogar con un decorador fake, sin librerías de agente."""
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from energia_ai.agent.inventory_tools import crear_tools_inventario
from energia_ai.services.home_inventory import InventarioHogar


class TestInventoryTools(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.repo=InventarioHogar(Path(tmp.name)/'x.sqlite3')
        self.repo.asegurar_hogar('casa1')
        self.repo.asegurar_hogar('casa2')

    def tools(self, hogar):
        module = types.ModuleType('langchain_core.tools')
        module.tool = lambda f: f
        with patch.dict(sys.modules, {'langchain_core': types.ModuleType('langchain_core'), 'langchain_core.tools': module}):
            return crear_tools_inventario(self.repo, hogar)

    def test_add_y_consulta(self):
        add, read = self.tools('casa1')
        result = add(id='tv_1', nombre='Televisor', potencia_watts='100',
                     horas_efectivas_por_dia='5', dias_de_uso=20)
        self.assertEqual(result['estado'], 'ok')
        self.assertEqual(read()['cantidad_equipos'], 1)

    def test_aislamiento_por_inyeccion(self):
        add,_ = self.tools('casa1')
        _,read2 = self.tools('casa2')
        add(id='tv_1', nombre='Televisor', potencia_watts='100',
            horas_efectivas_por_dia='5', dias_de_uso=20)
        self.assertEqual(read2()['cantidad_equipos'],0)

    def test_errores_estructurados(self):
        add,_ = self.tools('casa1')
        res=add(id='tv_1', nombre='Televisor', potencia_watts='invalido',
                horas_efectivas_por_dia='5', dias_de_uso=20)
        self.assertEqual(res['estado'],'error')
        self.assertEqual(self.repo.consultar('casa1')['cantidad_equipos'],0)


if __name__ == '__main__':
    unittest.main()
