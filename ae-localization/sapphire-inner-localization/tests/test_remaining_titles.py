import sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import build_lighting_remaining_titles as m
class BatchTitleTests(unittest.TestCase):
 def setUp(self):
  self.patch=patch.dict(m.SUPPORTED,{'Example':2});self.patch.start();self.addCleanup(self.patch.stop)
  self.d=b'(def_effect Example ( Source ) ( rgba_ok ) ( a = 1 ( popup Full Half ) b = 2 ) ( compute a b ) )'
  self.t={'a':'分辨率','b':'亮度'}
 def test_titles_and_original_expression(self):
  out,keys=m.translate(self.d,'Example',self.t)
  self.assertEqual(keys,['a','b']);self.assertIn(b'( compute a b )',out);self.assertIn(b'popup Full Half',out)
  self.assertEqual(out.count(b'title "'),2)
 def test_missing_key(self):
  with self.assertRaises(ValueError):m.translate(self.d,'Example',{'a':'甲'})
 def test_extra_key(self):
  with self.assertRaises(ValueError):m.translate(self.d,'Example',dict(self.t,c='丙'))
 def test_wrong_definition(self):
  with self.assertRaises(ValueError):m.translate(self.d,'Other',self.t)
 def test_quote_refused(self):
  with self.assertRaises(ValueError):m.translate(self.d,'Example',dict(self.t,a='甲"乙'))
 def test_long_refused(self):
  with self.assertRaises(ValueError):m.translate(self.d,'Example',dict(self.t,a='甲'*16))
 def test_unencodable_refused(self):
  with self.assertRaises(UnicodeEncodeError):m.translate(self.d,'Example',dict(self.t,a='\U0001f600'))
 def test_existing_title_refused(self):
  with self.assertRaises(ValueError):m.translate(self.d.replace(b'popup Full Half',b'popup Full Half title "old"'),'Example',self.t)
 def test_bad_count_refused(self):
  with patch.dict(m.SUPPORTED,{'Example':3}):
   with self.assertRaises(ValueError):m.translate(self.d,'Example',self.t)
 def test_deterministic(self):self.assertEqual(m.translate(self.d,'Example',self.t),m.translate(self.d,'Example',self.t))
if __name__=='__main__':unittest.main()
