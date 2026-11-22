# EnergiaAI

Agente de análisis y optimización del consumo eléctrico **residencial**, con alcance inicial en suministros **EDEMSA de la provincia de Mendoza (Argentina)**.

**Estado:** Etapa 01 - preparación de entorno. El agente y sus tools **todavía no están implementados**.

## Alcance del MVP

- Dominio: consumo y ahorro eléctrico residencial.
- Distribuidora soportada: EDEMSA.
- UC-01: analizar un hogar, calcular consumo, consultar tarifas verificadas, recuperar consejos RAG, simular escenarios y generar informe PDF.
- La tarifa se consultará desde un conjunto de datos local validado, construido a partir de cuadros oficiales del EPRE; no se descargará en cada consulta del agente.
- Memoria inicial: `InMemorySaver` con `thread_id` cuando implementemos el agente. No persiste después de reiniciar.

## Requisitos de esta etapa

- Windows 10/11 (equipo de desarrollo previsto).
- Python **3.12**.
- Git.
- Visual Studio Code con extensiones Python y Pylance.

## Instalación y primer arranque (PowerShell)

Abrir una terminal en la carpeta `energia-ai`:

```powershell
py -3.12 --version
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m pip --version
```

No hace falta activar el entorno: los comandos invocan su intérprete explícitamente.

## Validaciones

```powershell
.\.venv\Scripts\python.exe scripts\check_environment.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Se espera que el diagnóstico informe `Estado: CORRECTO` y que las **4 pruebas** resulten `OK`.

## Control de versiones

```powershell
git init
git status
git add .
git commit -m "chore: preparar entorno inicial de EnergiaAI"
```

Si Git pide identidad, configurarla solo para este repositorio:

```powershell
git config user.name "Nombre Apellido"
git config user.email "correo@ejemplo.com"
```

Reemplazar los ejemplos con los datos que el equipo decida utilizar.

## Estructura

```text
energia-ai/
├── .env.example
├── .gitignore
├── README.md
├── requirements.txt
├── docs/ETAPA_01.md
├── scripts/
│   ├── __init__.py
│   └── check_environment.py
├── src/energia_ai/__init__.py
└── tests/test_check_environment.py
```

## Documentación

Ver [Etapa 01](docs/ETAPA_01.md) para pasos, criterios y relación con la propuesta corregida.

## Próximos pasos

Etapa 02: fuentes oficiales EPRE/EDEMSA, tablas de tarifas verificadas y corpus documental RAG. No se incluyen aquí valores tarifarios ni documentos externos sin verificar.
