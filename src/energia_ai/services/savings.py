"""Simulación determinística de cambios de hábitos de consumo.

Etapa 03.3. No calcula factura final ni interpreta lenguaje natural.
La parte económica se limita a la diferencia del cargo variable SIN_SEF
cuando la categoría se mantiene estable y la fuente fue verificada.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from energia_ai.data.tariff_catalog import (
    CATALOGO_EDEMSA_221_2026,
    CatalogoTarifario,
)
from energia_ai.services.consumption import Electrodomestico, calcular_consumo_equipos
from energia_ai.services.tariffs import consultar_tarifa_catalogo

_CUATRO = Decimal("0.0001")
_DOS = Decimal("0.01")


def _entero(value: int | None, campo: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{campo}: debe ser un entero no negativo")
    return value


def _comparar_equipos(
    actuales: list[Electrodomestico],
    propuestos: list[Electrodomestico],
) -> None:
    """Restringe el MVP a cambios de hábitos, no a reemplazar equipos."""
    por_id = {equipo.id: equipo for equipo in actuales}
    if len(por_id) != len(actuales):
        raise ValueError("Hay IDs duplicados en el escenario actual")
    nuevos = {equipo.id: equipo for equipo in propuestos}
    if len(nuevos) != len(propuestos) or por_id.keys() != nuevos.keys():
        raise ValueError("Ambos escenarios deben tener exactamente los mismos IDs de equipos")
    for identifier, original in por_id.items():
        nuevo = nuevos[identifier]
        if (original.nombre != nuevo.nombre or
                original.potencia_watts != nuevo.potencia_watts or
                original.cantidad != nuevo.cantidad):
            raise ValueError(
                f"{identifier}: para esta etapa solo se pueden modificar horas o días de uso"
            )


def simular_ahorro_escenarios(
    *,
    periodo_dias: int,
    equipos_actuales: list[Electrodomestico],
    equipos_propuestos: list[Electrodomestico],
    consumo_hogar_bimestral_kwh: int | None = None,
    tarifa_consultada: dict[str, Any] | None = None,
    catalogo: CatalogoTarifario = CATALOGO_EDEMSA_221_2026,
) -> dict[str, Any]:
    """Compara escenarios y calcula ahorro energético (puede ser negativo).

    Si la entrada incluye consumo bimestral del hogar y una salida sin cambios
    de `consultar_tarifa`, estima el delta de cargo variable solo con SIN_SEF,
    catálogo revisado, categoría estable y período de 45 a 75 días. La
    herramienta de tarifas debe consultarse previamente en el flujo del agente.
    """
    _entero(consumo_hogar_bimestral_kwh, "consumo_hogar_bimestral_kwh")
    _comparar_equipos(equipos_actuales, equipos_propuestos)

    actual = calcular_consumo_equipos(periodo_dias=periodo_dias, equipos=equipos_actuales)
    propuesto = calcular_consumo_equipos(periodo_dias=periodo_dias, equipos=equipos_propuestos)
    consumo_actual = Decimal(actual["consumo_total_kwh"])
    consumo_propuesto = Decimal(propuesto["consumo_total_kwh"])
    ahorro = consumo_actual - consumo_propuesto
    porcentaje = (
        (ahorro / consumo_actual * Decimal("100")).quantize(_DOS, rounding=ROUND_HALF_UP)
        if consumo_actual > 0 else None
    )
    advertencias = [
        "Los resultados se basan en potencias y horas efectivas supuestas; no son mediciones.",
        "Un ahorro negativo representa un aumento de consumo.",
        "El resultado económico, cuando exista, NO es el ahorro de la factura completa: "
        "excluye cargos fijos, impuestos, tasas, subsidios y prorrateos.",
    ]
    resultado: dict[str, Any] = {
        "estado": "ok",
        "tipo_resultado": "comparacion_de_escenarios_no_factura",
        "periodo_dias": periodo_dias,
        "escenario_actual": actual,
        "escenario_propuesto": propuesto,
        "ahorro_kwh": str(ahorro.quantize(_CUATRO, rounding=ROUND_HALF_UP)),
        "ahorro_porcentual_equipos": str(porcentaje) if porcentaje is not None else None,
        "consumo_hogar_bimestral_actual_kwh": consumo_hogar_bimestral_kwh,
        "consumo_hogar_bimestral_proyectado_kwh": None,
        "categoria_actual": None,
        "categoria_proyectada": None,
        "estimacion_monetaria_disponible": False,
        "ahorro_componente_variable_estimado_ars": None,
        "motivo_sin_estimacion_monetaria": None,
        "moneda": "ARS",
        "fuente_tarifa": None,
        "advertencias": advertencias,
    }

    def sin_dinero(razon: str) -> dict[str, Any]:
        resultado["motivo_sin_estimacion_monetaria"] = razon
        return resultado

    if consumo_hogar_bimestral_kwh is None or tarifa_consultada is None:
        return sin_dinero(
            "Falta el consumo total facturado del bimestre o la respuesta "
            "completa de consultar_tarifa; solo se informa energía."
        )

    if not 45 <= periodo_dias <= 75:
        return sin_dinero(
            "La estimación monetaria requiere que los escenarios describan "
            "un mismo período bimestral de referencia (45 a 75 días)."
        )

    if consumo_actual > Decimal(consumo_hogar_bimestral_kwh):
        return sin_dinero(
            "El consumo estimado de los equipos supera el consumo total "
            "facturado del hogar; revisar los supuestos."
        )

    proyectado = Decimal(consumo_hogar_bimestral_kwh) - ahorro
    resultado["consumo_hogar_bimestral_proyectado_kwh"] = str(
        proyectado.quantize(_CUATRO, rounding=ROUND_HALF_UP)
    )
    if proyectado < 0:
        return sin_dinero("El consumo total proyectado del hogar sería negativo.")

    if not isinstance(tarifa_consultada, dict):
        return sin_dinero("La respuesta de consultar_tarifa no es un objeto válido.")
    if tarifa_consultada.get("estado") != "ok":
        return sin_dinero("consultar_tarifa no devolvió una tarifa válida.")

    fecha_texto = tarifa_consultada.get("fecha_consultada")
    try:
        fecha = date.fromisoformat(fecha_texto)
    except (TypeError, ValueError):
        return sin_dinero("Fecha ausente o inválida en la respuesta tarifaria.")

    try:
        esperada = consultar_tarifa_catalogo(
            distribuidora="EDEMSA",
            fecha=fecha,
            consumo_kwh_bimestral=consumo_hogar_bimestral_kwh,
            regimen="SIN_SEF",
            catalogo=catalogo,
        )
    except (ValueError, TypeError):
        return sin_dinero("No existe un cuadro EDEMSA aplicable para la referencia recibida.")

    # Comprobamos la integridad de la respuesta anterior, no valores inventados
    # por el LLM ni cálculos con números provenientes del texto libre.
    if tarifa_consultada != esperada:
        return sin_dinero(
            "La respuesta no coincide exactamente con la consulta EDEMSA "
            "SIN_SEF registrada para ese bimestre. Volver a consultar_tarifa."
        )
    resultado["categoria_actual"] = esperada["categoria"]
    resultado["fuente_tarifa"] = esperada["fuente"]
    if not esperada["datos_contrastados_para_informe"]:
        return sin_dinero("El catálogo todavía no figura contrastado con el PDF oficial.")

    # Si queda a menos de 1 kWh del cambio de banda, una regla de redondeo
    # desconocida podría alterar la categoría. Mejor no cuantificar ARS.
    for corte in (Decimal("300"), Decimal("600")):
        if proyectado != corte and abs(proyectado - corte) < Decimal("1"):
            return sin_dinero(
                "El consumo proyectado está cerca del límite tarifario; "
                "sin la regla de redondeo de facturación no se estima dinero."
            )
    categoria_proyectada = catalogo.obtener_banda(
        int(proyectado.quantize(Decimal("1"), rounding=ROUND_HALF_UP)), fecha
    ).codigo
    resultado["categoria_proyectada"] = categoria_proyectada
    if categoria_proyectada != esperada["categoria"]:
        return sin_dinero(
            "La simulación cambia la categoría residencial. No se aplica "
            "automáticamente el precio de una banda a la otra."
        )

    variable = Decimal(esperada["cargos_principales"]["variable_ars_por_kwh"])
    resultado["ahorro_componente_variable_estimado_ars"] = str(
        (ahorro * variable).quantize(_DOS, rounding=ROUND_HALF_UP)
    )
    resultado["estimacion_monetaria_disponible"] = True
    return resultado
