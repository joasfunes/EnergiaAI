"""Invocación de la tool LangChain SIN LLM (requiere requirements-tools.txt)."""

from energia_ai.agent.consumption_tool import calcular_consumo


def main() -> None:
    result = calcular_consumo.invoke({
        "periodo_dias": 30,
        "equipos": [
            {"id": "tv_1", "nombre": "Televisor", "potencia_watts": 100,
             "horas_efectivas_por_dia": 5, "dias_de_uso": 20, "cantidad": 1}
        ],
    })
    print("Tool:", calcular_consumo.name)
    print("Respuesta:", result)


if __name__ == "__main__":
    main()
