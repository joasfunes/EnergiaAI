"""Audita mensajes del último turno PERSISTENTE sin llamar al LLM.

Ejemplo:
python scripts/auditar_conversacion_06_4.py --hogar-id casa_demo --thread-id chat_abc --exigir simular_ahorro buscar_consejos
No registra el texto del usuario, prompts ni identidades en archivos.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from energia_ai.agent.persistent_runtime import abrir_runtime_persistente
from energia_ai.agent.session import configuracion_thread
from energia_ai.quality import auditar_ultimo_turno
from energia_ai.ui.conversations import IndiceConversaciones
from energia_ai.reporting.extraction import InformeNoDisponible, extraer_ultimo_analisis


def main() -> None:
    parser = argparse.ArgumentParser(description="Auditar una conversación existente SIN consultar Qwen")
    parser.add_argument("--hogar-id", required=True)
    parser.add_argument("--thread-id", required=True)
    parser.add_argument("--exigir", nargs="*", default=[])
    parser.add_argument("--carpeta-estado", default="data/state")
    args = parser.parse_args()
    raiz = Path(args.carpeta_estado)
    # Control antes de abrir el checkpoint; no confundirlo con autenticación.
    IndiceConversaciones(raiz / "conversaciones_ui.sqlite3").comprobar(args.hogar_id, args.thread_id)
    with abrir_runtime_persistente(hogar_id=args.hogar_id, carpeta_estado=raiz) as runtime:
        estado = runtime.agente.get_state(configuracion_thread(args.thread_id))
        mensajes = (getattr(estado, "values", {}) or {}).get("messages", [])
    salida = {"traza_ultimo_turno": auditar_ultimo_turno(mensajes, requeridas=args.exigir)}
    try:
        analisis = extraer_ultimo_analisis(mensajes)
    except InformeNoDisponible:
        salida["informe_disponible"] = False
    else:
        salida["informe_disponible"] = True
        salida["informe_ahorro_kwh"] = analisis["ahorro_kwh"]
        salida["informe_fuentes"] = len(analisis["evidencias_rag"])
    print(json.dumps(salida, ensure_ascii=False, indent=2))
    # No serializar ni prompts, ni mensajes, ni IDs a un archivo.
    if salida["traza_ultimo_turno"]["estado"] != "ok":
        raise SystemExit(1)

if __name__ == "__main__":
    main()
