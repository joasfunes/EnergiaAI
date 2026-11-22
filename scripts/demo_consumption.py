"""Demostración local sin red, LLM ni tarifas. Etapa 03.1."""

from decimal import Decimal
from energia_ai.services.consumption import Electrodomestico, calcular_consumo_equipos


def main() -> None:
    equipos = [
        Electrodomestico(
            id="aire_1", nombre="Aire acondicionado (potencia constante supuesta)",
            potencia_watts=Decimal("1500"), horas_efectivas_por_dia=Decimal("4"),
            dias_de_uso=20,
        ),
        Electrodomestico(
            id="tv_1", nombre="Televisor",
            potencia_watts=Decimal("100"), horas_efectivas_por_dia=Decimal("5"),
            dias_de_uso=20,
        ),
    ]
    resultado = calcular_consumo_equipos(periodo_dias=30, equipos=equipos)
    for equipo in resultado["equipos"]:
        print(f"{equipo['nombre']}: {equipo['consumo_kwh']} kWh")
    print("Total:", resultado["consumo_total_kwh"], "kWh")
    print("No se calculó un importe de factura.")


if __name__ == "__main__":
    main()
