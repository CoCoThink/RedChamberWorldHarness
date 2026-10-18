"""Final audit compares frozen engineering outcomes without granting adoption."""
import json
from pathlib import Path

from rcwh.generation.records import bound_bytes

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'artifacts/agent_research/phase6/revisions-v2'


def test_final_audit_keeps_exact_candidate_bindings_and_original_failures():
    audit = json.loads((BASE / 'final-audit-v1.json').read_bytes())
    assert audit['status'] == 'FAIL_NOT_ADOPTED_NOT_RELEASED'
    assert audit['authority_effect'] == 'NONE'
    assert audit['same_release_request'] is True
    assert audit['prior_report_retained'] is True
    assert audit['v2_and_v3_evaluation_report_bytes_equal'] is True
    for ref in audit['records']:
        bound_bytes(ROOT, ref)
    assert [row['chapter'] for row in audit['chapter_gate_comparison']] == list(range(81, 101))
    for row in audit['chapter_gate_comparison']:
        assert row['exact_candidate_and_bound_inputs_unchanged'] is True
        assert row['before_status'] == row['after_status'] == 'FAIL'
        if row['chapter'] == 86:
            assert row['gate_changes'] == {}
            assert row['before_findings'] == row['after_findings']
        else:
            assert row['gate_changes']['WRITING_PACKAGE'] == {'before': 'FAIL', 'after': 'PASS'}
            assert row['gate_changes']['CORPUS_PEERS'] == {'before': 'PENDING', 'after': 'FAIL'}
            assert row['after_findings'] == []
    assert audit['corrected_snapshot']['input_drift'] == []
    assert audit['protected_originals'] == {'checked': 325, 'changed': []}
    assert audit['publication']['build_called'] is False
    assert audit['publication']['release_directory_present'] is False
    assert audit['publication']['stable_active_effect'] == 'NONE'
    assert audit['publication']['stable_v15'] == 'PROPOSAL_ONLY_NOT_ACTIVATED'
    assert audit['publication']['commit'] == audit['publication']['push'] == 'NOT_PERFORMED'
    assert len(audit['wrapper_failures_retained_as_execution_history']) == 5
    for key in ('result', 'pytest_log', 'validate'):
        bound_bytes(ROOT, audit['engineering_checkpoint'][key])
