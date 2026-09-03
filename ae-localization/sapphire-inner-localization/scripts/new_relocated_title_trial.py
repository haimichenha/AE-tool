from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path

BASELINE_SHA256 = "3A01082AD1D1F3189B9929B717BFD384FB5676BB0BC927F9E2141FAF54C07482"
LAB_ROOT = Path(r"D:\tmp\sapphire-patch-lab")


def align(value: int, alignment: int) -> int:
    return (value + alignment - 1) // alignment * alignment


def find_all(data: bytes, needle: bytes) -> list[int]:
    hits: list[int] = []
    cursor = 0
    while True:
        cursor = data.find(needle, cursor)
        if cursor < 0:
            return hits
        hits.append(cursor)
        cursor += 1


def pe_checksum(data: bytearray, checksum_offset: int) -> int:
    data[checksum_offset:checksum_offset + 4] = b"\0" * 4
    total = 0
    for i in range(0, len(data) - 1, 2):
        total += data[i] | (data[i + 1] << 8)
        total = (total & 0xFFFF) + (total >> 16)
    if len(data) & 1:
        total += data[-1]
        total = (total & 0xFFFF) + (total >> 16)
    total = (total & 0xFFFF) + (total >> 16)
    total = (total & 0xFFFF) + (total >> 16)
    return (total + len(data)) & 0xFFFFFFFF


