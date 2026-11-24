"""Auditoría determinística de aceptación (06.4), separada del LLM."""
from .acceptance import auditar_ultimo_turno, verificar_preparacion, verificar_informe

__all__ = ["auditar_ultimo_turno", "verificar_preparacion", "verificar_informe"]
