# EnergiaAI — Etapa 06.2: Interfaz web con Streamlit

**Fecha:** 23/11/2026 · **Estado:** pendiente de validación en Windows

## Decisión de arquitectura

Se mantiene **Qwen3.5 9B** mediante Ollama. La interfaz es una capa de presentación y **no** reimplementa las tools, el RAG ni el inventario. Se reutilizan `abrir_runtime_persistente`, `ejecutar_turno_medido` y el `SqliteSaver` ya desarrollados.

## Alcance y límites

- Interfaz local Streamlit para un solo usuario, con chat Markdown.
- Hogar activo y lista de conversaciones indexadas en SQLite (`data/state/conversaciones_ui.sqlite3`), **sin duplicar el contenido del chat**.
- Historial real leído del checkpointer (`data/state/conversaciones.sqlite3`), por `thread_id`.
- Inventario consultado directamente desde `data/state/inventario.sqlite3`, sin inventar equipos.
- Streaming de texto, solicitud y ejecución de tools; presentación de argumentos **depurados** y resultado resumido de la telemetría. El resumen no sustituye el resultado completo almacenado en el historial de LangGraph.
- Diagnóstico opcional de una medición de 06.1; no incluye comparativa de modelos.
- **Sin autenticación ni aislamiento seguro multiusuario. Solo localhost.** No compartir datos reales ni publicar la aplicación en una red.
- El resultado final tangible (informe con gráfico y descarga) se realizará en **06.3**.

## Estructura nueva

```text
energia-ai/
├── app.py                                        # UI Streamlit
├── requirements-ui.txt
├── src/energia_ai/
│   ├── agent/streaming.py                       # MODIFICADO: registra solicitudes de tools
│   └── ui/
│       ├── __init__.py
│       ├── conversations.py                     # Índice SQLite de threads
│       ├── presentation.py                      # Redacta argumentos y lee historial/métricas
│       └── runtime.py                           # Puente streaming/thread con cola
├── scripts/inspect_metrics_06_2.py
├── tests/test_ui_conversations_06_2.py
├── tests/test_ui_presentation_06_2.py
├── tests/test_ui_runtime_06_2.py
├── tests/test_ui_streaming_06_2.py
└── docs/ETAPA_06_2.md
```

## Pasos de instalación y uso (Windows 11)

1. Hacer `git status`. Si hay cambios propios en `src/energia_ai/agent/streaming.py`, hacer un respaldo antes de reemplazarlo.
2. Descomprimir `EnergiaAI_Etapa_06_2_Streamlit.zip` y **fusionar** las carpetas con el proyecto existente; no sustituir `data/` ni tus bases SQLite.
3. En una terminal PowerShell en la **raíz** del repositorio:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-ui.txt
.\.venv\Scripts\python.exe -m pip install -e .
```

4. Asegurarse de que Ollama tenga descargado `qwen3.5:9b` y `embeddinggemma:300m`:

```powershell
ollama list
```

5. Ejecutar las pruebas nuevas sin LLM:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_ui_*_06_2.py" -v
```

6. Ejecutar todas las pruebas previas y nuevas:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

7. Iniciar la web **solo en localhost**:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501
```

8. Abrir en el navegador `http://127.0.0.1:8501` (no abrir el archivo `app.py` directamente).
9. Con el hogar `casa_demo`, crear una conversación. Probar: «Tengo un televisor de 100 W que uso cinco horas al día durante veinte días. ¿Cuánto consume?»; verificar cálculo de **10 kWh** y tool ejecutada.
10. Hacer una consulta sobre eficiencia en verano; verificar `buscar_consejos` y referencias.
11. Cerrar **solo la pestaña** y reabrir; luego detener y reiniciar el **servidor** Streamlit. La misma conversación debe seguir visible desde SQLite.
12. Probar dos conversaciones distintas y comprobar que los mensajes no se mezclan.
13. Probar inventario (sin duplicar IDs existentes). En una conversación nueva, pedir «Consultá mi inventario de electrodomésticos»; verificar equipos y datos reales.
14. Inspeccionar el diagnóstico de 06.1 en la barra lateral. Si falta el archivo, mostrar «no encontrado», sin inventar valores.

