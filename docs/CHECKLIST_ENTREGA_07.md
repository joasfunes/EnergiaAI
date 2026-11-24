# Checklist de entrega — EnergiaAI

Este archivo es un **control a completar por el equipo**; no contiene aprobaciones inventadas.

## Repositorio (consigna, sección 6)
- [ ] Código completo en GitHub, rama final confirmada, commit anterior a presentación.
- [ ] `README.md` explica instalación limpia, Ollama, corpus, ejecución y demo.
- [ ] `.env.example` sin secretos y variables opcionales precisas.
- [ ] `requirements.txt` incluye dependencias completas.
- [ ] Corpus reproducible con 3 fuentes oficiales (descarga, preparación, chunks, embeddings, ChromaDB).
- [ ] `.gitignore` y `git ls-files` verificados: no subir bases, historial, PDF de usuarios, modelos, `.env`.
- [ ] Prueba desde clon limpio documentada y reproducible.

## Caso de uso y tecnología
- [ ] `create_agent`, no Deep Agents.
- [ ] Cuatro tools energéticas reales en caso principal; dos de inventario para continuidad.
- [ ] Tool propia con cálculos determinísticos y tool externa (SQLite/Chroma).
- [ ] Entradas, salidas y errores controlados; evidencia de ejecución y orden.
- [ ] RAG con tres documentos: chunking, embeddings, index, recuperación y citas.
- [ ] SQLite y `thread_id`: turno dependiente del anterior, aun tras reinicio.
- [ ] Streamlit: Markdown y tools visibles en streaming con argumentos y resultados depurados.
- [ ] Razonamiento: documentar si Qwen/Ollama NO expone bloques separables; no simularlos.
- [ ] Informe PDF real con gráficos, advertencias y fuentes cuando corresponda.

## Defensa
- [ ] Presentación: caso de uso, modelo elegido y motivos, diagrama, tools, RAG, memoria, UI y límites.
- [ ] Demo real: mismo caso integral EDEMSA de 350 kWh bimestrales y 30 kWh ahorrados.
- [ ] Demostración de memoria con nuevo equipo y recuperación posterior.
- [ ] Mostrar resultados de evaluación RAG (10 consultas) y latencia medida del LLM.
- [ ] Cada integrante explica **cualquier** herramienta y mecanismo técnico.
- [ ] Plan de contingencia por lentitud de Qwen local con evidencia histórica REAL y demo breve.

## Evidencia
- Fecha y responsable: **pendiente de completar**.
- GitHub URL: **pendiente**.
- Commit / rama entregada: **pendiente**.
- Resultado del preflight: **pendiente**.
- Suite de pruebas (total, errores, omisiones): **pendiente**.
- Acta de aceptación: `docs/ACTA_06_4.md` — completar y enlazar capturas reales.
