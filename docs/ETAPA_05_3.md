# EnergiaAI — Etapa 05.3: Memoria persistente, inventario del hogar y streaming

**Estado inicial:** 05.2 cerrada por el equipo; cuatro tools con Qwen, 182 tests en Windows y commit.  
**Objetivo:** reiniciar el programa sin perder el historial ni los electrodomésticos registrados, y poder ver la ejecución progresivamente.  
**Alcance:** prototipo LOCAL monousuario Windows 11, Python 3.12. **No es un backend multiusuario listo para Internet.**

## 1. Decisión arquitectónica

| Datos | Implementación | Identificador | Persistencia |
|---|---|---|---|
| Conversación | `SqliteSaver` de LangGraph | `thread_id` | SQLite `data/state/conversaciones.sqlite3` |
| Inventario | `InventarioHogar`, SQL parametrizado | `hogar_id` | SQLite `data/state/inventario.sqlite3` |
| RAG | ChromaDB existente | Colección 04.4 | No se modifica |
| Tarifas | Catálogo Python | EDEMSA + fecha + consumo | En memoria durante el proceso |

No debemos guardar datos del hogar únicamente en el historial conversacional. El `thread_id` representa una conversación; el `hogar_id` representa un hogar. Varios `thread_id` pueden utilizar el mismo inventario en este prototipo local. La autenticación real y los permisos de acceso se diseñarán antes de exponerlo a Internet.

Se conservan los cuatro nombres de tools existentes. Se agregan `registrar_electrodomestico` y `consultar_inventario`; su `hogar_id` se fija por el runtime, y **no** se acepta como argumento del LLM. El registro rechaza IDs duplicados en lugar de sobrescribir registros sin autorización.

`SqliteSaver.from_conn_string` devuelve un *context manager*. El runtime utiliza `with` para mantener viva la conexión mientras el agente atiende turnos y cerrarla ordenadamente al salir. Streaming con `stream_mode=['messages','updates']` y `version='v1'` para procesar tuplas de forma explícita.

## 2. Archivos incorporados

```text
src/energia_ai/services/home_inventory.py   NUEVO: repositorio SQLite y validación
src/energia_ai/agent/inventory_tools.py      NUEVO: dos tools ligadas al hogar activo
src/energia_ai/agent/persistent_runtime.py   NUEVO: agente con SqliteSaver y 6 tools
src/energia_ai/agent/streaming.py            NUEVO: eventos de texto y tool
scripts/chat_persistente.py                 NUEVO: consola conversacional
scripts/inspect_inventory.py                NUEVO: lectura sin LLM
requirements-persistence.txt               NUEVO: dependencia oficial SQLite

tests/test_home_inventory.py                NUEVO: 15 pruebas
tests/test_inventory_tools.py               NUEVO: 3 pruebas
tests/test_persistent_runtime.py            NUEVO: 4 pruebas
tests/test_streaming_05_3.py                NUEVO: 9 pruebas
docs/ETAPA_05_3.md                          NUEVO: esta guía
```

Total nuevas: **31 pruebas**, objetivo acumulado **213** (182 + 31). Las pruebas nuevas cubren SQLite, reinicio del repositorio, validación, aislamiento lógico de hogares, mocks del runtime y streaming. **No sustituyen** una prueba real de checkpoints con Ollama después de reiniciar.

## 3. Implementación en Windows, paso a paso

### 05.3.1 — Copiar los archivos

Extraer el ZIP y fusionar el contenido de su carpeta `energia-ai` con el repositorio existente. No eliminar nada ni reemplazar `full_agent.py`, `session.py` o las cuatro tools previas.

### 05.3.2 — Actualizar .gitignore

Agregar al final de tu `.gitignore` (sin borrar sus otras entradas):

```gitignore
# Datos personales y memoria conversacional del piloto
data/state/
```

**Importante:** la regla exacta es `data/state/`. Comprobar con `git check-ignore -v data/state/conversaciones.sqlite3` luego de generarlo.

### 05.3.3 — Dependencias

