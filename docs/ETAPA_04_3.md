# Etapa 04.3 — Evaluación de recuperación del RAG

**Estado inicial:** pendiente de ejecutar sobre el índice real del usuario. **No se modifica la tool `buscar_consejos` ni ChromaDB.**

## Objetivo

Medir si el sistema recupera evidencia útil, completa y trazable para el caso de uso de EnergiaAI. La evaluación se hace **sin LLM evaluador** y **sin respuestas generadas por el agente**, que todavía no está implementado. Las pruebas unitarias no garantizan pertinencia semántica.

## Alcance y relación con la teoría

- Estrategia bajo evaluación: chunking por ventana de 900 caracteres, overlap de 130, separación por página PDF.
- Embeddings: `embeddinggemma:300m` con Ollama.
- Almacenamiento: índice ChromaDB creado en 04.1.
- Tool real: `buscar_consejos`, creada en 04.2 (invocación por `.invoke()`).
- El *Research side* prepara las fuentes y la evaluación; el runtime del futuro agente usa el índice, **no CSV por consulta**.

## Preguntas de evaluación

Se incluyen **ocho preguntas dentro del dominio** (tres sobre invierno, tres sobre verano y dos sobre eficiencia general) y **dos preguntas fuera de dominio**. Cada pregunta de dominio contiene una **fuente esperada**; esta expectativa ayuda a diagnosticar la búsqueda, pero no confirma que los fragmentos respondan a la pregunta. Las preguntas fuera de dominio permiten observar si el buscador sigue devolviendo resultados; esto es esperable en una búsqueda vectorial sin filtro de relevancia, y no debe interpretarse por sí solo como respuesta válida.

Los casos están en `src/energia_ai/rag/evaluation.py`. Se pueden ampliar **solo si las preguntas y fuentes esperadas se justifican documentalmente**.

## Métricas automáticas

- **Source Hit@k:** porcentaje de preguntas del dominio donde aparece al menos una vez el documento esperado entre las primeras `k` posiciones.
- **Source MRR@k:** promedio de `1/rango` de la primera aparición del documento esperado; 0 cuando no aparece.
- **Consultas con error:** llamadas que fallaron o devolvieron estructura inválida.
- **Casos fuera de dominio con fragmentos:** indicador de que Chroma devuelve vecinos incluso para preguntas sin relación; **no equivale a alucinación**.
- **Señales de chunking:** reglas simples sobre mayúsculas al inicio y puntuación al final; son avisos heurísticos, no errores confirmados.

**Importante:** estas medidas no son *Recall@k* clásico ni precisión de relevancia: no tenemos un conjunto exhaustivo de fragmentos relevantes etiquetados.

## Revisión manual obligatoria

Calificar cada resultado de las **diez preguntas**, según la evidencia del texto original:

- `relevancia_manual`: **0** (no pertinente), **1** (relacionado al contexto), **2** (ayuda directamente a responder).
- `cita_verificada_manual`: `true` si la URL y, si corresponde, la página realmente apoyan el fragmento; `false` en caso contrario.
- `fragmento_completo_manual`: `true` si conserva suficiente contexto para comprender la recomendación; `false` si se corta o mezcla contenido.
- `observaciones`: explicación corta de defectos, datos numéricos dudosos o sugerencias.

El archivo JSON es **un artefacto de evaluación**, no una base de datos de la aplicación. Guardarlo fuera del flujo del agente es coherente con la simplificación pedida por la cátedra.

Con las marcas completas se calculan:

- **Precisión temática@k:** fragmentos con relevancia 1 o 2 / (k × preguntas del dominio).
- **Precisión útil@k:** fragmentos con relevancia 2 / (k × preguntas del dominio).
- **Hit útil@k:** porcentaje de preguntas del dominio que contienen al menos un fragmento calificado con 2.
- **Citas revisadas y fragmentos completos:** recuentos humanos.

Un fragmento fuera de dominio que parece relacionado se etiqueta según el contenido; no se debe asignar 0 automáticamente sin leerlo.

## Pasos en Windows (terminal PowerShell, carpeta `energia-ai`)

### 1. Incorporar archivos

Descomprimir el ZIP de 04.3 y copiar su contenido en la **carpeta existente `energia-ai`**, combinando carpetas. No borrar los archivos anteriores. Esta ampliación agrega:

```text
src/energia_ai/rag/evaluation.py
scripts/evaluate_rag.py
scripts/score_rag_review.py
tests/test_rag_evaluation.py
docs/ETAPA_04_3.md
```

### 2. Comprobar servicios y dependencias

```powershell
ollama list
.\.venv\Scripts\python.exe -m pip install -e .
```

