"""EnergiaAI 06.3 — chat local y exportación PDF de un análisis real.

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
from energia_ai.ui.reporting import preparar_pdf_conversacion
from energia_ai.ui.inventory_editor import mostrar_editor_inventario
from energia_ai.reporting import InformeNoDisponible

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
        seccion = st.radio("Sección", ("Consultor IA", "Mis electrodomésticos"),
                           help="Administrá tus equipos sin esperar al modelo de IA.")
        if seccion == "Mis electrodomésticos":
            st.info("El inventario se gestiona directamente en la tabla, sin Qwen.")
        if seccion == "Consultor IA":
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
            st.caption("ID de la conversación:")
            st.code(thread_id, language=None)
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

    if seccion == "Mis electrodomésticos":
        mostrar_editor_inventario(hogar_id, estado_dir=ESTADO_DIR)
        return

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
        st.info("Consultá tus consumos o pedí recomendaciones energéticas con fuentes oficiales. "
                "Para agregar equipos, abrí Mis electrodomésticos.")

    # Etapa 06.3: PDF reproducible a partir de resultados REALES almacenados en
    # SQLite. No vuelve a invocar el LLM ni toma cifras de su texto libre.
    st.subheader("Informe energético descargable")
    st.caption("Generá un PDF del último turno de esta conversación que haya ejecutado simular_ahorro. "
               "Las recomendaciones solo se adjuntan si buscar_consejos se ejecutó en ese mismo turno.")
    clave_reporte = f"informe_pdf_{hogar_id}_{thread_id}"
    clave_meta = f"informe_meta_{hogar_id}_{thread_id}"
    if st.button("Preparar informe PDF", key=f"crear_pdf_{hogar_id}_{thread_id}"):
        try:
            indice.comprobar(hogar_id, thread_id)
            datos_pdf, meta = preparar_pdf_conversacion(hogar_id=hogar_id, thread_id=thread_id)
            st.session_state[clave_reporte] = datos_pdf
            st.session_state[clave_meta] = meta
        except InformeNoDisponible as exc:
            st.session_state.pop(clave_reporte, None)
            st.session_state.pop(clave_meta, None)
            st.warning(str(exc))
        except Exception as exc:
            st.session_state.pop(clave_reporte, None)
            st.session_state.pop(clave_meta, None)
            st.error(f"No fue posible generar el informe ({type(exc).__name__}).")
    if clave_reporte in st.session_state:
        meta = st.session_state.get(clave_meta, {})
        cols = st.columns(3)
        cols[0].metric("Consumo actual", f"{meta.get('consumo_actual_kwh', '—')} kWh")
        cols[1].metric("Consumo propuesto", f"{meta.get('consumo_propuesto_kwh', '—')} kWh")
        cols[2].metric("Ahorro energético", f"{meta.get('ahorro_kwh', '—')} kWh")
        if not meta.get('evidencias_rag'):
            st.info("El análisis seleccionado no contiene fuentes RAG del mismo turno; "
                    "el PDF lo explicará sin inventar recomendaciones.")
        st.download_button("Descargar informe energético (PDF)",
                           data=st.session_state[clave_reporte],
                           file_name="EnergiaAI_informe_energetico.pdf",
                           mime="application/pdf", key=f"descargar_pdf_{hogar_id}_{thread_id}")

    consulta = st.chat_input("Escribí tu consulta sobre consumo o ahorro eléctrico…", max_chars=3000)
    if not consulta or not consulta.strip():
        return
    # No ofrecer un informe anterior como si perteneciera al turno nuevo.
    st.session_state.pop(clave_reporte, None)
    st.session_state.pop(clave_meta, None)
    indice.actualizar(hogar_id, thread_id)
    with st.chat_message("user"):
        st.markdown(consulta)

    with st.chat_message("assistant"):
        status = st.status("Consultando a EnergiaAI…", expanded=True)
        # Canal de razonamiento visible en directo y separado del texto final.
        # Los deltas llegan desde ChatOllama: no inferimos ni fabricamos pasos.
        with st.expander("Razonamiento expuesto por Ollama", expanded=True):
            panel_razonamiento = st.empty()
            panel_razonamiento.caption("Esperando un bloque de razonamiento del modelo…")
        respuesta = st.empty()
        texto = ""
        razonamiento = ""
        ultimo_render = monotonic()
        ultimo_render_razonamiento = monotonic()
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
                if clase == "razonamiento":
                    razonamiento += str(evento.get("texto", ""))
                    # Evita saturar Streamlit mientras Qwen emite muchos deltas.
                    if monotonic() - ultimo_render_razonamiento >= 0.20:
                        visible = razonamiento[-30000:]
                        if len(razonamiento) > 30000:
                            visible = "[Vista limitada a los últimos 30.000 caracteres]\n" + visible
                        panel_razonamiento.code(visible, language=None)
                        ultimo_render_razonamiento = monotonic()
                elif clase == "texto":
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
        if razonamiento.strip():
            visible = razonamiento[-30000:]
            if len(razonamiento) > 30000:
                visible = "[Vista limitada a los últimos 30.000 caracteres]\n" + visible
            panel_razonamiento.code(visible, language=None)
        else:
            panel_razonamiento.caption("El proveedor no expuso razonamiento en este turno.")
        if texto.strip():
            respuesta.markdown(texto)
        elif not hubo_error:
            st.warning("El agente terminó sin respuesta final. El razonamiento, si existe, "
                       "NO sustituye la respuesta ni demuestra ejecución de tools.")
        if not hubo_error:
            if texto.strip():
                status.update(label=f"Ejecución terminada · {solicitudes} solicitudes de tools",
                              state="complete")
            else:
                status.update(label="Ejecución incompleta · sin respuesta final", state="error")
        if isinstance(resultado_final, dict):
            tiempo = resultado_final.get("duracion_total_s")
            if isinstance(tiempo, (int, float)):
                st.caption(f"Duración observada: {tiempo:.1f} s · Qwen3.5 9B (modelo local)")
    st.caption("Las herramientas calculan y recuperan información; las estimaciones no constituyen una factura oficial.")


if __name__ == "__main__":
    main()
