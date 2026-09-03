from pathlib import Path
import ctypes, hashlib, json, struct
SRC=Path(r'C:\Program Files\BorisFX\Sapphire 2024 Adobe\lib64\BorisFX.Sapphire.mocha.em64t\mocha4bcc.dll')
DST=Path(r'D:\tmp\sapphire-patch-lab\trials\mocha_leftpanel_utf8\mocha4bcc.dll')
EXPECTED='969E1724C74FB4A661043E626FE92E8C29F062038C8D1BF647C99051F23DC029'
PATCHES=[(0x356e320,'Essentials','基础'),(0x356e330,'Track motion options','跟踪运动选项'),(0x356e360,'Link to track','关联跟踪'),(0x356e370,'Surface','表面'),(0x356e378,'Show surface\n(tracking data)','显示表面\n(跟踪数据)'),(0x356e398,'Align surface','对齐表面'),(0x356e3a8,'Show grid','网格'),(0x356e3b8,'Exports','导出'),(0x356e3c0,'Export Tracking Data','导出跟踪数据'),(0x356e3d8,'Export Shape Data','导出形状'),(0x356fe10,'Layer Properties','图层属性')]
if DST.exists():raise SystemExit('refusing to overwrite')
b=bytearray(SRC.read_bytes())
if hashlib.sha256(b).hexdigest().upper()!=EXPECTED:raise SystemExit('source hash mismatch')
records=[]
for off,old,new in PATCHES:
 oldb=old.encode('ascii');newb=new.encode('utf-8')
 if len(newb)>len(oldb):raise SystemExit(f'{old}: replacement too long')
 if b[off:off+len(oldb)]!=oldb or b[off+len(oldb)]!=0:raise SystemExit(f'{old}: preimage mismatch at {off:#x}')
 b[off:off+len(oldb)+1]=newb+b'\0'*(len(oldb)+1-len(newb));records.append({'offset':f'0x{off:X}','english':old,'chinese':new,'preimage_bytes':len(oldb),'replacement_bytes':len(newb)})
pe=struct.unpack_from('<I',b,0x3c)[0];checksum_offset=pe+24+64
DST.parent.mkdir(parents=True,exist_ok=False);DST.write_bytes(b);head=ctypes.c_uint32();chk=ctypes.c_uint32();rc=ctypes.windll.imagehlp.MapFileAndCheckSumW(str(DST),ctypes.byref(head),ctypes.byref(chk));
if rc:raise SystemExit(f'checksum failed: {rc}')
with DST.open('r+b') as f:f.seek(checksum_offset);f.write(struct.pack('<I',chk.value))
post=DST.read_bytes()
for r in records:
 off=int(r['offset'],16);newb=r['chinese'].encode('utf-8');oldlen=r['preimage_bytes']
 if post[off:off+len(newb)]!=newb or any(post[off+len(newb):off+oldlen+1]):raise SystemExit('postimage mismatch')
m={'source_sha256':EXPECTED,'destination':str(DST),'destination_sha256':hashlib.sha256(post).hexdigest().upper(),'encoding':'UTF-8','patched_ui_strings':records}
(DST.parent/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(m,ensure_ascii=False))
