r"""Etapa 03.4: prueba de integración real de las tres tools de LangChain.

NO implementa un agente ni interpreta lenguaje natural. El caso de prueba
suministra argumentos explícitos y reutiliza exactamente las respuestas
producidas por cada tool. No lee CSV/PDF ni recalcula tarifas a mano.

Ejecutar desde la raíz del proyecto:
    .\.venv\Scripts\python.exe scripts\demo_tools_integration.py
"""

from __future__ import annotations

import argparse
from decimal import Decimal
import json
from typing import Any

from energia_ai.agent.consumption_tool import calcular_consumo
from energia_ai.agent.savings_tool import simular_ahorro
from energia_ai.agent.tariff_tool import consultar_tarifa


def _objeto(resultado: Any, nombre: str) -> dict[str, Any]:
    """Normaliza resultados de .invoke() a un dict, incluso errores JSON."""
    if isinstance(resultado, str):
        try:
            resultado = json.loads(resultado)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{nombre} devolvió texto que no es JSON") from exc
    if not isinstance(resultado, dict) or "estado" not in resultado:
        raise ValueError(f"{nombre} no devolvió el contrato esperado")
    return resultado


def ejecutar_flujo(
    *,
    horas_propuestas: str = "3",
    consumo_hogar_bimestral_kwh: int | None = 350,
    regimen: str = "SIN_SEF",
    fecha: str = "2026-11-15",
) -> dict[str, Any]:
    """Ejecuta tools en secuencia con un caso de prueba de 60 días.

    La salida es didáctica: contiene el registro ordenado de invocaciones,
    la respuesta de cada herramienta y verificaciones entre servicios.

    Si no hay factura no se llama consultar_tarifa (datos insuficientes):
    se conserva la simulación exclusivamente energética.
    """
    actual = {
        "id": "aire_1",
        "nombre": "Aire acondicionado",
        "potencia_watts": "1500",
        "horas_efectivas_por_dia": "5",
        "dias_de_uso": 10,
        "cantidad": 1,
    }
    propuesto = {**actual, "horas_efectivas_por_dia": horas_propuestas}
    periodo_dias = 60
    pasos: list[dict[str, Any]] = []

    args_consumo = {"periodo_dias": periodo_dias, "equipos": [actual]}
    resultado_consumo = _objeto(calcular_consumo.invoke(args_consumo), "calcular_consumo")
    pasos.append({
        "tool": "calcular_consumo",
        "argumentos": args_consumo,
        "resultado_resumen": {
            "estado": resultado_consumo["estado"],
            "consumo_total_kwh": resultado_consumo.get("consumo_total_kwh"),
        },
    })
    if resultado_consumo["estado"] != "ok":
        return {"estado": "error", "codigo": "CONSUMO_INVALIDO", "pasos": pasos}

    resultado_tarifa: dict[str, Any] | None = None
    if consumo_hogar_bimestral_kwh is not None:
        args_tarifa = {
            "distribuidora": "EDEMSA",
            "fecha": fecha,
            "consumo_kwh_bimestral": consumo_hogar_bimestral_kwh,
            "regimen": regimen,
        }
        resultado_tarifa = _objeto(consultar_tarifa.invoke(args_tarifa), "consultar_tarifa")
        pasos.append({
            "tool": "consultar_tarifa",
            "argumentos": args_tarifa,
            "resultado_resumen": {
                "estado": resultado_tarifa["estado"],
                "categoria": resultado_tarifa.get("categoria"),
                "resolucion": resultado_tarifa.get("fuente", {}).get("resolucion")
                if isinstance(resultado_tarifa.get("fuente"), dict) else None,
                "codigo_error": resultado_tarifa.get("codigo"),
            },
        })

    # La herramienta de ahorro recibe la salida REAL e íntegra de la tool
    # tarifaria. Si falla o falta, simula solo energía y explica el motivo.
    args_ahorro = {
        "periodo_dias": periodo_dias,
        "equipos_actuales": [actual],
        "equipos_propuestos": [propuesto],
        "consumo_hogar_bimestral_kwh": consumo_hogar_bimestral_kwh,
        "tarifa_consultada": (
            resultado_tarifa if resultado_tarifa is not None
            and resultado_tarifa["estado"] == "ok" else None
        ),
    }
    resultado_ahorro = _objeto(simular_ahorro.invoke(args_ahorro), "simular_ahorro")
    pasos.append({
        "tool": "simular_ahorro",
        "argumentos": args_ahorro,
        "resultado_resumen": {
            "estado": resultado_ahorro["estado"],
            "ahorro_kwh": resultado_ahorro.get("ahorro_kwh"),
            "estimacion_monetaria_disponible": resultado_ahorro.get("estimacion_monetaria_disponible"),
        },
    })
    if resultado_ahorro["estado"] != "ok":
        return {
            "estado": "error", "codigo": "SIMULACION_INVALIDA",
            "pasos": pasos, "simulacion": resultado_ahorro,
        }

    # Las verificaciones cruzadas detectan incompatibilidades entre tools.
    energia_inicial = Decimal(resultado_consumo["consumo_total_kwh"])
    energia_actual_en_simulacion = Decimal(
        resultado_ahorro["escenario_actual"]["consumo_total_kwh"]
    )
    energia_propuesta = Decimal(
        resultado_ahorro["escenario_propuesto"]["consumo_total_kwh"]
    )
    ahorro = Decimal(resultado_ahorro["ahorro_kwh"])
    if energia_inicial != energia_actual_en_simulacion:
        raise AssertionError("La línea base difiere entre calcular_consumo y simular_ahorro")
    if energia_inicial - energia_propuesta != ahorro:
        raise AssertionError("La diferencia entre escenarios no coincide con ahorro_kwh")
    if consumo_hogar_bimestral_kwh is not None:
        esperado = Decimal(consumo_hogar_bimestral_kwh) - ahorro
        proyectado = resultado_ahorro["consumo_hogar_bimestral_proyectado_kwh"]
        if proyectado is not None and Decimal(proyectado) != esperado:
            raise AssertionError("La proyección bimestral no coincide con el ahorro")
    if resultado_ahorro["estimacion_monetaria_disponible"] and not (
        resultado_tarifa is not None and resultado_tarifa["estado"] == "ok"
    ):
        raise AssertionError("La simulación monetiza sin consulta tarifaria válida")

    return {
        "estado": "ok",
        "pasos": pasos,
        "consumo": resultado_consumo,
        "tarifa": resultado_tarifa,
        "simulacion": resultado_ahorro,
        "verificaciones": {
            "linea_base_coincide": True,
            "ahorro_kwh_coincide": True,
            "proyeccion_coherente": True,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Demostración de integración de tres tools")
    parser.add_argument("--horas-propuestas", default="3", help="Horas de uso alternativas")
    parser.add_argument("--regimen", default="SIN_SEF", choices=("SIN_SEF", "CON_SEF"))
    parser.add_argument("--fecha", default="2026-11-15", help="AAAA-MM-DD")
    parser.add_argument("--sin-factura", action="store_true", help="Ejecutar únicamente simulación energética")
    args = parser.parse_args()
    resultado = ejecutar_flujo(
        horas_propuestas=args.horas_propuestas,
        regimen=args.regimen,
        fecha=args.fecha,
        consumo_hogar_bimestral_kwh=None if args.sin_factura else 350,
    )
    print("EnergiaAI | Etapa 03.4 — integración SIN LLM")
    for numero, paso in enumerate(resultado["pasos"], start=1):
        print(f"\n{numero}. Tool: {paso['tool']}")
        print("   Resumen:", json.dumps(paso["resultado_resumen"], ensure_ascii=False))
    if resultado["estado"] != "ok":
        raise SystemExit("ERROR: la integración no se completó correctamente")
    simulacion = resultado["simulacion"]
    print("\nRESULTADO")
    print(" Consumo actual:", resultado["consumo"]["consumo_total_kwh"], "kWh")
    print(" Ahorro energético:", simulacion["ahorro_kwh"], "kWh")
    print(" Consumo del hogar proyectado:", simulacion["consumo_hogar_bimestral_proyectado_kwh"])
    if simulacion["estimacion_monetaria_disponible"]:
        print(" Diferencia estimada del COMPONENTE VARIABLE (ARS):",
              simulacion["ahorro_componente_variable_estimado_ars"])
    else:
        print(" Sin estimación monetaria:", simulacion["motivo_sin_estimacion_monetaria"])
    print(" Verificaciones cruzadas: OK")
    print(" Nota: NO es una factura ni un agente LLM; las tools fueron invocadas manualmente.")


if __name__ == "__main__":
    main()
