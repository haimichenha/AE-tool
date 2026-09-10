"""Stage a new six-effect lighting runtime locally; never overwrite an existing runtime.
Copies vendor dependency/resources, not factory plugin entries. No deployment.
The inherited Mocha thunk still depends on the recorded l3dao runtime.
"""
import argparse,hashlib,json,shutil
from pathlib import Path
CORE_SHA='3DA5AF307B0B0B15B9B950AD9BB84A0CD33284F8174D52397EF1D97B4EBFCCE3'
FACTORY_SHA='3A01082AD1D1F3189B9929B717BFD384FB5676BB0BC927F9E2141FAF54C07482'
MOCHA_SHA='9141D09D02DD2E303E2BDB6F5BAB21844A441201562A5CE85790489FD0020030'
FOLDERS=['lib64','dialogs','docs','effect-builder','flare-editor','glares','help-dialog','lensflares','luts','mocha-data','ocio','preset-browser','pylib','stamps','star-data']
FILES=['s_config.text','s_filmtypes.text','s_function_list.text','sapphire-app-settings.ini']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()
def stage(core,root,source):
 core=Path(core).resolve();root=Path(root).resolve();source=Path(source).resolve();allowed=Path(r'D:\tmp\saprt').resolve()
 if allowed not in root.parents or root.exists():raise ValueError('new runtime below D:/tmp/saprt required')
 if sha(core)!=CORE_SHA or sha(source/'lib64/sapphire_ae.dll')!=FACTORY_SHA:raise ValueError('core baseline mismatch')
 mocha=allowed/'l3dao/lib64/BorisFX.Sapphire.mocha.em64t/mocha4bcc.dll'
 if sha(mocha)!=MOCHA_SHA:raise ValueError('inherited localized Mocha dependency mismatch')
 entries=[]
 for name in FOLDERS+FILES:
  p=source/name
  if not p.exists():raise ValueError('missing dependency '+name)
  for f in ([p] if p.is_file() else p.rglob('*')):
   if f.is_symlink() or (hasattr(f,'is_junction') and f.is_junction()):raise ValueError('linked dependency not allowed')
   if f.is_file():entries.append(f)
 root.mkdir(parents=True,exist_ok=False)
 records=[]
 for f in entries:
  rel=f.relative_to(source)
  selected=core if str(rel).replace('\\','/')=='lib64/sapphire_ae.dll' else f
  h=sha(selected);out=root/rel;out.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(selected,out)
  if sha(out)!=h:raise ValueError('copy readback failed '+str(rel))
  records.append({'relative_path':str(rel),'sha256':h,'length':out.stat().st_size})
 report={'runtime_root':str(root),'core_sha256':CORE_SHA,'files':records,'localized_mocha_dependency':str(mocha),'localized_mocha_sha256':MOCHA_SHA,'factory_aex_copied':False,'deployed':False,'ae_runtime_test':'pending'}
 (root/'runtime-manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 return {'runtime_root':str(root),'files_copied':len(records),'bytes_copied':sum(x['length'] for x in records),'core_sha256':CORE_SHA,'ae_runtime_test':'pending','external_mocha_root':str(allowed/'l3dao')}
if __name__=='__main__':
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--core',required=True);ap.add_argument('--root',required=True);ap.add_argument('--source-root',default=r'C:\Program Files\BorisFX\Sapphire 2024 Adobe');a=ap.parse_args();print(json.dumps(stage(a.core,a.root,a.source_root)))
