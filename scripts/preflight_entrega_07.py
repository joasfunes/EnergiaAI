"""Comprobaciones de entrega de EnergiaAI sin ejecutar Qwen.

Modos:
  repo       valida archivos, dependencias, exclusiones y Git si disponible
  ejecucion  agrega presencia de corpus/indice y dependencias instaladas

NO comprueba conectividad a Ollama, exactitud del catálogo o demo en vivo.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
from importlib import metadata

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = (
    'README.md', '.env.example', '.gitignore', 'app.py', 'pyproject.toml',
    'requirements.txt', 'requirements-rag-prep.txt', 'requirements-rag-index.txt',
    'requirements-tools.txt', 'requirements-llm.txt', 'requirements-persistence.txt',
    'requirements-ui.txt', 'requirements-report.txt', 'requirements-qa.txt',
    'src/energia_ai/agent/persistent_runtime.py',
    'src/energia_ai/agent/full_agent.py',
    'src/energia_ai/reporting/pdf_report.py',
    'src/energia_ai/rag/vector_store.py',
    'scripts/build_rag_index.py',
    'scripts/prepare_rag_corpus.py',
    'scripts/fetch_rag_sources.py',
    'docs/ACTA_06_4.md',
)
REQUIRED_INCLUDES = (
    'requirements-rag-prep.txt', 'requirements-rag-index.txt',
    'requirements-tools.txt', 'requirements-llm.txt',
    'requirements-persistence.txt', 'requirements-ui.txt',
    'requirements-report.txt', 'requirements-qa.txt',
)
IGNORE_LINES = ('data/raw/', 'data/processed/', 'data/vectorstore/', 'data/state/', '.env', '*.egg-info/')
RUNTIME_FILES = (
    'data/processed/rag/corpus_report.json',
    'data/processed/rag/arg_residencial_2024.md',
    'data/processed/rag/epre_invierno_2022.md',
    'data/processed/rag/epre_verano_2025.md',
    'data/vectorstore/energiaai_rag_manifest.json',
)
RUNTIME_DISTS = ('langchain', 'langchain-ollama', 'langgraph-checkpoint-sqlite', 'streamlit',
                 'chromadb', 'ollama', 'reportlab', 'pypdf', 'PyMuPDF')
SENSITIVE_TRACKED_PREFIXES = ('data/raw/', 'data/processed/', 'data/vectorstore/', 'data/state/',
                              '.venv/', 'venv/', 'src/energia_ai.egg-info/')


def inspect_repo(root: Path, *, tracked: list[str] | None = None) -> dict:
    """Revisa estructura, dependencias y seguridad de rutas versionadas."""
    root = Path(root)
    faltantes = [x for x in REQUIRED_FILES if not (root / x).is_file()]
    req_path = root / 'requirements.txt'
    includes = []
    if req_path.is_file():
        for line in req_path.read_text(encoding='utf-8').splitlines():
            clean = line.split('#', 1)[0].strip()
            if clean.startswith('-r '):
                includes.append(clean[3:].strip())
    req_faltantes = [x for x in REQUIRED_INCLUDES if x not in includes or not (root / x).is_file()]
    ign_path = root / '.gitignore'
    ignore = set(ign_path.read_text(encoding='utf-8').splitlines()) if ign_path.is_file() else set()
    ignores_faltantes = [x for x in IGNORE_LINES if x not in ignore]
    tracked = tracked or []
    leaked = [x for x in tracked if x == '.env' or (x.startswith('.env.') and x != '.env.example')
              or x.startswith(SENSITIVE_TRACKED_PREFIXES) or '.egg-info/' in x]
    return dict(estado='ok' if not (faltantes or req_faltantes or ignores_faltantes or leaked) else 'revision_requerida',
                archivos_faltantes=faltantes, dependencias_no_incluidas=req_faltantes,
                exclusiones_faltantes=ignores_faltantes, archivos_privados_versionados=leaked)


def inspect_runtime(root: Path, *, installed: set[str] | None = None) -> dict:
    root = Path(root)
    archivos = [x for x in RUNTIME_FILES if not (root / x).is_file()]
    installed = installed if installed is not None else installed_distributions()
    dependencias = [x for x in RUNTIME_DISTS if x.casefold() not in installed]
    return dict(estado='ok' if not (archivos or dependencias) else 'revision_requerida',
                archivos_locales_faltantes=archivos, distribuciones_no_instaladas=dependencias,
                nota='No valida Ollama activo, ejecución de tools, validez de fuentes ni contenido del índice')


def installed_distributions() -> set[str]:
    return {dist.metadata['Name'].casefold() for dist in metadata.distributions() if dist.metadata.get('Name')}


def tracked_files(root: Path) -> list[str] | None:
    try:
        p = subprocess.run(['git', '-C', str(root), 'ls-files', '-z'], capture_output=True, check=True, timeout=10)
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None
    return [x for x in p.stdout.decode('utf-8', 'replace').split('\x00') if x]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--modo', choices=('repo', 'ejecucion'), default='repo')
    args = parser.parse_args()
    tracked = tracked_files(ROOT)
    resultado = {'modo': args.modo, 'repositorio': inspect_repo(ROOT, tracked=tracked)}
    if tracked is None:
        resultado['advertencia_git'] = 'No se pudo ejecutar git ls-files; revisar archivos versionados manualmente'
    if args.modo == 'ejecucion':
        resultado['ejecucion'] = inspect_runtime(ROOT)
    ok = resultado['repositorio']['estado'] == 'ok' and (args.modo != 'ejecucion' or resultado['ejecucion']['estado'] == 'ok')
    resultado['estado'] = 'ok' if ok else 'revision_requerida'
    print(json.dumps(resultado, indent=2, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
