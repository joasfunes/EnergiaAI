"""Motor puro de consumo eléctrico. Etapa 03.1.

No accede a tarifas, Internet, archivos ni LLM. Usa potencia constante y
horas **efectivas** de uso, no simplemente horas conectado/enchufado.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import re
from typing import Any

_KWH_PRECISION = Decimal("0.0001")
_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,32}$")
_MAX_APPLIANCES = 30


def _decimal(value: Decimal | int | float | str, field: str) -> Decimal:
    """Convierte números JSON a Decimal sin operaciones de float."""
    if isinstance(value, bool) or not isinstance(value, (Decimal, int, float, str)):
        raise ValueError(f"{field}: se requiere un valor numérico")
    if isinstance(value, str) and not value.strip():
        raise ValueError(f"{field}: no puede quedar vacío")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError(f"{field}: número inválido") from None
    if not result.is_finite():
        raise ValueError(f"{field}: debe ser finito")
    return result


def _positive_integer(value: int, field: str, *, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field}: debe ser un entero")
    if not minimum <= value <= maximum:
        raise ValueError(f"{field}: debe estar entre {minimum} y {maximum}")
    return value


@dataclass(frozen=True, slots=True)
class Electrodomestico:
    """Descripción de un equipo para un período de análisis.

    potencia_watts: potencia media constante usada como hipótesis.
    horas_efectivas_por_dia: horas de trabajo a esa potencia (0 a 24).
    dias_de_uso: días de utilización dentro del período estudiado.
    """

    id: str
    nombre: str
    potencia_watts: Decimal
    horas_efectivas_por_dia: Decimal
    dias_de_uso: int
    cantidad: int = 1

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not _ID_PATTERN.fullmatch(self.id):
            raise ValueError("id: use 1 a 32 letras ASCII, números, _ o -")
        if not isinstance(self.nombre, str) or not 1 <= len(self.nombre.strip()) <= 100:
            raise ValueError("nombre: debe contener de 1 a 100 caracteres")
        potencia = _decimal(self.potencia_watts, "potencia_watts")
        horas = _decimal(self.horas_efectivas_por_dia, "horas_efectivas_por_dia")
        if not Decimal("0") < potencia <= Decimal("20000"):
            raise ValueError("potencia_watts: debe estar entre 0 (exclusivo) y 20000 W")
        if not Decimal("0") <= horas <= Decimal("24"):
            raise ValueError("horas_efectivas_por_dia: debe estar entre 0 y 24")
        _positive_integer(self.dias_de_uso, "dias_de_uso", minimum=0, maximum=366)
        _positive_integer(self.cantidad, "cantidad", minimum=1, maximum=30)
        object.__setattr__(self, "potencia_watts", potencia)
        object.__setattr__(self, "horas_efectivas_por_dia", horas)
        object.__setattr__(self, "nombre", self.nombre.strip())


def calcular_consumo_equipos(
    *, periodo_dias: int, equipos: list[Electrodomestico]
) -> dict[str, Any]:
    """Calcula consumos en kWh. No consulta tarifas ni estima costos.

    E[kWh] = cantidad × potencia[W] / 1000 × horas_efectivas_por_dia × dias_de_uso.
    Redondea solo para mostrar, conservando precisión en la suma.
    """
    _positive_integer(periodo_dias, "periodo_dias", minimum=1, maximum=366)
    if not isinstance(equipos, list) or not 1 <= len(equipos) <= _MAX_APPLIANCES:
        raise ValueError(f"equipos: se requieren entre 1 y {_MAX_APPLIANCES} equipos")

    ids: set[str] = set()
    resultados = []
    total = Decimal("0")
    for equipo in equipos:
        if not isinstance(equipo, Electrodomestico):
            raise ValueError("equipos: todos deben ser objetos Electrodomestico")
        if equipo.id in ids:
            raise ValueError(f"id duplicado: {equipo.id}")
        ids.add(equipo.id)
        if equipo.dias_de_uso > periodo_dias:
            raise ValueError(f"{equipo.id}: dias_de_uso supera periodo_dias")
        kwh = (
            Decimal(equipo.cantidad) * equipo.potencia_watts
            * equipo.horas_efectivas_por_dia * Decimal(equipo.dias_de_uso)
            / Decimal("1000")
        )
        total += kwh
        resultados.append({
            "id": equipo.id,
            "nombre": equipo.nombre,
            "cantidad": equipo.cantidad,
            "consumo_kwh": str(kwh.quantize(_KWH_PRECISION, rounding=ROUND_HALF_UP)),
        })
    return {
        "estado": "ok",
        "periodo_dias": periodo_dias,
        "consumo_total_kwh": str(total.quantize(_KWH_PRECISION, rounding=ROUND_HALF_UP)),
        "equipos": resultados,
        "metodo": "potencia_constante_estimada",
        "advertencias": [
            "Estimación: la potencia real puede variar; use mediciones o etiquetas cuando existan.",
            "Las horas informadas son horas efectivas de trabajo, no necesariamente horas enchufado.",
            "No se calculó costo monetario ni importe de factura.",
        ],
    }
