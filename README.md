# EnergiaAI — Consultor de energía residencial en Mendoza

**Proyecto integrador de Modelos de Lenguaje (2026) · Prototipo académico de ejecución local.**

EnergiaAI es un agente construido con **LangChain `create_agent`** y **Qwen3.5 9B mediante Ollama**. Analiza el consumo de electrodomésticos residenciales, consulta un catálogo tarifario local de **EDEMSA (Mendoza)**, compara escenarios, recupera recomendaciones oficiales mediante **RAG** y permite descargar un **informe PDF con gráficos y fuentes**. Incluye conversación y perfil del hogar persistidos en SQLite e interfaz Streamlit con eventos de ejecución.

> **Límites:** no calcula una factura oficial completa ni garantiza ahorros económicos. En el MVP solo se admite EDEMSA, consumos residenciales y las fechas/regímenes implementados en el catálogo (EPRE 221/2026). El simulador no monetiza si hay SEF, cambio de categoría o datos insuficientes. El sistema no incluye autenticación y **no debe exponerse públicamente**.

## 1. Requisitos previos

- Windows 11 (probado por el equipo), Python **3.12**, Git y terminal PowerShell.
- Ollama instalado y en ejecución: https://ollama.com/download/windows
- Modelos descargados: `qwen3.5:9b` (chat y tools) y `embeddinggemma:300m` (RAG).
- Conexión a internet **solo para instalación de dependencias, modelos y adquisición inicial de documentos**. Las consultas posteriores usan archivos e índices locales.
- Hardware: el modelo 9B puede tardar varios minutos en CPU; la latencia real depende del equipo.

## 2. Instalación reproducible desde el repositorio

Clonar el repositorio oficial del equipo (URL que el equipo debe publicar y comprobar):

```powershell
git clone <URL-REAL-DEL-REPOSITORIO>
cd energia-ai
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -e .
```

No reemplazar `<URL-REAL-DEL-REPOSITORIO>` por una dirección inventada. La carpeta clonada debe ser aquella que contiene `app.py` y `pyproject.toml` (si el repositorio tiene una carpeta envolvente, ingresar allí). `requirements.txt` ahora referencia los archivos de dependencias de todas las etapas.

Configurar Ollama:

```powershell
ollama --version
ollama pull qwen3.5:9b
ollama pull embeddinggemma:300m
ollama list
.\.venv\Scripts\python.exe scripts\check_ollama_llm.py
```

En general no hace falta crear `.env`. El proyecto utiliza `qwen3.5:9b` y `http://127.0.0.1:11434` por defecto; consultar `.env.example` para variables de entorno **opcionales**. El código no carga el archivo `.env` automáticamente. Ejemplo de configuración manual en PowerShell:

```powershell
$env:ENERGIAAI_LLM_MODEL="qwen3.5:9b"
$env:ENERGIAAI_OLLAMA_URL="http://127.0.0.1:11434"
```

## 3. Preparación del corpus RAG desde fuentes oficiales

Las fuentes originales no se incluyen en Git por ser descargas externas; se conservan localmente en `data/raw/`. El índice ChromaDB también se genera localmente y no se versiona. **Estos pasos son obligatorios después de una instalación limpia.**

