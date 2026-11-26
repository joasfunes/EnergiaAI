"""Prueba local del canal de razonamiento expuesto por Qwen+Ollama.

No usa ninguna tool ni modifica SQLite; no persiste el contenido generado.
"""
from __future__ import annotations

from energia_ai.agent.local_llm import config_local, crear_modelo
from energia_ai.agent.streaming import razonamiento_del_chunk, texto_del_chunk


def main() -> int:
    config = config_local()
    print(f"Modelo: {config['model']} | contexto: {config['num_ctx']}")
    print("Prueba fija sin datos privados. Se esperan dos canales independientes.\n")
    razonamiento_chars = 0
    respuesta_chars = 0
    canal = None
    try:
        for chunk in crear_modelo().stream(
            "¿Por qué reducir el tiempo de uso de un horno eléctrico puede ahorrar energía? "
            "Respondé en una sola oración."
        ):
            thinking = razonamiento_del_chunk(chunk)
            answer = texto_del_chunk(chunk)
            if thinking:
                if canal != "razonamiento":
                    print("\n[Razonamiento expuesto por Ollama]\n", flush=True)
                    canal = "razonamiento"
                print(thinking, end="", flush=True)
                razonamiento_chars += len(thinking)
            if answer:
                if canal != "respuesta":
                    print("\n\n[Respuesta final]\n", flush=True)
                    canal = "respuesta"
                print(answer, end="", flush=True)
                respuesta_chars += len(answer)
    except Exception as exc:
        print(f"\nERROR: {type(exc).__name__}. Revisá logs locales de Ollama.")
        return 2

    print(f"\n\nRESUMEN: reasoning_chars={razonamiento_chars} | respuesta_chars={respuesta_chars}")
    if razonamiento_chars == 0:
        print("No se recibió razonamiento separado de este proveedor/modelo en este turno.")
    if respuesta_chars == 0:
        print("ATENCIÓN: el modelo no emitió respuesta final; no validar como tarea completada.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
