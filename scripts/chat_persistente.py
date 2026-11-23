"""Chat persistente de consola para EnergiaAI 05.3 (sin frontend).

Ejemplo:
python scripts/chat_persistente.py --hogar-id casa_demo --thread-id conversacion_1
"""
from __future__ import annotations

import argparse
import sys

from energia_ai.agent.persistent_runtime import abrir_runtime_persistente
from energia_ai.agent.session import ejecutar_turno
from energia_ai.agent.streaming import transmitir_turno


def imprimir_evento(evento: dict[str, str]) -> None:
    if evento["tipo"] == "tool":
        print(f"\n[Tool ejecutada: {evento['nombre']} | estado={evento['estado']}]", flush=True)
    elif evento["tipo"] == "texto":
        print(evento["texto"], end="", flush=True)
    elif evento["tipo"] == "fin":
        print(flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="EnergiaAI: chat local persistente con streaming")
    parser.add_argument("--hogar-id", default="hogar_demo")
    parser.add_argument("--thread-id", default="conversacion_1")
    parser.add_argument("--periodo-dias", type=int, default=60)
    parser.add_argument("--carpeta-estado", default="data/state")
    parser.add_argument("--sin-stream", action="store_true")
    parser.add_argument("--consulta", help="Realiza un turno y termina")
    args = parser.parse_args()
    try:
        with abrir_runtime_persistente(hogar_id=args.hogar_id, carpeta_estado=args.carpeta_estado,
                                     periodo_dias=args.periodo_dias) as runtime:
            print(f"EnergiaAI 05.3 | hogar={args.hogar_id} | thread={args.thread_id}")
            print("Historial e inventario guardados en SQLite local. Escribí salir para terminar.")
            def ejecutar(pregunta: str) -> None:
                if args.sin_stream:
                    turno = ejecutar_turno(runtime.agente, consulta=pregunta, thread_id=args.thread_id)
                    print(turno["respuesta"])
                    for evento in turno["ejecuciones"]:
                        print(f"[Tool: {evento['tool']} | estado={evento['estado']}]")
                else:
                    transmitir_turno(runtime.agente, consulta=pregunta, thread_id=args.thread_id,
                                    notificar=imprimir_evento)
            if args.consulta:
                ejecutar(args.consulta)
                return 0
            while True:
                consulta = input("\nVos> ").strip()
                if consulta.lower() in {"salir", "exit", "quit"}:
                    break
                if consulta:
                    ejecutar(consulta)
        return 0
    except (KeyboardInterrupt, EOFError):
        print("\nSesión finalizada")
        return 130
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
