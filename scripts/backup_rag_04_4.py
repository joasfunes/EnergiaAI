"""Copia/recupera el índice de la Etapa 04.3 ANTES de reconstruirlo.

Ejecutar sin la aplicación/consultas abiertas. No se sube a Git.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil


INDEX = Path('data/vectorstore/energiaai_rag')
MANIFEST = Path('data/vectorstore/energiaai_rag_manifest.json')
BACKUPS = Path('data/vectorstore/rag_backups')
EVAL = Path('data/processed/rag/evaluacion_04_3.json')
BASELINE = Path('data/processed/rag/evaluacion_04_3_baseline.json')


def backup(root: Path) -> Path:
    root = root.resolve()
    db, manifest, report = root / INDEX, root / MANIFEST, root / EVAL
    if not db.is_dir() or not manifest.is_file():
        raise FileNotFoundError('No se encontró el índice 04.1 completo; no reconstruir todavía.')
    identifier = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    parent = root / BACKUPS
    parent.mkdir(parents=True, exist_ok=True)
    candidate = parent / identifier
    suffix = 0
    while candidate.exists():
        suffix += 1
        candidate = parent / f'{identifier}-{suffix}'
    candidate.mkdir()
    shutil.copytree(db, candidate / 'index')
    shutil.copy2(manifest, candidate / 'manifest.json')
    if report.is_file():
        shutil.copy2(report, candidate / 'evaluacion_04_3.json')
        # Copia fija para comparar con la evaluación mejorada.
        baseline = root / BASELINE
        if not baseline.exists():
            baseline.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(report, baseline)
    info = {'snapshot': candidate.name, 'fecha_utc': identifier,
            'indice': str(INDEX), 'manifiesto': str(MANIFEST),
            'evaluacion_incluida': report.is_file()}
    (candidate / 'snapshot.json').write_text(json.dumps(info, indent=2, ensure_ascii=False), 'utf-8')
    return candidate


def restore(root: Path, identifier: str) -> None:
    if not re.fullmatch(r'\d{8}T\d{6}Z(?:-\d+)?', identifier):
        raise ValueError('Identificador de respaldo inválido')
    root = root.resolve()
    snapshot = root / BACKUPS / identifier
    db, manifest = root / INDEX, root / MANIFEST
    if not (snapshot / 'index').is_dir() or not (snapshot / 'manifest.json').is_file():
        raise FileNotFoundError('Respaldo incompleto: no se restauró nada')
    if db.exists():
        shutil.rmtree(db)
    shutil.copytree(snapshot / 'index', db)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(snapshot / 'manifest.json', manifest)


def main() -> None:
    parser = argparse.ArgumentParser(description='Respaldo local RAG antes de la etapa 04.4')
    parser.add_argument('--restore', metavar='SNAPSHOT', help='Restaura el snapshot indicado, después de cerrar consultas')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if args.restore:
        restore(root, args.restore)
        print('Índice anterior restaurado. Reiniciar la aplicación para limpiar _get_searcher().')
    else:
        destination = backup(root)
        print(f'Respaldo creado en: {destination}')
        print('La versión original no se borró. Ahora se puede reconstruir explícitamente con --rebuild.')


if __name__ == '__main__':
    main()
