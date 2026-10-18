"""Real anonymous opinions stay unverified, with exact quotes and old negatives."""
import importlib.util
import json
from pathlib import Path

from rcwh.generation.records import bound_bytes
from rcwh.workflow.agent_panel import AgentPanel

ROOT = Path(__file__).resolve().parents[1]
BASE = 'artifacts/agent_research/phase6/advancement'
SPEC = importlib.util.spec_from_file_location('actual_readings', ROOT / 'tools/check_pilot_readings.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_actual_two_readers_exact_quotes_complete_declarations_and_raw_correction():
    custody = json.loads((ROOT / f'{BASE}/pilot-reading-custody-v1.json').read_bytes())
    authors = set()
    for chapter in (86, 95, 99):
        receipt = json.loads((ROOT / f'{BASE}/pilot-imports-v1/ch{chapter}.json').read_bytes())
        ref = receipt['result']['draft']
        while ref is not None:
            draft = json.loads(bound_bytes(ROOT, ref))
            run = json.loads(bound_bytes(ROOT, draft['run']))
            authors.add(run['session_id'])
            ref = draft['parent']
    report = MODULE.check(ROOT, custody['packet'], custody['submissions'], authors)
    assert report['status'] == custody['status']
    assert sum(row['quote_count'] for row in report['readers']) == 90
    assert all(row['raw_verdicts'] == ['UNVERIFIED'] * 6 for row in report['readers'])
    assert all(not row['reviewer']['context_isolation']['asserted'] for row in report['readers'])
    correction = json.loads(bound_bytes(ROOT, custody['submissions'][1]['scope_correction']))
    assert correction['raw_observations'] == custody['submissions'][1]['observations']
    assert correction['literary_opinions_changed'] is False


def test_actual_panel_preserves_unverified_without_manufacturing_full_reviewers():
    custody = json.loads((ROOT / f'{BASE}/pilot-reading-custody-v1.json').read_bytes())
    report = AgentPanel(ROOT).summary(packet=custody['packet'])
    assert report['status'] == 'PENDING' and report['record_integrity_status'] == 'PASS'
    subjects = report['panels'][0]['subjects']
    assert len(subjects) == 6
    for subject in subjects:
        assert subject['status'] == 'PENDING'
        assert subject['review_count'] == 2 and subject['distinct_reviewer_count'] == 0
        assert [opinion['verdict'] for opinion in subject['opinions']] == ['UNVERIFIED'] * 2
    for submitted in custody['submissions']:
        opinion = json.loads(bound_bytes(ROOT, submitted['opinion']))
        assert opinion['independent_human_admission'] is False
    raw = json.loads(bound_bytes(ROOT, custody['submissions'][1]['observations']))
    ch99 = next(row for row in raw['chapters'] if row['chapter'] == 99)
    assert ch99['continuity_contradictions'][0]['status'] == 'APPARENT_LOCAL_CONTINUITY_CONTRADICTION'
