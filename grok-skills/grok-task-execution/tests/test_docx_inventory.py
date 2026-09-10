import importlib.util,json,tempfile,unittest,zipfile
from pathlib import Path
s=importlib.util.spec_from_file_location('docx_inventory',Path(__file__).resolve().parents[1]/'scripts/inspect-docx-sources.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class InventoryTests(unittest.TestCase):
 def test_distinguishes_real_fake_missing_without_content(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);real=root/'source.docx';fake=root/'v47.docx';missing=root/'next.docx'
   with zipfile.ZipFile(real,'w') as z:
    for n in m.REQUIRED:z.writestr(n,'PRIVATE_DOC_CONTENT')
   fake.write_text('# PRIVATE_DOC_CONTENT')
   before={p.name:p.read_bytes() for p in root.iterdir()}
   r=m.inventory(root,missing)
   self.assertEqual(r['valid_sources'],[str(real.resolve())]);self.assertFalse(r['requested_target']['exists'])
   self.assertNotIn('PRIVATE_DOC_CONTENT',json.dumps(r));self.assertEqual(before,{p.name:p.read_bytes() for p in root.iterdir()})
 def test_random_zip_not_word(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'a.docx'
   with zipfile.ZipFile(p,'w') as z:z.writestr('a.txt','x')
   self.assertFalse(m.inspect(p)['docx_package'])
if __name__=='__main__':unittest.main()
