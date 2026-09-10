"""Create an isolated T_Glare AEX with a Chinese native display name; never replace S_Glare."""
import argparse,hashlib,json,struct
from pathlib import Path
import pefile

SOURCE_SHA='E55E0F35DB86F80E0B782A6D51C27A0DB50686D9547ED6A60E071CA6B1A165A6'
OLD_ROOT=b'c:/Program Files/BorisFX/Sapphire 2024 Adobe'

def sha(b):return hashlib.sha256(b).hexdigest().upper()
def align(v,a):return (v+a-1)//a*a

def build(source,output,runtime):
 source=Path(source).resolve();output=Path(output).resolve();runtime=Path(runtime).resolve()
 if output.exists() or source.parent==output.parent:raise ValueError('new isolated output required')
 if runtime==Path(r'D:\tmp\saprt\l3dao') or Path(r'D:\tmp\saprt') not in runtime.parents:raise ValueError('new runtime below saprt required')
 if not (runtime/'lib64/sapphire_ae.dll').is_file():raise ValueError('runtime not prepared')
 if sha((runtime/'lib64/sapphire_ae.dll').read_bytes())!='7F077A162E7DF5A264A05D10BA5BB6D1AC3B9E40647E66EB0D0EF4D2FB82F223':raise ValueError('Glare candidate core hash mismatch')
 root=str(runtime).replace('\\','/').encode('ascii','strict')
 if len(root)>len(OLD_ROOT):raise ValueError('runtime root too long')
 b=source.read_bytes()
 if sha(b)!=SOURCE_SHA:raise ValueError('unsupported Glare AEX baseline')
 pe=pefile.PE(data=b,fast_load=True);pe.parse_data_directories(directories=[2]);entries=[]
 for typ in pe.DIRECTORY_ENTRY_RESOURCE.entries:
  if str(typ.name).upper()=='PIPL':
   for name in typ.directory.entries:
    for lang in name.directory.entries:entries.append(lang.data.struct)
 if len(entries)!=1:raise ValueError('unexpected PiPL count')
 rd=entries[0];res=pe.get_data(rd.OffsetToData,rd.Size);edits=[]
 for tag,new in [(b'eman','S_眩光副本'.encode('cp936')),(b'ANMe',b'T_Glare')]:
  needle=b'MIB8'+tag
  if res.count(needle)!=1:raise ValueError('ambiguous property')
  pos=res.index(needle)+16;size=struct.unpack_from('<I',res,pos-4)[0]
  if tag==b'ANMe' and res[pos+1:pos+1+res[pos]]!=b'S_Glare':raise ValueError('original match name not S_Glare')
  newsize=align(1+len(new),4);edits.append((pos-4,4+size,struct.pack('<I',newsize)+(bytes([len(new)])+new).ljust(newsize,b'\0')))
 payload=bytearray(res)
 for pos,size,new in sorted(edits,reverse=True):payload[pos:pos+size]=new
 header=pe.sections[-1].get_file_offset()+40
 if header+40>min(s.PointerToRawData for s in pe.sections) or any(b[header:header+40]):raise ValueError('no unused section header')
 va=align(max(s.VirtualAddress+max(s.Misc_VirtualSize,s.SizeOfRawData) for s in pe.sections),pe.OPTIONAL_HEADER.SectionAlignment);raw=align(len(b),pe.OPTIONAL_HEADER.FileAlignment);rs=align(len(payload),pe.OPTIONAL_HEADER.FileAlignment)
 out=bytearray(b);out.extend(b'\0'*(raw+rs-len(out)));out[raw:raw+len(payload)]=payload;changes=[]
 out[header:header+40]=struct.pack('<8sIIIIIIHHI',b'.glarcn\0',len(payload),va,rs,raw,0,0,0,0,0x40000040);changes.append((header,40))
 for obj,name,value,fmt in [(pe.FILE_HEADER,'NumberOfSections',pe.FILE_HEADER.NumberOfSections+1,'<H'),(pe.OPTIONAL_HEADER,'SizeOfImage',align(va+len(payload),pe.OPTIONAL_HEADER.SectionAlignment),'<I'),(pe.OPTIONAL_HEADER,'SizeOfInitializedData',pe.OPTIONAL_HEADER.SizeOfInitializedData+rs,'<I')]:
  pos=obj.get_field_absolute_offset(name);struct.pack_into(fmt,out,pos,value);changes.append((pos,struct.calcsize(fmt)))
 pos=rd.get_file_offset();struct.pack_into('<II',out,pos,va,len(payload));changes.append((pos,8))
 if b.count(OLD_ROOT)!=1:raise ValueError('ambiguous hardcoded root')
 pos=b.index(OLD_ROOT);out[pos:pos+len(OLD_ROOT)]=root.ljust(len(OLD_ROOT),b'\0');changes.append((pos,len(OLD_ROOT)))
 check=pe.OPTIONAL_HEADER.get_field_absolute_offset('CheckSum');struct.pack_into('<I',out,check,0);q=pefile.PE(data=bytes(out),fast_load=True);struct.pack_into('<I',out,check,q.generate_checksum());changes.append((check,4))
 reverse=bytearray(out[:len(b)])
 for pos,size in changes:reverse[pos:pos+size]=b[pos:pos+size]
 if reverse!=b:raise ValueError('unexpected original image mutation')
 q=pefile.PE(data=bytes(out),fast_load=True);q.parse_data_directories(directories=[2])
 typ=next(e for e in q.DIRECTORY_ENTRY_RESOURCE.entries if str(e.name).upper()=='PIPL');r=typ.directory.entries[0].directory.entries[0].data.struct;v=q.get_data(r.OffsetToData,r.Size)
 for tag,new in [(b'eman','S_眩光副本'.encode('cp936')),(b'ANMe',b'T_Glare')]:
  pos=v.index(b'MIB8'+tag)+16
  if v[pos+1:pos+1+v[pos]]!=new:raise ValueError('resource readback failed')
 output.parent.mkdir(parents=True,exist_ok=True)
 with output.open('xb') as f:f.write(out)
 report={'source_sha256':SOURCE_SHA,'output_sha256':sha(out),'display_name':'S_眩光副本','test_match_name':'T_Glare','original_match_name':'S_Glare','runtime_root':str(runtime),'native_code_changed':False,'original_installed_entry_changed':False,'runtime_validation':'pending'}
 output.with_suffix('.manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');return report

if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--source',required=True);a.add_argument('--output',required=True);a.add_argument('--runtime',required=True);p=a.parse_args();print(json.dumps(build(p.source,p.output,p.runtime)))
