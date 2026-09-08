"""Build a Chinese Light3D entry without changing the canonical AE match name.
This command produces a new file only; deployment and removal require separate review.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path
from new_relocated_title_trial import pe_checksum

INPUT_HASHES = {
    '888BB1C868D1DE4488FABDCF33CCB320400659329DC80F16FBB463B6B8F26D4C',
    'B65193F4D46F0911D1DCBB0B56583E185D10F70B2A65A7747C1394999E6B97AA',
}
OLD_ROOT = b'c:/Program Files/BorisFX/Sapphire 2024 Adobe'


def sha(data):
    return hashlib.sha256(data).hexdigest().upper()


def property_field(data, tag):
    marker = b'MIB8' + tag
    if data.count(marker) != 1:
        raise ValueError('ambiguous PiPL property: ' + repr(tag))
    off = data.index(marker) + 4
    size = struct.unpack_from('<I', data, off + 8)[0]
    start = off + 12
    if not 1 <= size <= 256 or start + size > len(data) or data[start] >= size:
        raise ValueError('invalid Pascal string property')
    return start, size


def build(source, destination, runtime_root, display_name='S_3D灯光', category='S_蓝宝石 光照效果'):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if destination.exists() or source.parent == destination.parent:
        raise ValueError('output must be new and outside source directory')
    original = source.read_bytes()
    if sha(original) not in INPUT_HASHES:
        raise ValueError('unrecognized source hash')
    root = str(Path(runtime_root).resolve()).replace('\\', '/').encode('ascii', 'strict')
    if len(root) > len(OLD_ROOT) or b'\0' in root:
        raise ValueError('runtime root exceeds original field capacity')
    if not (Path(runtime_root) / 'lib64' / 'sapphire_ae.dll').is_file():
        raise ValueError('runtime core is absent')
    out = bytearray(original)
    match_off, match_size = property_field(original, b'ANMe')
    if original[match_off + 1:match_off + 1 + original[match_off]] != b'S_Light3D':
        raise ValueError('unexpected AE match name')
    changes = []
    for tag, value in [(b'eman', display_name), (b'gtac', category)]:
        offset, size = property_field(original, tag)
        payload = value.encode('cp936', 'strict')
        if not payload or b'\0' in payload or len(payload) + 1 > size:
            raise ValueError('display text exceeds PiPL field capacity')
        out[offset:offset + size] = (bytes([len(payload)]) + payload).ljust(size, b'\0')
        changes.append((offset, size))
    if original.count(OLD_ROOT) != 1:
        raise ValueError('ambiguous core root field')
    root_off = original.index(OLD_ROOT)
    out[root_off:root_off + len(OLD_ROOT)] = root.ljust(len(OLD_ROOT), b'\0')
    changes.append((root_off, len(OLD_ROOT)))
    pe = struct.unpack_from('<I', original, 0x3c)[0]
    if original[pe:pe + 4] != b'PE\0\0':
        raise ValueError('not PE')
    check_off = pe + 24 + 64
    struct.pack_into('<I', out, check_off, pe_checksum(out, check_off))
    changes.append((check_off, 4))
    restored = bytearray(out)
    for offset, size in changes:
        restored[offset:offset + size] = original[offset:offset + size]
    if restored != original or out[match_off:match_off + match_size] != original[match_off:match_off + match_size]:
        raise ValueError('unexpected mutation or match-name change')
    manifest = destination.with_suffix('.manifest.json')
    if manifest.exists():
        raise ValueError('manifest already exists')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('xb') as f:
        f.write(out)
    if sha(destination.read_bytes()) != sha(out):
        raise ValueError('disk hash mismatch')
    report = {'source_sha256': sha(original), 'output_sha256': sha(out), 'display_name': display_name,
              'category': category, 'encoding': 'cp936', 'match_name': 'S_Light3D', 'runtime_root': str(Path(runtime_root).resolve()),
              'static_check': 'PiPL display fields, runtime-root data and checksum only; match-name and other bytes unchanged',
              'runtime_validation': 'pending', 'old_O_projects': 'O_Light3D is a different match name; retain backup or remap test projects before retiring its entry'}
    manifest.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source', required=True)
    ap.add_argument('--output', required=True)
    ap.add_argument('--runtime-root', required=True)
    ap.add_argument('--display-name', default='S_3D灯光')
    ap.add_argument('--category', default='S_蓝宝石 光照效果')
    a = ap.parse_args()
    print(json.dumps(build(a.source, a.output, a.runtime_root, a.display_name, a.category), ensure_ascii=True))
