"""Pinned contextual title correction helper. Host group labels are handled in layout_effect, not doc_group_name."""
import argparse,hashlib,json,struct,sys
from pathlib import Path
import pefile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from new_light3d_bulk_trial import parse
from build_lighting_batch_titles import segments

PIN='23425CFF3CB0A27BCBFA41167EEE67CFD853B2B8D16EDBC382579DC73C17FC28'
COUNTS={'LightLeak':70,'LightLeak_Autogen':84}
sha=lambda b:hashlib.sha256(b).hexdigest().upper()

def translate(d,name):
 if name not in COUNTS:raise ValueError('unsupported definition')
 parts=segments(d,name)
 if len(parts)!=COUNTS[name]:raise ValueError('parameter count changed')
 rows=dict(parts);edits=[]
 for i in [1,2]:
  key=f'softness{i}';nodes=rows[key];hits=[]
  for node in nodes:
   if node.kind!='list':continue
   for j,child in enumerate(node.children[:-1]):
    if child.atom(d)==b'title':hits.append(node.children[j+1])
  old=('"灯光'+str(i)+'柔和度"').encode('cp936');new=('"元素'+str(i)+'柔和度"').encode('cp936')
  if len(hits)!=1 or hits[0].atom(d)!=old or len(old)!=len(new):raise ValueError('title preimage mismatch')
  edits.append((hits[0].start,old,new,'title',key))
 out=bytearray(d)
 for off,old,new,kind,key in edits:
  if out[off:off+len(old)]!=old:raise ValueError('overlap/preimage')
  out[off:off+len(old)]=new
 if [k for k,_ in segments(bytes(out),name)]!=[k for k,_ in parts]:raise ValueError('parameter key/order changed')
 reverse=bytearray(out)
 for off,old,new,kind,key in edits:
  if reverse[off:off+len(new)]!=new:raise ValueError('metadata readback')
  reverse[off:off+len(old)]=old
 if reverse!=d:raise ValueError('non-display definition mutation')
 return bytes(out),edits
