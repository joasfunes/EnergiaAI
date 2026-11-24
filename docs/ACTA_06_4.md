# Acta de aceptación — EnergiaAI 06.4

> **Plantilla vacía**. Completar con ejecuciones observadas en Windows. No marcar como aprobado sin evidencias. Las cifras de consumo son referencias para el escenario sintético.

**Fecha de revisión:** _______________  
**Revisó:** _______________  
**Equipo:** Windows 11 / Ryzen 7 5700U / 16 GB RAM / Ollama + Qwen3.5 9B  
**Último commit:** _______________  
**Python:** 3.12  
**Modelo:** qwen3.5:9b  
**RAG:** embeddinggemma:300m + ChromaDB  

## Control automático

| Comprobación | Objetivo | Resultado real | Evidencia |
|---|---|---|---|
| Tests 06.4 | 25/25 OK | PENDIENTE | Terminal |
| Suite acumulada | 289/289 OK, 0 omitidas | PENDIENTE | Terminal |
| Prueba offline integral | `estado=ok` | PENDIENTE | `data/processed/qa/resultado_integracion_06_4.json` |
| Reglas de Git | 4 exclusiones presentes | PENDIENTE | `.gitignore` + `git status --ignored` |

## Pruebas reales desde la interfaz

| ID | Escenario | Estado (APROBADO/FALLÓ/PENDIENTE) | Resultado observado / enlace a captura |
|---|---|---|---|
| AC-01 | 4 tools, 75 → 45, 30 kWh, tarifa + RAG | PENDIENTE | |
| AC-02 | SIN estimación económica ante SEF o salto de banda | PENDIENTE | |
| AC-03 | Datos incompletos y PDF ausente | PENDIENTE | |
| AC-04 | Fuera de dominio e instrucciones engañosas | PENDIENTE | |
| AC-05 | Inventario persistente y 130 kWh tras reinicio | PENDIENTE | |
| AC-06 | Streaming y herramientas mostradas en orden | PENDIENTE | |
| AC-07 | PDF coherente, RAG citado y persistente | PENDIENTE | |
| AC-08 | Solo localhost; bases y claves fuera de Git | PENDIENTE | |

## Riesgos conocidos (no son bloqueos del prototipo local si están documentados)

- Qwen3.5 9B puede tardar varios minutos sobre el Ryzen 7 5700U. Referencia 06.1: **227,943 s en una medición**; no es el promedio.
- `SqliteSaver` e inventarios locales sin autenticación ni cifrado de datos; **no publicar en internet**.
- El RAG contiene algunos fragmentos con texto extraído de PDF incompleto; verificar toda cifra específica antes de aplicarla.
- El simulador **NO calcula una factura completa**, y solo monetiza si cumple las condiciones verificadas para EDEMSA SIN_SEF.
- Pueden ocurrir errores de planificación del LLM; el orden de tools debe validarse observando ToolMessages realmente ejecutados.
- La tarifa de noviembre de 2026 no debe presentarse como válida fuera de su fecha de cobertura; no hay sincronización automática con el EPRE.

## Incidencias y acciones correctivas

| Incidencia | Severidad | Acción y responsable | Reprueba realizada |
|---|---|---|---|
|  |  |  |  |

## Decisión de cierre

- [ ] Todas las comprobaciones necesarias están aprobadas.
- [ ] Los riesgos pendientes están documentados.
- [ ] Los datos de prueba no están incluidos en Git.
- [ ] El README final y la presentación quedan para Etapa 07.

**Decisión:** PENDIENTE / APROBADA CON LIMITACIONES / RECHAZADA  
**Firmas o responsables:** ________________________
