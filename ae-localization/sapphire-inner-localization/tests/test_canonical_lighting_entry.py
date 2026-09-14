from pathlib import Path
import sys,tempfile,unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build_lighting_canonical_entry import PINS,build,field


class CanonicalEntryTests(unittest.TestCase):
    def test_exact_supported_scope(self):
        self.assertEqual(len(PINS),23)
        self.assertIn('S_LensFlare',PINS)
        self.assertIn('S_LensFlareAutoTrack',PINS)
        self.assertNotIn('S_Light3D',PINS)
        self.assertTrue(all(k.startswith('S_') and len(v['source_sha256'])==64 for k,v in PINS.items()))

    def test_wrong_version_or_unsafe_output_does_not_write(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'source'/'S_Glare.aex';source.parent.mkdir();source.write_bytes(b'wrong version')
            out=root/'output'/'S_Glare.aex'
            for runtime in ['relative','D:/x/../y','D:/中文','D:/'+('x'*80),'//server/share/runtime','D:/runtime']:
                with self.subTest(runtime=runtime),self.assertRaises(ValueError):build(source,out,runtime,'S_Glare')
                self.assertFalse(out.exists())
            with self.assertRaises(ValueError):build(source,source.parent/'child'/'x.aex','D:/runtime','S_Glare')
            out.parent.mkdir();out.write_bytes(b'keep')
            with self.assertRaises(ValueError):build(source,out,'D:/runtime','S_Glare')
            self.assertEqual(out.read_bytes(),b'keep')

    def test_resource_field_bounds(self):
        data=b'MIB8ANMe'+b'\0'*8+bytes([7])+b'S_Glare'
        self.assertEqual(field(data,b'ANMe'),'S_Glare')
        for bad in [data+data,data[:-1],b'none']:
            with self.assertRaises(ValueError):field(bad,b'ANMe')


if __name__=='__main__':unittest.main()
