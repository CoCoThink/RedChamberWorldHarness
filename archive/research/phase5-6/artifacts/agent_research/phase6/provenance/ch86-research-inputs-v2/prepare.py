"""Isolated current-toolchain sidecar construction, never asset registration."""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

BASE = 'artifacts/agent_research/phase6/provenance/ch86-research-inputs-v2'
PREVIOUS = 'artifacts/agent_research/phase6/provenance/ch86-research-inputs-v1'
OLD_EXTRACTION = 'corpus/extractions/b9df50fdab4356483924e76e3952a43ae26413e16cc15997d73ec1eab9fb166f'


def canonical(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n').encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def bound(root, ref):
    path = (root / ref['path']).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError('OUTSIDE_SIDECAR_ROOT')
    raw = path.read_bytes()
    if sha(raw) != ref['sha256']:
        raise ValueError(f'SIDECAR_BINDING_MISMATCH: {ref["path"]}')
    return raw


def binding(root, path):
    return {'path': path, 'sha256': sha((root / path).read_bytes())}


def write(root, path, document):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    raw = canonical(document)
    with target.open('xb') as handle:
        handle.write(raw)
    return {'path': path, 'sha256': sha(raw)}


def validate_extraction(manifest, raw, stamp, input_ref, config):
    """Additional sidecar acceptance; not a claim about loader validation."""
    body = {key: value for key, value in manifest.items() if key != 'id'}
    if manifest['id'] != 'extraction:' + sha(canonical(body)):
        raise ValueError('SIDECAR_EXTRACTION_ID_MISMATCH')
    if manifest['input'] != input_ref or manifest['config'] != config:
        raise ValueError('SIDECAR_INPUT_OR_CONFIG_MISMATCH')
    if {key: manifest[key] for key in ('extractor', 'dependency_lock')} != stamp:
        raise ValueError('SIDECAR_CURRENT_TOOLCHAIN_MISMATCH')
    if manifest['output']['sha256'] != sha(raw) or manifest['output']['bytes'] != len(raw):
        raise ValueError('SIDECAR_OUTPUT_MISMATCH')
    units = {}
    for line in raw.splitlines():
        unit = json.loads(line)
        identity = unit['unit_ref']
        if identity in units:
            raise ValueError('SIDECAR_DUPLICATE_UNIT')
        if unit['input'] != input_ref or sha(unit['text'].encode()) != unit['text_sha256']:
            raise ValueError('SIDECAR_UNIT_INPUT_OR_TEXT_MISMATCH')
        cursor = 0
        for node in unit['nodes']:
            if not cursor == node['start'] <= node['end'] <= len(unit['text']):
                raise ValueError('SIDECAR_NODE_MAPPING_MISMATCH')
            cursor = node['end']
        if cursor != len(unit['text']):
            raise ValueError('SIDECAR_INCOMPLETE_NODE_COVERAGE')
        units[identity] = unit
    if list(units) != manifest['unit_refs']:
        raise ValueError('SIDECAR_UNIT_ORDER_OR_COVERAGE_MISMATCH')
    return units


def validate_reproducibility(first_manifest, first_raw, second_manifest, second_raw, old_raw):
    if canonical(first_manifest) != canonical(second_manifest) or first_raw != second_raw:
        raise ValueError('SIDECAR_INDEPENDENT_COMPILE_MISMATCH')
    if first_raw != old_raw:
        raise ValueError('SIDECAR_OLD_UNITS_DIFFER_NO_AUTOMATIC_MIGRATION')


def validate_spans(sources, units, manifest_ref, output_sha):
    positions = {key: index for index, key in enumerate(units)}
    for source in sources:
        if source['type'] != 'NOVEL_TEXT':
            continue
        locator = source['locator']
        if locator['extraction_ref'] != manifest_ref or locator['output_sha256'] != output_sha or locator['kind'] != 'PDF_TEXT_SPANS':
            raise ValueError('SIDECAR_LOCATOR_EXTRACTION_MISMATCH')
        previous, chunks = (-1, 0), []
        for span in locator['spans']:
            identity = span['unit_ref']
            if identity not in units:
                raise ValueError('SIDECAR_UNKNOWN_UNIT')
            text = units[identity]['text']
            if not 0 <= span['start'] < span['end'] <= len(text):
                raise ValueError('SIDECAR_SPAN_OUT_OF_RANGE')
            if (positions[identity], span['start']) < previous:
                raise ValueError('SIDECAR_REORDERED_OR_OVERLAPPING_SPANS')
            previous = positions[identity], span['end']
            chunks.append(text[span['start']:span['end']])
        excerpt = locator['joiner'].join(chunks)
        if excerpt != source['text'] or sha(excerpt.encode()) != source['text_sha256'] or sha(excerpt.encode()) != locator['raw_text_sha256']:
            raise ValueError('SIDECAR_EXCERPT_MISMATCH')


def validate_report(root, spec, report, manifest_ref, required_paths):
    """Fail closed beyond the generic loader's unknown-registration allowance."""
    if spec['chapters'] != [86] or spec['claim_bindings'] or spec['reading_refs']:
        raise ValueError('SIDECAR_SCOPE_OR_CLAIM_DRIFT')
    assets = spec.get('asset_bindings', [])
    if len(assets) != 1 or assets[0]['asset_ref'] != manifest_ref:
        raise ValueError('SIDECAR_REQUIRED_MANIFEST_BINDING_MISSING')
    ref = assets[0]
    bound(root, ref)
    if manifest_ref != 'asset:sha256:' + ref['sha256']:
        raise ValueError('SIDECAR_MANIFEST_ASSET_ID_MISMATCH')
    if report['unregistered_asset_refs'] != [manifest_ref]:
        raise ValueError('SIDECAR_UNEXPECTED_UNKNOWN_ASSETS')
    if not set(required_paths) <= set(report['paths']):
        raise ValueError('SIDECAR_REQUIRED_DEPENDENCY_PATH_MISSING')
    if (report['status'], report['integrity_status'], report['evidence_readiness']) != ('PENDING', 'PASS', 'PENDING') or report['findings']:
        raise ValueError('SIDECAR_LOADER_NOT_INTEGRITY_PASS_RESEARCH_PENDING')
    sources = json.loads(bound(root, spec['source_bindings'][0]))['sources']
    if len(sources) != 7 or report['records'] != {'sources': sources, 'claims': []}:
        raise ValueError('SIDECAR_ACCEPTED_RECORD_MISMATCH')
    rows = {row['source_id']: row for row in report['source_reports']}
    if len(rows) != 7 or report['qualification'] != 'MODEL' or report['authority_effect'] != 'NONE':
        raise ValueError('SIDECAR_RESEARCH_IDENTITY_MISMATCH')
    for source in sources:
        row = rows[source['id']]
        computed = row['computed_source_report']
        if row['status'] != 'PENDING' or computed['status'] != 'FAIL':
            raise ValueError('SIDECAR_REGISTRATION_OR_EVIDENCE_UPGRADE')
        findings = computed['findings']
        if source['type'] == 'NOVEL_TEXT':
            if len(findings) != 1 or f'unknown asset: {manifest_ref}' not in findings[0]:
                raise ValueError('SIDECAR_UNEXPECTED_NOVEL_LOCATOR_FAILURE')
            if computed['verification_report']['status'] != 'FAIL':
                raise ValueError('SIDECAR_FALSE_REGISTERED_LOCATOR_PASS')
        elif source['type'] == 'SECONDARY_RESEARCH':
            if len(findings) != 1 or not findings[0].startswith('LOCATOR_VERSION_UNVERIFIED:'):
                raise ValueError('SIDECAR_PROJECT_QUALIFICATION_DRIFT')
        else:
            raise ValueError('SIDECAR_SOURCE_TYPE_DRIFT')


def compile_child(root, destination):
    from rcwh.assets import AssetCatalog
    from rcwh.corpus.extraction import ExtractionRepository

    catalog = AssetCatalog.from_repo(root)
    old = json.loads((root / OLD_EXTRACTION / 'manifest.json').read_bytes())
    repository = ExtractionRepository(catalog)
    stamp = repository.execution_stamp(old['config']['format'])
    manifest, raw = repository.compile(old['input']['asset_ref'], old['config'])
    validate_extraction(manifest, raw, stamp, old['input'], old['config'])
    destination.mkdir()
    (destination / 'manifest.json').write_bytes(canonical(manifest))
    (destination / 'units.jsonl').write_bytes(raw)
    (destination / 'stamp.json').write_bytes(canonical(stamp))


def execute(root):
    from rcwh.assets import AssetCatalog
    from rcwh.corpus.extraction import ExtractionRepository
    from rcwh.graph import ProvenanceGraph
    from rcwh.provenance.research_inputs import ResearchSourceInputs
    from rcwh.workflow.admission import chapter_scope

    base = root / BASE
    catalog = AssetCatalog.from_repo(root)
    old = json.loads((root / OLD_EXTRACTION / 'manifest.json').read_bytes())
    old_output = catalog.resolve(old['output']['asset_ref'])
    old_raw = old_output.path.read_bytes()
    v1_ref = json.loads((root / PREVIOUS / 'binding.json').read_bytes())
    old_graph = ProvenanceGraph.from_repo(root)
    graph_ids = sorted(set(old_graph.sources) | set(old_graph.claims) | set(old_graph.decisions) | set(old_graph.implementations) | set(old_graph.title_axes))
    before_scope = chapter_scope(root, 'data/writing/packages/ch86-agent-research-v3.json', plan_contracts=True)
    # Frozen compatibility scope excludes mutable progress documentation/tests.
    protected = json.loads((root / 'artifacts/agent_research/phase5/verification/protected-originals-final.json').read_bytes())['checked_files']
    watched = set(protected)
    for prefix in ('data', 'schemas', 'src', PREVIOUS, OLD_EXTRACTION):
        watched.update(path.relative_to(root).as_posix() for path in (root / prefix).rglob('*') if path.is_file())
    watched.update(['requirements/extraction.lock.json', 'artifacts/agent_research/phase6/revisions-v2/editorial-requests-v1/ch86.json', 'artifacts/agent_research/phase6/revisions-v2/narrow-repair-requests/ch86-v2.json', 'artifacts/agent_research/phase6/revisions-v2/release-evaluation/report-v1.json', 'artifacts/agent_research/phase6/revisions-v2/release-evaluation/report-v3.json', 'artifacts/agent_research/phase6/revisions-v2/continuity-reading-selection-v1.json'])
    before = {name: sha((root / name).read_bytes()) for name in sorted(watched)}
    with tempfile.TemporaryDirectory(prefix='rcwh-independent-compiles-') as directory:
        compiles = []
        for index in (1, 2):
            out = Path(directory) / str(index)
            subprocess.run([sys.executable, str(base / 'prepare.py'), '--root', str(root), '--compile', str(out)], cwd=root, check=True)
            compiles.append((json.loads((out / 'manifest.json').read_bytes()), (out / 'units.jsonl').read_bytes(), json.loads((out / 'stamp.json').read_bytes())))
        manifest, raw, stamp = compiles[0]
        validate_reproducibility(manifest, raw, compiles[1][0], compiles[1][1], old_raw)
        if stamp != compiles[1][2] or stamp != ExtractionRepository(catalog).execution_stamp('PDF'):
            raise ValueError('SIDECAR_TOOLCHAIN_CHANGED_DURING_COMPILE')
        units = validate_extraction(manifest, raw, stamp, old['input'], old['config'])
    manifest_bytes = canonical(manifest)
    manifest_ref = 'asset:sha256:' + sha(manifest_bytes)
    if manifest_ref in catalog.assets:
        raise ValueError('SIDECAR_NEW_MANIFEST_ALREADY_REGISTERED')
    if manifest['output']['asset_ref'] != old_output.id:
        raise ValueError('SIDECAR_OUTPUT_IDENTITY_CHANGED')
    manifest_binding = write(root, BASE + '/extraction-manifest.json', manifest)
    sources = deepcopy(json.loads((root / PREVIOUS / 'sources.json').read_bytes())['sources'])
    for source in sources[3:]:
        source['id'] += ':current-extraction-v2'
        source['locator']['extraction_ref'] = manifest_ref
        source['locator']['output_sha256'] = manifest['output']['sha256']
    if set(source['id'] for source in sources) & set(graph_ids):
        raise ValueError('SIDECAR_GLOBAL_ID_COLLISION')
    validate_spans(sources, units, manifest_ref, manifest['output']['sha256'])
    source_ref = write(root, BASE + '/sources.json', {'schema_version': 1, 'sources': sources})
    spec = {'schema_version': 1, 'id': 'research-source-set:ch86:project-and-novel:current-extraction-v2', 'kind': 'RESEARCH_SOURCE_SET', 'chapters': [86], 'qualification': 'MODEL', 'authority_effect': 'NONE', 'source_bindings': [source_ref], 'claim_bindings': [], 'reading_refs': [], 'asset_bindings': [{'asset_ref': manifest_ref, **manifest_binding}], 'limitations': ['New unregistered current-toolchain extraction manifest; exact manual binding checks are not registered locator PASS.', 'Two independent process compiles use the same algorithm, not independent textual witnesses or human review.', 'Project references remain unverified secondary interpretations; novel excerpts are not efficacy, historical diagnosis or86event evidence.', 'No source registration, global graph overlay, admission waiver or generation consumption. Old three dependent source blockers remain.']}
    set_ref = write(root, BASE + '/source-set.json', spec)
    write(root, BASE + '/binding.json', set_ref)
    required = [set_ref['path'], source_ref['path'], manifest_binding['path'], old_output.relative_path, catalog.resolve(old['input']['asset_ref']).relative_path, stamp['dependency_lock']['path'], 'schemas/source.schema.json', 'schemas/research_source_set.schema.json', 'schemas/locator_v2.schema.json', 'schemas/extraction_manifest.schema.json', 'schemas/extraction_unit.schema.json']
    report = ResearchSourceInputs(catalog).report(set_ref, chapter=86, mode='RESEARCH')
    write(root, BASE + '/load-report.json', report)
    validate_report(root, spec, report, manifest_ref, required)
    v1_report = ResearchSourceInputs(catalog).report(v1_ref, chapter=86, mode='RESEARCH')
    if v1_report['status'] != 'FAIL' or v1_report['records'] != {'sources': [], 'claims': []} or 'STALE_RESEARCH_INPUT: requirements/extraction.lock.json' not in v1_report['findings']:
        raise ValueError('SIDECAR_OLD_V1_FAILURE_CHANGED')
    write(root, BASE + '/v1-recheck.json', v1_report)
    compile_ref = write(root, BASE + '/compile-comparison.json', {'schema_version': 1, 'kind': 'UNREGISTERED_CURRENT_EXTRACTION_COMPILE_COMPARISON', 'authority_effect': 'NONE', 'independent_process_count': 2, 'canonical_manifest_bytes_equal': True, 'units_bytes_equal': True, 'old_registered_units_bytes_equal': True, 'output_reused': {'asset_ref': old_output.id, 'path': old_output.relative_path, 'sha256': old_output.sha256}, 'current_toolchain': stamp, 'old_toolchain': {key: old[key] for key in ('extractor', 'dependency_lock')}, 'manifest': manifest_binding, 'manifest_asset_ref': manifest_ref, 'manifest_internal_id_checked': True, 'unit_count': len(units), 'nodes_and_unit_hashes_checked': True, 'four_exact_spans_checked': True, 'required_report_paths': required, 'registered_locator_verifier_pass': False, 'limitation': 'Real independent processes, same extraction algorithm; no registered load/rebuild report, independent witness or human qualification.'})
    old_scope_doc = json.loads((root / PREVIOUS / 'support-scope.json').read_bytes())
    layers = deepcopy(old_scope_doc['layers'])
    layers[1]['source_ids'] = [source['id'] for source in sources[3:]]
    write(root, BASE + '/support-scope.json', {'schema_version': 1, 'kind': 'CH86_CURRENT_EXTRACTION_SUPPORT_SCOPE', 'authority_effect': 'NONE', 'layers': layers, 'excluded_claims': old_scope_doc['excluded_claims'], 'prior_scope': binding(root, PREVIOUS + '/support-scope.json'), 'source_set': set_ref, 'note': 'New novel source ids only identify new exact extraction bindings, not a new claim; project records unchanged. No generation/release effect.'})
    after_scope = chapter_scope(root, 'data/writing/packages/ch86-agent-research-v3.json', plan_contracts=True)
    graph_after = ProvenanceGraph.from_repo(root)
    new_ids = sorted(set(graph_after.sources) | set(graph_after.claims) | set(graph_after.decisions) | set(graph_after.implementations) | set(graph_after.title_axes))
    drift = [name for name, value in before.items() if sha((root / name).read_bytes()) != value]
    if drift or graph_ids != new_ids or before_scope != after_scope:
        raise ValueError(f'SIDECAR_LEGACY_DRIFT: {drift}')
    protected = json.loads((root / 'artifacts/agent_research/phase5/verification/protected-originals-final.json').read_bytes())['checked_files']
    if any(sha((root / name).read_bytes()) != value for name, value in protected.items()):
        raise ValueError('SIDECAR_PROTECTED_ORIGINAL_CHANGED')
    write(root, BASE + '/compatibility.json', {'schema_version': 1, 'kind': 'CH86_CURRENT_EXTRACTION_COMPATIBILITY', 'authority_effect': 'NONE', 'preexisting_file_hashes': before, 'existing_input_changes': drift, 'old_graph_ids': graph_ids, 'new_graph_ids': new_ids, 'scope_before': before_scope, 'scope_after': after_scope, 'protected_original_count': len(protected), 'old_v1_loader_status': v1_report['status'], 'old_v1_findings': v1_report['findings'], 'source_or_asset_registration': False, 'render_prepare_import_evaluate_build_called': False, 'stable_active_effect': 'NONE'})
    output_refs = [binding(root, BASE + '/' + name) for name in ('extraction-manifest.json', 'sources.json', 'source-set.json', 'binding.json', 'load-report.json', 'v1-recheck.json', 'compile-comparison.json', 'support-scope.json', 'compatibility.json')]
    write(root, BASE + '/observation.json', {'schema_version': 1, 'kind': 'CH86_CURRENT_EXTRACTION_RESEARCH_OBSERVATION', 'authority_effect': 'NONE', 'status': 'RESEARCH_INTEGRITY_PASS_EVIDENCE_PENDING', 'outputs': output_refs, 'candidate_count': 7, 'accepted_research_record_count': len(report['records']['sources']), 'claims': 0, 'research_loader_status': report['status'], 'integrity_status': report['integrity_status'], 'evidence_readiness': report['evidence_readiness'], 'unknown_assets': report['unregistered_asset_refs'], 'compile_comparison': compile_ref, 'registered_locator_verifier_pass': False, 'old_scope_blockers_preserved': True, 'source_registration': False, 'adoption': 'NOT_GRANTED', 'publication': 'NOT_ADOPTED_NOT_RELEASED'})
    print('Research integrity PASS, evidence PENDING; old v1 FAIL and old scope preserved.', flush=True)


def run_snapshot(root):
    for name in ('extraction-manifest.json', 'sources.json', 'source-set.json', 'binding.json', 'load-report.json', 'custody.json', 'failure.json'):
        if (root / BASE / name).exists():
            raise FileExistsError(name)
    files = subprocess.check_output(['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'], cwd=root).decode().split('\0')
    inputs = {}
    with tempfile.TemporaryDirectory(prefix='rcwh-ch86-source-v2-') as directory:
        snapshot = Path(directory) / 'repo'
        snapshot.mkdir()
        for name in sorted(set(files) - {''}):
            source = root / name
            if source.is_symlink():
                raise ValueError(f'SIDECAR_SYMLINK_INPUT: {name}')
            if not source.is_file():
                continue
            destination = snapshot / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
            inputs[name] = sha(destination.read_bytes())
        subprocess.run(['git', 'init', '-q', str(snapshot)], check=True)
        subprocess.run(['git', 'add', '.'], cwd=snapshot, check=True, capture_output=True)
        env = {**os.environ, 'PYTHONPATH': str(snapshot / 'src'), 'PYTHONDONTWRITEBYTECODE': '1'}
        child = subprocess.run([sys.executable, str(snapshot / BASE / 'prepare.py'), '--root', str(snapshot), '--execute'], cwd=snapshot, env=env, capture_output=True)
        print(child.stdout.decode(), end='', flush=True)
        drift = [name for name, value in inputs.items() if not (root / name).is_file() or sha((root / name).read_bytes()) != value]
        if child.returncode or drift:
            diagnostics = {}
            for name in ('load-report.json', 'compile-comparison.json'):
                path = snapshot / BASE / name
                if path.is_file():
                    diagnostics[name] = json.loads(path.read_bytes())
            write(root, BASE + '/failure.json', {'schema_version': 1, 'kind': 'CH86_SIDECAR_V2_FAILURE', 'authority_effect': 'NONE', 'returncode': child.returncode, 'stderr': child.stderr.decode(), 'original_input_drift': drift, 'diagnostics': diagnostics, 'success_outputs_copied': False, 'snapshot_removed': True})
            raise ValueError('SIDECAR_V2_FAILED_NO_SUCCESS_COPYBACK')
        outputs = {}
        for path in sorted((snapshot / BASE).glob('*.json')):
            raw = path.read_bytes()
            with (root / BASE / path.name).open('xb') as handle:
                handle.write(raw)
            outputs[path.name] = sha(raw)
        write(root, BASE + '/custody.json', {'schema_version': 1, 'kind': 'CH86_CURRENT_EXTRACTION_EXACT_SNAPSHOT_CUSTODY', 'authority_effect': 'NONE', 'inputs': inputs, 'input_count': len(inputs), 'original_input_drift': drift, 'outputs': outputs, 'snapshot_removed': True, 'source_or_asset_registration': False, 'build_called': False, 'limitation': 'Only new sidecar outputs copied. Compiler caches and catalog read locks confined to temporary checkout; no old failures or binding rules changed.'})
    print('Sidecar v2 outputs copied byte-exact; temporary snapshot removed.', flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--compile', type=Path)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    root = args.root.resolve()
    if args.compile:
        compile_child(root, args.compile)
    elif args.execute:
        execute(root)
    else:
        run_snapshot(root)


if __name__ == '__main__':
    main()
