from __future__ import annotations
import hashlib,json,struct
from pathlib import Path
SRC=Path(r'D:\tmp\sapphire-patch-lab\trials\light3d_full_cp936_highbit\sapphire_ae.dll')
DST=Path(r'D:\tmp\sapphire-patch-lab\trials\light3d_full_mocha_root_thunk\sapphire_ae.dll')
EXPECTED='3F1C7BC6DB490680A9D962AEDD8EA5222B0FACA8407590F51844E3DB47FFEF50'
ROOT=r'D:\tmp\saprt\l3dao'.encode('ascii')+b'\0';FMT=b'%s\\lib64\\mocha-wrapper.exe';FORMAT_RVA=0xD35370
def align(v,a):return(v+a-1)//a*a
def checksum(d,o):
 d[o:o+4]=b'\0'*4;s=0
 for i in range(0,len(d)-1,2):s+=(d[i]|d[i+1]<<8);s=(s&0xffff)+(s>>16)
 if len(d)&1:s+=d[-1];s=(s&0xffff)+(s>>16)
 s=(s&0xffff)+(s>>16);s=(s&0xffff)+(s>>16);return(s+len(d))&0xffffffff
if DST.exists():raise SystemExit('refusing to overwrite destination')
b=SRC.read_bytes()
if hashlib.sha256(b).hexdigest().upper()!=EXPECTED:raise SystemExit('source hash mismatch')
pe=struct.unpack_from('<I',b,0x3c)[0];opt=pe+24;base=struct.unpack_from('<Q',b,opt+24)[0];ns=struct.unpack_from('<H',b,pe+6)[0];os=struct.unpack_from('<H',b,pe+20)[0];table=opt+os;sa=struct.unpack_from('<I',b,opt+32)[0];fa=struct.unpack_from('<I',b,opt+36)[0]
secs=[]
for i in range(ns):
 h=table+i*40;name=b[h:h+8].split(b'\0',1)[0].decode('ascii','replace');vs,va,rs,ro=struct.unpack_from('<IIII',b,h+8);secs.append({'name':name,'h':h,'vs':vs,'va':va,'rs':rs,'ro':ro})
if table+(ns+1)*40>min(s['ro'] for s in secs):raise SystemExit('no PE header room')
start=b.find(FMT);sec=next(s for s in secs if s['ro']<=start<s['ro']+s['rs']);fmt_va=base+sec['va']+start-sec['ro'];text=next(s for s in secs if s['name']=='.text');refs=[]
for raw in range(text['ro'],text['ro']+text['rs']-7):
 if 0x40<=b[raw]<=0x4f and b[raw+1]==0x8d and (b[raw+2]&0xc7)==0x05:
  disp=struct.unpack_from('<i',b,raw+3)[0];rva=text['va']+raw-text['ro']
  if base+rva+7+disp==fmt_va:
   call_raw=raw+10;call_rva=rva+10
   if b[raw+7:raw+10]!=b'\x49\x89\xc1' or b[call_raw]!=0xe8:raise SystemExit('unexpected root-to-format call preimage')
   target=base+call_rva+5+struct.unpack_from('<i',b,call_raw+1)[0]
   if target!=base+FORMAT_RVA:raise SystemExit('unexpected formatting target')
   refs.append((raw,rva,call_raw,call_rva))
if len(refs)!=5:raise SystemExit(f'expected 5 call sites, got {len(refs)}')
newrva=align(max(s['va']+max(s['vs'],s['rs']) for s in secs),sa);stuboff=align(len(ROOT),16);stub_rva=newrva+stuboff;stub_va=base+stub_rva;root_va=base+newrva
lea=b'\x4c\x8d\x0d'+struct.pack('<i',root_va-(stub_va+7));jmp=b'\xe9'+struct.pack('<i',(base+FORMAT_RVA)-(stub_va+12));body=ROOT+b'\0'*(stuboff-len(ROOT))+lea+jmp
raw=align(len(b),fa);rawsize=align(len(body),fa);out=bytearray(raw+rawsize);out[:len(b)]=b;out[raw:raw+len(body)]=body
for _,_,call_raw,call_rva in refs:
 out[call_raw]=0xe8;struct.pack_into('<i',out,call_raw+1,stub_va-(base+call_rva+5))
 if base+call_rva+5+struct.unpack_from('<i',out,call_raw+1)[0]!=stub_va:raise SystemExit('call thunk postimage mismatch')
h=table+ns*40;out[h:h+40]=b'\0'*40;out[h:h+8]=b'.spmt\0\0\0';struct.pack_into('<IIII',out,h+8,len(body),newrva,rawsize,raw);struct.pack_into('<I',out,h+36,0x60000020);struct.pack_into('<H',out,pe+6,ns+1);struct.pack_into('<I',out,opt+56,align(newrva+len(body),sa));struct.pack_into('<I',out,opt+64,checksum(out,opt+64))
if out[raw:raw+len(body)]!=body:raise SystemExit('section postimage mismatch')
DST.parent.mkdir(parents=True,exist_ok=False);DST.write_bytes(out)
m={'source_sha256':EXPECTED,'destination':str(DST),'destination_sha256':hashlib.sha256(out).hexdigest().upper(),'root_override':ROOT[:-1].decode(),'format_string_unchanged':FMT.decode(),'format_function_rva':f'0x{FORMAT_RVA:X}','call_sites':[{'lea_rva':f'0x{x[1]:X}','call_rva':f'0x{x[3]:X}'} for x in refs],'thunk':{'section':'.spmt','rva':f'0x{stub_rva:X}','root_string_rva':f'0x{newrva:X}','bytes':body.hex().upper()}}
(DST.parent/'manifest.json').write_text(json.dumps(m,indent=2),encoding='utf-8');print(json.dumps(m))
