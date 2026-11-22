# EnergiaAI · Etapa 04.4 — Optimización controlada y reevaluación del RAG

**Estado:** pendiente de ejecución en Windows. No declarar una mejora sin contrastar resultados reales.

## 1. Motivación y alcance

La evaluación de 04.3 (8 consultas energéticas y 2 ajenas al dominio) detectó:

| Indicador inicial | Línea base informada |
|---|---:|
| Source Hit@3 | 7/8 = 87,5 % |
| Hit útil@3 | 7/8 = 87,5 % |
| Precisión útil@3 | 11/24 = 45,83 % |
| Fragmentos suficientemente completos | 4/24 = 16,67 % |
| Casos fuera de dominio que devolvieron fragmentos | 2/2 |

Esto es un *baseline*, no representa la precisión de respuestas de Qwen ni una garantía sobre los porcentajes energéticos.

Objetivo: mejorar integridad y pertinencia de fragmentos sin cambiar EmbeddingGemma, ChromaDB ni el contrato `buscar_consejos(consulta, max_resultados)`.

## 2. Cambios de código

| Archivo | Modificación |
|---|---|
| `src/energia_ai/rag/chunking.py` | `clean_retrieval_text` elimina ruido repetitivo y normaliza caracteres; `split_text_recursive` privilegia párrafos y luego oraciones, con overlap **aproximado** y límite de 900 caracteres; preserva páginas de PDF. |
| `src/energia_ai/rag/vector_store.py` | Identifica si la consulta indica claramente verano o invierno. Recupera candidatos adicionales y excluye publicaciones de la estación opuesta, conservando la guía nacional. Nueva huella del índice (`chunk_strategy`). |
| `src/energia_ai/rag/retrieval.py` | Control experimental de evidencia: descarta candidatos con distancia **mayor que 1,45**, sin interpretarla como probabilidad. Debe calibrarse con más preguntas. |
| `scripts/backup_rag_04_4.py` | Crea copia del índice y de la evaluación previa y permite recuperación manual si hay una regresión. |
| `scripts/evaluate_rag_04_4.py` | Ejecuta las mismas 10 preguntas, guarda un reporte nuevo, no sobrescribe el baseline. |
| `scripts/compare_rag_04_4.py` | Compara métricas automáticas y manuales cuando están calificadas. |
| `scripts/spotcheck_rag_04_4.py` | Ejecuta ocho preguntas adicionales no utilizadas al diseñar el control. |
| `tests/test_rag_quality.py` | Nuevas pruebas unitarias sin conexiones externas. |

**Limitaciones técnicas deliberadas:** el splitter no reconstruye columnas de PDFs ni corrige cifras ambiguas. El filtro estacional solo actúa cuando la consulta es clara. El valor de distancia 1,45 es provisional y específico de este modelo/vectorstore; no es un criterio universal de relevancia.

## 3. Procedimiento en Windows — desde la raíz de `energia-ai`

### Paso 04.4.1 — Estado inicial y copia de seguridad

1. Confirmar que todas las modificaciones previas están guardadas (`git status`).
2. Cerrar procesos o aplicaciones Python que estén consultando ChromaDB.
3. Copiar los archivos incrementales del ZIP a la carpeta `energia-ai`; se reemplazan **tres módulos anteriores**. No tocar `data/`.
4. Crear respaldo del índice **antes de reconstruir**:

```powershell
.\.venv\Scripts\python.exe scripts\backup_rag_04_4.py
```

El programa informa un nombre `YYYYMMDDTHHMMSSZ`. Guardar ese nombre. En `data/processed/rag/` quedará `evaluacion_04_3_baseline.json` para la comparación si estaba presente el reporte anterior.

**El respaldo es local** y está dentro de `data/vectorstore/rag_backups/`, que ya ignoramos con `.gitignore`. Se recomienda conservar también una copia fuera del repositorio.

### Paso 04.4.2 — Validar cambios sin Ollama

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_rag_quality.py -v
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Se añaden 13 pruebas. Esperamos **155** en total, **sin fallos ni omisiones** en tu entorno. La suite anterior contenía 142.

### Paso 04.4.3 — Reconstruir el índice (una sola vez)

```powershell
.\.venv\Scripts\python.exe scripts\build_rag_index.py --rebuild
```

