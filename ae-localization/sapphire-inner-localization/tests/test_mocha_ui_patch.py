import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
from mocha_ui_catalog import BASELINE, extract
from build_mocha_ui_relocated import build, placeholders


class Safeguards(unittest.TestCase):
    def test_placeholders_multiplicity(self):
        self.assertEqual(placeholders('%1 %2 %1 %n %L3'), placeholders('%n %1 %L3 %1 %2'))
        self.assertNotEqual(placeholders('%1 %1'), placeholders('%1'))

    def test_wrong_baseline_cannot_write(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / 'wrong.dll'
            source.write_bytes(b'not a supported PE image')
            with self.assertRaisesRegex(ValueError, 'unsupported baseline'):
                extract(source)

    def test_existing_output_untouched(self):
        with tempfile.TemporaryDirectory() as td:
            output = Path(td) / 'keep.dll'
            output.write_bytes(b'keep')
            with self.assertRaises(ValueError):
                build(Path(td) / 'source.dll', 'unused', output)
            self.assertEqual(output.read_bytes(), b'keep')

    def test_source_directory_guard(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(ValueError, 'isolated'):
                build(Path(td) / 'source.dll', 'unused', Path(td) / 'new.dll')

    def test_all_mapping_placeholders_and_mnemonics(self):
        mapping = Path(__file__).resolve().parents[1] / 'maps' / 'Mocha-context-menu-zh-CN.json'
        m = json.loads(mapping.read_text(encoding='utf-8'))
        keys = set()
        for e in m['translations']:
            self.assertEqual(placeholders(e['source']), placeholders(e['translation']), e['source'])
            self.assertNotIn('\0', e['translation'])
            key = (e['context'], e['source'])
            self.assertNotIn(key, keys)
            keys.add(key)
        self.assertIn(('frmMain', '&File'), keys)
        self.assertIn(('ViewControls', 'Selected track mattes'), keys)
        self.assertIn(('GUI::LayoutManager', 'Manage custom layouts...'), keys)
        self.assertIn(('LayerControls', 'Lock/Unlock All'), keys)


if __name__ == '__main__':
    unittest.main()
