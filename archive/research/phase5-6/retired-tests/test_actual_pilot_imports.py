"""Actual frozen pilots retain ordinary imports and exact anonymous copies."""
import json
from pathlib import Path

import pytest

from rcwh.candidate_reviews import digest
from rcwh.generation.records import bound_bytes
from rcwh.workflow.agent_panel import verify_packet

ROOT = Path(__file__).resolve().parents[1]
BASE = 'artifacts/agent_research/phase6/advancement'


@pytest.mark.parametrize('chapter', [86, 95, 99])
def test_actual_pilot_normal_import_preserves_request_parent_and_all_products(chapter):
    receipt = json.loads((ROOT / f'{BASE}/pilot-imports-v1/ch{chapter}.json').read_bytes())
    assert receipt['status'] == receipt['result']['status'] == 'PASS'
    assert receipt['changed_original_inputs'] == []
    assert receipt['scope'] == 'FRESH_SESSION_IMPORT_ON_BYTE_IDENTICAL_LINUX_SNAPSHOT'
    result = receipt['result']
    request = json.loads(bound_bytes(ROOT, receipt['request']))
    draft = json.loads(bound_bytes(ROOT, result['draft']))
    parent = json.loads(bound_bytes(ROOT, draft['parent']))
    assert draft['chapter'] == parent['chapter'] == request['chapter'] == chapter
    assert draft['parent'] == request['parent']
    assert draft['package'] == parent['package'] == request['package']
    assert bound_bytes(ROOT, receipt['text']) == bound_bytes(ROOT, result['candidate'])
    assert draft['candidate'] == result['candidate']
    assert len(receipt['output_hashes']) == 4
    for path, sha in receipt['output_hashes'].items():
        assert digest((ROOT / path).read_bytes()) == sha
    assert receipt['authority_effect'] == 'NONE'
    assert 'literary quality' in receipt['limitation']


def test_actual_anonymous_packet_has_six_exact_full_texts_and_counterbalanced_orders():
    path = f'{BASE}/pilot-comparison-v1/packet.json'
    packet = verify_packet(ROOT, {'path': path, 'sha256': digest((ROOT / path).read_bytes())})
    mapping = json.loads((ROOT / f'{BASE}/pilot-comparison-coordinator-v1/mapping.json').read_bytes())
    inventory = json.loads((ROOT / f'{BASE}/pilot-reading-inventory-v1.json').read_bytes())
    assert mapping['input_inventory'] == inventory
    assert len(packet['subjects']) == len(mapping['mapping']) == 6
    assert mapping['reader_orders'][0] == list(reversed(mapping['reader_orders'][1]))
    assert mapping['reader_orders'][0] == [row['id'] for row in packet['subjects']]
    for row in mapping['mapping']:
        assert bound_bytes(ROOT, row['public']) == bound_bytes(ROOT, row['original'])
    assert {(row['chapter'], row['role']) for row in mapping['mapping']} == {
        (chapter, role) for chapter in (86, 95, 99) for role in ('parent', 'pilot')}
    assert all('samples' not in subject for subject in packet['subjects'])
    assert not (ROOT / f'{BASE}/pilot-comparison-v1/mapping.json').exists()
