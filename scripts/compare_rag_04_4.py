"""Compara línea base 04.3 con 04.4; no asigna puntuaciones a IA."""
from __future__ import annotations
import json
from pathlib import Path
from energia_ai.rag.evaluation import metricas_automaticas, metricas_manuales


def read(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(f'Falta {path.name}; conservá la evaluación 04.3 antes de reemplazar nada')
    return json.loads(path.read_text('utf-8'))


def safe_manual(report: dict) -> dict | None:
    try:
        return metricas_manuales(report)
    except ValueError:
        return None


def comparison(root: Path) -> dict:
    directory = root / 'data/processed/rag'
    original = read(directory / 'evaluacion_04_3_baseline.json')
    improved = read(directory / 'evaluacion_04_4.json')
    if [case['id'] for case in original['casos']] != [case['id'] for case in improved['casos']]:
        raise ValueError('Las consultas no coinciden: comparar el mismo conjunto de evaluación')
    return {
        'descripcion': 'Comparación 04.3 vs 04.4. Métricas de recuperación, NO calidad de respuestas del LLM.',
        'automaticas_antes': metricas_automaticas(original),
        'automaticas_despues': metricas_automaticas(improved),
        'manuales_antes': safe_manual(original),
        'manuales_despues': safe_manual(improved),
        'revisiones_pendientes': safe_manual(original) is None or safe_manual(improved) is None,
    }


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    report = comparison(root)
    target = root / 'data/processed/rag/comparacion_04_4.json'
    target.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', 'utf-8')
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if report['revisiones_pendientes']:
        print('ATENCIÓN: falta revisión manual. No concluir que mejoró la pertinencia o integridad.')
    print(f'Comparación: {target}')

if __name__ == '__main__':
    main()
