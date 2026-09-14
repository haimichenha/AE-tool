"""Independent readback of emitted PE, definition pointers and executable sections."""
import argparse,hashlib,json,re,struct,sys
from pathlib import Path
import pefile

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--project',type=Path,default=Path('D:/tmp/AE-tool/ae-localization/sapphire-inner-localization'))
parser.add_argument('--work',type=Path,required=True)
parser.add_argument('--source',type=Path,default=Path('D:/tmp/saprt/l3dao/lib64/sapphire_ae.dll'))
args=parser.parse_args()
ROOT=args.project
sys.path.insert(0,str(ROOT/'scripts'))
from new_light3d_bulk_trial import parse
from build_lighting_remaining_titles import segments

work=args.work.resolve()
source=args.source
original=source.read_bytes()
candidate=(work/'build-a/sapphire_ae.dll').read_bytes()
replica=(work/'build-b/sapphire_ae.dll').read_bytes()
sha=lambda b:hashlib.sha256(b).hexdigest().upper()
assert sha(original)=='410C69A61BEC964322550ECC8662D60E454C1984175E2850B4244B02C31A7B91'
assert candidate==replica
manifest=json.loads((work/'build-a/sapphire_ae.manifest.json').read_text(encoding='utf-8'))
mapping=json.loads((work/'Lighting-remaining16-zh-CN.candidate.json').read_text(encoding='utf-8'))
oldpe=pefile.PE(data=original,fast_load=True)
newpe=pefile.PE(data=candidate,fast_load=True)
assert newpe.OPTIONAL_HEADER.CheckSum==newpe.generate_checksum()
code=[]
for section in oldpe.sections:
    if section.Characteristics & 0x20000000:
        start=section.PointerToRawData;end=start+section.SizeOfRawData
        assert original[start:end]==candidate[start:end]
        code.append(section.Name.rstrip(b'\0').decode())
assert code
added=newpe.sections[-1]
assert added.Characteristics==0x40000040  # initialized read-only data, not executable
rows=[]
for record in manifest['definitions']:
    name=record['definition']
    ptr=struct.unpack_from('<Q',candidate,record['pointer_offset'])[0]
    offset=newpe.get_offset_from_rva(ptr-newpe.OPTIONAL_HEADER.ImageBase)
    assert added.PointerToRawData<=offset<added.PointerToRawData+added.SizeOfRawData
    _,end=parse(candidate,offset);new=candidate[offset:end]
    start=record['original_offset'];_,oldend=parse(original,start);old=original[start:oldend]
    oldparts=segments(old,name);newparts=segments(new,name)
    assert [k for k,_ in oldparts]==[k for k,_ in newparts]
    for key,nodes in newparts:
        titles=[]
        for node in nodes:
            if node.kind=='list':
                for i,child in enumerate(node.children[:-1]):
                    if child.atom(new)==b'title':titles.append(node.children[i+1].atom(new))
        assert titles==[b'"'+mapping['definitions'][name]['parameters'][key].encode('cp936')+b'"']
    # Remove only the inserted title syntax, then compare the entire definition.
    restored=re.sub(rb' \( title "[^"\r\n]*" \)',b'',new)
    restored=re.sub(rb' title "[^"\r\n]*"',b'',restored)
    assert restored==old
    rows.append({'definition':name,'titles':len(newparts),'non_title_bytes_identical':True,
                 'relocated_pointer_readback':True})
report={'date':'2026-09-11','source_sha256':sha(original),'candidate_sha256':sha(candidate),
        'candidate_path':str(work/'build-a/sapphire_ae.dll'),
        'repeat_build_identical':True,'checksum_valid':True,'unchanged_executable_sections':code,
        'new_section_read_only_non_executable':True,'definitions':rows,
        'title_count':sum(r['titles'] for r in rows),'parity':'static title-only invariants verified',
        'deployed':False,'runtime_validation':'not run','all_ui_translated':False,
        'pending':['AE load/render comparison','buttons, groups and popup display labels','related editor UI']}
out=work/'remaining16-static-20260911.json'
out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
