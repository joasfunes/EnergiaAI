# EnergiaAI — Etapa 06.1: Rendimiento, trazabilidad y consistencia

**Estado:** preparado para ejecutar en Windows 11.  
**Fecha:** 23 de noviembre de 2026.  
**Decisión de producto:** se mantiene **Qwen3.5 9B en Ollama**. No se compara ni reemplaza el modelo en esta subetapa.

## 1. Cierre de la Etapa 05

Según los resultados confirmados por el equipo: 213 pruebas aprobadas, agente con `create_agent`, 6 tools (4 energéticas y 2 de inventario), ChromaDB y EmbeddingGemma, memoria e inventario persistentes mediante SQLite y streaming. Esto certifica el alcance académico comprobado, **no** el estado de producción o comercial de la aplicación.

## 2. Necesidad y objetivo

Durante las pruebas en Windows 11 (Ryzen 7 5700U, 16 GB RAM) se observaron demoras de varios minutos. Se conserva el LLM actual y se construye una medición por turno que permita conocer:

- duración **total** del turno, medida con reloj monotónico;
- tiempo hasta el primer **texto visible** (no equivale necesariamente al primer token interno ni al primer evento);
- cantidad y duración observada de las llamadas a modelo por callbacks, si son propagados;
- nombre, parámetros permitidos, estado, resumen de resultado y duración observada de cada tool;
- evidencia de tools ejecutadas recuperada de `updates`, aunque no se reciban callbacks de tiempo.

El streaming facilita observar progreso, pero no asegura inferencia más rápida. No ejecutamos un benchmark de varios modelos ni cambiamos parámetros de Qwen.

## 3. Archivos afectados

| Archivo | Acción | Responsabilidad |
|---|---|---|
| `src/energia_ai/agent/telemetry.py` | Nuevo | Registrar tiempos y llamadas sin conversaciones ni datos privados |
| `scripts/benchmark_agent_06_1.py` | Nuevo | Medir exactamente un turno real, mostrar eventos y guardar resumen JSON |
| `tests/test_telemetry_06_1.py` | Nuevo | 16 pruebas sin dependencia de modelo/GPU |
| `src/energia_ai/agent/streaming.py` | Modificado | Aceptar callbacks opcionales sin cambiar el comportamiento previo |
| `src/energia_ai/agent/inventory_tools.py` | Modificado | Retornar `inventario_actualizado` después de guardar equipo |
| `src/energia_ai/agent/persistent_runtime.py` | Modificado | Explicar orden registrar → consultar; evitar llamadas paralelas para ese flujo |
| `docs/ETAPA_06_1.md` | Nuevo | Documentar la subetapa y resultados esperados |

**No se modifica:** Qwen, Ollama, la base ChromaDB, los embeddings, los cálculos energéticos, la estructura de SQLite, los esquemas de tarifas o las tools de ahorro.

## 4. Integración de trazabilidad

Las llamadas a funciones (`on_tool_start`, `on_tool_end`) permiten medir el intervalo que el cliente observa dentro de una tool. Las llamadas a modelo (`on_chat_model_start`, `on_llm_end`) permiten obtener duraciones observadas. En ambos casos depende de que LangChain propague callbacks. Se utiliza `stream_mode=['messages','updates']` para conservar la visualización existente; cuando existe un `ToolMessage` sin callback, se registra su ejecución con `duracion_s: null` y `origen: 'stream_updates_sin_tiempo'`.

Los resultados de la medición se guardan en `data/processed/performance/medicion_06_1.json`, **sin** mensajes del usuario o del LLM y sin nombres, identificadores del hogar o contenido íntegro de herramientas. Los campos de argumentos expuestos son numéricos/códigos permitidos. El directorio `data/processed/` debe permanecer ignorado por Git como en etapas anteriores.

No es telemetría de bajo nivel del servidor Ollama: para analizar GPU/CPU sigue disponible `ollama ps`. Las duraciones de las tools pueden superponerse si LangChain las ejecuta simultáneamente, por lo que no deben sumarse como si todas fueran secuenciales.

## 5. Consistencia al registrar electrodomésticos

En 05.3 se observó un caso donde el LLM **consultó el inventario antes de registrar** y posteriormente comunicó el estado obsoleto. El cambio incorpora dos defensas:

1. Instrucción explícita de registrar, esperar el resultado y consultar, sin solicitar ambas tools en paralelo.
2. `registrar_electrodomestico` devuelve el inventario posterior a la escritura mediante `inventario_actualizado`.

