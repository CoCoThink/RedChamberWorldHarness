"""Only synthetic model opinions in tiny local repositories; no provider calls."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import shutil

import pytest

from rcwh.application import agent_panel as cli
from rcwh.candidate_reviews import canonical_bytes, digest
from rcwh.schema import validate_instance
from rcwh.workflow import agent_panel as panel


ROOT = Path(__file__).resolve().parents[1]


def save(root, path, value):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(value if isinstance(value, bytes) else canonical_bytes(value))
    return target


def bound(root, path):
    return {"path": path, "sha256": digest((root / path).read_bytes())}


def snapshot(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*")
            if p.is_file() and ".rcwh-cache" not in p.parts}


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "repo"
    (root / "schemas").mkdir(parents=True)
    for name in ("agent_packet", "agent_review", "source_audit_review", "corpus_audit_review", "candidate_review", "semantic_reading"):
        shutil.copyfile(ROOT / f"schemas/{name}.schema.json", root / f"schemas/{name}.schema.json")
    save(root, "data/provenance/sources/a.yaml", {
        "schema_version": 1, "sources": [{"id": "src:a", "text": "真实原文。", "text_sha256": digest("真实原文。".encode())}]})
    save(root, "data/corpus/manifest.json", {"dataset_ref": "corpus:synthetic"})
    samples = [{"segment_id": f"seg:{i}", "text": f"正文{i}。", "text_sha256": digest(f"正文{i}。".encode())} for i in range(2)]
    save(root, "data/corpus/segments.jsonl", b"".join(canonical_bytes(s) for s in samples))
    save(root, "artifacts/candidate.txt", b"synthetic candidate bytes\r\n")
    return root


def make_packet(root, scopes=("SOURCE", "CORPUS", "CANDIDATE"), path="artifacts/agent-packet.json"):
    all_subjects = {
        "SOURCE": {"id": "subject:source", "scope": "SOURCE", "source_ref": "src:a",
                   "binding": bound(root, "data/provenance/sources/a.yaml")},
        "CORPUS": {"id": "subject:corpus", "scope": "CORPUS", "dataset_ref": "corpus:synthetic",
                   "binding": bound(root, "data/corpus/manifest.json"),
                   "samples": [{"id": f"seg:{i}", "binding": bound(root, "data/corpus/segments.jsonl")} for i in range(2)]},
        "CANDIDATE": {"id": "subject:candidate", "scope": "CANDIDATE", "binding": bound(root, "artifacts/candidate.txt")},
    }
    value = {"schema_version": 1, "packet_kind": "AGENT_REVIEW_PACKET", "id": f"packet:{path}",
             "coordinator_session_id": "session:coordinator", "subjects": [all_subjects[s] for s in scopes],
             "authority_effect": "NONE", "usage": "RESEARCH_ONLY"}
    save(root, path, value)
    return bound(root, path), value


def opinion(binding, packet, reviewer=1, verdict="PASS"):
    return {"schema_version": 1, "report_kind": "AGENT_REVIEW_OPINION", "packet": deepcopy(binding),
            "reviewer": {"id": f"reviewer:{reviewer}", "kind": "MODEL_SUBAGENT", "session_id": f"session:{reviewer}",
                         "model": {"label": "synthetic-test-model", "verification": "DECLARED_NOT_VERIFIED"},
                         "context_isolation": {"asserted": True, "verification": "NOT_PROVEN"}},
            "results": [{"subject_id": s["id"], "subject_sha256": s["binding"]["sha256"],
                         "verdict": verdict, "notes": "Synthetic opinion; not a genuine review.",
                         "sample_checks": [{"sample_id": sample["id"], "sha256": sample["binding"]["sha256"],
                                            "verdict": verdict, "notes": "Synthetic sample check."}
                                           for sample in s.get("samples", [])]} for s in packet["subjects"]],
            "authority_effect": "NONE", "usage": "RESEARCH_ONLY", "independent_human_admission": False}


def receive(root, value, filename=None, **kwargs):
    path = save(root, f"incoming/{filename or digest(canonical_bytes(value))}.json", value)
    return panel.register(root, path, origin="test:synthetic-fixture", **kwargs)


def test_empty_panel_is_pending_not_a_synthetic_pass(repo):
    result = panel.summary(repo)
    assert result["status"] == "PENDING" and result["review_count"] == 0
    assert result["panels"] == result["records"] == []
    assert result["independent_human_admission"] is False


def test_two_distinct_full_reviewers_each_subject_and_retained_actual_output(repo):
    binding, packet = make_packet(repo)
    one = receive(repo, opinion(binding, packet, 1))
    assert one["registered"] is True and one["status"] == "PENDING"
    two = receive(repo, opinion(binding, packet, 2))
    assert two["status"] == "PASS"
    result = panel.AgentPanel(repo).summary(packet=binding)
    assert result["status"] == result["record_integrity_status"] == "PASS"
    assert result["review_count"] == 2 and len(result["panels"]) == 1
    assert all(s["status"] == "PASS" and s["distinct_reviewer_count"] == 2 for s in result["panels"][0]["subjects"])
    assert result["authority_effect"] == result["evidence_effect"] == "NONE"
    assert result["usage"] == "RESEARCH_ONLY" and result["independent_human_admission"] is False
    assert result["automatic_literary_pass"] is False
    assert result["independence_limitations"] == panel.LIMITATIONS
    for registered in (one, two):
        raw = (repo / registered["raw_output"]["path"]).read_bytes()
        structured_raw = (repo / registered["record"]["path"]).read_bytes()
        assert digest(raw) == registered["raw_output"]["sha256"]
        assert digest(structured_raw) == registered["record"]["sha256"]
        assert json.loads(structured_raw)["opinion"] == json.loads(raw)
        assert registered["record"]["path"].endswith(digest(structured_raw) + ".json")


@pytest.mark.parametrize("negative", ["FAIL", "REJECT"])
def test_negative_precedence_keeps_all_opinions_not_just_favorable_pair(repo, negative):
    binding, packet = make_packet(repo)
    adverse = opinion(binding, packet, 1, negative)
    result = receive(repo, adverse)
    before = snapshot(repo)
    assert result["registered"] and result["status"] == "FAIL"
    receive(repo, opinion(binding, packet, 2))
    receive(repo, opinion(binding, packet, 3))
    result = panel.summary(repo, packet=binding)
    assert result["status"] == "FAIL" and result["review_count"] == 3
    assert all(s["status"] == "FAIL" and len(s["opinions"]) == 3 for s in result["panels"][0]["subjects"])
    assert all((repo / p).read_bytes() == raw for p, raw in before.items())
    assert result["panels"][0]["subjects"][0]["opinions"][0]["verdict"] in {negative, "PASS"}
    assert sum(o["verdict"] == negative for o in result["panels"][0]["subjects"][0]["opinions"]) == 1


def test_later_negative_from_same_reviewer_is_retained_and_overrules(repo):
    binding, packet = make_packet(repo, ("CANDIDATE",))
    receive(repo, opinion(binding, packet, 1))
    receive(repo, opinion(binding, packet, 2))
    receive(repo, opinion(binding, packet, 1, "REJECT"))
    result = panel.summary(repo, binding)
    assert result["status"] == "FAIL" and result["review_count"] == 3
    assert result["panels"][0]["subjects"][0]["distinct_reviewer_count"] == 2


@pytest.mark.parametrize("duplicate", ["id", "session_id", "both"])
def test_reused_identity_or_session_never_counts_as_two_peers(repo, duplicate):
    binding, packet = make_packet(repo, ("SOURCE",))
    receive(repo, opinion(binding, packet, 1))
    second = opinion(binding, packet, 2)
    if duplicate in ("id", "both"):
        second["reviewer"]["id"] = "reviewer:1"
    if duplicate in ("session_id", "both"):
        second["reviewer"]["session_id"] = "session:1"
    second["results"][0]["notes"] = "Different local opinion bytes, same declared identity."
    receive(repo, second)
    result = panel.summary(repo, binding)
    assert result["status"] == "PENDING"
    assert result["panels"][0]["subjects"][0]["distinct_reviewer_count"] == 1


def test_coordinator_session_cannot_masquerade_as_a_peer(repo):
    binding, packet = make_packet(repo)
    value = opinion(binding, packet)
    value["reviewer"]["session_id"] = packet["coordinator_session_id"]
    with pytest.raises(ValueError, match="differ"):
        receive(repo, value)
    assert not (repo / panel.DIRECTORY).exists()


def test_distinct_two_reviewers_required_for_every_subject(repo):
    binding, packet = make_packet(repo, ("SOURCE", "CANDIDATE"))
    first = opinion(binding, packet, 1)
    second = opinion(binding, packet, 2)
    first["results"] = first["results"][:1]
    second["results"] = second["results"][1:]
    receive(repo, first)
    receive(repo, second)
    result = panel.summary(repo, binding)
    assert result["status"] == "PENDING"
    assert all(s["distinct_reviewer_count"] == 1 for s in result["panels"][0]["subjects"])


def test_splitting_corpus_sample_sets_cannot_count_as_two_full_reviews(repo):
    binding, packet = make_packet(repo, ("CORPUS",))
    first, second = opinion(binding, packet, 1), opinion(binding, packet, 2)
    first["results"][0]["sample_checks"] = first["results"][0]["sample_checks"][:1]
    second["results"][0]["sample_checks"] = second["results"][0]["sample_checks"][1:]
    receive(repo, first)
    receive(repo, second)
    subject = panel.summary(repo, binding)["panels"][0]["subjects"][0]
    assert subject["status"] == "PENDING" and subject["distinct_reviewer_count"] == 0
    assert [r["distinct_reviewer_count"] for r in subject["sample_coverage"]] == [1, 1]
    # Even disjoint pairs do not become two full corpus readers.
    third, fourth = opinion(binding, packet, 3), opinion(binding, packet, 4)
    third["results"][0]["sample_checks"] = third["results"][0]["sample_checks"][:1]
    fourth["results"][0]["sample_checks"] = fourth["results"][0]["sample_checks"][1:]
    receive(repo, third)
    receive(repo, fourth)
    subject = panel.summary(repo, binding)["panels"][0]["subjects"][0]
    assert all(s["status"] == "PASS" for s in subject["sample_coverage"])
    assert subject["status"] == "PENDING" and subject["full_reviewers"] == []


def test_negative_sample_overrules_overall_pass(repo):
    binding, packet = make_packet(repo, ("CORPUS",))
    value = opinion(binding, packet, 1)
    value["results"][0]["sample_checks"][1]["verdict"] = "REJECT"
    receive(repo, value)
    receive(repo, opinion(binding, packet, 2))
    receive(repo, opinion(binding, packet, 3))
    subject = panel.summary(repo, binding)["panels"][0]["subjects"][0]
    assert subject["status"] == "FAIL" and subject["sample_coverage"][1]["status"] == "FAIL"
    assert subject["findings"][0]["rejected_samples"] == ["seg:1"]


@pytest.mark.parametrize("verdict", ["PENDING", "UNVERIFIED", "NOT_CHECKED"])
def test_unknown_opinion_never_becomes_pass_even_with_two_favorable_reviews(repo, verdict):
    binding, packet = make_packet(repo, ("CANDIDATE",))
    receive(repo, opinion(binding, packet, 1, verdict))
    receive(repo, opinion(binding, packet, 2))
    receive(repo, opinion(binding, packet, 3))
    assert panel.summary(repo, binding)["status"] == "PENDING"


def test_unasserted_context_isolation_remains_pending(repo):
    binding, packet = make_packet(repo, ("CANDIDATE",))
    value = opinion(binding, packet, 1)
    value["reviewer"]["context_isolation"]["asserted"] = False
    receive(repo, value)
    receive(repo, opinion(binding, packet, 2))
    assert panel.summary(repo, binding)["status"] == "PENDING"


@pytest.mark.parametrize("fault", ["packet", "subject", "raw", "record", "sample", "manifest", "missing-raw"])
def test_stale_or_missing_byte_binding_truthfully_fails_status(repo, fault):
    binding, packet = make_packet(repo)
    registered = receive(repo, opinion(binding, packet))
    target = {
        "packet": binding["path"], "subject": "data/provenance/sources/a.yaml",
        "raw": registered["raw_output"]["path"], "record": registered["record"]["path"],
        "sample": "data/corpus/segments.jsonl", "manifest": "data/corpus/manifest.json",
        "missing-raw": registered["raw_output"]["path"],
    }[fault]
    if fault == "missing-raw":
        (repo / target).unlink()
    else:
        (repo / target).write_bytes((repo / target).read_bytes() + b"\n")
    result = panel.summary(repo, packet=binding)
    assert result["status"] == result["record_integrity_status"] == "FAIL"
    assert result["findings"]


def test_packet_file_whitespace_is_part_of_binding_not_canonical_json(repo):
    binding, packet = make_packet(repo)
    (repo / binding["path"]).write_text(json.dumps(packet, indent=4), encoding="utf-8")
    with pytest.raises(ValueError, match="stale bound file"):
        receive(repo, opinion(binding, packet))
    assert not (repo / panel.DIRECTORY).exists()


def test_exact_noncanonical_raw_bytes_retained_without_fake_transformation(repo):
    binding, packet = make_packet(repo)
    raw = (json.dumps(opinion(binding, packet), ensure_ascii=False, indent=3) + "\r\n").encode()
    path = save(repo, "incoming/noncanonical.json", raw)
    result = panel.register(repo, path, origin="test:raw")
    assert (repo / result["raw_output"]["path"]).read_bytes() == raw == path.read_bytes()


def test_fabricated_structured_opinion_cannot_replace_original_even_with_fresh_record_hash(repo):
    binding, packet = make_packet(repo)
    result = receive(repo, opinion(binding, packet, 1, "REJECT"))
    record = json.loads((repo / result["record"]["path"]).read_bytes())
    record["opinion"]["results"][0]["verdict"] = "PASS"
    fresh_raw = canonical_bytes(record)
    fresh_binding = {"path": f"{panel.DIRECTORY}/records/{digest(fresh_raw)}.json", "sha256": digest(fresh_raw)}
    save(repo, fresh_binding["path"], fresh_raw)
    save(repo, f"{panel.DIRECTORY}/receipts/{fresh_binding['sha256']}.json", {"schema_version": 1, "record": fresh_binding})
    assert panel.summary(repo)["status"] == "FAIL"
    assert any("raw agent output does not match" in f for f in panel.summary(repo)["findings"])


@pytest.mark.parametrize("fault", ["unknown-subject", "wrong-subject-sha", "unknown-sample", "wrong-sample-sha", "duplicate-subject", "duplicate-sample"])
def test_invalid_opinion_bindings_rejected_before_registration(repo, fault):
    binding, packet = make_packet(repo, ("CORPUS",))
    value = opinion(binding, packet)
    row = value["results"][0]
    if fault == "unknown-subject":
        row["subject_id"] = "subject:invented"
    elif fault == "wrong-subject-sha":
        row["subject_sha256"] = "0" * 64
    elif fault == "unknown-sample":
        row["sample_checks"][0]["sample_id"] = "seg:invented"
    elif fault == "wrong-sample-sha":
        row["sample_checks"][0]["sha256"] = "0" * 64
    elif fault == "duplicate-subject":
        value["results"].append(deepcopy(row))
    else:
        row["sample_checks"].append(deepcopy(row["sample_checks"][0]))
    with pytest.raises(ValueError):
        receive(repo, value)
    assert not (repo / panel.DIRECTORY).exists()


@pytest.mark.parametrize("fault", ["source-ref", "source-text-sha", "dataset-ref", "invented-sample", "duplicate-sample", "duplicate-subject"])
def test_packet_subjects_are_actual_raw_repository_sources_and_manifest(repo, fault):
    binding, packet = make_packet(repo)
    if fault == "source-ref":
        packet["subjects"][0]["source_ref"] = "src:invented"
    elif fault == "source-text-sha":
        source_path = "data/provenance/sources/a.yaml"
        source = json.loads((repo / source_path).read_bytes())
        source["sources"][0]["text_sha256"] = "0" * 64
        save(repo, source_path, source)
        packet["subjects"][0]["binding"] = bound(repo, source_path)
    elif fault == "dataset-ref":
        packet["subjects"][1]["dataset_ref"] = "corpus:invented"
    elif fault == "invented-sample":
        packet["subjects"][1]["samples"][0]["id"] = "seg:invented"
    elif fault == "duplicate-sample":
        packet["subjects"][1]["samples"].append(deepcopy(packet["subjects"][1]["samples"][0]))
    else:
        packet["subjects"].append(deepcopy(packet["subjects"][0]))
    save(repo, binding["path"], packet)
    binding = bound(repo, binding["path"])
    with pytest.raises(ValueError):
        receive(repo, opinion(binding, packet))
    assert not (repo / panel.DIRECTORY).exists()


@pytest.mark.parametrize("unsafe", ["../outside.txt", "/tmp/outside", "data/../bad", "data\\bad", "C:/bad", "data//bad", "./data/bad"])
def test_subject_path_safety_rejects_external_or_noncanonical_paths(repo, unsafe):
    binding, packet = make_packet(repo, ("CANDIDATE",))
    packet["subjects"][0]["binding"]["path"] = unsafe
    save(repo, binding["path"], packet)
    binding = bound(repo, binding["path"])
    with pytest.raises(ValueError):
        receive(repo, opinion(binding, packet))
    assert not (repo / panel.DIRECTORY).exists()


@pytest.mark.parametrize("symlink", ["input", "packet", "subject", "store-parent"])
def test_symlinks_are_rejected_for_input_packet_subject_and_storage(repo, symlink, tmp_path):
    binding, packet = make_packet(repo, ("CANDIDATE",))
    value = opinion(binding, packet)
    file = save(repo, "incoming/opinion.json", value)
    if symlink == "input":
        link = repo / "incoming/link.json"
        link.symlink_to(file)
        file = link
    elif symlink in ("packet", "subject"):
        target = repo / (binding["path"] if symlink == "packet" else packet["subjects"][0]["binding"]["path"])
        original = tmp_path / "original"
        original.write_bytes(target.read_bytes())
        target.unlink()
        target.symlink_to(original)
    else:
        (repo / "data/agent_panel").symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(ValueError):
        panel.register(repo, file, origin="test:symlink")


@pytest.mark.parametrize("fault", ["human", "verified-model", "verified-isolation", "human-admission", "authority", "production", "unknown", "missing-session", "blank-id"])
def test_no_human_coercion_and_schema_qualification_boundaries(repo, fault):
    binding, packet = make_packet(repo)
    value = opinion(binding, packet)
    if fault == "human":
        value["reviewer"]["kind"] = "INDEPENDENT_HUMAN"
    elif fault == "verified-model":
        value["reviewer"]["model"]["verification"] = "VERIFIED"
    elif fault == "verified-isolation":
        value["reviewer"]["context_isolation"]["verification"] = "VERIFIED"
    elif fault == "human-admission":
        value["independent_human_admission"] = True
    elif fault == "authority":
        value["authority_effect"] = "ADMIT"
    elif fault == "production":
        value["usage"] = "PRODUCTION"
    elif fault == "unknown":
        value["independent_of_authors"] = True
    elif fault == "missing-session":
        del value["reviewer"]["session_id"]
    else:
        value["reviewer"]["id"] = "  \t"
    assert validate_instance(value, repo / "schemas/agent_review.schema.json")
    with pytest.raises(ValueError):
        receive(repo, value)
    assert not (repo / panel.DIRECTORY).exists()


@pytest.mark.parametrize("human_schema", ["source_audit_review", "corpus_audit_review", "candidate_review", "semantic_reading"])
def test_agent_opinion_and_filing_envelope_never_validate_as_human_lane(repo, human_schema):
    binding, packet = make_packet(repo)
    value = opinion(binding, packet)
    result = receive(repo, value)
    record = json.loads((repo / result["record"]["path"]).read_bytes())
    assert not validate_instance(value, repo / "schemas/agent_review.schema.json")
    assert not validate_instance(record, repo / "schemas/agent_review.schema.json")
    assert validate_instance(value, repo / f"schemas/{human_schema}.schema.json")
    assert validate_instance(record, repo / f"schemas/{human_schema}.schema.json")


def test_duplicate_original_cannot_overwrite_immutable_record(repo):
    binding, packet = make_packet(repo)
    value = opinion(binding, packet)
    receive(repo, value)
    before = snapshot(repo)
    with pytest.raises(ValueError, match="already registered"):
        receive(repo, value)
    assert snapshot(repo) == before


def test_status_inspects_unreceipted_records_and_every_existing_receipt(repo):
    binding, packet = make_packet(repo)
    result = receive(repo, opinion(binding, packet))
    (repo / f"{panel.DIRECTORY}/receipts/{result['record']['sha256']}.json").unlink()
    summary = panel.summary(repo)
    assert summary["status"] == "FAIL"
    assert any("unreceipted" in f for f in summary["findings"])
    save(repo, f"{panel.DIRECTORY}/receipts/broken.json", b"not JSON")
    assert len(panel.summary(repo)["records"]) == 2


def test_scoped_panel_does_not_fail_for_unrelated_valid_negative_but_inspects_it(repo):
    first, packet1 = make_packet(repo, ("CANDIDATE",), "artifacts/packet-one.json")
    second, packet2 = make_packet(repo, ("SOURCE",), "artifacts/packet-two.json")
    receive(repo, opinion(first, packet1, 1))
    receive(repo, opinion(first, packet1, 2))
    other = receive(repo, opinion(second, packet2, 3, "REJECT"))
    assert panel.summary(repo)["status"] == "FAIL"
    scoped = panel.summary(repo, packet=first)
    assert scoped["status"] == "PASS" and len(scoped["records"]) == 3
    assert scoped["panels"][0]["packet"] == first and len(scoped["panels"]) == 1
    # A broken record of another packet is surfaced store-wide (and fails
    # `rcwh validate`), but is not imputed to an unrelated packet.
    (repo / other["raw_output"]["path"]).write_bytes(b"changed")
    scoped = panel.summary(repo, packet=first)
    assert scoped["status"] == "PASS" and scoped["store_integrity_status"] == "FAIL"
    assert scoped["store_findings"] and panel.summary(repo)["status"] == "FAIL"
    assert panel.summary(repo, packet=second)["status"] == "FAIL"


def test_reissued_packet_cannot_hide_same_byte_negative_opinion(repo):
    first, packet1 = make_packet(repo, ("CANDIDATE",), "artifacts/packet-old.json")
    receive(repo, opinion(first, packet1, 1, "REJECT"))
    second, packet2 = make_packet(repo, ("CANDIDATE",), "artifacts/packet-new.json")
    packet2["subjects"][0]["id"] = "subject:renamed"
    save(repo, second["path"], packet2)
    second = bound(repo, second["path"])
    receive(repo, opinion(second, packet2, 2))
    receive(repo, opinion(second, packet2, 3))
    subject = panel.summary(repo, second)["panels"][0]["subjects"][0]
    assert subject["status"] == "FAIL" and len(subject["opinions"]) == 3
    assert subject["distinct_reviewer_count"] == 2
    assert any(o["verdict"] == "REJECT" and o["packet"] == first for o in subject["opinions"])
    assert any(p["reason"] == "DIFFERENT_PACKET_CONTEXT_FOR_SAME_SUBJECT_BYTES" for p in subject["pending"])


def test_same_byte_old_packet_positive_is_not_new_context_peer_credit(repo):
    first, packet1 = make_packet(repo, ("CANDIDATE",), "artifacts/old.json")
    receive(repo, opinion(first, packet1, 1))
    second, packet2 = make_packet(repo, ("CANDIDATE",), "artifacts/new.json")
    receive(repo, opinion(second, packet2, 2))
    subject = panel.summary(repo, second)["panels"][0]["subjects"][0]
    assert subject["status"] == "PENDING" and subject["distinct_reviewer_count"] == 1
    assert len(subject["opinions"]) == 2


def test_registration_preserves_independent_human_selections_and_admission_inputs(repo):
    human_files = ["data/provenance/audits/selection.json", "data/corpus/audits/selection.json",
                   "data/evaluation/paired_selection.json", "data/evaluation/scene_readings.json",
                   "data/project/closure_roots.json", "data/project/owners.json"]
    for path in human_files:
        save(repo, path, b'{ "fixture" : "immutable human lane" }\n')
    original = {path: (repo / path).read_bytes() for path in human_files}
    binding, packet = make_packet(repo)
    result = receive(repo, opinion(binding, packet, 1))
    assert all((repo / path).read_bytes() == raw for path, raw in original.items())
    assert all(path.startswith(panel.DIRECTORY + "/") for path in result["written_files"])
    assert result["independent_human_admission"] is False


def test_requested_packet_without_registered_reviews_reports_all_subjects_pending(repo):
    binding, packet = make_packet(repo)
    result = panel.summary(repo, packet=binding)
    assert result["status"] == "PENDING" and len(result["panels"][0]["subjects"]) == 3
    assert all(s["status"] == "PENDING" for s in result["panels"][0]["subjects"])


def test_dry_run_does_not_create_records_receipts_or_lock(repo):
    binding, packet = make_packet(repo)
    path = save(repo, "incoming/dry.json", opinion(binding, packet))
    before = snapshot(repo)
    result = panel.register(repo, path, origin="test:dry", dry_run=True)
    assert result["status"] == "PASS" and result["dry_run"] and not result["registered"]
    assert result["written_files"] == [] and snapshot(repo) == before
    assert not (repo / ".rcwh-cache").exists()


@pytest.mark.parametrize("invalid", ["duplicate-key", "nonfinite", "list", "origin", "network-origin"])
def test_invalid_json_or_non_file_origin_rejected_without_registration(repo, invalid):
    binding, packet = make_packet(repo)
    raw = canonical_bytes(opinion(binding, packet))
    if invalid == "duplicate-key":
        raw = b'{"schema_version":1,' + raw[1:]
    elif invalid == "nonfinite":
        raw = raw.replace(b'"schema_version":1', b'"schema_version":NaN')
    elif invalid == "list":
        raw = b"[]"
    path = save(repo, "incoming/invalid.json", raw)
    with pytest.raises(ValueError):
        panel.register(repo, path, origin=" " if invalid == "origin" else "test:bad",
                       origin_kind="PROVIDER" if invalid == "network-origin" else "FILE")
    assert not (repo / panel.DIRECTORY).exists()


def parser():
    result = argparse.ArgumentParser()
    result.add_argument("--root")
    cli.add_commands(result.add_subparsers(dest="command", required=True))
    return result


def test_standalone_add_commands_status_and_register_cli(repo, capsys):
    args = parser().parse_args(["--root", str(repo), "agent-panel", "status"])
    assert args.func(args) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "PENDING"
    binding, packet = make_packet(repo)
    path = save(repo, "incoming/cli.json", opinion(binding, packet, 1, "REJECT"))
    args = parser().parse_args(["--root", str(repo), "agent-panel", "register", str(path), "--origin", "test:cli"])
    assert args.func(args) == 1
    report = json.loads(capsys.readouterr().out)
    assert report["registered"] and report["status"] == "FAIL"
    args = parser().parse_args(["--root", str(repo), "agent-panel", "status", "--packet", binding["path"]])
    assert args.func(args) == 1
    assert json.loads(capsys.readouterr().out)["panels"][0]["packet"] == binding


def test_cli_failure_is_truthful_not_claimed_registration(repo, capsys):
    args = parser().parse_args(["--root", str(repo), "agent-panel", "register", "missing.json", "--origin", "test:missing"])
    assert args.func(args) == 1
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "FAIL" and result["independent_human_admission"] is False
    assert "registered" not in result


def test_non_blocking_negative_counts_as_review_and_stays_advisory(repo):
    binding, packet = make_packet(repo, ("CANDIDATE",))
    receive(repo, opinion(binding, packet, 1))
    soft = opinion(binding, packet, 2, "FAIL")
    soft["results"][0]["severity"] = "ADVISORY"
    receive(repo, soft)
    subject = panel.summary(repo, packet=binding)["panels"][0]["subjects"][0]
    assert subject["status"] == "PASS" and subject["distinct_reviewer_count"] == 2
    assert [a["severity"] for a in subject["advisories"]] == ["ADVISORY"]
    hard = opinion(binding, packet, 3, "FAIL")  # No severity declared means BLOCKING.
    receive(repo, hard)
    assert panel.summary(repo, packet=binding)["panels"][0]["subjects"][0]["status"] == "FAIL"


def test_reviewer_supersedes_own_record_but_history_is_kept(repo):
    binding, packet = make_packet(repo, ("CANDIDATE",))
    receive(repo, opinion(binding, packet, 1))
    old = receive(repo, opinion(binding, packet, 2, "FAIL"))
    assert panel.summary(repo, packet=binding)["status"] == "FAIL"
    revised = opinion(binding, packet, 2)
    revised["supersedes"] = [old["record"]]
    receive(repo, revised)
    subject = panel.summary(repo, packet=binding)["panels"][0]["subjects"][0]
    assert subject["status"] == "PASS"
    assert [o["record"] for o in subject["superseded_opinions"]] == [old["record"]]


def test_reviewer_cannot_supersede_another_reviewers_negative(repo):
    binding, packet = make_packet(repo, ("CANDIDATE",))
    receive(repo, opinion(binding, packet, 1))
    other = receive(repo, opinion(binding, packet, 2, "FAIL"))
    forged = opinion(binding, packet, 3)
    forged["supersedes"] = [other["record"]]
    with pytest.raises(ValueError, match="their own"):
        receive(repo, forged)
    assert panel.summary(repo, packet=binding)["panels"][0]["subjects"][0]["status"] == "FAIL"


def test_scaffold_prefills_exact_bindings_and_rejects_unfilled_skeleton(repo):
    binding, packet = make_packet(repo)
    skeleton = panel.scaffold(repo, binding["path"], reviewer_id="reviewer:s", session_id="session:s")
    assert skeleton["packet"] == binding
    by_id = {r["subject_id"]: r for r in skeleton["results"]}
    assert set(by_id) == {s["id"] for s in packet["subjects"]}
    assert all(r["subject_sha256"] == s["binding"]["sha256"]
               for r in skeleton["results"] for s in packet["subjects"] if s["id"] == r["subject_id"])
    assert by_id["subject:candidate"]["sample_checks"] == []
    assert [c["sample_id"] for c in by_id["subject:corpus"]["sample_checks"]] == ["seg:0", "seg:1"]
    path = save(repo, "incoming/skeleton.json", skeleton)
    with pytest.raises(ValueError):  # empty verdicts/notes never become records
        panel.register(repo, path, origin="test:scaffold")


def test_scaffold_filled_in_registers_and_subject_filter_is_checked(repo):
    binding, packet = make_packet(repo)
    skeleton = panel.scaffold(repo, binding["path"], reviewer_id="reviewer:s", session_id="session:s",
                              subjects=["subject:candidate"])
    assert [r["subject_id"] for r in skeleton["results"]] == ["subject:candidate"]
    skeleton["results"][0].update(verdict="PASS", notes="Filled by the reviewer after reading.")
    result = receive(repo, skeleton)
    assert result["status"] in {"PASS", "PENDING"}
    with pytest.raises(ValueError, match="unknown packet subjects"):
        panel.scaffold(repo, binding["path"], reviewer_id="r", session_id="s", subjects=["nope"])
