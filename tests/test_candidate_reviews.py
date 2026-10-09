"""Synthetic submissions exercise custody/identity checks, not literary quality."""
from copy import deepcopy
from pathlib import Path
import shutil

import pytest

from rcwh.candidate_reviews import (
    CandidateReviewService, REVIEW_CHECKS, canonical_bytes, digest,
    raw_opinion, review_packet,
)
from rcwh.competition import CompetitionRegistry


ROOT = Path(__file__).resolve().parents[1]
COMPETITION = "comp:43-0:ch86:pressure-test"


def write_binding(root, path, value):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    raw = canonical_bytes(value)
    target.write_bytes(raw)
    return {"path": path, "sha256": digest(raw)}


@pytest.fixture
def reviewed_competition(tmp_path):
    return make_reviewed_competition(tmp_path)


def make_reviewed_competition(tmp_path, record=None):
    shutil.copytree(ROOT / "schemas", tmp_path / "schemas")
    suite = tmp_path / "data/literary_eval"
    suite.mkdir(parents=True)
    shutil.copyfile(ROOT / "data/literary_eval/v05_suite.json", suite / "v05_suite.json")
    record = deepcopy(record or CompetitionRegistry.from_repo(ROOT).records[COMPETITION])
    record["adjudication_basis"] = "CURRENT_SUBMISSIONS"
    for candidate in record["candidates"]:
        path = candidate["artifact"]["path"]
        (tmp_path / path).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / path, tmp_path / path)
        candidate["authors"] = [{"principal_id": f"author:{candidate['id']}",
                                  "source_id": f"source:author:{candidate['id']}", "kind": "HUMAN"}]
    record["review_protocol"] = write_binding(tmp_path, "reviews/protocol.json", {
        "schema_version": 1, "id": "fixture:protocol", "minimum_reviewers": 2,
        "questions": ["测试数据：逐项判断并引用正文；不构成实际文学评审。"], "authority_effect": "NONE",
    })
    prepared = review_packet(tmp_path, record)
    packet = write_binding(tmp_path, "reviews/packet.json", prepared["packet"])
    opinions = {}
    for candidate in record["candidates"]:
        text = (tmp_path / candidate["artifact"]["path"]).read_bytes().decode("utf-8")
        candidate["review_records"] = []
        opinions[candidate["id"]] = []
        for reviewer in range(2):
            review = {
                "schema_version": 1, "id": f"fixture:{candidate['id']}:{reviewer}",
                "report_kind": "REVIEW_OPINION", "blind_token": candidate["blind_token"],
                "candidate_sha256": digest(text.encode()), "context_sha256": prepared["context_sha256"],
                "protocol": record["review_protocol"], "packet": packet,
                "reviewer": {"principal_id": f"fixture:reader:{reviewer}", "source_id": f"fixture:source:{reviewer}",
                             "kind": "INDEPENDENT_HUMAN", "independent_of_authors": True,
                             "mapping_unseen_during_review": True},
                "checks": {name: {"status": "PASS", "reason": "合成测试意见，无实际评审效力。",
                                  "evidence_spans": [{"start": 0, "end": 20, "quote": text[:20]}]}
                           for name in REVIEW_CHECKS},
                "authority_effect": "NONE",
            }
            save_review(tmp_path, candidate, review)
            opinions[candidate["id"]].append(review)
    return tmp_path, record, opinions


def save_review(root, candidate, review):
    review["raw_review"] = write_binding(root, f"reviews/{review['id'].replace(':', '-')}-raw.json", raw_opinion(review))
    binding = write_binding(root, f"reviews/{review['id'].replace(':', '-')}.json", review)
    if "review_records" in candidate:
        candidate["review_records"] = [b for b in candidate["review_records"] if b["path"] != binding["path"]]
    candidate.setdefault("review_records", []).append(binding)


def evaluate(fixture, machine_status="READY_FOR_BLIND_READ"):
    root, record, _ = fixture
    return CandidateReviewService(root, record).evaluate(record["candidates"][0], machine_status)


def test_two_bound_independent_opinions_qualify_and_hand_flags_are_ignored(reviewed_competition, monkeypatch):
    root, record, _ = reviewed_competition
    for candidate in record["candidates"]:
        candidate["six_field"] = {name: "FAIL" for name in candidate["six_field"]}
        candidate["human_plock"]["status"] = "PENDING"
        candidate["blind_read"].update(status="PENDING", reviewer_blinded=False)
    assert evaluate(reviewed_competition)["status"] == "PASS"
    monkeypatch.setattr("rcwh.competition.candidate_semantics", lambda *a: {"status": "PASS", "reports": []})
    monkeypatch.setattr("rcwh.competition.run_r4_evidence_regression", lambda _: {"overall": "PASS"})
    monkeypatch.setattr("rcwh.competition.evaluate_literary_candidate", lambda *a, **k: {"machine_status": "READY_FOR_BLIND_READ"})
    payload = CompetitionRegistry({}).evaluate_record(root, record)
    assert payload["consistency_errors"] == []
    assert payload["adjudication_qualification"] == "PASS"
    assert payload["adjudication"]["winner_candidate_id"] == "ch86-B"
    assert all(row["adjudication_eligible"] for row in payload["candidate_results"])


