"""Custody tests use synthetic declarations, never real independent reviews."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from rcwh.candidate_reviews import canonical_bytes, digest
from rcwh.evaluation.policy_evidence import build_policy_evidence_request
from rcwh.evaluation.policy_readings import DIRECTORY, policy_reading_summary, register_policy_reading
from rcwh.generation.records import binding
from test_policy_evidence import isolated


def save(root, reading, name="submission.json"):
    file = root / name
    file.write_bytes(canonical_bytes(reading))
    return file


def test_empty_registry_is_pending_and_writes_nothing(isolated):
    root, request, _, _ = isolated
    report = policy_reading_summary(root, request)
    assert report["status"] == "PENDING" and report["integrity_status"] == "PASS"
    assert report["records"] == []
    assert not (root / DIRECTORY).exists()


def test_dry_run_and_exact_raw_custody_idempotent_origin(isolated):
    root, request, reading, _ = isolated
    path = save(root, reading)
    # Preserve noncanonical original JSON bytes, not just the parsed projection.
    path.write_bytes(b" \n" + path.read_bytes() + b" \n")
    raw = path.read_bytes()
    preview = register_policy_reading(root, request, path, origin="fixture", dry_run=True)
    assert preview["written"] is False
    assert not (root / DIRECTORY).exists()
    first = register_policy_reading(root, request, path, origin="fixture")
    second = register_policy_reading(root, request, path, origin="other description")
    assert first["written"] is True and second["written"] is False
    summary = policy_reading_summary(root, request)
    assert len(summary["records"]) == 1
    record = summary["records"][0]
    assert (root / record["raw_reading"]["path"]).read_bytes() == raw
    assert record["reader"]["isolation_asserted"] is False
    assert summary["semantic_status"] == summary["release_gate_eligibility"] == "PENDING"


def test_negative_retained_with_positive_and_contaminated_reader(isolated):
    root, request, reading, text = isolated
    ref = request["context"]["selected"]["candidate"]
    reading["checks"][0].update(finding="VIOLATED", counterevidence=[
        {"file": ref, "start": 0, "end": 2, "quote": text[:2]}])
    register_policy_reading(root, request, save(root, reading), origin="negative fixture")
    positive = deepcopy(reading)
    positive["reader"]["principal_id"] = "other"
    positive["checks"][0].update(finding="SUPPORTED", counterevidence=[], support=[
        {"file": ref, "start": 0, "end": 2, "quote": text[:2]}])
    register_policy_reading(root, request, save(root, positive, "positive.json"), origin="positive fixture")
    report = policy_reading_summary(root, request)
    assert len(report["records"]) == 2
    assert len(report["active_negative_declarations"]) == 1
    assert report["active_negative_declarations"][0]["reader"]["isolation_asserted"] is False
    # Custody does not adjudicate an arbitrary fixture allegation into truth.
    assert report["status"] == report["semantic_status"] == "PENDING"
    assert report["identity_eligibility"] == "PENDING_NOT_IMPLEMENTED"


def test_same_subject_repackaging_cannot_hide_negative(isolated):
    root, request, reading, text = isolated
    reading["checks"][0].update(finding="VIOLATED", support=[{
        "file": request["context"]["selected"]["candidate"], "start": 0, "end": 2, "quote": text[:2]}])
    register_policy_reading(root, request, save(root, reading), origin="fixture")
    (root / "another-selection.json").write_bytes((root / "selection.json").read_bytes())
    new = build_policy_evidence_request(root, binding(root, "another-selection.json"), 86)
    assert new["context_sha256"] != request["context_sha256"]
    report = policy_reading_summary(root, new)
    assert len(report["active_negative_declarations"]) == 1
    assert report["pending_applicability"]


def test_changed_candidate_retains_historical_negative_crosswalk_pending(isolated):
    root, request, reading, text = isolated
    reading["checks"][0].update(finding="VIOLATED", support=[{
        "file": request["context"]["selected"]["candidate"], "start": 0, "end": 2, "quote": text[:2]}])
    register_policy_reading(root, request, save(root, reading), origin="fixture")
    (root / "revision.txt").write_bytes((text + "另版\r\n").encode())
    selected = json.loads((root / "selection.json").read_bytes())
    selected["chapters"][0]["candidate"] = binding(root, "revision.txt")
    (root / "revision-selection.json").write_bytes(canonical_bytes(selected))
    new = build_policy_evidence_request(root, binding(root, "revision-selection.json"), 86)
    report = policy_reading_summary(root, new)
    assert not report["active_negative_declarations"]
    assert len(report["historical_negative_declarations"]) == 1
    assert report["pending_applicability"]


@pytest.mark.parametrize("fault", ["raw", "receipt", "orphan", "unreceipted", "unexpected"])
def test_corrupt_or_omitted_registry_custody_blocks_intake(isolated, fault):
    root, request, reading, _ = isolated
    path = save(root, reading)
    register_policy_reading(root, request, path, origin="fixture")
    report = policy_reading_summary(root, request)
    record = report["records"][0]
    if fault == "raw":
        (root / record["raw_reading"]["path"]).write_bytes(b"{}")
    elif fault == "receipt":
        (root / record["receipt"]["path"]).write_bytes(b"{}")
    elif fault == "orphan":
        (root / DIRECTORY / "orphan.json").write_bytes(b"{}")
    elif fault == "unreceipted":
        (root / record["receipt"]["path"]).unlink()
    else:
        (root / DIRECTORY / "favorable-index.json").write_bytes(b"{}")
    report = policy_reading_summary(root, request)
    assert report["integrity_status"] == report["status"] == "FAIL"
    with pytest.raises(ValueError, match="custody invalid"):
        register_policy_reading(root, request, path, origin="another attempt")


def test_stale_historical_context_does_not_hide_raw_negative(isolated):
    root, request, reading, text = isolated
    reading["checks"][0].update(finding="VIOLATED", support=[{
        "file": request["context"]["selected"]["candidate"], "start": 0, "end": 2, "quote": text[:2]}])
    register_policy_reading(root, request, save(root, reading), origin="fixture")
    (root / "candidate.txt").write_bytes(b"changed input")
    report = policy_reading_summary(root)
    assert report["integrity_status"] == "PASS"
    assert report["replay_pending"]
    assert len(report["records"]) == 1
    assert len(report["active_negative_declarations"]) == 1
    assert report["active_negative_declarations"][0]["check"]["finding"] == "VIOLATED"


def test_same_policy_bytes_different_path_preserves_negative(isolated):
    root, request, reading, text = isolated
    reading["checks"][0].update(finding="VIOLATED", support=[{
        "file": request["context"]["selected"]["candidate"], "start": 0, "end": 2, "quote": text[:2]}])
    register_policy_reading(root, request, save(root, reading), origin="fixture")
    policy = request["context"]["selected"]["policy"]
    (root / "same-policy.json").write_bytes((root / policy["path"]).read_bytes())
    selected = json.loads((root / "selection.json").read_bytes())
    selected["chapters"][0]["policy"] = binding(root, "same-policy.json")
    (root / "repacked.json").write_bytes(canonical_bytes(selected))
    other = build_policy_evidence_request(root, binding(root, "repacked.json"), 86)
    report = policy_reading_summary(root, other)
    assert len(report["active_negative_declarations"]) == 1
    assert report["pending_applicability"]


@pytest.mark.parametrize("fault", ["receipt_missing", "receipt_corrupt", "extra_symlink", "schema_changed"])
def test_bad_member_cannot_hide_readable_raw_negative(isolated, fault):
    root, request, reading, text = isolated
    reading["checks"][0].update(finding="VIOLATED", support=[{
        "file": request["context"]["selected"]["candidate"], "start": 0, "end": 2, "quote": text[:2]}])
    result = register_policy_reading(root, request, save(root, reading), origin="fixture")
    receipt = root / result["bundle"] / "receipt.json"
    if fault == "receipt_missing":
        receipt.unlink()
    elif fault == "receipt_corrupt":
        receipt.write_bytes(b"{}")
    elif fault == "schema_changed":
        raw = root / result["bundle"] / "raw.json"
        changed = json.loads(raw.read_bytes())
        changed["extra"] = "new unsupported field"
        raw.write_bytes(canonical_bytes(changed))
    else:
        (root / DIRECTORY / "extra-link").symlink_to(root / "candidate.txt")
    report = policy_reading_summary(root, request)
    assert report["integrity_status"] == "FAIL"
    negatives = report["active_negative_declarations"] + report["unverified_negative_declarations"]
    assert len(negatives) == 1
    assert negatives[0]["check"]["finding"] == "VIOLATED"


def test_interrupted_stage_can_retry_without_orphan_in_registry(isolated, monkeypatch):
    root, request, reading, _ = isolated
    import rcwh.evaluation.policy_readings as runtime
    original = runtime.os.rename
    def interrupted(*args):
        raise OSError("simulated publish interruption")
    monkeypatch.setattr(runtime.os, "rename", interrupted)
    file = save(root, reading)
    with pytest.raises(OSError, match="interruption"):
        register_policy_reading(root, request, file, origin="fixture")
    report = policy_reading_summary(root, request)
    assert report["integrity_status"] == "PASS" and not report["records"]
    monkeypatch.setattr(runtime.os, "rename", original)
    assert register_policy_reading(root, request, file, origin="fixture")["written"]
    assert len(policy_reading_summary(root, request)["records"]) == 1


def test_stale_old_request_does_not_block_new_valid_intake(isolated):
    root, request, reading, text = isolated
    reading["checks"][0].update(finding="VIOLATED", support=[{
        "file": request["context"]["selected"]["candidate"], "start": 0, "end": 2, "quote": text[:2]}])
    register_policy_reading(root, request, save(root, reading), origin="old fixture")
    # Change the original selected candidate dependency without overwriting saved
    # request/raw bundle bytes; new selection binds a new actual version.
    (root / "candidate.txt").write_bytes((text + "变更").encode())
    selected = json.loads((root / "selection.json").read_bytes())
    selected["chapters"][0]["candidate"] = binding(root, "candidate.txt")
    (root / "new-selection.json").write_bytes(canonical_bytes(selected))
    new = build_policy_evidence_request(root, binding(root, "new-selection.json"), 86)
    fresh = deepcopy(reading)
    for key in ("request_sha256", "context_sha256", "manifest_sha256"):
        fresh[key] = new[key]
    fresh["candidate_sha256"] = new["context"]["selected"]["candidate"]["sha256"]
    fresh["checks"] = []
    fresh["read_scope"] = []
    register_policy_reading(root, new, save(root, fresh, "fresh.json"), origin="new fixture")
    report = policy_reading_summary(root, new)
    assert report["integrity_status"] == "PASS" and report["replay_pending"]
    assert len(report["records"]) == 2 and len(report["historical_negative_declarations"]) == 1


@pytest.mark.parametrize("payload", [b"[]", b"null"])
def test_nonobject_request_does_not_crash_or_hide_raw_negative(isolated, payload):
    root, request, reading, text = isolated
    reading["checks"][0].update(finding="VIOLATED", support=[{
        "file": request["context"]["selected"]["candidate"], "start": 0, "end": 2, "quote": text[:2]}])
    result = register_policy_reading(root, request, save(root, reading), origin="fixture")
    (root / result["bundle"] / "request.json").write_bytes(payload)
    report = policy_reading_summary(root, request)
    assert report["integrity_status"] == "FAIL"
    assert len(report["unverified_negative_declarations"]) == 1


def test_fifo_receipt_is_rejected_without_reading(isolated):
    import os
    root, request, reading, _ = isolated
    result = register_policy_reading(root, request, save(root, reading), origin="fixture")
    path = root / result["bundle"] / "receipt.json"
    path.unlink()
    os.mkfifo(path)
    report = policy_reading_summary(root, request)
    assert report["integrity_status"] == "FAIL"
    assert any("regular registry file" in issue for issue in report["findings"])


def test_other_chapter_negative_is_history_not_revision_crosswalk(isolated):
    root, request, reading, text = isolated
    reading["checks"][0].update(finding="VIOLATED", support=[{
        "file": request["context"]["selected"]["candidate"], "start": 0, "end": 2, "quote": text[:2]}])
    register_policy_reading(root, request, save(root, reading), origin="fixture")
    from rcwh.agent_policies import derive_agent_anchors
    policy = derive_agent_anchors(root, 87)
    (root / "policy87.json").write_bytes(canonical_bytes(policy))
    (root / "candidate87.txt").write_bytes("第八十七回 测试\n正文。落叶萧萧，寒烟漠漠\n".encode())
    selected = json.loads((root / "selection.json").read_bytes())
    row = selected["chapters"][0]
    row.update(chapter=87, policy=binding(root, "policy87.json"), candidate=binding(root, "candidate87.txt"))
    (root / "selection87.json").write_bytes(canonical_bytes(selected))
    other = build_policy_evidence_request(root, binding(root, "selection87.json"), 87)
    report = policy_reading_summary(root, other)
    assert len(report["historical_negative_declarations"]) == 1
    assert report["pending_applicability"] == []


def test_inventory_completeness_not_claimed_from_surviving_files(isolated):
    root, request, reading, _ = isolated
    register_policy_reading(root, request, save(root, reading), origin="fixture")
    assert policy_reading_summary(root, request)["inventory_completeness"] == "PENDING_NO_INDEPENDENT_EXPECTED_BUNDLE_ANCHOR"


def test_summary_refuses_to_read_mid_publish(isolated):
    root, request, reading, _ = isolated
    from rcwh.evaluation.policy_readings import _registry_lock
    register_policy_reading(root, request, save(root, reading), origin="fixture")
    with _registry_lock(root):
        report = policy_reading_summary(root, request)
        assert report["integrity_status"] == "FAIL"
        assert any("temporarily unavailable" in item.lower() or "resource" in item.lower() for item in report["findings"])
    assert len(policy_reading_summary(root, request)["records"]) == 1


def test_same_registry_concurrent_writer_lock_refuses_second_intake(isolated):
    root, request, reading, _ = isolated
    from rcwh.evaluation.policy_readings import _registry_lock
    file = save(root, reading)
    with _registry_lock(root):
        with pytest.raises(OSError):
            register_policy_reading(root, request, file, origin="second writer")
    assert not (root / DIRECTORY).exists()


def test_intake_rejects_link_and_blank_origin(isolated):
    root, request, reading, _ = isolated
    file = save(root, reading)
    with pytest.raises(ValueError):
        register_policy_reading(root, request, file, origin=" ")
    link = root / "link.json"
    link.symlink_to(file)
    with pytest.raises(ValueError):
        register_policy_reading(root, request, link, origin="fixture")


def test_registry_directory_symlink_reports_integrity_failure(isolated):
    root, request, _, _ = isolated
    outside = root / "other"
    outside.mkdir()
    base = root / DIRECTORY
    base.parent.mkdir(parents=True, exist_ok=True)
    base.symlink_to(outside, target_is_directory=True)
    report = policy_reading_summary(root, request)
    assert report["status"] == report["integrity_status"] == "FAIL"


def test_summary_rejects_type_aliased_request_even_without_records(isolated):
    root, request, _, _ = isolated
    request["schema_version"] = True
    report = policy_reading_summary(root, request)
    assert report["integrity_status"] == "FAIL"
