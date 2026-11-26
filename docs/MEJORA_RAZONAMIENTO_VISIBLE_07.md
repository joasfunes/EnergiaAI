# EnergiaAI — Mejora: mostrar razonamiento expuesto por Qwen/Ollama

**Rama:** `feat/inventario-manual-ui` (NO hacer merge a `main` sin aceptación).  
**Propósito:** cubrir la visibilidad del bloque de razonamiento **cuando el proveedor lo expone**, según el requisito 3.5 de *Consigna Integrador.pdf* (pág. 2).  
**Modelo:** `qwen3.5:9b` con Ollama. No se cambia el modelo ni la arquitectura de las cinco tools.  
**Limitaciones de seguridad:** solo localhost y datos ficticios; el razonamiento expuesto por el proveedor puede repetir contenido del prompt. No utilizar esta interfaz para información sensible.

## 1. ¿Qué hace esta mejora?

1. `local_llm.py`: configura `ChatOllama(..., reasoning=True)` para pedir a Ollama un bloque de razonamiento **separado del texto final**.
2. `streaming.py`: recupera los deltas del campo `additional_kwargs["reasoning_content"]` (o, en adaptadores compatibles, de bloques normalizados de tipo `reasoning`) y emite eventos `tipo="razonamiento"`, distintos de `tipo="texto"` y de los eventos de tools.
3. `app.py`: agrega un panel **Razonamiento expuesto por Ollama** que se actualiza durante el streaming, separado de la respuesta del asistente y de la traza de herramientas. Usa texto literal (no Markdown) y limita la visualización a los últimos 30.000 caracteres.
4. `app.py`: si el turno terminó sin respuesta final, presenta **Ejecución incompleta**, aunque haya habido razonamiento o llamadas a tools. Un bloque de razonamiento **no es** una tarea completada.
5. La app NO guarda un registro nuevo de razonamiento en `data/processed/performance/`; únicamente se muestra lo emitido en el turno. Los estados internos que LangGraph checkpointa conservan su comportamiento previo. El panel de streaming en vivo no se reconstruye automáticamente al recargar la página.

No se cambia el motor de consumos, RAG, tarifas, simulador, inventario SQLite ni PDF.

## 2. Resguardo y copia de archivos

**Detener Streamlit** con `Ctrl+C`. Desde la raíz del proyecto:

```powershell
git status
git branch --show-current
```

La rama esperada es `feat/inventario-manual-ui`. Si hay modificaciones locales, hacer primero un commit provisional o copiar los archivos para comparar. **No aplicar `-Force` a ciegas si hay código personalizado que quieran conservar.**

Descomprimir el ZIP dentro de la raíz (sin crear otra carpeta envolvente). Se reemplazan:

```text
app.py
src/energia_ai/agent/local_llm.py
src/energia_ai/agent/streaming.py
```

Y se agregan:

```text
scripts/probar_razonamiento_ollama_07.py
tests/test_reasoning_stream_07_3.py
docs/MEJORA_RAZONAMIENTO_VISIBLE_07.md
```

No borrar `data/state`, el índice de ChromaDB, ni los electrodomésticos existentes.

## 3. Validar antes de Streamlit

Comprobar modelos instalados:

```powershell
ollama list
.\.venv\Scripts\python.exe scripts\check_ollama_llm.py
```

Ejecutar el diagnóstico **real y directo** (requiere Ollama, puede tardar):

```powershell
.\.venv\Scripts\python.exe scripts\probar_razonamiento_ollama_07.py
```

En la consola deben aparecer encabezados `[Razonamiento expuesto por Ollama]` y `[Respuesta final]` **solo si fueron generados**. Al final figuran `reasoning_chars` y `respuesta_chars`. Para considerar el canal disponible, `reasoning_chars > 0`; para que exista respuesta completa, `respuesta_chars > 0`. La primera medición no garantiza que todos los turnos expongan razonamiento.

Si Ollama produce un `ResponseError`, leer los registros locales y comprobar la versión y disponibilidad del modelo. **No concluir que la herramienta funciona si no se recibe razonamiento real.**

## 4. Ejecutar las pruebas

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_reasoning_stream_07_3.py -v
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Las 9 pruebas nuevas y las pruebas anteriores de streaming/local LLM pasaron en una revisión offline con mensajes simulados. **No son evidencia de que tu equipo haya transmitido razonamiento real**. Si tenías 309 pruebas en la rama y todas estaban habilitadas, el total **potencial** es 318 (309 + 9); verificar el número real sin omisiones en Windows.

