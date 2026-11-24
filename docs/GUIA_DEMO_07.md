# Guía de demostración — EnergiaAI

## Inicio (explicar en 30–60 s)
- Dominio: hogares residenciales EDEMSA en Mendoza.
- Problema: detectar consumo por equipo y estimar efecto de cambiar hábitos; no factura oficial.
- Arquitectura: Qwen3.5 9B + LangChain `create_agent`, cuatro tools energéticas principales, RAG de tres fuentes, SQLite, Streamlit y PDF.

## Demo A — Tarea integral (herramientas necesarias)
Abrir Streamlit en localhost y usar **un chat nuevo con datos ficticios**:

> Mi hogar consume 350 kWh por bimestre con EDEMSA, régimen SIN_SEF, tarifa del 15/11/2026. Analizá un período de 60 días. Mi aire acondicionado de 1500 W se usa 5 horas efectivas por día durante 10 días. ¿Cuánto ahorraría si lo usara 3 horas por día durante los mismos 10 días? Calculá consumo, consultá tarifa, simulá ahorro y buscá consejos oficiales para el verano.

Verificar sin anticipar éxito: herramientas realmente solicitadas y ejecutadas, argumentos visibles, respuesta y PDF descargable. Cifras esperadas: 75 kWh → 45 kWh; ahorro 30 kWh; hogar 350 → 320 kWh, ambos R2. El ahorro monetario, si disponible, solo es **componente variable**, no factura.

Si no se ejecutan todas las tools, registrar el resultado como parcial y examinar la traza en vez de afirmar lo contrario. No cambiar datos para forzar un monto.

## Demo B — Memoria (turno dependiente del anterior)
En hogar nuevo y conversación de prueba: registrar televisor de 100 W, 5 h/día, 20 días; verificar con tool/inventario que son 10 kWh. Reiniciar servidor y recuperar mismo thread. Agregar aire de 1500 W, 4 h/día, 20 días; comprobar inventario total 130 kWh. No usar un perfil de un usuario real.

## Demo C — Resultado tangible
Desde la conversación integral, pulsar «Preparar informe PDF» y luego descargar. Revisar que el informe cite fuentes realmente recuperadas, exhiba gráficos y advertencias y no invente ahorros cuando falte evidencia.

## Pruebas de contingencia
- Ollama lento (~228 s observados en 06.1): iniciar una única consulta integral con anticipación en el entorno de demo y mostrar progreso; **no presentar una grabación como ejecución en vivo**.
- Si el servicio local se cae: mostrar error y pruebas históricas documentadas, dejando claro que ya no es una prueba en vivo.
- Si el RAG devuelve `sin_resultados`: explicar que la herramienta no inventa recomendaciones; si faltan embeddings, mostrar instrucciones para reconstruirlos.
- Si falla un PDF: ejecutar demostración offline `scripts/demo_report_06_3.py`, diferenciándola de la herramienta del agente.
- No mostrar cadenas privadas de razonamiento; mostrar únicamente los eventos que el proveedor entrega y las tools visibles.

## Preguntas para ensayar
¿Por qué una tool y no cálculos del LLM? ¿Por qué `Decimal`? ¿Por qué RAG y no fine-tuning? ¿Qué guarda SQLite? ¿Qué significan distancias de embeddings? ¿Por qué no se monetiza SEF? ¿Qué pasa si la tarifa cambia? ¿Qué muestra el streaming y qué no? ¿Cuáles son los riesgos de publicar esta aplicación?
