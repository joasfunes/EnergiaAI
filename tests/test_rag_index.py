"""Pruebas sin conexión a Ollama ni descarga de embeddings: dobles en memoria."""
from __future__ import annotations
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from energia_ai.rag.corpus import SOURCES, safe_path
from energia_ai.rag.chunking import (
    extract_body, page_sections, split_text, load_chunks,
)
from energia_ai.rag.vector_store import create_index, RagSearcher, validate_vectors


class FakeEmbedding:
    """Vectores deterministas; solo se usan en pruebas, nunca en producción."""
    calls = 0
    def embed(self, texts):
        self.calls += 1
        return [[1.0, 0.0, float(len(s) % 37) / 100.0] for s in texts]


class FakeCollection:
    def __init__(self):
        self.items = {}
    def upsert(self, *, ids, documents, embeddings, metadatas):
        for id, doc, vec, meta in zip(ids, documents, embeddings, metadatas):
            self.items[id] = (doc, vec, meta)
    def count(self):
        return len(self.items)
    def query(self, *, query_embeddings, n_results, include):
        # La simulación comprueba el contrato y la trazabilidad; NO la relevancia semántica.
        results = list(self.items.items())[:n_results]
        return {
            "documents": [[v[0] for _, v in results]],
            "metadatas": [[v[2] for _, v in results]],
            "distances": [[0.01 + i * 0.1 for i in range(len(results))]],
        }


class FakeChroma:
    def __init__(self):
        self.collections = {}
    def get_or_create_collection(self, name, embedding_function=None):
        return self.collections.setdefault(name, FakeCollection())
    def get_collection(self, name, embedding_function=None):
        if name not in self.collections:
            raise ValueError("No existe")
        return self.collections[name]
    def delete_collection(self, name):
        if name not in self.collections:
            raise ValueError("No existe")
        del self.collections[name]


def fake_corpus(root: Path):
    entries = []
    for source in SOURCES:
        path = safe_path(root, source.prepared_relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        hash_orig = "a" * 64
        text = (
            "El consumo responsable de energía depende del clima local y del equipo. "
            "Elegir prácticas eficientes puede reducir el desperdicio eléctrico. "
        ) * 4
        if source.kind == "pdf":
            text = "## Pagina 1\n\n" + text + "\n\n## Pagina 2\n\n" + text
        md = (f"# {source.title}\n\nID: {source.id}\n\n"
              f"Fuente original: {source.official_url}\n\nSHA256 de origen: {hash_orig}"
              f"\n\n---\n\n{text}\n")
        path.write_text(md, encoding="utf-8")
        entries.append({
            "id": source.id,
            "url": source.official_url,
            "prepared_file": source.prepared_relative,
            "sha256_raw": hash_orig,
            "status": "READY_FOR_MANUAL_REVIEW",
        })
    report = safe_path(root, "data/processed/rag/corpus_report.json")
    report.write_text(json.dumps({"documents": entries}), encoding="utf-8")


class TestRagIndex(unittest.TestCase):
    def test_split_text_overlap(self):
        parts = split_text("palabra " * 160, size=150, overlap=30)
        self.assertGreater(len(parts), 5)
        self.assertTrue(all(len(x) <= 150 for x in parts))
        self.assertTrue(any(x[-20:] in parts[i+1] for i, x in enumerate(parts[:-1])))

    def test_invalid_chunk_settings(self):
        with self.assertRaises(ValueError):
            split_text("algo", size=50)
        with self.assertRaises(ValueError):
            split_text("algo", size=150, overlap=90)

    def test_pdf_page_markers(self):
        sections = page_sections("## Pagina 1\n\nAires\n## Pagina 2\n\nHeladeras", True)
        self.assertEqual(sections, [(1, "Aires"), (2, "Heladeras")])

    def test_pdf_missing_markers(self):
        with self.assertRaises(ValueError):
            page_sections("texto sin pagina", True)

    def test_header_provenance_required(self):
        with self.assertRaises(ValueError):
            extract_body("# Titulo\n\n---\n\nTexto", "SRC", "https://example.com", "a"*64)

    def test_load_chunks_with_page_attribution(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            fake_corpus(root)
            chunks = load_chunks(root, size=350, overlap=35)
            self.assertGreater(len(chunks), 3)
            self.assertEqual({c.metadata["source_id"] for c in chunks}, {s.id for s in SOURCES})
            self.assertEqual(len({c.id for c in chunks}), len(chunks))
            for c in chunks:
                self.assertTrue(c.metadata["url"].startswith("https://"))
                self.assertIn(c.metadata["page"], {0, 1, 2})

    def test_missing_source_rejected(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            fake_corpus(root)
            safe_path(root, SOURCES[0].prepared_relative).unlink()
            with self.assertRaises(FileNotFoundError):
                load_chunks(root)

    def test_corrupted_report_rejected(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            fake_corpus(root)
            path = safe_path(root, "data/processed/rag/corpus_report.json")
            contents = json.loads(path.read_text("utf-8"))
            contents["documents"][0]["sha256_raw"] = "b" * 64
            path.write_text(json.dumps(contents), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_chunks(root)

    def test_validate_embeddings_wrong_count(self):
        with self.assertRaises(ValueError):
            validate_vectors([[1., 2.]], 2)

    def test_validate_embeddings_nan(self):
        with self.assertRaises(ValueError):
            validate_vectors([[1., float("nan")]], 1)

    def test_index_reuse_and_search(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            fake_corpus(root)
            db = FakeChroma()
            emb = FakeEmbedding()
            first = create_index(root, embedder=emb, client=db)
            self.assertEqual(first["documents"], 3)
            self.assertGreater(first["chunks"], 3)
            n = emb.calls
            second = create_index(root, embedder=emb, client=db)
            self.assertEqual(second["status"], "REUTILIZADO")
            self.assertEqual(emb.calls, n)
            searcher = RagSearcher(root, embedder=emb, client=db)
            results = searcher.search("¿Cómo ahorrar en verano?", k=2)
            self.assertEqual(len(results), 2)
            self.assertTrue(all("source_url" in r and "citation" in r for r in results))
            with self.assertRaises(ValueError):
                searcher.search(" ")

    def test_rebuild_after_changes(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            fake_corpus(root)
            db = FakeChroma()
            emb = FakeEmbedding()
            create_index(root, embedder=emb, client=db)
            f = safe_path(root, SOURCES[1].prepared_relative)
            f.write_text(f.read_text("utf-8") + "\nUna recomendación adicional de ejemplo.", "utf-8")
            with self.assertRaisesRegex(ValueError, "rebuild"):
                create_index(root, embedder=emb, client=db)
            restored = create_index(root, embedder=emb, client=db, rebuild=True)
            self.assertEqual(restored["status"], "INDEXADO")

    def test_search_wrong_model(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            fake_corpus(root)
            db = FakeChroma()
            create_index(root, embedder=FakeEmbedding(), client=db)
            with self.assertRaises(ValueError):
                RagSearcher(root, embedder=FakeEmbedding(), client=db, model_name="otro-modelo")

if __name__ == "__main__":
    unittest.main()
