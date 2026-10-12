from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import shutil

import pytest
import yaml

from rcwh.cli import main
from rcwh.evaluation.continuity import continuity_report, impact_report
from rcwh.evaluation.state import SceneStateAdapter, SceneStateProjector
from rcwh.io import load_data

ROOT = Path(__file__).resolve().parents[1]
BOUNDARY = {"authority_effect": "NONE", "evidence_effect": "NONE", "scope": "STAGING_DIAGNOSTIC_ONLY"}


def codes(report, status=None):
    return {row["code"] for row in report["checks"] if status in (None, row["status"])}


def test_actual_repository_is_sparse_pending_without_contradictions():
    report = continuity_report(ROOT)
    assert report["status"] == "PENDING" and not report["production_block"]
    assert {key: report[key] for key in BOUNDARY} == BOUNDARY
    assert report["coverage"]["covered_chapters"] == [86, 89, 92]
    assert len(report["coverage"]["missing_chapters"]) == 17 and not report["coverage"]["complete"]
    assert "FAIL" not in {row["status"] for row in report["checks"]}
    assert {"SPARSE_SCENE_COVERAGE", "SCENE_CHAIN_UNDECLARED", "EXIT_EVENTS_UNPROVED"} <= codes(report, "PENDING")
    assert report["scene_chains"] == [] and report["automatic_repair"] is False
    assert report == continuity_report(ROOT)


def test_chapter_filter_and_unknown_chapter():
    report = continuity_report(ROOT, 89)
    assert [scene["id"] for scene in report["scenes"]] == ["ch89_confiscation_message"]
    assert report["coverage"]["missing_chapters"] == []
    assert continuity_report(ROOT, 88)["coverage"]["missing_chapters"] == [88]
    assert continuity_report(ROOT, 55)["status"] == "FAIL"
    assert continuity_report(ROOT, True)["status"] == "FAIL"


def test_ch86_to_ch89_is_not_chained_by_adjacency():
    report = continuity_report(ROOT)
    assert all(scene["exit_state_semantics"] == "DECLARATIONS_NOT_PROVED_EVENTS" for scene in report["scenes"])
    assert all(row["comparison"] == "DECLARATION_ONLY" for scene in report["scenes"]
               for row in scene["state_checks"] if row["field"] == "exit_state")


def test_medicine_bridge_reports_differences_without_aliasing():
    rows = {(row["chapter"], row["field"]): row for row in SceneStateProjector(ROOT).bridge_overlaps(86)
            if row["legacy_id"] == "medicine_bowl_86"}
    assert rows[(86, "status")]["status"] == "MATCH"
    location = rows[(86, "location")]
    assert location["status"] == "REFINES" and location["status"] != "MATCH"
    assert (location["selected"], location["registered"]) == ("s02", "xiaoxiang_room")
    assert location["refinement"]["relation"] == "CONTAINED_IN" and location["refinement"]["within"] == "S02"
    assert rows[(86, "temperature")]["status"] == "DIFFERENT"
    assert (rows[(86, "temperature")]["selected"], rows[(86, "temperature")]["registered"]) == ("cold", "warm")
    assert all(row["authority_effect"] == "NONE" for row in rows.values())
    pending = [row for row in continuity_report(ROOT, 86)["checks"] if row["code"] == "BRIDGE_MANUAL_REVIEW"]
    assert any("temperature" in row["detail"] for row in pending)
    assert not any("/location:" in row["detail"] for row in pending)


