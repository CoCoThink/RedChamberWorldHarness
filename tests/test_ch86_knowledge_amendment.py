"""A supported causal refinement must not manufacture medical knowledge."""
import importlib
import json
from pathlib import Path

import pytest

from rcwh.generation.local_scenario import compile_scenario

ROOT = Path(__file__).resolve().parents[1]


def test_amendment_preserves_uncertainty_and_supported_order(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / 'tools'))
    amendment = importlib.import_module('prepare_ch86_knowledge_amendment')
    assert amendment.verify(ROOT)['status'] == 'PASS'
    scenario = json.loads((ROOT / amendment.SCENARIO).read_bytes())
    checkpoints = compile_scenario(scenario)['checkpoints']
    for event in ('baoyu_arrives', 'wangfuren_notified'):
        assert checkpoints[event]['values']['actor.liwan.knowledge.death_occurred'] == 'KNOWS'
    for checkpoint in checkpoints.values():
        for actor in ('zijuan', 'baoyu'):
            for fact in ('death_precise_time', 'death_physiological_detail', 'death_medical_cause'):
                assert checkpoint['values'][f'actor.{actor}.knowledge.{fact}'] == 'UNKNOWN'


def test_notice_cannot_transmit_an_unestablished_medical_cause():
    scenario = json.loads((ROOT / 'data/writing/local-scenarios/ch86-v4/scenario.json').read_bytes())
    message = next(m for m in scenario['messages'] if m['id'] == 'death-account-notice')
    message['facts'].append('death_medical_cause')
    with pytest.raises(ValueError):
        compile_scenario(scenario)
