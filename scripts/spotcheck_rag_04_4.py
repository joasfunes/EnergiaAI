"""Preguntas nuevas para inspección rápida de 04.4; NO forman parte del baseline."""
from __future__ import annotations
from energia_ai.agent.advice_tool import buscar_consejos

PREGUNTAS = (
    '¿Qué puedo hacer si la heladera abre y cierra muchas veces?',
    '¿Cómo usar luminarias LED de forma eficiente?',
    '¿Cómo disminuir pérdidas de calor por aberturas en un día frío?',
    '¿Qué hacer con el aire acondicionado durante el verano en Mendoza?',
    '¿Cuál es la capital de Nepal?',
    '¿Cómo compilar un programa en Rust?',
    '¿Quién ganó la final del Mundial de fútbol 2014?',
    '¿Cómo cambiar la contraseña del Wi-Fi?',
)


def main() -> None:
    print('Inspección adicional (4 consultas de energía + 4 fuera de dominio)')
    for question in PREGUNTAS:
        result = buscar_consejos.invoke({'consulta': question, 'max_resultados': 3})
        first = result.get('resultados', [{}])
        best = first[0] if first else {}
        print(f'\nPregunta: {question}\n'
              f'Estado: {result.get("estado")} | Resultados: {result.get("cantidad_resultados", 0)} '
              f'| Primer origen: {best.get("fuente_id", "sin evidencia")}')
    print('\nEstas son comprobaciones manuales adicionales, no una prueba estadística.')


if __name__ == '__main__':
    main()
