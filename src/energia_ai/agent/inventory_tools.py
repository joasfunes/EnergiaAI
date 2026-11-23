"""Herramientas con acceso a un hogar fijado por aplicación (NO por el LLM)."""
from __future__ import annotations
from typing import Any

from energia_ai.services.home_inventory import InventarioHogar, validar_hogar_id


def crear_tools_inventario(repositorio: InventarioHogar, hogar_id: str) -> tuple[Any, Any]:
    """Genera herramientas vinculadas a un hogar para este agente/sesión."""
    from langchain_core.tools import tool

    validar_hogar_id(hogar_id)

    @tool
    def registrar_electrodomestico(
        id: str, nombre: str, potencia_watts: str,
        horas_efectivas_por_dia: str, dias_de_uso: int, cantidad: int = 1
    ) -> dict[str, Any]:
        """Registra un equipo nuevo SOLO si el usuario lo pidió expresamente y proporcionó sus datos.

        Potencia en W y horas efectivas diarias como números decimales expresados en texto.
        Si faltan datos, primero solicitarlos. No reemplaza equipos existentes.
        """
        try:
            return repositorio.registrar_equipo(
                hogar_id, id=id, nombre=nombre, potencia_watts=potencia_watts,
                horas_efectivas_por_dia=horas_efectivas_por_dia,
                dias_de_uso=dias_de_uso, cantidad=cantidad,
            )
        except ValueError as exc:
            return {"estado": "error", "codigo": "DATOS_INVALIDOS", "mensaje": str(exc)}

    @tool
    def consultar_inventario() -> dict[str, Any]:
        """Recupera equipos y período del hogar activo guardados en SQLite.

        Usar cuando el usuario pregunte por equipos anteriores o quiera calcular
        un total incluyendo electrodomésticos guardados.
        """
        return repositorio.consultar(hogar_id)

    return registrar_electrodomestico, consultar_inventario
