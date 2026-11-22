# EnergiaAI — Subetapa 03.4: integración de las tres tools

**Estado:** implementación preparada y validación final pendiente en la computadora Windows del equipo.

**Historias asociadas:** HU-01 (consumo), HU-02 (tarifas) y HU-04 (simulación de ahorro).  
**Caso de uso:** UC-01, análisis y optimización del consumo residencial para usuarios de EDEMSA en Mendoza.

## 1. Objetivo y alcance

Comprobar que `calcular_consumo`, `consultar_tarifa` y `simular_ahorro` pueden invocarse **en un mismo flujo** utilizando sus herramientas de LangChain reales, y que sus respuestas respetan contratos y unidades compatibles.

**No se implementa todavía un agente LLM**: `create_agent`, Ollama, memoria conversacional, RAG y Streamlit quedan para etapas posteriores. Este es un *harness* de pruebas; el script NO es una cuarta tool, no reemplaza al agente y no intenta interpretar lenguaje natural.

## 2. Componentes añadidos

- `scripts/demo_tools_integration.py`: invoca las tres tools con `.invoke()`, muestra un resumen ordenado por operación y comprueba consistencia matemática entre respuestas.
- `tests/test_tools_integration.py`: 10 pruebas de integración, sin entrenar ni consultar un LLM.
- `docs/ETAPA_03_4.md`: especificación y procedimientos (este archivo).

Ningún archivo de las subetapas 03.1, 03.2 o 03.3 necesita reemplazarse.

## 3. Flujo y contratos

1. **`calcular_consumo`** recibe `periodo_dias=60` y un aire de 1500 W, 5 horas efectivas durante 10 días. Devuelve `consumo_total_kwh="75.0000"`.
2. **`consultar_tarifa`** recibe EDEMSA, `fecha="2026-11-15"`, `consumo_kwh_bimestral=350`, `regimen="SIN_SEF"`. Devuelve la categoría `R2`, sus cargos y la fuente oficial. Esta consulta utiliza el catálogo Python ya cargado en RAM.
3. **`simular_ahorro`** recibe los equipos actuales y propuestos (3 horas), el período, 350 kWh bimestrales y **la respuesta íntegra y sin alterar de `consultar_tarifa`**. Calcula 45 kWh alternativos, 30 kWh de diferencia, 40 % del equipo, y 320 kWh bimestrales proyectados.
4. El script compara la línea base de `calcular_consumo` con la de `simular_ahorro`; verifica la diferencia de kWh y, cuando corresponde, el consumo del hogar proyectado.

La información tarifaria **no se vuelve a teclear, recomputar ni modificar** entre tools. El servicio de ahorro realiza su propia validación independiente de la tarifa recibida.

## 4. Política económica y limitaciones

- Solo se informa una estimación en ARS cuando el catálogo figura como `CONTRASTADO_CON_PDF_LOCAL`, el período es comparable (45 a 75 días), la categoría no cambia y el régimen es `SIN_SEF`.
- En el ejemplo válido, la diferencia estimada del **componente variable** es ARS 8.682,95, **no** la diferencia final entre facturas.
- En régimen `CON_SEF`, cambio de categoría, ausencia de consumo facturado, tarifa fuera de cobertura o catálogo pendiente, la simulación conserva kWh y explica por qué no cuantifica dinero.
- Este flujo usa consumos hipotéticos basados en potencia constante. No representa una medición ni una auditoría eléctrica.
- No se incorporan equipos nuevos en `simular_ahorro` durante esta versión. Eso requerirá actualizar el perfil y recalcular una línea base en el agente posterior.

## 5. Instalación en Windows, paso a paso

Desde la carpeta raíz `energia-ai`, en PowerShell:

1. Incorporar los tres archivos del ZIP de la Etapa 03.4 en sus rutas correspondientes, sin borrar componentes anteriores.
2. Comprobar entorno: ` .\.venv\Scripts\python.exe --version ` (debe usar Python 3.12).
3. Confirmar proyecto editable: ` .\.venv\Scripts\python.exe -m pip install -e . `.
4. Confirmar dependencia de tools: ` .\.venv\Scripts\python.exe -m pip install -r requirements-tools.txt `.
5. Ejecutar demostración normal: ` .\.venv\Scripts\python.exe scripts\demo_tools_integration.py `.
6. Ejecutar demostración SEF: ` .\.venv\Scripts\python.exe scripts\demo_tools_integration.py --regimen CON_SEF `.
7. Ejecutar cambio de categoría: ` .\.venv\Scripts\python.exe scripts\demo_tools_integration.py --horas-propuestas 1 `.
8. Ejecutar sin datos de factura: ` .\.venv\Scripts\python.exe scripts\demo_tools_integration.py --sin-factura `.
9. Ejecutar pruebas de esta subetapa: ` .\.venv\Scripts\python.exe -m unittest discover -s tests -p test_tools_integration.py -v `.
10. Ejecutar suite completa: ` .\.venv\Scripts\python.exe -m unittest discover -s tests -v `.
11. Comprobar `Ran 95 tests` y `OK`, **sin `skipped`**.
12. Registrar los archivos: ` git add scripts/demo_tools_integration.py tests/test_tools_integration.py docs/ETAPA_03_4.md `.
13. Crear commit: ` git commit -m "test: integrar tres tools energeticas" `.

## 6. Casos de aceptación

| Caso | Esperado |
|---|---|
| Normal y catálogo contrastado | 75 → 45 kWh, ahorro 30 kWh, proyección 320 kWh R2, diferencia variable ARS 8.682,95 |
| Normal y catálogo pendiente | Los mismos kWh, sin ARS, motivo explícito |
| CON_SEF | Ahorro en kWh; sin ARS |
| 5 → 1 h/día | Ahorro 60 kWh; cruce de R2 a R1 cuando fuente contrastada; sin ARS |
| Fecha fuera del cuadro | Error controlado en la tool tarifaria; simulación de kWh sin ARS |
| Sin factura | No se invoca `consultar_tarifa`; se simula solo consumo energético |
| 5 → 7 h/día | Ahorro negativo de -30 kWh; no se presenta como ahorro positivo |
| Integridad | La herramienta de ahorro recibe la misma estructura tarifaria entregada por la herramienta anterior |

La suite se compone de 85 pruebas previas + 10 pruebas nuevas = **95 pruebas**. No se considera terminada hasta validar la ejecución con `langchain-core` real en el equipo del usuario.

## 7. Justificación académica

**¿Por qué hacer integración si cada tool ya pasó su test?** Porque una tool aislada puede funcionar pero entregar datos incompatibles con los que necesita la siguiente: valores, fechas, régimen o unidades incorrectas.

**¿Por qué no crear una sexta tool “integrar_tools”?** No hay una operación de negocio nueva: solo comprobamos el funcionamiento conjunto. La coordinación definitiva la realizará `create_agent` cuando integremos el LLM.

**¿Por qué enviamos el resultado completo de `consultar_tarifa`?** Para que `simular_ahorro` pueda contrastar los datos, la fuente y las condiciones con el catálogo de memoria en vez de confiar en valores reescritos por un modelo.

**¿Qué significa que la suite esté en verde?** Confirma los casos cubiertos por el código; no demuestra que el sistema ya tenga RAG, memoria, UI o un agente autónomo.

## 8. Próximos pasos

Después de aprobar 03.4: Etapa 04 (RAG: chunking, modelo de embeddings, base vectorial ChromaDB y `buscar_consejos`). Posteriormente, agregar el modelo LLM, registrar tools en `create_agent` y configurar `InMemorySaver` y UI Streamlit con streaming.
