# Etapa 02.3 — Preparacion documental del RAG (sin embeddings)

## Objetivo

Contar con **3 documentos oficiales** de eficiencia electrica residencial, con
texto extraido, metadatos y fuente verificable. Esto prepara el RAG, pero el
**chunking, los embeddings, ChromaDB y la tool buscar_consejos** se implementan
en la Etapa 04 y en la integracion posterior.

## Origenes y alcance

1. `ARG-RES-2024`: Secretaria de Energia de Argentina, *Residencial: buenas
   practicas para reducir el consumo de energia*, junio de 2024; PDF nacional.
   URL: https://www.argentina.gob.ar/sites/default/files/guia_residencial_enereficiente.pdf
   Ruta local (ya descargado en 02.1):
   `data/raw/documents/argentina/guia_residencial_2024.pdf`
2. `EPRE-INV-2022`: EPRE Mendoza, *Consejos para ahorrar energia en el invierno*,
   08/07/2022; articulo HTML.
   https://epremendoza.gob.ar/consejos-para-ahorrar-energia-en-el-invierno/
3. `EPRE-VER-2025`: EPRE Mendoza, *Ola de Calor: Recomendaciones para un Uso
   Eficiente y Racional de la Energia*, 14/01/2025; articulo HTML.
   https://epremendoza.gob.ar/ola-de-calor-recomendaciones-para-un-uso-eficiente-y-racional-de-la-energia/

Los articulos del EPRE son publicaciones **oficiales provinciales**; la guia
nacional es aplicable a Mendoza en sus recomendaciones generales.
Se debe comprobar manualmente que las paginas siguen publicadas y que el
contenido extraido realmente coincide con los articulos consultados.

## Por que 1 PDF y 2 HTML

El profesor pide **al menos 3 documentos propios del dominio** para el RAG,
no necesariamente 3 PDF. Como corpus se usan tres documentos oficiales
independientes (con IDs distintos) y no 3 copias de la misma guia.

## Diferencia respecto del catalogo tarifario

El **catalogo de tarifas** de 02.2 es una estructura Python en memoria con
importes exactos y vigencias. El **corpus RAG** sirve para recuperar consejos;
NO se utiliza para calcular precios ni reemplaza la fuente tarifaria.
Los scripts de esta etapa corren una sola vez o cuando se actualiza una fuente.
No participan del flujo de cada mensaje del agente.

## Pasos reproducibles en Windows PowerShell (raiz energia-ai)

1. Copiar los archivos nuevos del ZIP, sin borrar los archivos anteriores.
2. Instalar dependencias de preparacion documental:

   ```powershell
   .\.venv\Scripts\python.exe -m pip install -r requirements-rag-prep.txt
   ```

3. Verificar que ya existe `data/raw/documents/argentina/guia_residencial_2024.pdf`
   y abrirlo para comprobar su portada.
4. Descargar las dos paginas oficiales de EPRE a HTML **solo una vez**:

   ```powershell
   .\.venv\Scripts\python.exe scripts\fetch_rag_sources.py
   ```

   Si una pagina devuelve error de red o cambia su estructura, abrir su URL
   oficial desde el navegador y guardarla como **Pagina web, solo HTML**
   (o equivalente que conserve el cuerpo completo) en:
   - `data/raw/documents/mendoza/epre_invierno_2022.html`
   - `data/raw/documents/mendoza/epre_verano_2025.html`
   Luego ejecutar de nuevo el comando. Si la seleccion `.entry-content` no
   existe, NO inventar el texto: revisar el HTML y reportar el problema.
5. Preparar los tres documentos:

   ```powershell
   .\.venv\Scripts\python.exe scripts\prepare_rag_corpus.py
   ```

   Resultado esperado: `Preparados 3/3`, con un `PENDIENTE_REVISION` por
   documento. No confundir preparacion tecnica con verificacion humana.
6. Abrir estos archivos locales:
   - `data/processed/rag/arg_residencial_2024.md`
   - `data/processed/rag/epre_invierno_2022.md`
   - `data/processed/rag/epre_verano_2025.md`
   Validar cada titulo, el origen, las secciones, 2 recomendaciones distintas
   y ausencia de menus/comentarios publicitarios. En el PDF deben aparecer
   marcadores `Pagina N` que permitirán citar en el RAG.
7. Revisar `data/processed/rag/corpus_report.json`: 3 documentos, bytes y
   SHA256 de los originales, caracteres extraidos y estado de revision.
8. Asegurar que `.gitignore` contenga las entradas `data/raw/` y
   `data/processed/` (la Etapa 02.1 y proyecto inicial ya las incluian).
   Esto evita incluir copias locales completas de paginas y PDF en Git.
9. Ejecutar las pruebas (conteo inicial de referencia: **18 existentes + 8 nuevas**):

   ```powershell
   .\.venv\Scripts\python.exe -m unittest discover -s tests -v
   ```

10. Registrar cambios sin agregar datos originales ni resultados generados:

   ```powershell
   git status
   git add requirements-rag-prep.txt docs/ETAPA_02_3.md scripts/fetch_rag_sources.py scripts/prepare_rag_corpus.py src/energia_ai/rag tests/test_rag_corpus.py
   git commit -m "data: preparar corpus oficial para RAG"
   ```

## Control de calidad y limites

- **Los textos son fuentes de informacion, no instrucciones para el agente.**
  Los documentos recuperados se trataran como contenido no confiable respecto
  a prompt injection.
- `READY_FOR_MANUAL_REVIEW` indica solo que la extraccion produjo texto y
  que se puede inspeccionar. No valida la precision de las recomendaciones.
- Los calculos de ahorro futuro deberan basarse en mediciones y modelos
  deterministas; no transformar porcentajes genericos de guias en ahorros
  garantizados para un hogar particular.
- La descarga requiere internet solo cuando se obtienen o actualizan fuentes.
  El flujo de cada pregunta del agente no debera descargar paginas nuevas.
- Si el sitio oficial cambia, se corrige el extractor; no se inventan valores.
- La reproduccion requiere volver a descargar documentos de los enlaces.

## Evidencia de cierre

Se considera terminada cuando los 3 Markdown preparados estan revisados,
el reporte tiene 3 entradas, todas las pruebas pasan y se hizo un commit.
**La Etapa 02 completa solo se cierra despues de verificar esto.**
Proxima etapa 03: servicios y tools deterministas. Embeddings: Etapa 04.