Verificar que sigue disponible `embeddinggemma:300m` y que existe `data/vectorstore/energiaai_rag_manifest.json`. No volver a indexar ni descargar el corpus.

### 3. Probar el módulo nuevo (sin Ollama)

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_rag_evaluation.py -v
```

Se esperan **16 pruebas nuevas** (simuladas). La suite acumulada sería **142 pruebas** (126 previas + 16 nuevas) en la computadora del usuario si conserva la misma versión del proyecto:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

### 4. Ejecutar evaluación real

```powershell
.\.venv\Scripts\python.exe scripts\evaluate_rag.py
```

La herramienta se invoca diez veces con `max_resultados=3`; cada pregunta se convierte en embedding y se consulta ChromaDB. Se guarda el archivo:

```text
data/processed/rag/evaluacion_04_3.json
```

El reporte contiene resultados, fragmentos, distancias, fuente y campos de revisión. El script también muestra Source Hit@3 y Source MRR@3. **No reutiliza embeddings de la pregunta** entre ejecuciones, ni reconstruye documentos.

### 5. Revisar el JSON manualmente

Abrir `evaluacion_04_3.json` en VS Code. Localizar cada entrada de `"resultados"` y completar:

```json
"relevancia_manual": 2,
"cita_verificada_manual": true,
"fragmento_completo_manual": false,
"observaciones": "Pertinente, pero la última oración está cortada."
```

**Ejemplo únicamente:** asignar los valores que correspondan en cada caso, no copiarlos indiscriminadamente. Revisar especialmente el PDF nacional que anteriormente mostró texto repetido y las publicaciones del EPRE con frases cortadas. Para valores numéricos como porcentajes de ahorro, contrastar el pasaje con la fuente original; la recuperación no valida las cifras.

La regla `posible_inicio_cortado` o `posible_final_cortado` es una **alerta de revisión**, no una clasificación definitiva. Leer el texto original antes de decidir.

### 6. Obtener métricas manuales

```powershell
.\.venv\Scripts\python.exe scripts\score_rag_review.py
```

Si faltan etiquetas, indicará cuáles. Cuando estén todas, mostrará las métricas y generará:

```text
data/processed/rag/evaluacion_04_3_resumen.json
```

### 7. Interpretar y decidir

Criterios orientativos propuestos para la entrega (no son umbrales del profesor):

1. No quedan errores de tool ni atribuciones erróneas de URL/página.
2. `hit_util_at_k >= 0.75` (al menos seis de ocho preguntas obtienen un fragmento directamente útil).
3. Las citas manuales verifican todas las recomendaciones que utilizaremos.
4. Los fragmentos defectuosos quedan identificados y no se utilizan para justificar cifras sin contexto.

Si hay fallas importantes de extracción, **primero** limpiar el corpus de 02.3 y reconstruir el índice con `--rebuild`, siempre guardando copia del reporte anterior para comparar. Si el problema es contexto cortado, evaluar un cambio a chunking por párrafos/recursivo en una iteración posterior. Si el problema es la posición de recomendaciones útiles, estudiar *reranking* o MMR más adelante.

No incorporar Parent Document, HyDE o Self Query solamente para sumar técnicas: deben responder a una falla observada.

### 8. Git

Los datos evaluados están dentro de `data/processed/` (ignorado por Git). No subirlos por accidente. Versionar **código y protocolo de evaluación**:

```powershell
git status
git add src/energia_ai/rag/evaluation.py scripts/evaluate_rag.py scripts/score_rag_review.py tests/test_rag_evaluation.py docs/ETAPA_04_3.md
git commit -m "test: evaluar recuperacion y relevancia del RAG"
```

Si para la defensa querés incluir resultados anónimos y revisados, más adelante podremos agregar un resumen en `docs/` (no se publica automáticamente ni se incluyen datos privados).

## Límite de esta evaluación

Se evalúa **recuperación**, no la redacción final de un LLM ni la veracidad de todos los porcentajes que aparezcan en el material. La herramienta devuelve evidencia; el futuro agente debe respetar las fuentes y no obedecer instrucciones incluidas en documentos.

## Criterio de cierre de 04.3

- Diez consultas reales ejecutadas con `buscar_consejos` y sin errores internos.
- Reporte JSON completo y revisión humana realizada.
- Métricas automáticas y manuales calculadas e interpretadas.
- Decisión documentada sobre mantener o ajustar chunking, con evidencia.
- Pruebas automatizadas sin fallos ni omisiones en Windows; commit registrado.

**Siguiente:** Etapa 05, integración del modelo conversacional y comprobación de tool calling. La memoria, UI y PDF se construirán en etapas posteriores.
