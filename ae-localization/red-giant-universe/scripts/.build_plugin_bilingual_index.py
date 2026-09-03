# -*- coding: utf-8 -*-
from pathlib import Path
from html import escape
import json
work=Path(r"E:\插件备份\AE_PR_汉化工作")
media=json.loads((work/'应用清单.json').read_text(encoding='utf-8'))
cc=json.loads((work/'AE2022_CycoreFXHD_应用清单.json').read_text(encoding='utf-8'))
rows=[]
for item in media:
    for change in item.get('changes',[]):
        if change.get('field')!='eman': continue
        f=item['file']; parts=f.split('\\')
        suite=parts[0] if parts else 'MediaCore'
        if suite=='BorisFX' and len(parts)>1: suite='BorisFX / '+parts[1]
        safety='保留原始标识' if suite in ('Red Giant Universe','Red Giant VFX') or suite.startswith('BorisFX / Sapphire') else '可作为中文参考'
        rows.append((suite,change['to'],change['from'],f,safety))
for item in cc:
    rows.append(('AE 内置 CC 效果',item['to'],item['from'],item['file'],'可作为中文参考'))
rows.sort(key=lambda r:(r[0],r[1]))
trs='\n'.join('<tr data-search="{q}"><td>{suite}</td><td class="cn">{cn}</td><td class="en">{orig}</td><td>{safe}</td><td><button data-copy="{orig_attr}">复制原名</button></td></tr>'.format(q=escape(' '.join(r),quote=True).lower(),suite=escape(r[0]),cn=escape(r[1]),orig=escape(r[2]),safe=escape(r[4]),orig_attr=escape(r[2],quote=True)) for r in rows)
html=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>AE / PR 插件中文索引</title><style>body{{font:14px "Microsoft YaHei",sans-serif;margin:24px;background:#171717;color:#eee}}input{{width:min(720px,95%);padding:10px;font-size:15px}}table{{width:100%;border-collapse:collapse;margin-top:16px}}td,th{{padding:9px;border-bottom:1px solid #333;text-align:left}}th{{color:#82cfff}}.cn{{color:#9be28d;font-weight:bold}}.en{{font-family:Consolas,monospace}}button{{padding:5px 8px}}.note{{color:#ffcc66}}</style><h1>AE / PR 插件中文索引</h1><p class="note">中文用于识别；Dashboard 套件应保持原始英文标识。点击“复制原名”后可在 AE 效果搜索框中粘贴。</p><input id="q" autofocus placeholder="搜索中文、英文、套件或文件名…"><table><thead><tr><th>套件</th><th>中文标注</th><th>原始效果名</th><th>使用方式</th><th></th></tr></thead><tbody>{trs}</tbody></table><script>const q=document.querySelector('#q');q.oninput=()=>document.querySelectorAll('tbody tr').forEach(x=>x.hidden=!x.dataset.search.includes(q.value.toLowerCase()));document.addEventListener('click',e=>{{let v=e.target.dataset.copy;if(v)navigator.clipboard.writeText(v).then(()=>e.target.textContent='已复制');}});</script></html>'''
out=work/'插件中文索引.html';out.write_text(html,encoding='utf-8');print(f'Created {out} with {len(rows)} entries')
