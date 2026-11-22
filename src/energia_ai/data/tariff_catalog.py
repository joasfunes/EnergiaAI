"""Catálogo de consulta en memoria: EPRE 221/2026, Anexo I, T1 residencial.

Los valores se transcribieron del cuadro oficial. El catálogo NO factura:
- Los valores son cargos por bimestre o por kWh, según su unidad.
- Los regímenes SEF y su cupo requieren lógica de aplicación separada.
- Impuestos, tasas, ajustes, prorrateos y demás conceptos no están incluidos.

Antes de usar las tarifas en un informe económico, contrastar manualmente las
filas con el PDF descargado del EPRE. Ver docs/ETAPA_02_2.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

SOURCE_URL = (
    "https://epremendoza.gob.ar/2019/resoluciones-anexos/Res%20221-2026.pdf"
)


def dec(value: str) -> Decimal:
    """Convierte un decimal explícito sin utilizar números float."""
    return Decimal(value)


@dataclass(frozen=True, slots=True)
class Cargos:
    fijo_por_bimestre_ars: Decimal
    variable_por_kwh_ars: Decimal

    def __post_init__(self) -> None:
        for value in (self.fijo_por_bimestre_ars, self.variable_por_kwh_ars):
            if not value.is_finite() or value < 0:
                raise ValueError("Los importes deben ser finitos y no negativos")


@dataclass(frozen=True, slots=True)
class BandaResidencial:
    codigo: str
    kwh_desde_inclusive: int
    kwh_hasta_inclusive: int | None
    sin_sef: Cargos
    con_sef_o_base: Cargos
    con_sef_excedente: Cargos | None

    def __post_init__(self) -> None:
        if self.kwh_desde_inclusive < 0:
            raise ValueError("El límite inferior de consumo debe ser >= 0")
        if (self.kwh_hasta_inclusive is not None and
                self.kwh_hasta_inclusive < self.kwh_desde_inclusive):
            raise ValueError("El límite superior debe ser >= al inferior")

    def contiene(self, kwh_bimestrales: int) -> bool:
        return (kwh_bimestrales >= self.kwh_desde_inclusive and
                (self.kwh_hasta_inclusive is None or
                 kwh_bimestrales <= self.kwh_hasta_inclusive))


@dataclass(frozen=True, slots=True)
class CatalogoTarifario:
    distribuidora: str
    resolucion: str
    anexo: str
    fuente_url: str
    cobertura_desde: date
    cobertura_hasta: date
    bandas: tuple[BandaResidencial, ...]
    estado_revision: str
    facturacion_minima_kwh_bimestral: int
    nota_sef: str

    def __post_init__(self) -> None:
        if self.cobertura_desde > self.cobertura_hasta:
            raise ValueError("Rango de fechas invertido")
        if not self.fuente_url.startswith("https://epremendoza.gob.ar/"):
            raise ValueError("Se requiere la fuente oficial del EPRE")
        if not self.bandas:
            raise ValueError("El catálogo necesita al menos una categoría")
        ordenadas = sorted(self.bandas, key=lambda x: x.kwh_desde_inclusive)
        siguiente_inicio = 0
        for index, banda in enumerate(ordenadas):
            if banda.kwh_desde_inclusive != siguiente_inicio:
                raise ValueError("Hay un hueco o solapamiento entre categorías")
            if banda.kwh_hasta_inclusive is None:
                if index != len(ordenadas) - 1:
                    raise ValueError("La categoría sin límite superior debe ser la última")
            else:
                siguiente_inicio = banda.kwh_hasta_inclusive + 1
        if ordenadas[-1].kwh_hasta_inclusive is not None:
            raise ValueError("Falta la banda final sin límite superior")

    def obtener_banda(self, consumo_kwh_bimestral: int, fecha: date) -> BandaResidencial:
        """Selecciona la banda; no calcula el importe de una factura.

        El consumo facturado para esta clasificación debe ser entero en kWh.
        """
        if isinstance(consumo_kwh_bimestral, bool) or not isinstance(consumo_kwh_bimestral, int):
            raise TypeError("El consumo facturado debe ser un entero en kWh")
        if consumo_kwh_bimestral < 0:
            raise ValueError("El consumo no puede ser negativo")
        if not isinstance(fecha, date) or isinstance(fecha, datetime):
            raise TypeError("La fecha debe ser datetime.date")
        if not self.cobertura_desde <= fecha <= self.cobertura_hasta:
            raise ValueError("No hay cobertura tarifaria verificada para la fecha")
        for banda in self.bandas:
            if banda.contiene(consumo_kwh_bimestral):
                return banda
        raise ValueError("No se encontró categoría de consumo")


def cargos(fijo: str, variable: str) -> Cargos:
    return Cargos(dec(fijo), dec(variable))


# Se cargan una única vez al importar el módulo (no se lee CSV ni PDF aquí).
CATALOGO_EDEMSA_221_2026 = CatalogoTarifario(
    distribuidora="EDEMSA",
    resolucion="EPRE 221/2026",
    anexo="I - T1 residencial, pequeñas demandas hasta 10 kW",
    fuente_url=SOURCE_URL,
    cobertura_desde=date(2026, 11, 1),
    # Ventana de cobertura del MVP, NO aseveración de vigencia jurídica
    # inmutable: debe revisarse ante nuevas resoluciones.
    cobertura_hasta=date(2027, 1, 31),
    estado_revision="CONTRASTADO_CON_PDF_LOCAL",
    facturacion_minima_kwh_bimestral=45,
    nota_sef=(
        "Anexo I: noviembre, base SEF de 400 kWh/bimestre; "
        "diciembre y enero, 600 kWh/bimestre. "
        "La aplicación de estos bloques aún NO está implementada."
    ),
    bandas=(
        BandaResidencial(
            codigo="R1", kwh_desde_inclusive=0, kwh_hasta_inclusive=299,
            sin_sef=cargos("8526.621", "297.8234"),
            con_sef_o_base=cargos("7893.019", "182.8933"),
            con_sef_excedente=None,
        ),
        BandaResidencial(
            codigo="R2", kwh_desde_inclusive=300, kwh_hasta_inclusive=599,
            sin_sef=cargos("9299.861", "289.4315"),
            con_sef_o_base=cargos("7640.151", "182.3271"),
            con_sef_excedente=cargos("9299.861", "289.4315"),
        ),
        BandaResidencial(
            codigo="R3", kwh_desde_inclusive=600, kwh_hasta_inclusive=None,
            sin_sef=cargos("54659.736", "259.3782"),
            con_sef_o_base=cargos("41234.213", "165.1047"),
            con_sef_excedente=cargos("54659.736", "259.3782"),
        ),
    ),
)
