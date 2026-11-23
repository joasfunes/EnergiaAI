# EnergiaAI — Etapa 05.2 | Integración de cuatro tools con Qwen

**Estado:** pendiente de verificación en Windows. **Entrada:** Etapa 05.1 completada (Qwen/Ollama, 166 pruebas, `calcular_consumo` ejecutada realmente). **Salida:** agente que ofrece cuatro herramientas, registra las invocaciones y supera casos normales y de error.

## 1. Alcance

- Reutilizar, sin modificar, `calcular_consumo`, `consultar_tarifa`, `simular_ahorro` y `buscar_consejos`.
- Construir `create_agent(model=ChatOllama(...), tools=[...], system_prompt=..., checkpointer=InMemorySaver())`.
- Separar la configuración de tools (`full_agent.py`) de la ejecución y trazabilidad (`session.py`).
- Mostrar evidencia de **ToolMessage** real, no solamente texto que diga «usé una herramienta».
- Ejecutar cinco escenarios con datos de prueba: consumo, tarifa, consejos, ahorro energético y análisis integral; incluir un caso con datos faltantes.
- Comprobar continuidad en el proceso con `--escenario chat` y un `thread_id` fijo.

**No incluye:** inventario permanente de electrodomésticos, historial tras reiniciar, streaming, PDF, UI ni cálculos de factura completa. Se trabajarán en etapas posteriores.

## 2. Contratos reutilizados

| Tool | Datos indispensables | Resultado | Restricciones |
|---|---|---|---|
| `calcular_consumo` | Período, lista de equipos (ID, W, horas efectivas, días, cantidad) | kWh por equipo/total | Estimación de potencia constante, no factura |
| `consultar_tarifa` | EDEMSA, fecha, **kWh facturados bimestrales**, SIN_SEF/CON_SEF | Categoría, cargos, vigencia, fuente | No inventar régimen, no total factura |
| `simular_ahorro` | Escenario actual y propuesto del mismo equipo; opcional factura y respuesta tarifaria íntegra | Delta kWh, %, componente variable opcional | ARS solo si la tool informa `estimacion_monetaria_disponible=true` |
| `buscar_consejos` | Consulta temática, k de fragmentos (1–5) | Citas, fragmentos, URLs | Evidencia insuficiente => no inventar recomendaciones |

**Riesgo conocido:** pasar la respuesta tarifaria íntegra desde el LLM a `simular_ahorro` es frágil. Si el LLM altera campos, el motor rechaza la monetización. No eliminar esa verificación para que aparezcan pesos; la próxima refactorización podría introducir un estado tipado de ejecución para traspasar estructuras sin volver a generarlas en lenguaje natural.

## 3. Archivos nuevos

```text
energia-ai/
├── src/energia_ai/agent/full_agent.py     # Crea agente, prompt, lista de tools
├── src/energia_ai/agent/session.py        # Estado del thread y trazas por turno
├── scripts/check_full_agent.py            # Inspección SIN LLM
├── scripts/demo_full_agent.py             # Demo REAL con Qwen
├── tests/test_full_agent.py               # 8 pruebas de configuración
├── tests/test_agent_session.py            # 8 pruebas de sesión y trazas
└── docs/ETAPA_05_2.md                     # Esta documentación
```

No reemplazar ni `local_llm.py` ni los archivos de las cuatro tools ni la base ChromaDB. La configuración del modelo en `local_llm.py` se reutiliza directamente.

## 4. Implementación paso a paso en Windows

Desde la raíz de `energia-ai` en VS Code con PowerShell:

### 05.2.1 — Copiar los archivos incrementales

Extraer el ZIP y fusionar **el contenido de la carpeta `energia-ai/`** con tu proyecto local, conservando las carpetas existentes.

### 05.2.2 — Verificar entorno

```powershell
ollama list
.\.venv\Scripts\python.exe -m pip install -r requirements-llm.txt
.\.venv\Scripts\python.exe -m pip install -r requirements-rag-index.txt
.\.venv\Scripts\python.exe -m pip install -e .
```

Debés tener `qwen3.5:9b`, `embeddinggemma:300m`, el índice RAG 04.4 y el catálogo EDEMSA revisado. No es necesario descargar nuevos modelos.

### 05.2.3 — Verificar los cuatro contratos, sin LLM

```powershell
.\.venv\Scripts\python.exe scripts\check_full_agent.py
```

Se deben listar exactamente las cuatro tools y sus parámetros. El comando no genera embeddings ni llama Qwen.

### 05.2.4 — Ejecutar una consulta por herramienta

