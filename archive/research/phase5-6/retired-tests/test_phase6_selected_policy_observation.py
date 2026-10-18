"""Actual frozen candidate loss cannot be hidden by local reading success."""
import json
from pathlib import Path

from rcwh.agent_policies import evaluate_agent_policy
from rcwh.generation.records import bound_bytes

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'artifacts/agent_research/phase6/revisions-v2'


def test_actual_selected_policy_gates_retain_ch86_exact_anchor_failure():
    report = json.loads((BASE / 'selected-policy-gate-observation-v1.json').read_bytes())
    assert report['literary_acceptance'] == 'NOT_GRANTED'
    assert [row['chapter'] for row in report['chapters']] == list(range(81, 101))
    assert {row['chapter'] for row in report['chapters'] if row['status'] == 'FAIL'} == {86}
    assert sum(row['status'] == 'PENDING' for row in report['chapters']) == 19
    for row in report['chapters']:
        assert row['error'] is None
        policy = json.loads(bound_bytes(ROOT, row['policy']))
        text = bound_bytes(ROOT, row['candidate']).decode('utf-8')
        checked = evaluate_agent_policy(ROOT, policy, row['chapter'], text)
        assert checked['status'] == row['status']
        assert checked['automatic_policy_pass'] is False


def test_actual_all_package_scopes_keep_25_sources_and_ch86_carrier_blockers():
    report = json.loads((BASE / 'selected-package-scope-observation-v1.json').read_bytes())
    assert report['distinct_reported_source_count'] == 25
    assert len(report['distinct_reported_source_ids']) == 25
    assert [row['chapter'] for row in report['chapters']] == list(range(81, 101))
    for row in report['chapters']:
        bound_bytes(ROOT, row['package'])
        assert row['execution_error'] is None
        assert row['scope']['chapter'] == row['chapter']
        assert row['scope']['advisory_contract_paths']
        if row['chapter'] == 86:
            assert len(row['scope']['findings']) == 3
            assert all(item.startswith('UNRESOLVED_DEPENDENT_SOURCE_ASSET:') for item in row['scope']['findings'])
        else:
            assert row['scope']['findings'] == []


def test_ch86_task_exposure_gap_does_not_waive_actual_anchor_failures():
    report = json.loads((BASE / 'ch86-plock-task-exposure-v1.json').read_bytes())
    request = json.loads(bound_bytes(ROOT, report['request']))
    notes = bound_bytes(ROOT, report['notes']).decode('utf-8')
    assert report['gate_effect'].startswith('NONE; actual candidate FAIL retained')

    def contains(value, phrase):
        if isinstance(value, str):
            return phrase in value
        if isinstance(value, dict):
            return any(contains(child, phrase) for child in value.values())
        if isinstance(value, list):
            return any(contains(child, phrase) for child in value)
        return False

    for row in report['exact_anchor_occurrences']:
        assert row['task_string_leaf_occurrences'] == []
        assert not contains(request['task'], row['text'])
        assert row['text'] not in notes
    assert 'P-Lock' in notes
    diagnostic = json.loads(bound_bytes(ROOT, report['original_gate_diagnostic']))
    assert diagnostic['agent_policy']['status'] == 'FAIL'


def test_original_ch86_anchor_losses_remain_fail_not_semantic_paraphrase_pass():
    report = json.loads((BASE / 'ch86-policy-gate-diagnostic-v1.json').read_bytes())
    assert report['disposition'] == 'FAIL_RETAINED_NO_WAIVER'
    policy = report['agent_policy']
    assert policy['status'] == policy['anchor_status'] == 'FAIL'
    assert policy['semantic_status'] == 'PENDING'
    assert len(policy['findings']) == 2
    legacy = report['mandatory_legacy_plock']
    assert legacy['machine_status'] == 'REPLACEMENT_CASE'
    assert legacy['automatic_literary_pass'] is False
    assert legacy['protected_anchor_losses'] == [
        '药不是还没吃么？再温一温。今儿早起她还说药苦。',
        '那盏药早已冷透，再没有人去温。',
    ]
    text = bound_bytes(ROOT, report['candidate']).decode('utf-8')
    assert all(anchor not in text for anchor in legacy['protected_anchor_losses'])
    assert legacy['evidence_core_regression'] == 'PASS'
    assert report['literary_acceptance'] == 'NOT_GRANTED'
