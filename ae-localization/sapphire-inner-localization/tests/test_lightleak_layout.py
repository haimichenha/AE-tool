import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import build_lightleak_layout as m

class LayoutTests(unittest.TestCase):
 def setUp(self):
  groups=' '.join('( :modify a ( group_start '+g+' ) ) ( :modify b ( group_end '+g+' ) )' for g in ['Glow','Element1','Element2','Element3'])
  self.first=('(layout_effect ( LightLeak LightLeak_Autogen ) ( Source ) ( ) ( '+groups+' ( :extra opacity = 1 ( popup All_Opaque Normal As_Premult ) ) ').encode()
  self.tail=b') )'
 def test_display_only_tokens(self):
  out=m.update_layout(self.first,self.tail)
  self.assertEqual(len(out),len(self.first))
  for value in m.GROUPS.values():self.assertEqual(out.count(value.encode('cp936')),2)
  self.assertIn(b'popup All_Opaque Normal As_Premult',out)
  self.assertIn('title "不透明度"'.encode('cp936'),out)
 def test_pair_mismatch_refused(self):
  with self.assertRaises(ValueError):m.update_layout(self.first.replace(b'group_end Element2',b'group_end Element9'),self.tail)
 def test_wrong_owner_refused(self):
  with self.assertRaises(ValueError):m.update_layout(self.first.replace(b'LightLeak LightLeak_Autogen',b'Other Other_Autogen'),self.tail)
 def test_changed_enum_refused(self):
  with self.assertRaises(ValueError):m.update_layout(self.first.replace(b'Normal As_Premult',b'NewMode As_Premult'),self.tail)
 def test_double_apply_refused(self):
  out=m.update_layout(self.first,self.tail)
  with self.assertRaises(ValueError):m.update_layout(out,self.tail)

if __name__=='__main__':unittest.main()
