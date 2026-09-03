# -*- coding: utf-8 -*-
from pathlib import Path
import argparse, hashlib, json, shutil
ROOT=Path(r"C:\Program Files\Adobe\Common\Plug-ins\7.0\MediaCore")
ARCHIVE=Path(r"E:\插件备份\AE_PR_汉化工作\MediaCore_清理归档_20260830")
MANIFEST=Path(r"E:\插件备份\AE_PR_汉化工作\MediaCore_清理清单_20260830.json")
DUPLICATES={
 Path(r"UltraPix bianma\CmptoJ2KExport.prm"):Path(r"UltraPix\CmptoJ2KExport.prm"),
 Path(r"UltraPix bianma\CmptoJ2KImport.prm"):Path(r"UltraPix\CmptoJ2KImport.prm"),
}
INSTALLERS=[
 Path(r"zMatte-4.0v6.CE.exe"),
 Path(r"Digieffects\Digieffects-Suite-3.0.2-CE.exe"),
 Path(r"UltraPix bianma\UltraPix 1.0.6 CE.exe"),
 Path(r"YuYan\RELens1AE-1.5.0-windows-installer.exe"),
]
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def planned():
 rows=[]
 for rel,canonical in DUPLICATES.items():
  src=ROOT/rel;keep=ROOT/canonical
  if not(src.is_file() and keep.is_file()):raise RuntimeError(f'Missing duplicate pair: {rel}')
  if sha(src)!=sha(keep):raise RuntimeError(f'Hash mismatch; refusing duplicate cleanup: {rel}')
  rows.append((rel,'exact duplicate',canonical))
 for rel in INSTALLERS:
  src=ROOT/rel
  if not src.is_file():raise RuntimeError(f'Missing explicit installer candidate: {rel}')
  if src.suffix.lower()!='.exe' or not any(x in src.name.lower() for x in ('installer','suite','zmatte','ultrapix')):
   raise RuntimeError(f'Installer safeguard rejected: {rel}')
  rows.append((rel,'installer artifact',None))
 return rows
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');args=ap.parse_args();rows=planned()
 print(f'保守清理候选：{len(rows)} 个文件（2 个精确重复插件 + 4 个安装包）')
 for rel,why,keep in rows: print(f'{why}: {rel}' + (f' | retained: {keep}' if keep else ''))
 if not args.apply:return
 output=[]
 for rel,why,keep in rows:
  src=ROOT/rel;dest=ARCHIVE/rel;dest.parent.mkdir(parents=True,exist_ok=True);source_hash=sha(src)
  if dest.exists():
   if sha(dest)!=source_hash:raise RuntimeError(f'Archive collision has different content: {dest}')
  else:shutil.copy2(src,dest)
  if sha(dest)!=source_hash:raise RuntimeError(f'Archive verification failed: {dest}')
  src.unlink()
  output.append({'moved_from':str(src),'archived_to':str(dest),'reason':why,'retained_canonical':str(ROOT/keep) if keep else None,'sha256':source_hash})
 MANIFEST.write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf-8')
 print(f'已归档并从 MediaCore 移除：{len(output)}；归档：{ARCHIVE}')
if __name__=='__main__':main()
