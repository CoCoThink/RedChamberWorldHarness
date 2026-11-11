"""Exercise the actual executable-scene package in a disposable repository clone."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

from rcwh.assets import AssetError
from rcwh.candidate_reviews import canonical_bytes
from rcwh.generation.records import binding
from rcwh.generation.scene_projection import rule_bindings
from rcwh.generation.session import prepare_request, verify_prepared_request
from rcwh.io import load_data

PACKAGE = 'data/writing/packages/ch86-scene-projection-pilot-v3.json'


def verify(root):
    cases = []
    with tempfile.TemporaryDirectory(prefix='rcwh-scene-projection-') as temporary:
        clone = Path(temporary) / 'repo'
        subprocess.run(['git', 'clone', '--quiet', '--shared', str(root), str(clone)], check=True)
        # Explicit overlay before commit; implementation always comes from the
        # host import, whose actual source hashes are recorded below.
        package = load_data(root / PACKAGE)
        for path in (PACKAGE, package['world'][0]['path']):
            (clone / path).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root / path, clone / path)
        packet = prepare_request(clone, package_path=PACKAGE, chapter=86, renderer_version=2)
        carriers = [r for r in packet['inputs'] if r['path'].startswith(
            ('data/world/m3_', 'data/objects/', 'data/knowledge/'))]
        if carriers:
            raise ValueError('scene projection retained full runtime carriers')
        scene = packet['task']['scenes'][0]
        if (scene['entry']['values']['object.medicine_bowl_86.temperature'] != 'warm'
                or scene['entry']['knowledge']['checkpoint'] != 'ENTRY'
                or scene['knowledge_checkpoints']['K86-DEATH-OCCURS']['states']['zijuan']['knows']
                   == scene['entry']['knowledge']['states']['zijuan']['knows']):
            raise ValueError('real scene entry leaked a later checkpoint')
        specifications = [
            ('unrelated_object', 'data/objects/m4.json', False),
            ('future_object_transition', 'data/objects/m4.json', False),
            ('new_prefix_object_transition', 'data/objects/m4.json', True),
            ('legacy_state', 'data/objects/medicine_bowl.yaml', True),
            ('unrelated_knowledge_scene', 'data/knowledge/v03_slice2.json', False),
            ('new_prefix_knowledge_event', 'data/knowledge/v03_slice2.json', True),
            ('selected_fact_definition', 'data/knowledge/v03_slice2.json', True),
            ('new_same_chapter_scene', 'data/scenes/projection_new.json', True),
        ]
        for case, relative, stale in specifications:
            path = clone / relative; original = path.read_bytes() if path.exists() else None
            data = load_data(path) if original is not None else {}
            if case == 'unrelated_object': data['objects'][0]['name'] = 'unrelated changed name'
            elif case in {'future_object_transition', 'new_prefix_object_transition'}:
                data['transitions'].append({'id': 'PROJECTION_MUTATION', 'object_id': 'OBJ-MEDICINE-BOWL-86',
                    'chapter': 87 if case == 'future_object_transition' else 85, 'sequence': 999,
                    'from': {}, 'to': {'holder':'zijuan','location':'S02',
                                      'status':'CONTAINS_UNFINISHED_MEDICINE','temperature':'UNKNOWN'}})
            elif case == 'legacy_state': data['state']['temperature'] = 'UNKNOWN'
            elif case == 'unrelated_knowledge_scene':
                next(s for s in data['scenes'] if s['chapter'] == 89)['events'][-1]['updates'] = []
            elif case == 'new_prefix_knowledge_event':
                next(s for s in data['scenes'] if s['chapter'] == 86)['events'].append(
                    {'id':'PROJECTION_MUTATION','sequence':5,'updates':[]})
            elif case == 'selected_fact_definition':
                next(f for f in data['facts'] if f['id']=='daiyu_death_exact_moment')['label']='changed definition'
            else: data = {'id':'projection_new','chapter':86,'participants':['baoyu']}
            path.write_bytes(canonical_bytes(data))
            rejection = None
            try:
                verify_prepared_request(clone, packet)
            except (ValueError, AssetError, KeyError) as exc:
                rejection = str(exc)
            finally:
                if original is None: path.unlink()
                else: path.write_bytes(original)
            if stale != bool(rejection):
                raise ValueError(f'unexpected scene package outcome: {case}: {rejection}')
            cases.append({'case':case, 'result':'STALE' if rejection else 'EXACT_REQUEST_PRESERVED',
                          'reason':rejection})
        verify_prepared_request(clone, packet)
    return {'status':'PASS', 'scope':'REAL_SCENE_PACKAGE_WITH_HOST_CODE_AND_WORKTREE_MATERIAL',
            'package':binding(root, PACKAGE), 'implementation':rule_bindings(),
            'request_sha256':packet['request_sha256'], 'request_bytes':len(canonical_bytes(packet['request'])),
            'raw_runtime_bindings':carriers, 'cases':cases, 'authority_effect':'NONE', 'semantic_replay':'NOT_CHECKED'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    print(json.dumps(verify(args.root.resolve()), ensure_ascii=False, indent=2))
