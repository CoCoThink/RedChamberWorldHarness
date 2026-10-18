"""Actual final review failures remain visible despite literary preferences."""
import json
from pathlib import Path

from rcwh.generation.records import bound_bytes
from rcwh.workflow.agent_panel import AgentPanel
from rcwh.schema import validate_instance

ROOT = Path(__file__).resolve().parents[1]
BASE = 'artifacts/agent_research/phase6/advancement'


def test_final_real_opinions_keep_all_28_results_and_literal_evidence():
    for index in (1, 2):
        opinion = json.loads((ROOT / f'{BASE}/final-reader{index}-v1-opinion.json').read_bytes())
        observation = json.loads((ROOT / f'{BASE}/final-reader{index}-v1-observations.json').read_bytes())
        assert not validate_instance(opinion, ROOT / 'schemas/agent_review.schema.json')
        assert len(opinion['results']) == 28
        assert len({row['subject_id'] for row in opinion['results']}) == 28
        assert opinion['reviewer']['context_isolation']['asserted'] is False
        assert opinion['independent_human_admission'] is False
        chapter95 = next(row for row in opinion['results'] if row['subject_id'] == 'chapter-95')
        assert chapter95['verdict'] == 'FAIL'
        for evidence in observation['evidence']:
            text = (ROOT / evidence['path']).read_bytes().decode('utf-8')
            lines = text.splitlines(keepends=True)
            assert evidence['quote'] in ''.join(lines[evidence['line_start'] - 1:evidence['line_end']])
        for row in observation['read_scope']:
            bound_bytes(ROOT, row['binding'])


def test_final_panel_does_not_override_negative_with_positive_preference():
    report = AgentPanel(ROOT).summary(packet=f'{BASE}/final-packet-v1.json')
    assert report['record_integrity_status'] == 'PASS'
    assert report['status'] == 'FAIL'
    subjects = {row['id']: row for row in report['panels'][0]['subjects']}
    assert subjects['chapter-95']['status'] == 'FAIL'
    assert [row['verdict'] for row in subjects['chapter-95']['opinions']] == ['FAIL', 'FAIL']
    assert subjects['contract-95-S3']['status'] == 'FAIL'
    assert all(row['distinct_reviewer_count'] == 0 for row in subjects.values())
    assert subjects['chapter-81']['review_count'] == 0


def test_final_evaluation_request_uses_new_selection_without_adopt_or_corpus_switch():
    selection = json.loads((ROOT / f'{BASE}/final-selection-v1.json').read_bytes())
    request = json.loads((ROOT / f'{BASE}/final-evaluation-request-v1.json').read_bytes())
    schema = json.loads((ROOT / 'schemas/agent_release_manifest.schema.json').read_bytes())
    assert not validate_instance(request, {'$ref': '#/$defs/request', '$defs': schema['$defs']})
    chosen = {row['chapter']: row for row in selection['chapters']}
    for row in request['chapters']:
        assert row['candidate'] == chosen[row['chapter']]['candidate']
        assert row['draft'] == chosen[row['chapter']]['draft']
        assert row['writing_package'] == chosen[row['chapter']]['package']
        assert 'decision' not in row and 'source_reviews' not in row
        assert row['minimum_baseline_ratio'] == 0.8
        assert row['corpus_reviews'][0]['subject_id'] == 'corpus-v2'
    assert not (ROOT / 'releases/agent' / request['id']).exists()
