# -*- coding: utf-8 -*-
from pathlib import Path
import argparse,hashlib,json,shutil
WORK=Path(r"E:\插件备份\AE_PR_汉化工作")
MEDIA_ROOT=Path(r"C:\Program Files\Adobe\Common\Plug-ins\7.0\MediaCore")
MEDIA_BASE=WORK/'MediaCore_汉化前备份_20260830'
CC_ROOT=Path(r"D:\AZBao\PR 22\Ae2022\Adobe After Effects 2022\Support Files\Plug-ins\Effects\CycoreFXHD")
CC_BASE=WORK/'AE2022_CycoreFXHD_汉化前备份'
SNAP=WORK/'稳定性回滚前快照_20260830'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def load():
 media=[x['file'] for x in json.loads((WORK/'应用清单.json').read_text(encoding='utf-8'))]
 cc=[x['file'] for x in json.loads((WORK/'AE2022_CycoreFXHD_应用清单.json').read_text(encoding='utf-8'))]
 if len(media)!=400 or len(cc)!=75:raise RuntimeError(f'unexpected manifest counts: {len(media)}, {len(cc)}')
 return media,cc
def restore(items,root,base,snap_root,label):
 rows=[]
 for rel in items:
  rel=Path(rel); target=root/rel; source=base/rel; snap=snap_root/rel
  if not target.is_file() or not source.is_file():raise RuntimeError(f'missing {label}: {rel}')
  before=sha(target); snap.parent.mkdir(parents=True,exist_ok=True)
  if snap.exists():
   if sha(snap)!=before:raise RuntimeError(f'snapshot collision differs: {label}/{rel}')
  else:shutil.copy2(target,snap)
  expected=sha(source);shutil.copy2(source,target)
  actual=sha(target)
  if actual!=expected:raise RuntimeError(f'hash mismatch after restore: {label}/{rel}')
  rows.append({'file':str(rel),'before_sha':before,'baseline_sha':actual,'snapshot':str(snap)})
 return rows
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');args=ap.parse_args();media,cc=load()
 print(f'Stability baseline candidates: MediaCore={len(media)}, CC={len(cc)}')
 if not args.apply:return
 m=restore(media,MEDIA_ROOT,MEDIA_BASE,SNAP/'MediaCore','MediaCore')
 c=restore(cc,CC_ROOT,CC_BASE,SNAP/'CycoreFXHD','CycoreFXHD')
 (WORK/'稳定性回滚清单_20260830.json').write_text(json.dumps({'mediacore':m,'cc':c},ensure_ascii=False,indent=2),encoding='utf-8')
 (WORK/'Universe_当前模式.json').write_text(json.dumps({'mode':'stability_baseline','mediacore_restored':len(m),'cc_restored':len(c),'next':'restart AE and validate stability before non-binary localization'},ensure_ascii=False,indent=2),encoding='utf-8')
 print(f'Restored stability baseline: MediaCore={len(m)}, CC={len(c)}')
if __name__=='__main__':main()
