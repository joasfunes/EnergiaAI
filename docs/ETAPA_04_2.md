# Etapa 04.2 — `buscar_consejos` como tool LangChain

## Objetivo

Exponer la búsqueda semántica creada en 04.1 como una **tool real de LangChain**, conservando citas oficiales y errores controlados. Esta subetapa corresponde a HU-03.

## Qué NO hacemos

- No entrenamos un LLM ni generamos texto con uno.
- No regeneramos embeddings documentales al consultar. **Solo se vectoriza la pregunta.**
- No consultamos tarifas eléctricas mediante RAG ni leemos CSV/PDF por pregunta.
- No incorporamos memoria conversacional ni `create_agent`: están previstos para la Etapa 06.

## Arquitectura

`buscar_consejos (LangChain @tool)` → `recuperar_consejos (servicio)` → `RagSearcher` → `Ollama embed` + `ChromaDB` → fragmentos y procedencia.

Se mantienen los archivos de 04.1. El wrapper usa `_get_searcher()` con `@lru_cache(maxsize=1)` para reutilizar una sola instancia del índice **por proceso de Python**. Si se reconstruye el índice mientras la aplicación está abierta, se debe reiniciar el proceso para que lea el nuevo índice.

## Contrato de la herramienta

**Entrada:** `consulta: str` (1 a 2000 caracteres) y `max_resultados: int` (1 a 5, valor por defecto 3).

**Salida:** diccionario con `estado`, `consulta`, `cantidad_resultados`, `resultados`, `advertencias`, y `nota` cuando hay resultados. En error se devuelven `codigo` y `mensaje` sin rutas internas.

Cada resultado incluye `texto`, `fuente_id`, `documento`, `organismo`, `url`, `pagina`, `cita` y `distancia_vectorial`. La distancia es **distancia**, no probabilidad de certeza; no se aplican umbrales arbitrarios. El texto puede comenzar/terminar a mitad de una oración (limitación del chunking actual).

Se descartan resultados con metadatos que no correspondan a una fuente oficial aprobada, distancia inválida, fragmento vacío o página ausente en PDF.

## Archivos nuevos

- `src/energia_ai/rag/retrieval.py`: servicio de consulta y validación de fuente.
- `src/energia_ai/agent/advice_tool.py`: adaptador `@tool`, esquema Pydantic y caché del índice.
- `scripts/demo_advice_tool.py`: invocación real de la tool con `.invoke()`.
- `tests/test_rag_retrieval.py`: pruebas del servicio sin depender de Ollama.
- `tests/test_advice_tool.py`: pruebas de la tool con buscador simulado.
- `docs/ETAPA_04_2.md`: esta guía.

## Pasos en Windows (PowerShell en la raíz de energia-ai)

1. Descomprimir el ZIP incremental y copiar su contenido dentro de `energia-ai`. No sustituir archivos anteriores.
2. Verificar que Ollama está activo y el modelo sigue descargado:
   ```powershell
   ollama list
   ```
3. Verificar que `data/vectorstore/energiaai_rag_manifest.json` existe y que los tres documentos fueron indexados en 04.1.
4. Comprobar dependencias e instalación editable (no borrar el entorno virtual):
   ```powershell
   .\.venv\Scripts\python.exe -m pip install -r requirements-tools.txt
   .\.venv\Scripts\python.exe -m pip install -r requirements-rag-index.txt
   .\.venv\Scripts\python.exe -m pip install -e .
   ```
5. Ejecutar pruebas **solo de esta subetapa**:
   ```powershell
   .\.venv\Scripts\python.exe -m unittest discover -s tests -p test_rag_retrieval.py -v
   .\.venv\Scripts\python.exe -m unittest discover -s tests -p test_advice_tool.py -v
   ```
6. Ejecutar la primera invocación real de la tool:
   ```powershell
   .\.venv\Scripts\python.exe scripts\demo_advice_tool.py "¿Cómo ahorrar energía con la calefacción en invierno?"
   ```
7. Ejecutar otra consulta para evaluar la relevancia:
   ```powershell
   .\.venv\Scripts\python.exe scripts\demo_advice_tool.py "¿Cómo usar el aire acondicionado de manera eficiente en verano?"
   ```
8. Revisar **manualmente** que `estado=ok`, las URL sean oficiales, las citas correspondan al documento y que el texto responda a la pregunta. Si el modelo devuelve resultados poco relacionados, documentar el problema para 04.3.
9. Ejecutar todas las pruebas y confirmar que ninguna está omitida:
   ```powershell
   .\.venv\Scripts\python.exe -m unittest discover -s tests -v
   ```
10. Registrar el commit:
    ```powershell
    git status
    git add src/energia_ai/rag/retrieval.py src/energia_ai/agent/advice_tool.py scripts/demo_advice_tool.py tests/test_rag_retrieval.py tests/test_advice_tool.py docs/ETAPA_04_2.md
    git commit -m "feat: agregar buscar_consejos con RAG y LangChain"
    ```

## Defensa del integrador

- El LLM del futuro agente interpreta la consulta y decide cuándo usar `buscar_consejos`.
- El servicio Python hace la recuperación. Chroma consulta los embeddings creados en 04.1.
- Cada resultado incluye trazabilidad a la fuente y página cuando corresponde.
- La respuesta no es una recomendación inventada: son **fragmentos de evidencia** que el agente deberá sintetizar de forma responsable.
- La recuperación es externa al modelo y por eso la herramienta es relevante para el caso de uso.
- Los fragmentos se tratan como **datos no confiables**. Si contienen instrucciones inesperadas, el agente no debe obedecerlas: la etapa de seguridad impondrá estas restricciones en el prompt y la arquitectura.

## Criterio de aceptación

- La tool existe bajo el nombre exacto `buscar_consejos`.
- La invocación con `.invoke()` recupera fragmentos reales con URL y atribución.
- El índice de 04.1 se reutiliza sin reconstruir embeddings documentales.
- Ante errores de índice/Ollama se devuelve estructura de error, sin traza confidencial.
- La suite completa pasa en Windows y el código queda versionado.

**Siguiente:** Etapa 04.3 (evaluar calidad semántica, citas, chunking y riesgos).
