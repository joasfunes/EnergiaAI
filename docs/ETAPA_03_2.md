# Etapa 03.2 — Consulta del catálogo EDEMSA en memoria

**Estado:** lista para probar en Windows. HU-02. **Esta subetapa no calcula facturas.**

## 1. Qué ya existía y qué incorporamos

- Etapa 02.2: `src/energia_ai/data/tariff_catalog.py` contiene la Resolución EPRE 221/2026 (EDEMSA T1 residencial). **No sustituirlo** con este paquete.
- Nuevo `src/energia_ai/services/tariffs.py`: servicio Python puro, sin LLM, que selecciona banda y cargos *del catálogo cargado al importar*.
- Nuevo `src/energia_ai/agent/tariff_tool.py`: adaptador `@tool` con esquema Pydantic, errores controlados y nombre `consultar_tarifa`.
- Nuevos scripts de demostración, pruebas automatizadas y este documento.

## 2. Contrato y límites funcionales

**Entrada obligatoria** (no se infieren valores que el usuario no brindó):

```json
{
  "distribuidora": "EDEMSA",
  "fecha": "2026-11-15",
  "consumo_kwh_bimestral": 350,
  "regimen": "SIN_SEF"
}
```

El consumo representa el consumo **bimestral** de referencia, en kWh enteros. No se debe enviar como bimestral un cálculo de 20 o 30 días sin una conversión con supuestos explícitos. El `regimen` es `SIN_SEF` o `CON_SEF`; si el usuario no conoce su condición hay que pedirla. La fecha está en formato ISO `AAAA-MM-DD` y se rechazan fechas fuera de la cobertura del catálogo.

**Salida:** `estado`, categoría `R1/R2/R3`, intervalo de consumo, régimen, cargos principales (fijo ARS/bimestre y variable ARS/kWh), cargos de excedente si están representados, resolución/URL, cobertura y estado de contraste; incluye advertencias. Todos los importes monetarios se serializan como cadenas decimales. No incluye el total de factura ni el total de ahorro.

**SEF:** para `CON_SEF` se muestran valores base y, cuando existe columna específica, excedente. **NO se calcula el subsidio, ni se decide el cupo que corresponde, ni se usa un solo cargo para todo el consumo**. El esquema del EPRE cambia según mes y condición, y necesita una etapa adicional de reglas antes de hacer facturación.

## 3. Procedimiento de instalación

1. Copiar los **7 archivos nuevos** del ZIP en la misma raíz de `energia-ai`; combinar carpetas, no borrar nada anterior.
2. Confirmar que siguen presentes `src/energia_ai/data/tariff_catalog.py` y `requirements-tools.txt` de etapas previas.
3. En VS Code / PowerShell ejecutar:

```powershell
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m pip install -r requirements-tools.txt
.\.venv\Scripts\python.exe scripts\demo_tariff_service.py
.\.venv\Scripts\python.exe scripts\demo_tariff_tool.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

4. Esperar categoría R2 y cargos principales `9299.861 ARS/bimestre`, `289.4315 ARS/kWh`, régimen SIN_SEF, resolución EPRE 221/2026. **No es el total de la factura**.
5. Revisar que el resultado de `test_tariff_tool.py` no figure `skipped`. Las **46 pruebas anteriores** deben seguir aprobadas. Las **17 nuevas** llevan el total a **63 pruebas**.
6. Ejecutar `git status`, confirmar que no hay credenciales ni archivos ignorados incluidos, y registrar un commit.

## 4. Estado de revisión documental

El catálogo de la Etapa 02.2 trae inicialmente:

```python
estado_revision="PENDIENTE_CONTRASTE_CON_PDF_LOCAL"
```

Una vez completado y documentado el contraste manual en la Etapa 02.2, el equipo debe editar **esa línea del catálogo** a:

```python
estado_revision="CONTRASTADO_CON_PDF_LOCAL"
```

Esto **no verifica automáticamente** la fuente: solo registra la verificación realizada por el equipo. No cambiar tarifas ni otros campos. Si el estado permanece pendiente, el servicio lo expone y advierte que no debe utilizarse como insumo de informes económicos. El valor de cobertura `2027-01-31` es un límite del MVP, no una promesa de que no pueda publicarse otra resolución antes.

El cuadro de EPRE 221/2026 está en https://epremendoza.gob.ar/2019/resoluciones-anexos/Res%20221-2026.pdf, Anexo I (R1, R2, R3), y la resolución puede revisarse también desde https://epremendoza.gob.ar/resoluciones/.

## 5. Fallos esperados y decisiones

| Situación | Comportamiento |
| --- | --- |
| EDEMSA, noviembre 2026, 350 kWh, SIN_SEF | Recupera categoría R2, devuelve cargos y fuente |
| 600 kWh | Categoría R3 |
| Condición SEF | Devuelve base/excedente cuando corresponde, sin calcular subsidio |
| Distribuidora distinta | Error de validación |
| Fecha fuera de cobertura | `TARIFA_NO_DISPONIBLE` |
| Régimen desconocido | `PARAMETROS_INVALIDOS`; el agente pregunta |
| No hay consumo bimestral | `PARAMETROS_INVALIDOS`; no inventa el dato |

## 6. Por qué es una tool (y no pedirle al LLM que lo calcule)

El LLM interpreta el texto y elige esta operación. La tool ejecuta una selección precisa y reproducible de reglas de vigencia/categoría y de importes ya contrastados. Esta lógica **no** se ejecuta nuevamente mediante un PDF, scraping ni CSV para cada consulta. La dependencia de `@tool` se encuentra solamente en `agent/tariff_tool.py`; el dominio sigue testeable sin IA.

## 7. Lo que queda para la Etapa 03.3

Definir *simular_ahorro* con escenarios de consumo y condiciones tarifarias. No calcular automáticamente impuestos ni totales de factura hasta verificar reglas específicas de cada régimen. Si el alcance de tiempo no permite una factura completa, se devolverá una simulación parcial explícitamente identificada con sus supuestos.
