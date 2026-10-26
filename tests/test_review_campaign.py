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
from rcwh.workflow.agent_panel import register, summary

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
    book = write("book.md", "current whole book" * 5)
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


def test_adjacent_chapter_context_is_counted_and_kept_with_each_whole_subject(work):
    request = json.loads((work.root / "request.json").read_bytes())
    packet = json.loads((work.root / "packet.json").read_bytes())
    adjacent = work.write("adjacent-chapter.txt", "adjacent" * 13)
    for subject in packet["subjects"]:
        if subject["scope"] == "CONTRACT":
            # The candidate is shared context; count it only once.
            subject["context"] = [work.candidate, adjacent]
    request["chapters"][0]["panel"]["packet"] = work.write("context-packet.json", packet)
    work.write("request.json", request)
    campaign.plan(work.root, "request.json", "context-campaign.json", max_read_bytes=500)
    plan = campaign._load(work.root, "context-campaign.json")
    chapters = [j for j in plan["jobs"] if j["kind"] == "CHAPTER"]
    assert all(j["reading_bytes"] <= 500 for j in chapters)
    assert Counter(s for j in chapters for s in j["subjects"]) == {
        "chapter-86": 2, "package-86": 2, "contract-86": 2, "contract-86-2": 2}
    for job in chapters:
        if any(s.startswith("contract-") for s in job["subjects"]):
            assert adjacent in job["read_in_full"]
        assert len({ref["path"] for ref in job["read_in_full"]}) == len(job["read_in_full"])


def test_single_subject_with_oversized_adjacent_context_is_refused(work):
    request = json.loads((work.root / "request.json").read_bytes())
    packet = json.loads((work.root / "packet.json").read_bytes())
    packet["subjects"][-1]["context"] = [work.write("huge-adjacent.txt", "x" * 500)]
    request["chapters"][0]["panel"]["packet"] = work.write("huge-context-packet.json", packet)
    work.write("request.json", request)
    with pytest.raises(ValueError, match="exceeds reading budget"):
        campaign.plan(work.root, "request.json", "huge-context-campaign.json", max_read_bytes=500)


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


def exported(work, **kwargs):
    result = campaign.dispatch(work.root, "campaign.json", **kwargs)
    return [(row, json.loads((work.root / row["assignment"]["path"]).read_bytes())) for row in result["assignments"]]


def test_exported_batch_respects_active_slots_and_resume_does_not_redispatch(work):
    batch = exported(work)
    assert len(batch) == 2
    assert exported(work) == []
    report = campaign.status(work.root, "campaign.json")
    assert sum(j["status"] == "ASSIGNED" for j in report["jobs"]) == 2
    row, assignment = batch[0]
    work.write("returned.json", json.loads(opinion(assignment)))
    campaign.submit(work.root, "campaign.json", row["job_id"], "returned.json", origin="synthetic agent environment")
    assert len(exported(work)) == 1
    assert summary(work.root)["review_count"] == 1


def test_direct_panel_registration_counts_and_campaign_runner_skips_it(work, monkeypatch):
    row, assignment = exported(work, limit=1)[0]
    work.write("returned.json", json.loads(opinion(assignment)))
    record = register(work.root, work.root / "returned.json", origin="direct agent-panel register")
    current = campaign.status(work.root, "campaign.json")
    job = next(j for j in current["jobs"] if j["id"] == row["job_id"])
    assert job["status"] == "COMPLETE" and job["record"] == record["record"]

    def worker(command, *, input, **kwargs):
        task = json.loads(input)
        assert task["job"]["id"] != row["job_id"]
        return SimpleNamespace(returncode=0, stdout=opinion(task), stderr=b"")
    monkeypatch.setattr(campaign.subprocess, "run", worker)
    assert campaign.run(work.root, "campaign.json", ["test-worker"])["status"] == "PASS"
    assert summary(work.root)["review_count"] == len(current["jobs"])


