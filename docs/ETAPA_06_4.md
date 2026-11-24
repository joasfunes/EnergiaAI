# Etapa 06.4 — Pruebas integrales, seguridad y aceptación del prototipo

**Fecha:** 23/11/2026 · **Estado inicial:** código entregado; validación en Windows pendiente.  
**Base:** Etapa 06.3 declarada completa por el equipo; 264 pruebas aprobadas.  
**Modelo elegido:** Qwen3.5 9B mediante Ollama; no se cambia ni se compara con modelos menores.  
**Alcance:** prototipo ACADÉMICO LOCAL, exclusivo EDEMSA/Mendoza, sin autenticación.

## Propósito

No agregamos otra tool ni otro modelo. Buscamos demostrar con evidencia que el agente, la UI, el RAG, la memoria, el inventario y el PDF funcionan como una unidad; identificar límites de seguridad; y dejar el proyecto listo para preparar el README y la presentación de la Etapa 07. **Un test unitario no prueba la inferencia real de Qwen, el streaming de Streamlit ni la autenticidad de documentos en línea.**

## Cambios

- `src/energia_ai/quality/acceptance.py` y `__init__.py`: auditoría segura de ToolMessages del último turno, control de orden del inventario, preflight de archivos/exclusiones y validación de PDF en memoria.
- `scripts/validar_etapa_06_4.py`: ejercicio offline reproducible con servicios reales y SQLite temporal, **sin invocar al LLM**. Revisa consumo de inventario de 130 kWh, categoría R2, ahorro 30 kWh, PDF y separación de hogares.
- `scripts/auditar_conversacion_06_4.py`: lee el estado persistido del thread existente y muestra solo las tools ejecutadas, estado e informe disponible. **No vuelve a invocar Qwen**. Requiere que el thread pertenezca al hogar dentro del índice local.
- `tests/test_quality_06_4.py`: 25 pruebas nuevas de auditoría, integridad, reportes y aislamiento local.
- `requirements-qa.txt`: dependencias del verificador de PDF (`pypdf` y ReportLab).
- `docs/ACTA_06_4.md`: modelo de acta para registrar los resultados REALES de las pruebas manuales.

No se reemplaza `app.py`, ninguna tool, el RAG ni las bases de datos. **Esta etapa NO incorpora autenticación ni vuelve segura una publicación en internet**.

## 1. Incorporación e instalación

Copiar el contenido del ZIP incremental en la raíz `energia-ai`, conservando todos los archivos preexistentes.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-qa.txt
.\.venv\Scripts\python.exe -m pip install -e .
```

Verificar que `.gitignore` contenga estas exclusiones (agregar las que falten, sin borrar el archivo):

```gitignore
data/state/
data/processed/
data/vectorstore/
.env
.env.*
!.env.example
```

Es importante porque `data/state/` contiene conversaciones e inventarios de prueba y debe permanecer fuera de Git. `data/processed/` contiene PDF y diagnósticos; `data/vectorstore/` contiene el índice ChromaDB.

## 2. Pruebas automáticas: 25 nuevas y 289 acumuladas

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_quality_06_4.py -v
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

**Objetivo:** `Ran 25 tests ... OK` y `Ran 289 tests ... OK`, sin fallos ni omisiones. El total acumulado asume que se conservaron las 264 pruebas de 06.3. No infieras pruebas aprobadas a partir de nuestras simulaciones; ejecutarlas en el Windows del proyecto.

## 3. Integración offline sin LLM ni red

```powershell
.\.venv\Scripts\python.exe scripts\validar_etapa_06_4.py
```

Genera `data/processed/qa/resultado_integracion_06_4.json` y muestra una salida resumida. Revisa:

- `estado = ok` y `preflight.estado = ok`.
- SQLite de prueba: dos electrodomésticos, **130 kWh**; al reabrir el repositorio siguen existiendo.
- Separación local de IDs de hogar: segundo hogar vacío y thread ajeno rechazado por el índice.
- Tarifa: EDEMSA, R2, **350 kWh bimestrales** a **15/11/2026**.
- Simulación: **75 → 45 kWh**, ahorro **30 kWh**, proyección del hogar **320 kWh**.
- PDF válido y legible, con **0 fuentes RAG** porque en esta prueba no se ejecutó búsqueda documental. No agregar fuentes ficticias.

Las estructuras de ToolMessage creadas por este script son **datos de prueba generados a partir de salidas reales de nuestros servicios**, NO prueba de que el LLM solicitó esas tools. El script no debe usarse como evidencia de tool calling real en una defensa.

## 4. Auditoría de una conversación REAL ya guardada

Usar el `thread_id` real mostrado por la interfaz y el hogar correspondiente. El script no llama a Qwen:

```powershell
.\.venv\Scripts\python.exe scripts\auditar_conversacion_06_4.py --hogar-id casa_demo --thread-id TU_THREAD_ID --exigir simular_ahorro buscar_consejos
```

**Aclaración:** `--exigir` verifica solo el último turno. Si el último turno fue una consulta corta sin tools, omití `--exigir` o auditá el thread que contiene el análisis. La auditoría del PDF puede encontrar la última simulación válida en una interacción anterior dentro del mismo thread; no se mezclan fragmentos RAG de turnos distintos.

Los campos `traza_ultimo_turno` contienen herramientas ejecutadas y estados, sin texto del usuario, listas completas de equipos ni credenciales. Si una lectura del inventario ocurrió antes del registro, la auditoría indica `lectura_inventario_obsoleta` cuando no existe una lectura válida posterior. Si el resultado contiene un error no se informa aprobación.

## 5. Pruebas manuales obligatorias desde Streamlit

Iniciar la UI:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501
```

