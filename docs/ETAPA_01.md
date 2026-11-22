# Etapa 01 - Preparación del entorno de desarrollo

**Estado:** instrucciones y archivos base preparados; ejecución en Windows aún pendiente de verificar.

## Objetivo

Comprobar que el equipo puede ejecutar Python 3.12 en un entorno virtual, editar código, ejecutar pruebas y registrar cambios con Git. No implementar IA ni lógica energética en esta etapa.

## Decisiones heredadas de la Etapa 00

- Provincia de Mendoza, solo usuarios residenciales abastecidos por EDEMSA.
- Caso de uso UC-01: análisis energético integral y PDF final.
- Cinco tools previstas: calcular_consumo, consultar_tarifa, buscar_consejos, simular_ahorro y generar_informe.
- Tarifas oficiales del EPRE extraídas, verificadas y consultadas desde datos estructurados. La actualización web será un proceso separado.
- LangChain create_agent + memoria de corto plazo con InMemorySaver en una etapa posterior; no hay persistencia entre reinicios en el MVP académico.
- RAG para conocimiento, sin skill de LaTeX.

## Qué necesitamos instalar

1. Python 3.12 desde https://www.python.org/downloads/windows/
2. VS Code desde https://code.visualstudio.com/download
3. Git desde https://git-scm.com/install/win
4. Extensiones VS Code: Python, Pylance y, opcionalmente, Ruff.

Ollama se instalará y probará en la etapa de integración del modelo, no ahora.

## Comandos de preparación (PowerShell)

```powershell
py -3.12 --version
git --version
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe --version
```

En VS Code: `Ctrl+Shift+P` → `Python: Select Interpreter` → `.venv\Scripts\python.exe`.

## Verificaciones

```powershell
.\.venv\Scripts\python.exe scripts\check_environment.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## Inicialización de Git

```powershell
git init
git status
git add .
git commit -m "chore: preparar entorno inicial de EnergiaAI"
```

El archivo `.gitignore` impide incluir `.venv`, claves privadas `.env` y productos generados.

## Criterios de aceptación

- [ ] Python 3.12 accesible en PowerShell.
- [ ] VS Code abierto en carpeta raíz y con intérprete del `.venv` seleccionado.
- [ ] `check_environment.py` informa `Estado: CORRECTO`.
- [ ] Se ejecutan 4 pruebas con resultado `OK`.
- [ ] `git status` funciona y hay un primer commit local.
- [ ] No se versionan carpetas `.venv` ni archivos `.env` privados.

## Evidencias para conservar

Copiar al informe de la etapa las salidas de `py -3.12 --version`, el diagnóstico, el resumen de pruebas y `git log -1 --oneline`. No registrar contraseñas ni tokens.

## Relación con la rúbrica

Esta etapa prepara reproducibilidad, README, estructura del repositorio y entorno verificable. Las tools, RAG, streaming, memoria y UI se implementan en etapas posteriores y se evalúan en integración.
