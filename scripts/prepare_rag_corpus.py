"""Extrae texto y genera 3 Markdown locales con metadatos; aun SIN embeddings."""

from __future__ import annotations
from pathlib import Path

from energia_ai.rag.corpus import prepare_corpus

ROOT = Path(__file__).resolve().parents[1]

if __name__ == "__main__":
    try:
        result = prepare_corpus(ROOT)
        for item in result:
            pages = f", {item['pages']} paginas" if item['pages'] else ""
            print(f"[PENDIENTE_REVISION] {item['id']}: {item['characters_extracted']} caracteres{pages}")
        print("Preparados 3/3. Revisar texto y fuentes antes de cerrar 02.3.")
        print("No se generaron embeddings. Eso corresponde a la Etapa 04.")
    except (FileNotFoundError, ValueError, OSError) as error:
        raise SystemExit(f"ERROR: {error}") from error
