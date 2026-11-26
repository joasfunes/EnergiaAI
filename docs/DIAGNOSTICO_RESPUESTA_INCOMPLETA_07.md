# EnergiaAI · Diagnóstico de respuestas cortadas (rama de desarrollo)

## Qué comprueba
Lee **solo** el último turno guardado en LangGraph/SQLite, sin volver a llamar a Ollama ni modificar el inventario. Compara la información de finalización del proveedor (`done_reason`, `eval_count`, `prompt_eval_count`) con el contenido que ya aparece en Streamlit. No demuestra la causa por sí solo.

## Instalación
Copiar la carpeta `scripts/`, `tests/` y `docs/` de este paquete a la raíz `energia-ai/`. No reemplaza archivos anteriores.

## Uso en Windows
Conservar el hilo que produjo la respuesta cortada. Desde la raíz del proyecto:

```powershell
.\.venv\Scripts\python.exe scripts\diagnosticar_ultimo_turno_07.py --hogar-id TU_HOGAR_ID --thread-id TU_THREAD_ID
```

`TU_HOGAR_ID`: hogar elegido en la UI. `TU_THREAD_ID`: el valor exacto mostrado como "ID de la conversación" en el sidebar. **No** lo sustituyas por el título visible del chat.

Si el diagnóstico no permite diferenciar la respuesta, opcionalmente añadir `--mostrar-final` para ver el texto guardado completo, solo en tu terminal local; no compartirlo si contiene datos privados.

Pruebas offline:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_diagnostico_ultimo_turno_07.py -v
```

## Interpretación

| Resultado | Posible explicación | Siguiente paso |
|---|---|---|
| `done_reason=length` | Generación se detuvo por límite | Revisar límite efectivo (`num_predict`), uso de contexto y memoria antes de modificar configuración |
| `done_reason=stop` y texto guardado también cortado | El modelo/proveedor finalizó así; puede ser bug o terminación prematura | Ver versión Ollama y ChatOllama; reproducir prueba aislada; conservar evidencia |
| El texto guardado es completo, pero Streamlit está cortado | Se perdieron deltas o hubo un problema de visualización | Corregir streaming/reconciliar con mensaje final del estado |
| No hay metadatos suficientes | Algunos adaptadores/versiones no almacenan estos campos | Capturar `response_metadata` durante una ejecución real; no inferir la causa |

**Advertencia:** `stop` no significa «respuesta semánticamente completa». No debemos declarar la demo aprobada si no se observa la tool y una respuesta útil. Al compartir JSON, revisar cualquier dato privado (en principio solo aparecen nombres de tools, conteos y metadatos técnicos). El script de diagnóstico no corrige el error; evita aplicar cambios a ciegas.