La segunda medida proporciona evidencia post-registro incluso si Qwen invoca herramientas en un orden inadecuado. **No garantiza por sí sola que el modelo respete el orden**; la interfaz debe considerar el resultado posterior como fuente de verdad, y la consistencia concurrente completa queda fuera del MVP.

## 6. Procedimiento en Windows

1. Hacer `git status` y verificar que el árbol esté limpio. Opcionalmente crear una rama `git switch -c etapa-06-1`.
2. Copiar los siete archivos del ZIP, combinando carpetas. Se **reemplazan** `streaming.py`, `inventory_tools.py` y `persistent_runtime.py`. Guardar respaldo antes de reemplazar si hubo cambios propios.
3. Desde la raíz del proyecto, mantener el entorno actual: ` .\.venv\Scripts\python.exe -m pip install -e .`.
4. Ejecutar las pruebas nuevas: ` .\.venv\Scripts\python.exe -m unittest discover -s tests -p test_telemetry_06_1.py -v`. Resultado objetivo: **16 tests, OK**.
5. Ejecutar la suite completa: ` .\.venv\Scripts\python.exe -m unittest discover -s tests -v`. Resultado objetivo: **229 tests**, sin fallos ni omisiones en la máquina de desarrollo.
6. Mantener Ollama abierto y verificar `ollama list`: modelo `qwen3.5:9b` disponible.
7. Ejecutar **un solo turno de diagnóstico**: ` .\.venv\Scripts\python.exe scripts\benchmark_agent_06_1.py`. No descargar ningún modelo adicional.
8. Opcionalmente, durante la consulta, ejecutar `ollama ps` en otra ventana para observar `PROCESSOR`.
9. Revisar los eventos en consola y `data/processed/performance/medicion_06_1.json`.
10. Para comprobar registro post-escritura, usar una conversación de prueba con un ID nuevo y luego ejecutar `inspect_inventory.py`; no registrar un `tv_1` que ya exista.
11. Registrar los cambios con Git una vez comprobados.

### Ejemplo de métrica (solo ilustrativo)

```json
{
  "schema_version": "06.1.1",
  "duracion_total_s": 145.2,
  "tiempo_primera_salida_s": 87.1,
  "llamadas_modelo": 2,
  "duracion_modelo_observada_s": 139.8,
  "herramientas": [
    {
      "nombre": "calcular_consumo",
      "duracion_s": 0.02,
      "estado": "ok",
      "argumentos": {"periodo_dias": 20},
      "resultado": {"estado": "ok", "consumo_total_kwh": "10.0000"}
    }
  ]
}
```

Los tiempos del ejemplo **no son resultados medidos** y las cifras reales dependerán de la ejecución local.

## 7. Pruebas, aceptación y limitaciones

Aprobamos 06.1 cuando:

- las 16 pruebas adicionales y la suite completa funcionen en Windows sin omisiones;
- el script real termine con Qwen3.5 9B y el resultado esperado de **10 kWh** para 100 W × 5 h/día × 20 días;
- el JSON muestre el tiempo total y datos de tools realmente observadas;
- las tools sin callbacks se representen sin atribuirles un tiempo inventado;
- la salida no contenga consultas privadas ni identificadores del hogar;
- se compruebe el inventario posterior a una escritura y se verifique la persistencia anterior;
- se registre el commit.

**Pendiente para 06.2:** representación en la interfaz de eventos por tool y mensajes de streaming; no introducir una capa de seguridad multiusuario aún inexistente.

## 8. Riesgos documentados

- El equipo actual puede tardar varios minutos por turno; no se promete una latencia comercial.
- El orden de tools sigue siendo una decisión probabilística del LLM. El snapshot post-escritura reduce el impacto, pero no bloquea todas las ejecuciones paralelas.
- SQLite del MVP no cuenta con autenticación multiusuario ni cifrado incorporado.
- Las trazas muestran campos seleccionados, no argumentos/respuestas íntegros de datos sensibles. Para la demo de la cátedra eso debe explicarse.
- Si no se propagan callbacks, `llamadas_modelo` y tiempos por modelo no son exhaustivos; se registra una evidencia de `updates` para tools.

## 9. Siguiente paso

**Etapa 06.2 — Interfaz Streamlit** con chat, selección de hogar/thread, historial, estado y eventos de herramientas; se reutilizarán los eventos de `telemetry.py` y `streaming.py` sin duplicar cálculos. **06.3:** informe y gráfico descargable. **06.4:** pruebas integrales de UI. **07:** entrega reproducible y defensa.
