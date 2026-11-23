"""Puente Streamlit/agente: el trabajador nunca invoca métodos de Streamlit.

El contexto de SqliteSaver se abre y cierra dentro del mismo hilo del turno.
"""
from __future__ import annotations
from queue import Queue
from threading import Thread
from typing import Any, Iterator

from energia_ai.agent.persistent_runtime import abrir_runtime_persistente
from energia_ai.agent.telemetry import ejecutar_turno_medido
from energia_ai.ui.presentation import historial_visible


def recuperar_historial(*, hogar_id: str, thread_id: str, carpeta_estado: str = "data/state") -> list[dict[str, str]]:
    with abrir_runtime_persistente(hogar_id=hogar_id, carpeta_estado=carpeta_estado) as runtime:
        return historial_visible(runtime.agente, thread_id)


def ejecutar_stream_ui(*, hogar_id: str, thread_id: str, consulta: str,
                       carpeta_estado: str = "data/state") -> Iterator[tuple[str, Any]]:
    """Produce eventos en tiempo real sin tocar Streamlit desde threads de LangChain.

    Advertencia de prototipo: detener bruscamente la pestaña NO cancela las tools.
    """
    if not isinstance(consulta, str) or not consulta.strip():
        raise ValueError("Consulta vacía")
    cola: Queue[tuple[str, Any]] = Queue()

    def worker() -> None:
        try:
            with abrir_runtime_persistente(hogar_id=hogar_id, carpeta_estado=carpeta_estado) as runtime:
                resumen = ejecutar_turno_medido(runtime.agente, consulta=consulta,
                    thread_id=thread_id, notificar=lambda e: cola.put(("evento", e)))
                cola.put(("resumen", resumen))
        except Exception as exc:
            # No enviar mensajes crudos: podrían contener la consulta o credenciales.
            cola.put(("error", type(exc).__name__))
        finally:
            cola.put(("fin_worker", None))

    hilo = Thread(target=worker, name="energiaai-turno-ui", daemon=True)
    hilo.start()
    while True:
        tipo, payload = cola.get()
        if tipo == "fin_worker":
            break
        yield tipo, payload
    hilo.join()
