"""Generate a configurable diagnostic JSX without launching AE or touching plugins."""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path, PureWindowsPath
import re

TOKEN = '/*__LIGHTING_CONFIG__*/'


def validate_config(config):
    required = {'media_path', 'work_dir', 'tag', 'cases'}
    allowed = required | {'time_seconds', 'fps', 'span_frames', 'resolution_divisor'}
    if set(config) - allowed or not required <= set(config):
        raise ValueError('Missing or unknown configuration keys')
    for key in ('media_path', 'work_dir'):
        value = config[key]
        if not isinstance(value, str) or any(c in value for c in '\x00\r\n'):
            raise ValueError('Invalid path: ' + key)
        if not (Path(value).is_absolute() or PureWindowsPath(value).is_absolute()):
            raise ValueError('Absolute path required: ' + key)
    if not isinstance(config['tag'], str) or not re.fullmatch(r'[a-zA-Z0-9-]{1,60}', config['tag']):
        raise ValueError('Invalid project tag')
    cases = config['cases']
    if not isinstance(cases, list) or not cases:
        raise ValueError('At least one case is required')
    names = set()
    for case in cases:
        if not isinstance(case, dict) or set(case) != {'name', 'effects'}:
            raise ValueError('A case needs only name/effects')
        name, effects = case['name'], case['effects']
        if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,70}', name) or name in names:
            raise ValueError('Invalid or duplicate case name')
        names.add(name)
        if not isinstance(effects, list) or not effects or any(
                not isinstance(e, str) or not re.fullmatch(r'S_[A-Za-z0-9_]+', e) for e in effects):
            raise ValueError('Canonical S_ effect identities required')
    result = dict(config)
    for key, default, low, high in [('time_seconds', 1, 0, 86400), ('fps', 25, 1, 120),
                                    ('span_frames', 1, 1, 120), ('resolution_divisor', 2, 1, 16)]:
        value = config.get(key, default)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
            raise ValueError('Invalid numeric option: ' + key)
        if key != 'time_seconds' and value != int(value):
            raise ValueError('Integer option required: ' + key)
        result[key] = value
    return result


def render_probe(config):
    config = validate_config(config)
    template = Path(__file__).with_name('lighting_native_probe.jsx').read_text(encoding='utf-8')
    if template.count(TOKEN) != 1:
        raise ValueError('Template token must occur exactly once')
    return template.replace(TOKEN, json.dumps(config, ensure_ascii=True, allow_nan=False))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    args = p.parse_args()
    script = render_probe(json.loads(args.config.read_text(encoding='utf-8-sig')))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as stream:
        stream.write(script)
    print('Generated diagnostic only: ' + str(args.output))


if __name__ == '__main__':
    main()
