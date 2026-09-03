from pathlib import Path
import ctypes,hashlib,json,struct
SRC=Path(r'C:\Program Files\BorisFX\Sapphire 2024 Adobe\lib64\BorisFX.Sapphire.mocha.em64t\mocha4bcc.dll');DST=Path(r'D:\tmp\sapphire-patch-lab\trials\mocha_menu_batch_utf8\mocha4bcc.dll');EXPECTED='969E1724C74FB4A661043E626FE92E8C29F062038C8D1BF647C99051F23DC029'
P=[(0x356e320,'Essentials','基础'),(0x356e330,'Track motion options','跟踪运动选项'),(0x356e360,'Link to track','关联跟踪'),(0x356e370,'Surface','表面'),(0x356e378,'Show surface\n(tracking data)','显示表面\n(跟踪数据)'),(0x356e398,'Align surface','对齐表面'),(0x356e3a8,'Show grid','网格'),(0x356e3b8,'Exports','导出'),(0x356e3c0,'Export Tracking Data','导出跟踪数据'),(0x356e3d8,'Export Shape Data','导出形状'),(0x356fe10,'Layer Properties','图层属性'),(0x33deee9,'Show All Overlays','显示叠加层'),(0x33d9fe0,'Hide All Controls','隐藏控件'),(0x33da040,'Canvas Color...','画布颜色...'),(0x33da108,'Viewer Preferences','查看器首选项'),(0x3555278,'Proxies','代理'),(0x35552c0,'Spline tangents','样条切线'),(0x33dadf0,'Undo/Redo','撤重'),(0x35568b8,'Workspace','工作区'),(0x3538388,'View controls','查看控件'),(0x3573520,'Project Notes','项目备注'),(0x3570a18,'Edge Properties','边缘属性'),(0x3571058,'Overlay Colors','叠加颜色'),(0x35765d8,'Keyframe Controls','关键帧控件')]
if DST.exists():raise SystemExit('refusing to overwrite')
b=bytearray(SRC.read_bytes());
if hashlib.sha256(b).hexdigest().upper()!=EXPECTED:raise SystemExit('source hash mismatch')
R=[]
for off,old,new in P:
 o=old.encode('ascii');n=new.encode('utf-8')
 if len(n)>len(o):raise SystemExit(f'too long: {old}')
 if b[off:off+len(o)]!=o or b[off+len(o)]!=0:raise SystemExit(f'preimage mismatch: {old} @ {off:#x}')
 b[off:off+len(o)+1]=n+b'\0'*(len(o)+1-len(n));R.append({'offset':f'0x{off:X}','english':old,'chinese':new,'preimage_bytes':len(o),'replacement_bytes':len(n)})
pe=struct.unpack_from('<I',b,0x3c)[0];ckoff=pe+24+64;DST.parent.mkdir(parents=True,exist_ok=False);DST.write_bytes(b);h=ctypes.c_uint32();c=ctypes.c_uint32();rc=ctypes.windll.imagehlp.MapFileAndCheckSumW(str(DST),ctypes.byref(h),ctypes.byref(c));
if rc:raise SystemExit(f'checksum failed {rc}')
with DST.open('r+b') as f:f.seek(ckoff);f.write(struct.pack('<I',c.value))
post=DST.read_bytes();
for r in R:
 off=int(r['offset'],16);n=r['chinese'].encode();L=r['preimage_bytes']
 if post[off:off+len(n)]!=n or any(post[off+len(n):off+L+1]):raise SystemExit('postimage mismatch')
m={'source_sha256':EXPECTED,'destination':str(DST),'destination_sha256':hashlib.sha256(post).hexdigest().upper(),'encoding':'UTF-8','patched_ui_string_count':len(R),'patched_ui_strings':R};(DST.parent/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(m,ensure_ascii=False))
