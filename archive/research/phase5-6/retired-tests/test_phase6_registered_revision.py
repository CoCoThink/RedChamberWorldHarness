"""Native import success must not erase the actual negative reading."""
import json
from pathlib import Path

import pytest

from rcwh.candidate_reviews import digest
from rcwh.generation.records import bound_bytes
from rcwh.schema import validate_instance

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'artifacts/agent_research/phase6/revisions-v2'


@pytest.mark.parametrize('chapter,expected_sha', [
    (81, 'a92799e04f61fdd2e99eb6eba99b38a7fa87ef2f5d137fc4eb1fdc681bccda0d'),
    (91, '751bca67b2e72bd13883a8ee2331baaf60878967b3c4f276b277e7cc2b11c602'),
])
def test_completed_native_import_has_exact_long_candidate_and_short_parent(chapter, expected_sha):
    receipt = json.loads((BASE / f'imports/ch{chapter}-v1-direct.json').read_bytes())
    draft = json.loads(bound_bytes(ROOT, receipt['result']['draft']))
    parent = json.loads(bound_bytes(ROOT, draft['parent']))
    assert receipt['status'] == 'PASS' and receipt['literary_acceptance'] == 'NOT_GRANTED'
    assert draft['candidate']['sha256'] == expected_sha
    assert len(bound_bytes(ROOT, draft['candidate']).decode('utf-8')) >= 9000
    assert len(bound_bytes(ROOT, parent['candidate']).decode('utf-8')) < 3000
    assert parent['parent'] is None
    assert parent['package'] == draft['package']
    assert draft['formal_eligibility'] is False and draft['human_qualification'] is False


def test_registered_ch91_long_v1_retains_exact_short_parent_and_negative_feedback():
    receipt = json.loads((BASE / 'imports/ch91-v1-direct.json').read_bytes())
    assert receipt['status'] == 'PASS' and receipt['literary_acceptance'] == 'NOT_GRANTED'
    assert receipt['scope'] == 'NORMAL_IMPORT_DRAFT_IN_ORIGINAL_REPOSITORY'
    assert len(receipt['retained_local_failures']) == 2
    result = receipt['result']
    draft = json.loads(bound_bytes(ROOT, result['draft']))
    run = json.loads(bound_bytes(ROOT, draft['run']))
    request = json.loads(bound_bytes(ROOT, draft['prepared_request']))
    assert not validate_instance(draft, ROOT / 'schemas/draft_registry.schema.json')
    assert draft['parent'] == request['parent']
    parent = json.loads(bound_bytes(ROOT, draft['parent']))
    assert parent['parent'] is None
    assert parent['package'] == draft['package']
    assert draft['candidate']['sha256'] == '751bca67b2e72bd13883a8ee2331baaf60878967b3c4f276b277e7cc2b11c602'
    assert run['output'].encode('utf-8') == bound_bytes(ROOT, draft['candidate'])
    assert draft['formal_eligibility'] is False and draft['human_qualification'] is False
    assert run['session_configured_model']['basis'] == 'UNVERIFIED_DECLARATION'
    assert request['request']['model'] != run['session_configured_model']['label']
    assert 'provider' not in run and 'usage' not in run

    repair = json.loads((BASE / 'ch91-v2-preparation-inputs.json').read_bytes())
    assert repair['parent'] == result['draft']
    feedback = json.loads(bound_bytes(ROOT, repair['feedback']))
    assert not validate_instance(feedback, ROOT / 'schemas/writing_feedback.schema.json')
    assert feedback['draft'] == result['draft']
    assert feedback['candidate'] == draft['candidate']
    assert feedback['inputs'] == draft['inputs']
    assert feedback['checks'][0]['status'] == 'FAIL'
    assert len(feedback['checks'][0]['findings']) == 2
    reader = json.loads(bound_bytes(ROOT, repair['reader_report']))
    assert reader['overall_assessment']['confirmed_local_fail_count'] == 2
    assert digest(bound_bytes(ROOT, repair['notes'])) == repair['notes']['sha256']


def test_registered_ch91_v2_keeps_real_two_step_long_revision_lineage():
    receipt = json.loads((BASE / 'imports/ch91-v2-direct.json').read_bytes())
    first = json.loads((BASE / 'imports/ch91-v1-direct.json').read_bytes())
    revised = json.loads(bound_bytes(ROOT, receipt['result']['draft']))
    long_parent = json.loads(bound_bytes(ROOT, revised['parent']))
    short_parent = json.loads(bound_bytes(ROOT, long_parent['parent']))
    assert receipt['status'] == 'PASS' and receipt['literary_acceptance'] == 'NOT_GRANTED'
    assert revised['parent'] == first['result']['draft']
    assert short_parent['parent'] is None
    assert revised['package'] == long_parent['package'] == short_parent['package']
    assert revised['candidate']['sha256'] == '0bf1f11f7a53f2112ac8eeaa21d166cf26737b7e29415de9f2624e808d22a6a1'
    feedback = json.loads(bound_bytes(ROOT, revised['feedback']))
    assert feedback['draft'] == first['result']['draft']
    assert feedback['checks'][0]['status'] == 'FAIL'
    assert len(feedback['checks'][0]['findings']) == 2
    original = json.loads(bound_bytes(ROOT, receipt['original_negative_reading_retained']))
    followup = json.loads(bound_bytes(ROOT, receipt['same_reader_followup']))
    assert original['overall_assessment']['confirmed_local_fail_count'] == 2
    assert followup['review_relationship'] == 'SAME_READER_FOLLOWUP_NOT_ADDITIONAL_INDEPENDENT_REVIEWER'
    assert revised['formal_eligibility'] is False and revised['human_qualification'] is False


def test_failed_snapshot_attempt_remains_distinct_from_successful_native_import():
    failed = json.loads((BASE / 'ch91-v1-import-attempt1.json').read_bytes())
    assert failed['status'] == 'FAIL_INPUT_DRIFT_NO_COPYBACK'
    assert failed['copyback_reached'] is False
    assert failed['changed_snapshot_input'].endswith('ch81-v1.txt')
    success = json.loads((BASE / 'imports/ch91-v1-direct.json').read_bytes())
    assert failed['candidate']['sha256'] == success['result']['candidate']['sha256']
    assert success['scope'] == 'NORMAL_IMPORT_DRAFT_IN_ORIGINAL_REPOSITORY'
