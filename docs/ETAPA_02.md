# Etapa 02 — Ingeniería de datos

**Estado:** en progreso; subetapa 02.1 (inventario y adquisición).  
**Alcance:** suministros residenciales de **EDEMSA**, provincia de Mendoza.  
**Fuentes:** EPRE Mendoza y Secretaría de Energía de la Nación.

## Objetivo

Preparar un catálogo tarifario verificable para cargarlo en memoria RAM al ejecutar EnergiaAI, y reunir los documentos que utilizará el RAG. No entrenaremos un LLM ni ejecutaremos tools durante esta etapa.

## Subetapas previstas

1. **02.1 Inventario y adquisición:** registrar fuentes oficiales, descargar originales y auditar la integridad básica.
2. **02.2 Extracción y normalización:** identificar cuadros residenciales, cargo fijo, cargo variable, categorías, subsidios y unidades; llevar los valores verificados a estructuras de Python, sin requerir CSV de tarifas en tiempo de consulta.
3. **02.3 Validación de negocio:** comprobar valores contra anexos originales, condiciones de aplicación, vigencia y simulador oficial.
4. **02.4 Corpus RAG:** reunir **al menos 3 documentos** pertinentes y registrar sus metadatos y derechos de reutilización.
5. **02.5 Reproducibilidad:** documentar el procedimiento y crear pruebas del catálogo en memoria para reproducir los valores desde los documentos originales.

## Decisión arquitectónica — research side versus ejecución (21/11/2026)

Esta aclaración sustituye el planteo anterior de una base de tarifas consultada desde CSV.

- **Research side / preparación (Etapa 02):** descargar los PDF oficiales, verificar el texto y las tablas, anotar su procedencia y transcribir únicamente registros tarifarios contrastados. El inventario `data/metadata/fuentes.csv` y el reporte `data/processed/auditoria_fuentes.csv` son **archivos auxiliares de investigación**, no fuentes de cálculo del agente. Se usan únicamente al auditar y mantener los documentos, no en cada conversación.
- **Runtime / ejecución (Etapa 03):** un catálogo en objetos Python (por ejemplo, `src/energia_ai/data/tariff_catalog.py`) se carga en memoria al iniciar la aplicación. `consultar_tarifa` consulta los objetos ya cargados; **no abre CSV ni PDF por cada petición**.
- **RAG (Etapa 04):** procesa guías energéticas por separado; no usa embeddings para determinar importes tarifarios.
- **Memoria conversacional (Etapa 07):** `InMemorySaver` almacena el estado de las conversaciones y no debe confundirse con el catálogo de tarifas.

Para evitar trabajo innecesario, **no hay que borrar ni modificar** ahora `fuentes.csv`, `audit_sources.py` o `test_audit_sources.py`. El CSV sigue siendo útil como inventario opcional de auditoría y ya está integrado con los tests; no formará parte de `consultar_tarifa`.

Los datos tarifarios **no quedan automáticamente actualizados** por residir en memoria. Toda nueva resolución requerirá contraste, actualización del catálogo y recarga de la aplicación. Si falta una tarifa comprobada para el período solicitado, el agente debe declarar que no puede estimarla con precisión.

## 02.1 Descargas manuales

Guardá los archivos exactamente con las rutas indicadas en `data/metadata/fuentes.csv`.

- Resolución EPRE 221/2026: <https://epremendoza.gob.ar/2019/resoluciones-anexos/Res%20221-2026.pdf>
- Guía residencial nacional (junio 2024): <https://www.argentina.gob.ar/sites/default/files/guia_residencial_enereficiente.pdf>

En Windows, podés crear estas carpetas en la terminal de VS Code:

```powershell
New-Item -ItemType Directory -Force -Path data/raw/tariffs/mendoza/edemsa
New-Item -ItemType Directory -Force -Path data/raw/documents/argentina
```

Luego descargá los PDF desde el navegador y colocá cada archivo con el nombre previsto por el CSV.

Ejecutá el script desde la raíz del proyecto:

