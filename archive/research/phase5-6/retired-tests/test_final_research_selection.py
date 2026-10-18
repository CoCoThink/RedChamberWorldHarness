"""Final reading choices bind genuine revisions without changing packages or gates."""
import json
from pathlib import Path

from rcwh.generation.records import bound_bytes
from rcwh.workflow.agent_panel import verify_packet
from rcwh.candidate_reviews import digest

ROOT = Path(__file__).resolve().parents[1]
BASE = 'artifacts/agent_research/phase6/advancement'


def test_final_selection_preserves_all20_and_exact_real_revision_lineage():
    frozen = json.loads((ROOT / f'{BASE}/m2-input-freeze-v3/freeze.json').read_bytes())
    selection = json.loads((ROOT / f'{BASE}/final-selection-v1.json').read_bytes())
    assert [row['chapter'] for row in selection['chapters']] == list(range(81, 101))
    assert selection['status'] == 'NOT_ADOPTED_NOT_RELEASED'
    assert selection['independent_human_admission'] is False
    for row in selection['chapters']:
        chapter = row['chapter']
        old = frozen['chapters'][str(chapter)]
        assert row['package'] == old['package']
        assert row['policy'] == old['policy']
        draft = json.loads(bound_bytes(ROOT, row['draft']))
        assert draft['chapter'] == chapter
        assert draft['candidate'] == row['candidate']
        assert draft['package'] == row['package']
        bound_bytes(ROOT, row['candidate'])
        if chapter in (86, 94, 95, 99):
            receipt = json.loads(bound_bytes(ROOT, row['import_receipt']))
            assert receipt['status'] == 'PASS' and receipt['changed_original_inputs'] == []
            assert receipt['result']['draft'] == row['draft']
            assert receipt['result']['candidate'] == row['candidate']
            if chapter == 99:
                pilot = json.loads((ROOT / f'{BASE}/pilot-imports-v1/ch99.json').read_bytes())
                assert draft['parent'] == pilot['result']['draft']
            elif chapter == 86:
                assert draft['parent'] == frozen['pilot_parents']['86']['draft']
            else:
                assert draft['parent'] == old['draft']
        else:
            assert row['candidate'] == old['candidate'] and row['draft'] == old['draft']
        assert row['selection_effect'] == 'READING_ONLY_NOT_ADOPT'
    for ref in selection['retained_negatives']:
        bound_bytes(ROOT, ref)


def test_final_packet_contains_exact_four_changed_packages_and20_contracts():
    path = f'{BASE}/final-packet-v1.json'
    packet = verify_packet(ROOT, {'path': path, 'sha256': digest((ROOT / path).read_bytes())})
    subjects = packet['subjects']
    assert len(subjects) == 44
    assert len([s for s in subjects if s['scope'] == 'CANDIDATE']) == 20
    assert len([s for s in subjects if s['scope'] == 'PACKAGE']) == 4
    assert len([s for s in subjects if s['scope'] == 'CONTRACT']) == 20
    for ch in (86, 94, 95, 99):
        pkg = next(s for s in subjects if s['id'] == f'package-{ch}')
        value = json.loads(bound_bytes(ROOT, pkg['binding']))
        for ref in value['plan']:
            if ref['path'].startswith('data/planning/contracts/'):
                assert any(s['scope'] == 'CONTRACT' and s['binding'] == ref for s in subjects)
    assert all('samples' not in s for s in subjects)
