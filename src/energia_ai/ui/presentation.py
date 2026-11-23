"""Conversión segura de estados y trazas para la UI local."""
from __future__ import annotations
from pathlib import Path
from typing import Any
import json
import math

from energia_ai.agent.streaming import texto_del_chunk

# Campos limitados. Nunca incluir credenciales, hogar_id, thread_id ni rutas.
_SCALARS = {"id", "nombre", "potencia_watts", "horas_efectivas_por_dia", "dias_de_uso",
    "periodo_dias", "cantidad", "fecha", "regimen", "distribuidora",
    "consumo_kwh_bimestral", "consumo_hogar_bimestral_kwh", "max_resultados",
    "estado", "categoria", "categoria_actual", "categoria_proyectada",
    "consumo_total_kwh", "ahorro_kwh", "cantidad_equipos",
    "estimacion_monetaria_disponible", "ahorro_componente_variable_estimado_ars"}
_LISTAS = {"equipos", "equipos_actuales", "equipos_propuestos"}


def _cortar(texto: str, limite: int = 160) -> str:
    return texto[:limite] + ("…" if len(texto) > limite else "")


def argumentos_para_ui(nombre: str, argumentos: Any) -> dict[str, Any]:
    """Vista local de los argumentos REALES solicitados, sin identificadores secretos.

    No persistir el resultado en archivos de telemetría.
    """
    if not isinstance(nombre, str) or not isinstance(argumentos, dict):
        return {}
    if nombre not in {"calcular_consumo", "consultar_tarifa", "simular_ahorro",
                      "buscar_consejos", "registrar_electrodomestico", "consultar_inventario"}:
        return {}
    salida: dict[str, Any] = {}
    for clave, valor in argumentos.items():
        if clave in _SCALARS:
            if isinstance(valor, bool):
                salida[clave] = valor
            elif isinstance(valor, (int, float)) and math.isfinite(valor):
                salida[clave] = valor
            elif isinstance(valor, str):
                salida[clave] = _cortar(valor)
        elif clave == "consulta" and nombre == "buscar_consejos" and isinstance(valor, str):
            salida[clave] = _cortar(valor, 180)
        elif clave in _LISTAS and isinstance(valor, list):
            salida[clave] = [{k: _cortar(v) if isinstance(v, str) else v
                for k, v in elem.items() if k in _SCALARS and
                (isinstance(v, (str, bool, int)) or (isinstance(v, float) and math.isfinite(v)))}
                for elem in valor[:12] if isinstance(elem, dict)]
        elif clave == "tarifa_consultada" and isinstance(valor, dict):
            salida[clave] = {k: v for k, v in valor.items() if k in _SCALARS
                and isinstance(v, (str, int, float, bool))}
    return salida


def solicitudes_en_update(update: dict[str, Any]) -> list[dict[str, Any]]:
    """Extrae tool_calls solicitados por la IA (no los confunde con ejecutados)."""
    if not isinstance(update, dict):
        return []
    eventos = []
    for nodo, payload in update.items():
        if nodo == "tools" or not isinstance(payload, dict):
            continue
        for mensaje in payload.get("messages", []):
            if getattr(mensaje, "type", None) not in {"ai", "AIMessage"}:
                continue
            for solicitud in getattr(mensaje, "tool_calls", []) or []:
                if not isinstance(solicitud, dict):
                    continue
                nombre = solicitud.get("name", "")
                if not isinstance(nombre, str) or not nombre:
                    continue
                eventos.append({"tipo": "tool_solicitada", "nombre": nombre,
                    "argumentos": argumentos_para_ui(nombre, solicitud.get("args", {}))})
    return eventos


def historial_visible(agente: Any, thread_id: str) -> list[dict[str, str]]:
    """Carga conversación desde el checkpointer; omite tool calls internos y ToolMessages."""
    from energia_ai.agent.session import configuracion_thread
    estado = agente.get_state(configuracion_thread(thread_id))
    valores = getattr(estado, "values", None)
    mensajes = valores.get("messages", []) if isinstance(valores, dict) else []
    salida = []
    for mensaje in mensajes:
        role = getattr(mensaje, "type", None)
        if role in {"human", "HumanMessage"}:
            rol = "user"
        elif role in {"ai", "AIMessage"}:
            # Mensajes intermedios con tool_calls no son respuestas finales al usuario.
            if getattr(mensaje, "tool_calls", None):
                continue
            rol = "assistant"
        else:
            continue
        texto = texto_del_chunk(mensaje)
        if texto.strip():
            salida.append({"role": rol, "content": texto})
    return salida


def cargar_medicion_06_1(ruta: str | Path) -> dict[str, Any] | None:
    path = Path(ruta)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    def num(campo: str) -> float | None:
        x = data.get(campo)
        if isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) and x >= 0:
            return round(float(x), 2)
        return None
    return {"duracion_total_s": num("duracion_total_s"),
            "duracion_modelo_observada_s": num("duracion_modelo_observada_s"),
            "tiempo_primera_salida_s": num("tiempo_primera_salida_s"),
            "llamadas_modelo": data.get("llamadas_modelo") if isinstance(data.get("llamadas_modelo"), int) else None}
