"""Diagnóstico local y de solo lectura del último turno LangGraph de EnergiaAI.

No invoca a Qwen, no muestra prompts ni razonamientos, no guarda en archivos.
Solo muestra metadatos técnicos y, OPCIONALMENTE, el texto final ya existente.

Desde la raíz de EnergiaAI:
 python scripts/diagnosticar_ultimo_turno_07.py --hogar-id casa_demo --thread-id chat_...
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

SAFE_METADATA = (
    "done_reason", "finish_reason", "prompt_eval_count", "eval_count",
    "total_duration", "load_duration", "prompt_eval_duration", "eval_duration",
)


def _texto_visible(mensaje: Any) -> str:
    contenido = getattr(mensaje, "content", "")
    if isinstance(contenido, str):
        return contenido
    if isinstance(contenido, list):
        return "".join(
            parte.get("text", "")
            for parte in contenido
            if isinstance(parte, dict) and parte.get("type") == "text"
            and isinstance(parte.get("text"), str)
        )
    return ""


def analizar_mensajes(mensajes: list[Any]) -> tuple[dict[str, Any], str]:
    """Función pura: no revela contenidos, hogares ni IDs de herramientas arbitrarios."""
    if not isinstance(mensajes, list):
        raise ValueError("Estado inválido: messages no es una lista")
    ultimo_humano = None
    for indice, msg in enumerate(mensajes):
        if getattr(msg, "type", None) in {"human", "HumanMessage"}:
            ultimo_humano = indice
    if ultimo_humano is None:
        return {"estado": "sin_turno", "mensajes_totales": len(mensajes)}, ""

    turno = mensajes[ultimo_humano + 1:]
    solicitudes = []
    ejecuciones = []
    generaciones = []
    texto_final = ""
    for msg in turno:
        tipo = getattr(msg, "type", None)
        if tipo in {"ai", "AIMessage", "AIMessageChunk"}:
            calls = getattr(msg, "tool_calls", None) or []
            nombres = [c.get("name", "desconocida") for c in calls if isinstance(c, dict)]
            solicitudes.extend(nombres)
            texto = _texto_visible(msg)
            metadata = getattr(msg, "response_metadata", None) or {}
            if not isinstance(metadata, dict):
                metadata = {}
            meta = {
                clave: metadata[clave]
                for clave in SAFE_METADATA
                if clave in metadata and isinstance(metadata[clave], (str, int, float))
                and not isinstance(metadata[clave], bool)
            }
            extra = getattr(msg, "additional_kwargs", None) or {}
            thinking = extra.get("reasoning_content", "") if isinstance(extra, dict) else ""
            info = {
                "tiene_tool_calls": bool(nombres),
                "cantidad_tool_calls": len(nombres),
                "caracteres_texto_visible": len(texto),
                "caracteres_razonamiento_expuesto": len(thinking) if isinstance(thinking, str) else None,
                "metadata": meta,
            }
            generaciones.append(info)
            if not nombres:
                texto_final = texto
        elif tipo in {"tool", "ToolMessage"}:
            nombre = getattr(msg, "name", None)
            ejecuciones.append(nombre if isinstance(nombre, str) and nombre else "desconocida")

    ultima = generaciones[-1] if generaciones else {}
    ultimo_motivo = ultima.get("metadata", {}).get("done_reason") or ultima.get("metadata", {}).get("finish_reason")
    estado = "sin_respuesta_final" if not texto_final.strip() else (
        "limite_de_generacion_reportado" if ultimo_motivo == "length" else "respuesta_con_texto"
    )
    reporte = {
        "estado": estado,
        "mensaje": (
            "El proveedor reportó done_reason=length; puede haberse agotado el límite de generación."
            if ultimo_motivo == "length" else
            "done_reason=stop no prueba que la respuesta esté completa; comparar con Streamlit."
            if ultimo_motivo == "stop" else
            "No hay motivo de finalización disponible; comparar el texto guardado con Streamlit."
        ),
        "mensajes_totales_en_checkpointer": len(mensajes),
        "mensajes_posteriores_al_ultimo_usuario": len(turno),
        "tools_solicitadas_en_el_turno": solicitudes,
        "tools_ejecutadas_en_el_turno": ejecuciones,
        "generaciones_modelo": generaciones,
        "respuesta_final_guardada_caracteres": len(texto_final),
    }
    return reporte, texto_final


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspecta el último turno de una conversación; no ejecuta Qwen")
    parser.add_argument("--hogar-id", required=True, help="Hogar seleccionado en Streamlit")
    parser.add_argument("--thread-id", required=True, help="ID completo mostrado en la barra lateral")
    parser.add_argument("--carpeta-estado", default="data/state")
    parser.add_argument("--mostrar-final", action="store_true", help="Imprime también el texto del último mensaje localmente")
    args = parser.parse_args()

    try:
        # Diferimos imports y reutilizamos las comprobaciones reales del sistema.
        from energia_ai.agent.persistent_runtime import abrir_runtime_persistente
        from energia_ai.agent.session import configuracion_thread
        from energia_ai.ui.conversations import IndiceConversaciones

        carpeta = Path(args.carpeta_estado)
        IndiceConversaciones(carpeta / "conversaciones_ui.sqlite3").comprobar(args.hogar_id, args.thread_id)
        with abrir_runtime_persistente(hogar_id=args.hogar_id, carpeta_estado=carpeta) as runtime:
            estado = runtime.agente.get_state(configuracion_thread(args.thread_id))
            valores = getattr(estado, "values", None)
            mensajes = valores.get("messages", []) if isinstance(valores, dict) else []
            reporte, final = analizar_mensajes(mensajes)
        print(json.dumps(reporte, indent=2, ensure_ascii=False))
        if args.mostrar_final:
            print("\n--- TEXTO FINAL DEL CHECKPOINTER (SOLO TERMINAL LOCAL) ---")
            print(final or "[No existe texto final]")
        return 0
    except Exception as exc:
        print(f"No se pudo inspeccionar el turno ({type(exc).__name__}). "
              "Verificá hogar, thread, dependencias y que el proceso tenga acceso a SQLite.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
