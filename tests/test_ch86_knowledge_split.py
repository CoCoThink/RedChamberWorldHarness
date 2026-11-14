import json
from pathlib import Path

import pytest

from rcwh.generation.local_scenario import compile_scenario, verify_material

ROOT = Path(__file__).resolve().parents[1]
NEW = ROOT / 'data/writing/local-scenarios/ch86-v3'


def test_split_replay_does_not_invent_precision():
    model = json.loads((NEW / 'scenario.json').read_bytes())
    cp = compile_scenario(model)['checkpoints']
    for fact in ('death_occurred', 'death_relative_account'):
        assert cp['unfinished_revision']['values'][f'actor.zijuan.knowledge.{fact}'] == 'NOT_KNOWN'
        assert cp['death_witnessed']['values'][f'actor.zijuan.knowledge.{fact}'] == 'KNOWS'
        for point in ('baoyu_arrives', 'baoyu_asks_rewarm'):
            assert cp[point]['values'][f'actor.baoyu.knowledge.{fact}'] == 'NOT_KNOWN'
        assert cp['baoyu_learns_death_account']['values'][f'actor.baoyu.knowledge.{fact}'] == 'KNOWS'
    for actor in ('zijuan', 'baoyu'):
        for fact in ('death_precise_time', 'death_physiological_detail'):
            assert all(c['values'][f'actor.{actor}.knowledge.{fact}'] == 'UNKNOWN' for c in cp.values())
    assert cp['body_care_started']['values']['actor.baoyu.knowledge.critical_decline'] == 'UNKNOWN_AT_UNORDERED_CUT'
    assert cp['baoyu_receives_critical_message']['values']['actor.daiyu.life_state'] == 'UNKNOWN_AT_UNORDERED_CUT'


def test_precision_cannot_be_smuggled_into_message():
    model = json.loads((NEW / 'scenario.json').read_bytes())
    next(m for m in model['messages'] if m['id'] == 'death-account-notice')['facts'].append('death_precise_time')
    with pytest.raises(ValueError):
        compile_scenario(model)


def test_package_preserves_original_declarations_and_obligations():
    package = json.loads((ROOT / 'data/writing/packages/ch86-local-scenario-v3.json').read_bytes())
    model, _, contracts = verify_material(ROOT, package)
    previous = json.loads((ROOT / 'data/writing/local-scenarios/ch86-v2/scenario.json').read_bytes())
    assert model['original_declarations'] == previous['original_declarations']
    for _, contract in contracts:
        old = json.loads((ROOT / f'data/writing/local-scenarios/ch86-v2/contracts/{contract["id"]}.v3.json').read_bytes())
        for key in ('original_declarations', 'required_beats', 'forbidden_beats'):
            assert contract[key] == old[key]
