"""Chunking trazable del corpus elaborado en la subetapa 02.3.

No procesa tarifas, no llama a un LLM y no descarga documentos.
La ruta de entrada es data/processed/rag/*.md (tres fuentes oficiales).
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import re
import unicodedata
from typing import Any

from energia_ai.rag.corpus import SOURCES, safe_path


DEFAULT_CHUNK_SIZE = 900
DEFAULT_CHUNK_OVERLAP = 130
MANIFEST_VERSION = 2
CHUNK_STRATEGY = "recursive_paragraph_sentence_v2"


@dataclass(frozen=True)
class RagChunk:
    id: str
    text: str
    metadata: dict[str, Any]


def split_text(text: str, *, size: int = DEFAULT_CHUNK_SIZE,
               overlap: int = DEFAULT_CHUNK_OVERLAP) -> list[str]:
    """Separa texto en ventanas parcialmente superpuestas, cortando en espacios.

    `size` se mide en caracteres, no tokens. El RAG se evaluará empíricamente.
    """
    if size < 100 or overlap < 0 or overlap >= size // 2:
        raise ValueError("Usar size>=100 y overlap entre 0 y menos de size/2")
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    parts: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            boundary = text.rfind(" ", start + (size * 2 // 3), end)
            if boundary > start:
                end = boundary
        part = text[start:end].strip()
        if part:
            parts.append(part)
        if end >= len(text):
            break
        next_start = end - overlap
        if next_start <= start:
            raise RuntimeError("El chunking no avanza")
        start = next_start
    return parts



def clean_retrieval_text(text: str) -> str:
    """Normaliza texto del corpus sin alterar números ni afirmaciones técnicas.

    Preserva párrafos y listas. Elimina marcas repetitivas de editorial que
    ya están representadas en los metadatos; NO intenta arreglar tablas PDF.
    """
    if not isinstance(text, str):
        raise TypeError("El texto del corpus debe ser una cadena")
    text = unicodedata.normalize("NFKC", text).replace("\u00ad", "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(
        r"(?i)Secretar[ií]a de Energ[ií]a\s+Subsecretar[ií]a de Transici[oó]n y Planeamiento Energ[eé]tico",
        " ", text,
    )
    # Un solo salto de línea en extracción PDF suele ser visual; dos delimitan párrafo.
    paragraphs = re.split(r"\n\s*\n+", text)
    cleaned = []
    for paragraph in paragraphs:
        p = re.sub(r"\s+", " ", paragraph).strip()
        if p:
            cleaned.append(p)
    return "\n\n".join(cleaned)


def _units_for_paragraph(paragraph: str, size: int) -> list[str]:
    """Mantiene párrafos completos y divide por oraciones solo si hace falta."""
    if len(paragraph) <= size:
        return [paragraph]
    sentences = re.split(r"(?<=[.!?;:])\s+(?=[A-ZÁÉÍÓÚÜÑ0-9¿¡-])", paragraph)
    result: list[str] = []
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        if len(sentence) <= size:
            result.append(sentence)
        else:
            # Fallback para oraciones excepcionalmente largas y PDF mal extraído.
            result.extend(split_text(sentence, size=size, overlap=0))
    return result


def split_text_recursive(text: str, *, size: int = DEFAULT_CHUNK_SIZE,
                         overlap: int = DEFAULT_CHUNK_OVERLAP) -> list[str]:
    """Fragmentación por párrafos/oraciones con solapamiento de unidades completas.

    Overlap es objetivo aproximado (en caracteres), nunca garantiza un valor
    exacto: preferimos no iniciar un fragmento en mitad de una oración.
    """
    if size < 100 or overlap < 0 or overlap >= size // 2:
        raise ValueError("Usar size>=100 y overlap entre 0 y menos de size/2")
    cleaned = clean_retrieval_text(text)
    if not cleaned:
        return []
    units = [unit for paragraph in cleaned.split("\n\n")
             for unit in _units_for_paragraph(paragraph, size)]
    chunks: list[str] = []
    buf: list[str] = []
    for unit in units:
        if not buf:
            buf = [unit]
            continue
        proposed = "\n\n".join([*buf, unit])
        if len(proposed) <= size:
            buf.append(unit)
            continue
        chunks.append("\n\n".join(buf))
        retained: list[str] = []
        if overlap:
            # Reciclar frases/párrafos completos, sin exceder el tamaño del chunk.
            for prev in reversed(buf):
                candidate = [prev, *retained]
                if len("\n\n".join(candidate)) > overlap or len("\n\n".join([*candidate, unit])) > size:
                    break
                retained.insert(0, prev)
        buf = [*retained, unit]
    if buf:
        last = "\n\n".join(buf)
        if not chunks or chunks[-1] != last:
            chunks.append(last)
    if any(not chunk or len(chunk) > size for chunk in chunks):
        raise RuntimeError("El chunking recursivo produjo una ventana inválida")
    return chunks

def extract_body(markdown: str, expected_id: str, expected_url: str,
                 expected_sha: str) -> str:
    """Comprueba encabezados escritos en 02.3 y extrae el contenido editorial."""
    head, separator, body = markdown.partition("\n---\n")
    if not separator or not body.strip():
        raise ValueError(f"Documento {expected_id}: falta separador o cuerpo")
    for label, value in (
        ("ID", expected_id),
        ("Fuente original", expected_url),
        ("SHA256 de origen", expected_sha),
    ):
        if not re.search(rf"(?m)^{re.escape(label)}:\s*{re.escape(value)}\s*$", head):
            raise ValueError(f"Documento {expected_id}: metadato inválido: {label}")
    return body.strip()


def page_sections(body: str, is_pdf: bool) -> list[tuple[int, str]]:
    """En PDFs, cada chunk pertenece a una sola página para citarla con precisión."""
    if not is_pdf:
        return [(0, body)]
    parts = re.split(r"(?m)^## Pagina\s+(\d+)\s*$", body)
    if len(parts) < 3:
        raise ValueError("PDF preparado sin marcadores '## Pagina N'")
    if parts[0].strip():
        raise ValueError("PDF con texto sin número de página antes del primer marcador")
    result: list[tuple[int, str]] = []
    for i in range(1, len(parts), 2):
        number = int(parts[i])
        text = parts[i + 1].strip()
        if number < 1:
            raise ValueError("Número de página inválido")
        if text:
            result.append((number, text))
    if not result:
        raise ValueError("No se encontraron páginas con texto")
    return result


def load_chunks(project_root: Path, *, size: int = DEFAULT_CHUNK_SIZE,
                overlap: int = DEFAULT_CHUNK_OVERLAP) -> list[RagChunk]:
    """Devuelve chunks de exactamente las tres fuentes aprobadas en la etapa 02."""
    root = project_root.resolve()
    report_path = safe_path(root, "data/processed/rag/corpus_report.json")
    if not report_path.is_file():
        raise FileNotFoundError("Falta corpus_report.json: ejecutar Etapa 02.3")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    records = {item["id"]: item for item in report["documents"]}
    required_ids = {source.id for source in SOURCES}
    if set(records) != required_ids or len(SOURCES) != 3:
        raise ValueError("Se esperaban exactamente los tres documentos del corpus oficial")
    chunks: list[RagChunk] = []
    for source in SOURCES:
        record = records[source.id]
        if record.get("url") != source.official_url or record.get("prepared_file") != source.prepared_relative:
            raise ValueError(f"Inconsistencia en el reporte: {source.id}")
        fingerprint = record.get("sha256_raw", "")
        if not re.fullmatch(r"[0-9a-f]{64}", fingerprint):
            raise ValueError(f"SHA-256 inválido: {source.id}")
        path = safe_path(root, source.prepared_relative)
        if not path.is_file():
            raise FileNotFoundError(f"Falta documento preparado: {path}")
        content = path.read_text(encoding="utf-8")
        body = extract_body(content, source.id, source.official_url, fingerprint)
        if len(body) < 250:
            raise ValueError(f"Documento demasiado corto: {source.id}")
        count_for_source = 0
        for page, text in page_sections(body, source.kind == "pdf"):
            for fragment in split_text_recursive(text, size=size, overlap=overlap):
                # Hash estable para reproducibilidad, páginas y contenido.
                digest = sha256(f"{source.id}\0{page}\0{fragment}".encode("utf-8")).hexdigest()[:24]
                metadata = {
                    "source_id": source.id,
                    "title": source.title,
                    "publisher": source.publisher,
                    "published": source.published,
                    "region": source.region,
                    "topic": source.topic,
                    "season": ("winter" if source.id == "EPRE-INV-2022" else
                               "summer" if source.id == "EPRE-VER-2025" else "general"),
                    "url": source.official_url,
                    "page": page,  # cero significa publicación web (sin paginación)
                    "sha256_raw": fingerprint,
                }
                chunks.append(RagChunk(id=f"rag_{digest}", text=fragment, metadata=metadata))
                count_for_source += 1
        if count_for_source < 1:
            raise ValueError(f"Documento sin chunks: {source.id}")
    if len({item.id for item in chunks}) != len(chunks):
        raise ValueError("IDs duplicados en los chunks")
    return chunks


def corpus_fingerprint(chunks: list[RagChunk], *, model: str,
                       size: int, overlap: int) -> str:
    data = {
        "schema": MANIFEST_VERSION,
        "chunk_strategy": CHUNK_STRATEGY,
        "model": model,
        "chunk_size": size,
        "chunk_overlap": overlap,
        "chunks": [
            {"id": c.id, "sha256_raw": c.metadata["sha256_raw"], "page": c.metadata["page"]}
            for c in chunks
        ],
    }
    return sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
