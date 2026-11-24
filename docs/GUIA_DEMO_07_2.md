# EnergiaAI — Guion verificable de demostración (Etapa 07.2)

> **Uso:** guía del equipo para la demostración, no un registro de pruebas ya ejecutadas. Marcar los resultados reales en el ensayo y durante la exposición.

## A. Preparación previa en la computadora de exposición

**Entorno esperado:** Windows 11, Python 3.12, Qwen3.5 9B y EmbeddingGemma 300M instalados, Streamlit, LangChain, ChromaDB y SQLite del proyecto.

1. Abrir PowerShell en el directorio raíz `energia-ai`, que contiene `app.py`.
2. Comprobar modelos locales:

```powershell
ollama list
```

Debe figurar `qwen3.5:9b` y `embeddinggemma:300m`.

3. Verificar que los servicios y artefactos estén presentes:

```powershell
.\.venv\Scripts\python.exe scripts\preflight_entrega_07.py --modo ejecucion
```

4. Si falta el índice vectorial, reconstruirlo **antes** de la demostración según el README. No volver a generar embeddings durante la presentación.
5. Iniciar Streamlit:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501
```

6. Abrir http://127.0.0.1:8501. Mantener una segunda terminal disponible para diagnóstico (`ollama ps`).
7. Usar **hogar y conversación de prueba, con datos ficticios**. No mostrar chats, documentos ni claves reales.
8. Tener visible la pestaña de trazas del agente. Si se van a usar capturas, deben ser genuinas y rotuladas.

**Latencia comprobada:** medición puntual 06.1 de 227,943 s; el tiempo hasta primera salida fue de 187,179 s. No prometer respuesta instantánea ni hacer varias consultas integrales simultáneas. Mostrar que la interfaz está procesando desde el inicio.

## B. Demo 1 — Caso de uso integral (principal)

Crear una conversación nueva y enviar **este texto exacto**:

> Mi hogar consume 350 kWh por bimestre con EDEMSA, bajo régimen SIN_SEF y tarifa del 15 de noviembre de 2026. Quiero analizar un período de 60 días. Tengo un aire acondicionado de 1500 W que utilizo 5 horas efectivas por día durante 10 días del bimestre. ¿Cuánto podría ahorrar si lo utilizara 3 horas efectivas por día durante esos mismos 10 días? Calculá el consumo, consultá la tarifa, simulá ambos escenarios y buscá consejos oficiales de eficiencia para el verano en Mendoza.

### Qué observar, en vivo y en orden registrado

| Componente | Evidencia necesaria | Esperado en el ejemplo |
|---|---|---|
| `calcular_consumo` | Tool ejecutada (no solo mencionada) | 75 kWh del aire en escenario actual |
| `consultar_tarifa` | Tool ejecutada + datos/fuente | EDEMSA, 350 kWh bimestrales, R2, SIN_SEF |
| `simular_ahorro` | Tool ejecutada + validación | 75 → 45 kWh, delta de 30 kWh, 40 % del equipo; hogar 350 → 320 kWh (R2) |
| `buscar_consejos` | Tool ejecutada + resultados | Fragmentos oficiales útiles de verano / guía nacional, con URLs o citas |
| Streamlit | Eventos observables durante el proceso | Nombre, argumentos permitidos y estado/resumen de cada tool |
| Salida final | Respuesta consistente | Ningún importe final de factura inventado |

No presuponer que el agente invoca las herramientas en un orden fijo: anotar el orden observado. Si omite una, clasificar el resultado como **parcial** y revisar la traza, sin atribuir una ejecución inexistente.

### Prueba del artefacto tangible

1. En el **mismo turno** que recuperó simulación y RAG, pulsar **Preparar informe PDF**.
2. Pulsar **Descargar informe energético (PDF)**.
3. Abrirlo y comprobar: 75 kWh, 45 kWh, delta 30 kWh, gráficos, advertencias y fuentes realmente recuperadas.
4. Si `simular_ahorro` devolvió estimación en pesos, aclarar que corresponde solo al **componente variable**, no a la factura final.
5. No afirmar una cita si el PDF indica que no hubo recuperación RAG verificable en el mismo turno.

## C. Demo 2 — Memoria persistente (turno dependiente)

Usar un hogar de prueba separado y un identificador de conversación reconocible.

**Primer turno**

> Registrá un electrodoméstico en este hogar: ID `tv_demo_07`, nombre Televisor, potencia 100 W, cinco horas efectivas por día, 20 días de uso y cantidad 1. Después consultá el inventario para confirmar que quedó guardado.

Esperar una ejecución real de `registrar_electrodomestico`. Verificar el **inventario posterior** al registro, no una consulta anterior. Esperado: 10 kWh.

**Reinicio**

Cerrar Streamlit con `Ctrl+C`, volver a iniciarlo y seleccionar **el mismo hogar y el mismo hilo**.

**Segundo turno, dependiente**

> Recuperá el inventario que registramos anteriormente. Agregá un aire acondicionado con ID `aire_demo_07`, 1500 W, cuatro horas efectivas por día, 20 días y cantidad 1. Después consultá todos los equipos y su consumo total.

Esperado: TV 10 kWh + aire 120 kWh = **130 kWh**, sin borrar el primer equipo. Verificar contra el panel de inventario o con:

```powershell
.\.venv\Scripts\python.exe scripts\inspect_inventory.py --hogar-id TU_HOGAR_ID
```

No reutilizar IDs en un hogar donde los equipos ya existen. Si ya se ejecutó una demo de prueba, crear un hogar nuevo o IDs nuevos.

## D. Evidencia adicional que puede mostrar el equipo

- La traza de una conversación real: último turno, herramientas ejecutadas y sus estados.
- La evaluación RAG 04.3 vs 04.4: Hit útil@3 87,5 % → 100 % (muestra pequeña), baja integridad documentada.
- Pruebas automatizadas confirmadas por el equipo: **299** al cerrar 07.1.
- Rendimiento medido: dos llamadas del modelo 178,832 s y 49,061 s; tool de cálculo 0,003 s. No atribuir la causa a CPU o GPU sin medirla.
- Repositorio GitHub: README, `.env.example`, `requirements.txt`, scripts de ingesta y reconstrucción de ChromaDB. Verificar URL real antes de la exposición.

## E. Respuestas previstas ante incidencias

| Incidencia | Acción honesta |
|---|---|
| Qwen tarda | Mantener la UI y eventos visibles; esperar el resultado real. No presentar capturas como ejecución en vivo. |
| Ollama se cae o supera una espera tolerable | Mostrar diagnóstico y registro de pruebas anterior **rotulado como evidencia histórica**, declarando que el live falló. |
| Falta una herramienta esencial | Mostrar la traza y decir que el recorrido principal no quedó completamente validado en esa corrida. |
| RAG devuelve `sin_resultados` | Explicar umbral de evidencia insuficiente y no improvisar citas. |
| Falta monetización | Mostrar kWh y explicar la restricción de SEF, categoría, vigencia o verificación. |
| PDF no disponible | Mostrar el generador offline como prueba del módulo, sin atribuirlo falsamente al agente. |
| La cátedra pregunta por razonamiento interno | Mostrar solo lo que la integración expone legítimamente; la traza de tools es comprobable, el chain-of-thought oculto no. |

## F. Checklist antes de exponer

- [ ] Propuesta previa efectivamente aprobada por la cátedra.
- [ ] Fecha de exposición/entrega vigente confirmada (la consigna impresa conserva fechas originales).
- [ ] PowerPoint actualizado con integrantes, URL real y sin ejemplos rotulados incorrectamente.
- [ ] `git status` limpio y último commit subido.
- [ ] Ollama y los dos modelos operativos.
- [ ] RAG indexado y `preflight` correcto.
- [ ] Streamlit en `127.0.0.1:8501`.
- [ ] Hogares ficticios, IDs nuevos y conversaciones de prueba.
- [ ] Prueba integral: cuatro tools, datos y PDF verificables.
- [ ] Prueba memoria: un turno depende del anterior después del reinicio.
- [ ] Todos pueden justificar las seis tools, RAG, memoria y seguridad.

## G. Plan de exposición con las diapositivas

- **Diapositivas 1–4:** problema, usuario, alcance y tarea integral.
- **5–9:** arquitectura, tools, ciclo ReAct, reglas económicas y RAG.
- **10–14:** métricas de RAG, memoria, UI, PDF y rendimiento.
- **15–18:** pruebas, límites, plan demo y conclusiones.
- **19–21:** anexos para preguntas de la cátedra y contingencias; no es necesario proyectarlos si el tiempo no lo permite.

Las diapositivas poseen notas del orador editables. Esta guía se complementa con `docs/GUIA_DEMO_07.md` de la Etapa 07.1.
