"""Seven candidates are not seven accepted sources or old dependency closure."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path

import pytest

from rcwh.assets import AssetCatalog
from rcwh.candidate_reviews import digest
from rcwh.generation.records import bound_bytes
from rcwh.graph import ProvenanceGraph
from rcwh.provenance.research_inputs import ResearchSourceInputs
from rcwh.schema import validate_instance
from rcwh.workflow.admission import chapter_scope
from test_research_source_inputs import research, assert_failed, assert_pending

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'artifacts/agent_research/phase6/provenance/ch86-research-inputs-v1'


def test_seven_candidates_preserve_types_and_exact_unregistered_novel_proposals():
    ref = json.loads((BASE / 'binding.json').read_bytes())
    spec = json.loads(bound_bytes(ROOT, ref))
    assert not validate_instance(spec, ROOT / 'schemas/research_source_set.schema.json')
    assert spec['chapters'] == [86]
    assert spec['qualification'] == 'MODEL' and spec['authority_effect'] == 'NONE'
    assert spec['claim_bindings'] == spec['reading_refs'] == []
    assert 'status' not in spec and 'asset_bindings' not in spec
    sources = json.loads(bound_bytes(ROOT, spec['source_bindings'][0]))['sources']
    assert Counter(row['type'] for row in sources) == {'SECONDARY_RESEARCH': 3, 'NOVEL_TEXT': 4}
    assert len({row['id'] for row in sources}) == 7
    graph = ProvenanceGraph.from_repo(ROOT)
    assert not set(row['id'] for row in sources) & (set(graph.sources) | set(graph.claims))
    proposal = json.loads((ROOT / 'artifacts/agent_research/phase6/provenance/ch86-narrow-text-evidence-v1.json').read_bytes())
    assert sources[3:] == [row['source_proposal'] for row in proposal['records']]
    for row in sources:
        assert not validate_instance(row, ROOT / 'schemas/source.schema.json')
        assert row['tier'] == 'EDITORIAL'
        assert row['locator_verification']['status'] == 'UNVERIFIED'
        assert digest(row['text'].encode()) == row['text_sha256']
    for row in sources[:3]:
        locator = row['locator']
        assert locator.get('schema_version') != 2
        carrier = ROOT / locator['path']
        assert digest(carrier.read_bytes()) == row['container']['sha256']
        exact = ''.join(carrier.read_text(encoding='utf-8').splitlines(keepends=True)[locator['line_start'] - 1:locator['line_end']])
        assert exact == locator['quote'] == row['text']


def test_real_loader_refuses_old_exact_lock_while_independent_locators_can_pass():
    ref = json.loads((BASE / 'binding.json').read_bytes())
    report = ResearchSourceInputs(AssetCatalog.from_repo(ROOT)).report(ref, chapter=86, mode='RESEARCH')
    assert_failed(report, 'STALE_RESEARCH_INPUT: requirements/extraction.lock.json')
    assert report['evidence_readiness'] == 'PENDING'
    assert report['qualification'] == 'MODEL' and report['authority_effect'] == 'NONE'
    assert report['unregistered_asset_refs'] == []
    # Three project rows are processed before the first novel record hits the lock.
    assert len(report['source_reports']) == 3
    assert all(row['status'] == 'PENDING' for row in report['source_reports'])
    assert all(row['computed_source_report']['status'] == 'FAIL' for row in report['source_reports'])
    stored = json.loads((BASE / 'load-report.json').read_bytes())
    assert stored['findings'] == report['findings']
    assert stored['records'] == report['records'] == {'sources': [], 'claims': []}
    comparison = json.loads((BASE / 'locator-comparison.json').read_bytes())
    assert len(comparison['records']) == 4
    for row in comparison['records']:
        assert row['verification']['status'] == 'PASS'
        assert row['verification']['findings'] == []
        assert row['verification']['rebuild']['status'] == 'PASS'
    assert comparison['source_registration'] == 'NOT_PERFORMED'


def test_sidecar_does_not_change_legacy_scope_graph_or_frozen_inputs():
    compatibility = json.loads((BASE / 'compatibility.json').read_bytes())
    assert compatibility['before_hashes'] == compatibility['after_hashes']
    for path, expected in compatibility['before_hashes'].items():
        assert digest((ROOT / path).read_bytes()) == expected
    assert compatibility['old_graph_ids'] == compatibility['new_graph_ids']
    assert compatibility['candidate_record_count'] == 7
    assert compatibility['accepted_source_count'] == 0
    assert compatibility['scope_before'] == compatibility['scope_after']
    assert chapter_scope(ROOT, 'data/writing/packages/ch86-agent-research-v3.json', plan_contracts=True) == compatibility['scope_before']
    findings = compatibility['scope_after']['findings']
    assert len(findings) == 3
    assert all(row.startswith('UNRESOLVED_DEPENDENT_SOURCE_ASSET:') for row in findings)
    assert compatibility['source_registration'] is False and compatibility['waiver_added'] is False
    assert compatibility['render_prepare_import_build_called'] is False
    custody = json.loads((BASE / 'custody.json').read_bytes())
    assert custody['original_input_drift'] == [] and custody['snapshot_removed'] is True
    observation = json.loads((BASE / 'observation.json').read_bytes())
    assert observation['status'] == 'DATA_PREPARED_ACTUAL_LOAD_FAILED'
    assert observation['accepted_source_count'] == 0
    assert observation['source_registration'] is False and observation['waiver_added'] is False
    assert observation['generation_consumption_claimed'] is False
    for key in ('source_set', 'sources', 'binding', 'support_scope', 'actual_loader',
                'independent_locator_comparison', 'compatibility', 'custody'):
        bound_bytes(ROOT, observation[key])
    for name, expected in custody['outputs'].items():
        assert digest((BASE / name).read_bytes()) == expected


def mixed_fixture(research):
    research.spec['chapters'] = [86]
    research.claims = []
    research.source['type'] = 'NOVEL_TEXT'
    research.extraction()
    sources = []
    for index in range(3):
        row = deepcopy(research.source)
        row['id'] = f'src:mixed:project:{index}'
        row['type'] = 'SECONDARY_RESEARCH'
        row['tier'] = 'EDITORIAL'
        row['locator'] = {'kind': 'PROJECT_LINE_QUOTE_UNVERIFIED', 'line_start': 1}
        row['notes'] = 'Fixture project reference, not historical evidence or whole-document qualification.'
        carrier = research.asset(f'asset:mixed:project:{index}', f'research/project-{index}.md', row['text'].encode())
        row['container'] = {'ref': carrier['asset_ref'], 'sha256': carrier['sha256']}
        sources.append(row)
    for index in range(4):
        row = deepcopy(research.source)
        row['id'] = f'src:mixed:novel:{index}'
        sources.append(row)
    research.sources = sources
    return research


def test_valid_synthetic_seven_record_set_is_pending_not_evidence_pass(research):
    fixture = mixed_fixture(research)
    report = fixture.report(chapter=86)
    assert_pending(report)
    assert len(report['records']['sources']) == 7 and report['records']['claims'] == []
    assert len(report['source_reports']) == 7
    assert report['unregistered_asset_refs'] == []
    assert [row['computed_source_report']['status'] for row in report['source_reports']] == ['FAIL'] * 3 + ['PASS'] * 4
    assert all(row['status'] == 'PENDING' for row in report['source_reports'])


@pytest.mark.parametrize('mode', ['PRODUCTION', 'BACKTEST', 'WRITING'])
def test_mixed_records_reject_nonresearch_mode(research, mode):
    assert_failed(mixed_fixture(research).report(chapter=86, mode=mode), 'RESEARCH_SOURCE_SET_REQUIRES_RESEARCH_MODE')


def test_mixed_records_reject_wrong_chapter(research):
    assert_failed(mixed_fixture(research).report(chapter=87), 'RESEARCH_SOURCE_SET_CHAPTER_OUT_OF_SCOPE')


@pytest.mark.parametrize('target', ['set', 'sources'])
def test_mixed_records_reject_stale_bound_data(research, target):
    fixture = mixed_fixture(research)
    fixture.publish_records()
    ref = fixture.publish_spec()
    changed = ref if target == 'set' else fixture.spec['source_bindings'][0]
    (fixture.root / changed['path']).write_bytes(b'changed bytes')
    assert_failed(fixture.load(ref, chapter=86), 'STALE_RESEARCH_INPUT')


def test_mixed_records_reject_changed_excerpt_even_when_wrapper_rebound(research):
    fixture = mixed_fixture(research)
    fixture.sources[0]['text'] += ' changed without updating text digest'
    assert_failed(fixture.report(chapter=86), 'SOURCE_TEXT_SHA_MISMATCH')


def test_mixed_records_reject_legacy_id_collision(research):
    fixture = mixed_fixture(research)
    fixture.legacy_source(deepcopy(fixture.sources[0]))
    assert_failed(fixture.report(chapter=86), 'RESEARCH_RECORD_OLD_ID_COLLISION')
