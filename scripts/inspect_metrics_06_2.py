"""Inspección opcional de la medición de la subetapa 06.1."""
from energia_ai.ui.presentation import cargar_medicion_06_1


if __name__ == "__main__":
    resultado = cargar_medicion_06_1("data/processed/performance/medicion_06_1.json")
    if resultado is None:
        print("No se encontró medicion_06_1.json. No se inventan métricas.")
    else:
        for campo, valor in resultado.items():
            print(f"{campo}: {valor if valor is not None else 'no medido'}")
        print("Los tiempos corresponden a un turno de prueba, no a un promedio de usuarios.")
