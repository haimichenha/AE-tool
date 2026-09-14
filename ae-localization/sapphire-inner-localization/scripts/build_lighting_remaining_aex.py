"""Build sixteen version-pinned lighting test entries, keeping original match names in formal entries untouched."""
import argparse,hashlib,json,struct
from pathlib import Path
import pefile

SUPPORTED={'DropShadow': {'source_file': 'S_DropShadow.aex', 'source_sha256': 'DE97CF11CCACA271BED7F1E8AC52624BEE9C299D6373F865C9D00A5B7CD29192', 'display_name': 'S_投影和阴影副本', 'test_match_name': 'R_DropShadow', 'definitions': ['Drop_Shadow']}, 'GlintRainbow': {'source_file': 'S_GlintRainbow.aex', 'source_sha256': 'AD3C29AE2D92451268C762A7A6EEC4BE743B304493A22020812710F6DD23B59C', 'display_name': 'S_彩虹闪烁副本', 'test_match_name': 'R_GlintRainbow', 'definitions': ['Glint_Rainbow']}, 'GlowAura': {'source_file': 'S_GlowAura.aex', 'source_sha256': 'C6C8C74FBBAD3A31A04FC6A753114AD5308230482CFE99A1CF06D25102BE41C0', 'display_name': 'S_环线辉光副本', 'test_match_name': 'R_GlowAura', 'definitions': ['Glow_Aura', 'Glow_Aura_Autogen']}, 'GlowDarks': {'source_file': 'S_GlowDarks.aex', 'source_sha256': '3A54FFEE979D372D2891A2F002A7A89FE3050FB58F04DDD7CB9811EA74F010D1', 'display_name': 'S_暗调辉光副本', 'test_match_name': 'R_GlowDarks', 'definitions': ['Glow_Darks', 'Glow_Darks_Autogen']}, 'GlowDist': {'source_file': 'S_GlowDist.aex', 'source_sha256': '57886289D812A4397CA5CF295316AAFADC3FF9F9269196EB93127C652E7A118E', 'display_name': 'S_区域辉光副本', 'test_match_name': 'R_GlowDist', 'definitions': ['Glow_Dist', 'Glow_Dist_Autogen']}, 'GlowEdges': {'source_file': 'S_GlowEdges.aex', 'source_sha256': 'DA2E2212447095EB73397273513ADCF8929A44C32B35DE4FC35BB6E43463221D', 'display_name': 'S_边缘辉光副本', 'test_match_name': 'R_GlowEdges', 'definitions': ['Glow_Edges', 'Glow_Edges_Autogen']}, 'GlowNoise': {'source_file': 'S_GlowNoise.aex', 'source_sha256': '29A1E89433F664DA7B2604954F593D0CC370BC45B878F5004DE72F493BFA92CD', 'display_name': 'S_噪波辉光副本', 'test_match_name': 'R_GlowNoise', 'definitions': ['Glow_Noise', 'Glow_Noise_Autogen']}, 'GlowOrthicon': {'source_file': 'S_GlowOrthicon.aex', 'source_sha256': 'D948468B12AE3778EEE5A88F165A62FBBE97C4851FFA5AAD56827F0ADCE63F61', 'display_name': 'S_辉光增强对比副本', 'test_match_name': 'R_GlowOrthicon', 'definitions': ['Glow_Orthicon', 'Glow_Orthicon_Autogen']}, 'GlowRainbow': {'source_file': 'S_GlowRainbow.aex', 'source_sha256': '9104B6FF30E70F81B2D8BEF40667356569ADB9EAAF227F4CCF7EEA8F19553867', 'display_name': 'S_彩虹辉光副本', 'test_match_name': 'R_GlowRainbow', 'definitions': ['Glow_Rainbow', 'Glow_Rainbow_Autogen']}, 'GlowRings': {'source_file': 'S_GlowRings.aex', 'source_sha256': 'FAE47CEF8687541048280656117E96AF25642BE59C697E79C31A351557C2A418', 'display_name': 'S_光环辉光副本', 'test_match_name': 'R_GlowRings', 'definitions': ['Glow_Rings', 'Glow_Rings_Autogen']}, 'LensFlare': {'source_file': 'S_LensFlare.aex', 'source_sha256': '818795B62140BC7AE5E5EAB23149FC516173D3A69A67805CA4CE1807D506F085', 'display_name': 'S_镜头光晕副本', 'test_match_name': 'R_LensFlare', 'definitions': ['LensFlare']}, 'LensFlareAutoTrack': {'source_file': 'S_LensFlareAutoTrack.aex', 'source_sha256': '815A7CC3FB3967F2A2DDB4636FBEE9CB076A430AAD2D3687601BDBD738B14092', 'display_name': 'S_镜头光晕自动跟踪副本', 'test_match_name': 'R_LensFlareAutoTrack', 'definitions': ['LensFlareAutoTrack']}, 'LightLeak': {'source_file': 'S_LightLeak.aex', 'source_sha256': '1FBBD1F73C8B3040C60AC7A0671882395977B7930128B4BBF71C84C72B29F49A', 'display_name': 'S_漏光效果副本', 'test_match_name': 'R_LightLeak', 'definitions': ['LightLeak', 'LightLeak_Autogen']}, 'SpotLight': {'source_file': 'S_SpotLight.aex', 'source_sha256': 'D1E96774AAE3628DCBA1D5D65BE9CF435A904948C880C744042CB072CEAF6FCC', 'display_name': 'S_聚光灯副本', 'test_match_name': 'R_SpotLight', 'definitions': ['SpotLight', 'SpotLight_Autogen']}, 'UltraGlow': {'source_file': 'S_UltraGlow.aex', 'source_sha256': 'A4038AF2A2D04A420B37B0C8EC78ABCDF2E7C6951539D8CB4514838A6F45AFF3', 'display_name': 'S_极致辉光副本', 'test_match_name': 'R_UltraGlow', 'definitions': ['UltraGlow']}, 'ZGlow': {'source_file': 'S_ZGlow.aex', 'source_sha256': 'C3A04683A3D7CE1090A03C90A78CD722D694CCBEB5D68221952FF9F44A719FCD', 'display_name': 'S_Z辉光副本', 'test_match_name': 'R_ZGlow', 'definitions': ['Z_Glow']}}
OLD_ROOT=b'c:/Program Files/BorisFX/Sapphire 2024 Adobe'

