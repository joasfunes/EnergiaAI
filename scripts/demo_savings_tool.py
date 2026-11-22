"""Invocación real de la tool, sin pedir decisiones a un LLM."""

from datetime import date
import json

from energia_ai.agent.savings_tool import simular_ahorro
from energia_ai.services.tariffs import consultar_tarifa_catalogo


def main() -> None:
    consulta = consultar_tarifa_catalogo(
        distribuidora="EDEMSA", fecha=date(2026, 11, 15),
        consumo_kwh_bimestral=350, regimen="SIN_SEF",
    )
    actual = {
        "id": "aire_1", "nombre": "Aire acondicionado", "potencia_watts": "1500",
        "horas_efectivas_por_dia": "5", "dias_de_uso": 10, "cantidad": 1,
    }
    propuesto = {**actual, "horas_efectivas_por_dia": "3"}
    r = simular_ahorro.invoke({
        "periodo_dias": 60,
        "equipos_actuales": [actual],
        "equipos_propuestos": [propuesto],
        "consumo_hogar_bimestral_kwh": 350,
        "tarifa_consultada": consulta,
    })
    print("Tool:", simular_ahorro.name)
    print(json.dumps(r, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
