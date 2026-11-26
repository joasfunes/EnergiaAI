"""Streaming simple compatible con stream(..., stream_mode=['messages','updates']).

No registra el contenido íntegro de herramientas en logs: solo nombre y estado.
"""
from __future__ import annotations

import json
from typing import Any, Callable

from energia_ai.agent.session import configuracion_thread


def texto_del_chunk(message: Any) -> str:
    """Extrae solo el texto visible; no publica tool_call_chunks ni razonamiento."""
    content = getattr(message, "content", None)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(part.get("text", "") for part in content
                       if isinstance(part, dict) and part.get("type") == "text"
                       and isinstance(part.get("text"), str))
    return ""


def razonamiento_del_chunk(message: Any) -> str:
    """Devuelve SOLAMENTE el delta de razonamiento expuesto por el proveedor.

    ChatOllama con reasoning=True coloca el razonamiento separado en
    additional_kwargs['reasoning_content']. Algunas versiones de LangChain
    lo exponen también en content_blocks. Priorizamos el primero para
    evitar duplicados. No reconstruimos ni inventamos razonamiento.
    """
    extra = getattr(message, "additional_kwargs", None)
    if isinstance(extra, dict):
        exposed = extra.get("reasoning_content")
        if isinstance(exposed, str) and exposed:
            return exposed
    blocks = getattr(message, "content_blocks", None)
    if isinstance(blocks, list):
        return "".join(
            part.get("reasoning", part.get("text", ""))
            for part in blocks
            if isinstance(part, dict) and part.get("type") == "reasoning"
            and isinstance(part.get("reasoning", part.get("text", "")), str)
        )
    # Formato de contenido estructurado utilizado por algunos adaptadores.
    content = getattr(message, "content", None)
    if isinstance(content, list):
        return "".join(
            part.get("reasoning", part.get("text", ""))
            for part in content
            if isinstance(part, dict) and part.get("type") == "reasoning"
            and isinstance(part.get("reasoning", part.get("text", "")), str)
        )
    return ""


def eventos_de_actualizacion(update: dict[str, Any]) -> list[dict[str, str]]:
    """Detecta ToolMessage de una actualización 'tools', sin exponer datos privados."""
    resultado = []
    for nodo, data in update.items():
        if nodo != "tools" or not isinstance(data, dict):
            continue
        for msg in data.get("messages", []):
            if getattr(msg, "type", None) != "tool":
                continue
            contenido = getattr(msg, "content", "")
            try:
                decoded = json.loads(contenido) if isinstance(contenido, str) else None
            except (ValueError, TypeError):
                decoded = None
            estado = decoded.get("estado") if isinstance(decoded, dict) else None
            resultado.append({"tipo": "tool", "nombre": getattr(msg, "name", "desconocida"),
                              "estado": estado or "desconocido"})
    return resultado


def transmitir_turno(agente: Any, *, consulta: str, thread_id: str,
                     notificar: Callable[[dict[str, Any]], None],
                     callbacks: list[Any] | None = None) -> None:
    if not isinstance(consulta, str) or not consulta.strip():
        raise ValueError("La consulta no puede estar vacía")
    if not callable(notificar):
        raise TypeError("notificar debe ser una función")
    config = configuracion_thread(thread_id)
    if callbacks is not None:
        config["callbacks"] = callbacks
    # Se fija expresamente v1 para interpretar sus tuplas (modo, dato).
    for modo, payload in agente.stream(
        {"messages": [{"role": "user", "content": consulta.strip()}]},
        config=config, stream_mode=["messages", "updates"], version="v1",
    ):
        if modo == "messages":
            if not isinstance(payload, tuple) or len(payload) != 2:
                continue
            msg, _metadata = payload
            # Tool-call y thinking chunks no deben confundirse con texto para el usuario.
            if getattr(msg, "type", "") not in {"AIMessageChunk", "ai"}:
                continue
            # No confundir el canal de thinking con la respuesta al usuario.
            reasoning = razonamiento_del_chunk(msg)
            if reasoning:
                notificar({"tipo": "razonamiento", "texto": reasoning})
            text = texto_del_chunk(msg)
            if text:
                notificar({"tipo": "texto", "texto": text})
        elif modo == "updates" and isinstance(payload, dict):
            # La solicitud de herramienta es distinta de su ejecución confirmada.
            from energia_ai.ui.presentation import solicitudes_en_update
            for evento in solicitudes_en_update(payload):
                notificar(evento)
            for evento in eventos_de_actualizacion(payload):
                notificar(evento)
    notificar({"tipo": "fin"})
