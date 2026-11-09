"""Prepare or check a bounded, lossless research review partition; no model calls."""
import argparse
import json
from pathlib import Path

from rcwh.assets.paths import repository_path
from rcwh.candidate_reviews import canonical_bytes
from rcwh.generation.records import append_bytes, binding, bound_bytes
from rcwh.generation.scope_audit import assess, bundle, reconstruct
from rcwh.generation.session import EXECUTION_BASIS, verify_frozen_request, verify_prepared_request


def prepare(root, prepared_path, receipt_path, output, **limits):
    prepared_ref, receipt_ref = binding(root, prepared_path), binding(root, receipt_path)
    prepared = json.loads(bound_bytes(root, prepared_ref))
    verify_prepared_request(root, prepared)
    receipt = json.loads(bound_bytes(root, receipt_ref))
    expected = {'kind':'SESSION_PAYLOAD_EXPORT', 'version':1, 'prepared_request':prepared_ref,
                'payload':receipt['payload'], 'byte_admission':prepared['byte_admission'],
                'execution_basis':EXECUTION_BASIS, 'consumption_proof':False, 'authority_effect':'NONE'}
    if canonical_bytes(receipt) != canonical_bytes(expected):
        raise ValueError('scope review requires the exact payload export receipt')
    raw = bound_bytes(root, receipt['payload'])
    manifest, files = bundle(prepared, raw, **limits)
    audit = assess(prepared['task'])
    manifest.update(prepared_request=prepared_ref, payload_export=receipt_ref, exported_payload=receipt['payload'])
    report = {'prepared_request':prepared_ref, 'payload_export':receipt_ref,
              'exported_payload':receipt['payload'], **audit}
    # Validate the whole bounded set before the first write; existing output is immutable.
    target = repository_path(root, output)
    if target.exists():
        raise ValueError('scope review output already exists; choose a new directory')
    publication = {**files,'manifest.json':canonical_bytes(manifest),'scope-report.json':canonical_bytes(report)}
    for name in publication:
        repository_path(root, f'{output}/{name}')
    for name, contents in publication.items():
        append_bytes(root, f'{output}/{name}', contents)
    return {'status':'PASS','scope_status':audit['status'],'explicit_id_coverage':audit['explicit_id_coverage'],
            'manifest':binding(root,f'{output}/manifest.json'), 'scope_report':binding(root,f'{output}/scope-report.json'),
            'assignments':len(manifest['assignments']), 'fragments':len(files),
            'max_reserved_task_bytes':max(t['reserved_total_bytes'] for t in manifest['assignments']),
            'token_capacity_status':'NOT_MEASURED','independent_review':'NOT_PERFORMED','authority_effect':'NONE'}


def check(root, directory):
    manifest = json.loads(repository_path(root,f'{directory}/manifest.json').read_bytes())
    files = {}
    for name in manifest['files']:
        if Path(name).name != name:
            raise ValueError('review fragments must be immediate files')
        files[name] = repository_path(root,f'{directory}/{name}').read_bytes()
    raw = reconstruct(manifest, files)
    if raw != bound_bytes(root, manifest['exported_payload']):
        raise ValueError('partition differs from original exported payload')
    prepared = json.loads(bound_bytes(root,manifest['prepared_request']))
    verify_frozen_request(root,prepared)
    if raw != canonical_bytes(prepared['request']):
        raise ValueError('partition differs from frozen prepared request')
    receipt = json.loads(bound_bytes(root,manifest['payload_export']))
    expected_receipt = {'kind':'SESSION_PAYLOAD_EXPORT','version':1,'prepared_request':manifest['prepared_request'],
                        'payload':manifest['exported_payload'],'byte_admission':prepared['byte_admission'],
                        'execution_basis':EXECUTION_BASIS,'consumption_proof':False,'authority_effect':'NONE'}
    if canonical_bytes(receipt) != canonical_bytes(expected_receipt):
        raise ValueError('partition export receipt identity mismatch')
    expected = {'prepared_request':manifest['prepared_request'], 'payload_export':manifest['payload_export'],
                'exported_payload':manifest['exported_payload'],
                **assess(prepared['task'])}
    if canonical_bytes(expected) != repository_path(root,f'{directory}/scope-report.json').read_bytes():
        raise ValueError('scope report differs from frozen task assessment')
    return {'status':'PASS', 'scope_status':expected['status'], 'source_request_sha256':manifest['source_request_sha256'],
            'assignments':len(manifest['assignments']), 'all_fragments_assigned':True,
            'exact_request_reconstructed':True, 'authority_effect':'NONE'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--prepared')
    parser.add_argument('--export-receipt')
    parser.add_argument('--output')
    parser.add_argument('--check', metavar='DIRECTORY')
    parser.add_argument('--max-file-bytes',type=int,default=65536)
    parser.add_argument('--max-task-bytes',type=int,default=131072)
    parser.add_argument('--overhead-bytes',type=int,default=16384)
    parser.add_argument('--output-bytes',type=int,default=8192)
    args = parser.parse_args()
    if args.check:
        result=check(args.root.resolve(),args.check)
    else:
        if not all((args.prepared,args.export_receipt,args.output)):
            parser.error('--prepared, --export-receipt and --output are required')
        result=prepare(args.root.resolve(),args.prepared,args.export_receipt,args.output,
                       max_file_bytes=args.max_file_bytes,max_task_bytes=args.max_task_bytes,
                       overhead_bytes=args.overhead_bytes,output_bytes=args.output_bytes)
    print(json.dumps(result,ensure_ascii=False,indent=2))
