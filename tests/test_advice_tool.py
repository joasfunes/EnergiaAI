"""Pruebas del adaptador LangChain; no realizan llamadas a Ollama."""
import importlib.util
import unittest
from unittest.mock import patch

if importlib.util.find_spec("langchain_core"):
    from energia_ai.agent.advice_tool import buscar_consejos

from energia_ai.rag.corpus import SOURCES


class FakeSearcher:
    def __init__(self, items=None):
        self.items = items or []
        self.calls = []

    def search(self, question, *, k=3):
        self.calls.append((question, k))
        return self.items[:k]


def item():
    source = SOURCES[1]
    return {
        "text": "Revisar el uso de calefacción.",
        "source_id": source.id,
        "source_url": source.official_url,
        "page": None,
        "distance": 0.7,
    }


@unittest.skipUnless(importlib.util.find_spec("langchain_core"), "Instalar requirements-tools.txt")
class TestBuscarConsejosTool(unittest.TestCase):
    def test_nombre_y_schema(self):
        self.assertEqual(buscar_consejos.name, "buscar_consejos")
        self.assertIn("consulta", buscar_consejos.args)
        self.assertIn("max_resultados", buscar_consejos.args)

    def test_invoke_falso_buscador(self):
        fake = FakeSearcher([item()])
        with patch("energia_ai.agent.advice_tool._get_searcher", return_value=fake):
            result = buscar_consejos.invoke({"consulta": "calefacción", "max_resultados": 3})
        self.assertEqual(result["estado"], "ok")
        self.assertEqual(result["cantidad_resultados"], 1)
        self.assertEqual(fake.calls, [("calefacción", 3)])

    def test_invoke_sin_resultados(self):
        with patch("energia_ai.agent.advice_tool._get_searcher", return_value=FakeSearcher()):
            result = buscar_consejos.invoke({"consulta": "consulta"})
        self.assertEqual(result["estado"], "sin_resultados")

    def test_error_inicializacion_controlado(self):
        with patch("energia_ai.agent.advice_tool._get_searcher", side_effect=FileNotFoundError("ruta privada")):
            result = buscar_consejos.invoke({"consulta": "verano"})
        self.assertEqual(result["codigo"], "INDICE_NO_DISPONIBLE")
        self.assertNotIn("ruta privada", str(result))


if __name__ == "__main__":
    unittest.main()
