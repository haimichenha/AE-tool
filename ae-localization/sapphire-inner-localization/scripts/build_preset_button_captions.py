"""Version-pinned display-only button pointer split; never replace dispatch strings.

Only two static right-hand preset captions; custom editor formats remain untouched.
Left property labels and every original English comparison string are retained.
"""
import argparse,hashlib,json,struct
from pathlib import Path
import pefile,capstone

PINS={'rem16':'5141659F6C7CEB78D3F2C2A5B4F2B27D83C222C56D7FE65E3A531DC182376BC4',
      'lights01':'3DA5AF307B0B0B15B9B950AD9BB84A0CD33284F8174D52397EF1D97B4EBFCCE3',
      'glare01':'7F077A162E7DF5A264A05D10BA5BB6D1AC3B9E40647E66EB0D0EF4D2FB82F223'}
# Specific UI pointer consumers; not the similarly-named property/dispatch users.
SITES=[(0xD93D65,0x1886C60,'Load Preset','载入预设','rsi'),
       (0xD93CD2,0x1886C54,'Save Preset','保存预设','rsi')]
# Explicitly protected: property-name construction and command comparisons.
PROTECTED=[0xDD101B,0xD6D91E,0xD6D93A,0xD92F2B,0xD93D39,0xDAF7C3,
           0xD93010,0xD93CA6,0xDAF61F,0xD95DBE,0xD99578,0xDD1039]
sha=lambda b:hashlib.sha256(b).hexdigest().upper()
align=lambda n,a:(n+a-1)//a*a

def build(source,output):
 source=Path(source).resolve();output=Path(output).resolve()
 if output.exists() or output.parent==source.parent:raise ValueError('new isolated output required')
 b=source.read_bytes()
 if sha(b) not in PINS.values():raise ValueError('unrecognized baseline')
 pe=pefile.PE(data=b,fast_load=True);base=pe.OPTIONAL_HEADER.ImageBase
 md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_64)
 header=pe.sections[-1].get_file_offset()+40
 if header+40>min(s.PointerToRawData for s in pe.sections) or any(b[header:header+40]):raise ValueError('section header capacity')
 va=align(max(s.VirtualAddress+max(s.Misc_VirtualSize,s.SizeOfRawData) for s in pe.sections),pe.OPTIONAL_HEADER.SectionAlignment)
 raw=align(len(b),pe.OPTIONAL_HEADER.FileAlignment);payload=bytearray();records=[]
 for rva,target,en,zh,reg in SITES:
  oldoff=pe.get_offset_from_rva(target)
  if b[oldoff:oldoff+len(en)+1]!=en.encode()+b'\0':raise ValueError('caption preimage')
  off=pe.get_offset_from_rva(rva);ins=list(md.disasm(b[off:off+7],base+rva))
  if len(ins)!=1 or ins[0].size!=7 or ins[0].mnemonic!='lea' or not ins[0].op_str.startswith(reg+', [rip '):raise ValueError('instruction preimage')
  if rva+7+struct.unpack_from('<i',b,off+3)[0]!=target:raise ValueError('original target mismatch')
  if zh.count('%s')!=en.count('%s'):raise ValueError('format placeholder mismatch')
  encoded=zh.encode('cp936')
  if len(encoded)>31 or any(x in zh for x in '\0\n\r'):raise ValueError('invalid caption')
  newrva=va+len(payload);payload.extend(encoded+b'\0')
  records.append({'rva':rva,'offset':off,'original_target_rva':target,'new_target_rva':newrva,'source':en,'translation':zh})
 rs=align(len(payload),pe.OPTIONAL_HEADER.FileAlignment);out=bytearray(b);out.extend(b'\0'*(raw+rs-len(out)));out[raw:raw+len(payload)]=payload
 changes=[]
 for row in records:
  pos=row['offset']+3;struct.pack_into('<i',out,pos,row['new_target_rva']-row['rva']-7);changes.append((pos,4))
 out[header:header+40]=struct.pack('<8sIIIIIIHHI',b'.spbtn\0\0',len(payload),va,rs,raw,0,0,0,0,0x40000040);changes.append((header,40))
 for obj,name,val,fmt in [(pe.FILE_HEADER,'NumberOfSections',pe.FILE_HEADER.NumberOfSections+1,'<H'),
   (pe.OPTIONAL_HEADER,'SizeOfImage',align(va+len(payload),pe.OPTIONAL_HEADER.SectionAlignment),'<I'),
   (pe.OPTIONAL_HEADER,'SizeOfInitializedData',pe.OPTIONAL_HEADER.SizeOfInitializedData+rs,'<I')]:
  pos=obj.get_field_absolute_offset(name);struct.pack_into(fmt,out,pos,val);changes.append((pos,struct.calcsize(fmt)))
 check=pe.OPTIONAL_HEADER.get_field_absolute_offset('CheckSum');struct.pack_into('<I',out,check,0)
 struct.pack_into('<I',out,check,pefile.PE(data=bytes(out),fast_load=True).generate_checksum());changes.append((check,4))
 restored=bytearray(out[:len(b)])
 for pos,size in changes:restored[pos:pos+size]=b[pos:pos+size]
 if restored!=b:raise ValueError('non-allowlisted change')
 for rva in PROTECTED:
  off=pe.get_offset_from_rva(rva)
  if out[off:off+32]!=b[off:off+32]:raise ValueError('protected name/dispatch code changed')
 for _,target,en,_,_ in SITES:
  off=pe.get_offset_from_rva(target)
  if out[off:off+len(en)+1]!=en.encode()+b'\0':raise ValueError('original string changed')
 q=pefile.PE(data=bytes(out),fast_load=True)
 for row in records:
  instruction=out[row['offset']:row['offset']+7]
  target=row['rva']+7+struct.unpack_from('<i',instruction,3)[0]
  wanted=row['translation'].encode('cp936')+b'\0'
  if q.get_data(target,len(wanted))!=wanted:raise ValueError('new caption target readback')
 if not q.verify_checksum():raise ValueError('PE checksum')
 output.parent.mkdir(parents=True,exist_ok=True)
 with output.open('xb') as f:f.write(out)
 if sha(output.read_bytes())!=sha(out):raise ValueError('disk readback')
 report={'source_sha256':sha(b),'output_sha256':sha(out),'sites':records,'original_dispatch_strings_preserved':True,
  'protected_code_ranges_unchanged':len(PROTECTED),'code_change_scope':'two RIP-relative LEA displacement operands only; opcodes, registers, calls, branches and all other existing bytes preserved except PE metadata',
  'left_property_names_unchanged':True,'enum_tokens_unchanged':True,'all_ui_translated':False,'runtime_validation':'pending'}
 output.with_suffix('.manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');return report

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--output',required=True);a=p.parse_args();print(json.dumps(build(a.source,a.output),ensure_ascii=False))
