"""A current freeze must not reinterpret saved diagnostics as live inputs."""
import importlib.util
import json
from pathlib import Path

import pytest

from rcwh.candidate_reviews import canonical_bytes, digest
from rcwh.generation.records import bound_bytes

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "artifacts/agent_research/phase6/advancement"
OUTPUT = BASE / "m2-input-freeze-v3"
SPEC = importlib.util.spec_from_file_location("freeze_inputs", ROOT / "tools/freeze_research_inputs.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_corrected_freeze_retains_selection_and_explicit_pilot_parents():
    freeze = json.loads((OUTPUT / "freeze.json").read_bytes())
    assert freeze["schema_version"] == 3
    assert freeze["status"] == "FROZEN_RETAIN_V2_NOT_ADOPTED"
    assert sorted(freeze["chapters"], key=int) == [str(ch) for ch in range(81, 101)]
    assert [freeze["chapters"][str(ch)]["reading_revision"] for ch in range(81, 101)] == ["v1"] * 10 + ["v2"] + ["v1"] * 9
    assert freeze["delta_decision"]["corpus"] == "RETAIN_V2"
    assert freeze["delta_decision"]["packages"] == "NO_NEW_PACKAGES"
    assert freeze["delta_decision"]["new_pilot_prepared_requests"] == "REQUIRED_BEFORE_WRITING"
    assert freeze["pilot_gate"]["fresh_preparation_run"] is False
    assert freeze["pilot_parents"]["86"]["candidate"]["sha256"] == "493de9a83fa7aa24601c023397f462790fc7b3676f94bf2c66dfca1376fe99a1"
    assert freeze["chapters"]["86"]["candidate"]["sha256"] == "8351a6680a36e7899a583927a57c86a10121b6321e512b0f7b4cd457d24e5721"
    impact = freeze["v3_experiment_impact"]
    assert impact["interval_count"] == 30
    assert impact["shifted_exact_locator_segment_count"] == 224
    assert impact["products_changed_beyond_dataset_identity"] == 4
    assert not impact["new_package_or_lineage_calls"]
    assert freeze["shared_inputs"]["direct_prepared_binding_occurrences"] == 3427
    assert freeze["shared_inputs"]["direct_stale_bindings"] == []
    assert freeze["shared_inputs"]["embedded_saved_observation_count"] == 68
    assert freeze["protected_count"] == 325
    inventory = json.loads(bound_bytes(ROOT, freeze["input_inventory"]))
    assert freeze["shared_inputs"]["selected_binding_count"] == len(inventory["bindings"])
    assert freeze["correction"]["superseded_for_current_use"]["path"] in inventory["bindings"]
    for ref in inventory["bindings"].values():
        bound_bytes(ROOT, ref)
    for item in inventory["embedded_saved_observations"]:
        assert item["role"] == "EMBEDDED_SAVED_OBSERVATION_NOT_DIRECT_INPUT"
        assert item["declared"]["path"] == "requirements/extraction.lock.json"
    payload = {key: value for key, value in freeze.items() if key != "freeze_sha256"}
    assert digest(canonical_bytes(payload)) == freeze["freeze_sha256"]


def test_erroneous_v1_retained_and_explicitly_corrected_not_overwritten():
    freeze = json.loads((OUTPUT / "freeze.json").read_bytes())
    old = json.loads(bound_bytes(ROOT, freeze["correction"]["prior_v1"]))
    assert old["v3_experiment_impact"]["interval_count"] == 86
    assert old["pilot_gate"]["status"] == "BLOCKED_HISTORICAL_BINDING_STALENESS"
    v2 = json.loads(bound_bytes(ROOT, freeze["correction"]["superseded_for_current_use"]))
    v2_inventory = json.loads(bound_bytes(ROOT, v2["input_inventory"]))
    assert v2["shared_inputs"]["selected_binding_count"] + 1 == len(v2_inventory["bindings"])
    assert freeze["pilot_gate"]["status"] == "READY_FOR_NEW_REVISION_PREPARATION_NOT_YET_FRESH_VERIFIED"


def test_full_projection_recomputes_without_writes():
    freeze = json.loads((OUTPUT / "freeze.json").read_bytes())
    inventory = json.loads(bound_bytes(ROOT, freeze["input_inventory"]))
    actual, actual_inventory = MODULE.project(ROOT)
    assert actual_inventory == inventory
    assert actual == {key: value for key, value in freeze.items() if key not in ("input_inventory", "freeze_sha256")}


def test_direct_input_fields_exclude_embedded_diagnostic_bindings():
    prepared = {"inputs": [{"path": "a", "sha256": "x"}], "template": {"path": "t", "sha256": "y"},
                "package": None, "parent": None, "feedback": None,
                "task": {"old_lock": {"path": "x", "sha256": "old"}}}
    assert MODULE.direct_prepared_inputs(prepared) == [prepared["inputs"][0], prepared["template"]]


def test_saved_observation_does_not_modify_or_qualify_current_input(tmp_path):
    (tmp_path / "lock.txt").write_bytes(b"new")
    value = {"saved": {"path": "lock.txt", "sha256": digest(b"old")}}
    rows = MODULE.saved_binding_observations(tmp_path, value, "/task")
    assert rows[0]["pointer"] == "/task/saved"
    assert rows[0]["declared"]["sha256"] == digest(b"old")
    assert rows[0]["actual_sha256"] == digest(b"new")
    assert (tmp_path / "lock.txt").read_bytes() == b"new"


@pytest.mark.parametrize("field", ["chapter", "candidate", "package"])
def test_unrelated_hashed_draft_relationship_rejected(field):
    row = {"chapter": 95, "candidate": {"path": "c", "sha256": "c"}, "writing_package": {"path": "p", "sha256": "p"}}
    draft = {"chapter": 95, "candidate": row["candidate"], "package": row["writing_package"]}
    draft[field] = 99 if field == "chapter" else {"path": "different", "sha256": "different"}
    with pytest.raises(ValueError, match="relationship"):
        MODULE.validate_selected_draft(row, draft)


def test_changed_samechapter_package_cannot_be_called_unchanged():
    row = {"chapter": 95, "writing_package": {"path": "new", "sha256": "new"}}
    prepared = {"chapter": 95, "package": {"path": "old", "sha256": "old"}}
    with pytest.raises(ValueError, match="historical prepared"):
        MODULE.validate_prepared_package(row, prepared)


def test_missing_direct_binding_fails_but_missing_saved_diagnostic_is_observation(tmp_path):
    with pytest.raises(FileNotFoundError):
        MODULE.load_bound(tmp_path, {"path": "missing", "sha256": "0" * 64})
    rows = MODULE.saved_binding_observations(tmp_path, {"path": "missing", "sha256": "0" * 64})
    assert rows[0]["actual_sha256"] is None


def test_freeze_refuses_overwrite_or_external_output(tmp_path):
    with pytest.raises(FileExistsError):
        MODULE.freeze(ROOT, OUTPUT)
    with pytest.raises(ValueError):
        MODULE.freeze(ROOT, tmp_path / "external")
