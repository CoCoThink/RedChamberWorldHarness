"""Exact P-Lock restoration is a new narrow candidate, not a frozen FAIL rewrite."""
import json
from pathlib import Path

from rcwh.candidate_reviews import canonical_bytes, digest
from rcwh.generation.records import bound_bytes
from rcwh.schema import validate_instance

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'artifacts/agent_research/phase6/revisions-v2'


def test_ch86_v2_has_only_three_disclosed_replacements_and_real_long_parent():
    disclosure = json.loads((BASE / 'authored/ch86-v2-disclosure.json').read_bytes())
    request = json.loads(bound_bytes(ROOT, disclosure['request']))
    parent = json.loads(bound_bytes(ROOT, disclosure['parent']))
    old = bound_bytes(ROOT, parent['candidate']).decode('utf-8')
    text = bound_bytes(ROOT, disclosure['candidate']).decode('utf-8')
    assert len(disclosure['replacements']) == 3
    changed = old
    for row in disclosure['replacements']:
        assert changed.count(row['old']) == 1
        changed = changed.replace(row['old'], row['new'], 1)
    assert changed == text
    assert request['parent'] == disclosure['parent']
    assert request['package'] == parent['package']
    assert request['task']['original'] == old
    assert len(old) == 10195
    assert len(text) == disclosure['counts']['total_unicode_characters'] == 10182
    assert text.endswith('那盏药早已冷透，再没有人去温。\n')
    assert text.count('药不是还没吃么？再温一温。今儿早起她还说药苦。') == 1
    assert disclosure['execution_basis'] == 'SESSION_AUTHORED_NOT_PROVIDER_VERIFIED'
    assert disclosure['formal_eligibility'] is False and disclosure['human_qualification'] is False
    assert disclosure['literary_acceptance'] == 'NOT_GRANTED'
    feedback = json.loads(bound_bytes(ROOT, disclosure['feedback']))
    assert not validate_instance(feedback, ROOT / 'schemas/writing_feedback.schema.json')
    assert feedback['draft'] == disclosure['parent']
    assert feedback['candidate'] == parent['candidate']
    assert feedback['inputs'] == parent['inputs']
    assert feedback['checks'][0]['status'] == 'FAIL'
    assert len(feedback['checks'][0]['protected_anchor_losses']) == 2
    assert request['task']['editorial_notes'] == bound_bytes(ROOT, disclosure['notes']).decode('utf-8')
    prompt = {'system': bound_bytes(ROOT, request['template']).decode('utf-8'),
              'messages': [{'role': 'user', 'content': canonical_bytes(request['task']).decode('utf-8')}]}
    assert digest(canonical_bytes(prompt)) == request['prompt_sha256']


def test_ch86_v2_native_import_preserves_two_step_lineage_and_old_selection():
    receipt = json.loads((BASE / 'imports/ch86-v2-direct.json').read_bytes())
    original = json.loads((BASE / 'imports/ch86-v1-direct.json').read_bytes())
    assert receipt['status'] == 'PASS' and receipt['literary_acceptance'] == 'NOT_GRANTED'
    draft = json.loads(bound_bytes(ROOT, receipt['result']['draft']))
    assert draft['parent'] == original['result']['draft']
    parent = json.loads(bound_bytes(ROOT, draft['parent']))
    short = json.loads(bound_bytes(ROOT, parent['parent']))
    assert short['parent'] is None
    assert draft['package'] == parent['package'] == short['package']
    assert draft['candidate']['sha256'] == '493de9a83fa7aa24601c023397f462790fc7b3676f94bf2c66dfca1376fe99a1'
    assert bound_bytes(ROOT, draft['candidate']) == bound_bytes(ROOT, receipt['candidate_source'])
    assert draft['formal_eligibility'] is False and draft['human_qualification'] is False
    diagnostic = json.loads(bound_bytes(ROOT, receipt['original_negative_diagnostic_retained']))
    assert diagnostic['agent_policy']['status'] == 'FAIL'
    selection = json.loads(bound_bytes(ROOT, receipt['frozen_reading_selection_unchanged']))
    assert next(row for row in selection['chapters'] if row['chapter'] == 86)['revision'] == 'v1'


def test_ch86_literal_repair_keeps_policy_pending_and_original_selected_v1_fail():
    observation = json.loads((BASE / 'ch86-v2-mechanical-observation.json').read_bytes())
    original = json.loads((BASE / 'ch86-policy-gate-diagnostic-v1.json').read_bytes())
    assert original['agent_policy']['status'] == 'FAIL'
    assert observation['agent_policy']['anchor_status'] == 'PASS'
    assert observation['agent_policy']['status'] == 'PENDING'
    assert observation['legacy_plock']['protected_anchor_losses'] == []
    assert observation['legacy_plock']['machine_status'] == 'READY_FOR_BLIND_READ'
    assert observation['legacy_plock']['automatic_literary_pass'] is False
    assert observation['prose_integrity']['status'] == 'PASS'
    assert observation['literary_acceptance'] == 'NOT_GRANTED'
    selection = json.loads((BASE / 'continuity-reading-selection-v1.json').read_bytes())
    chapter86 = next(row for row in selection['chapters'] if row['chapter'] == 86)
    assert chapter86['revision'] == 'v1'
    assert chapter86['candidate'] == original['candidate']
