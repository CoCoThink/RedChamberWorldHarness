"""The v5 review uses its exact CI/model inputs and preserves prior negatives."""
import importlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def review(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / 'tools'))
    return importlib.import_module('verify_ch86_care_order_review')


def test_prepared_v5_tasks_bind_current_model_and_do_not_expose_peer_opinion(review):
    plan = json.loads((ROOT / review.REVIEW / 'plan.json').read_bytes())
    manifest = json.loads((ROOT / review.amendment.OUTPUT / 'manifest.json').read_bytes())
    previous = json.loads((ROOT / review.previous.REVIEW / 'execution.json').read_bytes())
    prior = {a['job_id']: a for a in previous['attempts']}
    assert plan['input_commit'] == '5da0767708372da65003b6858f7d1f124eafbf41'
    assert plan['independent_opinions_added'] == 0 and plan['independent_model_readers_total'] == 2
    for ref in plan['tasks']:
        task = json.loads((ROOT / ref['path']).read_bytes())
        assert manifest['scenario'] in task['read_inputs']
        assert manifest['candidate'] in task['read_inputs']
        assert task['context_mode'] == 'REUSED_SAME_ORIGINAL_READER'
        assert task['expected_reader'] == prior[task['job_id']]['agent']
        assert prior['semantic-1' if task['job_id'] == 'semantic-2' else 'semantic-2']['raw_opinion'] not in task['read_inputs']
        budget = task['budget']
        assert budget['reserved_total_bytes'] == budget['read_bytes'] + 32768 <= budget['maximum_bytes']


def test_completed_v5_review_retains_prior_verdicts_and_does_not_grant_production(review):
    try:
        result = review.verify(ROOT)
    except FileNotFoundError:
        pytest.skip('v5 reviewers have not submitted yet')
    assert result['status'] == 'PASS'
    assert result['independent_model_readers'] == 2 and result['independent_opinions_added'] == 0
    assert result['citation_errata_verified'] is True
    assert len(result['citation_discrepancies']) == 1
    assert result['production_admission'] == 'NOT_GRANTED'
