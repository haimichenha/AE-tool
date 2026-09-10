"""Read-only DOCX inventory. Reports structure metadata, never document text."""
import argparse,json,zipfile
from pathlib import Path
REQUIRED={'[Content_Types].xml','_rels/.rels','word/document.xml'}
def inspect(path):
    path=Path(path)
    out={'path':str(path.resolve()),'exists':path.is_file(),'docx_package':False}
    if not out['exists']:return out
    out['bytes']=path.stat().st_size
    try:
        with zipfile.ZipFile(path) as z:
            names=z.namelist()
            out['docx_package']=REQUIRED.issubset(names) and len(names)==len(set(names))
            out['scope']='required ZIP members only; no content/layout acceptance'
    except (OSError,zipfile.BadZipFile):out['reason']='not a DOCX ZIP package; do not use as a Word source'
    return out
def inventory(root,target=None):
    root=Path(root).resolve()
    if not root.is_dir():raise ValueError('existing document directory required')
    paths=sorted(root.glob('*.docx'))
    if len(paths)>100:raise ValueError('more than 100 files; specify a narrower directory')
    entries=[inspect(p) for p in paths]
    return {'root':str(root),'requested_target':inspect(target) if target else None,'files':entries,'valid_sources':[x['path'] for x in entries if x['docx_package']],'next':'Choose the genuine user-designated source; modify a new copy using a document tool. Never recreate missing version names from stale memory or rename Markdown to DOCX.','modified_files':[]}
def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--root',required=True);ap.add_argument('--target');a=ap.parse_args()
    print(json.dumps(inventory(a.root,a.target),ensure_ascii=True))
if __name__=='__main__':main()
