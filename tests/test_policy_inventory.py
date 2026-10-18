"""An externally bound expected inventory detects deleted whole submissions."""
from copy import deepcopy
import json
import shutil

import pytest

from rcwh.candidate_reviews import canonical_bytes
from rcwh.evaluation.policy_inventory import build_policy_inventory, check_policy_inventory
from rcwh.evaluation.policy_readings import register_policy_reading
from rcwh.generation.records import binding
from test_policy_evidence import isolated
from test_policy_readings import save


def freeze(root, value, name="inventory.json"):
    (root / name).write_bytes(canonical_bytes(value))
    return binding(root, name)


def populate(root, request, reading, text):
    reading["checks"][0].update(finding="VIOLATED", support=[{
        "file": request["context"]["selected"]["candidate"], "start": 0, "end": 2, "quote": text[:2]}])
    negative = register_policy_reading(root, request, save(root, reading), origin="negative fixture")
    positive = deepcopy(reading)
    positive["reader"]["principal_id"] = "second-fixture"
    positive["checks"][0].update(finding="SUPPORTED", support=positive["checks"][0]["support"])
    register_policy_reading(root, request, save(root, positive, "positive.json"), origin="positive fixture")
    return negative


def test_empty_observed_checkpoint_remains_nonsemantic_and_readonly(isolated):
    root, request, _, _ = isolated
    value = build_policy_inventory(root)
    assert value["bundles"] == [] and value["previous"] is None
    ref = freeze(root, value)
    report = check_policy_inventory(root, ref, request)
    assert report["inventory_completeness"] == "PASS_EXACT_EXTERNALLY_BOUND_CHECKPOINT"
    assert report["status"] == report["semantic_status"] == "PENDING"
    assert report["identity_eligibility"] == "PENDING_NOT_IMPLEMENTED"


def test_deleted_entire_negative_detected_by_retained_anchor(isolated):
    root, request, reading, text = isolated
    negative = populate(root, request, reading, text)
    ref = freeze(root, build_policy_inventory(root))
    before = check_policy_inventory(root, ref, request)
    assert len(before["active_negative_declarations"]) == 1
    shutil.rmtree(root / negative["bundle"])
    report = check_policy_inventory(root, ref, request)
    assert report["integrity_status"] == report["inventory_completeness"] == "FAIL"
    assert len(report["missing_expected_members"]) == 3
    assert all(item["expected"]["path"].startswith(negative["bundle"]) for item in report["missing_expected_members"])
    assert len(report["records"]) == 1
    assert report["semantic_status"] == "PENDING"
    with pytest.raises(ValueError, match="previously anchored"):
        build_policy_inventory(root, previous=ref)


def test_new_bundle_requires_successor_not_old_anchor_clearance(isolated):
    root, request, reading, _ = isolated
    first = register_policy_reading(root, request, save(root, reading), origin="fixture")
    old = freeze(root, build_policy_inventory(root))
    reading["reader"]["principal_id"] = "new-fixture"
    second = register_policy_reading(root, request, save(root, reading, "second.json"), origin="second fixture")
    report = check_policy_inventory(root, old, request)
    assert report["inventory_completeness"] == "FAIL"
    assert report["unexpected_bundles"] == [second["bundle"]]
    successor = freeze(root, build_policy_inventory(root, previous=old), "successor.json")
    report = check_policy_inventory(root, successor, request)
    assert report["inventory_completeness"] == "PASS_EXACT_EXTERNALLY_BOUND_CHECKPOINT"
    assert {row["bundle"] for row in report["records"]} == {first["bundle"], second["bundle"]}
    assert report["release_gate_eligibility"] == "PENDING"


@pytest.mark.parametrize("fault", ["omit", "duplicate", "member", "schema", "extra", "boolean", "unsorted"])
def test_malformed_or_selectively_rewritten_successor_rejected(isolated, fault):
    root, request, reading, text = isolated
    populate(root, request, reading, text)
    value = build_policy_inventory(root)
    previous = freeze(root, value)
    altered = deepcopy(value)
    altered["previous"] = previous
    if fault == "omit":
        altered["bundles"].pop()
    elif fault == "duplicate":
        altered["bundles"].append(deepcopy(altered["bundles"][0]))
    elif fault == "member":
        altered["bundles"][0]["members"][0]["path"] = "candidate.txt"
    elif fault == "schema":
        altered["qualification"] = "INDEPENDENT_HUMAN"
    elif fault == "extra":
        altered["status"] = "PASS"
    elif fault == "boolean":
        altered["schema_version"] = True
    else:
        altered["bundles"].reverse()
    ref = freeze(root, altered, "broken.json")
    report = check_policy_inventory(root, ref, request)
    assert report["integrity_status"] == "FAIL"
    assert report["semantic_status"] == "PENDING"


def test_stale_anchor_bytes_and_changed_expected_member_rejected(isolated):
    root, request, reading, _ = isolated
    result = register_policy_reading(root, request, save(root, reading), origin="fixture")
    value = build_policy_inventory(root)
    ref = freeze(root, value)
    (root / "inventory.json").write_bytes(canonical_bytes(value) + b" ")
    assert check_policy_inventory(root, ref, request)["integrity_status"] == "FAIL"
    ref = binding(root, "inventory.json")
    (root / result["bundle"] / "receipt.json").write_bytes(b"{}")
    report = check_policy_inventory(root, ref, request)
    assert report["missing_expected_members"]


def test_builder_cannot_claim_history_before_first_anchor(isolated):
    root, request, reading, text = isolated
    negative = populate(root, request, reading, text)
    shutil.rmtree(root / negative["bundle"])
    # A new first checkpoint cannot know what was removed before it was bound.
    ref = freeze(root, build_policy_inventory(root))
    report = check_policy_inventory(root, ref, request)
    assert report["inventory_completeness"] == "PASS_EXACT_EXTERNALLY_BOUND_CHECKPOINT"
    assert any("predating" in line for line in report["limitations"])


@pytest.mark.parametrize("anchor", [None, {}, [], {"path": "inventory.json", "sha256": "0" * 64, "extra": True}])
def test_missing_or_malformed_entry_anchor_reports_failure(isolated, anchor):
    root, request, _, _ = isolated
    report = check_policy_inventory(root, anchor, request)
    assert report["integrity_status"] == report["inventory_completeness"] == "FAIL"
    assert report["findings"]


def test_anchor_fifo_rejected_without_blocking(isolated):
    import os
    root, request, _, _ = isolated
    os.mkfifo(root / "anchor.json")
    report = check_policy_inventory(root, {"path": "anchor.json", "sha256": "0" * 64}, request)
    assert report["integrity_status"] == "FAIL"
    assert any("regular registry file" in item for item in report["findings"])


def test_inventory_requires_same_reader_writer_lock(isolated):
    root, _, reading, _ = isolated
    from rcwh.evaluation.policy_readings import _registry_lock
    with _registry_lock(root):
        with pytest.raises(OSError):
            build_policy_inventory(root)
