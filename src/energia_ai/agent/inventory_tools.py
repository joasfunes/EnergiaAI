"""Tool de lectura: los cambios del inventario se realizan en Streamlit."""
from __future__ import annotations
from typing import Any

from energia_ai.services.home_inventory import InventarioHogar, validar_hogar_id


def crear_tools_inventario(repositorio: InventarioHogar, hogar_id: str) -> tuple[Any, ...]:
    """Solo lectura para Qwen; el hogar se fija en el backend."""
    from langchain_core.tools import tool

    validar_hogar_id(hogar_id)

    @tool
    def consultar_inventario() -> dict[str, Any]:
        """Recupera equipos y período del hogar activo guardados en SQLite.

        Usar antes de responder acerca de los electrodomésticos registrados.
        Para agregar, editar o eliminar equipos, derivar al editor de Streamlit.
        """
        return repositorio.consultar(hogar_id)

    return (consultar_inventario,)