1. Descargar el PDF nacional desde [la Secretaría de Energía](https://www.argentina.gob.ar/sites/default/files/guia_residencial_enereficiente.pdf) y guardarlo exactamente como `data/raw/documents/argentina/guia_residencial_2024.pdf`.
2. Descargar las dos páginas provinciales mediante el script (o guardar manualmente las páginas HTML en las rutas que informa `src/energia_ai/rag/corpus.py` si la descarga automática falla).
3. Preparar y revisar los tres documentos Markdown. Comprobar título, procedencia, texto extraído y marcadores de página.
4. Construir el índice de embeddings con el modelo local descargado.

```powershell
.\.venv\Scripts\python.exe scripts\fetch_rag_sources.py
.\.venv\Scripts\python.exe scripts\prepare_rag_corpus.py
.\.venv\Scripts\python.exe scripts\build_rag_index.py
.\.venv\Scripts\python.exe scripts\query_rag.py "¿Cómo ahorrar electricidad en invierno?"
```

Los documentos del corpus son: guía nacional residencial de 2024, consejos EPRE invierno 2022 y recomendaciones EPRE verano 2025. Se usa **chunking recursivo** por párrafos y oraciones, EmbeddingGemma y ChromaDB. Si cambian el corpus, el modelo de embeddings o la estrategia de chunking, deben respaldar y reconstruir el índice con `scripts/build_rag_index.py --rebuild`. No reconstruir por cada consulta.

**Tarifas:** `src/energia_ai/data/tariff_catalog.py` contiene un catálogo transcrito y revisado para la resolución EPRE 221/2026. Su fuente es [el PDF oficial del EPRE](https://epremendoza.gob.ar/2019/resoluciones-anexos/Res%20221-2026.pdf). Para auditoría documental, guardar el PDF en `data/raw/tariffs/mendoza/edemsa/resolucion_epre_221_2026.pdf`; esa ruta no es necesaria para consultas normales, que usan el catálogo ya cargado en memoria. Los valores no se actualizan automáticamente desde la web. Verificar vigencia antes de usar tarifas fuera del ejemplo académico.

## 4. Ejecutar EnergiaAI en el navegador

```powershell
.\.venv\Scripts\python.exe scripts\preflight_entrega_07.py --modo ejecucion
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501
```

Abrir http://127.0.0.1:8501, seleccionar o crear un hogar y una conversación. La aplicación permite ver respuestas Markdown, eventos de herramientas y descargar informes cuando `simular_ahorro` produjo datos válidos.

**No usar** `0.0.0.0`, túneles ni publicación de este prototipo: la separación local por `hogar_id` no equivale a autenticación ni autorización.

## 5. Prueba de aceptación y resultados esperados

Caso de uso para demostrar con **datos ficticios de prueba**:

> Mi hogar consume 350 kWh por bimestre con EDEMSA, SIN_SEF, al 15 de noviembre de 2026. Durante un período de referencia de 60 días, mi aire acondicionado de 1500 W se utiliza 5 horas efectivas por día durante 10 días. ¿Cuánto ahorro si lo uso 3 horas por día durante los mismos 10 días? Calculá consumo, consultá tarifa, simulá ahorro y buscá recomendaciones oficiales para el verano.

Verificar en la **traza real** que se llamaron `calcular_consumo`, `consultar_tarifa`, `simular_ahorro` y `buscar_consejos` (si el LLM omite alguna, el caso no está completamente aprobado). Valores de referencia: **75 → 45 kWh**, **30 kWh de diferencia**, hogar **350 → 320 kWh**, R2. La diferencia económica, cuando proceda, representa solo el **componente variable**, no la factura final. El PDF debe basarse en mensajes reales de las tools, no en cifras inventadas por el LLM.

Para probar memoria: registrar un equipo, cerrar Streamlit, reiniciarlo, seleccionar la misma conversación e incorporar otro equipo sin borrar el anterior. Se usa SQLite para checkpoints y para el inventario. El chat puede tardar varios minutos por la inferencia local de Qwen3.5 9B; los cálculos Python son rápidos.

## 6. Pruebas, diagnóstico y control de entrega

```powershell
.\.venv\Scripts\python.exe scripts\preflight_entrega_07.py --modo repo
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts\validar_etapa_06_4.py
```

El equipo confirmó **289 pruebas** hasta Etapa 06.4; la Etapa 07 incorpora pruebas del preflight. Las pruebas unitarias son offline y **no prueban por sí solas** Qwen, ChromaDB, Streamlit ni citas reales: realizar también el recorrido manual y registrar evidencia en `docs/ACTA_06_4.md`.

Antes de publicar:

```powershell
git status
git ls-files data/raw data/state data/vectorstore data/processed
# La salida anterior debería estar vacía; revisar cualquier excepción.
git remote -v
```

No subir `.env` con credenciales, conversaciones SQLite, inventarios, PDFs personales, modelos Ollama ni vectores. Si ya se versionaron, `.gitignore` **no los elimina del historial**; hay que resolverlo explícitamente antes de hacer público el repositorio.

## 7. Arquitectura y justificación

```text
Streamlit (interfaz local, streaming y chat Markdown)
    ↓
LangChain create_agent + Qwen3.5 9B (Ollama)
    ├── calcular_consumo → servicios Python determinísticos
    ├── consultar_tarifa → catálogo EPRE/EDEMSA cargado en memoria
    ├── simular_ahorro → comparación de escenarios / restricciones
    ├── buscar_consejos → EmbeddingGemma + índice ChromaDB
    ├── registrar_electrodomestico → inventario SQLite
    └── consultar_inventario → inventario SQLite
    ↓
Historial SQLite (SqliteSaver), trazas y generador PDF ReportLab
```

Las cuatro herramientas energéticas son las **esenciales del caso principal**. Las dos tools de inventario amplían la continuidad del hogar; no son necesarias para simular un ejemplo desde cero. No se entrena un LLM; se reutiliza un modelo preentrenado con RAG y herramientas.

## 8. Seguridad y limitaciones conocidas

- Uso **solo local, sin autenticación**; no es un servicio multiusuario seguro.
- Las tarifas corresponden a la vigencia incluida en el catálogo y pueden quedar desactualizadas. No se consulta al EPRE en vivo durante el diálogo.
- Consumos calculados con potencia supuesta y horas efectivas; no sustituyen mediciones reales.
- **SIN_SEF**, categoría estable y catálogo contrastado: solo estimación del componente variable. SEF, cambio de categoría y datos faltantes impiden monetizar.
- RAG evaluado con muestra pequeña de 10 preguntas. Persisten errores de extracción de PDFs con tablas/columnas; no usar porcentajes recuperados como garantías.
- Modelo Qwen3.5 9B lento en CPU: una medición local de referencia de la Etapa 06.1 registró unos **227,943 s** para un turno (dos llamadas al modelo). El streaming informa progreso; no acelera la inferencia.
- Los fragmentos recuperados son **datos**, nunca instrucciones de sistema; mantener la revisión humana de recomendaciones.
- El proveedor local no garantiza que exponga bloques de razonamiento. El requisito de visibilidad se cumple con **tools y argumentos/resultados**; no afirmar que se muestran cadenas internas de razonamiento si no están disponibles.

## 9. Material para entrega y defensa

- `docs/ETAPA_07_1.md`: paso a paso de publicación reproducible.
- `docs/CHECKLIST_ENTREGA_07.md`: verificación final del repositorio.
- `docs/ACTA_06_4.md`: acta con pruebas manuales (completar con evidencia real del equipo).
- Documentos `docs/ETAPA_*`: decisiones de ingeniería y subetapas.
- `docs/GUIA_DEMO_07.md`: caso principal, memoria y plan de contingencia.

Repositorio, video/capturas, presentación y URL de GitHub: **los aporta y verifica el equipo**. No se inventa una dirección ni se afirma que un entorno limpio ya quedó instalado.
