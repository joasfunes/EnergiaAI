"""Observabilidad local 06.1: latencia, tools y eventos resumidos sin guardar prompts.

La traza del usuario solo contiene nombres, argumentos numéricos permitidos,
resúmenes estructurados, estados y duraciones. No guarda respuestas del LLM,
identificadores de hogares, nombres de equipos, consultas libres ni rutas privadas.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass, field
from collections import Counter
from datetime import datetime, timezone
import json
import re
from threading import Lock
from time import perf_counter
from typing import Any, Callable

from energia_ai.agent.streaming import transmitir_turno

# Lista cerrada de campos que pueden mostrarse en una traza local académica.
_CAMPOS_PUBLICOS = frozenset({
    "potencia_watts", "periodo_dias", "horas_efectivas_por_dia", "dias_de_uso",
    "cantidad", "fecha", "regimen", "distribuidora", "consumo_kwh_bimestral",
    "consumo_hogar_bimestral_kwh", "max_resultados", "estado", "codigo",
    "accion", "cantidad_equipos", "consumo_total_kwh", "ahorro_kwh",
    "estimacion_monetaria_disponible", "categoria", "categoria_actual",
    "categoria_proyectada", "ahorro_componente_variable_estimado_ars",
})


_NUMERICOS = frozenset({
    "potencia_watts", "periodo_dias", "horas_efectivas_por_dia", "dias_de_uso",
    "cantidad", "consumo_kwh_bimestral", "consumo_hogar_bimestral_kwh",
    "max_resultados", "cantidad_equipos", "consumo_total_kwh", "ahorro_kwh",
    "ahorro_componente_variable_estimado_ars"
})
_ENUMERACIONES = {
    "estado": frozenset({"ok", "error", "sin_resultados", "sin_equipos"}),
    "regimen": frozenset({"CON_SEF", "SIN_SEF"}),
    "distribuidora": frozenset({"EDEMSA"}),
    "accion": frozenset({"registrado"}),
    "categoria": frozenset({"R1", "R2", "R3"}),
    "categoria_actual": frozenset({"R1", "R2", "R3"}),
    "categoria_proyectada": frozenset({"R1", "R2", "R3"}),
}


def _diccionario(obj: Any) -> dict[str, Any]:
    """Convierte un objeto JSON/dict si es posible; nunca ejecuta instrucciones."""
    if isinstance(obj, dict):
        return obj
    content = getattr(obj, "content", obj)
    if isinstance(content, dict):
        return content
    if isinstance(content, str):
        try:
            decoded = json.loads(content)
        except (TypeError, ValueError):
            try:
                decoded = ast.literal_eval(content)
            except (ValueError, SyntaxError, MemoryError, RecursionError):
                return {}
        if isinstance(decoded, dict):
            return decoded
    return {}


def resumen_permitido(obj: Any) -> dict[str, str | bool | int | float]:
    """Solo claves numéricas/estados definidos; no copiar texto libre a trazas."""
    res = {}
    for key, value in _diccionario(obj).items():
        if key not in _CAMPOS_PUBLICOS or isinstance(value, (dict, list, tuple)):
            continue
        if key == "estimacion_monetaria_disponible":
            if isinstance(value, bool):
                res[key] = value
        elif key in _NUMERICOS:
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                res[key] = value
            elif isinstance(value, str) and re.fullmatch(r"-?\d+(?:\.\d+)?", value):
                res[key] = value
        elif key in _ENUMERACIONES:
            if isinstance(value, str) and value in _ENUMERACIONES[key]:
                res[key] = value
        elif key == "fecha" and isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            res[key] = value
        elif key == "codigo" and isinstance(value, str) and re.fullmatch(r"[A-Z_]{1,32}", value):
            res[key] = value
    return res


@dataclass
class _Ejecucion:
    nombre: str
    inicio: float
    argumentos: dict[str, Any] = field(default_factory=dict)


class RegistroRendimiento:
    """Almacén efímero y thread-safe de trazas de un solo turno."""

    def __init__(self, *, reloj: Callable[[], float] = perf_counter,
                 emitir: Callable[[dict[str, Any]], None] | None = None):
        self._reloj = reloj
        self._inicio = reloj()
        self._emitir = emitir
        self._lock = Lock()
        self._tools_activas: dict[str, _Ejecucion] = {}
        self._modelos_activos: dict[str, float] = {}
        self._herramientas: list[dict[str, Any]] = []
        self._observadas_update: list[dict[str, Any]] = []
        self._modelos: list[dict[str, Any]] = []
        self._primera_salida: float | None = None
        self._fin: float | None = None
        self._error: str | None = None
        self.iniciado_utc = datetime.now(timezone.utc).isoformat()

    def observar_tool_stream(self, nombre: str, estado: str) -> None:
        """Evidencia de ToolMessage aunque el backend no emita callbacks temporizados."""
        with self._lock:
            self._observadas_update.append({"nombre": nombre, "estado": estado})

    def marcar_primer_texto(self) -> None:
        with self._lock:
            if self._primera_salida is None:
                self._primera_salida = self._reloj() - self._inicio

    def iniciar_modelo(self, run_id: Any) -> None:
        with self._lock:
            self._modelos_activos[str(run_id)] = self._reloj()

    def terminar_modelo(self, run_id: Any, *, error: bool = False) -> None:
        with self._lock:
            inicio = self._modelos_activos.pop(str(run_id), None)
            if inicio is None:
                return
            self._modelos.append({"duracion_s": round(self._reloj() - inicio, 3),
                                  "estado": "error" if error else "ok"})

    def iniciar_tool(self, run_id: Any, nombre: str, argumentos: Any = None) -> None:
        evento = {"tipo": "tool_inicio", "nombre": nombre,
                  "argumentos": resumen_permitido(argumentos)}
        with self._lock:
            self._tools_activas[str(run_id)] = _Ejecucion(
                nombre=nombre, inicio=self._reloj(), argumentos=evento["argumentos"])
        self._enviar(evento)

    def terminar_tool(self, run_id: Any, resultado: Any = None, *, error: bool = False) -> None:
        with self._lock:
            previo = self._tools_activas.pop(str(run_id), None)
            if previo is None:
                return
            resumen = resumen_permitido(resultado)
            estado = "error" if error else str(resumen.get("estado", "desconocido"))
            dato = {"nombre": previo.nombre, "duracion_s": round(self._reloj() - previo.inicio, 3),
                    "estado": estado, "argumentos": previo.argumentos, "resultado": resumen}
            self._herramientas.append(dato)
        self._enviar({"tipo": "tool_fin", **dato})

    def finalizar(self, error: Exception | None = None) -> None:
        with self._lock:
            if self._fin is None:
                self._fin = self._reloj()
            if error is not None:
                self._error = type(error).__name__  # Nunca guardar el mensaje de error sin depurar.

    def resumen(self) -> dict[str, Any]:
        with self._lock:
            fin = self._fin if self._fin is not None else self._reloj()
            terminadas = list(self._herramientas)
            cuentas = Counter(x["nombre"] for x in terminadas)
            # La actualización del nodo 'tools' prueba ejecución real incluso si
            # el runtime no propagó callbacks de tiempo de herramienta.
            for evento in self._observadas_update:
                if cuentas[evento["nombre"]]:
                    cuentas[evento["nombre"]] -= 1
                else:
                    terminadas.append({"nombre": evento["nombre"], "estado": evento["estado"],
                                      "duracion_s": None, "argumentos": {}, "resultado": {},
                                      "origen": "stream_updates_sin_tiempo"})
            return {
                "schema_version": "06.1.1", "iniciado_utc": self.iniciado_utc,
                "duracion_total_s": round(fin - self._inicio, 3),
                "tiempo_primera_salida_s": (round(self._primera_salida, 3)
                                              if self._primera_salida is not None else None),
                "llamadas_modelo": len(self._modelos),
                "duracion_modelo_observada_s": round(sum(x["duracion_s"] for x in self._modelos), 3),
                "modelos": list(self._modelos), "herramientas": terminadas,
                "estado": "error" if self._error else "ok",
                "tipo_error": self._error,
                "advertencia": "Tiempos medidos en el proceso cliente, no telemetría interna de Ollama. "
                               "La suma de las duraciones puede solaparse si hay herramientas paralelas."
            }

    def _enviar(self, evento: dict[str, Any]) -> None:
        if self._emitir is not None:
            self._emitir(evento)


def crear_callback_rendimiento(registro: RegistroRendimiento) -> Any:
    """Construye un handler LangChain auténtico al ejecutar; no se importa en tests unitarios."""
    from langchain_core.callbacks import BaseCallbackHandler

    class _Handler(BaseCallbackHandler):
        def on_chat_model_start(self, serialized: dict[str, Any], messages: Any,
                                *, run_id: Any, **kwargs: Any) -> None:
            registro.iniciar_modelo(run_id)

        def on_llm_end(self, response: Any, *, run_id: Any, **kwargs: Any) -> None:
            registro.terminar_modelo(run_id)

        def on_llm_error(self, error: Exception, *, run_id: Any, **kwargs: Any) -> None:
            registro.terminar_modelo(run_id, error=True)

        def on_tool_start(self, serialized: dict[str, Any], input_str: str,
                          *, run_id: Any, **kwargs: Any) -> None:
            nombre = str(serialized.get("name", "desconocida"))
            argumentos = kwargs.get("inputs", input_str)
            registro.iniciar_tool(run_id, nombre, argumentos)

        def on_tool_end(self, output: Any, *, run_id: Any, **kwargs: Any) -> None:
            registro.terminar_tool(run_id, output)

        def on_tool_error(self, error: Exception, *, run_id: Any, **kwargs: Any) -> None:
            registro.terminar_tool(run_id, {"estado": "error"}, error=True)

    return _Handler()


def ejecutar_turno_medido(agente: Any, *, consulta: str, thread_id: str,
                          notificar: Callable[[dict[str, Any]], None]) -> dict[str, Any]:
    """Un turno real con streaming+callbacks; devuelve solo telemetría anonimizada."""
    registro = RegistroRendimiento(emitir=notificar)
    handler = crear_callback_rendimiento(registro)

    def _notificacion(evento: dict[str, Any]) -> None:
        if evento.get("tipo") == "texto" and evento.get("texto", "").strip():
            registro.marcar_primer_texto()
        elif evento.get("tipo") == "tool":
            registro.observar_tool_stream(str(evento.get("nombre", "desconocida")),
                                         str(evento.get("estado", "desconocido")))
        notificar(evento)

    try:
        transmitir_turno(agente, consulta=consulta, thread_id=thread_id,
                         notificar=_notificacion, callbacks=[handler])
    except Exception as exc:
        registro.finalizar(error=exc)
        raise
    registro.finalizar()
    return registro.resumen()