## 5. Probar Streamlit en vivo

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501
```

Seleccionar un hogar **ficticio** ya registrado y crear una conversación nueva.

**Consulta A — básica, para comprobar la separación de canales:**

> ¿Qué función cumple una base de datos vectorial en un sistema RAG? Respondé en dos oraciones, en español.

Se espera una respuesta normal. Si Ollama expone razonamiento, el panel independiente se irá completando mientras el modelo trabaja. Si no lo expone, la interfaz indicará **El proveedor no expuso razonamiento en este turno**; no se inventa contenido.

**Consulta B — tool calling real:**

> Consultá mi inventario persistente y calculá el consumo de todos los electrodomésticos guardados durante 60 días. Usá `consultar_inventario` y `calcular_consumo`. Respondé con una tabla y un total.

Deben observarse **tres cosas diferentes**: (a) razonamiento del proveedor, si aparece; (b) solicitudes y ejecuciones efectivas de tools; (c) respuesta final. La tool debe estar en la traza con estado comprobable; una intención expresada en razonamiento NO equivale a tool ejecutada.

**Consulta C — flujo integral:** ejecutar el caso verificado de EDEMSA / ahorro / `buscar_consejos`, comprobar herramientas y PDF. La opción `reasoning=True` podría afectar latencia, contexto y estabilidad: no debe aceptarse sin prueba funcional real.

## 6. Criterios de aceptación

- [ ] Rama nueva/actual comprobada; `main` intacta.
- [ ] Diagnóstico directo evidencia `reasoning_chars > 0` y `respuesta_chars > 0` al menos en un turno.
- [ ] El panel **Razonamiento expuesto por Ollama** aparece separado de la respuesta final.
- [ ] El panel se actualiza **durante** la generación, no solo al final.
- [ ] La traza de cada herramienta ejecutada conserva nombre, argumentos permitidos, estado y resumen.
- [ ] `consultar_inventario`, `calcular_consumo`, `consultar_tarifa`, `simular_ahorro`, `buscar_consejos` continúan disponibles.
- [ ] El chat no presenta un razonamiento aislado como respuesta completa.
- [ ] Persistencia de inventario y conversaciones, más generación de PDF, sin regresiones.
- [ ] 9 pruebas nuevas y suite completa sin fallos/omisiones inesperadas.
- [ ] README y PowerPoint actualizados antes de la defensa.

**IMPORTANTE:** haber programado el panel no significa haber cumplido automáticamente con el requisito de la cátedra. Es necesario mostrar razonamiento efectivamente recibido del proveedor, en tiempo real, en la UI junto al flujo de tools.

## 7. Texto sugerido para incorporar al README

> **Visibilidad de razonamiento:** EnergiaAI solicita a Ollama el canal separado de razonamiento de Qwen3.5 9B mediante `ChatOllama(reasoning=True)`. Cuando el proveedor lo entrega, Streamlit lo muestra durante el streaming en un panel desplegable independiente de la respuesta final y la traza de herramientas. El contenido no es validación de cálculos ni evidencia de ejecución de tools; esas ejecuciones se comprueban en la traza. Si el proveedor no entrega el canal, la interfaz lo indica sin inventarlo. La disponibilidad y estabilidad dependen de la versión local de Ollama y de Qwen. La aplicación no utiliza autenticación y debe permanecer en localhost.

## 8. Texto para la presentación de defensa

> Implementamos el requisito de visibilidad del razonamiento cuando el proveedor lo expone. El `ChatOllama` del agente solicita `reasoning=True`; el streaming reenvía dos canales distintos: `razonamiento` y `texto`. La UI muestra el razonamiento en un panel y mantiene la respuesta final y las tools por separado. **No fabricamos pasos internos**; si el proveedor no emite el canal, lo declaramos. Los cálculos siguen realizándose exclusivamente por nuestras herramientas Python.

## 9. Errores conocidos y reversión

Una salida únicamente de razonamiento, sin respuesta final, sigue siendo un **fallo de completitud**. Ya se observaron respuestas vacías e intermitencia de Qwen3.5 9B; habilitar el panel no las repara. Si esta versión empeora el tool calling, volver a la versión previa desde Git después de guardar las evidencias.

Para revertir *solo la configuración del modelo* durante un diagnóstico, retirar temporalmente `reasoning=True` de `local_llm.py`, reiniciar Streamlit y crear una conversación nueva. Eso hará que el canal separado pueda dejar de estar disponible; **no es una solución para el requisito de razonamiento**.

## 10. Versionado

Si las pruebas pasan y se observa la UI en vivo:

```powershell
git add app.py src/energia_ai/agent/local_llm.py src/energia_ai/agent/streaming.py scripts/probar_razonamiento_ollama_07.py tests/test_reasoning_stream_07_3.py docs/MEJORA_RAZONAMIENTO_VISIBLE_07.md
git diff --cached --stat
git commit -m "feat: mostrar razonamiento de Ollama en Streamlit"
git push
```

No fusionar aún a `main` hasta finalizar la prueba integral.

**Referencias técnicas:** documentación oficial de `ChatOllama` sobre `reasoning=True` y `additional_kwargs['reasoning_content']`; documentación de Ollama sobre `message.thinking` y streaming; **Consigna Integrador**, requisito 3.5 y criterio 4 (págs. 2 y 4).
