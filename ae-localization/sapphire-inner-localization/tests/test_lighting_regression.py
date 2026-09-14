import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from lighting_regression import read_snapshots, compare_parameters, compare_frames


def snapshot(label='Solo__1__S_GlowDist', name='Brightness', value='1'):
    return (f'REPAIR_BEGIN {label}\n1|{name}|S_GlowDist-1|6212|{value}\n'
            f'2|Hidden|S_GlowDist-2|6212|SKIPPED\nREPAIR_END {label}\x00ALL_ADDED 1\x00').encode('utf-8')


class ParameterTests(unittest.TestCase):
    def test_unicode_name_change_requires_explicit_instance(self):
        a, b = read_snapshots(snapshot(), 1), read_snapshots(snapshot(name='亮度'), 1)
        self.assertFalse(compare_parameters(a, b)['passed'])
        self.assertTrue(compare_parameters(a, b, a.keys())['passed'])

    def test_value_or_identity_changes_cannot_be_allowed_as_names(self):
        a, b = read_snapshots(snapshot(), 1), read_snapshots(snapshot(name='亮度', value='2'), 1)
        self.assertFalse(compare_parameters(a, b, a.keys())['passed'])
        b = read_snapshots(snapshot().replace(b'S_GlowDist-1', b'S_Other-1'), 1)
        self.assertFalse(compare_parameters(a, b, a.keys())['passed'])

    def test_incomplete_duplicate_and_malformed_snapshots(self):
        bad = [snapshot().replace(b'ALL_ADDED', b'WAITING'), snapshot().replace(b'REPAIR_END', b'NO_END'),
               snapshot().replace(b'\n2|', b'\n3|'), snapshot().replace(b'REPAIR_END Solo__1__S_GlowDist', b'REPAIR_END Solo__1__S_GlowDistX'),
               snapshot() + b'PROBE_ERROR close failed', snapshot().replace(b'|6212|1', b'|1')]
        for data in bad:
            with self.subTest(data=data), self.assertRaises(ValueError):
                read_snapshots(data, 1)
        with self.assertRaises(ValueError):
            read_snapshots((snapshot() + snapshot()).replace(b'ALL_ADDED 1', b'ALL_ADDED 2'), 2)

    def test_allowlist_typo_and_count_mismatch(self):
        a = read_snapshots(snapshot(), 1)
        with self.assertRaises(ValueError):
            compare_parameters(a, a, ['unknown'])
        with self.assertRaises(ValueError):
            read_snapshots(snapshot(), 2)

    def test_cli_preserves_failure_report_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d); (d / 'a.aep').write_bytes(snapshot()); (d / 'b.aep').write_bytes(snapshot(value='2'))
            cmd = [sys.executable, str(ROOT / 'scripts/lighting_regression.py'), '--before-project', str(d / 'a.aep'),
                   '--after-project', str(d / 'b.aep'), '--expected-instances', '1', '--output', str(d / 'result.json')]
            r = subprocess.run(cmd, capture_output=True)
            self.assertEqual(r.returncode, 1)
            self.assertFalse(json.loads((d / 'result.json').read_text())['passed'])
            saved = (d / 'result.json').read_bytes()
            self.assertNotEqual(subprocess.run(cmd, capture_output=True).returncode, 0)
            self.assertEqual(saved, (d / 'result.json').read_bytes())


class FrameTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.before, self.after = Path(self.tmp.name) / 'before', Path(self.tmp.name) / 'after'
        self.before.mkdir(); self.after.mkdir()

    def save(self, folder, name='frame.tif', pixel=1, size=(2, 2)):
        from PIL import Image
        Image.new('RGB', size, (pixel, pixel, pixel)).save(folder / name)

    def test_exact_and_one_level_difference(self):
        self.save(self.before); self.save(self.after)
        self.assertTrue(compare_frames(self.before, self.after, 1)['passed'])
        self.save(self.after, pixel=2)
        result = compare_frames(self.before, self.after, 1)
        self.assertFalse(result['passed'])
        self.assertEqual(result['frames'][0]['max_channel_difference'], 1)

    def test_missing_extra_shape_and_float_rejected(self):
        self.save(self.before)
        with self.assertRaises(ValueError): compare_frames(self.before, self.after, 1)
        self.save(self.after, size=(3, 2))
        with self.assertRaises(ValueError): compare_frames(self.before, self.after, 1)
        self.save(self.after); self.save(self.after, name='extra.tif')
        with self.assertRaises(ValueError): compare_frames(self.before, self.after, 1)
        (self.after / 'extra.tif').unlink()
        from PIL import Image
        Image.new('F', (2, 2), 1.0).save(self.before / 'frame.tif')
        Image.new('F', (2, 2), 1.0).save(self.after / 'frame.tif')
        with self.assertRaises(ValueError): compare_frames(self.before, self.after, 1)


if __name__ == '__main__': unittest.main()
