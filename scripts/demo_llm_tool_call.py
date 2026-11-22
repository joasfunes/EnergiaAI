"""Prueba REAL de tool calling de Qwen mediante create_agent.

No cambia tarifas ni RAG. Todavía NO es el caso de uso completo de EnergiaAI.
"""
from __future__ import annotations
import sys
from uuid import uuid4

from energia_ai.agent.local_llm import crear_agente_piloto
from energia_ai.agent.tool_trace import resumir_ejecuciones, ultimo_mensaje_asistente


def main() -> int:
    print("EnergiaAI | Etapa 05.1 | Prueba LLM + UNA tool")
    print("El primer turno debe ejecutar calcular_consumo realmente.")
    agente = crear_agente_piloto()
    thread_id = f"piloto-{uuid4().hex[:12]}"
    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 8}

    pregunta = (
        "Tengo un televisor de 100 W que usé 5 horas efectivas por día durante 20 días. "
        "Calculá su consumo en kWh usando obligatoriamente la herramienta calcular_consumo."
    )
    try:
        resultado = agente.invoke({"messages": [{"role": "user", "content": pregunta}]}, config=config)
    except Exception as exc:
        print(f"ERROR durante la inferencia: {type(exc).__name__}: {exc}")
        print("Comprobá Ollama, el modelo y las librerías instaladas.")
        return 2

    ejecuciones = resumir_ejecuciones(resultado.get("messages", []))
    for ejecucion in ejecuciones:
        print(f"TOOL EJECUTADA: {ejecucion['tool']}")
        print(f"Resultado (extracto): {ejecucion['contenido'][:700]}")
    print(f"Respuesta del asistente: {ultimo_mensaje_asistente(resultado.get('messages', []))[:1000]}")
    if not any(x["tool"] == "calcular_consumo" for x in ejecuciones):
        print("NO VERIFICADO: el LLM respondió sin ejecutar la tool.")
        print("Reintentá o revisemos el modelo y la configuración de tool calling.")
        return 3

    print("OK: hubo ejecución REAL de calcular_consumo por decisión del modelo.")
    # Segunda consulta MISMO thread_id, MISMO proceso: prueba de InMemorySaver.
    followup = "¿Cuántos kWh consumía ese televisor según el cálculo anterior?"
    try:
        segundo = agente.invoke({"messages": [{"role": "user", "content": followup}]}, config=config)
    except Exception as exc:
        print(f"Error en la prueba de memoria: {type(exc).__name__}: {exc}")
        return 4
    print("Respuesta segundo turno: " + ultimo_mensaje_asistente(segundo.get("messages", []))[:1000])
    print("La memoria se conserva solo mientras este proceso esté activo.")
    print("Revisá manualmente que el segundo turno recuerde el resultado de 10 kWh.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
