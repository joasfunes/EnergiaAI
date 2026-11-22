"""Construye o reutiliza el índice RAG local. Ejecutar desde la raíz del repo."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from energia_ai.rag.vector_store import create_index


def main() -> None:
    parser = argparse.ArgumentParser(description="Indexación RAG de EnergiaAI")
    parser.add_argument("--rebuild", action="store_true", help="Recrear índice por cambio de corpus/modelo")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    result = create_index(root, rebuild=args.rebuild)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("Indexación terminada. Los fragmentos conservan su fuente y, si aplica, página.")

if __name__ == "__main__":
    main()
