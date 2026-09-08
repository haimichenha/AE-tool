"""Relocate ONLY allowlisted display-string arguments to known Qt translation calls.
No global string replacement, detours, new executable code, or function imports.
"""
import argparse
import collections
import json
import re
import struct
from pathlib import Path
import pefile
from mocha_ui_catalog import BASELINE, extract, sha


def align(n, size):
    return (n + size - 1) // size * size


def placeholders(s):
    return collections.Counter(re.findall(r'%(?:L?\d+|L?n|s|d|f)', s))


def build(source, mapping_path, destination):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if source == destination or destination.exists() or destination.parent == source.parent:
        raise ValueError('output must be a new isolated file, outside source directory')
    spec = json.loads(Path(mapping_path).read_text(encoding='utf-8-sig'))
    if spec['source_sha256'] != BASELINE:
        raise ValueError('mapping baseline mismatch')
    catalog = extract(source)
    original = source.read_bytes()
    if sha(original) != BASELINE:
        raise ValueError('source changed during scan')
    pe = pefile.PE(data=original)
    entries = {}
    for entry in spec['translations']:
        key = (entry['context'], entry['source'])
        if key in entries:
            raise ValueError(f'duplicate key: {key}')
        target = entry['translation']
        if not target or '\0' in target or placeholders(entry['source']) != placeholders(target):
            raise ValueError(f'invalid translation/placeholders: {key}')
        entries[key] = entry
    by_key = collections.defaultdict(list)
    for s in catalog['sites']:
        by_key[(s['context'], s['source'])].append(s)
    missing = set(entries) - set(by_key)
    if missing:
        raise ValueError(f'mapping has unknown keys: {sorted(missing)}')
    ns = pe.FILE_HEADER.NumberOfSections
    header = pe.sections[-1].get_file_offset() + 40
    if header + 40 > min(s.PointerToRawData for s in pe.sections):
        raise ValueError('no section header capacity')
    if any(original[header:header + 40]):
        raise ValueError('new section header is not unused')
    va = align(max(s.VirtualAddress + max(s.Misc_VirtualSize, s.SizeOfRawData) for s in pe.sections), pe.OPTIONAL_HEADER.SectionAlignment)
    raw = align(len(original), pe.OPTIONAL_HEADER.FileAlignment)
    pool, offsets, edits = bytearray(), {}, []
    for key, entry in entries.items():
        target = entry['translation'].encode('utf-8') + b'\0'
        if target not in offsets:
            offsets[target] = len(pool)
            pool.extend(target)
        for site in by_key[key]:
            off = site['lea_offset']
            pre = bytes.fromhex(site['preimage_hex'])
            if original[off:off + 7] != pre or pre[:3] != b'\x4c\x8d\x05':
                raise ValueError('LEA preimage mismatch')
            disp = va + offsets[target] - (site['lea_rva'] + 7)
            post = pre[:3] + struct.pack('<i', disp)
            edits.append({**site, 'translation': entry['translation'], 'postimage_hex': post.hex().upper()})
    if not edits:
        raise ValueError('empty patch')
    size = align(len(pool), pe.OPTIONAL_HEADER.FileAlignment)
    out = bytearray(original)
    out.extend(b'\0' * (raw + size - len(out)))
    out[raw:raw + len(pool)] = pool
    out[header:header + 40] = struct.pack('<8sIIIIIIHHI', b'.mcn\0\0\0\0', len(pool), va, size, raw, 0, 0, 0, 0, 0x40000040)
    struct.pack_into('<H', out, pe.FILE_HEADER.get_field_absolute_offset('NumberOfSections'), ns + 1)
    struct.pack_into('<I', out, pe.OPTIONAL_HEADER.get_field_absolute_offset('SizeOfImage'), align(va + len(pool), pe.OPTIONAL_HEADER.SectionAlignment))
    struct.pack_into('<I', out, pe.OPTIONAL_HEADER.get_field_absolute_offset('SizeOfInitializedData'), pe.OPTIONAL_HEADER.SizeOfInitializedData + size)
    for e in edits:
        off = e['lea_offset']
        out[off:off + 7] = bytes.fromhex(e['postimage_hex'])
    fixed_edits = []
    for e in spec.get('legacy_fixed', []):
        off = e['offset']; before = e['source'].encode('ascii') + b'\0'; after = e['translation'].encode('utf-8') + b'\0'
        section = pe.get_section_by_offset(off)
        if section is None or section.Name.rstrip(b'\0') != b'.rdata' or len(after) > len(before):
            raise ValueError('legacy fixed patch not within read-only string capacity')
        if original[off:off + len(before)] != before or out[off:off + len(before)] != before:
            raise ValueError('legacy preimage or overlap mismatch')
        out[off:off + len(before)] = after.ljust(len(before), b'\0')
        fixed_edits.append(e)
    checkoff = pe.OPTIONAL_HEADER.get_field_absolute_offset('CheckSum')
    struct.pack_into('<I', out, checkoff, 0)
    patched = pefile.PE(data=bytes(out))
    struct.pack_into('<I', out, checkoff, patched.generate_checksum())
    # Reverse every allowed mutation to prove no unrelated pre-existing bytes changed.
    restored = bytearray(out[:len(original)])
    restored[header:header + 40] = original[header:header + 40]
    for obj, name, width in [(pe.FILE_HEADER, 'NumberOfSections', 2), (pe.OPTIONAL_HEADER, 'SizeOfImage', 4),
                             (pe.OPTIONAL_HEADER, 'SizeOfInitializedData', 4), (pe.OPTIONAL_HEADER, 'CheckSum', 4)]:
        offset = obj.get_field_absolute_offset(name)
        restored[offset:offset + width] = original[offset:offset + width]
    for e in edits:
        off = e['lea_offset']
        restored[off:off + 7] = bytes.fromhex(e['preimage_hex'])
        loc = e['lea_rva'] + 7 + struct.unpack_from('<i', out, off + 3)[0] - va + raw
        expected = e['translation'].encode('utf-8') + b'\0'
        if out[loc:loc + len(expected)] != expected:
            raise ValueError('redirected string postimage mismatch')
        co = pe.get_offset_from_rva(e['call_rva'])
        if out[co:co + 5] != original[co:co + 5]:
            raise ValueError('translation call instruction changed')
    for e in fixed_edits:
        off = e['offset']; length = len(e['source'].encode('ascii')) + 1
        restored[off:off + length] = original[off:off + length]
    if restored != original:
        raise ValueError('unallowlisted byte change')
    destination.parent.mkdir(parents=True, exist_ok=True)
    manifest_path = destination.with_suffix('.manifest.json')
    if manifest_path.exists():
        raise ValueError('refusing manifest overwrite')
    with destination.open('xb') as f:
        f.write(out)
    if sha(destination.read_bytes()) != sha(out):
        raise ValueError('disk verification failed')
    report = {'source_sha256': BASELINE, 'output_sha256': sha(out), 'mapping_sha256': sha(Path(mapping_path).read_bytes()),
              'translated_keys': len(entries), 'patched_call_sites': len(edits), 'known_direct_sites': catalog['site_count'],
              'legacy_fixed': fixed_edits, 'static_validation': 'only allowlisted LEA displacement operands, one retained fixed UI string, and PE metadata changed; call targets preserved',
              'runtime_validation': 'pending', 'all_ui_translated': False, 'sites': edits}
    manifest_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return {k: v for k, v in report.items() if k != 'sites'}


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source', required=True)
    ap.add_argument('--mapping', required=True)
    ap.add_argument('--output', required=True)
    args = ap.parse_args()
    print(json.dumps(build(args.source, args.mapping, args.output), ensure_ascii=False))
