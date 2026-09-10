import importlib.util
from pathlib import Path
import tempfile
import unittest
import zipfile
s=importlib.util.spec_from_file_location('doccheck',Path(__file__).resolve().parents[1]/'scripts/verify-docx.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class DocxTests(unittest.TestCase):
    def test_markdown_not_docx(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'fake.docx';p.write_text('# fake')
            self.assertFalse(m.check(p)['structure_passed'])
    def test_zip_without_word_parts_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'fake.docx'
            with zipfile.ZipFile(p,'w') as z:z.writestr('readme.txt','not Word')
            self.assertFalse(m.check(p)['structure_passed'])
    def test_minimal_structure_not_claimed_visual_pass(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'minimal.docx'
            with zipfile.ZipFile(p,'w') as z:
                z.writestr('[Content_Types].xml','<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>')
                z.writestr('_rels/.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>')
                z.writestr('word/document.xml','<w:document xmlns:w="'+m.W+'"><w:body/></w:document>')
            r=m.check(p);self.assertTrue(r['structure_passed']);self.assertFalse(r['layout_verified'])
if __name__=='__main__':unittest.main()
