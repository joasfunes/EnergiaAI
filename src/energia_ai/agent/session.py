"""Utilidades de sesión y trazabilidad para la demo 05.2 (sin inferencia)."""
from __future__ import annotations

import json
import re
from typing import Any

from energia_ai.agent.tool_trace import ultimo_mensaje_asistente, resumir_ejecuciones

_THREAD_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,79}$")


def configuracion_thread(thread_id: str, *, recursion_limit: int = 24) -> dict[str, Any]:
    """Mantiene un thread estable para varios turnos del mismo proceso."""
    if not isinstance(thread_id, str) or not _THREAD_RE.fullmatch(thread_id):
        raise ValueError("thread_id debe tener de 1 a 80 caracteres alfanuméricos, _ o -")
    if (isinstance(recursion_limit, bool) or not isinstance(recursion_limit, int)
            or recursion_limit < 8 or recursion_limit > 80):
        raise ValueError("recursion_limit debe ser un entero entre 8 y 80")
    return {"configurable": {"thread_id": thread_id}, "recursion_limit": recursion_limit}


def _mensajes_anteriores(agente: Any, config: dict[str, Any]) -> int:
    """Obtiene longitud del estado previo para evitar duplicar tools en turnos posteriores."""
    state = agente.get_state(config)
    if state is None:
        return 0
    values = getattr(state, "values", None)
    if not isinstance(values, dict):
        return 0
    msgs = values.get("messages", [])
    return len(msgs) if isinstance(msgs, list) else 0


def analizar_ejecuciones(ejecuciones: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Clasifica ejecución real por `estado`, sin confundir tool solicitada y ejecutada."""
    validas: list[dict[str, Any]] = []
    for event in ejecuciones:
        content = event.get("contenido", "")
        try:
            parsed = json.loads(content)
        except (json.JSONDecodeError, TypeError):
            parsed = None
        estado = parsed.get("estado") if isinstance(parsed, dict) else None
        validas.append({"tool": event.get("tool", ""), "estado": estado or "desconocido",
                        "contenido": content})
    return validas


def ejecutar_turno(agente: Any, *, consulta: str, thread_id: str) -> dict[str, Any]:
    """Invoca el agente y devuelve SOLO los ToolMessage del turno actual."""
    if not isinstance(consulta, str) or not consulta.strip():
        raise ValueError("La consulta no puede estar vacía")
    config = configuracion_thread(thread_id)
    previos = _mensajes_anteriores(agente, config)
    salida = agente.invoke(
        {"messages": [{"role": "user", "content": consulta.strip()}]},
        config=config,
    )
    mensajes = salida.get("messages", [])
    if not isinstance(mensajes, list):
        raise RuntimeError("El agente no devolvió una lista de mensajes")
    if len(mensajes) < previos:
        # Algunos middlewares compactan mensajes; en ese caso, no atribuir ejecuciones
        # anteriores al turno nuevo.
        raise RuntimeError("La cantidad de mensajes disminuyó: revisar compactación del estado")
    nuevos = mensajes[previos:]
    return {
        "thread_id": thread_id,
        "respuesta": ultimo_mensaje_asistente(nuevos) or ultimo_mensaje_asistente(mensajes),
        "ejecuciones": analizar_ejecuciones(resumir_ejecuciones(nuevos)),
    }


def tools_ejecutadas(turno: dict[str, Any]) -> set[str]:
    return {event.get("tool", "") for event in turno.get("ejecuciones", [])}
