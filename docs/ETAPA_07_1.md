# Etapa 07.1 — Preparación del repositorio reproducible

**Alcance:** entrega académica de EnergiaAI, sin cambios en Qwen, LangChain, tools, RAG, SQLite ni Streamlit.  
**Base informada:** Etapa 06.4 completada, 289 pruebas aprobadas, acta y commit registrados por el equipo.  
**Fecha de referencia:** 23/11/2026. El equipo informó fecha de entrega 27/11/2026; la consigna impresa exhibe un cronograma anterior, por lo que conservar el plazo comunicado por la cátedra y confirmarlo externamente.

## Objetivo

Una persona que no participó del desarrollo debe poder clonar el repositorio, instalar Python 3.12 y Ollama, descargar el corpus, generar embeddings y ejecutar Streamlit siguiendo **solo el README**, sin archivos secretos ni información de tu computadora.

## Cambios incorporados

- `README.md`: reemplaza la documentación desactualizada de la Etapa 01. Explica el flujo completo desde una instalación limpia, enlaces oficiales, versiones del modelo, ejecución y demo.
- `requirements.txt`: incluye los archivos de dependencias existentes (`-r ...`) sin alterar sus rangos originales. Evita la falsa impresión de que el proyecto no tiene dependencias.
- `.env.example`: referencia las variables opcionales que **sí lee** el código. El proyecto no carga `.env` automáticamente.
- `.gitignore`: excluye `data/raw`, `data/processed`, `data/state`, `data/vectorstore`, `.egg-info`, secretos y cachés. Si algún archivo fue versionado antes, el .gitignore no lo quita del historial.
- `scripts/preflight_entrega_07.py`: comprobación reproducible de archivos, dependencias declaradas, exclusiones y (opcionalmente) artefactos locales de ejecución.
- `tests/test_release_preflight_07.py`: pruebas del verificador, sin Ollama ni LLM.
- `docs/CHECKLIST_ENTREGA_07.md`, `docs/GUIA_DEMO_07.md`: listas de control y demo para la cátedra.

## Paso 1: copiar la actualización

Descomprimir el ZIP y combinar carpetas con el proyecto `energia-ai` actual. **Se reemplazan** README.md, requirements.txt, .env.example y .gitignore. Respaldarlos primero si el equipo los editó. No copiar `.venv`, bases, indexados ni archivos personales de otro entorno.

## Paso 2: probar el preflight sin LLM

```powershell
.\.venv\Scripts\python.exe scripts\preflight_entrega_07.py --modo repo
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_release_preflight_07.py -v
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Las pruebas anteriores son 289 según el equipo. El nuevo total es 289 más las pruebas efectivamente detectadas por `test_release_preflight_07.py`. **No marcar pruebas nuevas como aprobadas antes de ejecutarlas en Windows.**

## Paso 3: comprobar artefactos locales

```powershell
ollama list
.\.venv\Scripts\python.exe scripts\preflight_entrega_07.py --modo ejecucion
```

En modo ejecución se verifica la presencia de los Markdown y del manifiesto de ChromaDB, pero **no valida** las llamadas reales al modelo. Si falta el corpus/index, seguir sección 3 del README para reconstruirlos.

## Paso 4: inspeccionar secretos y archivos grandes

```powershell
git status
git ls-files data/raw data/processed data/vectorstore data/state
git check-ignore -v data/state/inventario.sqlite3
```

La segunda salida debería estar vacía. Revisar también `git ls-files` antes de publicar y no subir tokens, `.env`, inventarios, historial, PDFs de usuarios ni archivos generados.

## Paso 5: registrar el commit y verificar GitHub

```powershell
git add README.md requirements.txt .env.example .gitignore docs/ETAPA_07_1.md docs/CHECKLIST_ENTREGA_07.md docs/GUIA_DEMO_07.md scripts/preflight_entrega_07.py tests/test_release_preflight_07.py
git commit -m "docs: preparar entrega reproducible de EnergiaAI"
git remote -v
git status
```

Publicar en el repositorio GitHub **real** del equipo con la rama acordada. No se inventan nombres de rama, URLs ni estados de publicación. Confirmar que el enlace permite acceder al código y que hay commit anterior a la exposición.

## Paso 6: prueba de instalación limpia (criterio crítico)

En una carpeta nueva que no contenga el entorno anterior, clonar el repositorio y ejecutar el README de principio a fin. Registrar: versión Python, instalación de dependencias, Ollama y modelos, descarga/corpus/index, inicio de Streamlit, tool calling, citas RAG, SQLite, PDF y comandos de pruebas.

Si falla una instalación limpia, **la Etapa 07.1 sigue abierta** aunque el sistema funcione en la computadora original. Corregir el README o las dependencias y repetir.

## Siguiente subetapa

07.2: presentación con diagrama de agente, evidencia de tools y razonamiento si el proveedor lo expone; demostrar caso completo y memoria de otro turno. Preparar contingencia si la inferencia local demora ~4 min. 07.3: defensa individual de decisiones y limitaciones. 07.4: auditoría final y entrega.
