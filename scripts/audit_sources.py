"""Audita la presencia e integridad básica de archivos fuente del proyecto.

No verifica importes tarifarios ni certifica vigencia jurídica: esas
comprobaciones requieren revisar el PDF oficial y sus anexos.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
from pathlib import Path
from urllib.parse import urlparse

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = PROJECT_ROOT / "data" / "metadata" / "fuentes.csv"
REPORT = PROJECT_ROOT / "data" / "processed" / "auditoria_fuentes.csv"
ALLOWED_HOSTS = {"epremendoza.gob.ar", "www.epremendoza.gob.ar", "www.argentina.gob.ar"}
REQUIRED_COLUMNS = {"id", "tipo", "organismo", "titulo", "url", "ruta_local"}


def safe_source_path(root: Path, relative: str) -> Path:
    """Resuelve una ruta declarada en el inventario sin salir del proyecto."""
    target = (root / relative).resolve()
    if not target.is_relative_to(root.resolve()):
        raise ValueError("La ruta declarada sale de la carpeta del proyecto")
    return target


def audit_one(row: dict[str, str], root: Path) -> dict[str, str]:
    """Genera el diagnóstico reproducible de una única fuente."""
    result = {
        "id": row.get("id", ""),
        "archivo": row.get("ruta_local", ""),
        "estado": "",
        "tamano_bytes": "",
        "sha256": "",
        "detalle": "",
    }
    url = urlparse(row.get("url", ""))
    if url.scheme != "https" or url.netloc.lower() not in ALLOWED_HOSTS:
        result.update(estado="ERROR", detalle="URL fuera de la lista de fuentes oficiales permitidas")
        return result

    try:
        local = safe_source_path(root, row.get("ruta_local", ""))
        if local.suffix.lower() != ".pdf":
            raise ValueError("Se esperaba un archivo con extensión PDF")
    except ValueError as error:
        result.update(estado="ERROR", detalle=str(error))
        return result

    if not local.is_file():
        result.update(estado="FALTA", detalle="Descargar el PDF y guardarlo con el nombre indicado")
        return result

    digest = hashlib.sha256()
    size = 0
    with local.open("rb") as source:
        signature = source.read(5)
        source.seek(0)
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)

    result["tamano_bytes"] = str(size)
    result["sha256"] = digest.hexdigest()
    if signature != b"%PDF-" or size < 1024:
        result.update(estado="ERROR", detalle="Archivo vacío, demasiado pequeño o sin cabecera PDF")
    else:
        result.update(estado="OK_BASICO", detalle="Archivo PDF presente; falta verificar el contenido contra su fuente")
    return result


def run(manifest: Path = MANIFEST, root: Path = PROJECT_ROOT, report: Path = REPORT) -> int:
    with manifest.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        if not REQUIRED_COLUMNS.issubset(reader.fieldnames or []):
            raise ValueError("El inventario de fuentes no tiene todas las columnas obligatorias")
        rows = list(reader)
    results = [audit_one(row, root) for row in rows]
    report.parent.mkdir(parents=True, exist_ok=True)
    with report.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["id", "archivo", "estado", "tamano_bytes", "sha256", "detalle"])
        writer.writeheader()
        writer.writerows(results)
    for entry in results:
        print(f"[{entry['estado']}] {entry['id']}: {entry['detalle']}")
    print(f"\nAuditoría guardada en: {report.relative_to(root) if report.is_relative_to(root) else report}")
    print("Nota: OK_BASICO no significa que los valores tarifarios hayan sido validados.")
    return 0 if results and all(entry["estado"] == "OK_BASICO" for entry in results) else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Auditar archivos oficiales descargados")
    parser.parse_args()
    raise SystemExit(run())
