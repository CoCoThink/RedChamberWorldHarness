"""Bounded dispatch, byte binding and transport retries with actual registration."""
from collections import Counter
import json
from pathlib import Path
import shutil
from types import SimpleNamespace
import threading
import time

import pytest

from rcwh.candidate_reviews import canonical_bytes, digest
from rcwh.workflow import review_campaign as campaign
from rcwh.workflow.agent_panel import summary

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def work(tmp_path, monkeypatch):
    shutil.copytree(ROOT / "schemas", tmp_path / "schemas")

    def write(name, value):
        raw = value.encode() if isinstance(value, str) else canonical_bytes(value)
        file = tmp_path / name
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(raw)
        return {"path": name, "sha256": digest(raw)}
    candidate = write("candidate.txt", "candidate" * 15)
    package = write("package.json", {"chapter": 86})
    contract = write("contract.json", {"chapter": 86, "text": "contract" * 20})
    second_contract = write("contract2.json", {"chapter": 86, "text": "second-contract" * 12})
    book = write("book.md", "current whole book" * 50)
    subjects = [{"id": "chapter-86", "scope": "CANDIDATE", "binding": candidate},
                {"id": "package-86", "scope": "PACKAGE", "binding": package},
                {"id": "contract-86", "scope": "CONTRACT", "binding": contract},
                {"id": "contract-86-2", "scope": "CONTRACT", "binding": second_contract}]

    def packet(name, rows):
        return write(name, {"schema_version": 1, "packet_kind": "AGENT_REVIEW_PACKET", "id": name,
            "coordinator_session_id": "coordinator", "subjects": rows, "authority_effect": "NONE", "usage": "RESEARCH_ONLY"})
    packet_ref = packet("packet.json", subjects)
    book_ref = packet("book-packet.json", [{"id": "book", "scope": "BOOK", "binding": book, "review_policy": "ADVISORY"}])
    request = {"chapters": [{"chapter": 86, "mode": "AGENT_CANDIDATE", "writing_package": package, "candidate": candidate,
                "panel": {"packet": packet_ref, "subject_id": "chapter-86"}}],
               "book_review": {"packet": book_ref, "subject_id": "book"}}
    write("request.json", request)
    monkeypatch.setattr("rcwh.workflow.admission.chapter_scope", lambda *a, **k: {"paths": [contract["path"], second_contract["path"]]})
    campaign.plan(tmp_path, "request.json", "campaign.json", batch_size=2, max_read_bytes=400)
    return SimpleNamespace(root=tmp_path, write=write, candidate=candidate)


def opinion(assignment):
    value = assignment["opinion_scaffold"]
    for row in value["results"]:
        row.update(verdict="PASS", notes="Synthetic test reading, never a real chapter opinion")
    return canonical_bytes(value)


def test_large_chapter_is_partitioned_with_two_readers_for_each_subject(work):
    value = json.loads((work.root / "campaign.json").read_bytes())
    jobs = value["jobs"]
    assert Counter(s for j in jobs for s in j["subjects"]) == {
        "chapter-86": 2, "package-86": 2, "contract-86": 2, "contract-86-2": 2, "book": 2}
    assert len([j for j in jobs if j["kind"] == "CHAPTER"]) == 4
    assert all(j["reading_bytes"] <= 400 for j in jobs if j["kind"] == "CHAPTER")
    assert all(work.candidate in j["read_in_full"] for j in jobs if j["kind"] == "CHAPTER")
    assert len([j for j in jobs if j["kind"] == "BOOK"]) == 2
    assert all(j["gate_effect"] == "NONE" for j in jobs if j["kind"] == "BOOK")


