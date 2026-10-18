"""Current toolchain sidecar is reproducible research, not registered evidence."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path

import pytest

from rcwh.assets import AssetCatalog
from rcwh.generation.records import bound_bytes
from rcwh.provenance.research_inputs import ResearchSourceInputs
from test_research_source_inputs import research, assert_failed

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = 'artifacts/agent_research/phase6/provenance/ch86-research-inputs-v2'
BASE = ROOT / DIRECTORY
CURRENT_COMPATIBILITY = ROOT / 'artifacts/agent_research/phase6/provenance/ch86-research-inputs-v3-compatibility.json'
OLD = ROOT / 'artifacts/agent_research/phase6/provenance/ch86-research-inputs-v1'
module_spec = importlib.util.spec_from_file_location('ch86_sidecar_v2', BASE / 'prepare.py')
sidecar = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(sidecar)


def fixture_chain(research):
    bindings = research.extraction(unregistered=('manifest', 'units'))
    manifest = json.loads((research.root / bindings['manifest']['path']).read_bytes())
    raw = (research.root / bindings['units']['path']).read_bytes()
    stamp = {key: deepcopy(manifest[key]) for key in ('extractor', 'dependency_lock')}
    return manifest, raw, stamp


@pytest.mark.parametrize('mutation,error', [
    ('id', 'EXTRACTION_ID'), ('toolchain', 'CURRENT_TOOLCHAIN'),
    ('output', 'OUTPUT_MISMATCH'), ('text', 'UNIT_INPUT_OR_TEXT'),
    ('input', 'UNIT_INPUT_OR_TEXT'), ('duplicate', 'DUPLICATE_UNIT'),
    ('nodes', 'NODE_MAPPING'), ('coverage', 'INCOMPLETE_NODE_COVERAGE'),
    ('order', 'UNIT_ORDER_OR_COVERAGE'),
])
def test_strict_acceptance_checks_identity_and_nodes_not_promised_by_loader(research, mutation, error):
    manifest, raw, stamp = fixture_chain(research)
    original_input, original_config = deepcopy(manifest['input']), deepcopy(manifest['config'])
    units = [json.loads(line) for line in raw.splitlines()]
    if mutation == 'id':
        manifest['id'] = 'extraction:' + '0' * 64
    elif mutation == 'toolchain':
        manifest['extractor']['python'] = 'forged executor'
    elif mutation == 'output':
        manifest['output']['sha256'] = '0' * 64
    elif mutation == 'order':
        manifest['unit_refs'] = ['not-the-unit']
    else:
        if mutation == 'text':
            units[0]['text'] += 'bad'
        elif mutation == 'input':
            units[0]['input']['sha256'] = '0' * 64
        elif mutation == 'duplicate':
            units.append(deepcopy(units[0]))
        elif mutation == 'nodes':
            units[0]['nodes'][0]['start'] = 1
        elif mutation == 'coverage':
            units[0]['nodes'] = []
        raw = b''.join(sidecar.canonical(row) for row in units)
        manifest['output']['sha256'] = sidecar.sha(raw)
        manifest['output']['bytes'] = len(raw)
    if mutation != 'id':
        manifest['id'] = 'extraction:' + sidecar.sha(sidecar.canonical({key: value for key, value in manifest.items() if key != 'id'}))
    with pytest.raises(ValueError, match=error):
        sidecar.validate_extraction(manifest, raw, stamp, original_input, original_config)


@pytest.mark.parametrize('changed', ['second_output', 'second_manifest', 'old_output'])
def test_compile_or_old_unit_difference_stops_automatic_migration(research, changed):
    manifest, raw, _ = fixture_chain(research)
    other_manifest, second, old = deepcopy(manifest), raw, raw
    if changed == 'second_output':
        second += b'changed'
    elif changed == 'second_manifest':
        other_manifest['id'] = 'extraction:' + '0' * 64
    else:
        old += b'old differs'
    with pytest.raises(ValueError, match='COMPILE_MISMATCH|NO_AUTOMATIC_MIGRATION'):
        sidecar.validate_reproducibility(manifest, raw, other_manifest, second, old)


@pytest.mark.parametrize('mutation,error', [
    ('slice', 'EXCERPT_MISMATCH'), ('empty', 'SPAN_OUT_OF_RANGE'),
    ('bounds', 'SPAN_OUT_OF_RANGE'), ('unknown', 'UNKNOWN_UNIT'),
    ('reordered', 'REORDERED_OR_OVERLAPPING'), ('output', 'LOCATOR_EXTRACTION'),
])
def test_strict_excerpt_acceptance_rejects_bad_spans(research, mutation, error):
    manifest, raw, _ = fixture_chain(research)
    source = deepcopy(research.source)
    source['type'] = 'NOVEL_TEXT'
    # This fixture is TEXT; make the locator kind PDF solely for pure span checks.
    source['locator']['kind'] = 'PDF_TEXT_SPANS'
    units = {row['unit_ref']: row for line in raw.splitlines() if (row := json.loads(line))}
    span = source['locator']['spans'][0]
    if mutation == 'slice':
        span.update(start=0, end=1)
    elif mutation == 'empty':
        span.update(start=1, end=1)
    elif mutation == 'bounds':
        span['end'] = 99999
    elif mutation == 'unknown':
        span['unit_ref'] = 'unknown'
    elif mutation == 'reordered':
        source['locator']['spans'] *= 2
    else:
        source['locator']['output_sha256'] = '0' * 64
    with pytest.raises(ValueError, match=error):
        sidecar.validate_spans([source], units, source['locator']['extraction_ref'], manifest['output']['sha256'])


def test_missing_binding_can_be_pending_in_loader_but_strict_acceptance_refuses(research):
    research.extraction(unregistered=('manifest', 'units'))
    manifest_ref = research.source['locator']['extraction_ref']
    research.spec['asset_bindings'] = []
    research.claims = []
    report = research.report()
    assert report['integrity_status'] == 'PASS' and report['status'] == 'PENDING'
    with pytest.raises(ValueError, match='REQUIRED_MANIFEST_BINDING_MISSING'):
        sidecar.validate_report(research.root, {**research.spec, 'chapters': [86]}, report, manifest_ref, [])


@pytest.mark.parametrize('mutation,error', [
    ('lock', 'STALE_RESEARCH_INPUT'), ('output', 'LOCATOR_OUTPUT_HASH_MISMATCH'),
    ('text_hash', 'UNIT_TEXT_HASH_MISMATCH'), ('unit_input', 'UNIT_INPUT_MISMATCH'),
])
def test_real_loader_rejects_bound_manifest_and_unit_corruption(research, mutation, error):
    bindings = research.extraction(unregistered=('manifest', 'units'))
    research.claims = []
    if mutation in ('lock', 'output'):
        manifest = json.loads((research.root / bindings['manifest']['path']).read_bytes())
        if mutation == 'lock':
            manifest['dependency_lock']['sha256'] = '0' * 64
        else:
            research.source['locator']['output_sha256'] = '0' * 64
        if mutation == 'lock':
            new = research.document('research/modified-manifest.json', manifest)
            research.source['locator']['extraction_ref'] = 'asset:sha256:' + new['sha256']
            research.spec['asset_bindings'][0] = {'asset_ref': research.source['locator']['extraction_ref'], **new}
    else:
        units = [json.loads(line) for line in (research.root / bindings['units']['path']).read_bytes().splitlines()]
        if mutation == 'text_hash':
            units[0]['text'] += 'changed'
        else:
            units[0]['input']['sha256'] = '0' * 64
        raw = b''.join(sidecar.canonical(row) for row in units)
        unit_ref = research.asset('asset:test:changed-units', 'research/changed-units.jsonl', raw)
        manifest = json.loads((research.root / bindings['manifest']['path']).read_bytes())
        manifest['output'] = {'asset_ref': unit_ref['asset_ref'], 'sha256': unit_ref['sha256'], 'bytes': len(raw)}
        new = research.document('research/modified-manifest.json', manifest)
        research.source['locator']['extraction_ref'] = 'asset:sha256:' + new['sha256']
        research.source['locator']['output_sha256'] = unit_ref['sha256']
        research.spec['asset_bindings'][0] = {'asset_ref': research.source['locator']['extraction_ref'], **new}
    assert_failed(research.report(), error)


def test_registered_units_cannot_be_rebound_to_different_path(research):
    bindings = research.extraction(unregistered=('manifest',))
    units = bindings['units']
    duplicate = research.write('research/copied-units.jsonl', (research.root / units['path']).read_bytes())
    research.spec['asset_bindings'].append({'asset_ref': units['asset_ref'], **duplicate})
    assert_failed(research.report(), 'RESEARCH_ASSET_BINDING_CONFLICT')


def test_real_v2_uses_reproducible_current_manifest_without_registered_locator_claim():
    ref = json.loads((BASE / 'binding.json').read_bytes())
    spec = json.loads(bound_bytes(ROOT, ref))
    sources = json.loads(bound_bytes(ROOT, spec['source_bindings'][0]))['sources']
    previous = json.loads((OLD / 'sources.json').read_bytes())['sources']
    assert sources[:3] == previous[:3]
    for old, new in zip(previous[3:], sources[3:], strict=True):
        expected = deepcopy(old)
        expected['id'] += ':current-extraction-v2'
        expected['locator']['extraction_ref'] = spec['asset_bindings'][0]['asset_ref']
        assert expected == new
    assert spec['schema_version'] == 1 and spec['chapters'] == [86]
    assert spec['claim_bindings'] == spec['reading_refs'] == []
    manifest = json.loads(bound_bytes(ROOT, spec['asset_bindings'][0]))
    comparison = json.loads((BASE / 'compile-comparison.json').read_bytes())
    raw = (ROOT / comparison['output_reused']['path']).read_bytes()
    units = sidecar.validate_extraction(manifest, raw, comparison['current_toolchain'], manifest['input'], manifest['config'])
    assert manifest['dependency_lock']['sha256'] == sidecar.sha((ROOT / 'requirements/extraction.lock.json').read_bytes())
    assert comparison['independent_process_count'] == 2
    assert comparison['canonical_manifest_bytes_equal'] is True
    assert comparison['old_registered_units_bytes_equal'] is True
    assert comparison['registered_locator_verifier_pass'] is False
    sidecar.validate_spans(sources, units, spec['asset_bindings'][0]['asset_ref'], manifest['output']['sha256'])
    report = ResearchSourceInputs(AssetCatalog.from_repo(ROOT)).report(ref, chapter=86)
    sidecar.validate_report(ROOT, spec, report, spec['asset_bindings'][0]['asset_ref'], comparison['required_report_paths'])
    assert report['records']['sources'] == sources
    assert len(report['source_reports']) == 7
    for row in report['source_reports']:
        assert row['status'] == 'PENDING'
        assert row['computed_source_report']['status'] == 'FAIL'


def test_real_compatibility_keeps_v1_failure_and_three_old_scope_blockers():
    report = json.loads(CURRENT_COMPATIBILITY.read_bytes())
    assert report['existing_input_changes'] == []
    assert report['old_graph_ids'] == report['new_graph_ids']
    assert report['scope_before'] == report['scope_after']
    assert len(report['scope_after']['findings']) == 3
    assert all('UNRESOLVED_DEPENDENT_SOURCE_ASSET' in finding for finding in report['scope_after']['findings'])
    assert report['old_v1_loader_status'] == 'FAIL'
    assert report['old_v1_findings'] == ['STALE_RESEARCH_INPUT: requirements/extraction.lock.json']
    assert report['source_or_asset_registration'] is False
    for name, value in report['preexisting_file_hashes'].items():
        assert sidecar.sha((ROOT / name).read_bytes()) == value
    custody = json.loads((BASE / 'custody.json').read_bytes())
    assert custody['original_input_drift'] == [] and custody['snapshot_removed'] is True
    for name, value in custody['outputs'].items():
        assert sidecar.sha((BASE / name).read_bytes()) == value


def test_strict_acceptance_refuses_missing_paths_or_manifest_binding():
    report = json.loads((BASE / 'load-report.json').read_bytes())
    spec = json.loads((BASE / 'source-set.json').read_bytes())
    comparison = json.loads((BASE / 'compile-comparison.json').read_bytes())
    manifest_ref = spec['asset_bindings'][0]['asset_ref']
    absent = deepcopy(report)
    absent['paths'].remove(spec['asset_bindings'][0]['path'])
    with pytest.raises(ValueError, match='REQUIRED_DEPENDENCY_PATH_MISSING'):
        sidecar.validate_report(ROOT, spec, absent, manifest_ref, comparison['required_report_paths'])
    missing = deepcopy(spec)
    missing['asset_bindings'] = []
    with pytest.raises(ValueError, match='REQUIRED_MANIFEST_BINDING_MISSING'):
        sidecar.validate_report(ROOT, missing, report, manifest_ref, comparison['required_report_paths'])
