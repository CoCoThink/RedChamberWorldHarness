"""A follow-up must retain its original readers and cannot inflate independence."""
import importlib
import json
from pathlib import Path
import shutil

import pytest

from rcwh.candidate_reviews import canonical_bytes
from test_ch86_knowledge_review import copied_review  # noqa: F401

ROOT = Path(__file__).resolve().parents[1]
BASE = 'artifacts/local-scenario-ch86-knowledge-split/amendment-v1'


@pytest.fixture
def followup(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / 'tools'))
    return importlib.import_module('verify_ch86_knowledge_followup')


@pytest.fixture
def copied_followup(copied_review):
    paths = {BASE + '/review/plan.json', BASE + '/review/execution.json', BASE + '/review/disposition.json'}
    disposition = json.loads((ROOT / BASE / 'review/disposition.json').read_bytes())
    paths.add(disposition['amendment']['path'])
    plan = json.loads((ROOT / BASE / 'review/plan.json').read_bytes())
    execution = json.loads((ROOT / BASE / 'review/execution.json').read_bytes())
    manifest = json.loads((ROOT / plan['manifest']['path']).read_bytes())
    for field in ('input_ci', 'manifest', 'candidate', 'original_execution', 'repository_instructions'):
        paths.add(plan[field]['path'])
    for value in manifest.values():
        for ref in value if isinstance(value, list) else [value]:
            if isinstance(ref, dict) and 'path' in ref:
                paths.add(ref['path'])
    for ref in plan['tasks']:
        paths.add(ref['path'])
        task = json.loads((ROOT / ref['path']).read_bytes())
        paths.update(r['path'] for r in task['read_inputs'])
    paths.update(a['raw_opinion']['path'] for a in execution['attempts'])
    for path in paths:
        target = copied_review / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / path, target)
    return copied_review


def test_real_followup_preserves_original_judgments_and_reader_count(followup):
    result = followup.verify(ROOT)
    assert result['status'] == 'PASS'
    assert result['original_reader_verdicts'] == {'semantic-1': 'FAIL', 'semantic-2': 'FAIL'}
    assert result['independent_model_readers'] == 2 and result['independent_opinions_added'] == 0
    assert result['production_admission'] == 'NOT_GRANTED'


@pytest.mark.parametrize('fault', ['extra_independence', 'wrong_reader', 'fresh_context',
                                  'missing_attempt', 'unread_opinions', 'missing_read_binding', 'wrong_total'])
def test_followup_cannot_invent_independence_or_completion(followup, copied_followup, fault):
    path = copied_followup / BASE / 'review/execution.json'
    record = json.loads(path.read_bytes())
    if fault == 'extra_independence': record['independent_opinions_added'] = 2
    elif fault == 'wrong_reader': record['attempts'][0]['agent'] = '/root/another_reader'
    elif fault == 'fresh_context': record['attempts'][0]['context_fork'] = 'none'
    elif fault == 'missing_attempt': record['attempts'].pop()
    elif fault == 'unread_opinions': record['coordinator_read']['read_complete'] = False
    elif fault == 'wrong_total': record['independent_model_readers_total'] = 4
    else: record['coordinator_read']['opinion_bindings'].pop()
    path.write_bytes(canonical_bytes(record))
    with pytest.raises((AssertionError, ValueError)):
        followup.verify(copied_followup)


def test_followup_cannot_relabel_an_original_failure(followup, copied_followup):
    path = copied_followup / BASE / 'review/disposition.json'
    record = json.loads(path.read_bytes())
    row = next(r for r in record['findings'] if r['original_assessment'] == 'FAIL')
    row['original_assessment'] = 'PASS'
    path.write_bytes(canonical_bytes(record))
    with pytest.raises(AssertionError):
        followup.verify(copied_followup)
