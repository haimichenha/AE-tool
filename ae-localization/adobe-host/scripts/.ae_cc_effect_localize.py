# -*- coding: utf-8 -*-
from pathlib import Path
import argparse, hashlib, json, shutil, struct

TARGET = Path(r"D:\AZBao\PR 22\Ae2022\Adobe After Effects 2022\Support Files\Plug-ins\Effects\CycoreFXHD")
BACKUP = Path(r"E:\插件备份\AE_PR_汉化工作\AE2022_CycoreFXHD_汉化前备份")
MANIFEST = Path(r"E:\插件备份\AE_PR_汉化工作\AE2022_CycoreFXHD_应用清单.json")
NAMES = {
"CC Ball Action":"CC 球体动作", "CC Bender":"CC 弯曲器", "CC Bend It":"CC 弯曲", "CC Blobbylize":"CC 气泡化",
"CC Block Load":"CC 块加载", "CC Bubbles":"CC 气泡", "CC Burn Film":"CC 烧灼胶片", "CC Color Neutralizer":"CC 色彩中和",
"CC Color Offset":"CC 色彩偏移", "CC Composite":"CC 合成", "CC Cross Blur":"CC 交叉模糊", "CC Cylinder":"CC 圆柱",
"CC Drizzle":"CC 细雨", "CC Environment":"CC 环境", "CC Flo Motion":"CC 流动动画", "CC Force Motion Blur":"CC 强制运动模糊",
"CC Glass":"CC 玻璃", "CC Glass Wipe":"CC 玻璃擦除", "CC Glue Gun":"CC 胶枪", "CC Griddler":"CC 网格器",
"CC Grid Wipe":"CC 网格擦除", "CC Hair":"CC 毛发", "CC HexTile":"CC 六角平铺", "CC Image Wipe":"CC 图像擦除",
"CC Jaws":"CC 锯齿", "CC Kaleida":"CC 万花筒", "CC Kernel":"CC 卷积核", "CC Lens":"CC 镜头",
"CC Light Burst 2.5":"CC 光爆2.5", "CC Light Rays":"CC 光线", "CC Light Sweep":"CC 扫光", "CC Light Wipe":"CC 光线擦除",
"CC Line Sweep":"CC 线条扫过", "CC Mr. Mercury":"CC 水银", "CC Mr. Smoothie":"CC 平滑器", "CC Overbrights":"CC 过曝",
"CC Page Turn":"CC 翻页", "CC PS Classic (obsolete)":"CC 粒子系统经典(旧)", "CC Particle Systems II":"CC 粒子系统II",
"CC PS LE Classic (obsolete)":"CC PS LE经典(旧)", "CC Pixel Polly":"CC 像素碎片", "CC Plastic":"CC 塑料",
"CC Power Pin":"CC 强力角点", "CC Particle World":"CC 粒子世界", "CC Radial Blur":"CC 径向模糊",
"CC Radial Fast Blur":"CC 快速径向模糊", "CC Radial ScaleWipe":"CC 径向缩放擦除", "CC Rain":"CC 雨",
"CC Rainfall":"CC 降雨", "CC RepeTile":"CC 重复平铺", "CC Ripple Pulse":"CC 涟漪脉冲", "CC Scale Wipe":"CC 缩放擦除",
"CC Scatterize":"CC 散射化", "CC Simple Wire Removal":"CC 简单擦线", "CC Slant":"CC 倾斜", "CC Smear":"CC 涂抹",
"CC Snow":"CC 雪", "CC Snowfall":"CC 降雪", "CC Sphere":"CC 球面", "CC Split":"CC 分割", "CC Split 2":"CC 分割2",
"CC Spotlight":"CC 聚光灯", "CC Star Burst":"CC 星爆", "CC Threads":"CC 线条", "CC Threshold":"CC 阈值",
"CC Threshold RGB":"CC RGB阈值", "CC Tiler":"CC 平铺", "CC Time Blend":"CC 时间混合", "CC Time Blend FX":"CC 时间混合FX",
"CC Toner":"CC 着色", "CC Twister":"CC 旋转器", "CC Vector Blur":"CC 向量模糊", "CC Vignette":"CC 暗角",
"CC WarpoMatic":"CC 自动扭曲", "CC Wide Time":"CC 宽时间",
}

def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for x in iter(lambda:f.read(1048576),b''):h.update(x)
 return h.hexdigest()

def pipl_strings(data):
 pe=struct.unpack_from('<I',data,0x3c)[0];ns=struct.unpack_from('<H',data,pe+6)[0];op=struct.unpack_from('<H',data,pe+20)[0];sh=pe+24+op;rs=None
 for i in range(ns):
  o=sh+40*i
  if data[o:o+8].split(b'\0')[0]==b'.rsrc': _,va,_,raw=struct.unpack_from('<IIII',data,o+8);rs=(va,raw)
 if not rs:return []
 va,base=rs; out=[]
 def name(x):
  if x&0x80000000:
   o=base+(x&0x7fffffff);n=struct.unpack_from('<H',data,o)[0];return data[o+2:o+2+n*2].decode('utf-16le')
  return x
 def walk(rel=0,path=()):
  o=base+rel;nn,ni=struct.unpack_from('<HH',data,o+12)
  for i in range(nn+ni):
   a,c=struct.unpack_from('<II',data,o+16+i*8);n=name(a)
   if c&0x80000000:walk(c&0x7fffffff,path+(n,))
   elif path and path[0]=='PIPL':
    d=base+c;rv,sz,_,_=struct.unpack_from('<IIII',data,d);fo=base+rv-va;x=data[fo:fo+sz]
    for j in range(len(x)-16):
     if x[j+4:j+8]!=b'eman':continue
     ln=struct.unpack_from('<I',x,j+12)[0]
     if 1<=ln<=512 and j+16+ln<=len(x) and x[j+16]<=ln-1:
      used=x[j+16]; raw=x[j+17:j+17+used]
      try:old=raw.decode('gbk')
      except:old=raw.decode('latin1')
      out.append((old,ln-1,fo+j+16))
 walk();return out

def prepare():
 work=[];skipped=[]
 for p in sorted(TARGET.glob('*.aex')):
  raw=p.read_bytes()
  for old,cap,start in pipl_strings(raw):
   new=NAMES.get(old)
   if not new:continue
   encoded=new.encode('gbk')
   if len(encoded)>cap:skipped.append((p.name,old,new,cap));continue
   work.append((p,raw,old,new,cap,start))
 return work,skipped

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');args=ap.parse_args()
 work,skipped=prepare();print(f'可写入 CC 效果名称：{len(work)}；容量不足跳过：{len(skipped)}')
 for s in skipped:print('SKIP',s)
 if not args.apply:return
 manifest=[]
 for p,raw,old,new,cap,start in work:
  dest=BACKUP/p.name;dest.parent.mkdir(parents=True,exist_ok=True)
  if not dest.exists():shutil.copy2(p,dest)
  out=bytearray(raw);enc=new.encode('gbk');out[start]=len(enc);out[start+1:start+1+cap]=enc+b'\0'*(cap-len(enc))
  before=sha(p);p.write_bytes(out);after=sha(p)
  manifest.append({'file':p.name,'from':old,'to':new,'backup':str(dest),'sha256_before':before,'sha256_after':after})
 MANIFEST.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
 print(f'已备份并写入 CC 效果：{len(manifest)}；备份：{BACKUP}')
if __name__=='__main__':main()
