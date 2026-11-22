# Etapa 05.1 — Integración piloto de Qwen local con LangChain

Fecha de inicio prevista: 22 de noviembre de 2026. Estado: pendiente de ejecutar en Windows.

## Cierre de Etapa 04

La comparación 04.3 vs. 04.4 confirma Source Hit@3 87,5 % (sin cambios),
Hit útil@3 87,5 % → 100 %, precisión útil@3 45,83 % → 58,33 %, precisión temática
75 % → 83,33 %, Source MRR 0,7292 → 0,8125 y rechazo de las 2 consultas fuera de dominio.
La completitud documental sigue limitada (4/24 → 5/24). Estas métricas provienen de
8 consultas dentro de dominio y 2 fuera; no miden exactitud de respuestas generadas.

Decisión: cerrar Etapa 04 para el MVP académico con limitaciones documentadas y controles
sobre información incompleta; mantener el RAG actual sin más reconstrucciones.

## Objetivo de 05.1

Demostrar que el LLM `qwen3.5:9b` ejecutado localmente en Ollama puede comunicarse con
LangChain y realizar al menos una llamada real a la tool `calcular_consumo`.
Probaremos también `InMemorySaver` durante dos turnos, sin considerarlo persistencia a disco.

### Incluye

- Diagnóstico HTTP local de Ollama y presencia del modelo.
- Crear `ChatOllama` usando la instalación local.
- Agente piloto con `create_agent`, una tool y un checkpointer efímero.
- Verificar un `ToolMessage` real (no basta que el LLM declare intención de llamar).
- Pruebas unitarias determinísticas de configuración y trazabilidad.

### Fuera del alcance

- Integrar simultáneamente las cuatro tools (próxima subetapa).
- Generar PDF, construir interfaz, historial tras reinicio.
- Streaming y evaluación del caso de uso completo.
- Asegurar que Qwen funcione siempre: necesitamos probarlo en el equipo Windows.

## Paso a paso (PowerShell en la raíz `energia-ai`)

1. Copiar los siete archivos nuevos manteniendo los anteriores.
2. Comprobar Ollama: `ollama --version` y `ollama list`.
3. Descargar el modelo: `ollama pull qwen3.5:9b` (una sola vez).
4. Instalar dependencias: `.\.venv\Scripts\python.exe -m pip install -r requirements-llm.txt`.
5. Mantener editable el proyecto: `.\.venv\Scripts\python.exe -m pip install -e .`.
6. Diagnóstico: `.\.venv\Scripts\python.exe scripts\check_ollama_llm.py`.
7. Piloto real: `.\.venv\Scripts\python.exe scripts\demo_llm_tool_call.py`.
8. Verificar que aparezca `TOOL EJECUTADA: calcular_consumo` y que el resultado sea
   10 kWh en el ejemplo de TV de 100 W durante 5 h/día por 20 días.
9. Verificar que el segundo turno recuerde el consumo, reutilizando `thread_id`.
10. Ejecutar `.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_local_llm.py -v`.
11. Ejecutar la suite completa y registrar en Git cuando pase.

## Arquitectura

Usuario de prueba → `create_agent` → `ChatOllama(qwen3.5:9b)` → `calcular_consumo`
→ servicio de consumo Python → `ToolMessage` → respuesta del LLM.

`InMemorySaver` guarda mensajes dentro de **un proceso** y diferencia conversaciones por
`thread_id`. Su información se pierde al reiniciar el programa. El catálogo de tarifas en
RAM y ChromaDB son mecanismos distintos que NO constituyen memoria conversacional.

## Seguridad y calidad

- Solo servidor Ollama HTTP local. No habilitamos endpoints remotos ni claves.
- No incluir PII ni facturas reales en ejemplos o repositorios.
- No aceptar cálculos monetarios al no exponer la tool de tarifas en este piloto.
- Distinguir texto generado y operaciones realizadas de verdad.
- Evitar `--rebuild` de ChromaDB: esta etapa no altera el RAG.
- Qwen en 16 GB VRAM es una opción plausible, pero comprobar GPU usando `ollama ps`.

## Criterios de cierre

- `check_ollama_llm.py` detecta Qwen descargado.
- `demo_llm_tool_call.py` produce al menos un `ToolMessage` real de consumo.
- Respuesta cita 10 kWh y no un precio inventado.
- Segundo turno conserva el contexto mientras el proceso sigue abierto.
- 11 nuevas pruebas pasan; suite acumulada esperada: 166 (155 + 11), sin omisiones.
- Commit registrado: `feat: conectar Qwen local y validar tool calling inicial`.

**Nota:** la memoria más allá del reinicio y el streaming se desarrollarán y evaluarán en
subetapas posteriores. La presencia de `InMemorySaver` aquí es solo una comprobación inicial.
