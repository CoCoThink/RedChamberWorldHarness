from pathlib import Path

from rcwh.io import load_data
from rcwh.runtime import WorldState


def root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_scene_preconditions_pass():
    state = WorldState.from_repo(root())
    contract = load_data(root() / "data/scenes/ch86_last_night.yaml")
    assert state.assert_contract_preconditions(contract) == []
