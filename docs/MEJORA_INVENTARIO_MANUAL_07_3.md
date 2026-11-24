# EnergiaAI · Rama de mejora: inventario manual

**Rama prevista:** `feat/inventario-manual-ui`  
**Base:** `main` (no fusionar hasta la aceptación)  
**Entorno:** Windows 11, Python 3.12, Streamlit local, SQLite.

## Objetivo

Separar la administración de electrodomésticos del agente. La interfaz usa `st.data_editor` para añadir, editar y borrar filas. El agente conserva la tool de lectura `consultar_inventario` y las cuatro tools energéticas; no puede modificar el inventario por chat.

## Archivos afectados

- `app.py`: selector de sección y acceso a `Mis electrodomésticos`; conserva chat, streaming, PDF y sidebar.
- `src/energia_ai/ui/inventory_editor.py`: nueva página Streamlit, tabla editable, normalización y errores.
- `src/energia_ai/services/home_inventory.py`: guardado atómico de la tabla y verificación de versión para evitar sobrescribir cambios desde otra sesión.
- `src/energia_ai/agent/inventory_tools.py`: deja de exponer `registrar_electrodomestico`; solo ofrece `consultar_inventario`.
- `src/energia_ai/agent/persistent_runtime.py`: prompt y registro de tools ajustados a cinco herramientas.
- `tests/test_inventory_editor_07_3.py`: diez casos nuevos.
- `tests/test_inventory_tools.py`, `tests/test_persistent_runtime.py`, `tests/test_telemetry_06_1.py`: adaptan las pruebas previas al diseño nuevo.

## 1. Crear la rama ANTES de incorporar los cambios

En PowerShell, con VS Code abierto en la raíz del proyecto y Streamlit detenido:

```powershell
git status
git switch main
git pull --ff-only origin main
git switch -c feat/inventario-manual-ui
git branch --show-current
```

**No continúes si hay cambios locales sin guardar**. En ese caso, hacé primero un commit de los cambios pendientes o guardalos mediante `git stash` si sabés cómo restaurarlos. Nunca sobrescribas una modificación propia sin compararla.

La cuenta GitHub conectada al asistente no otorgó permisos de escritura, por lo que el asistente no pudo crear la rama remota. Estos comandos la crean localmente.

## 2. Resguardar la base local

Detené Streamlit. Si ya existe `data/state/inventario.sqlite3`, guardá una copia privada en una carpeta fuera del repositorio. **No subas bases de datos ni credenciales a GitHub**. La mejora reutiliza el mismo esquema SQLite; no requiere migrar ni borrar datos.

## 3. Incorporar los archivos

Descomprimí `EnergiaAI_Mejora_Inventario_Manual_Rama.zip` en la **raíz** de `energia-ai`, conservando subcarpetas y reemplazando los archivos indicados. El ZIP incluye solo los diez archivos modificados/nuevos, no el repositorio completo.

En PowerShell, si el archivo se descargó a Descargas:

```powershell
Expand-Archive -Path "$HOME\Downloads\EnergiaAI_Mejora_Inventario_Manual_Rama.zip" -DestinationPath . -Force
git status
git diff --stat
git diff -- app.py src/energia_ai/agent/persistent_runtime.py
```

Revisá los cambios de `app.py` si habías personalizado la interfaz después de la última entrega.

## 4. Comprobar las pruebas

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_inventory_editor_07_3.py" -v
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Se espera un total **potencial** de 309 pruebas (299 anteriores + 10 nuevas). Confirmar que el total y las omisiones reflejen el entorno completo. No interpretar como aprobación definitiva un resumen con pruebas omitidas.

## 5. Probar manualmente la interfaz

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501
```

1. Elegí un hogar nuevo `hogar_tabla_demo` (no reutilices uno con inventario real).
2. En la barra lateral seleccioná **Mis electrodomésticos**.
3. Agregá por lo menos ocho filas. Usá IDs alfanuméricos distintos, potencias mayores que cero y hasta 20000 W; las horas son efectivas por día y deben estar entre 0 y 24, días entre 0 y 60 y cantidad entre 1 y 30.
4. Guardá. Deben persistir ocho filas y aparecer el consumo total estimado.
5. Editá una potencia y guardá; volvé a entrar y comprobá que se mantuvo.
6. Eliminá una fila con el control del editor y guardá; verificá que haya siete.
7. Intentá introducir dos IDs iguales: la operación debe fallar **sin modificar** el inventario anterior.
8. Presioná **Descartar y recargar** para volver a ver los datos guardados.
9. Volvé a **Consultor IA** y preguntá: «Consultá el inventario de mi hogar y calculá el consumo de sus equipos». Verificá `consultar_inventario` y `calcular_consumo` en la traza.
10. Pedile «Registrá un horno por chat». Debe indicar que uses **Mis electrodomésticos**, no inventar un registro.
11. Reiniciá Streamlit y confirmá que la tabla y la conversación siguen persistiendo.

El panel **Inventario registrado** de la barra lateral es de solo lectura y ofrece una comprobación adicional del guardado real.

## 6. Criterios de aceptación

- [ ] Rama local correcta y `main` intacta.
- [ ] Sin cambios en catálogo tarifario, RAG, motor de ahorro, reportes ni bases existentes.
- [ ] Altas, ediciones y bajas en una operación atómica.
- [ ] Datos inválidos y duplicados no modifican el inventario.
- [ ] Cambios realizados desde otra sesión no se sobrescriben inadvertidamente.
- [ ] Lectura del agente refleja el inventario guardado.
- [ ] Cinco tools disponibles para el agente, sin capacidad de escritura en inventario.
- [ ] Pruebas automáticas completas y demostración en Streamlit satisfactorias.
- [ ] Persistencia tras reiniciar y aislamiento lógico entre hogares de prueba.

## 7. Publicar la rama y conservar `main`

Solo después de comprobar las pruebas:

```powershell
git add app.py src/energia_ai/services/home_inventory.py src/energia_ai/ui/inventory_editor.py src/energia_ai/agent/inventory_tools.py src/energia_ai/agent/persistent_runtime.py tests/test_inventory_editor_07_3.py tests/test_inventory_tools.py tests/test_persistent_runtime.py tests/test_telemetry_06_1.py docs/MEJORA_INVENTARIO_MANUAL_07_3.md
git commit -m "feat: administrar electrodomesticos desde tabla en Streamlit"
git push -u origin feat/inventario-manual-ui
```

**No ejecutar merge todavía.** Después de la aceptación podremos revisar un pull request hacia `main`, actualizar la presentación/bitácora y ajustar los prompts de pruebas para comenzar por el registro manual.

## Observaciones

- Prototipo académico local sin autenticación: nunca exponer Streamlit a internet con hogares reales.
- El inventario tiene período fijo de 60 días para el piloto; no cambiarlo silenciosamente.
- Al eliminar una fila de la tabla se elimina ese equipo del inventario guardado cuando se confirma **Guardar tabla**.
- Las conversaciones previas siguen en SQLite; el agente nuevo no puede invocar la tool antigua, pero las trazas históricas pueden seguir mostrando registros anteriores.
- Los valores de los equipos son estimaciones de potencia constante, no mediciones de la factura eléctrica.
