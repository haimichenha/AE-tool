"""Guard absent subprocess startup-argument lists; retain original nonempty-list protocol.

The two user dumps retain AV records at core RVA 0x3BBF80, RAX=0,
and the preset-browser communication object's args/values pointers both zero.
Hook only register initialization before the dereference. No rendering, license,
dialog-selection, command execution, or handshake success checks are skipped.
"""
from pathlib import Path
import argparse, hashlib, json, struct
import pefile
PINS = {'rays09': '54DB5D9C542AE758C0E9F3803FBA60F830A6B572B5DF1B439605EE2DF8B71BBE', 'rem16': '2852350705D672CF49DABC17DF75D77ACC1DE39610B3C9BBA389244E0D315C12', 'lights01': '3BEE617AE8B3566A1E2C70F8250CFDC6571A9035D4A0E9B91FF37C1E30A60019', 'glare01': 'D5AB45A84E7BE8705FD9269EE0C702F2741A0D9B42B02F064C2719475F8533BE', 'l3dao': '410C69A61BEC964322550ECC8662D60E454C1984175E2850B4244B02C31A7B91'}
HOOK = 3915641
RESUME = 3915648
EMPTY = 3915703
ORIGINAL = bytes.fromhex('bf0100000033f6')
sha = lambda b: hashlib.sha256(b).hexdigest().upper()

def align(x, n):
    return (x + n - 1) // n * n

def branch(op, site, target):
    return op + struct.pack('<i', target - (site + len(op) + 4))

def _require(condition, message):
    if not condition:
        raise ValueError(message)

def guard_code(rva):
    body = ORIGINAL + bytes.fromhex('4885c0')
    body += branch(b'\x0f\x84', rva + len(body), EMPTY)
    body += branch(b'\xe9', rva + len(body), RESUME)
    return body

def build(source, output, version):
    source = Path(source)
    output = Path(output)
    _require(version in PINS, 'Unknown core version')
    _require(not output.exists() and not output.with_suffix('.guard.json').exists(), 'Output or report already exists')
    b = source.read_bytes()
    _require(sha(b) == PINS[version], 'Unsupported core version')
    pe = pefile.PE(data=b, fast_load=True)
    opt = pe.OPTIONAL_HEADER
    site = pe.get_offset_from_rva(HOOK)
    _require(b[site:site + 7] == ORIGINAL, 'Guard invariant failed')
    _require(pe.get_data(RESUME, 6) == bytes.fromhex('488338007431'), 'Expected null-terminated list loop changed')
    _require(pe.get_data(EMPTY, 7) == bytes.fromhex('488d15e2a53901'), 'Expected end-of-args protocol path changed')
    header = pe.sections[-1].get_file_offset() + 40
    _require(header + 40 <= opt.SizeOfHeaders and (not any(b[header:header + 40])), 'No spare section header')
    va = align(max((s.VirtualAddress + max(s.Misc_VirtualSize, s.SizeOfRawData) for s in pe.sections)), opt.SectionAlignment)
    raw = align(len(b), opt.FileAlignment)
    body = guard_code(va)
    size = align(len(body), opt.FileAlignment)
    out = bytearray(b)
    out.extend(b'\x00' * (raw + size - len(out)))
    out[raw:raw + len(body)] = body
    out[site:site + 7] = branch(b'\xe9', HOOK, va) + b'\x90\x90'
    out[header:header + 40] = struct.pack('<8sIIIIIIHHI', b'.spng\x00\x00\x00', len(body), va, size, raw, 0, 0, 0, 0, 1610612768)
    ns = pe.FILE_HEADER.get_field_absolute_offset('NumberOfSections')
    sc = opt.get_field_absolute_offset('SizeOfCode')
    si = opt.get_field_absolute_offset('SizeOfImage')
    ck = opt.get_field_absolute_offset('CheckSum')
    struct.pack_into('<H', out, ns, pe.FILE_HEADER.NumberOfSections + 1)
    struct.pack_into('<I', out, sc, opt.SizeOfCode + size)
    struct.pack_into('<I', out, si, align(va + len(body), opt.SectionAlignment))
    struct.pack_into('<I', out, ck, 0)
    struct.pack_into('<I', out, ck, pefile.PE(data=bytes(out), fast_load=True).generate_checksum())
    allowed = [(site, 7), (header, 40), (ns, 2), (sc, 4), (si, 4), (ck, 4)]
    restored = bytearray(out[:len(b)])
    for pos, n in allowed:
        restored[pos:pos + n] = b[pos:pos + n]
    _require(restored == b, 'Unexpected original-byte change')
    test = pefile.PE(data=bytes(out), fast_load=True)
    _require(test.verify_checksum(), 'Guard invariant failed')
    _require(test.get_data(RESUME, 6) == pe.get_data(RESUME, 6), 'Guard invariant failed')
    _require(test.get_data(EMPTY, 64) == pe.get_data(EMPTY, 64), 'Guard invariant failed')
    _require(HOOK + 5 + struct.unpack_from('<i', out, site + 1)[0] == va, 'Guard invariant failed')
    _require(va + 16 + struct.unpack_from('<i', body, 12)[0] == EMPTY, 'Guard invariant failed')
    _require(va + 21 + struct.unpack_from('<i', body, 17)[0] == RESUME, 'Guard invariant failed')
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('xb') as stream:
        stream.write(out)
    report = {'source_sha256': sha(b), 'output_sha256': sha(out), 'version': version, 'hook_rva': hex(HOOK), 'thunk_rva': hex(va), 'thunk_hex': body.hex(), 'null_list_target': hex(EMPTY), 'nonnull_target': hex(RESUME), 'allowed_original_byte_ranges': allowed, 'behavior': 'null args => same end-of-args path as an empty terminated list; nonnull args => original loop unchanged', 'registers_replayed': ['EDI=1', 'ESI=0'], 'no_stack_changes': True, 'runtime_acceptance': 'pending'}
    output.with_suffix('.guard.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return report
if __name__ == '__main__':
    a = argparse.ArgumentParser()
    a.add_argument('--source', required=True)
    a.add_argument('--output', required=True)
    a.add_argument('--version', required=True, choices=PINS)
    x = a.parse_args()
    print(json.dumps(build(x.source, x.output, x.version)))