### Revisión de las métricas 06.1

El archivo `data/processed/performance/medicion_06_1.json` se genera **en la computadora del equipo**. Para interpretarlo, abrirlo y revisar: `duracion_total_s`, `duracion_modelo_observada_s`, `llamadas_modelo`, `tiempo_primera_salida_s` y `herramientas`. Se puede ejecutar:

```powershell
.\.venv\Scripts\python.exe scripts\inspect_metrics_06_2.py
```

No es posible afirmar a partir de un solo turno cuánto tardarán todas las consultas ni que Streamlit reduzca la latencia. Si el archivo real se comparte, analizar tiempos medidos y cuellos de botella sin suposiciones.

### ¿Cómo funciona?

1. `IndiceConversaciones` guarda solamente `thread_id`, `hogar_id`, título genérico y fechas. No almacena una segunda copia del chat.
2. `historial_visible()` consulta el checkpointer y filtra los mensajes intermedios de herramientas para mostrar el diálogo real.
3. `ejecutar_stream_ui()` ejecuta el turno en un hilo propio. Los callbacks ponen eventos en una cola; **solo el hilo principal** actualiza Streamlit.
4. `streaming.py` notifica `tool_solicitada` leyendo `AIMessage.tool_calls` de las actualizaciones antes de la ejecución. Estos argumentos se reducen a un subconjunto permitido.
5. Las notificaciones `tool_inicio` y `tool_fin` vienen de la telemetría; la UI diferencia solicitudes de llamadas ejecutadas.
6. `st.status` muestra herramientas en ejecución y resúmenes. `st.markdown` actualiza el texto progresivamente.

### Límites y precauciones

- El modelo puede tardar minutos en la CPU Ryzen 7 5700U. El streaming muestra avance, no garantiza aceleración.
- Las herramientas que escriben SQLite pueden continuar si se cierra la pestaña a mitad del turno; no reintentar registros a ciegas.
- La simple elección de `hogar_id` **no es control de acceso**: no ofrecer acceso público a la app.
- La interfaz usa argumentos **seleccionados y truncados** para no exponer secretos, no el detalle completo sin depurar.
- Si el runtime falla, la interfaz presenta solo el **tipo** de error; revisar la terminal para diagnóstico controlado.
- Las instrucciones del prompt ayudan a secuenciar herramientas pero **no garantizan** orden. En 06.4 se probarán los casos dependientes con pruebas E2E.
- La memoria de conversaciones está en SQLite, no en `st.session_state` (que se reinicia con el navegador).
- Las referencias de RAG deben mostrarse si el LLM las incluye; la comprobación automática de citas será parte de la revisión E2E.
- Si se cambia `hogar_id`, nunca reutilizar un `thread_id` de otro hogar. El índice lo valida.

## Pruebas y aceptación

Hay 19 pruebas nuevas de índice, sanitización, historial, puente de streaming y solicitud de tools (229 anteriores + 19 nuevas = **248 esperadas**, sujeto a ejecución en Windows). Son pruebas de lógica, no reemplazan las verificaciones manuales de la interfaz con Ollama.

Para cerrar 06.2: pruebas en verde sin omisiones en Windows, chat real, tools y argumentos depurados visibles **durante** el procesamiento, separación de conversaciones, persistencia al reinicio, selección de hogar, inventario, lectura opcional de métricas, documentación y commit.

```powershell
git status
git add app.py requirements-ui.txt src/energia_ai/agent/streaming.py src/energia_ai/ui scripts/inspect_metrics_06_2.py tests/test_ui_conversations_06_2.py tests/test_ui_presentation_06_2.py tests/test_ui_runtime_06_2.py tests/test_ui_streaming_06_2.py docs/ETAPA_06_2.md
git commit -m "feat: incorporar interfaz Streamlit con chat y trazabilidad"
```

La Etapa 06.3 generará el informe energético descargable con gráfico y fuentes. La Etapa 06.4 abordará pruebas integrales, límites de seguridad y estabilidad.
