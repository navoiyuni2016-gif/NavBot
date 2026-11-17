"""Reproduce Windows CP1251 default while loading UTF-8 application data."""
import importlib.util
import sys
from pathlib import Path
import unittest
from unittest.mock import patch

APP = Path(__file__).resolve().parents[1] / 'navbot' / 'app.py'


class EncodingTest(unittest.TestCase):
    def test_catalog_loads_with_windows_default_encoding(self):
        original = Path.read_text

        def windows_read_text(path, encoding=None, errors=None):
            return original(path, encoding=encoding or 'cp1251', errors=errors)

        spec = importlib.util.spec_from_file_location('encoding_app', APP)
        module = importlib.util.module_from_spec(spec)
        with patch.object(sys, 'path', [str(APP.parent), *sys.path]), patch.object(Path, 'read_text', windows_read_text):
            spec.loader.exec_module(module)
        self.assertEqual(module.CATALOG[0][0][1], 'Академические вопросы')
        self.assertEqual(module.CATALOG[0][0][2], 'Academic services')


if __name__ == '__main__':
    unittest.main()
