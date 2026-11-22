# Etapa 04.1 - Chunking, embeddings locales e índice ChromaDB

## Objetivo

Crear una base vectorial real a partir de los tres documentos oficiales ya
preparados en la etapa 02.3. No se usa todavía el LLM conversacional ni se
registra `buscar_consejos` como tool de LangChain: eso se hará en 04.2.

## Fuentes

Se utilizan EXCLUSIVAMENTE las rutas registradas en
`energia_ai.rag.corpus.SOURCES`:

- ARG-RES-2024: guía residencial nacional (PDF, con páginas).
- EPRE-INV-2022: recomendaciones de invierno del EPRE Mendoza (HTML).
- EPRE-VER-2025: recomendaciones de verano del EPRE Mendoza (HTML).

Se verifica que el reporte `corpus_report.json` y los metadatos incluidos en
cada Markdown coincidan en ID, URL, ruta y huella SHA-256 del original. El
contenido fue revisado manualmente por el equipo en la etapa 02.3.

## Pipeline (dos momentos diferentes)

**Investigación / indexación, fuera de la conversación**: leer Markdown
preparado -> dividir por página (PDF) -> chunks con superposición -> vectorizar
con EmbeddingGemma en Ollama -> almacenar embeddings + texto + metadatos en
ChromaDB -> guardar manifiesto local.

**Consulta de prueba**: pregunta -> embedding con el MISMO modelo -> ChromaDB
busca similitud -> devuelve fragmentos, página si corresponde y URL oficial.

Al recuperar no se abren CSV ni los documentos PDF/HTML. El índice se carga
desde disco y se mantiene disponible durante el proceso. Persistir ChromaDB es
una decisión de reproducibilidad: NO contradice mantener el catálogo de tarifas
en RAM y reutilizar los vectores para cada pregunta.

## Modelo

- Embeddings: `embeddinggemma:300m` (Ollama), modelo multilingüe local.
- No es un LLM de chat ni genera recomendaciones por sí mismo.
- Embeddings generados únicamente a partir de contenido real del corpus.
- No exige API Key de terceros; se necesita conexión al descargar el modelo.
- El modelo se descarga aceptando los términos de su distribuidor.

## Procedimiento en Windows (PowerShell, raíz energia-ai)

1. Añadir los 5 archivos nuevos del ZIP 04.1 a la estructura existente.
2. Comprobar los tres Markdown y `data/processed/rag/corpus_report.json`.
3. Instalar Ollama de https://ollama.com/download/windows (si falta), abrirlo y comprobar:

   ```powershell
   ollama --version
   ollama list
   ```

4. Descargar el modelo SOLO una vez:

   ```powershell
   ollama pull embeddinggemma:300m
   ```

5. Instalar dependencias del nuevo módulo:

   ```powershell
   .\.venv\Scripts\python.exe -m pip install -r requirements-rag-index.txt
   .\.venv\Scripts\python.exe -m pip install -e .
   ```

6. Ejecutar las pruebas unitarias nuevas, offline (sin Ollama ni Chroma reales):

   ```powershell
   .\.venv\Scripts\python.exe -m unittest discover -s tests -p test_rag_index.py -v
   ```

7. Crear el índice real sobre el corpus aprobado:

   ```powershell
   .\.venv\Scripts\python.exe scripts\build_rag_index.py
   ```

   Resultado: JSON con `status: INDEXADO`, `documents: 3`, `chunks > 3`,
   `embedding_model: embeddinggemma:300m`.
   Los datos se almacenan en `data/vectorstore/energiaai_rag/` y su manifiesto
   en `data/vectorstore/energiaai_rag_manifest.json`. Ambos se ignoran en Git.

8. Probar una búsqueda semántica real:

   ```powershell
   .\.venv\Scripts\python.exe scripts\query_rag.py "¿Cómo usar el aire acondicionado con menos electricidad?"
   .\.venv\Scripts\python.exe scripts\query_rag.py "¿Qué hábitos convienen en invierno?"
   ```

   Revisar que las recomendaciones realmente estén en los documentos citados.
   Una distancia numérica de Chroma NO es probabilidad ni prueba de verdad.

9. Repetir indexación sin cambios:

   ```powershell
   .\.venv\Scripts\python.exe scripts\build_rag_index.py
   ```

   Debe informar `REUTILIZADO`: evita repetir cálculos de embeddings.

10. Si cambian documentos/modelo/chunking, reconstruir deliberadamente:

    ```powershell
    .\.venv\Scripts\python.exe scripts\build_rag_index.py --rebuild
    ```

    Esta acción reemplaza SOLO la colección RAG de EnergiaAI en ChromaDB.
    Si hay otras aplicaciones usando la misma carpeta no se deben mezclar.

11. Ejecutar suite total e informar pruebas omitidas, si las hubiera:

    ```powershell
    .\.venv\Scripts\python.exe -m unittest discover -s tests -v
    ```

12. Crear commit sin archivos generados:

    ```powershell
    git status
    git add requirements-rag-index.txt docs/ETAPA_04_1.md scripts/build_rag_index.py scripts/query_rag.py src/energia_ai/rag/chunking.py src/energia_ai/rag/vector_store.py tests/test_rag_index.py
    git commit -m "feat: indexar corpus energetico con embeddings y ChromaDB"
    ```

## Riesgos y límites

- Si Ollama no responde, comprobar que la aplicación está abierta y el modelo
  descargado (`ollama list`). No buscar embeddings con un modelo distinto sin
  reconstruir el índice.
- Los fragmentos de PDF se segmentan por página; los HTML se citan con URL.
- Los tamaños iniciales son 900 caracteres y 130 de superposición, por fuente.
- Las pruebas automáticas garantizan estructura y trazabilidad, no que la
  recuperación sea semánticamente óptima. Revisar consultas manuales.
- No se procesan cuadros de tarifas ni se calculan precios con el RAG.
- No se ejecutan instrucciones que puedan aparecer dentro de los documentos.

## Criterio de aceptación

- 3 documentos aprobados, metadatos completos y Chroma con >3 chunks.
- Búsqueda de ejemplo devuelve texto oficial con URL y página en PDFs.
- Indexación repetida reutiliza vectores, sin regenerarlos.
- Pruebas nuevas y regresión completas en Windows.
- Git commit sin `data/raw`, `data/processed`, `data/vectorstore`.