def test_missing_second_reviewer_is_pending(reviewed_competition):
    reviewed_competition[1]["candidates"][0]["review_records"].pop()
    report = evaluate(reviewed_competition)
    assert report["status"] == "PENDING"
    assert report["review_count"] == 1
    assert set(report["check_statuses"].values()) == {"PENDING"}


def test_protocol_questions_cannot_leak_candidate_or_author_identity(reviewed_competition):
    root, record, _ = reviewed_competition
    record["review_protocol"] = write_binding(root, "reviews/protocol.json", {
        "schema_version": 1, "id": "fixture:leaking-protocol", "minimum_reviewers": 2,
        "questions": ["ch86-A is written by author:ch86-A"], "authority_effect": "NONE",
    })
    with pytest.raises(ValueError, match="leaks metadata"):
        review_packet(root, record)


@pytest.mark.parametrize("identity", ["principal_id", "source_id"])
def test_duplicate_reviewer_aliases_do_not_count_twice(reviewed_competition, identity):
    root, record, opinions = reviewed_competition
    candidate = record["candidates"][0]
    first, second = opinions[candidate["id"]]
    second["reviewer"][identity] = first["reviewer"][identity]
    save_review(root, candidate, second)
    report = evaluate(reviewed_competition)
    assert report["status"] == "FAIL"
    assert any("duplicate reviewer" in finding for finding in report["findings"])


@pytest.mark.parametrize("identity", ["principal_id", "source_id"])
def test_reviewer_cannot_be_author_of_another_candidate(reviewed_competition, identity):
    root, record, opinions = reviewed_competition
    candidate = record["candidates"][0]
    review = opinions[candidate["id"]][0]
    review["reviewer"][identity] = record["candidates"][1]["authors"][0][identity]
    save_review(root, candidate, review)
    assert any("shares an author" in x for x in evaluate(reviewed_competition)["findings"])


@pytest.mark.parametrize("fault", ["candidate", "context", "protocol", "packet", "raw_review", "span", "coverage", "blinding", "reject", "model_reviewer"])
def test_changed_inputs_or_invalid_opinions_fail_closed(reviewed_competition, fault):
    root, record, opinions = reviewed_competition
    candidate = record["candidates"][0]
    review = opinions[candidate["id"]][0]
    if fault == "candidate":
        path = root / candidate["artifact"]["path"]
        path.write_bytes(path.read_bytes() + b"\n")
    elif fault == "context":
        write_binding(root, "data/world/test.json", {"new_context": True})
    elif fault == "protocol":
        review["protocol"]["sha256"] = "0" * 64
        save_review(root, candidate, review)
    elif fault in {"packet", "raw_review"}:
        write_binding(root, review[fault]["path"], {"invented": "PASS"})
    else:
        if fault == "span":
            review["checks"]["ROLE"]["evidence_spans"][0]["quote"] = "不存在的正文"
        elif fault == "coverage":
            del review["checks"]["ROLE"]
        elif fault == "blinding":
            review["reviewer"]["mapping_unseen_during_review"] = False
        elif fault == "reject":
            review["checks"]["ROLE"]["status"] = "FAIL"
        else:
            review["reviewer"]["kind"] = "MODEL"
        save_review(root, candidate, review)
    report = evaluate(reviewed_competition)
    assert report["status"] == "FAIL"
    assert report["findings"]
    assert set(report["check_statuses"].values()) == {"FAIL"}


def test_missing_author_identity_is_pending_not_independent(reviewed_competition):
    root, record, opinions = reviewed_competition
    del record["candidates"][1]["authors"]
    prepared = review_packet(root, record)
    # Rebind the changed context to isolate missing identity from stale input.
    candidate = record["candidates"][0]
    for review in opinions[candidate["id"]]:
        review["context_sha256"] = prepared["context_sha256"]
        save_review(root, candidate, review)
    report = evaluate(reviewed_competition)
    assert report["status"] == "PENDING"
    assert any("author identity" in item for item in report["pending"])


def test_replacement_case_requires_explicit_acceptance_from_both_reviewers(reviewed_competition):
    assert evaluate(reviewed_competition, "REPLACEMENT_CASE")["status"] == "FAIL"
    root, record, opinions = reviewed_competition
    candidate = record["candidates"][0]
    for review in opinions[candidate["id"]]:
        review["checks"]["HUMAN_PLOCK"]["status"] = "REPLACEMENT_ACCEPTED"
        save_review(root, candidate, review)
    report = evaluate(reviewed_competition, "REPLACEMENT_CASE")
    assert report["status"] == "PASS"
    assert report["check_statuses"]["HUMAN_PLOCK"] == "REPLACEMENT_ACCEPTED"


