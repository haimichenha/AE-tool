import sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import build_lightleak_layout as m

class GroupTests(unittest.TestCase):
 def setUp(self):
  self.d=('(def_effect LightLeak ( Source ) ( rgba_ok ) ( '
   'element1_enable = 1 ( boolean doc_group_name Element1 ) '
   'element2_enable = 0 ( boolean doc_group_name Element2 ) '
   'element3_enable = 0 ( boolean doc_group_name Element3 ) '
   'softness1 = 0.4 ( slider_max 4 title "灯光1柔和度" ) '
   'softness2 = 0.4 ( slider_max 4 title "灯光2柔和度" ) ) ( compute softness1 softness2 ) )').encode('cp936')
  p=patch.dict(m.COUNTS,{'LightLeak':5});p.start();self.addCleanup(p.stop)
 def test_only_metadata_and_length(self):
  out,edits=m.translate(self.d,'LightLeak')
  self.assertEqual(len(out),len(self.d));self.assertEqual(len(edits),2)
  self.assertIn('元素1'.encode('cp936'),out)
  self.assertIn(b'( compute softness1 softness2 )',out)
  restored=bytearray(out)
  for off,old,new,kind,key in edits:restored[off:off+len(old)]=old
  self.assertEqual(restored,self.d)
 def test_doc_group_names_preserved(self):
  out,_=m.translate(self.d,'LightLeak')
  self.assertIn(b'doc_group_name Element1',out)
 def test_title_preimage_guard(self):
  with self.assertRaises(ValueError):m.translate(self.d.replace('灯光1'.encode('cp936'),'其他1'.encode('cp936')),'LightLeak')
 def test_other_definition_refused(self):
  with self.assertRaises(ValueError):m.translate(self.d,'SpotLight')
 def test_double_apply_refused(self):
  out,_=m.translate(self.d,'LightLeak')
  with self.assertRaises(ValueError):m.translate(out,'LightLeak')
 def test_deterministic(self):self.assertEqual(m.translate(self.d,'LightLeak'),m.translate(self.d,'LightLeak'))
 def test_output_guard(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'out.dll';p.write_bytes(b'keep')
   with self.assertRaises(ValueError):m.build(Path(t)/'source/missing.dll',p)
   self.assertEqual(p.read_bytes(),b'keep')
 def test_wrong_version_cannot_write(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'source.dll';p.write_bytes(b'wrong');out=Path(t)/'out/x.dll'
   with self.assertRaises(ValueError):m.build(p,out)
   self.assertFalse(out.exists())

if __name__=='__main__':unittest.main()
