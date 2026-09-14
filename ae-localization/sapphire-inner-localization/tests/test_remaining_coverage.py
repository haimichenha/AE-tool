import json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from inventory_lighting import definition_matches_entry
import build_lighting_remaining_titles as builder

class RemainingCoverage(unittest.TestCase):
 def test_exact_and_underscore_aliases(self):
  for definition,entry in [('Glow_Aura','GlowAura'),('Drop_Shadow','DropShadow'),('Z_Glow','ZGlow'),('LightLeak_Autogen','LightLeak'),('Glow_Rings_Autogen','GlowRings')]:
   self.assertTrue(definition_matches_entry(definition,entry))
 def test_no_neighbor_or_dissolve_matches(self):
  for definition,entry in [('Glow_Aura','Glow'),('Dissolve_Glow','Glow'),('Dissolve_Glint_Rainbow','GlintRainbow'),('Glow_Rings_Autogen_Autogen','GlowRings')]:
   self.assertFalse(definition_matches_entry(definition,entry))
 def test_mapping_covers_all_remaining_entries(self):
  m=json.loads((ROOT/'maps/Lighting-remaining16-zh-CN.candidate.json').read_text(encoding='utf-8'))
  self.assertEqual(len(m['entries']),16)
  self.assertEqual(set(m['definitions']),set(builder.SUPPORTED))
  self.assertEqual(sum(builder.SUPPORTED.values()),1093)
  self.assertEqual(len(builder.SUPPORTED),26)
  for entry,meta in m['entries'].items():
   for definition in meta['definitions']:self.assertTrue(definition_matches_entry(definition,entry))
   self.assertEqual(meta['test_match_name'],'R_'+entry)
 def test_parameter_title_limits(self):
  m=json.loads((ROOT/'maps/Lighting-remaining16-zh-CN.candidate.json').read_text(encoding='utf-8'))
  for name,d in m['definitions'].items():
   self.assertEqual(len(d['parameters']),builder.SUPPORTED[name])
   for text in d['parameters'].values():
    self.assertTrue(0<len(text.encode('cp936'))<=31)
    self.assertTrue(any('\u4e00'<=c<='\u9fff' for c in text))

if __name__=='__main__':unittest.main()
