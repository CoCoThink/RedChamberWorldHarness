"""Fail closed on altered quotes, incomplete coverage and duplicate readers."""
import importlib.util
import json
from pathlib import Path
import shutil

import pytest

from rcwh.candidate_reviews import canonical_bytes, digest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('pilot_readings', ROOT / 'tools/check_pilot_readings.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def store(root, path, value):
    raw = value if isinstance(value, bytes) else canonical_bytes(value)
    (root / path).write_bytes(raw)
    return {'path': path, 'sha256': digest(raw)}


@pytest.fixture
def inputs(tmp_path):
    (tmp_path / 'schemas').mkdir()
    shutil.copyfile(ROOT / 'schemas/agent_review.schema.json', tmp_path / 'schemas/agent_review.schema.json')
    subjects = [{'id': f'text-{i}', 'binding': store(tmp_path, f'text-{i}.txt', '标题\r\n正文\r\n'.encode())} for i in range(6)]
    packet = store(tmp_path, 'packet.json', {'subjects': subjects, 'coordinator_session_id': 'coordinator'})
    submissions = []
    for n in range(2):
        opinion = {'schema_version': 1, 'report_kind': 'AGENT_REVIEW_OPINION', 'packet': packet,
                   'reviewer': {'id': f'reader{n}', 'kind': 'MODEL_SUBAGENT', 'session_id': f'session{n}',
                       'model': {'label': 'fixture', 'verification': 'DECLARED_NOT_VERIFIED'},
                       'context_isolation': {'asserted': False, 'verification': 'NOT_PROVEN'}},
                   'results': [{'subject_id': s['id'], 'subject_sha256': s['binding']['sha256'],
                                'verdict': 'PENDING', 'notes': 'fixture only', 'sample_checks': []} for s in subjects],
                   'authority_effect': 'NONE', 'usage': 'RESEARCH_ONLY', 'independent_human_admission': False}
        observation = {'actual_read_order': [s['id'] for s in subjects][::1 if n == 0 else -1],
                       'read_scope': [{'subject_id': s['id'], 'binding': s['binding'], 'line_ranges': [[1, 1], [2, 2]], 'complete': True} for s in subjects],
                       'evidence': [{'id': s['id'], 'subject_id': s['id'], 'path': s['binding']['path'], 'line_start': 2, 'line_end': 2, 'quote': '正文'} for s in subjects]}
        submissions.append({'opinion': store(tmp_path, f'opinion{n}.json', opinion),
                            'observations': store(tmp_path, f'observations{n}.json', observation)})
    return tmp_path, packet, submissions


def test_append_only_extra_eof_display_correction(inputs):
    root, packet, submissions = inputs
    ref = submissions[1]['observations']
    value = json.loads((root / ref['path']).read_bytes())
    corrections = []
    for row in value['read_scope']:
        row['line_ranges'] = [[1, 3]]
        corrections.append({'subject_id': row['subject_id'], 'binding': row['binding'],
                            'original_line_ranges': [[1, 3]], 'corrected_line_ranges': [[1, 2]],
                            'EOF_display_only': {'line_ranges': [[3, 3]]}})
    submissions[1]['observations'] = store(root, ref['path'], value)
    submissions[1]['scope_correction'] = store(root, 'correction.json', {
        'raw_observations': submissions[1]['observations'], 'corrections': corrections})
    report = MODULE.check(root, packet, submissions, {'author'})
    assert len(report['readers']) == 2
    corrections[0]['corrected_line_ranges'] = [[1, 1]]
    submissions[1]['scope_correction'] = store(root, 'correction.json', {
        'raw_observations': submissions[1]['observations'], 'corrections': corrections})
    with pytest.raises(ValueError):
        MODULE.check(root, packet, submissions, {'author'})


def test_exact_bytes_and_union_coverage_remain_not_qualification(inputs):
    report = MODULE.check(*inputs, {'author'})
    assert report['status'] == 'BYTE_QUOTES_AND_DECLARED_COVERAGE_PASS_NOT_QUALIFICATION'
    assert all(row['raw_verdicts'] == ['PENDING'] * 6 for row in report['readers'])


@pytest.mark.parametrize('fault', ['quote', 'gap', 'order', 'reader', 'author', 'negative_omitted', 'subject', 'isolation'])
def test_changed_quote_scope_identity_or_omitted_result_rejected(inputs, fault):
    root, packet, submissions = inputs
    kind = 'observations' if fault in ('quote', 'gap', 'order') else 'opinion'
    ref = submissions[1][kind]
    value = json.loads((root / ref['path']).read_bytes())
    if fault == 'quote':
        value['evidence'][0]['quote'] = '不存在'
    elif fault == 'gap':
        value['read_scope'][0]['line_ranges'] = [[2, 2]]
    elif fault == 'order':
        value['actual_read_order'].reverse()
    elif fault == 'reader':
        value['reviewer']['session_id'] = 'session0'
    elif fault == 'author':
        value['reviewer']['session_id'] = 'author'
    elif fault == 'negative_omitted':
        value['results'].pop()
    elif fault == 'subject':
        value['results'][0]['subject_sha256'] = '0' * 64
    else:
        value['reviewer']['context_isolation']['asserted'] = True
    submissions[1][kind] = store(root, ref['path'], value)
    with pytest.raises(ValueError):
        MODULE.check(root, packet, submissions, {'author'})
