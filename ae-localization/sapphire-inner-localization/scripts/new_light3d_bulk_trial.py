from __future__ import annotations
import argparse, ctypes, hashlib, json, struct
from dataclasses import dataclass
from pathlib import Path
from new_relocated_title_trial import BASELINE_SHA256, align, find_all, pe_checksum

@dataclass
class Node:
    kind: str; start: int; end: int; children: list['Node'] | None = None
    def atom(self, data: bytes) -> bytes: return data[self.start:self.end]

def ws(data: bytes, i: int) -> int:
    while i < len(data) and data[i] in b' \t\r\n': i += 1
    return i

def parse(data: bytes, i: int) -> tuple[Node, int]:
    i = ws(data, i); start = i
    if data[i] == 40:
        i += 1; children = []
        while True:
            i = ws(data, i)
            if data[i] == 41: return Node('list', start, i + 1, children), i + 1
            child, i = parse(data, i); children.append(child)
    if data[i] == 34:
        i += 1; escaped = False
        while i < len(data):
            c = data[i]; i += 1
            if escaped: escaped = False
            elif c == 92: escaped = True
            elif c == 34: break
        return Node('atom', start, i), i
    while i < len(data) and data[i] not in b'() \t\r\n': i += 1
    return Node('atom', start, i), i

