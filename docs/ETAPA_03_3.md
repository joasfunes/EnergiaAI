# EnergiaAI — Subetapa 03.3: simular_ahorro

**Estado:** implementada en código; requiere validación en la computadora del equipo.

**Historia de usuario:** HU-04 — Como usuario residencial de EDEMSA quiero comparar hábitos de utilización de mis electrodomésticos para estimar cuánto consumo y cuánto podría ahorrar.

## Alcance del MVP

Se comparan dos escenarios con **los mismos electrodomésticos** y la misma duración. Únicamente pueden cambiar horas efectivas diarias y días de uso. No se permite introducir equipos nuevos ni simular reemplazos de potencia en esta subetapa. No se usa un LLM para hacer operaciones aritméticas.

La energía se calcula reutilizando `services.consumption.calcular_consumo_equipos`. El ahorro se define como consumo actual de los equipos menos consumo propuesto: un resultado negativo indica un **aumento de consumo**, no un ahorro.

## Arquitectura

- `services/savings.py`: motor Python determinístico, validación cruzada con consumo y catálogo.
- `agent/savings_tool.py`: herramienta LangChain `simular_ahorro`, esquema Pydantic y manejo de errores.
- `scripts/demo_savings_service.py`: demostración sin LangChain.
- `scripts/demo_savings_tool.py`: invocación de la tool sin modelo.
- `tests/test_savings.py`: pruebas unitarias y de reglas de negocio.
- `tests/test_savings_tool.py`: integración con `langchain-core`.

## Contrato de la tool

Entradas:

| Campo | Tipo | Uso |
|---|---|---|
| `periodo_dias` | int | Período idéntico para escenarios actual y propuesto |
| `equipos_actuales` | lista de equipos | Consumo de referencia |
| `equipos_propuestos` | lista de equipos | Cambios de hábitos, mismos IDs/potencias/cantidad |
| `consumo_hogar_bimestral_kwh` | int opcional | Valor total facturado del hogar para una simulación monetaria |
| `tarifa_consultada` | dict opcional | Resultado **íntegro y sin modificaciones** de la tool `consultar_tarifa` |

Salida:

`estado`, consumos de ambos escenarios, `ahorro_kwh`, `ahorro_porcentual_equipos`, consumo del hogar proyectado, categorías inicial y proyectada, `estimacion_monetaria_disponible`, `ahorro_componente_variable_estimado_ars`, `motivo_sin_estimacion_monetaria`, fuente y advertencias.

## Reglas para expresar un ahorro en ARS

Se requiere **simultáneamente**:

1. Escenarios correspondientes a un período bimestral de referencia de 45–75 días.
2. Consumo total facturado del mismo bimestre, entero y no menor al estimado para los equipos incluidos.
3. Respuesta completa de `consultar_tarifa` para EDEMSA, régimen `SIN_SEF`, misma referencia bimestral y fuente comprobada contra el catálogo.
4. `estado_revision` del catálogo igual a `CONTRASTADO_CON_PDF_LOCAL`.
5. La categoría R1/R2/R3 debe permanecer igual después del cambio.
6. El consumo proyectado no debe estar en una zona de menos de 1 kWh de un umbral 300/600 con redondeo potencialmente ambiguo.

Cuando falta alguna condición, **no se genera una estimación de pesos**: el servicio conserva el resultado energético e indica el motivo.

**El importe entregado es únicamente la diferencia estimada del cargo variable SIN_SEF**, no el ahorro de la factura completa. No contempla SEF, límites de cupo, cargos fijos, impuestos, tasas, recargos, mínimos de facturación ni prorrateos. Se utiliza como proyección orientativa, no para reclamar importes a la distribuidora. Los 45–75 días son una restricción de demostración del MVP, no una regla jurídica del EPRE.

Si el usuario pide agregar un nuevo electrodoméstico, se debe actualizar el perfil en la aplicación y volver a calcular un escenario de referencia; no es una instrucción de sustitución de equipos en esta herramienta.

## Pasos de instalación y validación (Windows / VS Code)

1. Descargar el paquete incremental ZIP y **copiar sus archivos dentro de `energia-ai/`**, conservando el código anterior.
2. Abrir PowerShell en la raíz del repositorio.
3. Si aún no se hizo: ` .\.venv\Scripts\python.exe -m pip install -e . `.
4. Dependencias ya instaladas en 03.1: ` .\.venv\Scripts\python.exe -m pip install -r requirements-tools.txt `.
5. Confirmar que `estado_revision="CONTRASTADO_CON_PDF_LOCAL"` solo si el equipo verificó antes el catálogo contra el PDF oficial (03.2).
6. Ejecutar: ` .\.venv\Scripts\python.exe scripts\demo_savings_service.py `.
7. Ejecutar: ` .\.venv\Scripts\python.exe scripts\demo_savings_tool.py `.
8. Ejecutar: ` .\.venv\Scripts\python.exe -m unittest discover -s tests -v `.
9. Esperar **85 pruebas** y **ninguna omisión** en la instalación local con `langchain-core`. Si no está instalado, parte del conjunto será omitido.
10. Revisar `git status`; agregar los siete archivos nuevos y registrar el commit `feat: simular ahorro energetico con tarifas verificadas`.

### Ejemplo completo

- Período de referencia: 60 días.
- Aire de 1500 W; escenario actual: 5 horas/día durante 10 días = 75 kWh.
- Escenario alternativo: 3 horas/día durante 10 días = 45 kWh.
- Ahorro: **30 kWh** (40 % respecto del equipo analizado).
- Consumo facturado de referencia del hogar: 350 kWh bimestrales.
- Proyección de consumo del hogar: 320 kWh bimestrales, aún en R2.
- Tarifa de referencia: EDEMSA SIN_SEF del 15/11/2026, cargo variable R2 según catálogo.
- Diferencia de componente variable: **ARS 8.682,95** (proyección, **no factura total**), siempre que el catálogo figure contrastado.

### Casos que se deben mostrar en la demo

- Si el usuario reduce el aire lo suficiente como para pasar de R2 a R1, mostrar solo ahorro en kWh y explicar por qué no hay ARS.
- Si el usuario tiene CON_SEF, mostrar solo kWh mientras no exista modelado del cupo.
- Si el usuario no tiene factura o solo conoce sus equipos, comparar energía y solicitar datos para dinero.
- Si aumenta el uso, el ahorro debe salir negativo.

## Defensa individual

**¿Por qué dos escenarios?** Evita que el modelo invente la magnitud del ahorro: Python compara dos consumos calculados bajo los mismos supuestos.

**¿Por qué consultar_tarifa es otra tool?** Su responsabilidad es obtener y citar los cargos oficiales; `simular_ahorro` toma ese resultado y cuantifica una diferencia. No descarga ni parsea PDF en ejecución.

**¿Por qué no estimar siempre ARS?** Un cambio de categoría o cupo SEF hace incorrecto multiplicar por un único precio. Con una implementación parcial preferimos devolver un resultado limitado pero justificado.

**¿Por qué no necesitamos una skill LaTeX?** Las fórmulas del motor son sencillas, Python las resuelve y no requieren compilador LaTeX.

**Qué sigue:** Etapa 03.4 — compatibilidad e integración de las tres tools; después Etapa 04 — chunking, embeddings y ChromaDB.
