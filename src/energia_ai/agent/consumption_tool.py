"""Adaptador LangChain de la función determinística de consumo.

La tool NO interpreta mensajes: el LLM extrae los campos y llama esta función.
Requiere requirements-tools.txt; NO crea todavía un agente create_agent.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from langchain_core.tools import tool
from pydantic import BaseModel, ConfigDict, Field

from energia_ai.services.consumption import Electrodomestico, calcular_consumo_equipos


class EquipoEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(description="Identificador estable, ej. aire_1")
    nombre: str = Field(description="Nombre del aparato")
    potencia_watts: Decimal = Field(description="Potencia en watts, mayor que cero")
    horas_efectivas_por_dia: Decimal = Field(
        description="Horas a esa potencia por día, entre 0 y 24"
    )
    dias_de_uso: int = Field(description="Cantidad de días de uso durante el período")
    cantidad: int = Field(default=1, description="Cantidad de equipos idénticos")


class CalculoConsumoEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid")

    periodo_dias: int = Field(description="Duración del período analizado en días")
    equipos: list[EquipoEntrada] = Field(description="Uno o más equipos con datos completos")


@tool(args_schema=CalculoConsumoEntrada)
def calcular_consumo(periodo_dias: int, equipos: list[dict[str, Any]]) -> dict[str, Any]:
    """Calcula consumo energético por electrodoméstico y total (kWh).

    Úsala cuando se conozcan potencia, horas efectivas y días de uso.
    No obtiene tarifas ni calcula facturas. Solicita datos faltantes antes de usarla.
    """
    try:
        convertidos = []
        for item in equipos:
            datos = item.model_dump() if isinstance(item, BaseModel) else item
            convertidos.append(Electrodomestico(**datos))
        return calcular_consumo_equipos(periodo_dias=periodo_dias, equipos=convertidos)
    except (ValueError, TypeError, KeyError) as exc:
        return {
            "estado": "error",
            "codigo": "DATOS_INVALIDOS",
            "mensaje": str(exc),
        }
