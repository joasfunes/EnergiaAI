"""Descarga HTML oficial del EPRE UNA VEZ para preparar corpus, no en el chat."""

from __future__ import annotations
import argparse
from pathlib import Path

from energia_ai.rag.corpus import download_epre_html

ROOT = Path(__file__).resolve().parents[1]

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--overwrite", action="store_true", help="Actualizar originales (con cuidado)")
    args = parser.parse_args()
    try:
        for message in download_epre_html(ROOT, overwrite=args.overwrite):
            print(message)
    except RuntimeError as error:
        parser.exit(1, f"ERROR: {error}\n")
