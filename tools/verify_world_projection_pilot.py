"""Real package mutation checks on a disposable clone; no model or prose output."""
from pathlib import Path
import argparse
import json
import shutil
import subprocess
import tempfile

from rcwh.assets import AssetError
from rcwh.candidate_reviews import canonical_bytes, digest
from rcwh.generation.records import binding
from rcwh.generation.session import prepare_request, verify_prepared_request

PACKAGE='data/writing/packages/ch87-world-projection-pilot-v3.json'
BASE='data/writing/packages/ch87-agent-research-v6.json'


def verify(root):
    with tempfile.TemporaryDirectory(prefix='rcwh-world-projection-') as temporary:
        clone=Path(temporary)/'repo'
        subprocess.run(['git','clone','--quiet','--shared',str(root),str(clone)],check=True)
        # Explicit worktree overlay lets local checks run before committing. The
        # report binds host implementation and material; it is not a claim that
        # uncommitted code was present in the clone's HEAD.
        doc=json.loads((root/PACKAGE).read_bytes())
        for path in [PACKAGE,doc['world'][0]['path']]:
            (clone/path).parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(root/path,clone/path)
        packet=prepare_request(clone,package_path=PACKAGE,chapter=87,renderer_version=2)
        raw=[r for r in packet['inputs'] if r['path'].startswith('data/world/m3_')]
        if raw:raise ValueError('projection silently retained whole world dependencies')
        path=clone/'data/world/m3_core.json';original=path.read_bytes()
        outcomes=[]
        for case in ['unrelated_character','related_state','new_related_event','future_event','new_unrelated_event']:
            world=json.loads(original)
            if case=='unrelated_character':
                next(c for c in world['characters'] if c['id']=='xiangling')['name']='unrelated changed name'
            elif case=='related_state':world['baseline']['characters']['baoyu']['body_state']='UNKNOWN'
            else:
                who='xiangling' if case=='new_unrelated_event' else 'baoyu'
                world['events'].append({'id':'PROJECTION_MUTATION','chapter':88 if case=='future_event' else 86,
                    'sequence':999,'effects':[{'set':f'characters.{who}.body_state','value':'UNKNOWN'}]})
            path.write_bytes(canonical_bytes(world))
            rejection=None
            try:verify_prepared_request(clone,packet)
            except (ValueError,AssetError) as exc:rejection=str(exc)
            expected_stale=case in {'related_state','new_related_event'}
            if expected_stale != bool(rejection):raise ValueError(f'unexpected real-package outcome: {case}: {rejection}')
            if rejection and 'STALE_WORLD_PROJECTION' not in rejection:raise ValueError(rejection)
            row={'case':case,'result':'STALE' if rejection else 'EXACT_REQUEST_PRESERVED','reason':rejection}
            if case=='unrelated_character':
                try:prepare_request(clone,package_path=BASE,chapter=87,renderer_version=2)
                except (ValueError,AssetError) as exc:row['legacy_whole_file_control']=str(exc)
                else:raise ValueError('legacy whole-file control unexpectedly ignored carrier change')
            outcomes.append(row);path.write_bytes(original)
        verify_prepared_request(clone,packet)
    return {'status':'PASS','scope':'REAL_PACKAGE_MUTATIONS_WITH_HOST_CODE_AND_WORKTREE_MATERIAL',
        'package':binding(root,PACKAGE),'implementation':[binding(root,p) for p in [
            'src/rcwh/generation/world_projection.py','src/rcwh/generation/render.py','src/rcwh/literary_inputs.py']],
        'request_sha256':packet['request_sha256'],'request_bytes':len(canonical_bytes(packet['request'])),
        'raw_world_bindings':raw,'cases':outcomes,'authority_effect':'NONE','semantic_replay':'NOT_CHECKED'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);a=p.parse_args()
    print(json.dumps(verify(a.root.resolve()),ensure_ascii=False,indent=2))
