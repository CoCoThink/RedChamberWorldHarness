"""The v6 scenario adds only the review-dispositioned care/departure edge."""
import importlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_care_order_v6_is_a_single_bound_refinement(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / 'tools'))
    module = importlib.import_module('prepare_ch86_care_order_v6')
    result = module.verify(ROOT)
    manifest = json.loads((ROOT / module.OUTPUT / 'manifest.json').read_bytes())
    old = json.loads((ROOT / 'data/writing/local-scenarios/ch86-v5/scenario.json').read_bytes())
    new = json.loads((ROOT / module.SCENARIO).read_bytes())
    assert result['status'] == 'PASS' and result['semantic_status'] == 'PENDING'
    assert new == module.amend(old)
    assert manifest['added_edges'] == [['liwan_takes_care', 'baoyu_departs']]
    assert manifest['removed_unconstrained_pairs'] == [['liwan_takes_care', 'baoyu_departs']]
    assert manifest['production_admission'] == 'NOT_GRANTED'
