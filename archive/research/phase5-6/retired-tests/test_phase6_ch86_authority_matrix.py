"""Registration, exact location and interpretive authority remain separate axes."""
import json
from pathlib import Path

from rcwh.generation.records import bound_bytes

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'artifacts/agent_research/phase6/provenance'


def test_seven_source_matrix_preserves_inner_locator_fail_and_outer_pending():
    matrix = json.loads((BASE / 'ch86-source-authority-closure-matrix-v1.json').read_bytes())
    assert matrix['authority_effect'] == 'NONE'
    assert matrix['status'] == 'RESEARCH_PENDING_RELEASE_BLOCKED'
    for ref in matrix['evidence_basis']:
        bound_bytes(ROOT, ref)
    sources = json.loads((BASE / 'ch86-research-inputs-v2/sources.json').read_bytes())['sources']
    report = json.loads((BASE / 'ch86-research-inputs-v2/load-report.json').read_bytes())
    reports = {row['source_id']: row for row in report['source_reports']}
    assert report['integrity_status'] == 'PASS'
    assert report['status'] == report['evidence_readiness'] == 'PENDING'
    assert len(matrix['rows']) == len(sources) == 7
    for source, row in zip(sources, matrix['rows'], strict=True):
        assert row['source_id'] == source['id']
        assert row['source_type'] == source['type']
        assert row['container'] == source['container']
        assert row['exact_quote'] == source['text']
        assert row['quote_sha256'] == source['text_sha256']
        assert row['declared_locator_status'] == 'UNVERIFIED'
        assert row['computed_source_status'] == row['computed_locator_status'] == 'FAIL'
        assert row['computed_findings'] == reports[source['id']]['computed_source_report']['findings']
        assert row['research_evidence_status'] == 'PENDING'
        assert row['interpretive_review_status'] == 'NOT_QUALIFIED'
        assert row['human_qualification'] == 'NOT_PERFORMED'
        assert row['provenance_source_registration'] == 'NOT_PERFORMED'
        assert row['current_disposition'] == 'RESEARCH_ONLY_PENDING_NO_GATE_CLOSURE'
    assert matrix['counts'] == {
        'records': 7, 'registered_distinct_carriers': 4,
        'new_unregistered_shared_manifests': 1, 'claims': 0,
        'qualified_human_reviews': 0, 'independent_textual_witnesses_added': 0,
    }
    assert matrix['shared_extraction']['registered_locator_pass'] is False
    assert matrix['source_or_asset_registration_performed'] is False
    assert matrix['source_graph_changed'] is False
    assert matrix['admission_policy_changed'] is False
    assert matrix['build_called'] is False
    assert matrix['stable_active_effect'] == 'NONE'
    scope = json.loads(bound_bytes(ROOT, matrix['unchanged_old_scope_evidence']))
    assert len(scope['scope_after']['findings']) == 3
    evaluation = json.loads(bound_bytes(ROOT, matrix['unchanged_release_evaluation']))
    assert evaluation['status'] == 'FAIL'
    assert any('ResearchSourceInputs' in rule and 'PENDING' in rule for rule in matrix['layer_rules'])
