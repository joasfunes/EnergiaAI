"""Demostración de una tool LangChain sin modelo de lenguaje."""

from json import dumps

from energia_ai.agent.tariff_tool import consultar_tarifa


def main() -> None:
    resultado = consultar_tarifa.invoke({
        "distribuidora": "EDEMSA",
        "fecha": "2026-11-15",
        "consumo_kwh_bimestral": 350,
        "regimen": "SIN_SEF",
    })
    print("Tool LangChain:", consultar_tarifa.name)
    print(dumps(resultado, ensure_ascii=False, indent=2))
    print("AVISO: no se calculó una factura ni se aplicó el SEF.")


if __name__ == "__main__":
    main()
