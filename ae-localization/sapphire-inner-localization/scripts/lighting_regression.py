"""Read-only comparison of complete diagnostic AEP snapshots and integer TIFFs."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re

BLOCK = re.compile(rb'REPAIR_BEGIN ([A-Za-z0-9_]+)\n(.*?)\nREPAIR_END \1(?![A-Za-z0-9_])', re.S)


def read_snapshots(data: bytes, expected_instances: int) -> dict[str, list[list[str]]]:
    if expected_instances < 1:
        raise ValueError('expected_instances must be positive')
    blocks = list(BLOCK.finditer(data))
    begins = re.findall(rb'REPAIR_BEGIN ([A-Za-z0-9_]+)\n', data)
    ends = re.findall(rb'REPAIR_END ([A-Za-z0-9_]+)', data)
    completed = re.findall(rb'ALL_ADDED ([0-9]+)(?![0-9])', data)
    if (b'PROBE_ERROR' in data or begins != ends or len(blocks) != expected_instances or len(begins) != expected_instances
            or len(ends) != expected_instances or not completed
            or any(int(n) != expected_instances for n in completed)):
        raise ValueError('Incomplete or unexpected diagnostic coverage')
    result = {}
    for match in blocks:
        label = match[1].decode('ascii')
        if label in result:
            raise ValueError('Duplicate instance: ' + label)
        rows = [line.decode('utf-8').split('|', 4) for line in match[2].split(b'\n')]
        if not rows or any(len(row) != 5 for row in rows):
            raise ValueError('Malformed parameter row: ' + label)
        if [row[0] for row in rows] != [str(i) for i in range(1, len(rows) + 1)]:
            raise ValueError('Noncontiguous or repeated parameter index: ' + label)
        result[label] = rows
    return result


def compare_parameters(before, after, allow_name_changes=()):
    if set(before) != set(after):
        raise ValueError('Instance identities changed')
    allowed = set(allow_name_changes)
    if not allowed <= set(before):
        raise ValueError('Unknown instance in name-change allowlist')
    rows = []
    passed = True
    for label in sorted(before):
        old, new = before[label], after[label]
        changes, errors = [], []
        if len(old) != len(new):
            errors.append('parameter_count')
        for a, b in zip(old, new):
            if a[0] != b[0] or a[2:] != b[2:]:
                errors.append('structure_or_value_at_' + a[0])
            if a[1] != b[1]:
                changes.append({'index': a[0], 'before': a[1], 'after': b[1]})
                if label not in allowed:
                    errors.append('unapproved_name_change_at_' + a[0])
        passed = passed and not errors
        rows.append({'instance': label, 'parameter_count': len(new),
                     'name_changes': changes, 'errors': errors})
    return {'passed': passed, 'instances': rows}


def compare_frames(before_dir, after_dir, expected_frames):
    import numpy as np
    from PIL import Image
    if expected_frames < 1:
        raise ValueError('expected_frames must be positive')
    def inventory(folder):
        folder = Path(folder)
        if not folder.is_dir():
            raise ValueError('Frame directory missing')
        return {p.name: p for p in folder.iterdir()
                if p.is_file() and p.suffix.lower() in ('.tif', '.tiff')}
    old, new = inventory(before_dir), inventory(after_dir)
    if set(old) != set(new) or len(old) != expected_frames:
        raise ValueError('Frame identity/count mismatch')
    rows = []
    for name in sorted(old):
        with Image.open(old[name]) as im:
            a = np.array(im)
        with Image.open(new[name]) as im:
            b = np.array(im)
        if a.shape != b.shape or a.dtype != b.dtype:
            raise ValueError('Frame shape/type mismatch: ' + name)
        if a.dtype.kind not in 'iu' or a.dtype.itemsize > 4:
            raise ValueError('Only integer TIFFs up to 32-bit supported: ' + name)
        difference = np.abs(a.astype(np.int64) - b.astype(np.int64))
        rows.append({'file': name, 'shape': list(a.shape),
                     'max_channel_difference': int(difference.max()),
                     'changed_channels': int(np.count_nonzero(difference))})
    return {'passed': all(row['changed_channels'] == 0 for row in rows), 'frames': rows}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--before-project', type=Path, required=True)
    p.add_argument('--after-project', type=Path, required=True)
    p.add_argument('--expected-instances', type=int, required=True)
    p.add_argument('--allow-name-change', action='append', default=[])
    p.add_argument('--before-frames', type=Path)
    p.add_argument('--after-frames', type=Path)
    p.add_argument('--expected-frames', type=int)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    if args.output.exists():
        p.error('Output exists; preserve prior evidence')
    frame_args = [args.before_frames, args.after_frames, args.expected_frames]
    if any(x is not None for x in frame_args) and not all(x is not None for x in frame_args):
        p.error('Frame comparison requires both directories and expected count')
    try:
        before = read_snapshots(args.before_project.read_bytes(), args.expected_instances)
        after = read_snapshots(args.after_project.read_bytes(), args.expected_instances)
        report = {'parameters': compare_parameters(before, after, args.allow_name_change),
                  'scope': 'Automated diagnostics only; not editor/manual/full-host acceptance'}
        if args.before_frames is not None:
            report['render'] = compare_frames(*frame_args)
        report['passed'] = report['parameters']['passed'] and report.get('render', {'passed': True})['passed']
    except (ValueError, OSError, UnicodeError) as error:
        report = {'passed': False, 'error': str(error)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    print(json.dumps({'passed': report['passed'], 'report': str(args.output)}))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
