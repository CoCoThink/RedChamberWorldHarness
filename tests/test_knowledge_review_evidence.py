import json
import shutil
from pathlib import Path

import pytest

from rcwh.knowledge_versions import load_knowledge_version
from tools.knowledge_review_evidence import ROOT, REQUEST, SOURCES, create, verify


def test_evidence_bundle_detects_changed_candidate_and_request(tmp_path):
    request = json.loads((ROOT / REQUEST).read_bytes())
    paths = [REQUEST, request['knowledge_projection']['path'], *SOURCES.values(),
             'data/knowledge/v04_ch86.json', 'src/rcwh/knowledge.py',
             'src/rcwh/knowledge_versions.py', 'src/rcwh/generation/knowledge_projection.py']
    for path in paths:
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / path, target)
    ref = create(tmp_path)
    assert verify(tmp_path, ref['path'])['production_admission'] == 'NOT_GRANTED'
    candidate = tmp_path / SOURCES['candidate']
    original = candidate.read_bytes()
    candidate.write_bytes(original + b'changed')
    with pytest.raises(ValueError, match='candidate does not match'):
        verify(tmp_path, ref['path'])
    candidate.write_bytes(original)
    request_file = tmp_path / REQUEST
    request_file.write_bytes(request_file.read_bytes() + b' ')
    with pytest.raises(ValueError, match='request content digest mismatch'):
        verify(tmp_path, ref['path'])


@pytest.mark.parametrize('actor,checkpoint,expected', [
    ('zijuan', 'ENTRY', 'does_not_know'),
    ('zijuan', 'K86-ZIJUAN-SEES-RAPID-DECLINE', 'does_not_know'),
    ('zijuan', 'K86-V04-DEATH-WITNESSED', 'knows'),
    ('baoyu', 'K86-V04-DEATH-WITNESSED', 'does_not_know'),
    ('baoyu', 'K86-V04-BAOYU-LEARNS-DEATH-ACCOUNT', 'knows'),
])
def test_v04_guard_changes_only_after_each_actor_learns(actor, checkpoint, expected):
    rt = load_knowledge_version(ROOT, 'v0.4:ch86')
    guard = {'id': 'probe', 'actor': actor, 'fact': 'death_relative_account',
             'any_text': ['听说经过'], 'allowed_status': ['knows']}
    contract = {'knowledge_checkpoint': checkpoint, 'knowledge_guards': [guard]}
    hit = rt.text_guard('ch86_last_night_v04', contract, '听说经过')
    assert hit['checks'][0]['epistemic_status'] == expected
    assert hit['status'] == ('PASS' if expected == 'knows' else 'WARN')
    assert hit['semantic_coverage'] is False
    assert rt.text_guard('ch86_last_night_v04', contract, '没有命中短语')['status'] == 'PASS'


@pytest.mark.parametrize('fact', ['death_precise_time', 'death_physiological_detail', 'death_medical_cause'])
@pytest.mark.parametrize('actor', ['daiyu', 'zijuan', 'baoyu'])
def test_v04_guard_flags_unsupported_precision_even_at_final(fact, actor):
    rt = load_knowledge_version(ROOT, 'v0.4:ch86')
    contract = {'knowledge_checkpoint': None, 'knowledge_guards': [
        {'id': 'precision', 'actor': actor, 'fact': fact, 'any_text': ['精确断言']}]}
    result = rt.text_guard('ch86_last_night_v04', contract, '精确断言')
    assert result['status'] == 'WARN'
    assert result['checks'][0]['epistemic_status'] == 'does_not_know'