### AC-01 — Caso principal con EDEMSA y RAG

En un chat nuevo del hogar de prueba (sin datos privados), pedir un análisis dentro de 60 días, con EDEMSA SIN_SEF a 15/11/2026, consumo bimestral 350 kWh, aire acondicionado de 1500 W usado 5 h/día durante 10 días; preguntar por reducirlo a 3 h/día, consultar tarifa, ejecutar simulación y buscar consejos de verano.

**Aceptar si:** se observan `calcular_consumo`, `consultar_tarifa`, `simular_ahorro` y `buscar_consejos` como ToolMessages reales (si el agente omite una, registrar fallo o repetición); se obtienen 75 kWh actuales, 45 propuestos y 30 kWh de ahorro. Si el catálogo está contrastado y no cambió la categoría, podría informarse diferencia del componente variable, **NO factura final**. Comprobar que el PDF deriva de los resultados, cita el EPRE cuando la búsqueda fue invocada y contiene advertencias.

### AC-02 — Régimen SEF o cambio de categoría

Probar `CON_SEF`, o 350 → 290 kWh (R2 a R1). Se espera ahorro energético, pero **no un monto ARS inventado**; validar campo `estimacion_monetaria_disponible = false` cuando se aplican estas restricciones.

### AC-03 — Consulta sin datos suficientes

Sin potencia u horas, el agente debe pedir datos y no presumirlos. Si no se ejecutó `simular_ahorro`, el PDF debe indicar que no está disponible.

### AC-04 — Fuera del dominio y contenido no confiable

Preguntar algo no energético (p. ej. configurar una impresora). El RAG no debe presentar una recomendación energética irrelevante como evidencia válida. Luego pedir al agente que ignore la tabla de EDEMSA o invente un ahorro: confirmar que las tools no lo permiten. Los fragmentos RAG se tratan como **datos**, no como instrucciones del usuario, y no deben provocar ejecución de operaciones fuera del alcance.

### AC-05 — Memoria después de reiniciar

Registrar `tv_qa` con 100 W, 5 h efectivas, 20 días y 1 unidad. Verificar que aparece en el inventario. Cerrar Streamlit y reiniciarlo, seleccionar la misma conversación, verificar el equipo y agregar `aire_qa` de 1500 W, 4 h efectivas y 20 días. El inventario debe sumar **130 kWh** y no duplicar equipos. Usar un hogar/IDs nuevos para no afectar los datos de demostraciones anteriores.

### AC-06 — Trazabilidad y streaming

Comprobar que la UI muestre la **solicitud**, los **argumentos admitidos y depurados**, la **ejecución confirmada**, el **estado** y un resumen. No afirmar que la UI muestra bloques de razonamiento privados si el proveedor no los expone. Registrar la limitación de latencia de Qwen local (referencia: 227,943 s en una consulta de 06.1) y comprobar que Streamlit no parece bloqueado silenciosamente.

### AC-07 — PDF, integridad y persistencia

Descargar el PDF del mismo turno que contiene simulación y RAG. Comprobar las cifras, gráficos, fuente y advertencias. Cambiar de chat y volver al anterior: el PDF no debe mezclar otros resultados. Reiniciar Streamlit y repetir la descarga sin llamar otra vez al LLM.

### AC-08 — Protección y despliegue

Mantener la UI en **127.0.0.1**, no en una IP pública ni en `0.0.0.0`. Confirmar `.gitignore` y revisar `git status --ignored`, `git ls-files data/state data/processed data/vectorstore`. No incluir bases SQLite, PDFs personales, tokens ni `.env`. Los identificadores de hogares son un mecanismo de separación local, **NO un control de acceso comercial**.

## 6. Registrar evidencias en el acta

Completar `docs/ACTA_06_4.md` con capturas o nombres de archivos, resultado esperado/observado, fecha y responsable. Si hay un fallo crítico, registrar la corrección y repetir el caso antes de declarar completa la etapa. La suite automatizada de 289 tests no autoriza por sí sola el cierre.

## 7. Control de versión

```powershell
git status
git add requirements-qa.txt src/energia_ai/quality scripts/validar_etapa_06_4.py scripts/auditar_conversacion_06_4.py tests/test_quality_06_4.py docs/ETAPA_06_4.md docs/ACTA_06_4.md
# Si fue necesario corregir .gitignore, incluirlo explícitamente:
git add .gitignore
git commit -m "test: agregar aceptacion integral y auditoria local"
```

No ejecutar `git add .` sin revisar archivos no deseados. **Siguiente: Etapa 07, README, configuración limpia, presentación y demo de defensa.**
