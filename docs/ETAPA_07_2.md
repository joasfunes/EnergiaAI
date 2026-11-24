# EnergiaAI — Etapa 07.2: presentación y demostración

**Estado:** material preparado; cierre condicionado a ensayo y comprobación por el equipo.
**Tecnología conservada:** Qwen3.5 9B con Ollama; sin cambio de modelo ni del código energético.
**Antecedentes:** Etapa 07.1 cerrada por el equipo, con 299 pruebas aprobadas, instalación limpia verificada y commit registrado.

## Propósito

Preparar una defensa que demuestre que EnergiaAI cumple la consigna de la materia *Modelos de Lenguaje*:

- Agente `create_agent` con tarea de varios pasos y resultado final tangible.
- Mínimo tres tools necesarias; cada una con argumentos, salidas y manejo de errores.
- RAG sobre corpus propio con al menos tres documentos y citas verificables.
- Memoria con checkpointer que pueda demostrarse en un turno posterior.
- UI con Markdown, streaming de herramientas, argumentos y resultados resumidos.
- Presentación que explique y justifique arquitectura, elección del LLM, límites y riesgos.
- Repositorio reproducible y defensa de cualquier componente por cada integrante.

**Fuente:** `Consigna Integrador.pdf`, secciones 2–7 (págs. 1–4).

## Artefactos incluidos

- `presentacion/EnergiaAI_Presentacion_Defensa_07_2.pptx`: 18 diapositivas principales y 3 anexos. El PPTX es editable y contiene notas de exposición.
- `docs/GUIA_DEMO_07_2.md`: preparación, pasos de ejecución, evidencias, contingencias y criterios de aprobación.
- Este documento: instrucciones para incorporar el material y realizar la aceptación de 07.2.

## Decisiones de presentación

1. **Separar decisión y ejecución:** Qwen interpreta; LangChain orquesta; las tools Python calculan; ChromaDB recupera textos; SQLite persiste; ReportLab entrega el PDF.
2. **La cuatro tools energéticas son núcleo del caso principal:** `calcular_consumo`, `consultar_tarifa`, `simular_ahorro`, `buscar_consejos`. Otras dos (`registrar_electrodomestico`, `consultar_inventario`) permiten continuidad de uso.
3. **Resultados honestos:** 75 kWh actuales, 45 propuestos, ahorro 30 kWh y 40 % del equipo en el escenario ejemplo. No equivale a 40 % del hogar ni a un ahorro final de factura.
4. **RAG con límites:** Hit útil@3 pasó de 87,5 % a 100 % en ocho preguntas energéticas, pero la integridad sigue siendo baja (4/24 → 5/24); no ocultarlo.
5. **Rendimiento real:** 227,943 s en una medición particular; dos llamadas a Qwen acumulan 227,893 s; cálculo Python 0,003 s. No es un promedio general ni medición interna de Ollama.
6. **Seguridad:** prototipo académico para localhost; no desplegar públicamente sin identidad, permisos y gestión de datos.
7. **Pensamiento del LLM:** no inventar ni mostrar cadenas privadas de razonamiento. Solo mostrar salidas que el proveedor exponga explícitamente y, siempre, la traza de herramientas.

## Guía para presentar el archivo

1. Abrir el PPTX en PowerPoint o LibreOffice Impress.
2. Editar la portada con nombres de integrantes y datos institucionales reales. No inventar docente, integrantes ni URL de GitHub.
3. Conservar el alcance Mendoza/EDEMSA y las advertencias de la demo.
4. Revisar las **notas del orador** incorporadas en cada diapositiva.
5. Ensayar las 18 diapositivas principales. Las diapositivas 19–21 son anexos para preguntas y contingencias.
6. Si quieren mostrar capturas de Streamlit, utilizar capturas reales del sistema y rotularlas como tal; la diapositiva 12 contiene un esquema conceptual, no captura.
7. Utilizar un solo caso integral y una secuencia de memoria. Preparar todos los modelos e índices antes de la exposición.

## Criterios para cerrar 07.2

- [ ] Presentación personalizada (integrantes, GitHub y fecha real).
- [ ] Cada integrante puede explicar las seis tools y las decisiones principales.
- [ ] En vivo se observó tool calling real y sus argumentos/resultados en Streamlit.
- [ ] La consulta integral terminó en un PDF trazable y coherente.
- [ ] Se demostró un turno dependiente de memoria persistente.
- [ ] Se documentó la disponibilidad o ausencia de un bloque de razonamiento ofrecido por el proveedor.
- [ ] Se ensayó una contingencia en caso de lentitud o falta de evidencia.
- [ ] Se confirmó con la cátedra que la propuesta está aprobada y la fecha de exposición / entrega vigente.
- [ ] Commit del material de presentación registrado; sin incorporar secretos ni datos privados.

## Registro de cambios recomendado

```powershell
git add presentacion/EnergiaAI_Presentacion_Defensa_07_2.pptx docs/ETAPA_07_2.md docs/GUIA_DEMO_07_2.md
git commit -m "docs: preparar presentacion y demo del integrador"
git push
```

Antes de `git push`, comprobar `git status` y `git ls-files data/state data/raw data/vectorstore`.
