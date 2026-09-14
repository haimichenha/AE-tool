"""Read-only Lighting inventory against a pinned analysis core; no deployment.
Includes underscore aliases and _Autogen definitions. Static matching alone does not prove live binding.
"""
import argparse,hashlib,json,re,struct
from pathlib import Path
from new_light3d_bulk_trial import parse
from build_light3d_chinese_entry import property_field
PIN='410C69A61BEC964322550ECC8662D60E454C1984175E2850B4244B02C31A7B91'
def definition_matches_entry(definition,entry):
 return definition.removesuffix('_Autogen').replace('_','')==entry

def collect(core_path,plugin_dir):
 b=Path(core_path).read_bytes();sha=lambda x:hashlib.sha256(x).hexdigest().upper()
 if sha(b)!=PIN:raise ValueError('unsupported analysis baseline')
 pe=struct.unpack_from('<I',b,60)[0];opt=pe+24;base=struct.unpack_from('<Q',b,opt+24)[0];n=struct.unpack_from('<H',b,pe+6)[0];table=opt+struct.unpack_from('<H',b,pe+20)[0]
 sections=[struct.unpack_from('<IIII',b,table+40*i+8) for i in range(n)];rows=[]
 for p in sorted(Path(plugin_dir).glob('*.aex')):
  data=p.read_bytes();row={'file':p.name,'sha256':sha(data),'baseline_candidates':[]}
  for tag,label in [(b'eman','display_name'),(b'ANMe','match_name')]:
   at,size=property_field(data,tag);row[label]=data[at+1:at+1+data[at]].decode('cp936')
  name=p.stem.removeprefix('S_')
  for match in re.finditer(rb'\(def_effect ([A-Za-z0-9_]+)\s',b):
   if not definition_matches_entry(match.group(1).decode('ascii'),name):continue
   tree,end=parse(b,match.start());nodes=tree.children[4].children
   keys=[nodes[i].atom(b).decode('ascii') for i in range(len(nodes)-1) if nodes[i].kind=='atom' and nodes[i+1].atom(b)==b'=']
   vs,va,rs,ro=next(s for s in sections if s[3]<=match.start()<s[3]+s[2]);pointer=struct.pack('<Q',base+va+match.start()-ro)
   row['baseline_candidates'].append({'name':tree.children[1].atom(b).decode('ascii'),'offset':hex(match.start()),'parameter_count':len(keys),'keys':keys,'absolute_pointer_refs':b.count(pointer)})
  rows.append(row)
 return {'analysis_core_sha256':PIN,'entry_count':len(rows),'entries':rows,'interpretation':'static candidates only; neither missing same-name definitions nor old retained text prove a live localization status; Rays uses separate rays09 core','installed_files_modified':False}
if __name__=='__main__':
 a=argparse.ArgumentParser(description=__doc__);a.add_argument('--core',required=True);a.add_argument('--plugin-dir',required=True);a.add_argument('--output',required=True);v=a.parse_args()
 p=Path(v.output)
 if p.exists():raise ValueError('new report path required')
 r=collect(v.core,v.plugin_dir);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({'entry_count':r['entry_count'],'report':str(p)}))