def test_direct_superseding_opinion_recovers_latest_record_without_losing_history(work):
    row, assignment = exported(work, limit=1)[0]
    first = json.loads(opinion(assignment))
    first["results"][0]["verdict"] = "NOT_CHECKED"
    work.write("first.json", first)
    original = register(work.root, work.root / "first.json", origin="synthetic incomplete reading")
    followup = json.loads(opinion(assignment))
    followup["supersedes"] = [original["record"]]
    work.write("followup.json", followup)
    latest = register(work.root, work.root / "followup.json", origin="synthetic actual followup")
    job = campaign.status(work.root, "campaign.json")["jobs"][0]
    assert job["status"] == "COMPLETE" and job["record"] == latest["record"]
    assert (work.root / original["record"]["path"]).exists()


@pytest.mark.parametrize("direct", [False, True])
def test_incomplete_reading_reopens_into_new_session_and_supersedes_original(work, monkeypatch, direct):
    row, assignment = exported(work, limit=1)[0]
    first = json.loads(opinion(assignment))
    first["results"][0]["verdict"] = "NOT_CHECKED"
    work.write("first.json", first)
    if direct:
        original = register(work.root, work.root / "first.json", origin="synthetic first")
    else:
        original = campaign.submit(work.root, "campaign.json", row["job_id"], "first.json", origin="synthetic first")
    assert campaign.reopen(work.root, "campaign.json", row["job_id"], reason="Actual assigned text was not read")["jobs"][0]["status"] == "PENDING"
    retry_row, retry = exported(work, limit=1)[0]
    assert retry_row["attempt"] == 2
    assert retry["opinion_scaffold"]["supersedes"] == [original["record"]]
    assert retry["opinion_scaffold"]["reviewer"]["session_id"] != first["reviewer"]["session_id"]
    work.write("followup.json", json.loads(opinion(retry)))
    campaign.submit(work.root, "campaign.json", row["job_id"], "followup.json", origin="synthetic completed followup")
    monkeypatch.setattr(campaign.subprocess, "run", lambda command, *, input, **k:
        SimpleNamespace(returncode=0, stdout=opinion(json.loads(input)), stderr=b""))
    assert campaign.run(work.root, "campaign.json", ["synthetic-worker"])["status"] == "PASS"
    assert summary(work.root)["status"] == "PASS"


def test_late_failure_cannot_fail_the_next_attempt_and_duplicates_are_idempotent(work, monkeypatch):
    now = [100.0]
    monkeypatch.setattr(campaign.time, "time", lambda: now[0])
    row, _ = exported(work, limit=1)[0]
    kwargs = {"assignment_sha256": row["assignment"]["sha256"], "reason": "Actual synthetic 503", "status_code": 503}
    campaign.fail(work.root, "campaign.json", row["job_id"], **kwargs)
    now[0] += 5
    retry, _ = exported(work, limit=1)[0]
    assert retry["attempt"] == 2
    report = campaign.fail(work.root, "campaign.json", row["job_id"], **kwargs)
    assert report["jobs"][0]["status"] == "ASSIGNED"
    with pytest.raises(ValueError, match="stale"):
        campaign.fail(work.root, "campaign.json", row["job_id"], **{**kwargs, "reason": "Different late failure"})
    assert campaign.status(work.root, "campaign.json")["jobs"][0]["status"] == "ASSIGNED"


def test_new_plan_reuses_complete_unchanged_readings(work, monkeypatch):
    monkeypatch.setattr(campaign.subprocess, "run", lambda command, *, input, **k:
        SimpleNamespace(returncode=0, stdout=opinion(json.loads(input)), stderr=b""))
    campaign.run(work.root, "campaign.json", ["synthetic-worker"])
    campaign.plan(work.root, "request.json", "different-plan.json", batch_size=3, max_read_bytes=400)
    report = campaign.status(work.root, "different-plan.json")
    assert report["status"] == "PASS" and all(j["reused"] for j in report["jobs"])
    assert campaign.dispatch(work.root, "different-plan.json")["assignments"] == []
    first = report["jobs"][0]
    campaign.reopen(work.root, "different-plan.json", first["id"], reason="New genuine reading requested")
    batch = campaign.dispatch(work.root, "different-plan.json", limit=1)
    assert [r["job_id"] for r in batch["assignments"]] == [first["id"]]
    task = json.loads((work.root / batch["assignments"][0]["assignment"]["path"]).read_bytes())
    assert task["opinion_scaffold"]["supersedes"] == [first["record"]]
    work.write("reused-followup.json", json.loads(opinion(task)))
    campaign.submit(work.root, "different-plan.json", first["id"], "reused-followup.json", origin="synthetic rereading")
    updated = campaign.status(work.root, "different-plan.json")
    assert updated["status"] == "PASS"
    assert updated["jobs"][0]["record"] != updated["jobs"][1]["record"]


