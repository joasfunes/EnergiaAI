"""Pruebas unitarias del índice de conversaciones, sin red ni Streamlit."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from energia_ai.ui.conversations import IndiceConversaciones


class TestIndiceConversaciones(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.ruta = Path(self.tmp.name) / 'conversaciones.sqlite3'
        self.indice = IndiceConversaciones(self.ruta)

    def test_crea_y_lista_por_hogar(self):
        thread = self.indice.crear('casa_demo')
        result = self.indice.listar('casa_demo')
        self.assertEqual([x['thread_id'] for x in result], [thread])
        self.assertTrue(thread.startswith('chat_'))

    def test_un_hogar_no_ve_los_threads_de_otro(self):
        t1 = self.indice.crear('casa1')
        self.indice.crear('casa2')
        self.assertEqual(len(self.indice.listar('casa1')), 1)
        with self.assertRaises(ValueError):
            self.indice.comprobar('casa2', t1)

    def test_persiste_al_reabrir(self):
        thread = self.indice.crear('casa1')
        self.assertEqual(IndiceConversaciones(self.ruta).listar('casa1')[0]['thread_id'], thread)

    def test_rechaza_hogar_o_titulo_invalidos(self):
        for invalid in ['../secret', 'casa con espacios', 'ñ']:
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                self.indice.crear(invalid)
        with self.assertRaises(ValueError):
            self.indice.crear('casa1', titulo=' ')

    def test_actualizar_no_crea_thread_ajeno(self):
        t = self.indice.crear('casa1')
        self.indice.actualizar('casa1', t)
        with self.assertRaises(ValueError):
            self.indice.actualizar('casa2', t)
        self.assertEqual(len(self.indice.listar('casa1')), 1)


if __name__ == '__main__':
    unittest.main()
