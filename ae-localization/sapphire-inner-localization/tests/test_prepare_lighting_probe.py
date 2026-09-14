import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from prepare_lighting_probe import validate_config, render_probe, TOKEN


class ProbeTests(unittest.TestCase):
    def config(self):
        return {'media_path': 'D:/fixtures/测试".mp4', 'work_dir': 'D:/validation/test', 'tag': 'before',
                'cases': [{'name': 'AB', 'effects': ['S_LightLeak', 'S_LensFlare']}]}

    def test_encoded_config_and_stable_instance_counts(self):
        cfg = self.config(); generated = render_probe(cfg)
        encoded = generated.split('var cfg = ', 1)[1].split(';', 1)[0]
        decoded = json.loads(encoded)
        self.assertEqual(decoded, validate_config(cfg))
        self.assertNotIn(TOKEN, generated)
        self.assertEqual(sum(len(c['effects']) for c in decoded['cases']), 2)

    def test_duplicate_effect_supported_but_case_identity_unique(self):
        cfg = self.config(); cfg['cases'][0]['effects'] = ['S_LightLeak', 'S_LightLeak']
        self.assertEqual(len(validate_config(cfg)['cases'][0]['effects']), 2)
        cfg['cases'].append(copy.deepcopy(cfg['cases'][0]))
        with self.assertRaises(ValueError): validate_config(cfg)

    def test_reject_bad_scope_paths_and_numeric_options(self):
        for key, value in [('tag', '../overwrite'), ('fps', float('nan')), ('span_frames', 1.5),
                           ('resolution_divisor', True), ('media_path', 'relative.mp4'), ('work_dir', 'D:/x\x00y')]:
            cfg = self.config(); cfg[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError): validate_config(cfg)
        cfg = self.config(); cfg['cases'][0]['effects'] = ['R_LensFlare']
        with self.assertRaises(ValueError): validate_config(cfg)
        cfg = self.config(); cfg['install'] = True
        with self.assertRaises(ValueError): validate_config(cfg)

    def test_generator_refuses_existing_output(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d); (d / 'config.json').write_text(json.dumps(self.config()), encoding='utf-8')
            (d / 'out.jsx').write_text('keep', encoding='utf-8')
            r = subprocess.run([sys.executable, str(ROOT / 'scripts/prepare_lighting_probe.py'),
                                '--config', str(d / 'config.json'), '--output', str(d / 'out.jsx')], capture_output=True)
            self.assertNotEqual(r.returncode, 0)
            self.assertEqual((d / 'out.jsx').read_text(), 'keep')


if __name__ == '__main__': unittest.main()