```powershell
.\.venv\Scripts\python.exe scripts\audit_sources.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Debería imprimir `OK_BASICO` para ambos archivos, sin que eso implique que hayan sido validados los valores de las tablas. El resumen con huellas SHA-256 se guardará en `data/processed/auditoria_fuentes.csv` (salida auxiliar de la auditoría, no utilizada durante las conversaciones).

## Separación de responsabilidades

- **Ingesta/validación (Etapa 02):** adquiere, extrae, contrasta y registra fuentes con trazabilidad.
- **Catálogo tarifario en memoria (Etapa 02.2):** objetos Python con registros contrastados, fechas, unidades y fuente oficial.
- **Tool `consultar_tarifa` (Etapa 03):** busca en el catálogo ya cargado en RAM. No abre CSV ni descarga PDFs por pregunta.
- **RAG (Etapa 04):** recupera recomendaciones documentales, no números tarifarios para efectuar cálculos.

## Precauciones

- La Resolución 221/2026 incluye anexos de diversos regímenes; no se deben copiar filas de columnas incorrectas.
- El cuadro indica cargos fijos **$/bimestre** y variables **$/kWh** para T1 residencial; no mezclar unidades.
- El régimen de subsidios **SEF** y los límites de consumo base dependen de fecha y condiciones; no simplificar todo a una tarifa plana.
- Una resolución puede modificarse durante el período anunciado. Guardar fecha de verificación y buscar actualizaciones en EPRE.
- No guardar facturas reales, N.º de suministro ni datos personales dentro del repositorio.
- La auditoría de cabecera PDF y SHA-256 detecta algunos problemas técnicos, pero **no certifica** que el documento fue emitido por el organismo ni valida datos contables.

## Criterios de aceptación de 02.1

- [ ] Dos PDF oficiales descargados y ubicados en las rutas previstas.
- [ ] Ambos figuran `OK_BASICO` en el reporte técnico.
- [ ] Confirmar manualmente título, organismo, fecha y ámbito de ambos documentos.
- [ ] Tests de la auditoría aprobados junto con los de la Etapa 01.
- [ ] Guardar un commit Git con el manifiesto, script y tests (sin incluir PDFs pesados ni información privada).

## Fuentes

- EPRE, resoluciones: <https://epremendoza.gob.ar/resoluciones/>
- EPRE, simulador residencial: <https://epremendoza.gob.ar/simulador-de-facturas-usuarios-residenciales/>
- Argentina, guías de consumo eficiente: <https://www.argentina.gob.ar/economia/energia/transicion-planeamiento-energetico/guias-de-consumo-eficiente>

## Evitar subir documentos binarios grandes a Git

Agregá `data/raw/` y `data/processed/auditoria_fuentes.csv` a `.gitignore` (sin borrar las reglas anteriores). En el repositorio sí versionamos `data/metadata/fuentes.csv`, scripts y pruebas para poder recuperar los PDF cuando sea necesario.

Para verificar las exclusiones en Windows:

```powershell
git check-ignore data/raw/tariffs/mendoza/edemsa/resolucion_epre_221_2026.pdf
```

El comando debe devolver la ruta del PDF. Verificá también que el reporte de auditoría quede ignorado, ya que es una salida generada localmente.

## Commit sugerido

```powershell
git add docs/ETAPA_02.md scripts/audit_sources.py tests/test_audit_sources.py data/metadata/fuentes.csv .gitignore
git commit -m "data: iniciar inventario y auditoria de fuentes oficiales"
```

## 02.1 — Cierre adaptado a la recomendación del profesor

Después de copiar el ZIP del paso 02.1.1:

1. Crear las carpetas de `data/raw`.
2. Descargar y renombrar los dos PDF oficiales según el inventario.
3. Agregar las dos reglas de exclusión al `.gitignore`.
4. Ejecutar `scripts/audit_sources.py` desde la raíz. **No** ejecuta tools de LangChain ni carga datos para el agente.
5. Confirmar `OK_BASICO` para ambos documentos y revisar manualmente su título y organismo.
6. Ejecutar `python -m unittest discover -s tests -v` con el Python de `.venv`; deben pasar 9 pruebas.
7. Crear el commit con los archivos de código e inventario; no subir PDFs ni salidas generadas.

**Siguiente paso: 02.2.** Leer el anexo de EDEMSA, definir un subconjunto residencial y transcribir los valores verificados al catálogo Python en memoria. Antes de introducir importes, debemos confirmar categoría, unidades, fecha, subsidio y resolución.
