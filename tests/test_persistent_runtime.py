"""Tests de construcción y ciclo de vida con dependencias simuladas."""
from contextlib import contextmanager
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

from energia_ai.agent.persistent_runtime import (
    PROMPT_ANTERIOR, PROMPT_INVENTARIO, abrir_runtime_persistente, crear_agente_persistente
)


class TestRuntime(unittest.TestCase):
    def test_prompt_reemplaza_advertencia_antigua(self):
        from energia_ai.agent.full_agent import SYSTEM_PROMPT
        self.assertIn(PROMPT_ANTERIOR, SYSTEM_PROMPT)
        actual = SYSTEM_PROMPT.replace(PROMPT_ANTERIOR, '') + PROMPT_INVENTARIO
        self.assertNotIn('solo el historial del thread en RAM', actual)
        self.assertIn('Mis electrodomésticos', actual)
        self.assertNotIn('- registrar_electrodomestico:', actual)

    def test_inyeccion_agente_sin_llm(self):
        def module(name):
            m=types.ModuleType(name)
            m.__path__=[]
            return m
        fake = {'langchain': module('langchain'), 'langchain.agents': module('langchain.agents')}
        create = Mock(return_value='agente')
        fake['langchain.agents'].create_agent = create
        with patch.dict(sys.modules, fake), patch(
            'energia_ai.agent.persistent_runtime.herramientas_energia_ai', return_value=[1,2,3,4]
        ), patch('energia_ai.agent.persistent_runtime.crear_tools_inventario', return_value=(5,)):
            self.assertEqual(crear_agente_persistente(checkpointer='saver', repositorio=Mock(), hogar_id='casa1', modelo='modelo'), 'agente')
        kwargs=create.call_args.kwargs
        self.assertEqual(kwargs['tools'], [1,2,3,4,5])
        self.assertEqual(kwargs['checkpointer'], 'saver')
        self.assertEqual(kwargs['model'], 'modelo')

    def test_contexto_cierra_saver(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        cerrado=[]
        saver=Mock()
        @contextmanager
        def fake_from_conn_string(conn_str):
            self.assertTrue(conn_str.endswith('conversaciones.sqlite3'))
            yield saver
            cerrado.append(True)
        sqlite_mod=types.ModuleType('langgraph.checkpoint.sqlite')
        sqlite_mod.SqliteSaver=types.SimpleNamespace(from_conn_string=fake_from_conn_string)
        with patch.dict(sys.modules, {'langgraph': types.ModuleType('langgraph'), 'langgraph.checkpoint': types.ModuleType('langgraph.checkpoint'), 'langgraph.checkpoint.sqlite': sqlite_mod}), patch(
            'energia_ai.agent.persistent_runtime.crear_agente_persistente', return_value='AGENTE'):
            with abrir_runtime_persistente(hogar_id='casa', carpeta_estado=Path(temp.name)) as runtime:
                self.assertEqual(runtime.agente, 'AGENTE')
                self.assertEqual(runtime.repositorio.consultar('casa')['periodo_dias'],60)
                saver.setup.assert_called_once()
            self.assertEqual(cerrado, [True])

    def test_rechaza_hogar_invalido_antes_de_import(self):
        with self.assertRaises(ValueError):
            with abrir_runtime_persistente(hogar_id='../../secret'):
                pass


if __name__ == '__main__':
    unittest.main()
