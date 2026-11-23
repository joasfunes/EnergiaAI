"""EnergiaAI 06.2 — chat académico local sobre el agente persistente de la Etapa 05.

Iniciar desde la raíz: python -m streamlit run app.py --server.address 127.0.0.1
NO desplegar públicamente: esta versión no tiene autenticación/autorización.
"""
from __future__ import annotations
from pathlib import Path
from time import monotonic

import streamlit as st

from energia_ai.services.home_inventory import InventarioHogar, validar_hogar_id
from energia_ai.ui.conversations import IndiceConversaciones
from energia_ai.ui.presentation import cargar_medicion_06_1
from energia_ai.ui.runtime import recuperar_historial, ejecutar_stream_ui

ESTADO_DIR = Path("data/state")
INDICE_DB = ESTADO_DIR / "conversaciones_ui.sqlite3"
MEDICION_061 = Path("data/processed/performance/medicion_06_1.json")


def main() -> None:
    st.set_page_config(page_title="EnergiaAI · Mendoza", page_icon="⚡", layout="wide")
    st.title("⚡ EnergiaAI")
    st.caption("Asesor energético residencial · EDEMSA · Mendoza · Prototipo académico local")

    with st.sidebar:
        st.subheader("Hogar y conversaciones")
        hogar_id = st.text_input("Identificador de hogar", value="casa_demo",
                                 help="Modo local de demostración. No usar datos privados reales.")
        try:
            validar_hogar_id(hogar_id)
        except ValueError:
            st.error("Usá un ID de hogar alfanumérico, con _ o -, sin espacios.")
            st.stop()
        indice = IndiceConversaciones(INDICE_DB)
        key_selector = f"conv_select_{hogar_id}"
        if st.button("➕ Nueva conversación", use_container_width=True):
            st.session_state[key_selector] = indice.crear(hogar_id)
            st.rerun()
        opciones = indice.listar(hogar_id)
        if not opciones:
            st.session_state[key_selector] = indice.crear(hogar_id)
            opciones = indice.listar(hogar_id)
        disponibles = [c["thread_id"] for c in opciones]
        if st.session_state.get(key_selector) not in disponibles:
            st.session_state[key_selector] = disponibles[0]
        titulos = {c["thread_id"]: f'{c["titulo"]} · {c["creada_utc"][:16]}' for c in opciones}
        thread_id = st.selectbox("Conversación", options=disponibles,
                                 format_func=lambda tid: titulos.get(tid, tid), key=key_selector)
        indice.comprobar(hogar_id, thread_id)
        st.caption("Los mensajes se recuperan de SQLite por thread_id; no se copian al navegador como fuente de verdad.")

        with st.expander("Inventario registrado", expanded=False):
            repo = InventarioHogar(ESTADO_DIR / "inventario.sqlite3")
            inventario = repo.consultar(hogar_id)
            if inventario.get("estado") == "ok":
                st.metric("Electrodomésticos", inventario["cantidad_equipos"])
                if inventario["equipos"]:
                    st.dataframe(inventario["equipos"], hide_index=True, use_container_width=True)
                else:
                    st.caption("No hay equipos registrados en este hogar.")
            else:
                st.caption("El hogar todavía no tiene un inventario inicializado.")

        with st.expander("Diagnóstico 06.1", expanded=False):
            datos = cargar_medicion_06_1(MEDICION_061)
            if datos is None:
                st.info("Todavía no está el archivo local medicion_06_1.json.")
            else:
                for nombre, etiqueta in [
                    ("duracion_total_s", "Duración total (s)"),
                    ("duracion_modelo_observada_s", "Tiempo observado de Qwen (s)"),
                    ("tiempo_primera_salida_s", "Hasta primer texto (s)"),
                    ("llamadas_modelo", "Llamadas observadas al modelo")]:
                    valor = datos.get(nombre)
                    st.metric(etiqueta, valor if valor is not None else "No medido")
                st.caption("Una única medición local. No representa promedio ni garantía de latencia.")

        st.warning("Prototipo SIN autenticación. Usar exclusivamente en localhost; no exponer a internet.")

    st.subheader("Conversación")
    try:
        anteriores = recuperar_historial(hogar_id=hogar_id, thread_id=thread_id)
    except Exception as exc:
        st.error(f"No fue posible leer el historial ({type(exc).__name__}). Verificá SQLite y dependencias.")
        st.stop()

    for entrada in anteriores:
        with st.chat_message(entrada["role"]):
            st.markdown(entrada["content"])

    if not anteriores:
        st.info("Consultá tus consumos, registrá equipos o pedí recomendaciones energéticas con fuentes oficiales.")

    consulta = st.chat_input("Escribí tu consulta sobre consumo o ahorro eléctrico…", max_chars=3000)
    if not consulta or not consulta.strip():
        return
    indice.actualizar(hogar_id, thread_id)
    with st.chat_message("user"):
        st.markdown(consulta)

    with st.chat_message("assistant"):
        status = st.status("Consultando a EnergiaAI…", expanded=True)
        respuesta = st.empty()
        texto = ""
        ultimo_render = monotonic()
        resultado_final = None
        hubo_error = False
        # Primero se muestran solicitudes; después sus ejecuciones confirmadas.
        solicitudes = 0
        ejecuciones_temporizadas: set[str] = set()
        try:
            for tipo, evento in ejecutar_stream_ui(hogar_id=hogar_id, thread_id=thread_id,
                                                  consulta=consulta):
                if tipo == "error":
                    hubo_error = True
                    status.update(label="No se pudo completar la consulta", state="error")
                    st.error(f"Error controlado ({evento}). Reintentá después de revisar el servidor local.")
                    continue
                if tipo == "resumen":
                    resultado_final = evento
                    continue
                if tipo != "evento" or not isinstance(evento, dict):
                    continue
                clase = evento.get("tipo")
                if clase == "texto":
                    texto += str(evento.get("texto", ""))
                    if monotonic() - ultimo_render >= 0.12:
                        respuesta.markdown(texto)
                        ultimo_render = monotonic()
                elif clase == "tool_solicitada":
                    solicitudes += 1
                    nombre = str(evento.get("nombre", "desconocida"))
                    with status:
                        st.write(f"**Tool solicitada:** `{nombre}`")
                        argumentos = evento.get("argumentos")
                        if argumentos:
                            st.caption("Argumentos seleccionados por el LLM (vista depurada)")
                            st.json(argumentos, expanded=False)
                        else:
                            st.caption("Sin argumentos públicos para mostrar")
                elif clase == "tool_inicio":
                    with status:
                        st.write(f"⏳ Ejecutando `{evento.get('nombre', '')}`")
                elif clase == "tool_fin":
                    nombre = str(evento.get("nombre", ""))
                    ejecuciones_temporizadas.add(nombre)
                    with status:
                        st.write(f"✅ `{nombre}` · estado `{evento.get('estado', 'desconocido')}` · {evento.get('duracion_s', '—')} s")
                        if evento.get("resultado"):
                            st.caption("Resumen seguro del resultado")
                            st.json(evento["resultado"], expanded=False)
                elif clase == "tool" and evento.get("nombre") not in ejecuciones_temporizadas:
                    with status:
                        st.write(f"✅ Tool ejecutada: `{evento.get('nombre', '')}` · estado `{evento.get('estado', 'desconocido')}`")
        except Exception as exc:
            hubo_error = True
            st.error(f"Fallo de presentación ({type(exc).__name__}); la operación podría haber continuado en el servidor.")
        if texto.strip():
            respuesta.markdown(texto)
        elif not hubo_error:
            st.info("El agente no produjo texto final. Revisá la traza antes de repetir el pedido.")
        if not hubo_error:
            status.update(label=f"Ejecución finalizada · {solicitudes} solicitudes de tools", state="complete")
        if isinstance(resultado_final, dict):
            tiempo = resultado_final.get("duracion_total_s")
            if isinstance(tiempo, (int, float)):
                st.caption(f"Duración observada: {tiempo:.1f} s · Qwen3.5 9B (modelo local)")
    st.caption("Las herramientas calculan y recuperan información; las estimaciones no constituyen una factura oficial.")


if __name__ == "__main__":
    main()
