import json
import shutil
from pathlib import Path

import pytest

from rcwh.generation.knowledge_projection import (
    create, prepare_request, project, verify, verify_request,
)

ROOT = Path(__file__).resolve().parents[1]
SCENE = "ch86_last_night_v04"
CHECKPOINTS = ["ENTRY", "K86-V04-DEATH-WITNESSED",
               "K86-V04-BAOYU-LEARNS-DEATH-ACCOUNT"]


def _copy_minimal_repo(target):
    for relative in ("data/knowledge/v03_slice2.json", "data/knowledge/v04_ch86.json",
                     "src/rcwh/knowledge.py", "src/rcwh/knowledge_versions.py",
                     "src/rcwh/generation/knowledge_projection.py"):
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, destination)


def test_projection_binds_explicit_v04_version_and_narrow_scene():
    projection = project(ROOT, version="v0.4:ch86", scene_id=SCENE,
                         checkpoints=CHECKPOINTS)
    assert projection["knowledge_version"] == "v0.4:ch86"
    assert projection["carrier"]["path"] == "data/knowledge/v04_ch86.json"
    assert "daiyu_death_exact_moment" not in projection["fact_ids"]
    assert projection["checkpoints"]["ENTRY"] != projection["checkpoints"][CHECKPOINTS[-1]]
    assert projection["authority_effect"] == "NONE"
    assert projection["semantic_review"] == "NOT_COMPLETED"
    verify(ROOT, projection)


def test_projection_rejects_invalid_versions_and_duplicate_checkpoints():
    with pytest.raises(ValueError, match="unknown character knowledge version"):
        project(ROOT, version="latest", scene_id=SCENE, checkpoints=["ENTRY"])
    with pytest.raises(ValueError, match="unique"):
        project(ROOT, version="v0.4:ch86", scene_id=SCENE,
                checkpoints=["ENTRY", "ENTRY"])


def test_request_and_projection_are_immutable_and_not_production_admission(tmp_path):
    _copy_minimal_repo(tmp_path)
    task = {"purpose": "independent semantic review", "chapter": 86,
            "scope": "v0.4 knowledge facts and event state transitions"}
    made = create(tmp_path, version="v0.4:ch86", scene_id=SCENE,
                  checkpoints=CHECKPOINTS)
    packet = prepare_request(tmp_path, projection_path=made["projection"]["path"], task=task)
    request = verify_request(tmp_path, packet["request"]["path"])
    assert request["task"] == task
    assert request["knowledge_version"] == "v0.4:ch86"
    assert request["production_admission"] == "NOT_GRANTED"

    projection_path = tmp_path / made["projection"]["path"]
    original = projection_path.read_bytes()
    projection_path.write_bytes(original + b" ")
    with pytest.raises(ValueError, match="STALE_KNOWLEDGE_REQUEST"):
        verify_request(tmp_path, packet["request"]["path"])
    projection_path.write_bytes(original)


def test_projection_fails_closed_when_selected_carrier_changes(tmp_path):
    _copy_minimal_repo(tmp_path)
    projection = project(tmp_path, version="v0.4:ch86", scene_id=SCENE,
                         checkpoints=CHECKPOINTS)
    carrier = tmp_path / projection["carrier"]["path"]
    original = carrier.read_bytes()
    data = json.loads(original)
    data["facts"][0]["label"] += " altered"
    carrier.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError, match="STALE_KNOWLEDGE_PROJECTION"):
        verify(tmp_path, projection)
