"""Consulta semántica de prueba, sin LLM ni tool LangChain."""
from __future__ import annotations
import argparse
from pathlib import Path
from energia_ai.rag.vector_store import RagSearcher


def main() -> None:
    parser = argparse.ArgumentParser(description="Consulta al índice RAG")
    parser.add_argument("pregunta", nargs="?", default="¿Cómo reducir el uso del aire acondicionado durante el verano?")
    parser.add_argument("--k", type=int, default=3)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    finder = RagSearcher(root)
    for i, match in enumerate(finder.search(args.pregunta, k=args.k), start=1):
        print(f"\n{i}. {match['citation']}")
        print(f"   Fuente: {match['source_url']}")
        print(f"   Distancia vectorial: {match['distance']:.4f} (no es una probabilidad)")
        print("   Texto:", match["text"][:500])

if __name__ == "__main__":
    main()
