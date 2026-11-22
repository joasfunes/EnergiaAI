"""Research side: adquisicion y preparacion de 3 documentos oficiales para RAG.

No participa del loop de LangChain ni almacena tarifas. Las fuentes se
registran en codigo y se transforman ANTES de ejecutar el agente.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import re
from urllib.parse import urlparse

import fitz  # PyMuPDF
from bs4 import BeautifulSoup
import requests


# Solo fuentes oficiales aprobadas para este MVP.
ALLOWED_HOSTS = frozenset({"www.argentina.gob.ar", "epremendoza.gob.ar"})
MAX_HTML_BYTES = 5 * 1024 * 1024
MIN_TEXT_CHARS = 250


@dataclass(frozen=True)
class CorpusSource:
    id: str
    title: str
    publisher: str
    published: str
    official_url: str
    kind: str  # pdf | html
    raw_relative: str
    prepared_relative: str
    region: str
    topic: str


SOURCES: tuple[CorpusSource, ...] = (
    CorpusSource(
        id="ARG-RES-2024",
        title="Residencial: buenas practicas para reducir el consumo de energia",
        publisher="Secretaria de Energia de la Nacion",
        published="2024-06",
        official_url="https://www.argentina.gob.ar/sites/default/files/guia_residencial_enereficiente.pdf",
        kind="pdf",
        raw_relative="data/raw/documents/argentina/guia_residencial_2024.pdf",
        prepared_relative="data/processed/rag/arg_residencial_2024.md",
        region="Argentina (aplicable a Mendoza)",
        topic="eficiencia residencial general",
    ),
    CorpusSource(
        id="EPRE-INV-2022",
        title="Consejos para ahorrar energia en el invierno",
        publisher="EPRE Mendoza",
        published="2022-07-08",
        official_url="https://epremendoza.gob.ar/consejos-para-ahorrar-energia-en-el-invierno/",
        kind="html",
        raw_relative="data/raw/documents/mendoza/epre_invierno_2022.html",
        prepared_relative="data/processed/rag/epre_invierno_2022.md",
        region="Mendoza",
        topic="invierno, calefaccion y electrodomesticos",
    ),
    CorpusSource(
        id="EPRE-VER-2025",
        title="Ola de calor: recomendaciones para un uso eficiente y racional de la energia",
        publisher="EPRE Mendoza",
        published="2025-01-14",
        official_url="https://epremendoza.gob.ar/ola-de-calor-recomendaciones-para-un-uso-eficiente-y-racional-de-la-energia/",
        kind="html",
        raw_relative="data/raw/documents/mendoza/epre_verano_2025.html",
        prepared_relative="data/processed/rag/epre_verano_2025.md",
        region="Mendoza",
        topic="verano, refrigeracion y electrodomesticos",
    ),
)


def safe_path(root: Path, relative: str) -> Path:
    """No permitir rutas fuera del repositorio, incluso mediante '..' o symlinks."""
    base = root.resolve()
    destination = (base / relative).resolve()
    if not destination.is_relative_to(base):
        raise ValueError(f"Ruta fuera del proyecto: {relative}")
    return destination


def verify_source_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
        raise ValueError("La URL no pertenece a un origen oficial permitido")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def download_epre_html(root: Path, overwrite: bool = False) -> list[str]:
    """Descarga una sola vez las dos paginas oficiales; nunca en cada chat."""
    messages: list[str] = []
    for source in SOURCES:
        if source.kind != "html":
            continue
        verify_source_url(source.official_url)
        destination = safe_path(root, source.raw_relative)
        if destination.is_file() and not overwrite:
            messages.append(f"[YA EXISTE] {source.id}: {destination}")
            continue
        try:
            response = requests.get(
                source.official_url,
                timeout=(8, 30),
                headers={"User-Agent": "EnergiaAI-Educational-Corpus/0.1", "Accept": "text/html"},
                allow_redirects=True,
                stream=True,
            )
            with response:
                response.raise_for_status()
                verify_source_url(response.url)  # Aun si hubo redireccion
                if "text/html" not in response.headers.get("Content-Type", "").lower():
                    raise ValueError("La respuesta no tiene formato HTML")
                chunks: list[bytes] = []
                total = 0
                for piece in response.iter_content(chunk_size=65536):
                    total += len(piece)
                    if total > MAX_HTML_BYTES:
                        raise ValueError("Respuesta HTML demasiado grande")
                    chunks.append(piece)
                raw = b"".join(chunks)
                if b"<html" not in raw[:4096].lower() and b"<!doctype html" not in raw[:4096].lower():
                    raise ValueError("La respuesta no parece una pagina HTML")
                if not raw:
                    raise ValueError("Documento HTML vacio")
                destination.parent.mkdir(parents=True, exist_ok=True)
                temp = destination.with_suffix(destination.suffix + ".tmp")
                temp.write_bytes(raw)
                os.replace(temp, destination)
                messages.append(f"[DESCARGADO] {source.id}: {len(raw)} bytes")
        except (requests.RequestException, OSError, ValueError) as error:
            raise RuntimeError(
                f"No se pudo descargar {source.id}. Abrir {source.official_url} "
                "en el navegador, guardar el HTML completo en "
                f"{source.raw_relative} y reintentar. Detalle: {error}"
            ) from error
    return messages


def extract_html_article(raw_html: str) -> str:
    """Extrae solo el cuerpo editorial de la publicacion; excluye menus."""
    soup = BeautifulSoup(raw_html, "html.parser")
    content = soup.select_one("article .entry-content, .entry-content, article .post-content")
    if content is None:
        raise ValueError("No se encontro el articulo oficial (.entry-content)")
    for unwanted in content.select("script,style,nav,footer,form,iframe,.sharedaddy,.social-share"):
        unwanted.decompose()
    lines: list[str] = []
    for node in content.find_all(["h2", "h3", "h4", "p", "li"]):
        # La primera version evita tablas y otros widgets del sitio.
        value = re.sub(r"\s+", " ", node.get_text(" ", strip=True)).strip()
        if len(value) < 3:
            continue
        if node.name in {"h2", "h3", "h4"}:
            lines.append("## " + value)
        elif node.name == "li":
            lines.append("- " + value)
        else:
            lines.append(value)
    text = "\n\n".join(lines)
    if len(text) < MIN_TEXT_CHARS:
        raise ValueError("El articulo extraido tiene poco contenido; comprobar el HTML local")
    return text


def extract_pdf(raw_pdf: bytes) -> tuple[str, int]:
    """Devuelve texto y marcadores de pagina para permitir citas en RAG."""
    if not raw_pdf.startswith(b"%PDF-"):
        raise ValueError("El documento no es un PDF valido")
    pages: list[str] = []
    try:
        with fitz.open(stream=raw_pdf, filetype="pdf") as document:
            n_pages = len(document)
            for index, page in enumerate(document):
                text = page.get_text("text", sort=True)
                text = re.sub(r"[ \t]+", " ", text)
                text = re.sub(r"\n{3,}", "\n\n", text).strip()
                if text:
                    pages.append(f"## Pagina {index + 1}\n\n{text}")
    except Exception as error:
        raise ValueError(f"No se pudo procesar PDF: {error}") from error
    extracted = "\n\n".join(pages)
    if len(extracted) < MIN_TEXT_CHARS:
        raise ValueError("PDF sin texto suficiente: revisar si necesita OCR; no inventar contenido")
    return extracted, n_pages


def prepare_source(source: CorpusSource, root: Path) -> dict:
    verify_source_url(source.official_url)
    local = safe_path(root, source.raw_relative)
    target = safe_path(root, source.prepared_relative)
    if not local.is_file():
        raise FileNotFoundError(f"Falta {source.id}: {local} (ver guia ETAPA_02_3.md)")
    raw = local.read_bytes()
    pages = None
    if source.kind == "pdf":
        content, pages = extract_pdf(raw)
    elif source.kind == "html":
        content = extract_html_article(raw.decode("utf-8-sig", errors="replace"))
    else:
        raise ValueError("Formato no soportado")

    # Markdown reproducible: metadatos explícitos, separados del texto recuperable.
    header = (
        f"# {source.title}\n\n"
        f"ID: {source.id}\n\n"
        f"Organismo: {source.publisher}\n\n"
        f"Publicacion: {source.published}\n\n"
        f"Ambito: {source.region}\n\n"
        f"Tema: {source.topic}\n\n"
        f"Fuente original: {source.official_url}\n\n"
        f"SHA256 de origen: {sha256(raw)}\n\n"
        "---\n\n"
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    # Dejar contenido solo si fue verificado como extraíble y no vacío.
    target.write_text(header + content + "\n", encoding="utf-8")
    return {
        "id": source.id,
        "title": source.title,
        "publisher": source.publisher,
        "published": source.published,
        "url": source.official_url,
        "raw_file": source.raw_relative,
        "prepared_file": source.prepared_relative,
        "sha256_raw": sha256(raw),
        "characters_extracted": len(content),
        "pages": pages,
        "status": "READY_FOR_MANUAL_REVIEW",
    }


def prepare_corpus(root: Path) -> list[dict]:
    result = [prepare_source(source, root) for source in SOURCES]
    destination = safe_path(root, "data/processed/rag/corpus_report.json")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps({"created_on": date.today().isoformat(), "documents": result},
                   ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return result
