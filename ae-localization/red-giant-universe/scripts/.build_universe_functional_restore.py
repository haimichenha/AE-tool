# -*- coding: utf-8 -*-
from pathlib import Path
import json
work=Path(r"E:\插件备份\AE_PR_汉化工作")
files=[x['file'] for x in json.loads((work/'应用清单.json').read_text(encoding='utf-8')) if x['file'].startswith('Red Giant Universe\\')]
assert len(files)==97, len(files)
out=Path(r"E:\课程文件\四六级\抱回研研舞\.restore_universe_functional.py")
source='''# -*- coding: utf-8 -*-
from pathlib import Path
import argparse,hashlib,json,shutil
ROOT=Path(r"C:\\Program Files\\Adobe\\Common\\Plug-ins\\7.0\\MediaCore")
BASE=Path(r"E:\\插件备份\\AE_PR_汉化工作\\MediaCore_汉化前备份_20260830")
SNAP=Path(r"E:\\插件备份\\AE_PR_汉化工作\\Universe_全中文模式快照_20260830")
WORK=Path(r"E:\\插件备份\\AE_PR_汉化工作")
PANEL=Path(r"E:\\课程文件\\四六级\\抱回研研舞\\中文效果助手.jsx")
PANEL_DEST=Path(r"D:\\AZBao\\PR 22\\Ae2022\\Adobe After Effects 2022\\Support Files\\Scripts\\ScriptUI Panels\\宇宙插件中文助手.jsx")
FILES=__FILES__
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');args=ap.parse_args()
 print('Universe functional-mode candidates:',len(FILES))
 for rel in FILES:
  if not (ROOT/rel).is_file() or not (BASE/rel).is_file():raise RuntimeError('missing: '+rel)
 if not PANEL.is_file():raise RuntimeError('panel source missing')
 if not args.apply:return
 rows=[]
 for rel in FILES:
  target=ROOT/rel;baseline=BASE/rel;snap=SNAP/rel;snap.parent.mkdir(parents=True,exist_ok=True)
  current=sha(target)
  if snap.exists():
   if sha(snap)!=current:raise RuntimeError('snapshot collision differs: '+rel)
  else:shutil.copy2(target,snap)
  expected=sha(baseline);shutil.copy2(baseline,target)
  actual=sha(target)
  if actual!=expected:raise RuntimeError('restore mismatch: '+rel)
  rows.append({'file':str(rel),'chinese_sha':current,'functional_sha':actual,'snapshot':str(snap)})
 if PANEL_DEST.exists():
  prior=WORK/'ScriptUI面板备份_20260830'/PANEL_DEST.name;prior.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(PANEL_DEST,prior)
 shutil.copy2(PANEL,PANEL_DEST)
 (WORK/'Universe_功能模式_恢复清单_20260830.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
 (WORK/'Universe_当前模式.json').write_text(json.dumps({'mode':'functional_original_ids','files':len(rows),'dashboard':'supported','chinese_panel':str(PANEL_DEST)},ensure_ascii=False,indent=2),encoding='utf-8')
 print('Restored functional Universe:',len(rows),'Installed panel:',PANEL_DEST)
if __name__=='__main__':main()
'''.replace('__FILES__',json.dumps(files,ensure_ascii=False,indent=1))
out.write_text(source,encoding='utf-8')
print('Generated functional restore script:',out,'files:',len(files))
