from pathlib import Path

from rcwh.io import load_data
from rcwh.runtime import WorldState


def root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_scene_preconditions_pass():
    state = WorldState.from_repo(root())
    contract = load_data(root() / "data/scenes/ch86_last_night.yaml")
    assert state.assert_contract_preconditions(contract) == []


def test_scene_preconditions_do_not_require_full_world_files(tmp_path):
    import shutil

    for directory in ("characters", "objects"):
        shutil.copytree(root() / "data" / directory, tmp_path / "data" / directory)
    state = WorldState.from_repo(tmp_path)
    contract = load_data(root() / "data/scenes/ch86_last_night.yaml")
    assert state.assert_contract_preconditions(contract) == []
    state.characters["daiyu"]["resources"]["physical_strength"] = "recovered"
    assert state.assert_contract_preconditions(contract)


def test_unknown_namespace_fails_scene_precondition():
    state = WorldState.from_repo(root())
    errors = state.assert_contract_preconditions({"preconditions": [
        {"equals": "metadata.approved", "value": True},
        {"equals": "characters.daiyu.resources.physical_strength", "value": "critical"},
    ]})
    assert len(errors) == 2
    assert all("Unknown scene state namespace" in error for error in errors)
