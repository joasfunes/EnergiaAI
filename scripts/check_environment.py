"""Comprobaciones básicas del entorno de desarrollo de EnergiaAI.

Uso en Windows (PowerShell, desde la raíz del repositorio):
    .venv/Scripts/python.exe scripts/check_environment.py
"""

from __future__ import annotations

import platform
import sys
from pathlib import Path


def validate_configuration(
    version: tuple[int, int], *, virtual_env_active: bool
) -> list[str]:
    """Devuelve problemas del entorno; lista vacía significa validación exitosa."""
    problems: list[str] = []

    if version != (3, 12):
        problems.append("Se necesita Python 3.12 para este proyecto.")
    if not virtual_env_active:
        problems.append("Ejecuta el Python del entorno virtual .venv.")

    return problems


def main() -> int:
    """Muestra información del entorno y devuelve 0 si cumple los requisitos."""
    version = sys.version_info[:2]
    is_venv = sys.prefix != sys.base_prefix
    project_root = Path(__file__).resolve().parents[1]

    print("=" * 52)
    print("EnergiaAI - Diagnóstico de la Etapa 01")
    print("=" * 52)
    print(f"Sistema operativo : {platform.system()}")
    print(f"Versión de Python : {platform.python_version()}")
    print(f"Intérprete        : {sys.executable}")
    print(f"Entorno virtual   : {'Sí' if is_venv else 'No'}")
    print(f"Proyecto          : {project_root}")

    problems = validate_configuration(version, virtual_env_active=is_venv)
    if problems:
        print("\nEstado: REVISAR")
        for problem in problems:
            print(f" - {problem}")
        return 1

    print("\nEstado: CORRECTO. Podemos continuar con el desarrollo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