```powershell
.\.venv\Scripts\python.exe scripts\demo_full_agent.py --escenario consumo
.\.venv\Scripts\python.exe scripts\demo_full_agent.py --escenario tarifa
.\.venv\Scripts\python.exe scripts\demo_full_agent.py --escenario consejos
.\.venv\Scripts\python.exe scripts\demo_full_agent.py --escenario ahorro
```

La demo imprime, por turno, la respuesta del modelo y **los ToolMessage realmente recibidos**. Si falta una tool esperada, termina con código de salida 3. No es prueba de que el cálculo esté bien si solo el texto del LLM incluye un nombre de herramienta.

- **Consumo:** TV de 100 W x 5 h/día x 20 días = **10 kWh**.
- **Tarifa:** EDEMSA, 350 kWh facturados bimestrales, SIN_SEF, 2026-11-15 → R2 y cargos del catálogo. No es factura final.
- **Consejos:** buscar fuente oficial sobre aire acondicionado en verano. Comprobar citas y `estado=ok`.
- **Ahorro:** 1500 W, 5 → 3 h/día, 10 días dentro de un período de 60 → 75 y 45 kWh, delta 30 kWh. Sin factura → sin estimación en pesos.

### 05.2.5 — Integración integral

```powershell
.\.venv\Scripts\python.exe scripts\demo_full_agent.py --escenario integral
```

La consulta contiene datos bimestrales completos y le pide explícitamente al agente las cuatro herramientas. **Que aparezcan todas las tools es una expectativa de evaluación, no una garantía automática de Qwen**. Verificar la lista impresa; si faltan, conservar la traza y revisar la selección del modelo. Si una tool devuelve error, `sin_resultados` o estado desconocido, NO afirmar que el resultado final está validado. En particular, el ahorro en ARS solo puede provenir de una salida válida de `simular_ahorro` y puede no estar disponible aun cuando la diferencia energética sea válida.

### 05.2.6 — Datos faltantes

```powershell
.\.venv\Scripts\python.exe scripts\demo_full_agent.py --escenario faltantes
```

El modelo debería solicitar potencia/horas/consumo bimestral/régimen pertinentes. No debe improvisar el régimen SEF ni una factura ficticia.

### 05.2.7 — Conversación interactiva, mismo thread

```powershell
.\.venv\Scripts\python.exe scripts\demo_full_agent.py --escenario chat --thread-id hogar_demo
```

Probar dos consultas sucesivas en la terminal sin cerrar el programa. `InMemorySaver` comparte el mismo historial con ese `thread_id`. No hay un inventario estructurado persistente todavía: **no asumir** que agregar un equipo a un mensaje actualiza una base. Al cerrar Python, la memoria de ese proceso se pierde.

### 05.2.8 — Tests sin Ollama

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_full_agent.py -v
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_agent_session.py -v
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Hay **16 pruebas nuevas** (8 configuración, 8 sesión). Si tu suite 05.1 tenía 166 pruebas, el objetivo acumulado es **182 pruebas** sin errores ni omisiones. Estas nuevas pruebas son unitarias con dobles de prueba: no sustituyen las pruebas reales del punto 05.2.4–05.2.7.

### 05.2.9 — Git

```powershell
git status
git add src/energia_ai/agent/full_agent.py src/energia_ai/agent/session.py scripts/check_full_agent.py scripts/demo_full_agent.py tests/test_full_agent.py tests/test_agent_session.py docs/ETAPA_05_2.md
git commit -m "feat: integrar las cuatro tools en agente EnergiaAI"
```

No subir archivos de ChromaDB, copias de facturas, datos personales ni `.env`.

## 5. Aceptación y límites

- Las cuatro tools figuran en el registro con nombres y esquemas exactos.
- Los escenarios individuales muestran tool calling verdadero para las herramientas esperadas.
- El agente puede recuperar fragmentos RAG sin reconstruir el índice.
- La consulta integral es evaluada con la traza real: si Qwen no convoca todas las herramientas, se registra como limitación (no se falsifica un éxito).
- El ahorro energético proviene del servicio; el importe de factura final no se calcula.
- Los datos faltantes no se inventan; no se da valor monetario cuando las reglas lo prohíben.
- Las 182 pruebas de Python se ejecutan sin omisiones en Windows.
- Commit realizado.

**Siguiente:** 05.3 memoria y streaming, separación entre historial y datos estructurados del hogar, persistencia tras reinicio; posteriormente informe PDF e interfaz.

## Fuentes de implementación

- LangChain: https://docs.langchain.com/oss/python/langchain/agents
- ChatOllama: https://docs.langchain.com/oss/python/integrations/chat/ollama
- Checkpointer: https://docs.langchain.com/oss/python/langchain/short-term-memory
