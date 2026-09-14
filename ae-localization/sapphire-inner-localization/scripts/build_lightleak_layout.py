"""Localize verified layout group captions and fix two contextual title translations."""
import argparse,hashlib,json,struct,sys
from pathlib import Path
import pefile
from lightleak_title_metadata import PIN,COUNTS,translate,parse

LAYOUT=0x1A54E60
TAIL=0x1A9DA6C
FIRST_SHA='836DBB68C7C912FC9E2F41BCE51889FD348A7077F151E2AA65C47DD346126BE2'
GROUPS={b'Glow':'辉光',b'Element1':'元素1',b'Element2':'元素2',b'Element3':'元素3'}
sha=lambda b:hashlib.sha256(b).hexdigest().upper()

def walk(n):
 yield n
 if n.kind=='list':
  for c in n.children:yield from walk(c)

def opacity_modifier(tree,data):
 nodes=[n for n in walk(tree) if n.kind=='list' and len(n.children)>=5 and n.children[0].atom(data)==b':extra' and n.children[1].atom(data)==b'opacity']
 if len(nodes)!=1:raise ValueError('opacity extra not unique')
 node=nodes[0]
 if node.children[2].atom(data)!=b'=' or node.children[3].atom(data)!=b'1' or node.children[4].kind!='list':raise ValueError('opacity default/type changed')
 return node.children[4]

def normalized(node,data,opacity_mod):
 if node.kind!='list':return node.atom(data)
 children=node.children;result=[];i=0
 reverse={v.encode('cp936'):k for k,v in GROUPS.items()}
 while i<len(children):
  c=children[i];token=c.atom(data)
  if node is opacity_mod and token==b'title':
   if i+1>=len(children) or children[i+1].atom(data)!=b'"'+'不透明度'.encode('cp936')+b'"':raise ValueError('unexpected opacity title')
   i+=2;continue
  if token in [b'group_start',b'group_end'] and i+1<len(children):
   value=children[i+1].atom(data);result.extend([token,reverse.get(value,value)]);i+=2;continue
  result.append(normalized(c,data,opacity_mod));i+=1
 return result

def update_layout(first,tail):
 data=first+tail;tree,end=parse(data,0)
 if end!=len(data) or tree.children[0].atom(data)!=b'layout_effect':raise ValueError('incomplete layout')
 if [n.atom(data) for n in tree.children[1].children]!=[b'LightLeak',b'LightLeak_Autogen']:raise ValueError('wrong layout owner')
 edits=[];stack=[];pairs=[]
 for node in walk(tree):
  if node.kind!='list':continue
  for i,c in enumerate(node.children[:-1]):
   kind=c.atom(data)
   if kind not in [b'group_start',b'group_end']:continue
   arg=node.children[i+1];value=arg.atom(data)
   if kind==b'group_start':stack.append(value)
   elif not stack or stack.pop()!=value:raise ValueError('unbalanced layout group')
   if value in GROUPS:
    if arg.end>len(first):raise ValueError('group crosses fragment boundary')
    edits.append((arg.start,arg.end,GROUPS[value].encode('cp936')));pairs.append((kind,value))
 if stack or len(edits)!=8 or any(pairs.count((kind,key))!=1 for key in GROUPS for kind in [b'group_start',b'group_end']):raise ValueError('group coverage mismatch')
 mod=opacity_modifier(tree,data)
 if mod.atom(data)!=b'( popup All_Opaque Normal As_Premult )' or mod.end>len(first):raise ValueError('opacity modifier preimage')
 edits.append((mod.end-1,mod.end-1,b' title "'+'不透明度'.encode('cp936')+b'"'))
 out=bytearray(first)
 for start,end,payload in sorted(edits,reverse=True):out[start:end]=payload
 if len(out)>len(first):raise ValueError('layout fragment capacity')
 out.extend(b' '*(len(first)-len(out)));new=bytes(out)+tail;newtree,end=parse(new,0)
 if end!=len(new):raise ValueError('new layout boundary')
 if normalized(tree,data,mod)!=normalized(newtree,new,opacity_modifier(newtree,new)):raise ValueError('non-display layout token change')
 return bytes(out)

def build(source,output):
 source=Path(source).resolve();output=Path(output).resolve()
 if output.exists() or output.with_suffix('.manifest.json').exists() or output.parent==source.parent:raise ValueError('new isolated output required')
 b=source.read_bytes()
 if sha(b)!=PIN:raise ValueError('source pin mismatch')
 first=b[LAYOUT:b.index(b'\0',LAYOUT)];tail=b[TAIL:b.index(b'\0',TAIL)]
 if len(first)!=2040 or sha(first)!=FIRST_SHA or tail!=b' id_insert 542 ) ) ) )':raise ValueError('layout fragments mismatch')
 out=bytearray(b);out[LAYOUT:LAYOUT+len(first)]=update_layout(first,tail);changes=[(LAYOUT,len(first))];title_changes=[]
 pe=pefile.PE(data=b,fast_load=True);sec=next(s for s in pe.sections if s.Name.rstrip(b'\0')==b'.sploc');lo=sec.PointerToRawData;hi=lo+sec.Misc_VirtualSize
 for name in COUNTS:
  needle=b'(def_effect '+name.encode()+b' '
  if b[lo:hi].count(needle)!=1:raise ValueError('ambiguous localized definition')
  start=b.index(needle,lo,hi);_,end=parse(b,start);d=b[start:end]
  _,edits=translate(d,name)
  # Do not retain the ineffective doc_group_name experiment.
  for offset,old,new,kind,key in edits:
   if kind!='title':continue
   pos=start+offset;out[pos:pos+len(old)]=new;changes.append((pos,len(old)));title_changes.append({'definition':name,'key':key,'offset':pos})
 if len(title_changes)!=4:raise ValueError('title correction coverage')
 check=pe.OPTIONAL_HEADER.get_field_absolute_offset('CheckSum');struct.pack_into('<I',out,check,0);struct.pack_into('<I',out,check,pefile.PE(data=bytes(out),fast_load=True).generate_checksum());changes.append((check,4))
 reverse=bytearray(out)
 for pos,size in changes:reverse[pos:pos+size]=b[pos:pos+size]
 if reverse!=b or len(out)!=len(b):raise ValueError('unallowlisted byte changes')
 for s in pe.sections:
  if s.Characteristics&0x20000000:
   a=s.PointerToRawData;z=a+s.SizeOfRawData
   if out[a:z]!=b[a:z]:raise ValueError('executable code changed')
 if not pefile.PE(data=bytes(out),fast_load=True).verify_checksum():raise ValueError('PE checksum')
 output.parent.mkdir(parents=True,exist_ok=True)
 with output.open('xb') as f:f.write(out)
 if output.read_bytes()!=out:raise ValueError('disk readback')
 report={'source_sha256':PIN,'output_sha256':sha(out),'affected_effect':'R_LightLeak','layout_fragment_offset':hex(LAYOUT),'layout_tail_offset':hex(TAIL),
  'groups':{k.decode():v for k,v in GROUPS.items()},'extra_parameter_title':{'opacity':'不透明度'},'title_corrections':title_changes,
  'static_scope':'one layout fragment with paired group label changes and opacity title; four contextual title spans; PE checksum; no executable changes',
  'doc_group_name_preserved':True,'normalized_layout_tokens_identical':True,'runtime_validation':'pending','deployed':False}
 output.with_suffix('.manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');return report

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--source',required=True);ap.add_argument('--output',required=True);a=ap.parse_args();print(json.dumps(build(a.source,a.output),ensure_ascii=False))