@pytest.mark.parametrize("fault", [None, "metadata", "prompt", "input", "output", "candidate"])
def test_model_author_requires_bound_metadata_prompt_and_actual_io(reviewed_competition, fault):
    root, record, opinions = reviewed_competition
    candidate = record["candidates"][0]
    text = (root / candidate["artifact"]["path"]).read_bytes().decode("utf-8")
    prompt, input_text = "Synthetic test instruction", "Synthetic test input"
    run = {
        "schema_version": 1, "source_id": "model:fixture:family",
        "model": {"provider": "fixture", "name": "test-model", "version": "test-v1",
                  "family": "fixture-family", "session": "fixture-session"},
        "prompt": prompt, "prompt_sha256": digest(prompt.encode()), "prompt_summary": "Test only",
        "input": input_text, "input_sha256": digest(input_text.encode()),
        "output": text, "output_sha256": digest(text.encode()),
    }
    if fault == "metadata":
        del run["model"]["version"]
    elif fault in {"prompt", "input", "output"}:
        run[f"{fault}_sha256"] = "0" * 64
    elif fault == "candidate":
        run["output"] = "An unrelated test output"
        run["output_sha256"] = digest(run["output"].encode())
    candidate["authors"] = [{"principal_id": "agent:fixture", "source_id": run["source_id"], "kind": "MODEL",
                             "run": write_binding(root, "reviews/model-run.json", run)}]
    prepared = review_packet(root, record)
    for review in opinions[candidate["id"]]:
        review["context_sha256"] = prepared["context_sha256"]
        save_review(root, candidate, review)
    report = evaluate(reviewed_competition)
    assert report["status"] == ("FAIL" if fault else "PASS")


def test_production_promotion_reads_current_review_qualification(reviewed_competition, monkeypatch):
    from rcwh.promotion import PromotionRegistry

    fixture_root, record, _ = reviewed_competition
    registry = CompetitionRegistry({record["id"]: record})
    # The production book uses original bytes; review custody is evaluated in
    # the isolated submission fixture. No real review is added to the repository.
    actual_evaluate = registry.evaluate_record
    monkeypatch.setattr(registry, "evaluate_record", lambda root, rec: actual_evaluate(fixture_root, rec))
    monkeypatch.setattr(CompetitionRegistry, "from_repo", lambda _: registry)
    from rcwh.literary_eval import evaluate_literary_candidate
    from rcwh.regression import run_r4_evidence_regression
    monkeypatch.setattr("rcwh.competition.candidate_semantics", lambda *a: {"status": "PASS", "reports": []})
    monkeypatch.setattr("rcwh.competition.run_r4_evidence_regression", lambda _: run_r4_evidence_regression(ROOT))
    monkeypatch.setattr("rcwh.competition.evaluate_literary_candidate", lambda root, *a, **k: evaluate_literary_candidate(ROOT, *a, **k))
    promotions = PromotionRegistry.from_repo(ROOT)
    promotion_id = "promotion:ch86:b:v1-5-candidate"
    assert promotions.evaluate(ROOT, promotion_id)["overall"] == "PASS"
    winner = next(c for c in record["candidates"] if c["id"] == "ch86-B")
    winner["review_records"].pop()
    # A current winner claiming complete reviews is an inconsistency, not an
    # eligible candidate merely because its old WINNER flag is present.
    rejected = promotions.evaluate(ROOT, promotion_id)
    assert rejected["overall"] == "FAIL"
    assert rejected["gates"]["COMPETITION_ELIGIBILITY"] == "FAIL"


def test_anonymous_packet_cli_exports_bound_bytes_without_overwrite(reviewed_competition, monkeypatch, capsys):
    import json
    from rcwh.cli import main

    root, record, _ = reviewed_competition
    monkeypatch.setattr(CompetitionRegistry, "from_repo", lambda _: CompetitionRegistry({record["id"]: record}))
    target = root / "anonymous.json"
    monkeypatch.setattr("sys.argv", ["rcwh", "--root", str(root), "competition", record["id"], "--review-packet", str(target)])
    with pytest.raises(SystemExit) as exported:
        main()
    assert exported.value.code == 0
    binding = json.loads(capsys.readouterr().out)
    assert digest(target.read_bytes()) == binding["packet_sha256"]
    packet_text = target.read_text()
    assert "principal_id" not in packet_text
    assert "source_id" not in packet_text
    with pytest.raises(SystemExit) as refused:
        main()
    assert refused.value.code == 1
    assert json.loads(capsys.readouterr().out)["overall"] == "FAIL"
