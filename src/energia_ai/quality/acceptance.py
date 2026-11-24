"""Pruebas de aceptación determinísticas, sin ejecutar Qwen ni leer mensajes de IA.

Se examinan ÚNICAMENTE ToolMessages ejecutados y se devuelven METADATOS,
no contenido de conversaciones, datos de equipos, identificadores ni credenciales.
La decisión final de calidad requiere además pruebas manuales en Streamlit.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Sequence

TOOLS_ADMITIDAS = frozenset({
    "calcular_consumo", "consultar_tarifa", "simular_ahorro",
    "buscar_consejos", "registrar_electrodomestico", "consultar_inventario",
})

ARCHIVOS_OBLIGATORIOS = (
    "app.py", "README.md", ".env.example", "pyproject.toml",
    "src/energia_ai/agent/persistent_runtime.py",
    "src/energia_ai/rag/retrieval.py",
    "src/energia_ai/ui/runtime.py",
    "src/energia_ai/reporting/extraction.py",
    "src/energia_ai/reporting/pdf_report.py",
    "scripts/prepare_rag_corpus.py",
    "scripts/build_rag_index.py",
)


def _tipo(msg: Any) -> str | None:
    return getattr(msg, "type", None)


def _resultado(msg: Any) -> dict[str, Any] | None:
    content = getattr(msg, "content", None)
    if isinstance(content, dict):
        return content
    if not isinstance(content, str) or len(content) > 1_000_000:
        return None
    try:
        parsed = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        return None
    return parsed if isinstance(parsed, dict) else None


def auditar_ultimo_turno(
    mensajes: Sequence[Any], *, requeridas: Iterable[str] = (),
) -> dict[str, Any]:
    """Audita el último turno humano. No confunde tool solicitada con ejecutada.

    Criterios: las herramientas requeridas fueron ejecutadas con estado=ok;
    no hubo errors y si hubo registro+consulta del inventario, la lectura es
    POSTERIOR al último registro. No acredita por sí solo corrección del LLM.
    """
    if not isinstance(mensajes, (list, tuple)):
        raise TypeError("mensajes debe ser una lista/tupla")
    requeridas = tuple(requeridas)
    if any(not isinstance(x, str) or x not in TOOLS_ADMITIDAS for x in requeridas):
        raise ValueError("Se pidió auditar una herramienta desconocida")
    inicio = next((i for i in range(len(mensajes) - 1, -1, -1)
                   if _tipo(mensajes[i]) in ("human", "HumanMessage")), None)
    if inicio is None:
        return {"estado": "revision_requerida", "herramientas": [],
                "faltantes": sorted(set(requeridas)), "alertas": ["sin_turno_humano"]}
    ejecuciones: list[dict[str, str]] = []
    alertas: list[str] = []
    for m in mensajes[inicio+1:]:
        if _tipo(m) not in ("tool", "ToolMessage"):
            continue
        nombre = getattr(m, "name", None)
        if not isinstance(nombre, str) or nombre not in TOOLS_ADMITIDAS:
            alertas.append("tool_desconocida")
            continue
        res = _resultado(m)
        estado = res.get("estado") if res is not None else None
        if not isinstance(estado, str):
            estado = "desconocido"
        ejecuciones.append({"nombre": nombre, "estado": estado})
        if estado not in ("ok",):
            alertas.append("tool_sin_exito")
    aprobadas = {e["nombre"] for e in ejecuciones if e["estado"] == "ok"}
    faltantes = sorted(set(requeridas) - aprobadas)
    if faltantes:
        alertas.append("faltan_tools_requeridas")
    registros = [i for i, e in enumerate(ejecuciones)
                 if e["nombre"] == "registrar_electrodomestico" and e["estado"] == "ok"]
    lecturas = [i for i, e in enumerate(ejecuciones)
                if e["nombre"] == "consultar_inventario" and e["estado"] == "ok"]
    if registros and lecturas and max(lecturas) < max(registros):
        alertas.append("lectura_inventario_obsoleta")
    if not ejecuciones:
        alertas.append("sin_ejecuciones")
    return {
        "estado": "ok" if not alertas else "revision_requerida",
        "herramientas": ejecuciones,
        "faltantes": faltantes,
        "alertas": sorted(set(alertas)),
    }


def verificar_preparacion(root: str | Path) -> dict[str, Any]:
    """Inspección de archivos del repositorio; nunca lee credenciales."""
    raiz = Path(root)
    if not raiz.is_dir():
        raise ValueError("La carpeta del proyecto no existe")
    faltantes = [p for p in ARCHIVOS_OBLIGATORIOS if not (raiz / p).is_file()]
    ignore = raiz / ".gitignore"
    texto = ignore.read_text(encoding="utf-8") if ignore.is_file() else ""
    reglas = [r.strip() for r in texto.splitlines() if r.strip() and not r.lstrip().startswith("#")]
    bloqueos = {
        "data/state/": "data/state/" in reglas or "data/" in reglas,
        "data/processed/": "data/processed/" in reglas or "data/" in reglas,
        "data/vectorstore/": "data/vectorstore/" in reglas or "data/" in reglas,
        ".env": ".env" in reglas or ".env*" in reglas or ".env.*" in reglas,
    }
    alertas = []
    if faltantes:
        alertas.append("archivos_ausentes")
    if not all(bloqueos.values()):
        alertas.append("gitignore_incompleto")
    return {"estado": "ok" if not alertas else "revision_requerida",
            "faltantes": faltantes, "exclusiones_git": bloqueos, "alertas": alertas}


def verificar_informe(mensajes: Sequence[Any]) -> dict[str, Any]:
    """Inspecciona informe derivado de ToolMessages, sin crear archivos persistentes."""
    from io import BytesIO
    from energia_ai.reporting.extraction import extraer_ultimo_analisis
    from energia_ai.reporting.pdf_report import generar_informe_pdf
    from pypdf import PdfReader

    analisis = extraer_ultimo_analisis(mensajes)
    pdf = generar_informe_pdf(analisis)
    if not pdf.startswith(b"%PDF-"):
        raise ValueError("La salida no es un PDF")
    lector = PdfReader(BytesIO(pdf))
    if not lector.pages:
        raise ValueError("El PDF no contiene páginas")
    texto = "\n".join(p.extract_text() or "" for p in lector.pages)
    # No busca cifras redondeadas en el texto: esas ya están verificadas por
    # el extractor; aquí confirmamos que el PDF existe y contiene contenido.
    if len(texto.strip()) < 100:
        raise ValueError("PDF sin contenido legible")
    return {"estado": "ok", "paginas": len(lector.pages),
            "ahorro_kwh": analisis["ahorro_kwh"],
            "monetario_disponible": analisis["monetario_disponible"],
            "cantidad_fuentes": len(analisis["evidencias_rag"])}
