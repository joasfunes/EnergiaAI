"""Pruebas offline del research side. No descarga sitios reales ni usa un LLM."""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import fitz

from energia_ai.rag.corpus import (
    SOURCES, download_epre_html, extract_html_article,
    extract_pdf, prepare_corpus, safe_path, verify_source_url,
)


def sample_html() -> str:
    intro = "La eficiencia en los hogares permite reducir consumos sin perder confort. " * 3
    advice = "Es conveniente realizar un uso responsable de los equipos de climatización. " * 3
    return (
        "<html><body><nav>MENU NO DEBE ESTAR</nav>"
        "<article><div class='entry-content'>"
        f"<p>{intro}</p><h2>Recomendaciones</h2><ul><li>{advice}</li></ul>"
        "<script>NO PUBLICAR SCRIPT</script>"
        "</div></article><footer>PIE NO DEBE ESTAR</footer></body></html>"
    )


def sample_pdf() -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Buenas practicas de eficiencia energetica en el hogar")
    for i in range(1, 9):
        page.insert_text((72, 72 + 24 * i),
                         "Iluminacion eficiente y uso responsable de electrodomesticos.")
    data = doc.tobytes()
    doc.close()
    return data


class CorpusPreparationTest(unittest.TestCase):
    def test_01_three_distinct_official_documents(self):
        self.assertEqual(len(SOURCES), 3)
        self.assertEqual(len({item.id for item in SOURCES}), 3)
        self.assertEqual({item.kind for item in SOURCES}, {"pdf", "html"})
        for item in SOURCES:
            verify_source_url(item.official_url)

    def test_02_safe_path_rejects_traversal(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaises(ValueError):
                safe_path(root, "../fuera.txt")

    def test_03_untrusted_host_rejected(self):
        with self.assertRaises(ValueError):
            verify_source_url("https://ejemplo-malicioso.com/pagina")
        with self.assertRaises(ValueError):
            verify_source_url("http://epremendoza.gob.ar/inseguro")

    def test_04_html_extracts_article_not_navigation(self):
        result = extract_html_article(sample_html())
        self.assertIn("Recomendaciones", result)
        self.assertIn("climatización", result)
        self.assertNotIn("MENU NO DEBE ESTAR", result)
        self.assertNotIn("PIE NO DEBE ESTAR", result)
        self.assertNotIn("NO PUBLICAR SCRIPT", result)

    def test_05_html_without_article_is_not_accepted(self):
        with self.assertRaises(ValueError):
            extract_html_article("<html><body><p>Sin contenido principal</p></body></html>")

    def test_06_pdf_keeps_page_markers(self):
        text, pages = extract_pdf(sample_pdf())
        self.assertEqual(pages, 1)
        self.assertIn("## Pagina 1", text)
        self.assertIn("Iluminacion eficiente", text)

    def test_07_offline_preparation_generates_three_docs(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            for source in SOURCES:
                local = safe_path(root, source.raw_relative)
                local.parent.mkdir(parents=True, exist_ok=True)
                if source.kind == "pdf":
                    local.write_bytes(sample_pdf())
                else:
                    local.write_text(sample_html(), encoding="utf-8")
            report = prepare_corpus(root)
            self.assertEqual(len(report), 3)
            for item in report:
                self.assertEqual(item["status"], "READY_FOR_MANUAL_REVIEW")
                self.assertGreater(item["characters_extracted"], 250)
                self.assertEqual(len(item["sha256_raw"]), 64)
                text = safe_path(root, item["prepared_file"]).read_text("utf-8")
                self.assertIn(item["url"], text)
                self.assertIn("SHA256 de origen", text)
            path = root / "data/processed/rag/corpus_report.json"
            self.assertEqual(len(json.loads(path.read_text("utf-8"))["documents"]), 3)

    def test_08_html_download_can_use_mocked_http(self):
        class DummyResponse:
            url = "https://epremendoza.gob.ar/consejos-para-ahorrar-energia-en-el-invierno/"
            headers = {"Content-Type": "text/html; charset=UTF-8"}
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def raise_for_status(self): return None
            def iter_content(self, chunk_size=65536):
                yield sample_html().encode("utf-8")

        with TemporaryDirectory() as temp:
            with patch("energia_ai.rag.corpus.requests.get", return_value=DummyResponse()) as client:
                result = download_epre_html(Path(temp))
                self.assertEqual(len(result), 2)
                self.assertEqual(client.call_count, 2)
                for source in SOURCES:
                    if source.kind == "html":
                        self.assertTrue(safe_path(Path(temp), source.raw_relative).exists())
                result = download_epre_html(Path(temp))
                self.assertTrue(all("YA EXISTE" in value for value in result))
                self.assertEqual(client.call_count, 2)


if __name__ == "__main__":
    unittest.main()
