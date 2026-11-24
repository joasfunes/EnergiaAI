# EnergiaAI — Etapa 06.3: Informe energético descargable

**Fecha:** 23/11/2026 · **Estado:** desarrollo entregado, pendiente de verificar en Windows del equipo.

## Propósito

Entregar un **resultado tangible** (PDF A4 descargable) generado desde `simular_ahorro` y, cuando fue realmente invocada en el **mismo turno**, `buscar_consejos`. El informe incluye dos gráficos vectoriales, variación de kWh, importe parcial **solo si la tool lo autorizó**, fuentes oficiales realmente recuperadas y advertencias. No se genera una factura ni se ejecuta Qwen para crear el PDF.

## Arquitectura

1. `src/energia_ai/reporting/extraction.py`: lee `ToolMessage` reales de los checkpoints de LangGraph, agrupa los resultados por turno y toma la última simulación válida. Valida sumas, equipos, porcentaje, resultados de tools y procedencia de fuentes. No analiza el texto libre del LLM. Si no hay simulación, informa ausencia y no crea un reporte ficticio.
2. `src/energia_ai/reporting/pdf_report.py`: usa **ReportLab Platypus** y gráficos vectoriales en memoria. Devuelve bytes con encabezado `%PDF-`; no necesita ChromaDB, Ollama, GPU ni streaming.
3. `src/energia_ai/ui/reporting.py`: abre el runtime persistente, extrae la información y devuelve `(pdf_bytes, metadata)`.
4. `app.py` (modificado): agrega **Preparar informe PDF** y **Descargar informe energético (PDF)**. Compara hogar y conversación con el índice antes de abrir el estado. Conserva temporalmente el archivo en `st.session_state`, no en otra base de datos.
5. `scripts/demo_report_06_3.py`: genera una muestra reproducible **sin LLM** desde los servicios Python reales; no inventa evidencia RAG. Ruta de salida: `data/processed/reports/demo_06_3.pdf`.

## Nuevos archivos y archivo modificado

```
energia-ai/
├── app.py                                 # MODIFICADO: exportación PDF
├── requirements-report.txt                 # NUEVO: ReportLab
├── src/energia_ai/reporting/              # NUEVA CARPETA
│   ├── __init__.py
│   ├── extraction.py
│   └── pdf_report.py
├── src/energia_ai/ui/reporting.py          # NUEVO
├── scripts/demo_report_06_3.py            # NUEVO
├── tests/test_report_06_3.py              # NUEVO: 16 pruebas
└── docs/ETAPA_06_3.md                     # NUEVO
```

**No reemplazar** ningún otro módulo, ni `data/state/`, ni `data/vectorstore/`. Conservar copia de `app.py` si fue personalizado.

## Instalación y pruebas (Windows 11)

Desde la raíz de `energia-ai` en PowerShell:

```powershell
git status
.\.venv\Scripts\python.exe -m pip install -r requirements-report.txt
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_report_06_3.py -v
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Se agregaron **16 pruebas nuevas**, por lo que el objetivo acumulado es **264 pruebas** (248 anteriores + 16 nuevas). Las pruebas nuevas se ejecutan sin Ollama ni Streamlit; el entorno Windows deberá confirmar todas sin omisiones.

### Probar el generador sin Qwen

```powershell
.\.venv\Scripts\python.exe scripts\demo_report_06_3.py
```

Abrí `data/processed/reports/demo_06_3.pdf`. Debe mostrar el consumo actual **75 kWh**, propuesto **45 kWh**, ahorro **30 kWh** y dos gráficos. **Es una muestra técnica**, sin consejos RAG falsos. Si el catálogo descargado sigue con revisión pendiente, no monetiza; en la PC del equipo ya se contrastó en 03.2.

### Probar desde Streamlit con resultados reales

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501
```

1. Seleccioná `casa_demo` y una conversación (o creá una nueva).
2. Pedí un análisis completo al agente con datos coherentes: consumo bimestral **350 kWh**, régimen **SIN_SEF**, fecha **15/11/2026**, aire acondicionado **1500 W**, **5 a 3 h efectivas/día durante 10 días**, dentro de un período de **60 días**, y pedí consejos documentados de verano.
3. Confirmá que se ejecuten **simular_ahorro** y **buscar_consejos** realmente. Las otras tools pueden ejecutarse también según la tarea. La mera afirmación del LLM de haberlas usado no basta.
4. Cuando termine el turno, presioná **Preparar informe PDF** y después **Descargar informe energético (PDF)**. No debería haber nuevas llamadas a Qwen.
5. Comprobá los gráficos, las cifras (**75 → 45 kWh**, **30 kWh** de ahorro) y las fuentes que aparezcan en el mismo turno. Si hay una estimación económica válida del componente variable SIN_SEF, se mostrará distinguiéndola de la factura final; en caso contrario explicará su ausencia.
6. Cerrá y reiniciá Streamlit. Seleccioná la misma conversación y prepará de nuevo el PDF; debe extraerse del historial SQLite.
7. Probá preparar PDF en una conversación sin `simular_ahorro`: la aplicación debe mostrar una advertencia y **no producir un informe inventado**.
8. Probá cambiar de conversación y de hogar: el PDF no debe mezclar datos de otros threads.

**Advertencia importante:** si pedís consejos en un turno posterior a la simulación, el PDF no los mezcla automáticamente. Deben haberse recuperado en el mismo turno para conservar trazabilidad. La aplicación elige la última simulación válida de la conversación, aun cuando después existan otros turnos sin simulación.

## Reglas de calidad y seguridad

- Nada se obtiene del texto libre de Qwen: valores y fuentes se extraen solo de ToolMessages confirmados.
- Una simulación incoherente o ausente impide generar el PDF.
- Si `estimacion_monetaria_disponible != True`, no se incluye dinero. Si es `True`, además se verifica que la fuente coincida con el catálogo EPRE esperado y que figure contrastada.
- Si el RAG no se ejecutó en ese turno, el reporte declara falta de evidencia documental, sin generar consejos inventados.
- Los extractos del RAG se acortan, se escapan para el PDF y se admiten solamente si URL y `fuente_id` coinciden con el registro oficial de tres fuentes.
- La generación del documento no requiere otra tool LangChain: es una **operación determinística de presentación**, posterior al razonamiento multi-paso del agente.
- No se guardan PDFs privados en Git; los ejemplos de `data/processed/` están ignorados. No publicar la app: sigue siendo **solo localhost y sin autenticación**.

## Pruebas y criterios de cierre

- Las 16 pruebas nuevas y toda la suite pasan sin omisiones en Windows.
- `demo_report_06_3.py` produce un PDF legible con gráficos y advertencias.
- En Streamlit se puede descargar un PDF derivado de una simulación real con los resultados y citas disponibles.
- La exportación se puede repetir después de reiniciar Streamlit sin volver a consultar a Qwen.
- No hay reportes inventados sin simulación ni importes finales de facturas.
- Se registra un commit de Git con el código y el documento, sin bases ni documentos privados.

```powershell
git status
git add app.py requirements-report.txt src/energia_ai/reporting src/energia_ai/ui/reporting.py scripts/demo_report_06_3.py tests/test_report_06_3.py docs/ETAPA_06_3.md
git commit -m "feat: generar informes energeticos PDF con graficos y fuentes"
```

## Próxima etapa

**06.4** — Pruebas integrales de UI, control de errores y trazabilidad, seguridad del prototipo y revisión del informe. **07** — README final, instalación limpia, presentación y demo del integrador.
