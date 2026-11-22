"""Evaluación reproducible de recuperación RAG, sin LLM evaluador ni CSV.

Las fuentes esperadas son *hipótesis de evaluación*, no una verdad semántica
suficiente: la pertinencia se revisa manualmente sobre los fragmentos.
No construye embeddings de documentos ni modifica el índice Chroma.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import math
from typing import Any, Callable, Iterable

from energia_ai.rag.corpus import SOURCES

SCHEMA_VERSION = "04.3.1"
_SOURCE_URLS = {source.id: source.official_url for source in SOURCES}


@dataclass(frozen=True)
class EvaluationCase:
    id: str
    consulta: str
    fuente_esperada: str | None
    tipo: str = "dominio"

    def __post_init__(self) -> None:
        if self.tipo not in {"dominio", "fuera_de_dominio"}:
            raise ValueError("Tipo de evaluación desconocido")
        if not self.id or not 1 <= len(self.consulta.strip()) <= 2000:
            raise ValueError("Caso de evaluación inválido")
        if self.tipo == "dominio" and self.fuente_esperada not in _SOURCE_URLS:
            raise ValueError("Se necesita una fuente oficial esperada")
        if self.tipo == "fuera_de_dominio" and self.fuente_esperada is not None:
            raise ValueError("Un caso fuera del dominio no debe tener fuente esperada")


CASES: tuple[EvaluationCase, ...] = (
    EvaluationCase("INV-01", "¿Cómo puedo evitar la pérdida de calor por puertas y ventanas durante el invierno?", "EPRE-INV-2022"),
    EvaluationCase("INV-02", "¿Qué consejos hay para utilizar la calefacción eléctrica en invierno en Mendoza?", "EPRE-INV-2022"),
    EvaluationCase("INV-03", "¿Por qué conviene moderar el uso de caloventores?", "EPRE-INV-2022"),
    EvaluationCase("VER-01", "¿Cómo utilizar el aire acondicionado eficientemente durante una ola de calor?", "EPRE-VER-2025"),
    EvaluationCase("VER-02", "¿Qué hábitos conviene cambiar para consumir menos electricidad con la heladera durante el verano?", "EPRE-VER-2025"),
    EvaluationCase("VER-03", "¿Cómo reducir el consumo de electricidad durante los días de mucho calor en Mendoza?", "EPRE-VER-2025"),
    EvaluationCase("NAC-01", "¿Qué recomendaciones de iluminación eficiente hay para una vivienda?", "ARG-RES-2024"),
    EvaluationCase("NAC-02", "¿Cómo mejorar la eficiencia energética de una vivienda mediante su aislamiento?", "ARG-RES-2024"),
    EvaluationCase("OOD-01", "¿Quién ganó un torneo internacional de ajedrez en 1990?", None, "fuera_de_dominio"),
    EvaluationCase("OOD-02", "¿Cómo configurar una impresora inalámbrica?", None, "fuera_de_dominio"),
)


def _revision_fragmento(texto: str) -> list[str]:
    """Señales heurísticas de fragmentación (no confirman un error)."""
    limpio = texto.strip().strip('"“«(')
    senales: list[str] = []
    if limpio and limpio[0].islower():
        senales.append("posible_inicio_cortado")
    if limpio and limpio[-1] not in '.!?;:…»”\"':
        senales.append("posible_final_cortado")
    return senales


def _resultado(item: dict[str, Any], posicion: int) -> dict[str, Any]:
    fuente_id = item.get("fuente_id")
    if fuente_id not in _SOURCE_URLS or item.get("url") != _SOURCE_URLS[fuente_id]:
        raise ValueError("La herramienta entregó una fuente fuera del catálogo")
    texto = item.get("texto")
    if not isinstance(texto, str) or not texto.strip():
        raise ValueError("Fragmento vacío o inválido")
    distancia = item.get("distancia_vectorial")
    try:
        distancia_valida = float(distancia)
    except (ValueError, TypeError, OverflowError) as exc:
        raise ValueError("Distancia no numérica") from exc
    if not math.isfinite(distancia_valida) or distancia_valida < 0:
        raise ValueError("Distancia vectorial inválida")
    return {
        "posicion": posicion,
        "fuente_id": fuente_id,
        "url": item["url"],
        "pagina": item.get("pagina"),
        "cita": item.get("cita", ""),
        "distancia_vectorial": distancia_valida,
        "texto": texto,
        "senales_chunking": _revision_fragmento(texto),
        "relevancia_manual": None,        # 0=no pertinente; 1=contexto; 2=util
        "cita_verificada_manual": None,    # true/false tras comprobar fuente original
        "fragmento_completo_manual": None, # true/false tras revisar cortes
        "observaciones": "",
    }


def evaluar_casos(
    casos: Iterable[EvaluationCase],
    invocar_tool: Callable[[str, int], dict[str, Any]],
    *,
    k: int = 3,
) -> dict[str, Any]:
    """Evalúa la tool real (o un fake inyectado) y conserva revisión editable."""
    if isinstance(k, bool) or not isinstance(k, int) or not 1 <= k <= 5:
        raise ValueError("k debe estar entre 1 y 5")
    filas: list[dict[str, Any]] = []
    vistos: set[str] = set()
    for caso in casos:
        if caso.id in vistos:
            raise ValueError("Hay IDs de casos duplicados")
        vistos.add(caso.id)
        try:
            salida = invocar_tool(caso.consulta, k)
            if not isinstance(salida, dict):
                raise ValueError("La tool no devolvió un diccionario")
            estado = salida.get("estado", "error")
            lista = salida.get("resultados", [])
            if not isinstance(lista, list) or len(lista) > k:
                raise ValueError("Número o formato de resultados inválido")
            resultados = [_resultado(item, pos) for pos, item in enumerate(lista, 1)]
            advertencias = salida.get("advertencias", [])
            if not isinstance(advertencias, list):
                advertencias = ["Advertencias en formato inesperado"]
        except (ValueError, TypeError, KeyError, OSError, RuntimeError):
            estado, resultados = "error", []
            advertencias = ["Error controlado al recuperar o validar la evidencia. Revisar la ejecución."]
        if estado != "ok":
            resultados = []
        rank = next((i for i, r in enumerate(resultados, 1)
                     if r["fuente_id"] == caso.fuente_esperada), None)
        filas.append({
            "id": caso.id,
            "tipo": caso.tipo,
            "consulta": caso.consulta,
            "fuente_esperada": caso.fuente_esperada,
            "estado": estado,
            "rango_primera_fuente_esperada": rank if caso.tipo == "dominio" else None,
            "resultados": resultados,
            "advertencias": advertencias,
        })
    return {
        "schema_version": SCHEMA_VERSION,
        "generado_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "k": k,
        "descripcion": "Evaluación del recuperador, sin LLM. La fuente esperada no equivale a relevancia.",
        "casos": filas,
    }


def metricas_automaticas(reporte: dict[str, Any]) -> dict[str, Any]:
    casos = reporte["casos"]
    dominio = [c for c in casos if c["tipo"] == "dominio"]
    otros = [c for c in casos if c["tipo"] == "fuera_de_dominio"]
    if not dominio:
        raise ValueError("Se necesitan preguntas dentro del dominio")
    hits = sum(c["rango_primera_fuente_esperada"] is not None for c in dominio)
    rr = sum(1 / c["rango_primera_fuente_esperada"] for c in dominio
             if c["rango_primera_fuente_esperada"] is not None)
    return {
        "casos_dominio": len(dominio),
        "aciertos_fuente_en_top_k": hits,
        "source_hit_at_k": round(hits / len(dominio), 4),
        "source_mrr_at_k": round(rr / len(dominio), 4),
        "casos_fuera_de_dominio": len(otros),
        "fuera_de_dominio_con_fragmentos": sum(bool(c["resultados"]) for c in otros),
        "consultas_con_error": sum(c["estado"] == "error" for c in casos),
        "senales_de_chunking": sum(len(r["senales_chunking"]) for c in casos for r in c["resultados"]),
        "nota": "Hit y MRR miden coincidencia de fuente esperada, NO relevancia textual ni veracidad.",
    }


def metricas_manuales(reporte: dict[str, Any]) -> dict[str, Any]:
    """Exige revisar TODO fragmento antes de informar precision/utilidad."""
    if reporte.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Versión del reporte desconocida")
    casos = reporte["casos"]
    if not casos or not any(c["tipo"] == "dominio" for c in casos):
        raise ValueError("No hay casos del dominio")
    k = reporte["k"]
    pendientes: list[str] = []
    for caso in casos:
        for r in caso["resultados"]:
            if (type(r.get("relevancia_manual")) is not int or r["relevancia_manual"] not in (0, 1, 2)
                    or type(r.get("cita_verificada_manual")) is not bool
                    or type(r.get("fragmento_completo_manual")) is not bool):
                pendientes.append(f'{caso["id"]}/resultado-{r["posicion"]}')
    if pendientes:
        raise ValueError("Faltan evaluaciones manuales: " + ", ".join(pendientes[:8]))
    dominio = [c for c in casos if c["tipo"] == "dominio"]
    resultados = [r for c in dominio for r in c["resultados"]]
    total_slots = len(dominio) * k
    temas = sum(r["relevancia_manual"] >= 1 for r in resultados)
    utiles = sum(r["relevancia_manual"] == 2 for r in resultados)
    hits_utiles = sum(any(r["relevancia_manual"] == 2 for r in c["resultados"]) for c in dominio)
    citas = sum(r["cita_verificada_manual"] for r in resultados)
    completos = sum(r["fragmento_completo_manual"] for r in resultados)
    return {
        "casos_dominio": len(dominio),
        "precision_tematica_at_k": round(temas / total_slots, 4),
        "precision_util_at_k": round(utiles / total_slots, 4),
        "hit_util_at_k": round(hits_utiles / len(dominio), 4),
        "citas_verificadas": f"{citas}/{len(resultados)}",
        "fragmentos_completos": f"{completos}/{len(resultados)}",
        "fuera_de_dominio_con_fragmentos_calificados_utiles": sum(
            any(r["relevancia_manual"] == 2 for r in c["resultados"])
            for c in casos if c["tipo"] == "fuera_de_dominio"
        ),
        "nota": "Relevancia y completitud son juicios humanos. Sin evaluación de respuestas generadas por un LLM.",
    }
