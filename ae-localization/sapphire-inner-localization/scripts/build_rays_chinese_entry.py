"""Build formal S_Rays: preserve every PiPL property, change only core root/checksum.
The supported source already has the Chinese display name S_射线.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path
from build_light3d_chinese_entry import property_field
from new_relocated_title_trial import pe_checksum

SOURCE_SHA = '7040173BBD4D2C15AA42E4CB97E6246A0131AB3B651140F51CE29F701D481274'
CORE_SHA = '54DB5D9C542AE758C0E9F3803FBA60F830A6B572B5DF1B439605EE2DF8B71BBE'
OLD_ROOT = b'c:/Program Files/BorisFX/Sapphire 2024 Adobe'

def sha(data):
    return hashlib.sha256(data).hexdigest().upper()

def build(source, output, runtime):
    source, output, runtime = map(lambda p: Path(p).resolve(), (source, output, runtime))
    manifest = output.with_suffix('.manifest.json')
    if output.exists() or manifest.exists() or source.parent == output.parent:
        raise ValueError('new isolated output and manifest required')
    original = source.read_bytes()
    if sha(original) != SOURCE_SHA:
        raise ValueError('unsupported Rays entry baseline')
    if sha((runtime / 'lib64/sapphire_ae.dll').read_bytes()) != CORE_SHA:
        raise ValueError('unsupported localized Rays core')
    for tag, expected in [(b'eman', 'S_射线'.encode('cp936')), (b'ANMe', b'S_Rays')]:
        p, n = property_field(original, tag)
        if original[p + 1:p + 1 + original[p]] != expected:
            raise ValueError('unexpected display or match name')
    root = str(runtime).replace('\\', '/').encode('ascii', 'strict')
    if len(root) > len(OLD_ROOT) or original.count(OLD_ROOT) != 1:
        raise ValueError('root capacity or uniqueness failure')
    offset = original.index(OLD_ROOT)
    out = bytearray(original)
    out[offset:offset + len(OLD_ROOT)] = root.ljust(len(OLD_ROOT), b'\0')
    pe = struct.unpack_from('<I', original, 0x3c)[0]
    if original[pe:pe + 4] != b'PE\0\0':
        raise ValueError('not PE')
    check = pe + 24 + 64
    struct.pack_into('<I', out, check, pe_checksum(out, check))
    restored = bytearray(out)
    for p, size in [(offset, len(OLD_ROOT)), (check, 4)]:
        restored[p:p + size] = original[p:p + size]
    if restored != original:
        raise ValueError('unexpected mutation')
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('xb') as f:
        f.write(out)
    report = dict(source_sha256=SOURCE_SHA, output_sha256=sha(out), core_sha256=CORE_SHA,
                  display_name='S_射线', match_name='S_Rays', runtime_root=str(runtime),
                  static_check='only core-root data and PE checksum changed; all PiPL properties and machine code preserved',
                  runtime_validation='pending formal-entry restart/old-project verification')
    manifest.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return report

if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ('source', 'output', 'runtime'):
        ap.add_argument('--' + name, required=True)
    args = ap.parse_args()
    print(json.dumps(build(args.source, args.output, args.runtime), ensure_ascii=True))
