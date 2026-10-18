from copy import deepcopy
from types import SimpleNamespace

import pytest

from rcwh.assets import AssetError
from test_agent_release import edition, write


def test_agent_policy_plock_binding_must_match_declared_protection(edition, monkeypatch):
    e = edition
    row = deepcopy(e.request['chapters'][0])
    policy = {'plock': {'required': True, 'ref': row['plock_ref']}}
    row['policy'] = write(e.root, 'data/promotion/policies/agent/ch86.v1.json', policy)
    row['plock_ref'] = 'NONE'
    monkeypatch.setattr('rcwh.agent_policies.evaluate_agent_policy', lambda *args: {'status': 'PENDING'})
    with pytest.raises(AssetError, match='P-Lock differs'):
        e.runtime._policy(row, {86}, 'book', 'chapter')


@pytest.mark.parametrize('policy_status,plock_status,expected', [
    ('FAIL', 'READY_FOR_BLIND_READ', 'FAIL'),        # blocking anchor/integrity failure
    ('PASS', 'REPLACEMENT_CASE', 'PASS'),            # lost P-Lock anchor is advisory
    ('PASS', 'INFRASTRUCTURE_BLOCKED', 'PENDING'),   # P-Lock inputs unavailable
    ('PASS', 'READY_FOR_BLIND_READ', 'PASS')])
def test_agent_policy_follows_evidence_floor(edition, monkeypatch, policy_status, plock_status, expected):
    e = edition
    row = deepcopy(e.request['chapters'][0])
    policy = {'plock': {'required': True, 'ref': row['plock_ref']}}
    row['policy'] = write(e.root, 'data/promotion/policies/agent/ch86.v1.json', policy)
    monkeypatch.setattr('rcwh.agent_policies.evaluate_agent_policy', lambda *args: {'status': policy_status})
    monkeypatch.setattr('rcwh.literary_eval.evaluate_literary_candidate', lambda *args, **kwargs: {
        'machine_status': plock_status})
    assert e.runtime._policy(row, {86}, 'book', 'chapter') == expected
