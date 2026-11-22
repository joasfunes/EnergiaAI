"""Demostración del servicio Python puro: sin LLM ni LangChain."""

from datetime import date
from json import dumps

from energia_ai.services.tariffs import consultar_tarifa_catalogo


def main() -> None:
    resultado = consultar_tarifa_catalogo(
        distribuidora="EDEMSA",
        fecha=date(2026, 11, 15),
        consumo_kwh_bimestral=350,
        regimen="SIN_SEF",
    )
    print("Servicio Python puro: consultar_tarifa_catalogo")
    print(dumps(resultado, ensure_ascii=False, indent=2))
    print("AVISO: consulta de cargos, no total de factura.")


if __name__ == "__main__":
    main()
