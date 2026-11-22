"""Etapa 04.3: calcula métricas de relevancia DESPUÉS de revisar cada fragmento."""
from __future__ import annotations

import json
from pathlib import Path

from energia_ai.rag.evaluation import metricas_automaticas, metricas_manuales


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    path = root / "data" / "processed" / "rag" / "evaluacion_04_3.json"
    if not path.is_file():
        raise SystemExit("Falta evaluacion_04_3.json: ejecutar scripts/evaluate_rag.py")
    reporte = json.loads(path.read_text(encoding="utf-8"))
    try:
        automaticas = metricas_automaticas(reporte)
        manuales = metricas_manuales(reporte)
    except (KeyError, TypeError, ValueError) as error:
        raise SystemExit(f"No se pudo puntuar: {error}") from error
    resumen = {"automaticas": automaticas, "manuales": manuales}
    destino = path.with_name("evaluacion_04_3_resumen.json")
    destino.write_text(json.dumps(resumen, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(resumen, indent=2, ensure_ascii=False))
    print(f"\nResumen guardado en: {destino}")
    print("Las métricas NO califican respuestas del futuro agente ni verifican cifras automáticamente.")


if __name__ == "__main__":
    main()