Este comando **borra y recrea la colección actual** después de generar los nuevos embeddings. No ejecutarlo antes del respaldo. Los documentos originales Markdown permanecen intactos. Verificar `chunk_strategy=recursive_paragraph_sentence_v2` en el manifiesto nuevo.

### Paso 04.4.4 — Búsquedas manuales y de control

```powershell
.\.venv\Scripts\python.exe scripts\demo_advice_tool.py "¿Cómo reducir el consumo eléctrico durante los días de mucho calor en Mendoza?"
.\.venv\Scripts\python.exe scripts\demo_advice_tool.py "¿Qué consejos existen sobre calefacción en invierno?"
.\.venv\Scripts\python.exe scripts\demo_advice_tool.py "¿Cómo configurar una impresora inalámbrica?"
.\.venv\Scripts\python.exe scripts\spotcheck_rag_04_4.py
```

Para consultas fuera de dominio esperamos idealmente `estado=sin_resultados` y una advertencia. No afirmarlo si la ejecución real devuelve otra cosa. Para consultas de verano comprobar que no se utilicen fragmentos específicos de invierno. La guía nacional puede aparecer en cualquier estación.

### Paso 04.4.5 — Crear una evaluación nueva, sin borrar la anterior

```powershell
.\.venv\Scripts\python.exe scripts\evaluate_rag_04_4.py
```

Se genera `data/processed/rag/evaluacion_04_4.json` con las mismas diez preguntas de la versión anterior y campos de revisión `null`.

Completar **cada resultado** con los mismos criterios de 04.3: `relevancia_manual` (0/1/2), `cita_verificada_manual` (bool), `fragmento_completo_manual` (bool), `observaciones` (texto). Si una pregunta devuelve cero fragmentos no hay resultados que puntuar.

### Paso 04.4.6 — Comparar antes/después

```powershell
.\.venv\Scripts\python.exe scripts\compare_rag_04_4.py
```

Genera `data/processed/rag/comparacion_04_4.json`. Si faltan revisiones manuales, la comparación lo indica y no presenta métricas manuales como completas. No es correcto concluir «mejoró» solo porque la distancia bajó.

**Nota:** si tu evaluación revisada 04.3 está guardada con otro nombre, copiala como `data/processed/rag/evaluacion_04_3_baseline.json` antes de comparar; nunca recrees el baseline ejecutando nuevamente las preguntas.

### Paso 04.4.7 — Revertir si es necesario

Si la nueva indexación falla o las métricas muestran regresión, **cerrar los procesos que usan ChromaDB**, restaurar el respaldo con el identificador obtenido:

```powershell
.\.venv\Scripts\python.exe scripts\backup_rag_04_4.py --restore IDENTIFICADOR
```

También habrá que revertir en Git los cambios de `chunking.py`, `vector_store.py` y `retrieval.py` para que el código anterior sea compatible con el índice restaurado. No borrar manualmente `data/processed/rag/evaluacion_04_3_baseline.json`.

### Paso 04.4.8 — Registrar los cambios

```powershell
git status
git add src/energia_ai/rag/chunking.py src/energia_ai/rag/vector_store.py src/energia_ai/rag/retrieval.py scripts/backup_rag_04_4.py scripts/evaluate_rag_04_4.py scripts/compare_rag_04_4.py scripts/spotcheck_rag_04_4.py tests/test_rag_quality.py docs/ETAPA_04_4.md
git commit -m "refactor: optimizar chunking y evidencia del RAG"
```

## 4. Criterios para cerrar 04.4

- Se conservaron los documentos originales y las fuentes de las citas.
- Se respaldó el índice anterior y se puede reconstruir o restaurar.
- Las 155 pruebas pasan sin omisiones en Windows.
- Se completó la revisión manual de la nueva evaluación.
- Hit útil@3 no cae por debajo de 7/8 y aumenta la integridad de los fragmentos.
- Preguntas fuera de dominio reconocidas como insuficientes al menos en los casos de evaluación; revisar pruebas adicionales para detectar falsos positivos/negativos.
- Existe evidencia de comparación objetiva, incluidos posibles retrocesos.

**Si las métricas empeoran, se debe revertir la mejora o ajustar una variable a la vez antes de conectar el LLM.**
