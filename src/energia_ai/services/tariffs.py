"""Consulta determinística de tarifas EDEMSA T1 residenciales en memoria.

No descarga archivos, no accede a CSV/PDF, no simula subsidios, no factura.
Reutiliza el catálogo ya creado en la Etapa 02.2.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from energia_ai.data.tariff_catalog import (
    CATALOGO_EDEMSA_221_2026,
    CatalogoTarifario,
    Cargos,
)

REGIMENES = frozenset({"SIN_SEF", "CON_SEF"})
ESTADO_REVISADO = "CONTRASTADO_CON_PDF_LOCAL"


def _serializar_cargos(cargos: Cargos | None) -> dict[str, str] | None:
    """Devuelve importes como texto para preservar sus decimales exactos."""
    if cargos is None:
        return None
    return {
        "fijo_ars_por_bimestre": str(cargos.fijo_por_bimestre_ars),
        "variable_ars_por_kwh": str(cargos.variable_por_kwh_ars),
    }


def consultar_tarifa_catalogo(
    *,
    distribuidora: str,
    fecha: date,
    consumo_kwh_bimestral: int,
    regimen: str,
    catalogo: CatalogoTarifario = CATALOGO_EDEMSA_221_2026,
) -> dict[str, Any]:
    """Selecciona una categoría y muestra los cargos del cuadro en RAM.

    Devuelve datos estructurados; nunca el total monetario de una factura.
    El consumo debe corresponder al período *bimestral* utilizado por el
    cuadro EPRE y no a cualquier intervalo de días.
    """
    if not isinstance(distribuidora, str) or distribuidora != catalogo.distribuidora:
        raise ValueError("Distribuidora no disponible: el MVP solo admite EDEMSA")
    if not isinstance(fecha, date) or isinstance(fecha, datetime):
        raise ValueError("fecha debe ser de tipo date (AAAA-MM-DD)")
    if isinstance(consumo_kwh_bimestral, bool) or not isinstance(consumo_kwh_bimestral, int):
        raise ValueError("consumo_kwh_bimestral debe ser un entero")
    if consumo_kwh_bimestral < 0:
        raise ValueError("consumo_kwh_bimestral no puede ser negativo")
    if not isinstance(regimen, str) or regimen not in REGIMENES:
        raise ValueError("regimen debe ser SIN_SEF o CON_SEF, sin asumir subsidios")

    # Reutilizamos la validación de vigencia y categorías ya testeada en 02.2.
    banda = catalogo.obtener_banda(consumo_kwh_bimestral, fecha)
    confirmado = catalogo.estado_revision == ESTADO_REVISADO

    if regimen == "SIN_SEF":
        principal = banda.sin_sef
        excedente = None
    else:
        principal = banda.con_sef_o_base
        excedente = banda.con_sef_excedente

    advertencias = [
        "Consulta de cargos: NO calcula importe final de factura ni impuestos, tasas o prorrateos.",
        "El consumo introducido debe representar kWh bimestrales comparables con el cuadro.",
    ]
    if regimen == "CON_SEF":
        advertencias.append(
            "Se muestran los cargos de base y excedente publicados, pero NO se "
            "determina el cupo subsidiado ni se distribuye el consumo entre bloques."
        )
        if excedente is None:
            advertencias.append(
                "El catálogo no incluye una columna de excedente separada para esta categoría; "
                "no se interpreta su ausencia como costo cero."
            )
    if not confirmado:
        advertencias.append(
            "El estado del catálogo sigue sin confirmar en código: revisar el PDF "
            "antes de presentar estimaciones económicas."
        )

    return {
        "estado": "ok",
        "tipo_resultado": "consulta_de_cargos_no_factura",
        "distribuidora": catalogo.distribuidora,
        "fecha_consultada": fecha.isoformat(),
        "consumo_kwh_bimestral": consumo_kwh_bimestral,
        "categoria": banda.codigo,
        "categoria_kwh_desde": banda.kwh_desde_inclusive,
        "categoria_kwh_hasta": banda.kwh_hasta_inclusive,
        "regimen": regimen,
        "cargos_principales": _serializar_cargos(principal),
        "cargos_excedente": _serializar_cargos(excedente),
        "fuente": {
            "organismo": "EPRE Mendoza",
            "resolucion": catalogo.resolucion,
            "anexo": catalogo.anexo,
            "url": catalogo.fuente_url,
            "cobertura_desde": catalogo.cobertura_desde.isoformat(),
            "cobertura_hasta": catalogo.cobertura_hasta.isoformat(),
            "estado_revision": catalogo.estado_revision,
        },
        "datos_contrastados_para_informe": confirmado,
        "nota_sef": catalogo.nota_sef if regimen == "CON_SEF" else None,
        "advertencias": advertencias,
    }