def sha(b):return hashlib.sha256(b).hexdigest().upper()
def align(v,a):return (v+a-1)//a*a

def build(source,output,runtime,effect):
 if effect not in SUPPORTED:raise ValueError("unsupported effect")
 entry=SUPPORTED[effect];SOURCE_SHA=entry["source_sha256"];DISPLAY=entry["display_name"];ORIGINAL=("S_"+effect).encode("ascii");MATCH=entry["test_match_name"].encode("ascii")
 source=Path(source).resolve();output=Path(output).resolve();runtime=Path(runtime).resolve()
 if output.exists() or source.parent==output.parent:raise ValueError('new isolated output required')
 if runtime==Path(r'D:\tmp\saprt\l3dao') or Path(r'D:\tmp\saprt') not in runtime.parents:raise ValueError('new runtime below saprt required')
 if not (runtime/'lib64/sapphire_ae.dll').is_file():raise ValueError('runtime not prepared')
 if sha((runtime/'lib64/sapphire_ae.dll').read_bytes())!='5141659F6C7CEB78D3F2C2A5B4F2B27D83C222C56D7FE65E3A531DC182376BC4':raise ValueError('lighting candidate core hash mismatch')
 root=str(runtime).replace('\\','/').encode('ascii','strict')
 if len(root)>len(OLD_ROOT):raise ValueError('runtime root too long')
 b=source.read_bytes()
 if sha(b)!=SOURCE_SHA:raise ValueError('unsupported lighting AEX baseline')
 pe=pefile.PE(data=b,fast_load=True);pe.parse_data_directories(directories=[2]);entries=[]
 for typ in pe.DIRECTORY_ENTRY_RESOURCE.entries:
  if str(typ.name).upper()=='PIPL':
   for name in typ.directory.entries:
    for lang in name.directory.entries:entries.append(lang.data.struct)
 if len(entries)!=1:raise ValueError('unexpected PiPL count')
 rd=entries[0];res=pe.get_data(rd.OffsetToData,rd.Size);edits=[]
 for tag,new in [(b'eman',DISPLAY.encode('cp936')),(b'ANMe',MATCH)]:
  needle=b'MIB8'+tag
  if res.count(needle)!=1:raise ValueError('ambiguous property')
  pos=res.index(needle)+16;size=struct.unpack_from('<I',res,pos-4)[0]
  if tag==b'ANMe' and res[pos+1:pos+1+res[pos]]!=ORIGINAL:raise ValueError('original match name not S_lighting')
  newsize=align(1+len(new),4);edits.append((pos-4,4+size,struct.pack('<I',newsize)+(bytes([len(new)])+new).ljust(newsize,b'\0')))
 payload=bytearray(res)
 for pos,size,new in sorted(edits,reverse=True):payload[pos:pos+size]=new
 header=pe.sections[-1].get_file_offset()+40
 if header+40>min(s.PointerToRawData for s in pe.sections) or any(b[header:header+40]):raise ValueError('no unused section header')
 va=align(max(s.VirtualAddress+max(s.Misc_VirtualSize,s.SizeOfRawData) for s in pe.sections),pe.OPTIONAL_HEADER.SectionAlignment);raw=align(len(b),pe.OPTIONAL_HEADER.FileAlignment);rs=align(len(payload),pe.OPTIONAL_HEADER.FileAlignment)
 out=bytearray(b);out.extend(b'\0'*(raw+rs-len(out)));out[raw:raw+len(payload)]=payload;changes=[]
 out[header:header+40]=struct.pack('<8sIIIIIIHHI',b'.lightcn',len(payload),va,rs,raw,0,0,0,0,0x40000040);changes.append((header,40))
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
 for tag,new in [(b'eman',DISPLAY.encode('cp936')),(b'ANMe',MATCH)]:
  pos=v.index(b'MIB8'+tag)+16
  if v[pos+1:pos+1+v[pos]]!=new:raise ValueError('resource readback failed')
 output.parent.mkdir(parents=True,exist_ok=True)
 with output.open('xb') as f:f.write(out)
 report={'source_sha256':SOURCE_SHA,'output_sha256':sha(out),'display_name':DISPLAY,'test_match_name':MATCH.decode('ascii'),'original_match_name':ORIGINAL.decode('ascii'),'runtime_root':str(runtime),'native_code_changed':False,'original_installed_entry_changed':False,'runtime_validation':'pending'}
 output.with_suffix('.manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');return report

if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--source',required=True);a.add_argument('--output',required=True);a.add_argument('--runtime',required=True);a.add_argument('--effect',required=True,choices=SUPPORTED);p=a.parse_args();print(json.dumps(build(p.source,p.output,p.runtime,p.effect)))
