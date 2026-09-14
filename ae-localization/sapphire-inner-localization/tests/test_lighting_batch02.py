"""Batch02 guard tests. No installed binaries or AE preferences are changed."""
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import build_lighting_batch02_titles as m


class Batch02Tests(unittest.TestCase):
    def setUp(self):
        self.d = b'(def_effect Example ( Source ) ( rgba_ok ) ( a = 1 ( popup Full Half ) b = 2 ) ( compute a b ) )'
        self.t = {'a':'分辨率', 'b':'亮度'}
        p = patch.dict(m.SUPPORTED, {'Example':2})
        p.start()
        self.addCleanup(p.stop)

    def test_title_only(self):
        out, keys = m.translate(self.d, 'Example', self.t)
        self.assertEqual(keys, ['a', 'b'])
        self.assertIn(b'popup Full Half', out)
        self.assertIn(b'( compute a b )', out)
        self.assertEqual(out.count(b'title "'), 2)

    def test_missing_key(self):
        with self.assertRaises(ValueError):m.translate(self.d, 'Example', {'a':'甲'})

    def test_extra_key(self):
        with self.assertRaises(ValueError):m.translate(self.d, 'Example', dict(self.t,c='丙'))

    def test_wrong_definition(self):
        with self.assertRaises(ValueError):m.translate(self.d, 'Other', self.t)

    def test_invalid_titles(self):
        for bad in ['', ' ', '甲"乙', '甲\\乙', '甲\n乙', '甲\r乙', '甲\0乙', None, 3]:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                m.translate(self.d,'Example',dict(self.t,a=bad))

    def test_long_title(self):
        with self.assertRaises(ValueError):m.translate(self.d,'Example',dict(self.t,a='甲'*16))

    def test_unencodable(self):
        with self.assertRaises(UnicodeEncodeError):m.translate(self.d,'Example',dict(self.t,a='😀'))

    def test_existing_title(self):
        with self.assertRaises(ValueError):
            m.translate(self.d.replace(b'popup Full Half', b'popup Full Half title "old"'), 'Example', self.t)

    def test_count_mismatch(self):
        with patch.dict(m.SUPPORTED, {'Example':3}), self.assertRaises(ValueError):
            m.translate(self.d, 'Example', self.t)

    def test_deterministic(self):
        self.assertEqual(m.translate(self.d,'Example',self.t),m.translate(self.d,'Example',self.t))

    def test_candidate_coverage(self):
        mapping=json.loads((ROOT/'maps/Lighting-batch02-zh-CN.candidate.json').read_text(encoding='utf-8'))
        self.assertEqual(set(mapping['definitions']),set(m.SUPPORTED)-{'Example'})
        self.assertEqual(sum(d['parameter_count'] for d in mapping['definitions'].values()),299)
        for name,d in mapping['definitions'].items():
            self.assertEqual(len(d['parameters']),m.SUPPORTED[name])
            for t in d['parameters'].values():
                self.assertTrue(0<len(t.encode('cp936'))<=31)
                self.assertTrue(any('\u4e00'<=c<='\u9fff' for c in t))

    def test_batch01_not_mutated(self):
        import build_lighting_batch_titles as old
        self.assertEqual(sum(old.SUPPORTED.values()),289)
        self.assertNotIn('UltraGlow',old.SUPPORTED)

if __name__=='__main__':unittest.main()
