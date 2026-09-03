# -*- coding: utf-8 -*-
from pathlib import Path
import json,struct
root=Path(r"C:\Program Files\Adobe\Common\Plug-ins\7.0\MediaCore")
manifest=Path(r"E:\插件备份\AE_PR_汉化工作\应用清单.json")
out=Path(r"E:\课程文件\四六级\抱回研研舞\中文效果助手.jsx")
catmap={'Blur':'模糊','CrumplePop':'风格化','Distort':'扭曲','Generators':'发生器','Glow':'发光','Motion_Graphics':'运动图形','Noise':'发生器','Stylize':'风格化','Text':'字幕','Transitions':'转场','Utilities':'实用程序'}
def fields(p):
 b=p.read_bytes();pe=struct.unpack_from('<I',b,0x3c)[0];ns=struct.unpack_from('<H',b,pe+6)[0];op=struct.unpack_from('<H',b,pe+20)[0];sh=pe+24+op;rs=None
 for i in range(ns):
  o=sh+40*i
  if b[o:o+8].split(b'\0')[0]==b'.rsrc':_,va,_,raw=struct.unpack_from('<IIII',b,o+8);rs=(va,raw)
 if not rs:return {}
 va,base=rs;out={}
 def nm(x):
  if x&0x80000000:
   o=base+(x&0x7fffffff);n=struct.unpack_from('<H',b,o)[0];return b[o+2:o+2+n*2].decode('utf-16le')
  return x
 def walk(rel=0,path=()):
  o=base+rel;nn,ni=struct.unpack_from('<HH',b,o+12)
  for i in range(nn+ni):
   a,c=struct.unpack_from('<II',b,o+16+i*8);n=nm(a)
   if c&0x80000000:walk(c&0x7fffffff,path+(n,))
   elif path and path[0]=='PIPL':
    d=base+c;rv,sz,_,_=struct.unpack_from('<IIII',b,d);fo=base+rv-va;x=b[fo:fo+sz]
    for j in range(len(x)-16):
     key=x[j+4:j+8]
     if key not in (b'ANMe',):continue
     ln=struct.unpack_from('<I',x,j+12)[0]
     if 1<=ln<=512 and j+16+ln<=len(x) and x[j+16]<=ln-1:
      raw=x[j+17:j+17+x[j+16]]
      try:out[key.decode()]=raw.decode('gbk')
      except:out[key.decode()]=raw.decode('latin1')
 walk();return out
entries=[]
for item in json.loads(manifest.read_text(encoding='utf-8')):
 f=item['file']
 if not f.startswith('Red Giant Universe\\'):continue
 changes=[c for c in item['changes'] if c['field']=='eman']
 if not changes:continue
 c=changes[0];match=fields(root/f).get('ANMe')
 if not match:raise RuntimeError('missing ANMe: '+f)
 name=Path(f).stem
 family=name.replace('Universe_','').split('_AE_Fx')[0]
 cat=next((v for k,v in catmap.items() if family.startswith(k+'_') or family==k),'宇宙')
 entries.append({'category':cat,'cn':c['to'].replace('uni.',''),'en':c['from'],'match':match})
entries.sort(key=lambda x:(x['category'],x['cn']))
data=json.dumps(entries,ensure_ascii=False,indent=2)
js=r'''#target aftereffects
#targetengine "UniverseChineseAssistant"

(function (thisObj) {
    var effects = __DATA__;
    var visible = [];
    function buildUI(host) {
        var panel = (host instanceof Panel) ? host : new Window("palette", "宇宙插件中文助手", undefined, {resizeable:true});
        panel.orientation = "column"; panel.alignChildren = ["fill", "top"]; panel.margins = 12;
        var search = panel.add("edittext", undefined, ""); search.characters = 36; search.helpTip = "按中文、英文或分类搜索";
        var group = panel.add("dropdownlist", undefined, ["全部"]);
        var categories = {}; var i;
        for (i=0; i<effects.length; i++) categories[effects[i].category] = true;
        for (var key in categories) group.add("item", key);
        group.selection = 0;
        var list = panel.add("listbox", undefined, [], {multiselect:false}); list.preferredSize = [530, 380];
        var status = panel.add("statictext", undefined, "选择中文效果后，添加到当前合成的所有选中图层。", {multiline:true});
        var add = panel.add("button", undefined, "添加效果");
        function rebuild() {
            var q = search.text.toLowerCase(), cat = group.selection ? group.selection.text : "全部";
            visible = []; list.removeAll();
            for (var j=0; j<effects.length; j++) {
                var e=effects[j], text=e.category+" · "+e.cn+"  ["+e.en+"]";
                if ((cat==="全部" || e.category===cat) && (q==="" || text.toLowerCase().indexOf(q)!==-1)) {
                    visible.push(e); list.add("item", text);
                }
            }
            if (list.items.length) list.selection=0;
        }
        search.onChanging=rebuild; group.onChange=rebuild;
        add.onClick=function () {
            if (!list.selection) { alert("请先选择效果。"); return; }
            var comp=app.project.activeItem;
            if (!(comp instanceof CompItem)) { alert("请先打开一个合成。"); return; }
            var layers=comp.selectedLayers;
            if (!layers || layers.length===0) { alert("请先选择一个或多个图层。"); return; }
            var e=visible[list.selection.index], ok=0, failed=[];
            app.beginUndoGroup("宇宙插件中文助手：添加效果");
            try {
                for (var k=0; k<layers.length; k++) {
                    try { var fx=layers[k].property("ADBE Effect Parade").addProperty(e.match); if (fx) ok++; else failed.push(layers[k].name); }
                    catch(err) { failed.push(layers[k].name); }
                }
            } finally { app.endUndoGroup(); }
            status.text = ok>0 ? "已添加："+e.cn+"（"+e.en+"），图层数："+ok : "添加失败："+e.en+"。";
            if (failed.length) alert("部分图层未能添加："+failed.join(", "));
        };
        panel.onResizing=panel.onResize=function(){this.layout.resize();}; rebuild(); return panel;
    }
    var ui=buildUI(thisObj); if (ui instanceof Window) {ui.center();ui.show();}
})(this);
'''.replace('__DATA__',data)
out.write_text(js,encoding='utf-8-sig')
print('Generated',out,'entries:',len(entries))
