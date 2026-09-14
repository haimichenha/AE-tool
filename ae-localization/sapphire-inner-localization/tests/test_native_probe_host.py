import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from prepare_lighting_probe import render_probe


@unittest.skipUnless(shutil.which('node'), 'Optional host-model test requires Node.js')
class HostModelTests(unittest.TestCase):
    def test_native_repeat_identity_and_user_takeover(self):
        config = {'media_path': 'D:/fixtures/source.mp4', 'work_dir': 'D:/validation/session', 'tag': 'test',
                  'cases': [{'name': 'Solo', 'effects': ['S_A']},
                            {'name': 'AB', 'effects': ['S_A', 'S_B']},
                            {'name': 'BA', 'effects': ['S_B', 'S_A']}]}
        with tempfile.TemporaryDirectory() as d:
            output = Path(d) / 'probe.jsx'; output.write_text(render_probe(config), encoding='utf-8')
            for scenario in ['success', 'takeover', 'wrong-effect', 'existing']:
                with self.subTest(scenario=scenario):
                    run = subprocess.run(['node', str(Path(__file__).with_name('native_probe_mock.cjs')),
                                          str(output), scenario], capture_output=True, text=True)
                    self.assertEqual(run.returncode, 0, run.stderr)
                    self.assertTrue(json.loads(run.stdout)['passed'])


if __name__ == '__main__': unittest.main()