def test_exported_empty_or_wrong_identity_opinion_cannot_complete_job(work):
    row, assignment = exported(work, limit=1)[0]
    work.write("empty.json", assignment["opinion_scaffold"])
    with pytest.raises(ValueError):
        campaign.submit(work.root, "campaign.json", row["job_id"], "empty.json", origin="unfilled")
    wrong = json.loads(opinion(assignment))
    wrong["reviewer"]["session_id"] = "somebody-else"
    work.write("wrong.json", wrong)
    with pytest.raises(ValueError, match="assigned"):
        campaign.submit(work.root, "campaign.json", row["job_id"], "wrong.json", origin="wrong reader")
    register(work.root, work.root / "wrong.json", origin="unrelated valid opinion")
    assert campaign.status(work.root, "campaign.json")["jobs"][0]["status"] == "ASSIGNED"


def test_direct_registration_with_missing_receipt_is_not_credited(work):
    row, assignment = exported(work, limit=1)[0]
    work.write("returned.json", json.loads(opinion(assignment)))
    record = register(work.root, work.root / "returned.json", origin="synthetic")
    (work.root / f"data/agent_panel/receipts/{record['record']['sha256']}.json").unlink()
    with pytest.raises(OSError):
        campaign.status(work.root, "campaign.json")


def test_manual_503_retries_wait_and_exhaust_without_counting_opinions(work, monkeypatch):
    now = [100.0]
    monkeypatch.setattr(campaign.time, "time", lambda: now[0])
    row, first = exported(work, limit=1)[0]
    for attempt in range(1, 4):
        report = campaign.fail(work.root, "campaign.json", row["job_id"], assignment_sha256=row["assignment"]["sha256"], reason="actual synthetic 503", status_code=503)
        state = next(j for j in report["jobs"] if j["id"] == row["job_id"])
        assert state["attempts"] == attempt
        assert state["status"] == ("RETRY_WAIT" if attempt < 3 else "EXHAUSTED")
        if attempt < 3:
            # Leave no room for unrelated tasks while checking the retry delay.
            assert row["job_id"] not in [r["job_id"] for r, _ in exported(work, limit=1)]
            now[0] += 5 * 2 ** (attempt - 1)
            # The other available slot may already be occupied.
            batch = exported(work)
            retry_row, retry = next((r, a) for r, a in batch if r["job_id"] == row["job_id"])
            row = retry_row
            assert retry_row["attempt"] == attempt + 1
            assert retry["opinion_scaffold"]["reviewer"]["session_id"] != first["opinion_scaffold"]["reviewer"]["session_id"]
    assert summary(work.root)["review_count"] == 0


def test_runner_refuses_to_duplicate_active_exported_work(work, monkeypatch):
    exported(work, limit=1)
    monkeypatch.setattr(campaign.subprocess, "run", lambda *a, **k: pytest.fail("duplicate dispatch"))
    with pytest.raises(ValueError, match="active"):
        campaign.run(work.root, "campaign.json", ["test-worker"])


def test_oversized_legacy_book_cannot_be_dispatched(work):
    work.write("book.md", "oversized" * 100)
    packet = json.loads((work.root / "book-packet.json").read_bytes())
    packet["subjects"][0]["binding"] = work.write("book.md", "oversized" * 100)
    ref = work.write("book-packet.json", packet)
    request = json.loads((work.root / "request.json").read_bytes())
    request["book_review"]["packet"] = ref
    work.write("request.json", request)
    with pytest.raises(ValueError, match="exceeds reading budget"):
        campaign.plan(work.root, "request.json", "new-campaign.json", max_read_bytes=400)


