from __future__ import annotations
import hashlib, json, struct
from pathlib import Path

SRC=Path(r'D:\tmp\sapphire-patch-lab\trials\light3d_full_cp936_highbit\sapphire_ae.dll')
DST=Path(r'D:\tmp\sapphire-patch-lab\trials\light3d_full_mocha_redirect\sapphire_ae.dll')
EXPECTED='3F1C7BC6DB490680A9D962AEDD8EA5222B0FACA8407590F51844E3DB47FFEF50'
ROOT=r'D:\tmp\saprt\l3dan'
FORMAT=b'%s\\lib64\\mocha-wrapper.exe'

def align(v,a): return (v+a-1)//a*a
def checksum(d,o):
 d[o:o+4]=b'\0'*4;s=0
 for i in range(0,len(d)-1,2): s+=(d[i]|d[i+1]<<8);s=(s&0xffff)+(s>>16)
 if len(d)&1:s+=d[-1];s=(s&0xffff)+(s>>16)
 s=(s&0xffff)+(s>>16);s=(s&0xffff)+(s>>16);return(s+len(d))&0xffffffff
if DST.exists(): raise SystemExit('refusing to overwrite destination')
b=SRC.read_bytes()
if hashlib.sha256(b).hexdigest().upper()!=EXPECTED:raise SystemExit('source hash mismatch')
pe=struct.unpack_from('<I',b,0x3c)[0];opt=pe+24;ibase=struct.unpack_from('<Q',b,opt+24)[0];ns=struct.unpack_from('<H',b,pe+6)[0];os=struct.unpack_from('<H',b,pe+20)[0];table=opt+os;sa=struct.unpack_from('<I',b,opt+32)[0];fa=struct.unpack_from('<I',b,opt+36)[0]
secs=[]
for i in range(ns):
 h=table+i*40;name=b[h:h+8].split(b'\0',1)[0].decode('ascii','replace');vs,va,rs,ro=struct.unpack_from('<IIII',b,h+8);secs.append({'name':name,'h':h,'vs':vs,'va':va,'rs':rs,'ro':ro})
if table+(ns+1)*40>min(s['ro'] for s in secs):raise SystemExit('no PE header room')
start=b.find(FORMAT)
if start<0 or b.find(FORMAT,start+1)>=0:raise SystemExit('wrapper format preimage mismatch')
target_va=ibase+next(s['va']+start-s['ro'] for s in secs if s['ro']<=start<s['ro']+s['rs'])
text=next(s for s in secs if s['name']=='.text');refs=[]
for raw in range(text['ro'],text['ro']+text['rs']-7):
 if 0x40<=b[raw]<=0x4f and b[raw+1]==0x8d and (b[raw+2]&0xc7)==0x05:
  disp=struct.unpack_from('<i',b,raw+3)[0];rva=text['va']+raw-text['ro']
  if ibase+rva+7+disp==target_va:refs.append((raw,rva,b[raw:raw+7]))
if len(refs)!=5:raise SystemExit(f'expected 5 wrapper format references, got {len(refs)}')
body=ROOT.encode('ascii')+b'\\lib64\\mocha-wrapper.exe\0';raw=align(len(b),fa);rawsize=align(len(body),fa);newrva=align(max(s['va']+max(s['vs'],s['rs']) for s in secs),sa);newva=ibase+newrva
out=bytearray(raw+rawsize);out[:len(b)]=b;out[raw:raw+len(body)]=body
for oldraw,rva,oldbytes in refs:
 newdisp=newva-(ibase+rva+7)
 if not -0x80000000<=newdisp<=0x7fffffff:raise SystemExit('RIP displacement out of range')
 out[oldraw:oldraw+3]=oldbytes[:3];struct.pack_into('<i',out,oldraw+3,newdisp)
 if ibase+rva+7+struct.unpack_from('<i',out,oldraw+3)[0]!=newva:raise SystemExit('redirect postimage mismatch')
h=table+ns*40;out[h:h+40]=b'\0'*40;out[h:h+8]=b'.spmw\0\0\0';struct.pack_into('<IIII',out,h+8,len(body),newrva,rawsize,raw);struct.pack_into('<I',out,h+36,0x40000040);struct.pack_into('<H',out,pe+6,ns+1);struct.pack_into('<I',out,opt+56,align(newrva+len(body),sa));struct.pack_into('<I',out,opt+64,checksum(out,opt+64))
if out[raw:raw+len(body)]!=body:raise SystemExit('section postimage mismatch')
DST.parent.mkdir(parents=True,exist_ok=False);DST.write_bytes(out)
manifest={'source':str(SRC),'source_sha256':EXPECTED,'destination':str(DST),'destination_sha256':hashlib.sha256(out).hexdigest().upper(),'wrapper_original_format':FORMAT.decode(),'wrapper_redirect_path':body[:-1].decode(),'redirected_lea_file_offsets':[f'0x{x[0]:X}' for x in refs],'redirected_lea_rvas':[f'0x{x[1]:X}' for x in refs],'new_section':{'name':'.spmw','raw_offset':f'0x{raw:X}','raw_size':rawsize,'virtual_size':len(body)}}
(DST.parent/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8');print(json.dumps(manifest))
