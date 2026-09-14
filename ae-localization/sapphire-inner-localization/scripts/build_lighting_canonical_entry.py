"""Build one pinned canonical AEX in staging; never install it or rename matchName."""
from pathlib import Path, PureWindowsPath
import argparse
import hashlib
import json
import struct
import pefile

PINS = json.loads((Path(__file__).resolve().parents[1] / 'maps/Lighting-canonical-entries.pins.json').read_text(encoding='utf-8'))
OLD_ROOT = b'c:/Program Files/BorisFX/Sapphire 2024 Adobe'
sha = lambda data: hashlib.sha256(data).hexdigest().upper()


def require(condition, message):
    if not condition: raise ValueError(message)


def pipl(data):
    pe = pefile.PE(data=bytes(data), fast_load=True); pe.parse_data_directories(directories=[2])
    types = [e for e in pe.DIRECTORY_ENTRY_RESOURCE.entries if str(e.name).upper() == 'PIPL']
    require(len(types) == 1 and len(types[0].directory.entries) == 1, 'Ambiguous PiPL')
    langs = types[0].directory.entries[0].directory.entries
    require(len(langs) == 1, 'Ambiguous PiPL language')
    record = langs[0].data.struct
    return pe.get_data(record.OffsetToData, record.Size)


def field(data, tag):
    key = b'MIB8' + tag; require(data.count(key) == 1, 'Ambiguous PiPL field')
    at = data.index(key) + 16
    require(at < len(data) and at + 1 + data[at] <= len(data), 'Invalid PiPL string length')
    return data[at + 1:at + 1 + data[at]].decode('cp936')


def build(source, output, runtime_root, effect):
    source, output = Path(source).resolve(), Path(output).resolve()
    require(effect in PINS, 'Unsupported canonical effect')
    require(not output.exists() and not output.with_suffix('.manifest.json').exists(), 'Output exists')
    require(source.parent not in output.parents, 'Use a separate staging directory')
    root = PureWindowsPath(runtime_root)
    require(root.is_absolute() and '..' not in root.parts, 'Absolute local runtime root required')
    require(not str(root).startswith('\\\\'), 'Network runtime paths are not supported')
    try: new_root = root.as_posix().encode('ascii')
    except UnicodeEncodeError as e: raise ValueError('Use a short ASCII runtime path') from e
    require(len(new_root) <= len(OLD_ROOT), 'Runtime root does not fit pinned field')
    before = source.read_bytes(); require(sha(before) == PINS[effect]['source_sha256'], 'Unsupported AEX source version')
    original_pipl = pipl(before); require(field(original_pipl, b'ANMe') == effect, 'Wrong internal identity')
    require(before.count(OLD_ROOT) == 1, 'Unexpected root literal')
    pe = pefile.PE(data=before, fast_load=True); check = pe.OPTIONAL_HEADER.get_field_absolute_offset('CheckSum')
    offset = before.index(OLD_ROOT); after = bytearray(before)
    after[offset:offset + len(OLD_ROOT)] = new_root.ljust(len(OLD_ROOT), b'\0')
    struct.pack_into('<I', after, check, 0)
    struct.pack_into('<I', after, check, pefile.PE(data=bytes(after), fast_load=True).generate_checksum())
    restored = bytearray(after); restored[offset:offset + len(OLD_ROOT)] = before[offset:offset + len(OLD_ROOT)]
    restored[check:check + 4] = before[check:check + 4]
    require(restored == before and pipl(after) == original_pipl, 'Unexpected entry changes')
    for section in pe.sections:
        if section.Characteristics & 0x20000000:
            start, size = section.PointerToRawData, section.SizeOfRawData
            require(after[start:start + size] == before[start:start + size], 'Executable section changed')
    require(pefile.PE(data=bytes(after), fast_load=True).verify_checksum(), 'Checksum readback failed')
    report = {'effect': effect, 'display_name': field(original_pipl, b'eman'), 'source_sha256': sha(before),
              'output_sha256': sha(after), 'runtime_root': root.as_posix(), 'pipl_preserved': True,
              'executable_sections_preserved': True, 'allowed_ranges': [[offset, len(OLD_ROOT)], [check, 4]],
              'installed': False, 'runtime_validation': 'pending; validate the actual core and its consumers before installation'}
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('xb') as stream: stream.write(after)
    with output.with_suffix('.manifest.json').open('x', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True); parser.add_argument('--output', required=True)
    parser.add_argument('--runtime-root', required=True); parser.add_argument('--effect', required=True, choices=PINS)
    args = parser.parse_args()
    print(json.dumps(build(args.source, args.output, args.runtime_root, args.effect), ensure_ascii=False))
