# Etapa 02.2 — Catálogo tarifario EPRE en memoria

## Objetivo

Representar **solo T1 residencial (hasta 10 kW), EDEMSA**, a partir de la
Resolución EPRE 221/2026, Anexo I, sin hacer todavía cálculos de factura.

## Fuente oficial y evidencia

- Organismo: EPRE Mendoza.
- Resolución: **221/2026**, 5 de noviembre de 2026.
- Documento: https://epremendoza.gob.ar/2019/resoluciones-anexos/Res%20221-2026.pdf
- Anexo I: **página 4 del PDF** (índice 3 desde cero), tabla **Tarifa 1 -
  Pequeñas demandas / Residencial**.
- Vigencia declarada: desde el 1/11/2026. La ventana noviembre 2026–enero
  2027 es **cobertura del MVP**, no garantía de que no exista una
  resolución posterior.

## Extracción realizada

Los importes se transcribieron visualmente de la tabla a Python, utilizando
`Decimal` para preservar precisión decimal. Separar unidad de cargo fijo
(`$/bimestre`) y variable (`$/kWh`).

| Categoría | Consumo bimestral | Fijo sin SEF | Variable sin SEF | Fijo SEF / base | Variable SEF / base | Fijo SEF excedente | Variable SEF excedente |
|---|---|---:|---:|---:|---:|---:|---:|
| R1 | 0–299 | 8526,621 | 297,8234 | 7893,019 | 182,8933 | No aplica como columna separada | No aplica como columna separada |
| R2 | 300–599 | 9299,861 | 289,4315 | 7640,151 | 182,3271 | 9299,861 | 289,4315 |
| R3 | Desde 600 | 54659,736 | 259,3782 | 41234,213 | 165,1047 | 54659,736 | 259,3782 |

Nota del cuadro: facturación mínima, 45 kWh/bimestre. Para SEF:
noviembre, consumo base 400 kWh/bimestre; diciembre y enero,
600 kWh/bimestre. **No implementar automáticamente esos bloques sin
validar el criterio de facturación en la etapa 03**.

## Validación manual obligatoria por el equipo

1. Abrir `data/raw/tariffs/mendoza/edemsa/resolucion_epre_221_2026.pdf`.
2. Comprobar la resolución, la fecha y el Anexo I, página 4.
3. Comparar **celda por celda** los seis cargos sin SEF y los importes con
   SEF contra `src/energia_ai/data/tariff_catalog.py`.
4. Comprobar límites R1/R2/R3 y la unidad de cada cargo.
5. Revisar las notas de base subsidiada y la facturación mínima.
6. Consultar las resoluciones del EPRE para descartar modificaciones
   posteriores, antes de mostrar importes en una demo.
7. Registrar en el commit o en la documentación de validación quién y
   cuándo realizó el contraste. Hasta ese momento el estado del código
   permanece `PENDIENTE_CONTRASTE_CON_PDF_LOCAL`.

## Límites explícitos del catálogo

- No calcula el total de la factura: faltan impuestos, tasas, cargos
  adicionales, prorrateos por fecha y posibles adecuaciones.
- No interpreta todavía cómo se aplica el cargo fijo SEF excedente o el
  consumo base a períodos que cruzan meses.
- No cubre categorías comerciales, industriales, electrodependientes ni
  otras distribuidoras.
- La categoría se elige con un consumo **entero bimestral facturado**, no
  con los kWh estimados de un solo aparato.
- Si la fecha queda fuera de la cobertura, el catálogo falla explícitamente.
- No hay actualización automática ni lectura del PDF por cada consulta.

## Procedimiento en Windows PowerShell (raíz `energia-ai`)

```powershell
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe scripts\inspect_tariff_catalog.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Las **9 pruebas nuevas** del módulo comprueban los límites, importes
transcritos, tipos, fechas, inmovilidad de objetos y ausencia de huecos.
Con las 9 pruebas anteriores, el total esperado es **18**.

## Arquitectura

- `tariff_catalog.py`: tipos y **constantes cargadas en RAM** al importar.
- `inspect_tariff_catalog.py`: inspección manual sin cálculos de facturas.
- `test_tariff_catalog.py`: validaciones automáticas de integridad.
- `pyproject.toml`: instalación editable de `src/energia_ai`.

La futura herramienta de la Etapa 03 `consultar_tarifa` utilizará la misma
estructura de datos. `fuentes.csv` permanece solo en el flujo de auditoría
(*Research side*) de la Etapa 02.1; nunca es parte del runtime del LLM.

## Criterio de aceptación

La subetapa se cierra cuando:
- Las tres bandas son visibles en el diagnóstico y se contrastaron con el PDF.
- Se distinguen correctamente los cargos y regímenes sin inventar reglas.
- Las 18 pruebas totales pasan.
- Se documentó la fuente y el estado de revisión.
- Se creó un commit con los nuevos archivos.
