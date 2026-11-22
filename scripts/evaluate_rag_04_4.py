"""Ejecuta exactamente las 10 preguntas de la evaluación 04.3 sobre el índice nuevo.

No sobreescribe los reportes de la línea base ni asigna notas manuales.
"""
from __future__ import annotations
import json
from pathlib import Path
from energia_ai.agent.advice_tool import buscar_consejos, _get_searcher
from energia_ai.rag.evaluation import CASES, evaluar_casos, metricas_automaticas


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    target = root / 'data/processed/rag/evaluacion_04_4.json'
    if target.exists():
        raise SystemExit('Ya existe evaluacion_04_4.json: conservá tu revisión; renombralo si querés repetir.')
    _get_searcher.cache_clear()   # Si la app importó el módulo en este proceso.
    report = evaluar_casos(
        CASES,
        lambda q, k: buscar_consejos.invoke({'consulta': q, 'max_resultados': k}),
        k=3,
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', 'utf-8')
    metrics = metricas_automaticas(report)
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    print(f'Nueva evaluación creada: {target}')
    print('Asignar relevancia_manual, cita_verificada_manual y fragmento_completo_manual antes de comparar métricas manuales.')
    if metrics['consultas_con_error']:
        raise SystemExit('Hubo errores de recuperación. Conservar el reporte para diagnosticar; renombrarlo antes de reintentar.')

if __name__ == '__main__':
    main()
