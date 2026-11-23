"""Mide UN turno del agente actual con Qwen3.5 9B; no cambia modelos ni calcula embeddings.

Ejemplo: python scripts/benchmark_agent_06_1.py --consulta "¿Cuánto consume ...?"
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from uuid import uuid4

from energia_ai.agent.local_llm import config_local
from energia_ai.agent.persistent_runtime import abrir_runtime_persistente
from energia_ai.agent.telemetry import ejecutar_turno_medido


def _evento(evento: dict) -> None:
    tipo = evento.get("tipo")
    if tipo == "texto":
        print(evento.get("texto", ""), end="", flush=True)
    elif tipo == "tool":
        print(f"\n[TOOL OBSERVADA: {evento['nombre']} | estado={evento['estado']}]", flush=True)
    elif tipo == "tool_inicio":
        print(f"\n[INICIO TOOL: {evento['nombre']} | args permitidos: {evento['argumentos']}]", flush=True)
    elif tipo == "tool_fin":
        print(f"\n[FIN TOOL: {evento['nombre']} | estado={evento['estado']} | "
              f"{evento['duracion_s']}s | resumen={evento['resultado']}]", flush=True)
    elif tipo == "fin":
        print(flush=True)


def guardar_resumen(ruta: Path, resumen: dict) -> None:
    """Guarda solo métricas sin prompts y crea carpetas locales."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(resumen, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Etapa 06.1 — trazabilidad y rendimiento, mismo Qwen")
    parser.add_argument("--consulta", default=(
        "Tengo un televisor de 100 W que utilizo 5 horas efectivas diarias durante 20 días. "
        "Calculá su consumo en kWh mediante la herramienta."))
    parser.add_argument("--hogar-id", default="hogar_benchmark")
    parser.add_argument("--thread-id", default=None,
                        help="Omitido: se genera un thread nuevo para una medición aislada")
    parser.add_argument("--carpeta-estado", default="data/state")
    parser.add_argument("--salida", default="data/processed/performance/medicion_06_1.json")
    args = parser.parse_args()
    try:
        cfg = config_local()
        if cfg["model"] != "qwen3.5:9b":
            print("AVISO: ENERGIAAI_LLM_MODEL indica otro modelo. "
                  "Para mantener Qwen3.5 9B, revisá esa variable.")
        thread_id = args.thread_id or f"benchmark_{uuid4().hex[:12]}"
        print(f"EnergiaAI 06.1 | modelo configurado={cfg['model']} | "
              "medición única, sin benchmarking de otros modelos")
        with abrir_runtime_persistente(hogar_id=args.hogar_id,
                                      carpeta_estado=args.carpeta_estado) as runtime:
            resumen = ejecutar_turno_medido(runtime.agente, consulta=args.consulta,
                                           thread_id=thread_id, notificar=_evento)
        guardar_resumen(Path(args.salida), resumen)
        print("\nMétricas:")
        print(json.dumps({k: resumen[k] for k in (
            "duracion_total_s", "tiempo_primera_salida_s", "llamadas_modelo",
            "duracion_modelo_observada_s", "herramientas")}, indent=2, ensure_ascii=False))
        print(f"Guardado local: {args.salida}")
        return 0
    except (KeyboardInterrupt, EOFError):
        print("\nMedición cancelada")
        return 130
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
