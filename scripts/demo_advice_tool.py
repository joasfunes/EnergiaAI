"""Demo real SIN agente ni LLM conversacional: Ollama + ChromaDB + LangChain tool."""
from __future__ import annotations

import json
import sys

from energia_ai.agent.advice_tool import buscar_consejos


def main() -> None:
    consulta = " ".join(sys.argv[1:]).strip() or "¿Cómo reducir el consumo de calefacción en invierno?"
    print(f"Tool: {buscar_consejos.name}")
    print(f"Consulta: {consulta}")
    salida = buscar_consejos.invoke({"consulta": consulta, "max_resultados": 3})
    print(json.dumps(salida, ensure_ascii=False, indent=2))
    if salida.get("estado") == "error":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
