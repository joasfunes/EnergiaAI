"""Pruebas unitarias para la auditoría de fuentes documentales."""

import tempfile
import unittest
from pathlib import Path

from scripts.audit_sources import audit_one, safe_source_path


class AuditSourcesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.row = {
            "id": "TEST",
            "url": "https://epremendoza.gob.ar/documento.pdf",
            "ruta_local": "data/raw/prueba.pdf",
        }

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_reports_missing_file(self) -> None:
        self.assertEqual(audit_one(self.row, self.root)["estado"], "FALTA")

    def test_accepts_pdf_header_and_content_for_basic_audit(self) -> None:
        path = self.root / self.row["ruta_local"]
        path.parent.mkdir(parents=True)
        path.write_bytes(b"%PDF-1.7\n" + b"0" * 1500)
        result = audit_one(self.row, self.root)
        self.assertEqual(result["estado"], "OK_BASICO")
        self.assertEqual(len(result["sha256"]), 64)

    def test_rejects_invalid_document(self) -> None:
        path = self.root / self.row["ruta_local"]
        path.parent.mkdir(parents=True)
        path.write_bytes(b"no es un pdf")
        self.assertEqual(audit_one(self.row, self.root)["estado"], "ERROR")

    def test_rejects_unauthorized_domain(self) -> None:
        self.row["url"] = "https://sitio-no-oficial.example/fake.pdf"
        self.assertEqual(audit_one(self.row, self.root)["estado"], "ERROR")

    def test_prevents_traversal_outside_root(self) -> None:
        with self.assertRaises(ValueError):
            safe_source_path(self.root, "../../otro.pdf")


if __name__ == "__main__":
    unittest.main()