def main() -> None:
    ap = argparse.ArgumentParser(description="Create an isolated relocated Light3D title trial.")
    ap.add_argument("--source", type=Path, default=LAB_ROOT / "sapphire_ae.dll")
    ap.add_argument("--mode", choices=("ascii_quote", "gbk_quote", "utf8_quote", "unicode_escape"), default="gbk_quote")
    ap.add_argument("--definition", choices=("Light3D", "Light3D_Autogen"), default="Light3D")
    ap.add_argument("--allow-high-bit", action="store_true", help="Preserve bytes >= 0x80 in sapphire_get_param_title; test copies only.")
    ap.add_argument("--destination", type=Path)
    args = ap.parse_args()

    source = args.source.resolve()
    destination = (args.destination or LAB_ROOT / "trials" / f"light3d_{args.definition.lower()}_{args.mode}" / "sapphire_ae.dll").resolve()
    trial_root = (LAB_ROOT / "trials").resolve()
    if trial_root not in destination.parents:
        raise SystemExit(f"destination must remain below {trial_root}")
    if destination.exists():
        raise SystemExit(f"refusing to overwrite existing trial: {destination}")

    original = source.read_bytes()
    source_hash = hashlib.sha256(original).hexdigest().upper()
    if source_hash != BASELINE_SHA256:
        raise SystemExit(f"source hash is not the recorded baseline: {source_hash}")

    pe = struct.unpack_from("<I", original, 0x3C)[0]
    if original[pe:pe + 4] != b"PE\0\0":
        raise SystemExit("not a PE image")
    number_sections = struct.unpack_from("<H", original, pe + 6)[0]
    optional_size = struct.unpack_from("<H", original, pe + 20)[0]
    optional = pe + 24
    if struct.unpack_from("<H", original, optional)[0] != 0x20B:
        raise SystemExit("expected PE32+ image")
    image_base = struct.unpack_from("<Q", original, optional + 24)[0]
    section_alignment = struct.unpack_from("<I", original, optional + 32)[0]
    file_alignment = struct.unpack_from("<I", original, optional + 36)[0]
    section_table = optional + optional_size
    sections: list[dict[str, int | str]] = []
    for i in range(number_sections):
        h = section_table + i * 40
        name = original[h:h + 8].split(b"\0", 1)[0].decode("ascii")
        virtual_size, virtual_address, raw_size, raw_offset = struct.unpack_from("<IIII", original, h + 8)
        sections.append({"name": name, "virtual_size": virtual_size, "virtual_address": virtual_address, "raw_size": raw_size, "raw_offset": raw_offset})
    if section_table + (number_sections + 1) * 40 > min(int(s["raw_offset"]) for s in sections):
        raise SystemExit("no PE header room for one appended section")

    definition_prefix = f"(def_effect {args.definition} ".encode("ascii")
    definition_hits = find_all(original, definition_prefix)
    if len(definition_hits) != 1:
        raise SystemExit(f"expected one {args.definition} definition, found {len(definition_hits)}")
    definition_start = definition_hits[0]
    definition_end = original.find(b"\0", definition_start)
    if definition_end < 0:
        raise SystemExit("unterminated Light3D definition")
    definition = original[definition_start:definition_end]

    old_clause = b"ambient_bright = 0.2 ( min * slider_range 0 1 )"
    if args.mode == "ascii_quote":
        title = b'"Probe"'
    elif args.mode == "gbk_quote":
        title = b'"' + "环境亮度".encode("gbk") + b'"'
    elif args.mode == "utf8_quote":
        title = b'"' + "环境亮度".encode("utf-8") + b'"'
    else:
        title = b'"\\u73AF\\u5883\\u4EAE\\u5EA6"'
    new_clause = old_clause[:-1] + b" title " + title + b" )"
    clause_hits = find_all(definition, old_clause)
    if len(clause_hits) != 1:
        raise SystemExit(f"expected one target parameter clause, found {len(clause_hits)}")
    clause_start = clause_hits[0]
    new_definition = definition[:clause_start] + new_clause + definition[clause_start + len(old_clause):]

    def_section = next((s for s in sections if int(s["raw_offset"]) <= definition_start < int(s["raw_offset"]) + int(s["raw_size"])), None)
    if not def_section:
        raise SystemExit("definition does not belong to a mapped PE section")
    old_rva = int(def_section["virtual_address"]) + definition_start - int(def_section["raw_offset"])
    old_va = image_base + old_rva
    pointer_hits = find_all(original, struct.pack("<Q", old_va))
    if len(pointer_hits) != 1:
        raise SystemExit(f"expected one Light3D definition pointer, found {len(pointer_hits)}")
    pointer_offset = pointer_hits[0]

    max_image_end = max(int(s["virtual_address"]) + max(int(s["virtual_size"]), int(s["raw_size"])) for s in sections)
    new_rva = align(max_image_end, section_alignment)
    new_va = image_base + new_rva
    section_data = new_definition + b"\0"
    new_raw_offset = align(len(original), file_alignment)
    new_raw_size = align(len(section_data), file_alignment)
    output = bytearray(new_raw_offset + new_raw_size)
    output[:len(original)] = original
    output[new_raw_offset:new_raw_offset + len(section_data)] = section_data

    # title normalizer: retain high-bit bytes (e.g. GBK) while continuing to drop ASCII control bytes.
    # Original: test eax,eax; jne keep; xor edi,edi; jmp skip
    # Patched:  test eax,eax; jne keep; test bl,bl; jns skip
    normalizer_patch = None
    if args.allow_high_bit:
        title_normalizer_rva = 0xD54525
        code_section = next((s for s in sections if int(s["virtual_address"]) <= title_normalizer_rva < int(s["virtual_address"]) + int(s["raw_size"])), None)
        if not code_section:
            raise SystemExit("title normalizer RVA is not in a mapped raw section")
        title_normalizer_raw = int(code_section["raw_offset"]) + title_normalizer_rva - int(code_section["virtual_address"])
        expected = bytes.fromhex("85 C0 75 04 33 FF EB 48")
        replacement = bytes.fromhex("85 C0 75 04 84 DB 79 48")
        if output[title_normalizer_raw:title_normalizer_raw + len(expected)] != expected:
            raise SystemExit("title normalizer preimage mismatch")
        output[title_normalizer_raw:title_normalizer_raw + len(replacement)] = replacement
        normalizer_patch = {"rva": f"0x{title_normalizer_rva:X}", "file_offset": f"0x{title_normalizer_raw:X}", "preimage_hex": expected.hex().upper(), "postimage_hex": replacement.hex().upper()}

    # Update the existing table entry; its original base-relocation entry remains valid.
    struct.pack_into("<Q", output, pointer_offset, new_va)
    new_header = section_table + number_sections * 40
    output[new_header:new_header + 40] = b"\0" * 40
    output[new_header:new_header + 8] = b".sptitle"
    struct.pack_into("<IIII", output, new_header + 8, len(section_data), new_rva, new_raw_size, new_raw_offset)
    struct.pack_into("<I", output, new_header + 36, 0x40000040)  # initialized data, readable
    struct.pack_into("<H", output, pe + 6, number_sections + 1)
    struct.pack_into("<I", output, optional + 56, align(new_rva + len(section_data), section_alignment))
    struct.pack_into("<I", output, optional + 64, pe_checksum(output, optional + 64))

    if output[definition_start:definition_end] != definition:
        raise SystemExit("original in-place definition unexpectedly changed")
    if output[pointer_offset:pointer_offset + 8] != struct.pack("<Q", new_va):
        raise SystemExit("definition pointer postimage mismatch")
    if output[new_raw_offset:new_raw_offset + len(section_data)] != section_data:
        raise SystemExit("new section postimage mismatch")

    destination.parent.mkdir(parents=True, exist_ok=False)
    destination.write_bytes(output)
    manifest = {
        "source": str(source),
        "source_sha256": source_hash,
        "destination": str(destination),
        "destination_sha256": hashlib.sha256(output).hexdigest().upper(),
        "effect": args.definition,
        "parameter_key": "ambient_bright",
        "title_mode": args.mode,
        "title_bytes_hex": title.hex().upper(),
        "old_definition_file_offset": f"0x{definition_start:X}",
        "old_definition_rva": f"0x{old_rva:X}",
        "definition_pointer_file_offset": f"0x{pointer_offset:X}",
        "new_definition_rva": f"0x{new_rva:X}",
        "new_section": {"name": ".sptitle", "raw_offset": f"0x{new_raw_offset:X}", "raw_size": new_raw_size, "virtual_size": len(section_data)},
        "added_definition_bytes": len(new_definition) - len(definition),
        "title_normalizer_patch": normalizer_patch,
        "file_size_before": len(original),
        "file_size_after": len(output),
    }
    (destination.parent / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False))

if __name__ == "__main__":
    main()
