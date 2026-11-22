"""Pruebas unitarias de la validación del entorno de EnergiaAI."""

import unittest

from scripts.check_environment import validate_configuration


class ValidateConfigurationTests(unittest.TestCase):
    def test_version_y_entorno_correctos(self) -> None:
        problems = validate_configuration((3, 12), virtual_env_active=True)
        self.assertEqual(problems, [])

    def test_python_incorrecto(self) -> None:
        problems = validate_configuration((3, 11), virtual_env_active=True)
        self.assertTrue(any("Python 3.12" in problem for problem in problems))

    def test_entorno_virtual_inactivo(self) -> None:
        problems = validate_configuration((3, 12), virtual_env_active=False)
        self.assertTrue(any(".venv" in problem for problem in problems))

    def test_ambos_problemas(self) -> None:
        problems = validate_configuration((3, 13), virtual_env_active=False)
        self.assertEqual(len(problems), 2)


if __name__ == "__main__":
    unittest.main()