def test_503_is_retried_concurrency_is_bounded_and_resume_does_not_duplicate(work, monkeypatch):
    calls = Counter()
    lock = threading.Lock()
    active, maximum = 0, 0

    def worker(command, *, input, **kwargs):
        nonlocal active, maximum
        assignment = json.loads(input)
        identity = assignment["job"]["id"]
        with lock:
            active += 1; maximum = max(maximum, active); calls[identity] += 1
            attempt = calls[identity]
        time.sleep(.01)
        with lock:
            active -= 1
        if attempt == 1:
            return SimpleNamespace(returncode=1, stdout=b"", stderr=b'{"status_code":503}')
        return SimpleNamespace(returncode=0, stdout=opinion(assignment), stderr=b"")
    monkeypatch.setattr(campaign.subprocess, "run", worker)
    report = campaign.run(work.root, "campaign.json", ["test-worker"], backoff_seconds=0)
    assert report["status"] == "PASS" and maximum <= 2
    assert set(calls.values()) == {2}
    assert all(j["attempts"] == 2 for j in report["jobs"])
    review_count = summary(work.root)["review_count"]
    assert review_count == len(report["jobs"])
    assert campaign.run(work.root, "campaign.json", ["test-worker"])["status"] == "PASS"
    assert set(calls.values()) == {2} and summary(work.root)["review_count"] == review_count


def test_unfilled_scaffold_is_never_registered_or_automatically_retried(work, monkeypatch):
    calls = []

    def worker(command, *, input, **kwargs):
        calls.append(True)
        return SimpleNamespace(returncode=0, stdout=canonical_bytes(json.loads(input)["opinion_scaffold"]), stderr=b"")
    monkeypatch.setattr(campaign.subprocess, "run", worker)
    report = campaign.run(work.root, "campaign.json", ["test-worker"], backoff_seconds=0)
    assert report["status"] == "FAIL"
    assert all(j["attempts"] == 1 and j["status"] == "FAILED" for j in report["jobs"])
    assert summary(work.root)["review_count"] == 0
    campaign.run(work.root, "campaign.json", ["test-worker"])
    assert len(calls) == len(report["jobs"])


def test_request_changes_stop_resume_before_worker_is_called(work, monkeypatch):
    (work.root / "request.json").write_text("{}")
    monkeypatch.setattr(campaign.subprocess, "run", lambda *a, **k: pytest.fail("stale request dispatched"))
    with pytest.raises(ValueError, match="stale"):
        campaign.run(work.root, "campaign.json", ["test-worker"])


def test_coordinator_decision_does_not_invalidate_review_dispatch_or_frozen_request(work):
    original = (work.root / "request.json").read_bytes()
    request = json.loads(original)
    request["chapters"][0]["decision"] = {"path": "future-decision.json", "sha256": "0" * 64}
    (work.root / "request.json").write_bytes(canonical_bytes(request))
    document = campaign._load(work.root, "campaign.json")
    assert (work.root / document["request"]["path"]).read_bytes() == original
    assert campaign.status(work.root, "campaign.json")["status"] == "PENDING"


def test_retry_budget_exhausts_without_creating_a_review(work, monkeypatch):
    monkeypatch.setattr(campaign.subprocess, "run", lambda *a, **k: SimpleNamespace(returncode=75, stdout=b"", stderr=b"temporary failure"))
    report = campaign.run(work.root, "campaign.json", ["test-worker"], backoff_seconds=0)
    assert report["status"] == "FAIL"
    assert all(j["status"] == "EXHAUSTED" and j["attempts"] == 3 for j in report["jobs"])
    assert summary(work.root)["review_count"] == 0


def test_interrupted_runner_after_registration_recovers_without_duplicate_opinions(work, monkeypatch):
    monkeypatch.setattr(campaign.subprocess, "run", lambda command, *, input, **k:
        SimpleNamespace(returncode=0, stdout=opinion(json.loads(input)), stderr=b""))
    report = campaign.run(work.root, "campaign.json", ["test-worker"])
    for job in report["jobs"]:
        (work.root / report["attempt_directory"] / job["id"] / "attempt-1.json").unlink()
    monkeypatch.setattr(campaign.subprocess, "run", lambda *a, **k: pytest.fail("committed opinion rerun"))
    assert campaign.run(work.root, "campaign.json", ["test-worker"])["status"] == "PASS"
    assert summary(work.root)["review_count"] == len(report["jobs"])


def test_timeout_retries_without_registering_partial_output(work, monkeypatch):
    def worker(*a, **k):
        raise campaign.subprocess.TimeoutExpired("test-worker", 1, output=b"partial")
    monkeypatch.setattr(campaign.subprocess, "run", worker)
    report = campaign.run(work.root, "campaign.json", ["test-worker"], backoff_seconds=0)
    assert all(j["status"] == "EXHAUSTED" for j in report["jobs"])
    assert summary(work.root)["review_count"] == 0
