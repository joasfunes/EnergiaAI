"""Muestra las tarifas cargadas en memoria, sin generar facturas."""

from datetime import date
from energia_ai.data.tariff_catalog import CATALOGO_EDEMSA_221_2026


def main() -> None:
    catalogo = CATALOGO_EDEMSA_221_2026
    print(f"Catálogo: {catalogo.distribuidora} | {catalogo.resolucion}")
    print(f"Fuente: {catalogo.fuente_url}")
    print(f"Estado: {catalogo.estado_revision}")
    print(f"Cobertura del MVP: {catalogo.cobertura_desde} a {catalogo.cobertura_hasta}")
    print("Cargos SIN SEF (únicamente consulta de valores):")
    for banda in catalogo.bandas:
        a = banda.sin_sef
        print(f"  {banda.codigo}: fijo ${a.fijo_por_bimestre_ars}/bim; "
              f"variable ${a.variable_por_kwh_ars}/kWh")
    ejemplo = catalogo.obtener_banda(350, date(2026, 11, 15))
    print(f"Ejemplo: 350 kWh/bim corresponde a {ejemplo.codigo}.")
    print("NO se está calculando el importe final de una factura.")


if __name__ == "__main__":
    main()
