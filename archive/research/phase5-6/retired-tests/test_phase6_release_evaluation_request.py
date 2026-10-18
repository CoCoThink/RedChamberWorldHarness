"""Evaluation-only request must not invent chapter peers or release adoption."""
import json
from pathlib import Path

from rcwh.generation.records import bound_bytes
from rcwh.schema import validate_instance

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'artifacts/agent_research/phase6/revisions-v2'


def test_actual_full_evaluation_retains_fail_without_build_or_chapter_adoption():
    execution = json.loads((BASE / 'release-evaluation/execution-v1.json').read_bytes())
    report = json.loads(bound_bytes(ROOT, execution['report']))
    custody = json.loads((BASE / 'release-evaluation/snapshot-custody-v1.json').read_bytes())
    assert not validate_instance(report, ROOT / 'schemas/agent_release_manifest.schema.json')
    assert execution['status'] == report['status'] == 'FAIL'
    assert execution['build_called'] is False and execution['stable_snapshot_unchanged'] is True
    assert report['output']['text'] is None
    assert custody['changed_original_inputs'] == [] and custody['snapshot_removed'] is True
    assert custody['input_count'] == 4026
    assert report['automatic_winner'] is False and report['stable_active_effect'] == 'NONE'
    assert len(report['chapters']) == 20
    for row in report['chapters']:
        for gate in ('BYTE_INTEGRITY', 'FULL_CHAPTER_LENGTH', 'PROSE_INTEGRITY', 'AUTHOR_PROVENANCE'):
            assert row['gates'][gate] == 'PASS'
        assert row['gates']['CANDIDATE_PEERS'] == 'PENDING'
        assert row['gates']['COORDINATOR_DECISION'] == 'PENDING'
        assert row['gates']['WRITING_PACKAGE'] == 'FAIL'
        if row['chapter'] == 86:
            assert row['gates']['CHAPTER_SAFETY_POLICY'] == 'FAIL'
            assert 'UNRESOLVED_DEPENDENT_SOURCE_ASSET' in row['findings'][0]
        else:
            assert row['findings'] == ['corpus peer sample differs from selected exemplar']
    assert not (ROOT / report['output']['directory']).exists()


def test_corrected_evaluation_removes_container_false_positive_but_keeps_real_corpus_fail():
    execution = json.loads((BASE / 'release-evaluation/execution-v3.json').read_bytes())
    report = json.loads(bound_bytes(ROOT, execution['report']))
    custody = json.loads((BASE / 'release-evaluation/snapshot-custody-v3.json').read_bytes())
    diagnosis = json.loads((BASE / 'release-evaluation/corpus-container-diagnosis-v1.json').read_bytes())
    assert execution['status'] == report['status'] == 'FAIL'
    assert execution['reader_fix'] == 'CANONICAL_SAMPLE_CONTAINER_UNWRAP'
    assert execution['build_called'] is False and execution['stable_snapshot_unchanged'] is True
    assert custody['input_count'] == 4049
    assert custody['changed_original_inputs'] == [] and custody['snapshot_removed'] is True
    assert report['output']['text'] is None
    assert len(report['findings']) == 1
    assert all('corpus peer sample differs from selected exemplar' not in finding for finding in report['findings'])
    assert 'UNRESOLVED_DEPENDENT_SOURCE_ASSET' in report['findings'][0]
    for row in report['chapters']:
        assert row['gates']['CORPUS_PEERS'] in {'FAIL', 'PENDING'}
        if row['chapter'] != 86:
            assert row['gates']['WRITING_PACKAGE'] == 'PASS'
            assert row['findings'] == []
        else:
            assert row['gates']['CHAPTER_SAFETY_POLICY'] == 'FAIL'
    assert diagnosis['diagnostic_status'] == 'CONFIRMED_READER_BUG'
    assert diagnosis['original_corpus_negative_effect'] == 'NONE; original registered corpus reviews remain FAIL. Correct container parsing must retain binding hash, unique membership and actual text digest checks, then report original negative verdicts rather than PASS.'
    assert not (ROOT / report['output']['directory']).exists()


def test_release_evaluation_request_is_exact_registered_selection_with_unreviewed_subjects():
    scope = json.loads((BASE / 'release-evaluation/scope-v1.json').read_bytes())
    request = json.loads(bound_bytes(ROOT, scope['request']))
    schema = json.loads((ROOT / 'schemas/agent_release_manifest.schema.json').read_bytes())
    assert not validate_instance(request, {'$ref': '#/$defs/request', '$defs': schema['$defs']})
    selection = json.loads(bound_bytes(ROOT, scope['selection']))
    selected = {row['chapter']: row for row in selection['chapters']}
    assert [row['chapter'] for row in request['chapters']] == list(range(81, 101))
    packet_refs = {tuple(sorted(row['panel']['packet'].items())) for row in request['chapters']}
    assert len(packet_refs) == 1
    packet = json.loads(bound_bytes(ROOT, request['chapters'][0]['panel']['packet']))
    assert not validate_instance(packet, ROOT / 'schemas/agent_packet.schema.json')
    assert len(packet['subjects']) == 20
    subjects = {row['id']: row for row in packet['subjects']}
    for row in request['chapters']:
        chapter = row['chapter']
        assert row['mode'] == 'AGENT_CANDIDATE'
        assert row['minimum_baseline_ratio'] == 0.8
        assert row['minimum_body_characters'] == 7000
        assert 'decision' not in row and 'source_reviews' not in row
        draft = json.loads(bound_bytes(ROOT, row['draft']))
        assert draft['candidate'] == row['candidate']
        assert draft['package'] == row['writing_package']
        assert bound_bytes(ROOT, row['candidate']) == bound_bytes(ROOT, selected[chapter]['candidate'])
        assert subjects[row['panel']['subject_id']]['binding'] == row['candidate']
        assert subjects[row['panel']['subject_id']]['scope'] == 'CANDIDATE'
        assert row['corpus_reviews'][0]['subject_id'] == 'corpus-v2'
        corpus_packet = json.loads(bound_bytes(ROOT, row['corpus_reviews'][0]['packet']))
        assert corpus_packet['subjects'][0]['dataset_ref'] == 'corpus:front80:v2-candidate'
    assert 'No ADOPT decisions fabricated' in scope['decisions']
    assert 'never call build while FAIL' in scope['output']
    assert not (ROOT / 'releases/agent/phase6-selected-v1-evaluation-only').exists()
