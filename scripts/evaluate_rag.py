"""Etapa 04.3: evalúa la tool real buscar_consejos (Ollama + Chroma).

Escribe un reporte editable para revisar manualmente pertinencia, citas y cortes.
No reindexa los documentos y no usa un LLM para evaluar.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from energia_ai.agent.advice_tool import buscar_consejos
from energia_ai.rag.evaluation import CASES, evaluar_casos, metricas_automaticas


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluación reproducible del RAG")
    parser.add_argument("--k", type=int, default=3, help="Resultados por pregunta (1-5)")
    parser.add_argument("--recrear", action="store_true", help="Sobrescribe evaluaciones manuales anteriores")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    destino = root / "data" / "processed" / "rag" / "evaluacion_04_3.json"
    if destino.exists() and not args.recrear:
        raise SystemExit(
            "Ya existe evaluacion_04_3.json. Revisalo antes de reemplazarlo; "
            "usar --recrear para ejecutar una evaluación nueva."
        )
    reporte = evaluar_casos(
        CASES,
        lambda pregunta, k: buscar_consejos.invoke({"consulta": pregunta, "max_resultados": k}),
        k=args.k,
    )
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporal = destino.with_suffix(".json.tmp")
    temporal.write_text(json.dumps(reporte, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporal.replace(destino)
    metricas = metricas_automaticas(reporte)
    print("EnergiaAI - Etapa 04.3 | Evaluación automática de recuperación")
    print(json.dumps(metricas, ensure_ascii=False, indent=2))
    print(f"\nReporte editable: {destino}")
    print("IMPORTANTE: las métricas automáticas NO sustituyen la revisión humana.")
    if metricas["consultas_con_error"]:
        raise SystemExit(
            "Una o más consultas devolvieron error. Revisar Ollama/Chroma y el reporte; "
            "después repetir con --recrear si corresponde."
        )


if __name__ == "__main__":
    main()
