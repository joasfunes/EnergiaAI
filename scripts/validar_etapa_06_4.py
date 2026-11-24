"""Prueba integral determinística 06.4, SIN LLM, SIN red y SIN datos reales.

Ejecutar: python scripts/validar_etapa_06_4.py
Usa servicios Python, SQLite temporal, ToolMessages de prueba derivados de
las salidas de servicios y generador PDF; NO reemplaza el smoke test de Qwen.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import json

from energia_ai.quality import auditar_ultimo_turno, verificar_informe, verificar_preparacion
from energia_ai.services.home_inventory import InventarioHogar
from energia_ai.services.consumption import Electrodomestico
from energia_ai.services.tariffs import consultar_tarifa_catalogo
from energia_ai.services.savings import simular_ahorro_escenarios
from energia_ai.ui.conversations import IndiceConversaciones


def msg(tipo: str, content: str, nombre: str = "") -> SimpleNamespace:
    return SimpleNamespace(type=tipo, content=content, name=nombre)


def ejecutar(root: Path) -> dict:
    preflight = verificar_preparacion(root)
    if preflight["estado"] != "ok":
        return {"estado": "revision_requerida", "preflight": preflight,
                "nota": "Completá las exclusiones de .gitignore y archivos faltantes"}
    with TemporaryDirectory(prefix="energiaai_qa_064_") as temporal:
        base = Path(temporal)
        repo = InventarioHogar(base / "inventario.sqlite3")
        repo.asegurar_hogar("qa_hogar_1", periodo_dias=60)
        repo.asegurar_hogar("qa_hogar_2", periodo_dias=60)
        repo.registrar_equipo("qa_hogar_1", id="tv_1", nombre="TV", potencia_watts="100",
                            horas_efectivas_por_dia="5", dias_de_uso=20, cantidad=1)
        repo.registrar_equipo("qa_hogar_1", id="aire_1", nombre="Aire", potencia_watts="1500",
                            horas_efectivas_por_dia="4", dias_de_uso=20, cantidad=1)
        consumo = repo.consumo_inventario("qa_hogar_1")
        assert consumo["consumo_total_kwh"] == "130.0000"
        assert repo.consultar("qa_hogar_2")["cantidad_equipos"] == 0
        # Persistencia con una nueva instancia en la misma base de prueba.
        assert InventarioHogar(base / "inventario.sqlite3").consultar("qa_hogar_1")["cantidad_equipos"] == 2
        indice = IndiceConversaciones(base / "conversaciones_ui.sqlite3")
        tid = indice.crear("qa_hogar_1")
        indice.comprobar("qa_hogar_1", tid)
        try:
            indice.comprobar("qa_hogar_2", tid)
        except ValueError:
            aislamiento = True
        else:
            aislamiento = False
        assert aislamiento

        tarifa = consultar_tarifa_catalogo(distribuidora="EDEMSA", fecha=date(2026, 11, 15),
                                          consumo_kwh_bimestral=350, regimen="SIN_SEF")
        assert tarifa["categoria"] == "R2"
        actual = Electrodomestico("aire_1", "Aire", Decimal("1500"), Decimal("5"), 10)
        propuesto = Electrodomestico("aire_1", "Aire", Decimal("1500"), Decimal("3"), 10)
        simulacion = simular_ahorro_escenarios(
            periodo_dias=60, equipos_actuales=[actual], equipos_propuestos=[propuesto],
            consumo_hogar_bimestral_kwh=350, tarifa_consultada=tarifa)
        assert simulacion["ahorro_kwh"] == "30.0000"
        assert simulacion["consumo_hogar_bimestral_proyectado_kwh"] == "320.0000"
        # Se usan las salidas REALMENTE calculadas por servicios; no se
        # pretende falsificar una ejecución del agente. Estas son simulaciones
        # locales de mensajes SOLO para validar el pipeline del reporte.
        mensajes = [
            msg("human", "CASO DE PRUEBA; NO ES UNA CONVERSACION REAL"),
            msg("tool", json.dumps(tarifa), "consultar_tarifa"),
            msg("tool", json.dumps(simulacion), "simular_ahorro"),
        ]
        traza = auditar_ultimo_turno(mensajes, requeridas=["consultar_tarifa", "simular_ahorro"])
        assert traza["estado"] == "ok"
        informe = verificar_informe(mensajes)
        assert informe["ahorro_kwh"] == "30.0000"
        assert informe["cantidad_fuentes"] == 0  # No atribuir RAG si no se ejecutó.
        return {
            "estado": "ok", "tipo": "integracion_python_sin_llm",
            "preflight": preflight, "consumo_inventario_kwh": consumo["consumo_total_kwh"],
            "hogares_aislados_en_repositorio": aislamiento,
            "inventario_persistio": True,
            "categoria": tarifa["categoria"], "ahorro_kwh": simulacion["ahorro_kwh"],
            "consumo_hogar_proyectado_kwh": simulacion["consumo_hogar_bimestral_proyectado_kwh"],
            "monetario_disponible": simulacion["estimacion_monetaria_disponible"],
            "tools_simuladas_en_prueba": traza["herramientas"],
            "pdf": informe,
            "advertencia": "No prueba Qwen, LangChain, Streamlit, ChromaDB ni conexiones reales. "
                           "Completar aceptación manual en UI.",
        }


def main() -> None:
    raiz = Path(__file__).resolve().parents[1]
    resultado = ejecutar(raiz)
    destino = raiz / "data/processed/qa/resultado_integracion_06_4.json"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(resultado, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    print(f"Reporte local: {destino.relative_to(raiz)}")
    if resultado["estado"] != "ok":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
