"""Demostración real del agente 05.2; sin interfaz ni base persistente.

Uso: python scripts/demo_full_agent.py --escenario consumo|tarifa|consejos|ahorro|integral|faltantes|chat
"""
from __future__ import annotations

import argparse
import sys
from uuid import uuid4

from energia_ai.agent.full_agent import crear_agente_completo
from energia_ai.agent.session import ejecutar_turno, tools_ejecutadas

CASOS = {
    "consumo": (
        "Tengo un televisor de 100 W, que utilicé 5 horas efectivas al día durante "
        "20 días. Calculá su consumo en kWh usando calcular_consumo."
    ),
    "tarifa": (
        "Tengo servicio residencial EDEMSA, consumí 350 kWh facturados en el "
        "bimestre. Consultá los cargos tarifarios SIN_SEF vigentes el 15 de noviembre "
        "de 2026 usando consultar_tarifa. No calcules el total de la factura."
    ),
    "consejos": (
        "Vivo en Mendoza. Recuperá mediante buscar_consejos recomendaciones oficiales "
        "para reducir el uso de aire acondicionado durante el verano; mencioná las fuentes."
    ),
    "ahorro": (
        "Tengo un aire acondicionado de 1500 W que uso 5 horas efectivas diarias "
        "durante 10 días dentro de un período de 60 días. Evaluá bajarlo a 3 horas "
        "por día en esos mismos 10 días. Usá calcular_consumo y simular_ahorro. "
        "No tengo factura: informá solo kWh y porcentaje, nunca pesos."
    ),
    "integral": (
        "Analizá este caso residencial EDEMSA en Mendoza. Fecha de referencia "
        "15/11/2026. Consumo facturado del bimestre (60 días): 350 kWh, régimen "
        "SIN_SEF. Aire acondicionado único, ID aire_1, potencia supuesta 1500 W, "
        "uso actual 5 horas efectivas por día durante 10 días dentro del bimestre. "
        "Quiero reducir a 3 horas efectivas por día durante los mismos 10 días "
        "y conservar el resto del consumo del hogar sin cambios. "
        "Realizá el análisis usando calcular_consumo, consultar_tarifa, "
        "simular_ahorro y buscar_consejos (consejos de verano). "
        "No inventes el ahorro en ARS: si simular_ahorro no lo confirma, "
        "mostrá solo el ahorro energético y explicá por qué. "
        "Cita fuentes del EPRE o guía oficial."
    ),
    "faltantes": (
        "Quiero que calcules cuánto pago de luz con mi aire acondicionado. "
        "No sé potencia, horas, consumo de factura ni régimen tarifario."
    ),
}

# Las expectativas son de ejecución REAL, no garantías de comportamiento del LLM.
ESPERADAS = {
    "consumo": {"calcular_consumo"},
    "tarifa": {"consultar_tarifa"},
    "consejos": {"buscar_consejos"},
    "ahorro": {"calcular_consumo", "simular_ahorro"},
    "integral": {"calcular_consumo", "consultar_tarifa", "simular_ahorro", "buscar_consejos"},
    "faltantes": set(),
}


def imprimir_turno(turno: dict, *, esperadas: set[str] | None = None) -> bool:
    print("\nRESPUESTA DEL ASISTENTE\n" + (turno["respuesta"] or "<sin texto>"))
    print("\nEJECUCIONES REALES (ToolMessage del turno)")
    if not turno["ejecuciones"]:
        print("  Ninguna tool ejecutada")
    for item in turno["ejecuciones"]:
        print(f"  {item['tool']} → estado={item['estado']}")
        if item["estado"] in {"error", "sin_resultados"}:
            print("    Advertencia: revisar argumentos o evidencia; NO asumir éxito.")
    if esperadas is None:
        return True
    faltantes = esperadas - tools_ejecutadas(turno)
    if faltantes:
        print("\nNO VERIFICADO: faltó ejecución real de:", ", ".join(sorted(faltantes)))
        print("El modelo decide las herramientas; se debe revisar la traza y el prompt.")
        return False
    print("\nOK: se observaron las tools previstas para este escenario.")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Qwen + cuatro tools EnergiaAI")
    parser.add_argument("--escenario", choices=[*CASOS, "chat"], default="consumo")
    parser.add_argument("--thread-id", default=None, help="Identificador local del thread")
    args = parser.parse_args()
    thread_id = args.thread_id or f"energiaai-052-{uuid4().hex[:10]}"
    print("EnergiaAI | Etapa 05.2 | Modelo local con cuatro tools")
    print("Thread:", thread_id)
    print("Memoria solo en este proceso; no hay perfil del hogar persistido.")
    try:
        agente = crear_agente_completo()
        if args.escenario == "chat":
            print("Modo interactivo. Escribí salir para finalizar.")
            while True:
                consulta = input("\nVos> ").strip()
                if consulta.lower() in {"salir", "exit", "quit"}:
                    break
                if not consulta:
                    continue
                turno = ejecutar_turno(agente, consulta=consulta, thread_id=thread_id)
                imprimir_turno(turno)
            return 0
        pregunta = CASOS[args.escenario]
        print("\nCONSULTA DE PRUEBA\n" + pregunta)
        turno = ejecutar_turno(agente, consulta=pregunta, thread_id=thread_id)
        comprobado = imprimir_turno(turno, esperadas=ESPERADAS[args.escenario])
        if args.escenario == "faltantes" and tools_ejecutadas(turno):
            print("NO VERIFICADO: el modelo llamó tools sin los datos indispensables.")
            return 3
        return 0 if comprobado else 3
    except (KeyboardInterrupt, EOFError):
        print("\nSesión finalizada.")
        return 130
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}")
        print("Verificá Ollama, Qwen, el índice RAG y la configuración de las tools.")
        return 2


if __name__ == "__main__":
    sys.exit(main())
