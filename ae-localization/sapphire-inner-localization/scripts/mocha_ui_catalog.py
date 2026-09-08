"""Version-locked, read-only discovery of direct Qt translation call sites.
Only known translation sinks are accepted. This is not a complete runtime menu tree.
"""
import argparse
import bisect
import hashlib
import json
import re
import struct
from pathlib import Path
import capstone
import pefile

BASELINE = '969E1724C74FB4A661043E626FE92E8C29F062038C8D1BF647C99051F23DC029'
SINKS = {0x25B78B0: 'translate', 0x25DD700: 'meta_translate'}


def sha(data):
    return hashlib.sha256(data).hexdigest().upper()


def extract(source):
    data = Path(source).read_bytes()
    if sha(data) != BASELINE:
        raise ValueError('unsupported baseline; refusing offset reuse')
    pe = pefile.PE(data=data)
    base = pe.OPTIONAL_HEADER.ImageBase
    text = next(s for s in pe.sections if s.Name.rstrip(b'\0') == b'.text')
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
    md.detail = True
    directory = pe.OPTIONAL_HEADER.DATA_DIRECTORY[3]
    pdata = pe.get_data(directory.VirtualAddress, directory.Size)
    functions = sorted((a, b) for a, b, _ in struct.iter_unpack("<III", pdata) if a < b and text.VirtualAddress <= a < text.VirtualAddress + text.Misc_VirtualSize)
    starts = [f[0] for f in functions]
    boundaries = {}

    def string_at(rva):
        try:
            offset = pe.get_offset_from_rva(rva)
            end = data.find(b'\0', offset, offset + 4096)
            if end < 0:
                return None
            value = data[offset:end].decode('utf-8')
            return value if value and all(ord(c) >= 32 or c in '\n\r\t' for c in value) else None
        except (ValueError, UnicodeError, pefile.PEFormatError):
            return None

    def is_boundary(rva):
        idx = bisect.bisect_right(starts, rva) - 1
        if idx < 0 or rva >= functions[idx][1]:
            return False
        begin, end = functions[idx]
        if begin not in boundaries:
            offset = pe.get_offset_from_rva(begin)
            boundaries[begin] = {a - base for a, _, _, _ in md.disasm_lite(data[offset:offset + end - begin], base + begin)}
        return rva in boundaries[begin]

    records = []
    for match in re.finditer(rb'\x4c\x8d\x05', text.get_data()):
        offset = text.PointerToRawData + match.start()
        rva = text.VirtualAddress + match.start()
        target = rva + 7 + struct.unpack_from('<i', data, offset + 3)[0]
        source_text = string_at(target)
        if not source_text:
            continue
        context_rva = meta_rva = None
        sink = None
        for ins in md.disasm(data[offset + 7:offset + 55], base + rva + 7):
            if ins.mnemonic == 'call':
                if ins.operands[0].type == capstone.x86.X86_OP_IMM:
                    sink = ins.operands[0].imm - base
                break
            if ins.group(capstone.CS_GRP_JUMP) or ins.group(capstone.CS_GRP_RET):
                break
            _, writes = ins.regs_access()
            if any(ins.reg_name(w) in ('r8', 'r8d', 'r8w', 'r8b') for w in writes):
                break
            if ins.mnemonic == 'lea' and len(ins.operands) == 2:
                dst, src = ins.operands
                if src.type == capstone.x86.X86_OP_MEM and src.mem.base == capstone.x86.X86_REG_RIP:
                    ref = ins.address - base + ins.size + src.mem.disp
                    if dst.reg == capstone.x86.X86_REG_RDX:
                        context_rva = ref
                    if dst.reg == capstone.x86.X86_REG_RCX:
                        meta_rva = ref
        if sink not in SINKS or not is_boundary(rva):
            continue
        context = string_at(context_rva) if sink == 0x25B78B0 and context_rva is not None else None
        if sink == 0x25DD700 and meta_rva is not None:
            try:
                mo = pe.get_offset_from_rva(meta_rva)
                strings = struct.unpack_from('<Q', data, mo + 8)[0] - base
                metadata = struct.unpack_from('<Q', data, mo + 16)[0] - base
                class_index = struct.unpack_from('<I', data, pe.get_offset_from_rva(metadata) + 4)[0]
                entry = strings + class_index * 24
                rel = struct.unpack_from('<q', data, pe.get_offset_from_rva(entry) + 16)[0]
                context = string_at(entry + rel)
            except (ValueError, struct.error, pefile.PEFormatError):
                pass
        if not context:
            context = 'unresolved_context'
        records.append({'id': f'{rva:08X}', 'context': context, 'source': source_text,
                        'source_rva': target, 'lea_rva': rva, 'lea_offset': offset,
                        'preimage_hex': data[offset:offset + 7].hex().upper(),
                        'call_rva': ins.address - base, 'sink_rva': sink})
    return {'schema': 1, 'source_sha256': BASELINE, 'site_count': len(records),
            'scope': 'direct constant source references to two statically traced Qt translation sinks; not runtime completeness',
            'sites': records}


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    result = extract(args.source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(json.dumps({'sites': result['site_count'], 'output': str(args.output)}))
