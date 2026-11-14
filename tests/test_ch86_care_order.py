"""Care-order repairs constrain prose order without inventing knowledge or total order."""
import importlib
import json
from pathlib import Path

from rcwh.generation.local_scenario import compile_scenario

ROOT = Path(__file__).resolve().parents[1]


def test_care_precedes_triggered_observation_and_arrival(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / 'tools'))
    amendment = importlib.import_module('prepare_ch86_care_order')
    assert amendment.verify(ROOT)['semantic_status'] == 'PENDING'
    model = json.loads((ROOT / amendment.SCENARIO).read_bytes())
    checkpoints = compile_scenario(model)['checkpoints']
    for event in ('runner_observes_death', 'household_notices_sent', 'liwan_notified', 'wangfuren_notified'):
        assert 'body_care_started' in checkpoints[event]['events']
    assert 'liwan_takes_care' in checkpoints['baoyu_arrives']['events']
    assert 'liwan_takes_care' not in checkpoints['baoyu_departs']['events']
    assert 'baoyu_departs' not in checkpoints['liwan_takes_care']['events']
    for checkpoint in checkpoints.values():
        for actor in model['actors']:
            for fact in ('death_precise_time', 'death_physiological_detail', 'death_medical_cause'):
                assert checkpoint['values'][f'actor.{actor["id"]}.knowledge.{fact}'] == 'UNKNOWN'


def test_previous_model_really_allowed_the_rejected_order():
    model = json.loads((ROOT / 'data/writing/local-scenarios/ch86-v4/scenario.json').read_bytes())
    checkpoints = compile_scenario(model)['checkpoints']
    assert 'body_care_started' not in checkpoints['runner_observes_death']['events']
    assert 'runner_observes_death' not in checkpoints['body_care_started']['events']
    assert 'liwan_takes_care' not in checkpoints['baoyu_arrives']['events']
    assert all(not e['effects'] for e in model['events'] if e['id'] in ('liwan_takes_care', 'body_care_started'))
