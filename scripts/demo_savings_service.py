"""Demuestra la simulación SIN usar LangChain ni un LLM."""

from dataclasses import replace
from datetime import date
from decimal import Decimal

from energia_ai.data.tariff_catalog import CATALOGO_EDEMSA_221_2026
from energia_ai.services.consumption import Electrodomestico
from energia_ai.services.savings import simular_ahorro_escenarios
from energia_ai.services.tariffs import consultar_tarifa_catalogo


def main() -> None:
    # En el repositorio del alumno, después del contraste manual de 02.2,
    # estado_revision ya debe ser CONTRASTADO_CON_PDF_LOCAL.
    catalogo = CATALOGO_EDEMSA_221_2026
    fecha = date(2026, 11, 15)
    consulta = consultar_tarifa_catalogo(
        distribuidora="EDEMSA", fecha=fecha,
        consumo_kwh_bimestral=350, regimen="SIN_SEF", catalogo=catalogo,
    )
    actual = Electrodomestico(
        id="aire_1", nombre="Aire acondicionado", potencia_watts=Decimal("1500"),
        horas_efectivas_por_dia=Decimal("5"), dias_de_uso=10,
    )
    propuesto = replace(actual, horas_efectivas_por_dia=Decimal("3"))
    resultado = simular_ahorro_escenarios(
        periodo_dias=60, equipos_actuales=[actual], equipos_propuestos=[propuesto],
        consumo_hogar_bimestral_kwh=350, tarifa_consultada=consulta, catalogo=catalogo,
    )
    print("Simulación EnergiaAI (servicio Python)")
    print("Consumo anterior del equipo:", resultado["escenario_actual"]["consumo_total_kwh"], "kWh")
    print("Consumo propuesto del equipo:", resultado["escenario_propuesto"]["consumo_total_kwh"], "kWh")
    print("Ahorro energético:", resultado["ahorro_kwh"], "kWh")
    print("Ahorro porcentual de los equipos:", resultado["ahorro_porcentual_equipos"], "%")
    print("Ahorro en componente variable (ARS):", resultado["ahorro_componente_variable_estimado_ars"])
    print("Estimación monetaria disponible:", resultado["estimacion_monetaria_disponible"])
    if resultado["motivo_sin_estimacion_monetaria"]:
        print("Motivo:", resultado["motivo_sin_estimacion_monetaria"])
    print("NO es el importe de una factura completa")


if __name__ == "__main__":
    main()