def test_location_refinement_cites_front80_passages():
    obj = next(o for o in load_data(ROOT / "data/objects/m4.json")["objects"] if o["id"] == "OBJ-MEDICINE-BOWL-86")
    cited = {segment for item in obj["legacy_location_refinements"] for segment in item["basis_segments"]}
    found = {}
    with (ROOT / "corpus/front80/v1-candidate/segments.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            if row.get("segment_id") in cited:
                found[row["segment_id"]] = row["text"]
    assert set(found) == cited and all("潇湘馆" in text for text in found.values())


def edit_bowl(root, change):
    path = root / "data/objects/m4.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    change(next(o for o in data["objects"] if o["id"] == "OBJ-MEDICINE-BOWL-86"))
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


@pytest.mark.parametrize("change", [
    lambda o: o["legacy_location_refinements"][0].update(within="NO-SUCH-PLACE"),
    lambda o: o["legacy_location_refinements"][0].update(relation="SAME_AS"),
    lambda o: o["legacy_location_refinements"][0].update(basis_segments=[]),
    lambda o: o["legacy_location_refinements"].append(dict(o["legacy_location_refinements"][0])),
])
def test_malformed_refinement_fails_instead_of_aliasing(tmp_path, change):
    root = copied_repo(tmp_path)
    edit_bowl(root, change)
    assert continuity_report(root, 86)["status"] == "FAIL"


def test_refinement_applies_only_to_the_declared_pair(tmp_path):
    root = copied_repo(tmp_path)
    edit_bowl(root, lambda o: o["legacy_location_refinements"][0].update(legacy_value="hengwu_court"))
    row = next(r for r in SceneStateProjector(root).bridge_overlaps(86) if r["field"] == "location" and r["legacy_id"] == "medicine_bowl_86")
    assert row["status"] == "DIFFERENT" and row["refinement"] is None


def test_scene_adapter_default_snapshot_is_unchanged_by_projector():
    for path in sorted((ROOT / "data/scenes").glob("*.yaml")):
        contract = load_data(path)
        shared = SceneStateAdapter(ROOT, contract, projector=SceneStateProjector(ROOT)).snapshot()
        assert shared == SceneStateAdapter(ROOT, contract).snapshot()
        assert "fact_registry" not in shared
        assert shared["knowledge"] is None or shared["knowledge"]["checkpoint"] == "ENTRY"
    entry = SceneStateAdapter(ROOT, load_data(ROOT / "data/scenes/ch86_last_night.yaml")).snapshot()
    assert entry["values"]["character.daiyu.life_state"] == "active"
    assert entry["values"]["object.medicine_bowl_86.temperature"] == "warm"
    with pytest.raises(ValueError):
        SceneStateAdapter(ROOT, load_data(ROOT / "data/scenes/ch86_last_night.yaml")).snapshot(request_version=3)


def test_impact_is_exact_canonical_and_declared_only():
    report = impact_report(ROOT, "object.medicine_bowl_86.state.temperature")
    assert report["target"] == "object.medicine_bowl_86.temperature"
    assert report["affected_scene_ids"] == ["ch86_last_night"]
    assert {row["field"] for row in report["direct_references"]} == {"exit_state"}
    assert report["inference"] == "EXACT_CANONICAL_REFERENCES_ONLY" and report["transitive_impact"] == "NOT_INFERRED"
    assert {row["field"] for row in impact_report(ROOT, "character.daiyu.resources.physical_strength")["direct_references"]} == {"entry_state", "preconditions"}
    guarded = impact_report(ROOT, "character.baochai.knowledge.official_confiscation_exact_scope")
    assert {row["field"] for row in guarded["direct_references"]} == {"knowledge_guards"}
    assert guarded["affected_scene_ids"] == ["ch89_confiscation_message"]
    assert [row["ref"] for row in report["direct_references"]] == sorted(row["ref"] for row in report["direct_references"])


def test_unreferenced_target_reports_absence_not_safety():
    report = impact_report(ROOT, "character.baoyu.life_state")
    assert report["direct_references"] == [] and "NO_DIRECT_REFERENCES" in codes(report, "PENDING")
    assert report["status"] == "PENDING"
    assert "not proof" in next(row for row in report["checks"] if row["code"] == "NO_DIRECT_REFERENCES")["detail"]


@pytest.mark.parametrize("target", ["", "daiyu.life_state", "character.daiyu", "place.s02.name", "character..life_state", "character.nobody.life_state",
                                    "object.nothing.status", "character.daiyu.knowledge", "character.daiyu.knowledge.not_a_fact"])
def test_malformed_or_unknown_targets_fail(target):
    assert impact_report(ROOT, target)["status"] == "FAIL"


def copied_repo(tmp_path):
    root = tmp_path / "repo"
    for name in ("data", "schemas"):
        shutil.copytree(ROOT / name, root / name, ignore=shutil.ignore_patterns("__pycache__"))
    return root


def edit_scene(root, name, change):
    path = root / "data/scenes" / name
    contract = yaml.safe_load(path.read_text(encoding="utf-8"))
    change(contract)
    path.write_text(yaml.safe_dump(contract, allow_unicode=True, sort_keys=False), encoding="utf-8")


@pytest.mark.parametrize("name,change,code", [
    ("ch86_last_night.yaml", lambda c: c["preconditions"][0].update(value="healthy"), "PRECONDITION_CONTRADICTION"),
    ("ch86_last_night.yaml", lambda c: c["preconditions"].append({"equals": "character.nobody.life_state", "value": "x"}), "INVALID_STATE_REFERENCE"),
    ("ch86_last_night.yaml", lambda c: c["preconditions"].append(dict(c["preconditions"][0])), "INVALID_STATE_REFERENCE"),
    ("ch86_last_night.yaml", lambda c: c["preconditions"].append({"equals": "object.medicine_bowl_86.temperature"}), "INVALID_STATE_REFERENCE"),
    ("ch86_last_night.yaml", lambda c: c.update(participants=["daiyu", "ghost"]), "UNKNOWN_PARTICIPANT"),
    ("ch86_last_night.yaml", lambda c: c.update(required_objects=["ghost_object"]), "UNKNOWN_REQUIRED_OBJECT"),
    ("ch86_last_night.yaml", lambda c: c.update(chapter=55), "SCENE_OUTSIDE_SCOPE"),
    ("ch89_confiscation_message.yaml", lambda c: c["knowledge_guards"][0].update(fact="not_a_fact"), "INVALID_KNOWLEDGE_REFERENCE"),
    ("ch89_confiscation_message.yaml", lambda c: c.update(knowledge_checkpoint="NO-SUCH-CHECKPOINT"), "INVALID_KNOWLEDGE_REFERENCE"),
    ("ch89_confiscation_message.yaml", lambda c: c.pop("id"), "INVALID_SCENE_ID"),
    ("ch89_confiscation_message.yaml", lambda c: c.update(required_beats="not-a-list"), "INVALID_SCENE_STRUCTURE"),
])
def test_structural_reference_and_precondition_conflicts_fail(tmp_path, name, change, code):
    root = copied_repo(tmp_path)
    edit_scene(root, name, change)
    report = continuity_report(root)
    assert report["status"] == "FAIL" and code in codes(report, "FAIL")


def test_null_declaration_is_present_but_missing_checkpoint_stays_pending(tmp_path):
    root = copied_repo(tmp_path)
    edit_scene(root, "ch86_last_night.yaml", lambda c: c["entry_state"].append({"equals": "object.medicine_bowl_86.holder", "value": None}))
    report = continuity_report(root, 86)
    row = next(r for scene in report["scenes"] for r in scene["state_checks"] if r["target"] == "object.medicine_bowl_86.holder")
    assert row["present"] is True and row["actual"] is None and row["comparison"] == "MATCH"
    edit_scene(root, "ch89_confiscation_message.yaml", lambda c: c.pop("knowledge_checkpoint"))
    pending = continuity_report(root, 89)
    assert pending["status"] == "PENDING" and "KNOWLEDGE_CHECKPOINT_MISSING" in codes(pending, "PENDING")


def test_diagnostics_are_read_only_and_cli_exit_codes(monkeypatch, capsys):
    watched = [ROOT / "data/project/current.json", ROOT / "data/competitions/43_0.yaml", ROOT / "data/scenes/ch86_last_night.yaml"]
    before = {path: path.read_bytes() for path in watched}

    def run(*arguments):
        monkeypatch.setattr("sys.argv", ["rcwh", "--root", str(ROOT), "diagnostics", *arguments])
        with pytest.raises(SystemExit) as result:
            main()
        return result.value.code, json.loads(capsys.readouterr().out)

    code, payload = run("continuity")
    assert code == 2 and payload["status"] == "PENDING"
    code, payload = run("continuity", "--chapter", "55")
    assert code == 1 and payload["status"] == "FAIL"
    code, payload = run("impact", "character.daiyu.life_state")
    assert code == 2 and payload["affected_scene_ids"] == ["ch86_last_night"]
    code, payload = run("impact", "character.nobody.life_state")
    assert code == 1
    assert {path: path.read_bytes() for path in watched} == before
