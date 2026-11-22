"""Adaptador LangChain para simular ahorros con datos validados, etapa 03.3."""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

from langchain_core.tools import tool
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from energia_ai.services.consumption import Electrodomestico
from energia_ai.services.savings import simular_ahorro_escenarios


class EquipoEscenarioEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(description="ID estable del electrodoméstico, igual en ambos escenarios")
    nombre: str = Field(description="Nombre del mismo equipo")
    potencia_watts: Decimal = Field(description="Potencia media del equipo en W")
    horas_efectivas_por_dia: Decimal = Field(description="Horas efectivas al día, de 0 a 24")
    dias_de_uso: int = Field(description="Días efectivos dentro del período")
    cantidad: int = Field(default=1, description="Cantidad de equipos idénticos")


class SimulacionAhorroEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid")

    periodo_dias: int = Field(strict=True, ge=1, le=366,
                              description="Mismo período para ambos escenarios, en días")
    equipos_actuales: list[EquipoEscenarioEntrada] = Field(
        description="Lista de equipos y hábitos actuales; usar los IDs del análisis previo"
    )
    equipos_propuestos: list[EquipoEscenarioEntrada] = Field(
        description="Los mismos equipos, modificando solo horas o días de uso"
    )
    consumo_hogar_bimestral_kwh: int | None = Field(
        default=None, ge=0,
        description="kWh facturados del bimestre, no solo de los equipos analizados; "
                    "dejar vacío para simular únicamente energía"
    )
    tarifa_consultada: dict[str, Any] | None = Field(
        default=None,
        description="Respuesta JSON COMPLETA y sin modificar de la tool consultar_tarifa "
                    "para EDEMSA, consumo facturado y SIN_SEF; "
                    "si falta, no se estima un monto en pesos"
    )


def _error_validacion(_: ValidationError) -> str:
    return json.dumps({
        "estado": "error",
        "codigo": "PARAMETROS_INVALIDOS",
        "mensaje": "Revisar lista de equipos, período, consumos no negativos y "
                   "respuesta completa de consultar_tarifa; solicitar datos faltantes.",
    }, ensure_ascii=False)


@tool(args_schema=SimulacionAhorroEntrada)
def simular_ahorro(
    periodo_dias: int,
    equipos_actuales: list[dict[str, Any]],
    equipos_propuestos: list[dict[str, Any]],
    consumo_hogar_bimestral_kwh: int | None = None,
    tarifa_consultada: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compara hábitos de los MISMOS equipos y calcula ahorro energético.

    Para valorar solo la diferencia del cargo variable SIN_SEF, usar el mismo
    período bimestral, su consumo total facturado y la respuesta íntegra de
    consultar_tarifa. No calcula factura completa ni cupos subsidiados.
    """
    try:
        def convertir(items: list[dict[str, Any]]) -> list[Electrodomestico]:
            return [
                Electrodomestico(**(x.model_dump() if isinstance(x, BaseModel) else x))
                for x in items
            ]

        return simular_ahorro_escenarios(
            periodo_dias=periodo_dias,
            equipos_actuales=convertir(equipos_actuales),
            equipos_propuestos=convertir(equipos_propuestos),
            consumo_hogar_bimestral_kwh=consumo_hogar_bimestral_kwh,
            tarifa_consultada=tarifa_consultada,
        )
    except (ValueError, TypeError, KeyError) as exc:
        return {
            "estado": "error", "codigo": "ESCENARIO_INVALIDO", "mensaje": str(exc),
        }


simular_ahorro.handle_validation_error = _error_validacion
