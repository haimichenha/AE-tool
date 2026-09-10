"""Bounded structural DOCX check. Does not prove appearance or document semantics."""
import argparse
import json
from pathlib import Path
import zipfile
import xml.etree.ElementTree as ET

W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'

def check(path):
    try:
        with zipfile.ZipFile(path) as z:
            infos=z.infolist();names=[i.filename for i in infos]
            if len(names)!=len(set(names)):raise ValueError('duplicate ZIP entries')
            if sum(i.file_size for i in infos)>100*1024*1024:raise ValueError('package exceeds structural-check size bound')
            required={'[Content_Types].xml','_rels/.rels','word/document.xml'}
            if not required<=set(names):raise ValueError('missing required DOCX package parts')
            if z.testzip() is not None:raise ValueError('ZIP CRC failure')
            roots={}
            for name in required:
                data=z.read(name)
                if b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():raise ValueError('DTD/entity declarations not supported')
                roots[name]=ET.fromstring(data)
            doc=roots['word/document.xml']
            if doc.tag!='{'+W+'}document' or doc.find('{'+W+'}body') is None:raise ValueError('missing WordprocessingML document/body')
            if roots['[Content_Types].xml'].tag!='{http://schemas.openxmlformats.org/package/2006/content-types}Types':raise ValueError('invalid content-types root')
            if roots['_rels/.rels'].tag!='{http://schemas.openxmlformats.org/package/2006/relationships}Relationships':raise ValueError('invalid package relationships root')
        return {'structure_passed':True,'scope':'ZIP/CRC/required XML structure only','layout_verified':False,'requested_edit_verified':False}
    except (OSError,ValueError,RuntimeError,zipfile.BadZipFile,ET.ParseError) as e:
        return {'structure_passed':False,'reason':str(e),'layout_verified':False,'requested_edit_verified':False}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('file',type=Path);a=p.parse_args()
    r=check(a.file);print(json.dumps(r));raise SystemExit(0 if r['structure_passed'] else 2)
