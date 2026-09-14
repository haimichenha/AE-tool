import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import build_preset_button_captions as m

class CaptionGuards(unittest.TestCase):
 def test_wrong_version_cannot_write(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);source=r/'source.dll';source.write_bytes(b'wrong version');out=r/'out/x.dll'
   with self.assertRaises(ValueError):m.build(source,out)
   self.assertFalse(out.exists())
 def test_existing_output_untouched(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'keep.dll';p.write_bytes(b'keep')
   with self.assertRaises(ValueError):m.build(Path(d)/'missing/source.dll',p)
   self.assertEqual(p.read_bytes(),b'keep')
 def test_source_folder_guard(self):
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(ValueError):m.build(Path(d)/'source.dll',Path(d)/'out.dll')
 def test_only_confirmed_right_caption_sites(self):
  self.assertEqual({x[0] for x in m.SITES},{0xD93D65,0xD93CD2})
  self.assertEqual(len(m.SITES),2)
  self.assertIn(0xDD101B,m.PROTECTED)
  for site,*_ in m.SITES:
   for protected in m.PROTECTED:self.assertFalse(protected<=site<protected+32)
 def test_no_internal_string_replacement_map(self):
  self.assertEqual({x[2] for x in m.SITES},{'Load Preset','Save Preset'})
  for _,_,en,zh,reg in m.SITES:
   self.assertEqual(en.count('%s'),zh.count('%s'))
   self.assertLessEqual(len(zh.encode('cp936')),31)
   self.assertEqual(reg,'rsi')
 def test_three_exact_supported_baselines(self):
  self.assertEqual(set(m.PINS),{'glare01','lights01','rem16'})
  self.assertTrue(all(len(h)==64 for h in m.PINS.values()))

if __name__=='__main__':unittest.main()
