"""Verify actual chapter-86 lossless transport and explicit byte reservations."""
import argparse
import json
from pathlib import Path

from rcwh.candidate_reviews import canonical_bytes, digest
from rcwh.generation.prompt_view import admission, expand
from rcwh.generation.records import binding
from rcwh.generation.session import prepare_request, verify_frozen_request, verify_prepared_request

PACKAGE = 'data/writing/packages/ch86-scene-projection-pilot-v2.json'
LIMITS = {'version':1, 'max_context_bytes':350000, 'overhead_reserve_bytes':32768, 'output_reserve_bytes':24000}


def verify(root):
    legacy = prepare_request(root, package_path=PACKAGE, chapter=86, renderer_version=2)
    packet = prepare_request(root, package_path=PACKAGE, chapter=86, renderer_version=2,
                             prompt_view_version=1, context_limits=LIMITS)
    verify_prepared_request(root, packet); verify_frozen_request(root, packet)
    raw_task = canonical_bytes(legacy['task'])
    if canonical_bytes(packet['task']) != raw_task or canonical_bytes(expand(packet['prompt_view']['payload'])) != raw_task:
        raise ValueError('real shared view changed canonical task information')
    old_size, new_size = (len(canonical_bytes(p['request'])) for p in (legacy, packet))
    if new_size >= old_size:
        raise ValueError('actual shared request is not smaller')
    old_admission = admission(legacy['request'], LIMITS)
    if old_admission['status'] != 'FAIL' or packet['byte_admission']['status'] != 'PASS':
        raise ValueError('explicit byte budget did not distinguish full and shared transport')
    tight = {**LIMITS, 'max_context_bytes':packet['byte_admission']['reserved_total_bytes']-1}
    rejection = None
    try:
        prepare_request(root, package_path=PACKAGE, chapter=86, renderer_version=2,
                        prompt_view_version=1, context_limits=tight)
    except ValueError as exc:
        rejection = str(exc)
    if not rejection or 'context byte budget' not in rejection:
        raise ValueError('one-byte reservation overflow was not explicitly rejected')
    return {'status':'PASS', 'scope':'REAL_REQUEST_LOSSLESS_VIEW_AND_BYTE_RESERVATIONS',
            'package':binding(root, PACKAGE), 'task_sha256':digest(raw_task),
            'default_request_sha256':legacy['request_sha256'], 'shared_request_sha256':packet['request_sha256'],
            'default_request_bytes':old_size, 'shared_request_bytes':new_size, 'saved_request_bytes':old_size-new_size,
            'shared_values':len(packet['prompt_view']['payload']['shared']),
            'bindings':len(packet['prompt_view']['payload']['bindings']), 'full_task_retained':True,
            'default_under_same_limits':old_admission, 'shared_admission':packet['byte_admission'],
            'one_byte_overflow':{'result':'REJECTED','reason':rejection},
            'implementation':[binding(root,p) for p in ['src/rcwh/generation/prompt_view.py',
                'src/rcwh/generation/session.py','src/rcwh/generation/lineage.py',
                'src/rcwh/application/write.py','schemas/session_author_run.schema.json',
                'data/writing/prompts/shared-values-v1.md']],
            'token_capacity_status':'NOT_MEASURED', 'authority_effect':'NONE'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    print(json.dumps(verify(args.root.resolve()),ensure_ascii=False,indent=2))
