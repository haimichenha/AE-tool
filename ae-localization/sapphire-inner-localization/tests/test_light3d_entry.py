import struct
import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from build_light3d_chinese_entry import property_field


class EntryFields(unittest.TestCase):
    def test_pascal_field(self):
        b = b'MIB8eman' + b'\0'*4 + struct.pack('<I',12) + b'\x09S_Light3D\0\0'
        self.assertEqual(property_field(b,b'eman'), (16,12))

    def test_duplicate_refused(self):
        b = b'MIB8eman' + b'\0'*4 + struct.pack('<I',12) + b'\x09S_Light3D\0\0'
        with self.assertRaises(ValueError): property_field(b+b,b'eman')

    def test_missing_refused(self):
        with self.assertRaises(ValueError): property_field(b'not a resource',b'eman')

    def test_invalid_pascal_length_refused(self):
        b = b'MIB8eman' + b'\0'*4 + struct.pack('<I',12) + b'\x0cS_Light3D\0\0'
        with self.assertRaises(ValueError): property_field(b,b'eman')
