from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
import capstone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from build_empty_args_guard import branch, guard_code, EMPTY, RESUME, build


class GuardTests(unittest.TestCase):
    def test_relative_branches_both_directions(self):
        for source, target in [(0x3bbf79, 0x41ed000), (0x41ed00a, EMPTY), (0x41ed010, RESUME)]:
            for opcode in (b'\xe9', b'\x0f\x84'):
                data = branch(opcode, source, target)
                self.assertEqual(source + len(data) + struct.unpack_from('<i', data, len(opcode))[0], target)

    def test_actual_generated_instruction_paths(self):
        for rva in (0x41ed000, 0x4209000, 0x4300000):
            data = guard_code(rva); self.assertEqual(len(data), 21)
            cs = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64); cs.detail = True
            instructions = {i.address: i for i in cs.disasm(data, rva)}
            self.assertEqual([i.mnemonic for i in instructions.values()], ['mov', 'xor', 'test', 'je', 'jmp'])
            for i in instructions.values():
                self.assertFalse(any(o.type == capstone.x86.X86_OP_MEM for o in i.operands))
            for pointer in (0, 1, 8, 0x7ffca0000000, 0xffffffffffffffff):
                regs = {'rax': pointer, 'rdi': 42, 'rsi': 43, 'rsp': 44, 'rcx': 45}; old = dict(regs)
                ip, zf = rva, False
                for _ in range(6):
                    if ip not in instructions: break
                    i = instructions[ip]; nxt = ip + i.size
                    if i.mnemonic == 'mov':
                        self.assertEqual(i.op_str, 'edi, 1'); regs['rdi'] = 1
                    elif i.mnemonic == 'xor':
                        self.assertEqual(i.op_str, 'esi, esi'); regs['rsi'] = 0; zf = True
                    elif i.mnemonic == 'test':
                        self.assertEqual(i.op_str, 'rax, rax'); zf = regs['rax'] == 0
                    elif i.mnemonic == 'je' and zf: nxt = i.operands[0].imm
                    elif i.mnemonic == 'jmp': nxt = i.operands[0].imm
                    ip = nxt
                self.assertEqual(ip, EMPTY if pointer == 0 else RESUME)
                self.assertEqual(regs, {**old, 'rdi': 1, 'rsi': 0})

    def test_version_check_survives_optimized_python(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d); source = d / 'bad.dll'; source.write_bytes(b'not a supported vendor image')
            output = d / 'out.dll'
            result = subprocess.run([sys.executable, '-O', str(ROOT / 'scripts/build_empty_args_guard.py'),
                                     '--source', str(source), '--output', str(output), '--version', 'rays09'], capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(b'Unsupported core version', result.stderr)
            self.assertFalse(output.exists())
            output.write_bytes(b'keep')
            with self.assertRaises(ValueError): build(source, output, 'rays09')
            self.assertEqual(output.read_bytes(), b'keep')


if __name__ == '__main__': unittest.main()
