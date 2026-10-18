"""A custody baseline preserves failures; it does not grant release permission."""
import importlib.util
import json
from pathlib import Path

import pytest

from rcwh.generation.records import bound_bytes

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "artifacts/agent_research/phase6/advancement/m0-v1"
SPEC = importlib.util.spec_from_file_location("freeze_baseline", ROOT / "tools/freeze_research_baseline.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


@pytest.mark.parametrize(("path", "expected"), [
    ("src/rcwh/validate.py", "IMPLEMENTATION"),
    ("schemas/test.json", "IMPLEMENTATION"),
    ("tests/test_baseline.py", "TEST"),
    ("data/catalog/assets/00.yaml", "CATALOG_GENERATED_CUSTODY"),
    ("corpus/front80/v2-candidate/manifest.json", "CORPUS_PRODUCT_OR_CONFIGURATION"),
    ("data/releases/proposals/v1.5.json", "UNACTIVATED_PROPOSAL"),
    ("artifacts/rejected.json", "RESEARCH_EVIDENCE_OR_EXECUTION"),
    ("data/writing/packages/ch81.json", "VERSIONED_INPUT_OR_RECORD"),
])
def test_custody_classification_is_not_authorship(path, expected):
    assert MODULE.category(path) == expected


def test_expected_bytes_reject_changes_and_missing_files(tmp_path):
    path = tmp_path / "old.txt"
    path.write_bytes(b"old")
    expected = {"old.txt": MODULE.digest(b"old")}
    assert MODULE.verify_expected(tmp_path, expected) == []
    path.write_bytes(b"new")
    assert MODULE.verify_expected(tmp_path, expected) == ["old.txt"]
    path.unlink()
    assert MODULE.verify_expected(tmp_path, expected) == ["old.txt"]


def test_freeze_refuses_existing_or_external_output(tmp_path):
    with pytest.raises(ValueError):
        MODULE.freeze(tmp_path, tmp_path)
    existing = tmp_path / "existing"
    existing.mkdir()
    with pytest.raises(FileExistsError):
        MODULE.freeze(tmp_path, existing)
    with pytest.raises(ValueError):
        MODULE.freeze(tmp_path, tmp_path.parent / "outside-baseline")


def test_gate_routing_does_not_erase_failure_or_unreached_corpus():
    report = {"chapters": [{"chapter": 86, "gates": {
        "CORPUS_PEERS": "PENDING", "CHAPTER_SAFETY_POLICY": "FAIL", "WRITING_PACKAGE": "FAIL"}}]}
    rows = {row["gate"]: row for row in MODULE.gate_items(report)}
    assert rows["CORPUS_PEERS"]["blocker_class"] == "NOT_REACHED_OR_REQUIRES_INVESTIGATION"
    assert rows["CHAPTER_SAFETY_POLICY"]["status"] == "FAIL"
    assert rows["WRITING_PACKAGE"]["blocker_class"] == "UNRESOLVED_SOURCE_DEPENDENCY"


def test_actual_baseline_binds_history_and_keeps_selected86_v1():
    baseline = json.loads((BASE / "baseline.json").read_bytes())
    assert baseline["status"] == "NOT_ADOPTED_NOT_RELEASED"
    assert baseline["authority_effect"] == "NONE"
    assert baseline["evaluation_rerun"] is False
    for ref in baseline["records"]:
        bound_bytes(ROOT, ref)
    report = json.loads(bound_bytes(ROOT, baseline["evaluation"]))
    assert baseline["chapters"] == [{
        "chapter": row["chapter"], "bindings": row["bindings"], "gates": row["gates"],
        "status": row["status"], "findings": row["findings"],
        "reading_revision": "v2" if row["chapter"] == 91 else "v1",
    } for row in report["chapters"]]
    assert len(baseline["retained_corpus_negatives"]) == 2
    for row in baseline["retained_corpus_negatives"]:
        assert row["verdict"] == "FAIL"
        assert len(row["rejected_samples"]) == 31
        bound_bytes(ROOT, row["record"])
    assert baseline["preservation"]["protected_count"] == 325
    assert baseline["preservation"]["protected_changed"] == []
    assert baseline["preservation"]["checkpoint19_inputs_changed"] == []
    assert not any(baseline["authorization"].values())


def test_inventory_covers_historical_checkpoint_and_retains_dirty_state():
    inventory = json.loads((BASE / "inventory.json").read_bytes())
    files = inventory["files"]
    old = json.loads((ROOT / "artifacts/agent_research/phase6/verification/engineering-checkpoint-19/snapshot-inputs.json").read_bytes())
    assert set(old) <= set(files)
    assert all(files[path]["sha256"] == sha for path, sha in old.items())
    assert sum(inventory["counts"].values()) == len(files)
    assert sum(inventory["git_state_counts"].values()) == len(files)
    assert inventory["git_state_counts"]["MODIFIED"] > 0
    assert inventory["git_state_counts"]["UNTRACKED"] > 0
    assert all(row["authorship"] == "NOT_INFERRED_FROM_GIT_STATE" for row in files.values())
    # Later implementations may change working files; this is an immutable baseline,
    # not a requirement that the entire project stop evolving after capture.
