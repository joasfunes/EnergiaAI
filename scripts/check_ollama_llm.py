"""Comprueba la API local de Ollama y la presencia de Qwen3.5 9B."""
from __future__ import annotations
import sys
from energia_ai.agent.local_llm import (
    LocalModelError, comprobar_modelo_disponible, config_local, consultar_modelos_ollama,
)


def main() -> int:
    try:
        config = config_local()
        modelos = consultar_modelos_ollama(config["base_url"])
    except (ValueError, LocalModelError) as exc:
        print(f"ERROR: {exc}")
        return 2
    print(f"Ollama: {config['base_url']}")
    print(f"Modelo requerido: {config['model']}")
    print("Modelos locales:")
    for m in modelos:
        print(f" - {m}")
    if not comprobar_modelo_disponible(config["model"], modelos):
        print(f"FALTA EL MODELO. Ejecutar: ollama pull {config['model']}")
        return 2
    print("OK: Ollama está disponible y el modelo está descargado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
