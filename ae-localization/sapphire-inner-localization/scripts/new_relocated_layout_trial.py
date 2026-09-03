from __future__ import annotations
import hashlib,json,struct
from pathlib import Path

BASE='3A01082AD1D1F3189B9929B717BFD384FB5676BB0BC927F9E2141FAF54C07482'
SRC=Path(r'D:\tmp\sapphire-patch-lab\sapphire_ae.dll')
DST=Path(r'D:\tmp\sapphire-patch-lab\trials\light3d_layout_ascii\sapphire_ae.dll')

def align(v,a): return (v+a-1)//a*a
def allhits(b,n):
    x=[];i=0
    while 1:
        i=b.find(n,i)
        if i<0:return x
        x.append(i);i+=1
def csum(a,off):
    a[off:off+4]=b'\0'*4;s=0
    for i in range(0,len(a)-1,2):
        s+=(a[i]|a[i+1]<<8);s=(s&0xffff)+(s>>16)
    if len(a)&1:s+=a[-1]
    s=(s&0xffff)+(s>>16);s=(s&0xffff)+(s>>16)
    return (s+len(a))&0xffffffff

if DST.exists(): raise SystemExit(f'refusing to overwrite {DST}')
b=SRC.read_bytes()
if hashlib.sha256(b).hexdigest().upper()!=BASE: raise SystemExit('source hash mismatch')
pe=struct.unpack_from('<I',b,0x3c)[0]; opt=pe+24; nsec=struct.unpack_from('<H',b,pe+6)[0]; opsz=struct.unpack_from('<H',b,pe+20)[0]
if struct.unpack_from('<H',b,opt)[0]!=0x20b:raise SystemExit('not PE32+')
base=struct.unpack_from('<Q',b,opt+24)[0]; sa=struct.unpack_from('<I',b,opt+32)[0]; fa=struct.unpack_from('<I',b,opt+36)[0]; st=opt+opsz
secs=[]
for i in range(nsec):
 o=st+i*40;name=b[o:o+8].split(b'\0')[0].decode();vs,va,rs,rp=struct.unpack_from('<IIII',b,o+8);secs.append((name,vs,va,rs,rp))
if st+(nsec+1)*40>min(x[4] for x in secs):raise SystemExit('no header slot')
prefix=b'(layout_effect ( Light3D Light3D_Autogen )'
hits=allhits(b,prefix)
if len(hits)!=1:raise SystemExit(f'layout hit count {len(hits)}')
oldstart=hits[0];oldend=b.find(b'\0',oldstart);old=b[oldstart:oldend]
oldtoken=b'brightness ambient_bright ( :modify diffuse_bright'
newtoken=b'brightness ( :modify ambient_bright Probe ) ( :modify diffuse_bright'
if len(allhits(old,oldtoken))!=1:raise SystemExit('layout token not unique')
new=old.replace(oldtoken,newtoken)
sec=next(x for x in secs if x[4]<=oldstart<x[4]+x[3]);oldrva=sec[2]+oldstart-sec[4];oldva=base+oldrva
ptrhits=allhits(b,struct.pack('<Q',oldva))
if len(ptrhits)!=1:raise SystemExit(f'layout pointer count {len(ptrhits)}')
ptroff=ptrhits[0]
newrva=align(max(x[2]+max(x[1],x[3]) for x in secs),sa);newva=base+newrva;data=new+b'\0';raw=align(len(b),fa);rawsize=align(len(data),fa)
out=bytearray(raw+rawsize);out[:len(b)]=b;out[raw:raw+len(data)]=data
struct.pack_into('<Q',out,ptroff,newva);h=st+nsec*40;out[h:h+40]=b'\0'*40;out[h:h+8]=b'.splayt\0';struct.pack_into('<IIII',out,h+8,len(data),newrva,rawsize,raw);struct.pack_into('<I',out,h+36,0x40000040);struct.pack_into('<H',out,pe+6,nsec+1);struct.pack_into('<I',out,opt+56,align(newrva+len(data),sa));struct.pack_into('<I',out,opt+64,csum(out,opt+64))
if out[oldstart:oldend]!=old or out[ptroff:ptroff+8]!=struct.pack('<Q',newva):raise SystemExit('postimage mismatch')
DST.parent.mkdir(parents=True,exist_ok=False);DST.write_bytes(out)
m={'source':str(SRC),'source_sha256':BASE,'destination':str(DST),'destination_sha256':hashlib.sha256(out).hexdigest().upper(),'effect':'Light3D','parameter_key':'ambient_bright','layout_transform':'(:modify ambient_bright Probe)','old_layout_file_offset':hex(oldstart),'old_layout_rva':hex(oldrva),'layout_pointer_file_offset':hex(ptroff),'new_layout_rva':hex(newrva),'new_section':{'name':'.splayt','raw_offset':hex(raw),'raw_size':rawsize,'virtual_size':len(data)},'added_layout_bytes':len(new)-len(old),'file_size_before':len(b),'file_size_after':len(out)}
(DST.parent/'manifest.json').write_text(json.dumps(m,indent=2),encoding='utf-8');print(json.dumps(m))
