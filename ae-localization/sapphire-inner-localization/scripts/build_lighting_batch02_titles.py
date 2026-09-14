"""Version-pinned batch02: four effects, five definitions, titles only; no deployment."""
import argparse,hashlib,json,struct
from pathlib import Path
from new_light3d_bulk_trial import parse
from new_relocated_title_trial import align,find_all,pe_checksum
SOURCE_SHA='410C69A61BEC964322550ECC8662D60E454C1984175E2850B4244B02C31A7B91'
SUPPORTED={'LensFlare': 74, 'LensFlareAutoTrack': 73, 'SpotLight': 34, 'SpotLight_Autogen': 47, 'UltraGlow': 71}
def sha(b):return hashlib.sha256(b).hexdigest().upper()
def segments(d,name):
 root,end=parse(d,0)
 if end!=len(d) or [x.atom(d) for x in root.children[:2]]!=[b'def_effect',name.encode('ascii')]:raise ValueError('definition identity mismatch')
 items=root.children[4].children
 starts=[i for i in range(len(items)-1) if items[i].kind=='atom' and items[i+1].atom(d)==b'=']
 return [(items[i].atom(d).decode('ascii'),items[i:starts[n+1] if n+1<len(starts) else len(items)]) for n,i in enumerate(starts)]
def translate(d,name,titles):
 parts=segments(d,name);keys=[k for k,_ in parts]
 if len(keys)!=SUPPORTED[name] or len(set(keys))!=len(keys) or set(keys)!=set(titles):raise ValueError('exact parameter key coverage required: '+name)
 edits=[]
 for key,part in parts:
  value=titles[key]
  if not isinstance(value,str) or not value.strip() or any(c in value for c in '\0"\\\n\r'):raise ValueError('invalid title')
  t=value.encode('cp936')
  if len(t)>31:raise ValueError('title exceeds31 bytes')
  mods=[x for x in part if x.kind=='list']
  if any(any(x.atom(d)==b'title' for x in mod.children) for mod in mods):raise ValueError('existing title: '+key)
  pos=mods[-1].end-1 if mods else part[-1].end
  payload=b' title "'+t+b'"' if mods else b' ( title "'+t+b'" )'
  edits.append((pos,payload))
 out=bytearray(d)
 for pos,payload in sorted(edits,reverse=True):out[pos:pos]=payload
 if [k for k,_ in segments(bytes(out),name)]!=keys:raise ValueError('parameter order changed')
 reverse=bytearray(out);shift=0;positions=[]
 for pos,payload in sorted(edits):positions.append((pos+shift,payload));shift+=len(payload)
 for pos,payload in reversed(positions):
  if reverse[pos:pos+len(payload)]!=payload:raise ValueError('title readback mismatch')
  del reverse[pos:pos+len(payload)]
 if reverse!=d:raise ValueError('non-title definition bytes changed')
 return bytes(out),keys
def build(source,mapping,output):
 source=Path(source).resolve();output=Path(output).resolve()
 if output.exists() or output.parent==source.parent:raise ValueError('new isolated output required')
 b=source.read_bytes()
 if sha(b)!=SOURCE_SHA:raise ValueError('source hash mismatch')
 m=json.loads(Path(mapping).read_text(encoding='utf-8-sig'))
 if m.get('encoding')!='cp936' or m.get('source_sha256')!=SOURCE_SHA or set(m['definitions'])!=set(SUPPORTED):raise ValueError('unsupported batch mapping')
 pe=struct.unpack_from('<I',b,60)[0];opt=pe+24;ns=struct.unpack_from('<H',b,pe+6)[0];table=opt+struct.unpack_from('<H',b,pe+20)[0]
 base=struct.unpack_from('<Q',b,opt+24)[0];sa,fa=struct.unpack_from('<II',b,opt+32)
 sections=[struct.unpack_from('<IIII',b,table+40*i+8) for i in range(ns)]
 def rva(off):
  vs,va,rs,ro=next(s for s in sections if s[3]<=off<s[3]+s[2]);return va+off-ro
 header=table+40*ns
 if header+40>min(s[3] for s in sections) or any(b[header:header+40]):raise ValueError('section header capacity')
 text=next(s for s in sections if s[1]<=0xD54525<s[1]+s[2]);norm=text[3]+0xD54525-text[1]
 if b[norm:norm+8]!=bytes.fromhex('85C0750484DB7948'):raise ValueError('normalizer baseline mismatch')
 va=align(max(s[1]+max(s[0],s[2]) for s in sections),sa);payload=bytearray();records=[]
 for name in sorted(SUPPORTED):
  needle=b'(def_effect '+name.encode()+b' '
  if b.count(needle)!=1:raise ValueError('ambiguous definition '+name)
  start=b.index(needle);_,end=parse(b,start)
  updated,keys=translate(b[start:end],name,m['definitions'][name]['parameters'])
  refs=find_all(b,struct.pack('<Q',base+rva(start)))
  if len(refs)!=1:raise ValueError('definition reference count !=1')
  padding=align(len(payload),16)-len(payload);payload.extend(b'\0'*padding)
  offset=len(payload);payload.extend(updated+b'\0')
  records.append({'definition':name,'original_offset':start,'pointer_offset':refs[0],'new_rva':va+offset,'parameter_count':len(keys)})
 raw=align(len(b),fa);rs=align(len(payload),fa);out=bytearray(b);out.extend(b'\0'*(raw+rs-len(out)));out[raw:raw+len(payload)]=payload
 changes=[]
 for rec in records:struct.pack_into('<Q',out,rec['pointer_offset'],base+rec['new_rva']);changes.append((rec['pointer_offset'],8))
 out[header:header+40]=struct.pack('<8sIIIIIIHHI',b'.sploc\0\0',len(payload),va,rs,raw,0,0,0,0,0x40000040)
 struct.pack_into('<H',out,pe+6,ns+1);struct.pack_into('<I',out,opt+56,align(va+len(payload),sa));struct.pack_into('<I',out,opt+8,struct.unpack_from('<I',b,opt+8)[0]+rs);struct.pack_into('<I',out,opt+64,pe_checksum(out,opt+64))
 changes += [(header,40),(pe+6,2),(opt+56,4),(opt+8,4),(opt+64,4)]
 reverse=bytearray(out[:len(b)])
 for off,size in changes:reverse[off:off+size]=b[off:off+size]
 if reverse!=b:raise ValueError('unallowlisted byte mutation')
 output.parent.mkdir(parents=True,exist_ok=True)
 with output.open('xb') as f:f.write(out)
 if sha(output.read_bytes())!=sha(out):raise ValueError('disk readback mismatch')
 report={'source_sha256':SOURCE_SHA,'output_sha256':sha(out),'mapping_sha256':sha(Path(mapping).read_bytes()),'effects':list(m['entries']),'definitions':records,'title_insertions':sum(x['parameter_count'] for x in records),'static_invariants':'only title insertions, five existing definition pointers and PE metadata; defaults, enums, expression bodies and existing executable bytes unchanged','runtime_validation':'pending','all_ui_translated':False}
 output.with_suffix('.manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');return report
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--source',required=True);ap.add_argument('--mapping',required=True);ap.add_argument('--output',required=True);a=ap.parse_args();print(json.dumps(build(a.source,a.mapping,a.output)))