def test_agent_environment_cli_dispatch_register_and_status(work, monkeypatch, capsys):
    import sys
    from rcwh.cli import main

    def invoke(*args):
        monkeypatch.setattr(sys, "argv", ["rcwh", "--root", str(work.root), *args])
        with pytest.raises(SystemExit) as stop:
            main()
        return stop.value.code, json.loads(capsys.readouterr().out)

    code, batch = invoke("agent-release", "review-dispatch", "campaign.json", "--limit", "1")
    assert code == 0 and len(batch["assignments"]) == 1
    row = batch["assignments"][0]
    assignment = json.loads((work.root / row["assignment"]["path"]).read_bytes())
    work.write("returned.json", json.loads(opinion(assignment)))
    code, registration = invoke("agent-release", "review-register", "campaign.json", row["job_id"],
                                "--opinion", "returned.json", "--origin", "synthetic environment reader")
    assert code == 0 and registration["record"]
    code, progress = invoke("agent-release", "review-status", "campaign.json")
    assert code == 2 and progress["jobs"][0]["status"] == "COMPLETE"


def test_exported_permanent_failure_is_terminal_and_real_interruption_can_retry(work, monkeypatch):
    now = [100.0]
    monkeypatch.setattr(campaign.time, "time", lambda: now[0])
    batch = exported(work)
    campaign.fail(work.root, "campaign.json", batch[0][0]["job_id"], assignment_sha256=batch[0][0]["assignment"]["sha256"], reason="synthetic permanent error", status_code=401)
    report = campaign.fail(work.root, "campaign.json", batch[1][0]["job_id"], assignment_sha256=batch[1][0]["assignment"]["sha256"], reason="synthetic actual interruption", interrupted=True)
    assert [j["status"] for j in report["jobs"][:2]] == ["FAILED", "RETRY_WAIT"]
    now[0] += 5
    retried = [r["job_id"] for r, _ in exported(work)]
    assert batch[0][0]["job_id"] not in retried and batch[1][0]["job_id"] in retried


def test_corrected_permanent_failure_can_be_explicitly_reopened(work):
    row, _ = exported(work, limit=1)[0]
    campaign.fail(work.root, "campaign.json", row["job_id"], assignment_sha256=row["assignment"]["sha256"],
                  reason="Actual synthetic configuration failure", status_code=401)
    campaign.reopen(work.root, "campaign.json", row["job_id"], reason="Worker configuration was corrected")
    next_row, task = exported(work, limit=1)[0]
    assert next_row["attempt"] == 2 and "supersedes" not in task["opinion_scaffold"]


def test_reopened_runner_has_its_own_bounded_transport_budget_and_backoff(work, monkeypatch):
    monkeypatch.setattr(campaign.subprocess, "run", lambda command, *, input, **k:
        SimpleNamespace(returncode=0, stdout=opinion(json.loads(input)), stderr=b""))
    report = campaign.run(work.root, "campaign.json", ["synthetic-worker"])
    job = report["jobs"][0]["id"]
    campaign.reopen(work.root, "campaign.json", job, reason="New genuine reading after prior completion")
    calls, delays = [], []
    def worker(command, *, input, **kwargs):
        task = json.loads(input)
        assert task["job"]["id"] == job
        calls.append(task)
        if len(calls) < 3:
            return SimpleNamespace(returncode=75, stdout=b"", stderr=b"actual synthetic temporary failure")
        return SimpleNamespace(returncode=0, stdout=opinion(task), stderr=b"")
    monkeypatch.setattr(campaign.subprocess, "run", worker)
    monkeypatch.setattr(campaign.time, "sleep", delays.append)
    assert campaign.run(work.root, "campaign.json", ["synthetic-worker"])["status"] == "PASS"
    assert len(calls) == 3 and delays == [5, 10]


def test_registered_original_bytes_are_checked_on_external_progress_recovery(work):
    row, assignment = exported(work, limit=1)[0]
    work.write("returned.json", json.loads(opinion(assignment)))
    record = register(work.root, work.root / "returned.json", origin="synthetic")
    (work.root / record["raw_output"]["path"]).write_text("changed")
    with pytest.raises(ValueError):
        campaign.status(work.root, "campaign.json")
