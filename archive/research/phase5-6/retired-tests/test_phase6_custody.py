"""Frozen research custody is not full-chapter or provider qualification."""
import json
from pathlib import Path

from rcwh.candidate_reviews import canonical_bytes, digest
from rcwh.generation.records import bound_bytes

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = 'artifacts/agent_research/phase6/authored-v3/custody-inventory-v1.json'


def test_twenty_short_candidates_have_exact_revision_parents_and_feedback():
    inventory = json.loads((ROOT / INVENTORY).read_bytes())
    assert [row['chapter'] for row in inventory['chapters']] == list(range(81, 101))
    assert inventory['fresh_renderer_replayed_in_this_inventory'] is False
    batches = set()
    total = 0
    for row in inventory['chapters']:
        draft = json.loads(bound_bytes(ROOT, row['draft']))
        run = json.loads(bound_bytes(ROOT, row['author_run']))
        text = bound_bytes(ROOT, row['candidate']).decode('utf-8')
        request = json.loads(bound_bytes(ROOT, row['revision_request']))
        feedback = json.loads(bound_bytes(ROOT, row['feedback']))
        assert draft['parent'] is None
        assert draft['candidate'] == run['candidate'] == row['candidate']
        assert text == run['output']
        assert draft['package'] == request['package']
        assert request['parent'] == row['draft'] == feedback['draft']
        assert request['feedback'] == row['feedback']
        assert feedback['candidate'] == row['candidate']
        assert feedback['inputs'] == draft['inputs']
        assert request['context']['revision_template'] == 'revise-v2'
        assert request['template']['path'] == 'data/writing/prompts/revise-v2.md'
        for binding in request['inputs'] + [request['template'], request['package']]:
            bound_bytes(ROOT, binding)
        prompt = {'system': bound_bytes(ROOT, request['template']).decode('utf-8'),
                  'messages': [{'role': 'user', 'content': canonical_bytes(request['task']).decode('utf-8')}]}
        assert digest(canonical_bytes(prompt)) == request['prompt_sha256']
        assert digest(canonical_bytes(request['request'])) == request['request_sha256']
        assert row['readiness'] == 'SHORT_CANDIDATE_NOT_FULL_CHAPTER'
        assert row['characters'] == len(text) < 3000
        assert row['target_characters'] == 9000
        assert draft['formal_eligibility'] is False and draft['human_qualification'] is False
        batches.add(row['actual_author_batch'])
        total += len(text)
    assert total == 40767
    assert len(batches) == 4
    assert 'NOT_TWENTY_INDEPENDENT_AUTHORS' in inventory['author_independence']


def test_original_v3_predecessors_are_not_retroactively_claimed():
    inventory = json.loads((ROOT / INVENTORY).read_bytes())
    for row in inventory['chapters']:
        draft = json.loads(bound_bytes(ROOT, row['draft']))
        request = json.loads(bound_bytes(ROOT, draft['prepared_request']))
        assert request['context']['previous_path'] is None
        assert request['task']['previous_ending'] is None
        assert request['parent'] is None


def test_new_editorial_requests_bind_actual_notes_without_rebinding_old_requests():
    directory = ROOT / 'artifacts/agent_research/phase6/revisions-v2/editorial-requests-v1'
    report = json.loads((directory / 'preparation-report.json').read_bytes())
    custody = json.loads((directory / 'snapshot-custody.json').read_bytes())
    inventory = json.loads((ROOT / INVENTORY).read_bytes())
    old = {row['chapter']: row for row in inventory['chapters']}
    assert [row['chapter'] for row in report['chapters']] == list(range(81, 101))
    assert custody['changed_original_inputs'] == []
    assert custody['status'] == 'PASS'
    for row in report['chapters']:
        request = json.loads(bound_bytes(ROOT, row['request']))
        previous = json.loads(bound_bytes(ROOT, old[row['chapter']]['revision_request']))
        assert row['integrity']['status'] == 'PASS'
        assert request['parent'] == previous['parent'] == row['draft']
        assert request['feedback'] == previous['feedback'] == row['feedback']
        assert request['package'] == previous['package']
        assert previous['context']['notes_path'] is None
        assert request['context']['notes_path'] == row['notes']['path']
        assert request['task']['editorial_notes'] == bound_bytes(ROOT, row['notes']).decode('utf-8')
        assert row['notes'] in request['inputs']
        assert request['prompt_sha256'] != previous['prompt_sha256']
        prompt = {'system': bound_bytes(ROOT, request['template']).decode('utf-8'),
                  'messages': [{'role': 'user', 'content': canonical_bytes(request['task']).decode('utf-8')}]}
        assert digest(canonical_bytes(prompt)) == request['prompt_sha256']
        assert digest(canonical_bytes(request['request'])) == request['request_sha256']
    for name, expected in custody['output_hashes'].items():
        assert digest((directory / name).read_bytes()) == expected