En la raíz del proyecto:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-persistence.txt
.\.venv\Scripts\python.exe -m pip install -e .
```

No descargar un modelo de lenguaje nuevo: reutilizar el Qwen que funciona en 05.2. El nuevo paquete instala el soporte SQLite de LangGraph.

### 05.3.4 — Tests aislados y completos

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_home_inventory.py -v
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_inventory_tools.py -v
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_persistent_runtime.py -v
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_streaming_05_3.py -v
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Esperado en Windows con dependencias completas: `Ran 213 tests` y `OK`, sin `skipped`. La compatibilidad real con la versión de LangChain/Ollama debe confirmarse allí.

### 05.3.5 — Primer chat y registro

Ejecutar:

```powershell
.\.venv\Scripts\python.exe scripts\chat_persistente.py --hogar-id casa_demo --thread-id charla_1
```

Escribir (mensaje de prueba; datos ilustrativos):

> Registrá un electrodoméstico nuevo en mi hogar: ID `tv_1`, nombre Televisor, potencia 100 W, 5 horas efectivas por día, durante 20 días y cantidad 1. Consultá el inventario y confirmame lo guardado.

Verificar en la traza que se ejecutó realmente `registrar_electrodomestico` con `estado=ok` y luego `consultar_inventario` con `estado=ok`. **Si Qwen responde sin ejecutar la tool, el guardado no está verificado.**

En otra terminal, comprobar SIN utilizar LLM:

```powershell
.\.venv\Scripts\python.exe scripts\inspect_inventory.py --hogar-id casa_demo
```

Esperado: lista con `tv_1` y `consumo_total_kwh` de `10.0000`, calculado desde el inventario real.

### 05.3.6 — Cerrar y abrir de nuevo: prueba de persistencia

Escribir `salir`, cerrar el programa, y volver a ejecutar **exactamente el mismo comando** con `casa_demo` y `charla_1`. Preguntar:

> Retomá esta conversación: ¿qué televisor registré anteriormente y cuánto consumía?

Se espera memoria del hilo + consulta al inventario. Revisar que el agente **ejecute** `consultar_inventario` antes de afirmar el contenido guardado. También es válido ejecutar `--consulta` para un solo turno:

```powershell
.\.venv\Scripts\python.exe scripts\chat_persistente.py --hogar-id casa_demo --thread-id charla_1 --consulta "¿Qué equipos tengo registrados? Consultá el inventario."
```

**Prueba negativa:** ejecutar con `--thread-id charla_2` para comprobar que es otro hilo; los equipos siguen siendo los de `casa_demo` porque hogar y thread son identificadores diferentes.

### 05.3.7 — Agregar equipo tras reinicio

Con el mismo `--hogar-id`, solicitar:

> Agregá al inventario un aire acondicionado ID `aire_1` de 1500 W, 4 horas efectivas por día durante 20 días, cantidad 1. Después consultá el inventario.

Verificar con `inspect_inventory.py` que existen ambos equipos, y que el consumo total calculado es **130.0000 kWh** para ese período de 60 días. Este cálculo es de los equipos registrados, no el consumo de una factura oficial.

### 05.3.8 — Probar streaming y límite

El modo predeterminado imprime el texto de Qwen por fragmentos y notifica **herramientas realmente ejecutadas**. Para comparar con el anterior modo de respuesta completa:

```powershell
.\.venv\Scripts\python.exe scripts\chat_persistente.py --hogar-id casa_demo --thread-id charla_3 --sin-stream
```

Streaming **no reduce necesariamente la duración total**. Con Ryzen 7 5700U y 16 GB de RAM, Qwen puede seguir demorando. Se revisará rendimiento en una iteración separada; no cambiar modelo sin comparar tool calling y calidad.

### 05.3.9 — Git

```powershell
git status
git add .gitignore requirements-persistence.txt docs/ETAPA_05_3.md src/energia_ai/services/home_inventory.py src/energia_ai/agent/inventory_tools.py src/energia_ai/agent/persistent_runtime.py src/energia_ai/agent/streaming.py scripts/chat_persistente.py scripts/inspect_inventory.py tests/test_home_inventory.py tests/test_inventory_tools.py tests/test_persistent_runtime.py tests/test_streaming_05_3.py
git commit -m "feat: guardar conversaciones y electrodomesticos con SQLite y streaming"
```

**Nunca subir** `data/state/`, facturas personales, datos del hogar, los checkpoints o contraseñas.

## 4. Criterios de aceptación

1. Las 31 pruebas nuevas y las 213 acumuladas pasan en Windows sin omisiones.
2. `SqliteSaver` guarda y recupera el historial después de reiniciar el proceso, con el mismo `thread_id`.
3. Inventario `tv_1` persiste al reiniciar y `consultar_inventario` lo recupera.
4. Se agrega `aire_1` mediante una llamada de tool real, sin sobrescribir `tv_1`.
5. `inspect_inventory.py` devuelve dos equipos y 130 kWh con datos de ejemplo.
6. Los mensajes de streaming no muestran los argumentos internos de herramientas ni prompts ocultos.
7. El modo sin streaming sigue funcionando; los cuatro servicios energéticos previos permanecen intactos.
8. Se registra commit y `data/state/` está ignorado por Git.

## 5. Límites importantes

- **Solo desarrollo local monousuario**: `hogar_id` es un selector, NO autenticación. Sin permisos reales no usar este sistema como servicio web multiusuario. Faltan sesiones autenticadas, aislamiento de tenants, cifrado en reposo, backups/retención y eliminación de datos personales.
- Los DB SQLite locales NO están cifrados de forma predeterminada. Evitar datos sensibles reales y no sincronizar `data/state/` con repositorios.
- La persistencia no equivale a una solución de memoria ilimitada: conversaciones largas pueden hacer crecer el contexto del LLM y aumentar la latencia. Evaluar truncado/resumen en otro paso.
- `registrar_electrodomestico` solo **agrega**. Edición, borrado y versionado de registros se desarrollarán luego (evita sobrescrituras no intencionales).
- El inventario representa consumo supuesto de potencia constante; no es una medición ni una factura real.
- Una tool puede estar bien implementada y el LLM elegir no invocarla; por eso se exige corroborar la traza y el resultado en SQLite.
- El streaming muestra progreso, pero no garantiza respuesta más rápida.

## Referencias

- https://reference.langchain.com/python/langgraph.checkpoint.sqlite/SqliteSaver/from_conn_string
- https://github.com/langchain-ai/langgraph/blob/main/libs/checkpoint-sqlite/README.md
- https://github.com/langchain-ai/docs/blob/main/src/oss/langchain/streaming.mdx
