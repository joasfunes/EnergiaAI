"""Tool de LangChain que expone tarifas verificables ya cargadas en memoria.

No navega en internet y no realiza OCR ni cálculo completo de facturas.
La interpretación del mensaje del usuario pertenece al LLM, no a la tool.
"""

from __future__ import annotations

from datetime import date
import json
from typing import Any, Literal

from langchain_core.tools import tool
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from energia_ai.services.tariffs import consultar_tarifa_catalogo


class ConsultaTarifaEntrada(BaseModel):
    """Parámetros estrictos de una consulta bimestral EDEMSA."""

    model_config = ConfigDict(extra="forbid")

    distribuidora: Literal["EDEMSA"] = Field(
        description="Distribuidora residencial admitida: EDEMSA"
    )
    fecha: date = Field(
        description="Fecha de referencia del cuadro tarifario, AAAA-MM-DD"
    )
    consumo_kwh_bimestral: int = Field(
        strict=True,
        ge=0,
        le=100000,
        description="Consumo facturado del BIMESTRE, kWh enteros; no kWh de pocos días",
    )
    regimen: Literal["SIN_SEF", "CON_SEF"] = Field(
        description="Condición de subsidio conocida del usuario; no inventarla"
    )


def _error_validacion(_: ValidationError) -> str:
    """Evita que la validación de Pydantic detenga el ciclo del agente."""
    return json.dumps({
        "estado": "error",
        "codigo": "PARAMETROS_INVALIDOS",
        "mensaje": (
            "Revisar distribuidora (EDEMSA), fecha AAAA-MM-DD, consumo "
            "bimestral entero >= 0 y regimen SIN_SEF/CON_SEF. "
            "Solicitar al usuario cualquier dato faltante."
        ),
    }, ensure_ascii=False)


@tool(args_schema=ConsultaTarifaEntrada)
def consultar_tarifa(
    distribuidora: str,
    fecha: date,
    consumo_kwh_bimestral: int,
    regimen: str,
) -> dict[str, Any]:
    """Consulta cargos residenciales EDEMSA en un catálogo local verificado.

    Úsala antes de simular costos de un hogar con suministro EDEMSA. Requiere
    conocer fecha, kWh BIMESTRALES y condición SIN_SEF/CON_SEF. Si faltan
    datos, pregunta al usuario. No calcula montos finales de facturas.
    """
    try:
        return consultar_tarifa_catalogo(
            distribuidora=distribuidora,
            fecha=fecha,
            consumo_kwh_bimestral=consumo_kwh_bimestral,
            regimen=regimen,
        )
    except (ValueError, TypeError) as exc:
        return {
            "estado": "error",
            "codigo": "TARIFA_NO_DISPONIBLE",
            "mensaje": str(exc),
        }


# También son controlados los errores anteriores a ejecutar la función,
# como campos ausentes, tipos no admitidos o nombres de campo extra.
consultar_tarifa.handle_validation_error = _error_validacion
