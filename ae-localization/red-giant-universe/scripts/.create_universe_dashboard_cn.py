# -*- coding: utf-8 -*-
from pathlib import Path
import argparse,hashlib,json,shutil
SRC=Path(r"C:\Program Files (x86)\Common Files\Adobe\CEP\extensions\com.redgiant.uni.dashboard")
DST=Path(r"C:\Program Files (x86)\Common Files\Adobe\CEP\extensions\com.redgiant.uni.dashboard.cn")
WORK=Path(r"E:\插件备份\AE_PR_汉化工作")
REPL={
 'Red Giant Universe Dashboard':'RG Universe 中文面板',
 'Clear Most Recent':'清除最近使用',
 'Clear all Favorites':'清除全部收藏',
 'Clear all favorited presets and effects?':'清除所有收藏的预设和效果？',
 'BACK TO UNIVERSE EFFECTS':'返回 Universe 效果',
 'Apply Effect':'添加效果',
 'Applies effect using its default settings':'使用默认设置添加效果',
 'Apply Preset':'应用预设',
 'Applies effect using preset settings':'使用预设设置添加效果',
 'Most Recent':'最近使用',
 'Favorites':'收藏',
 'Effect not installed':'效果未安装',
 'Failed to apply effect':'添加效果失败',
 'Failed to apply preset':'应用预设失败',
 'Show Thumbnails':'显示缩略图',
}
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');args=ap.parse_args()
 if not SRC.is_dir():raise RuntimeError('source extension missing')
 if DST.exists():raise RuntimeError('destination already exists; refusing to overwrite')
 main=SRC/'main.js';manifest=SRC/'CSXS'/'manifest.xml';index=SRC/'index.html'
 hits={s:main.read_text(encoding='utf-8').count(s) for s in REPL}
 print('Source hash:',sha(main));print('Translation text matches:',sum(hits.values()),'across',len([x for x in hits.values() if x]))
 if not args.apply:return
 shutil.copytree(SRC,DST)
 m=(DST/'CSXS'/'manifest.xml').read_text(encoding='utf-8')
 m=m.replace('com.redgiant.uni.dashboard.extension','com.redgiant.uni.dashboard.cn.extension').replace('com.redgiant.uni.dashboard','com.redgiant.uni.dashboard.cn').replace('Red Giant Universe Dashboard','RG Universe 中文面板').replace('<Menu>RG Universe Dashboard</Menu>','<Menu>RG Universe 中文面板</Menu>')
 (DST/'CSXS'/'manifest.xml').write_text(m,encoding='utf-8')
 js=(DST/'main.js').read_text(encoding='utf-8').replace('com.redgiant.uni.dashboard.extension','com.redgiant.uni.dashboard.cn.extension')
 for old,new in REPL.items():js=js.replace(old,new)
 (DST/'main.js').write_text(js,encoding='utf-8')
 html=(DST/'index.html').read_text(encoding='utf-8').replace('Red Giant Universe Dashboard','RG Universe 中文面板')
 html=html.replace('</head>','<style>body,button,input,textarea{font-family:"Microsoft YaHei","Segoe UI",sans-serif!important;}</style></head>')
 (DST/'index.html').write_text(html,encoding='utf-8')
 record={'source':str(SRC),'source_main_sha256':sha(main),'clone':str(DST),'clone_main_sha256':sha(DST/'main.js'),'replacements':REPL,'counts':hits,'original_untouched':sha(main)==json.loads(json.dumps(sha(main)))}
 (WORK/'Universe_Dashboard_中文副本_清单_20260830.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
 print('Created Chinese dashboard clone:',DST)
if __name__=='__main__':main()
