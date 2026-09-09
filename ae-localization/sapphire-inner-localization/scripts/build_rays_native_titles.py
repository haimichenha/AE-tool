"""Native Rays title-only candidate on the pinned known-good Light3D core.
No installed files changed; no JSX, enum translation, or internal key replacement.
"""
import argparse,hashlib,json,struct
from pathlib import Path
from new_light3d_bulk_trial import parse
from new_relocated_title_trial import align,find_all,pe_checksum
SOURCE_SHA='410C69A61BEC964322550ECC8662D60E454C1984175E2850B4244B02C31A7B91'


def sha(b):return hashlib.sha256(b).hexdigest().upper()
def parameter_segments(definition):
 root,end=parse(definition,0)
 if end!=len(definition) or [n.atom(definition) for n in root.children[:2]]!=[b'def_effect',b'Rays']:raise ValueError('not a complete Rays definition')
 params=root.children[4];items=params.children
 starts=[i for i in range(len(items)-1) if items[i].kind=='atom' and items[i+1].atom(definition)==b'=']
 return root,params,[(items[i].atom(definition).decode('ascii'),items[i:starts[n+1] if n+1<len(starts) else len(items)]) for n,i in enumerate(starts)]


def build(source,mapping,destination):
 source=Path(source).resolve();destination=Path(destination).resolve()
 if destination.exists() or source.parent==destination.parent:raise ValueError('new isolated destination required')
 b=source.read_bytes()
 if sha(b)!=SOURCE_SHA:raise ValueError('source hash mismatch')
 m=json.loads(Path(mapping).read_text(encoding='utf-8-sig'))
 if m['effect']!='Rays' or m['encoding']!='cp936':raise ValueError('mapping effect/encoding mismatch')
 titles=m['parameters'];needle=b'(def_effect Rays '
 if b.count(needle)!=1:raise ValueError('ambiguous Rays definition')
 start=b.index(needle);_,end=parse(b,start);definition=b[start:end];tree,params,segments=parameter_segments(definition);keys=[key for key,_ in segments]
 if len(keys)!=47 or len(set(keys))!=47 or set(keys)!=set(titles):raise ValueError('mapping keys must exactly match all47 native parameters')
 edits=[]
 for key,seg in segments:
  text=titles[key]
  if not isinstance(text,str) or not text.strip() or any(c in text for c in ['\0','"','\\','\n','\r']):raise ValueError('invalid title: '+key)
  title=text.encode('cp936','strict')
  if len(title)>31:raise ValueError('title exceeds31 CP936 bytes: '+key)
  modifiers=[n for n in seg if n.kind=='list']
  for mod in modifiers:
   if any(n.atom(definition)==b'title' for n in mod.children):raise ValueError('title already present')
  if modifiers:pos=modifiers[-1].end-1;payload=b' title "'+title+b'"'
  else:pos=seg[-1].end;payload=b' ( title "'+title+b'" )'
  edits.append((pos,payload))
 updated=bytearray(definition)
 for pos,payload in sorted(edits,reverse=True):updated[pos:pos]=payload
 updated=bytes(updated);newtree,_,newsegments=parameter_segments(updated)
 if [k for k,_ in newsegments]!=keys:raise ValueError('key order changed')
 if [n.atom(updated) for n in newtree.children[5:]]!=[n.atom(definition) for n in tree.children[5:]]:raise ValueError('expression body changed')
 reverse=bytearray(updated);shift=0;positions=[]
 for pos,payload in sorted(edits):positions.append((pos+shift,payload));shift+=len(payload)
 for pos,payload in reversed(positions):
  if reverse[pos:pos+len(payload)]!=payload:raise ValueError('inserted title mismatch')
  del reverse[pos:pos+len(payload)]
 if reverse!=definition:raise ValueError('non-title DSL bytes changed')
 pe=struct.unpack_from('<I',b,60)[0];opt=pe+24;ns=struct.unpack_from('<H',b,pe+6)[0];table=opt+struct.unpack_from('<H',b,pe+20)[0];base=struct.unpack_from('<Q',b,opt+24)[0];sa,fa=struct.unpack_from('<II',b,opt+32)
 sections=[]
 for i in range(ns):
  h=table+40*i;vs,va,rs,ro=struct.unpack_from('<IIII',b,h+8);sections.append((vs,va,rs,ro))
 header=table+40*ns
 if header+40>min(s[3] for s in sections) or any(b[header:header+40]):raise ValueError('no section header capacity')
 defsection=next(s for s in sections if s[3]<=start<s[3]+s[2]);oldrva=defsection[1]+start-defsection[3];refs=find_all(b,struct.pack('<Q',base+oldrva))
 if len(refs)!=1:raise ValueError('definition pointer count must be1')
 # Already validated CP936 normalizer is inherited, not changed a second time.
 text=next(s for s in sections if s[1]<=0xD54525<s[1]+s[2]);code=text[3]+0xD54525-text[1]
 if b[code:code+8]!=bytes.fromhex('85C0750484DB7948'):raise ValueError('known-good normalizer missing')
 va=align(max(s[1]+max(s[0],s[2]) for s in sections),sa);raw=align(len(b),fa);body=updated+b'\0';rs=align(len(body),fa)
 out=bytearray(b);out.extend(b'\0'*(raw+rs-len(out)));out[raw:raw+len(body)]=body
 struct.pack_into('<Q',out,refs[0],base+va)
 out[header:header+40]=struct.pack('<8sIIIIIIHHI',b'.spry\0\0\0',len(body),va,rs,raw,0,0,0,0,0x40000040)
 struct.pack_into('<H',out,pe+6,ns+1);struct.pack_into('<I',out,opt+56,align(va+len(body),sa));struct.pack_into('<I',out,opt+8,struct.unpack_from('<I',b,opt+8)[0]+rs);struct.pack_into('<I',out,opt+64,pe_checksum(out,opt+64))
 reverse=bytearray(out[:len(b)])
 for off,size in [(refs[0],8),(header,40),(pe+6,2),(opt+56,4),(opt+8,4),(opt+64,4)]:reverse[off:off+size]=b[off:off+size]
 if reverse!=b:raise ValueError('unallowlisted core bytes changed')
 destination.parent.mkdir(parents=True,exist_ok=True)
 with destination.open('xb') as f:f.write(out)
 if sha(destination.read_bytes())!=sha(out):raise ValueError('disk hash mismatch')
 report={'source_sha256':SOURCE_SHA,'output_sha256':sha(out),'effect':'Rays','mapped_titles':len(keys),'keys':keys,'definition_offset':hex(start),'definition_pointer_offset':hex(refs[0]),'section':'.spry','mapping_sha256':sha(Path(mapping).read_bytes()),'static_check':'only Rays title insertions, one definition pointer and PE metadata; existing code and other definitions unchanged','runtime_validation':'pending','all_ui_translated':False,'unmapped_display_types':['buttons','groups','popup captions','dynamic shared UI']}
 destination.with_suffix('.manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');return report

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--source',required=True);ap.add_argument('--mapping',required=True);ap.add_argument('--output',required=True);a=ap.parse_args();print(json.dumps(build(a.source,a.mapping,a.output)))
