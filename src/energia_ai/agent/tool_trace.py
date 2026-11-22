"""Inspección de llamadas a herramientas sin depender del proveedor del LLM."""
from __future__ import annotations
from typing import Any, Iterable


def resumir_ejecuciones(messages: Iterable[Any]) -> list[dict[str, str]]:
    """Lista mensajes de herramientas efectivamente ejecutadas (ToolMessage).

    No confundir una intención del modelo (AIMessage.tool_calls) con ejecución real.
    """
    ejecuciones: list[dict[str, str]] = []
    for m in messages:
        if type(m).__name__ != "ToolMessage":
            continue
        name = getattr(m, "name", "") or ""
        content = getattr(m, "content", "")
        ejecuciones.append({"tool": str(name), "contenido": str(content)})
    return ejecuciones


def ultimo_mensaje_asistente(messages: Iterable[Any]) -> str:
    ultimo = ""
    for m in messages:
        if type(m).__name__ == "AIMessage":
            content = getattr(m, "content", "")
            if isinstance(content, str) and content.strip():
                ultimo = content
            elif isinstance(content, list):
                partes = [x.get("text", "") for x in content if isinstance(x, dict) and x.get("type") == "text"]
                if partes:
                    ultimo = " ".join(partes)
    return ultimo
