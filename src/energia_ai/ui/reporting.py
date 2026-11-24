"""Exportación de informe desde historial persistente, sin volver a ejecutar Qwen."""
from __future__ import annotations
from typing import Any
from energia_ai.agent.persistent_runtime import abrir_runtime_persistente
from energia_ai.reporting.extraction import extraer_desde_agente
from energia_ai.reporting.pdf_report import generar_informe_pdf


def preparar_pdf_conversacion(*, hogar_id: str, thread_id: str,
                               carpeta_estado: str = 'data/state') -> tuple[bytes, dict[str, Any]]:
    """Aislamiento por hogar+thread debe verificarse en la UI con IndiceConversaciones."""
    with abrir_runtime_persistente(hogar_id=hogar_id, carpeta_estado=carpeta_estado) as runtime:
        analisis = extraer_desde_agente(runtime.agente, thread_id)
    return generar_informe_pdf(analisis), analisis
