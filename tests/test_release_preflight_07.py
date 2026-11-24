"""Pruebas offline para preflight de publicación; sin LLM ni Ollama."""
from __future__ import annotations
from pathlib import Path
import tempfile
import unittest
from importlib.util import spec_from_file_location, module_from_spec

MODULE_FILE = Path(__file__).resolve().parents[1] / 'scripts' / 'preflight_entrega_07.py'
spec = spec_from_file_location('preflight_entrega_07', MODULE_FILE)
assert spec and spec.loader
mod = module_from_spec(spec)
spec.loader.exec_module(mod)


class TestsPreflight(unittest.TestCase):
    def fixture(self):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        for path in mod.REQUIRED_FILES:
            p = root/path
            p.parent.mkdir(parents=True, exist_ok=True)
            p.touch()
        (root/'.gitignore').write_text('\n'.join(mod.IGNORE_LINES),encoding='utf-8')
        (root/'requirements.txt').write_text('\n'.join(f'-r {x}' for x in mod.REQUIRED_INCLUDES),encoding='utf-8')
        return temp, root

    def test_repo_completo(self):
        tmp,root = self.fixture()
        with tmp:
            self.assertEqual(mod.inspect_repo(root)['estado'],'ok')

    def test_falta_readme(self):
        tmp,root = self.fixture()
        with tmp:
            (root/'README.md').unlink()
            self.assertIn('README.md',mod.inspect_repo(root)['archivos_faltantes'])

    def test_falta_requirements_incluido(self):
        tmp,root = self.fixture()
        with tmp:
            (root/'requirements.txt').write_text('-r requirements-llm.txt\n',encoding='utf-8')
            self.assertIn('requirements-ui.txt',mod.inspect_repo(root)['dependencias_no_incluidas'])

    def test_falta_gitignore_estado(self):
        tmp,root = self.fixture()
        with tmp:
            (root/'.gitignore').write_text('data/state/\n',encoding='utf-8')
            self.assertIn('data/raw/',mod.inspect_repo(root)['exclusiones_faltantes'])

    def test_git_no_debe_contener_sqlite(self):
        tmp,root = self.fixture()
        with tmp:
            item='data/state/inventario.sqlite3'
            self.assertEqual(mod.inspect_repo(root,tracked=[item])['archivos_privados_versionados'],[item])

    def test_git_no_debe_contener_env(self):
        tmp,root = self.fixture()
        with tmp:
            self.assertIn('.env',mod.inspect_repo(root,tracked=['.env'])['archivos_privados_versionados'])

    def test_no_versionar_env_local(self):
        tmp,root = self.fixture()
        with tmp:
            self.assertIn('.env.local',mod.inspect_repo(root, tracked=['.env.local'])['archivos_privados_versionados'])

    def test_runtime_falta_indice(self):
        with tempfile.TemporaryDirectory() as d:
            x = mod.inspect_runtime(Path(d),installed={v.casefold() for v in mod.RUNTIME_DISTS})
            self.assertIn('data/vectorstore/energiaai_rag_manifest.json',x['archivos_locales_faltantes'])

    def test_runtime_completo_con_dependencias(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            for f in mod.RUNTIME_FILES:
                p=root/f; p.parent.mkdir(parents=True,exist_ok=True); p.touch()
            x=mod.inspect_runtime(root,installed={v.casefold() for v in mod.RUNTIME_DISTS})
            self.assertEqual(x['estado'],'ok')

    def test_runtime_falta_pypdf(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            for f in mod.RUNTIME_FILES:
                p=root/f; p.parent.mkdir(parents=True,exist_ok=True); p.touch()
            installed={v.casefold() for v in mod.RUNTIME_DISTS if v!='pypdf'}
            self.assertIn('pypdf',mod.inspect_runtime(root,installed=installed)['distribuciones_no_instaladas'])


if __name__=='__main__':
    unittest.main()
