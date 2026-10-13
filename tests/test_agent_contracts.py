"""Authorable overlays preserve imported bytes and never confuse replay tiers."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import shutil

import pytest

from rcwh.application.plan import add_commands
from rcwh.io import load_data
from rcwh.knowledge import KNOWLEDGE_PATH
from rcwh.planning.chapters import check_plans
from rcwh.planning.contracts import AgentContracts, draft_contract, file_binding, inspect_contract, write_contract
from rcwh.planning.references import record
from rcwh.schema import validate_instance

ROOT = Path(__file__).resolve().parents[1]
SEED = "data/planning/scenes/s.json"
PLAN = "data/planning/chapters/ch81.json"
PACKET = "packets/source.json"
SELECTION = "data/planning/contracts/test-v1"


def store(root, path, value):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value), encoding="utf-8")


def fixture_repo(tmp_path):
    (tmp_path / "schemas").mkdir()
    for name in ("agent_scene_contract", "chapter_plan", "scene_contract", "project_scope"):
        shutil.copyfile(ROOT / f"schemas/{name}.schema.json", tmp_path / f"schemas/{name}.schema.json")
    store(tmp_path, PACKET, {"source": "fixture packet, not an attestation"})
    store(tmp_path, SEED, {"id": "s", "chapter": 81, "order": 1, "chapter_plan_ref": PLAN,
                          "kind": "SCENE_SKELETON", "entry_from": None, "entry_state": None, "exit_state": None})
    store(tmp_path, PLAN, {"chapter": 81, "title": "fixture", "title_status": "WORKING", "status": "DRAFT_IMPORTED",
                          "authority_effect": "NONE", "scenes": [{"id": "s", "order": 1, "ref": SEED}],
                          "entry_ref": "BASELINE", "exit_ref": "EXIT", "threads": [], "protections": [], "open_refs": [], "unresolved": []})
    store(tmp_path, "data/project/scope.json", {"schema_version": 1, "chapters": [81, 82]})
    store(tmp_path, "data/world/m3_core.json", {
        "characters": [{"id": "alice", "name": "Alice"}],
        "baseline": {"chapter": 80, "characters": {"alice": {"location": "room", "life_state": "ALIVE"}}},
        "events": [{"id": "w1", "chapter": 81, "sequence": 1, "effects": [{"set": "characters.alice.location", "value": "gate"}]},
                   {"id": "w2", "chapter": 81, "sequence": 2, "effects": [{"set": "characters.alice.location", "value": "outside"}]}]})
    for name, value in (("locations", {"locations": [{"id": "room"}, {"id": "gate"}]}),
                        ("presence", {"presence_matrix": [{"chapter": 81}, {"chapter": 82}]}),
                        ("body", {}), ("resources", {}), ("knowledge", {})):
        store(tmp_path, f"data/world/m3_{name}.json", value)
    store(tmp_path, "data/objects/m4.json", {"baseline_chapter": 80,
        "objects": [{"id": "o", "baseline": {"holder": "alice", "location": "room"}}],
        "transitions": [{"id": "o1", "chapter": 81, "sequence": 1, "object_id": "o", "from": {"holder": "alice", "location": "room"},
                         "to": {"holder": "alice", "location": "gate"}, "movement": "EXPLICIT"}]})
    store(tmp_path, KNOWLEDGE_PATH, {"characters": [{"id": "alice"}], "facts": [{"id": "rules"}],
        "scenes": [{"id": "knowledge-source", "chapter": 81, "participants": ["alice"],
                    "entry": {"alice": {"knows": [], "believes": [], "suspects": [], "does_not_know": ["rules"]}},
                    "events": [{"id": "k1", "sequence": 1, "updates": [{"character": "alice", "add": {"knows": ["rules"]}, "remove": {"does_not_know": ["rules"]}}]}]}]})
    return tmp_path


def source_record(root, path, pointer):
    from rcwh.planning.references import pointer_value
    return record(root, path, pointer, pointer_value(load_data(root / path), pointer))


def condition(root, target, value, pointer="/baseline/characters/alice/location", path="data/world/m3_core.json"):
    return {"equals": target, "value": value, "status": "KNOWN", "basis": [source_record(root, path, pointer)]}


def edited(root):
    contract = draft_contract(root, SEED, PACKET)
    contract.update({"status": "AGENT_EDITED", "entry_from": "BASELINE",
                     "entry_checkpoint": {"kind": "CHAPTER_ENTRY", "chapter": 80},
                     "participants": ["alice"], "participants_status": "KNOWN", "unresolved": [],
                     "entry_state": [condition(root, "character.alice.location", "room")],
                     "exit_state": [condition(root, "character.alice.location", "gate", "/events/0/effects/0/value")], "event_refs": ["w1"]})
    contract["references"]["participants"] = [source_record(root, "data/world/m3_core.json", "/characters/0")]
    return contract


def inspect(root, contract):
    return inspect_contract(root, contract, f"{SELECTION}/s.{contract['revision']}.json", seed_ref=SEED, plan_ref=PLAN)


def codes(report, tier):
    return {row["code"] for row in report[tier]["checks"]}


def test_honest_draft_schema_no_edits_and_new_revision_only(tmp_path):
    root = fixture_repo(tmp_path)
    before = {ref: (root / ref).read_bytes() for ref in (SEED, PLAN)}
    value = draft_contract(root, SEED, PACKET)
    assert value["status"] == "DRAFT_GENERATED"
    assert value["participants_status"] == "UNKNOWN"
    assert not validate_instance(value, root / "schemas/agent_scene_contract.schema.json")
    assert not (root / SELECTION).exists()
    ref = write_contract(root, value, directory=SELECTION)
    assert ref == f"{SELECTION}/s.v1.json"
    with pytest.raises(FileExistsError):
        write_contract(root, value, directory=SELECTION)
    value["revision"] = "v2"
    write_contract(root, value, directory=SELECTION)
    with pytest.raises(ValueError, match="ambiguous"):
        AgentContracts(root, SELECTION)
    assert {ref: (root / ref).read_bytes() for ref in before} == before


def test_selection_stays_in_overlay_tree_and_rejects_symlink(tmp_path):
    root = fixture_repo(tmp_path)
    value = draft_contract(root, SEED, PACKET)
    for directory in ("data/scenes", "data/planning/contracts", "data/planning/contracts/../chapters"):
        with pytest.raises(ValueError):
            write_contract(root, value, directory=directory)
    target = root / SELECTION
    target.mkdir(parents=True)
    other = root / "elsewhere"
    other.mkdir()
    target.rmdir()
    target.symlink_to(other, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        AgentContracts(root, SELECTION)


def test_opt_in_overlay_cli_and_default_output_compatible(tmp_path, capsys):
    root = fixture_repo(tmp_path)
    original = check_plans(root, [81])
    value = draft_contract(root, SEED, PACKET)
    write_contract(root, value, directory=SELECTION)
    assert check_plans(root, [81]) == original
    assert "agent_contracts" not in original
    report = check_plans(root, [81], contracts_directory=SELECTION)
    assert report["status"] == "PENDING"
    assert len(report["agent_contracts"]) == 1
    assert report["deterministic_world_state_replay"]["status"] == "NOT_CHECKED"
    assert report["prose_supported_semantic_replay"]["status"] == "NOT_CHECKED"
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(root))
    add_commands(parser.add_subparsers())
    args = parser.parse_args(["plan", "check", "--chapters", "81", "--contracts-directory", SELECTION])
    assert args.func(args) == 0
    assert json.loads(capsys.readouterr().out)["contracts_directory"] == SELECTION


def test_relocated_selection_accepts_only_byte_identical_predecessor(tmp_path):
    root = fixture_repo(tmp_path)
    value = draft_contract(root, SEED, PACKET)
    first = write_contract(root, value, directory=SELECTION)
    second_seed = "data/planning/scenes/s2.json"
    store(root, second_seed, {"id": "s2", "chapter": 81, "order": 2,
                             "chapter_plan_ref": PLAN, "kind": "SCENE_SKELETON"})
    plan = load_data(root / PLAN)
    plan["scenes"].append({"id": "s2", "order": 2, "ref": second_seed})
    store(root, PLAN, plan)
    # Prepare both again after the immutable chapter plan is finalized.
    (root / first).unlink()
    first = write_contract(root, draft_contract(root, SEED, PACKET), directory=SELECTION)
    second = draft_contract(root, second_seed, PACKET)
    second["entry_from"] = first
    second_ref = write_contract(root, second, directory=SELECTION)
    relocated = "data/planning/contracts/relocated"
    for ref in (first, second_ref):
        target = root / relocated / Path(ref).name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / ref, target)
    report = check_plans(root, [81], contracts_directory=relocated)
    assert not any(c["code"] == "SCENE_CHAIN_MISMATCH" for c in report["checks"])
    original = load_data(root / first)
    original["notes"] = "same identity is insufficient when predecessor bytes differ"
    store(root, first, original)
    report = check_plans(root, [81], contracts_directory=relocated)
    assert any(c["code"] == "SCENE_CHAIN_MISMATCH" for c in report["checks"])


def test_predecessor_alias_rejects_escape_missing_and_symlink(tmp_path):
    from rcwh.planning.checking import _identical_selected_predecessor
    root = fixture_repo(tmp_path)
    store(root, "selected.json", {"id": "s"})
    assert not _identical_selected_predecessor(root, "../selected.json", "selected.json")
    assert not _identical_selected_predecessor(root, "missing.json", "selected.json")
    assert not _identical_selected_predecessor(root, "selected.json", None)
    (root / "alias.json").symlink_to(root / "selected.json")
    assert not _identical_selected_predecessor(root, "alias.json", "selected.json")


def test_edited_label_does_not_pass_empty_or_unknown_contract(tmp_path):
    root = fixture_repo(tmp_path)
    value = draft_contract(root, SEED, PACKET)
    value["status"] = "AGENT_EDITED"
    value["unresolved"] = []
    value["entry_checkpoint"] = {"kind": "CHAPTER_ENTRY", "chapter": 80}
    report = inspect(root, value)
    assert report["declared_compatibility"]["status"] == "PENDING"
    assert report["deterministic_world_state_replay"]["status"] == "PENDING"
    assert "CONTRACT_REPLAY_COVERAGE_INCOMPLETE" in codes(report, "deterministic_world_state_replay")


@pytest.mark.parametrize("binding", ["source_packet", "seed", "chapter_plan", "world"])
def test_all_bound_inputs_detect_byte_tampering(tmp_path, binding):
    root = fixture_repo(tmp_path)
    value = edited(root)
    selected = value["bindings"][binding]
    path = selected["inputs"][0]["path"] if binding == "world" else selected["path"]
    with (root / path).open("a") as stream:
        stream.write("\n")
    report = inspect(root, value)
    assert report["declared_compatibility"]["status"] == "FAIL"
    assert "CONTRACT_INPUT_BYTES_CHANGED" in codes(report, "declared_compatibility")
    assert report["deterministic_world_state_replay"]["status"] == "NOT_CHECKED"


def test_replay_uses_actual_adapter_not_self_injected_entry(tmp_path):
    root = fixture_repo(tmp_path)
    value = edited(root)
    value["entry_state"][0]["value"] = "invented"
    value["preconditions"] = [deepcopy(value["entry_state"][0])]
    report = inspect(root, value)
    assert report["declared_compatibility"]["status"] == "PASS"
    assert report["deterministic_world_state_replay"]["status"] == "FAIL"
    mismatches = [row for row in report["deterministic_world_state_replay"]["checks"] if row["code"] == "CONTRACT_REPLAY_STATE_MISMATCH"]
    assert len(mismatches) == 2
    assert all("actual='room'" in row["detail"] for row in mismatches)


def test_real_world_effect_replay_distinct_from_semantics(tmp_path):
    root = fixture_repo(tmp_path)
    value = edited(root)
    report = inspect(root, value)
    assert report["declared_compatibility"]["status"] == "PASS"
    assert report["deterministic_world_state_replay"]["status"] == "PASS"
    assert report["prose_supported_semantic_replay"]["status"] == "NOT_CHECKED"
    store(root, "prose.txt", "unrelated prose cannot certify the event")
    value["bindings"]["prose"] = file_binding(root, "prose.txt")
    assert inspect(root, value)["prose_supported_semantic_replay"]["status"] == "NOT_CHECKED"
    value["exit_state"][0]["value"] = "wrong"
    assert inspect(root, value)["deterministic_world_state_replay"]["status"] == "FAIL"


def test_object_transition_and_knowledge_acquisition_replay(tmp_path):
    root = fixture_repo(tmp_path)
    value = edited(root)
    value["required_objects"] = ["o"]
    value["references"]["objects"] = [source_record(root, "data/objects/m4.json", "/objects/0")]
    value["references"]["knowledge"] = [source_record(root, KNOWLEDGE_PATH, "/facts/0")]
    value["entry_state"] += [condition(root, "object.o.state.location", "room", "/objects/0/baseline/location", "data/objects/m4.json"),
                              condition(root, "character.alice.knowledge.rules", "does_not_know", "/scenes/0/entry/alice", KNOWLEDGE_PATH)]
    value["exit_state"] += [condition(root, "object.o.location", "gate", "/transitions/0/to/location", "data/objects/m4.json"),
                             condition(root, "character.alice.knowledge.rules", "knows", "/scenes/0/events/0", KNOWLEDGE_PATH)]
    value["object_transition_refs"] = ["o1"]
    value["knowledge_binding"] = {"scene_id": "knowledge-source", "entry_checkpoint": "ENTRY"}
    value["knowledge_event_refs"] = ["k1"]
    report = inspect(root, value)
    assert report["deterministic_world_state_replay"]["status"] == "PASS"
    assert len(report["deterministic_world_state_replay"]["checks"]) == 6
    value["knowledge_binding"] = None
    report = inspect(root, value)
    assert report["deterministic_world_state_replay"]["status"] != "PASS"
    assert "CONTRACT_KNOWLEDGE_CHECKPOINT_UNBOUND" in codes(report, "deterministic_world_state_replay")


def test_unjustified_values_and_unsupported_transitions_not_pass(tmp_path):
    root = fixture_repo(tmp_path)
    value = edited(root)
    value["exit_state"][0].update({"value": None, "status": "UNKNOWN", "reason": "not supported"})
    report = inspect(root, value)
    assert report["declared_compatibility"]["status"] == "PENDING"
    assert report["deterministic_world_state_replay"]["status"] == "PENDING"
    value = edited(root)
    value["event_refs"] = []
    report = inspect(root, value)
    assert "CONTRACT_EXIT_TRANSITION_UNSUPPORTED" in codes(report, "deterministic_world_state_replay")
    assert report["deterministic_world_state_replay"]["status"] != "PASS"
    value["order"] = 2
    store(root, SEED, {**load_data(root / SEED), "order": 2})
    value["bindings"]["seed"] = file_binding(root, SEED)
    assert inspect(root, value)["deterministic_world_state_replay"]["status"] == "NOT_CHECKED"


def test_unknown_actor_fact_record_and_duplicate_target_fail(tmp_path):
    root = fixture_repo(tmp_path)
    value = edited(root)
    value["participants"] = ["invented"]
    assert "CONTRACT_ENTITY_UNGROUNDED" in codes(inspect(root, value), "declared_compatibility")
    value = edited(root)
    value["entry_state"].append(deepcopy(value["entry_state"][0]))
    assert "CONTRACT_DUPLICATE_STATE_TARGET" in codes(inspect(root, value), "declared_compatibility")
    value = edited(root)
    value["exit_state"][0]["basis"][0]["text_sha256"] = "0" * 64
    assert "CONTRACT_REFERENCE_INVALID" in codes(inspect(root, value), "declared_compatibility")
    value = edited(root)
    value["exit_state"][0]["equals"] = "character.alice.knowledge.invented"
    assert "CONTRACT_KNOWLEDGE_UNGROUNDED" in codes(inspect(root, value), "declared_compatibility")


def test_invalid_or_missing_selection_cannot_silently_fallback(tmp_path):
    root = fixture_repo(tmp_path)
    report = check_plans(root, [81], contracts_directory=SELECTION)
    assert report["status"] == "FAIL"
    assert "CONTRACT_SELECTION_INVALID" in {row["code"] for row in report["checks"]}
    (root / SELECTION).mkdir(parents=True)
    report = check_plans(root, [81], contracts_directory=SELECTION)
    assert report["status"] == "PENDING"
    assert "AGENT_CONTRACT_MISSING" in {row["code"] for row in report["checks"]}


def test_nonprefix_replay_never_compares_fabricated_exit(tmp_path):
    root = fixture_repo(tmp_path)
    value = edited(root)
    value["event_refs"] = ["w2"]
    value["exit_state"][0]["value"] = "outside"
    report = inspect(root, value)
    assert report["deterministic_world_state_replay"]["status"] == "NOT_CHECKED"
    assert "CONTRACT_WORLD_EVENT_ORDER_UNSUPPORTED" in codes(report, "deterministic_world_state_replay")
    assert "CONTRACT_REPLAY_STATE_MATCH" not in codes(report, "deterministic_world_state_replay")


def test_draft_known_states_do_not_auto_pass_and_declaration_basis_rejected(tmp_path):
    root = fixture_repo(tmp_path)
    value = edited(root)
    value["status"] = "DRAFT_GENERATED"
    assert inspect(root, value)["deterministic_world_state_replay"]["status"] == "PENDING"
    value = edited(root)
    value["entry_state"][0]["basis"] = [source_record(root, PLAN, "/entry_ref")]
    report = inspect(root, value)
    assert "CONTRACT_DECLARATION_NOT_STATE_BASIS" in codes(report, "declared_compatibility")
    assert report["deterministic_world_state_replay"]["status"] == "NOT_CHECKED"


def test_schema_requires_unknown_reason_and_known_basis(tmp_path):
    root = fixture_repo(tmp_path)
    value = edited(root)
    value["entry_state"][0]["basis"] = []
    assert validate_instance(value, root / "schemas/agent_scene_contract.schema.json")
    value["entry_state"][0].update({"value": None, "status": "UNKNOWN"})
    assert validate_instance(value, root / "schemas/agent_scene_contract.schema.json")
    value["entry_state"][0]["reason"] = "not justified"
    assert not validate_instance(value, root / "schemas/agent_scene_contract.schema.json")


def test_existing_production_seed_draft_preserves_original_bytes():
    seed = "data/planning/scenes/89-S1.json"
    plan = "data/planning/chapters/ch89.json"
    before = {path: (ROOT / path).read_bytes() for path in (seed, plan, "data/scenes/ch86_last_night.yaml")}
    value = draft_contract(ROOT, seed, plan)
    assert not validate_instance(value, ROOT / "schemas/agent_scene_contract.schema.json")
    assert value["status"] == "DRAFT_GENERATED" and value["entry_from"] == "UNKNOWN"
    assert {path: (ROOT / path).read_bytes() for path in before} == before
