"""Índice Chroma persistente y embeddings Ollama para EnergiaAI (sin LLM de chat).

La indexación se hace fuera del chat. En las consultas solamente se embeberá
la pregunta y se recuperarán fragmentos con metadatos de procedencia.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import math
import os
import re
import unicodedata
from pathlib import Path
from typing import Any, Protocol

from energia_ai.rag.chunking import (
    DEFAULT_CHUNK_OVERLAP, DEFAULT_CHUNK_SIZE, CHUNK_STRATEGY, corpus_fingerprint, load_chunks,
)
from energia_ai.rag.corpus import safe_path

MODEL_NAME = "embeddinggemma:300m"
COLLECTION_NAME = "energiaai_eficiencia_mendoza"
INDEX_DIR = "data/vectorstore/energiaai_rag"
MANIFEST_FILE = "data/vectorstore/energiaai_rag_manifest.json"
BATCH_SIZE = 12


class Embedder(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


@dataclass
class OllamaEmbedder:
    model_name: str = MODEL_NAME

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            import ollama
            response = ollama.embed(model=self.model_name, input=texts)
            vectors = response.embeddings if hasattr(response, "embeddings") else response["embeddings"]
        except ImportError as exc:
            raise RuntimeError("Instalar requirements-rag-index.txt") from exc
        except Exception as exc:
            raise RuntimeError(
                f"Ollama no pudo generar embeddings. Comprobar 'ollama list' y que "
                f"'{self.model_name}' esté descargado. Detalle: {exc}"
            ) from exc
        return validate_vectors(vectors, len(texts))


def validate_vectors(vectors: Any, expected: int) -> list[list[float]]:
    if len(vectors) != expected:
        raise ValueError("El modelo devolvió una cantidad incorrecta de embeddings")
    validated: list[list[float]] = []
    for vector in vectors:
        v = [float(n) for n in vector]
        if not v or any(not math.isfinite(n) for n in v):
            raise ValueError("Embedding vacío o con valores no finitos")
        if validated and len(v) != len(validated[0]):
            raise ValueError("Dimensiones de embeddings inconsistentes")
        validated.append(v)
    return validated


def _client(index_path: Path) -> Any:
    try:
        import chromadb
    except ImportError as exc:
        raise RuntimeError("Instalar requirements-rag-index.txt") from exc
    return chromadb.PersistentClient(path=str(index_path))


def _collection(client: Any, *, create: bool) -> Any:
    if create:
        return client.get_or_create_collection(name=COLLECTION_NAME, embedding_function=None)
    return client.get_collection(name=COLLECTION_NAME, embedding_function=None)


def create_index(project_root: Path, *, rebuild: bool = False,
                 embedder: Embedder | None = None, client: Any | None = None,
                 model_name: str = MODEL_NAME) -> dict[str, Any]:
    """Indexa corpus verificado. Nunca borra un índice vigente sin --rebuild."""
    root = project_root.resolve()
    chunk_size, overlap = DEFAULT_CHUNK_SIZE, DEFAULT_CHUNK_OVERLAP
    chunks = load_chunks(root, size=chunk_size, overlap=overlap)
    signature = corpus_fingerprint(chunks, model=model_name, size=chunk_size, overlap=overlap)
    manifest_path = safe_path(root, MANIFEST_FILE)
    existing = json.loads(manifest_path.read_text("utf-8")) if manifest_path.exists() else None
    client = client if client is not None else _client(safe_path(root, INDEX_DIR))
    if existing is not None and not rebuild:
        if existing.get("fingerprint") != signature:
            raise ValueError("Cambió el corpus/modelo/chunking: reconstruir con --rebuild")
        try:
            count = _collection(client, create=False).count()
        except Exception as exc:
            raise ValueError("Manifiesto encontrado, pero la colección Chroma no existe") from exc
        if count != len(chunks):
            raise ValueError("Colección incompleta: reconstruir con --rebuild")
        return {**existing, "status": "REUTILIZADO"}
    if existing is None and not rebuild:
        # Evitar mezclar colección vieja con manifiesto perdido.
        try:
            old_collection = _collection(client, create=False)
        except Exception:
            old_collection = None
        if old_collection is not None and old_collection.count() > 0:
            raise ValueError("Ya existe una colección sin manifiesto. Revisar y usar --rebuild")
    embedder = embedder if embedder is not None else OllamaEmbedder(model_name)
    vectors: list[list[float]] = []
    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i:i + BATCH_SIZE]
        vectors.extend(validate_vectors(embedder.embed([c.text for c in batch]), len(batch)))
    validate_vectors(vectors, len(chunks))
    if rebuild:
        try:
            previous = _collection(client, create=False)
        except Exception:
            previous = None
        if previous is not None:
            # No ocultar errores reales de borrado: abortar si Chroma falla.
            client.delete_collection(name=COLLECTION_NAME)
    collection = _collection(client, create=True)
    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i:i + BATCH_SIZE]
        collection.upsert(
            ids=[c.id for c in batch],
            documents=[c.text for c in batch],
            metadatas=[c.metadata for c in batch],
            embeddings=vectors[i:i + BATCH_SIZE],
        )
    if collection.count() != len(chunks):
        raise RuntimeError("Chroma no almacenó todos los fragmentos")
    manifest = {
        "status": "INDEXADO",
        "collection": COLLECTION_NAME,
        "embedding_model": model_name,
        "embedding_dimensions": len(vectors[0]),
        "chunk_size": chunk_size,
        "chunk_overlap": overlap,
        "chunk_strategy": CHUNK_STRATEGY,
        "chunks": len(chunks),
        "documents": len(set(c.metadata["source_id"] for c in chunks)),
        "fingerprint": signature,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = manifest_path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(temporary, manifest_path)
    return manifest



def infer_season(question: str) -> str | None:
    """Detecta únicamente un contexto estacional explícito y no ambiguo.

    No sustituye la recuperación semántica; solo evita mezclar consejos de
    invierno con verano. Si hay señales contradictorias, no filtra.
    """
    norm = unicodedata.normalize("NFKD", question.casefold())
    norm = "".join(char for char in norm if not unicodedata.combining(char))
    winter = bool(re.search(r"\b(invierno|frio|calefaccion|caloventores?|estufas?)\b", norm))
    summer = bool(re.search(r"\b(verano|refrigeracion|ola de calor|mucho calor|dias? de calor|temperaturas? altas?)\b", norm))
    if winter == summer:
        return None
    return "winter" if winter else "summer"


class RagSearcher:
    """Se crea una vez al iniciar la aplicación; una búsqueda no lee PDFs/CSV."""
    def __init__(self, project_root: Path, *, embedder: Embedder | None = None,
                 client: Any | None = None, model_name: str = MODEL_NAME):
        root = project_root.resolve()
        manifest_path = safe_path(root, MANIFEST_FILE)
        if not manifest_path.is_file():
            raise FileNotFoundError("Falta índice RAG: ejecutar scripts/build_rag_index.py")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("embedding_model") != model_name:
            raise ValueError("Modelo de embeddings distinto al usado para construir el índice")
        if manifest.get("chunk_strategy") != CHUNK_STRATEGY:
            raise ValueError("Índice con estrategia de chunking anterior: ejecutar respaldo y --rebuild")
        self.embedder = embedder if embedder is not None else OllamaEmbedder(model_name)
        self.client = client if client is not None else _client(safe_path(root, INDEX_DIR))
        self.collection = _collection(self.client, create=False)
        if self.collection.count() != manifest.get("chunks"):
            raise ValueError("Índice RAG incompleto: reconstruir")
        self.manifest = manifest

    def search(self, question: str, *, k: int = 3) -> list[dict[str, Any]]:
        question = question.strip()
        if not question or len(question) > 2000:
            raise ValueError("La consulta debe contener entre 1 y 2000 caracteres")
        if not 1 <= k <= 8:
            raise ValueError("k debe estar entre 1 y 8")
        embedding = validate_vectors(self.embedder.embed([question]), 1)[0]
        if len(embedding) != self.manifest["embedding_dimensions"]:
            raise ValueError("Dimensión de consulta distinta a la del índice")
        # Para el corpus pequeño del MVP recuperamos candidatos adicionales y
        # después descartamos la estación opuesta cuando la pregunta es clara.
        # En corpus grandes, reemplazar esto por filtros por metadatos en Chroma.
        candidate_count = min(self.collection.count(), max(k * 6, 18))
        retrieved = self.collection.query(
            query_embeddings=[embedding],
            n_results=candidate_count,
            include=["documents", "metadatas", "distances"],
        )
        texts = retrieved["documents"][0]
        metas = retrieved["metadatas"][0]
        distances = retrieved["distances"][0]
        matches: list[dict[str, Any]] = []
        season = infer_season(question)
        for text, meta, distance in zip(texts, metas, distances):
            if season is not None and meta.get("season", "general") not in (season, "general"):
                continue
            page = int(meta["page"])
            citation = f'{meta["title"]} (p. {page})' if page else f'{meta["title"]} (publicación web)'
            matches.append({
                "text": text,
                "citation": citation,
                "source_id": meta["source_id"],
                "source_url": meta["url"],
                "page": page if page else None,
                "distance": float(distance),
            })
        return matches[:k]
