"""Read-only candidate inventory for UI-bearing DSL modifiers across 25 lighting effects.

This does NOT patch binaries or infer that raw English tokens are visible in AE.
Keeps complete modifier text rather than guessing where popup options stop.
Executed as a read-only inventory against the pinned source; does not establish live UI labels.
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

PIN = '410C69A61BEC964322550ECC8662D60E454C1984175E2850B4244B02C31A7B91'
DEFAULT_PROJECT = Path('D:/tmp/AE-tool/ae-localization/sapphire-inner-localization')


def collect(source, inventory, project):
    sys.path.insert(0, str(project / 'scripts'))
    from new_light3d_bulk_trial import parse
    from build_lighting_batch_titles import segments

    data = source.read_bytes()
    if hashlib.sha256(data).hexdigest().upper() != PIN:
        raise ValueError('Unsupported source: do not remove the version guard')
    baseline = json.loads(inventory.read_text(encoding='utf-8-sig'))
    if baseline.get('analysis_core_sha256') != PIN:
        raise ValueError('Inventory/source version mismatch')
    names = {Path(row['file']).stem.removeprefix('S_') for row in baseline['entries']}
    if len(names) != 25:
        raise ValueError('Expected the complete 25-effect scope')
    result = {name: [] for name in sorted(names)}
    markers = {'popup', 'doc_group_name', 'doc_group', 'glare', 'lens_flare', 'mocha_data'}
    for match in re.finditer(rb'\(def_effect ([A-Za-z0-9_]+)\s', data):
        definition = match.group(1).decode('ascii')
        name = definition.removesuffix('_Autogen').replace('_', '')
        if name not in names:
            continue
        _, end = parse(data, match.start())
        definition_bytes = data[match.start():end]
        records = []
        for key, nodes in segments(definition_bytes, definition):
            for node in nodes:
                if node.kind != 'list':
                    continue
                # Decode tokens only to identify known metadata, not to rewrite them.
                tokens = [child.atom(definition_bytes).decode('ascii', errors='backslashreplace')
                          for child in node.children if child.kind == 'atom']
                found = sorted(markers.intersection(tokens))
                if not found:
                    continue
                raw = node.atom(definition_bytes)
                records.append({
                    'parameter_key': key,
                    'markers': found,
                    'modifier_file_offset': hex(match.start() + node.start),
                    'raw_modifier_cp936': raw.decode('cp936', errors='strict'),
                    'raw_modifier_hex': raw.hex(),
                    'sha256': hashlib.sha256(raw).hexdigest().upper(),
                    'interpretation': 'Static source candidate only; enum boundaries and display consumer require review'
                })
        result[name].append({'definition': definition, 'ui_modifiers': records})
    return {
        'source_sha256': PIN,
        'effects': result,
        'effects_without_matching_definition': [name for name, rows in result.items() if not rows],
        'not_enumerated_here': ['Shared host button call sites', 'External editor UI', 'Host-generated property groups'],
        'installed_files_modified': False,
        'live_ui_coverage_proven': False
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--project', type=Path, default=DEFAULT_PROJECT)
    parser.add_argument('--inventory', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('Refuse to overwrite an existing evidence report')
    inventory = args.inventory or args.project / 'observations/lighting-inventory-20260909.json'
    report = collect(args.source, inventory, args.project)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    print(json.dumps({'effects': len(report['effects']), 'report': str(args.output), 'binary_writes': False}))


if __name__ == '__main__':
    main()