def assignment_points(definition: bytes) -> tuple[list[str], dict[str, tuple[int, bool]]]:
    root, end = parse(definition, 0)
    if end != len(definition) or root.kind != 'list': raise ValueError('invalid definition boundary')
    c = root.children or []
    if [x.atom(definition) for x in c[:2]] != [b'def_effect', b'Light3D_Autogen']: raise ValueError('unexpected def_effect')
    params = c[4]; items = params.children or []
    starts = [i for i in range(len(items)-1) if items[i].kind == 'atom' and items[i+1].atom(definition) == b'=']
    keys = [items[i].atom(definition).decode('ascii') for i in starts]; points = {}
    for n, start in enumerate(starts):
        stop = starts[n+1] if n+1 < len(starts) else len(items)
        segment = items[start:stop]
        if any(x.kind == 'atom' and x.atom(definition) == b'title' for x in segment): raise ValueError(f'existing title: {keys[n]}')
        modifiers = [x for x in segment if x.kind == 'list']
        points[keys[n]] = (modifiers[-1].end - 1, True) if modifiers else ((items[stop].start if stop < len(items) else params.end - 1), False)
    return keys, points

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', type=Path, default=Path(r'D:\tmp\sapphire-patch-lab\sapphire_ae.dll'))
    ap.add_argument('--mapping', type=Path, required=True)
    ap.add_argument('--destination', type=Path, required=True)
    a = ap.parse_args(); source = a.source.resolve(); dest = a.destination.resolve()
    trials = Path(r'D:\tmp\sapphire-patch-lab\trials').resolve()
    if trials not in dest.parents or dest.exists(): raise SystemExit('destination must be new and below trials')
    original = source.read_bytes()
    if hashlib.sha256(original).hexdigest().upper() != BASELINE_SHA256: raise SystemExit('baseline hash mismatch')
    mapping = json.loads(a.mapping.read_text(encoding='utf-8'))['parameters']
    pe = struct.unpack_from('<I', original, 0x3c)[0]; opt = pe + 24
    if original[pe:pe+4] != b'PE\0\0' or struct.unpack_from('<H', original, opt)[0] != 0x20B: raise SystemExit('PE32+ expected')
    ns = struct.unpack_from('<H', original, pe+6)[0]; os = struct.unpack_from('<H', original, pe+20)[0]; table = opt + os
    image_base = struct.unpack_from('<Q', original, opt+24)[0]; sa = struct.unpack_from('<I', original, opt+32)[0]; fa = struct.unpack_from('<I', original, opt+36)[0]
    sections=[]
    for i in range(ns):
        h=table+i*40; vs,va,rs,ro=struct.unpack_from('<IIII',original,h+8); sections.append({'h':h,'vs':vs,'va':va,'rs':rs,'ro':ro})
    if table+(ns+1)*40 > min(x['ro'] for x in sections): raise SystemExit('no PE header room')
    start=original.find(b'(def_effect Light3D_Autogen ')
    definition_node,end=parse(original,start); definition=original[start:end]
    keys,points=assignment_points(definition)
    if set(keys)!=set(mapping): raise SystemExit(f'map mismatch missing={sorted(set(keys)-set(mapping))} extra={sorted(set(mapping)-set(keys))}')
    cp=ctypes.windll.kernel32.GetOEMCP(); encoding=f'cp{cp}'; edits=[]
    for key in keys:
        title=mapping[key].encode(encoding,'strict')
        if not title or len(title)>31: raise SystemExit(f'{key}: title is not within PF name limit')
        pos,has_modifiers=points[key]; edits.append((pos, (b' title "'+title+b'"') if has_modifiers else (b' ( title "'+title+b'" )')))
    new_def=bytearray(definition)
    for pos,payload in sorted(edits,reverse=True): new_def[pos:pos]=payload
    new_def=bytes(new_def)
    new_keys,_=assignment_points(new_def)
    if new_keys != keys: raise SystemExit('internal parameter keys changed')
    section=next(x for x in sections if x['ro']<=start<x['ro']+x['rs']); old_rva=section['va']+start-section['ro']; refs=find_all(original,struct.pack('<Q',image_base+old_rva))
    if len(refs)!=1: raise SystemExit(f'definition pointer count={len(refs)}')
    new_rva=align(max(x['va']+max(x['vs'],x['rs']) for x in sections),sa); raw=align(len(original),fa); body=new_def+b'\0'; raw_size=align(len(body),fa)
    out=bytearray(raw+raw_size); out[:len(original)]=original; out[raw:raw+len(body)]=body; struct.pack_into('<Q',out,refs[0],image_base+new_rva)
    code_rva=0xD54525; text=next(x for x in sections if x['va']<=code_rva<x['va']+x['rs']); code_raw=text['ro']+code_rva-text['va']; pre=bytes.fromhex('85 C0 75 04 33 FF EB 48'); post=bytes.fromhex('85 C0 75 04 84 DB 79 48')
    if out[code_raw:code_raw+8]!=pre: raise SystemExit('normalizer preimage mismatch')
    h=table+ns*40; out[h:h+40]=b'\0'*40; out[h:h+8]=b'.spcn\0\0\0'; struct.pack_into('<IIII',out,h+8,len(body),new_rva,raw_size,raw); struct.pack_into('<I',out,h+36,0x40000040)
    struct.pack_into('<H',out,pe+6,ns+1); struct.pack_into('<I',out,opt+56,align(new_rva+len(body),sa)); out[code_raw:code_raw+8]=post; struct.pack_into('<I',out,opt+64,pe_checksum(out,opt+64))
    if out[raw:raw+len(body)]!=body or out[code_raw:code_raw+8]!=post: raise SystemExit(f'postimage verification failed body={out[raw:raw+len(body)]==body} code={out[code_raw:code_raw+8].hex().upper()}')
    dest.parent.mkdir(parents=True); dest.write_bytes(out)
    manifest={'source_sha256':BASELINE_SHA256,'destination':str(dest),'destination_sha256':hashlib.sha256(out).hexdigest().upper(),'effect':'Light3D_Autogen','mapped_parameter_count':len(keys),'oem_code_page':cp,'internal_parameter_keys_unchanged':True,'definition_pointer_file_offset':f'0x{refs[0]:X}','new_section':{'name':'.spcn','raw_offset':f'0x{raw:X}','raw_size':raw_size,'virtual_size':len(body)},'title_normalizer_patch':{'rva':f'0x{code_rva:X}','file_offset':f'0x{code_raw:X}','preimage_hex':pre.hex().upper(),'postimage_hex':post.hex().upper()}}
    (dest.parent/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8'); print(json.dumps(manifest,ensure_ascii=False))
if __name__ == '__main__': main()
