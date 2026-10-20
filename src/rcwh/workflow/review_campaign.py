"""Bounded, resumable review work. Workers produce actual opinions, never scores.

A local worker accepts a JSON assignment on stdin, reads its bound files, and
returns an AGENT_REVIEW_OPINION on stdout. No shell interpolation is used.
Transport retries do not create or count opinions; registration is serialized.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter
import json
from pathlib import Path
import re
import subprocess
import threading
import time

from ..assets import AssetError
from ..assets.paths import repository_path
from ..candidate_reviews import canonical_bytes, digest
from ..generation.records import bound_bytes
from ..schema import validate_instance
from .agent_panel import _sample_records, _verify_opinion, register, scaffold, verify_packet
from .release_packets import _binding, _write_immutable

TEMPORARY = {429, 500, 502, 503, 504}
DEFAULT_LIMIT = 197 * 1024


def _review_basis(request: dict) -> str:
    # Coordinator decisions consume reviews; they are not reviewer inputs.
    value = {**request, "chapters": [{k: v for k, v in row.items() if k != "decision"}
                                    for row in request["chapters"]]}
    return digest(canonical_bytes(value))


def _current_request(root: Path, document: dict) -> None:
    try:
        current = json.loads(repository_path(root, document["current_request_path"]).read_bytes())
        basis = _review_basis(current)
    except (KeyError, TypeError, ValueError) as exc:
        raise AssetError("stale review campaign: invalid current request") from exc
    if basis != document["review_basis_sha256"]:
        raise AssetError("stale review campaign: current review inputs changed")


def plan(root: Path, request_path: str, output: str, *, batch_size: int = 5,
         max_read_bytes: int = DEFAULT_LIMIT, max_attempts: int = 3) -> dict:
    if not 1 <= batch_size <= 6 or max_read_bytes < 1 or not 1 <= max_attempts <= 5:
        raise AssetError("review limits: batch size 1..6, positive byte budget, attempts 1..5")
    root = Path(root).resolve()
    request_binding = _binding(root, request_path)
    request = json.loads(bound_bytes(root, request_binding))
    request_snapshot = (Path(output).parent / "review-requests" / f"{digest(canonical_bytes(request))}.json").as_posix()
    request_binding = _write_immutable(root, request_snapshot, request)
    jobs, packets, carriers = [], {}, {}

    def packet(ref):
        key = (ref["path"], ref["sha256"])
        if key not in packets:
            packets[key] = verify_packet(root, ref)
        return packets[key]

    def add(kind, ref, subjects, chapter=None, context=()):
        document = packet(ref)
        index = {s["id"]: s for s in document["subjects"]}
        files = {index[s]["binding"]["path"]: index[s]["binding"] for s in subjects}
        files.update({b["path"]: b for b in context})
        samples = [{"subject_id": s, **sample} for s in subjects for sample in index[s].get("samples", [])]
        for sample in samples:
            carrier_key = (sample["binding"]["path"], sample["binding"]["sha256"])
            if carrier_key not in carriers:
                carriers[carrier_key] = _sample_records(root, sample["binding"])
            records = carriers[carrier_key]
            if records is None:
                files[sample["binding"]["path"]] = sample["binding"]
            else:
                selected = [r for r in records if sample["id"] in (r.get("id"), r.get("segment_id"))]
                projection = {"sample_id": sample["id"], "carrier": sample["binding"], "records": selected}
                relative = (Path(output).parent / "review-samples" / f"{digest(canonical_bytes(projection))}.json").as_posix()
                sample["reading"] = _write_immutable(root, relative, projection)
                files[relative] = sample["reading"]
        size = sum(len(bound_bytes(root, b)) for b in files.values())
        for reader in (1, 2):
            identity = f"{kind}-{chapter if chapter is not None else 'shared'}-{len(jobs):03d}-r{reader}"
            jobs.append({"id": identity, "kind": kind, "chapter": chapter, "packet": ref,
                         "subjects": subjects, "read_in_full": list(files.values()), "samples": samples,
                         "reading_bytes": size, "exceeds_budget": size > max_read_bytes,
                         "severity": "ADVISORY" if kind == "BOOK" else "EVIDENCE_FLOOR",
                         "gate_effect": "NONE" if kind == "BOOK" else "EXISTING_PEER_GATES"})

    shared = {}
    for row in request["chapters"]:
        if row["mode"] != "AGENT_CANDIDATE":
            continue
        ref = row["panel"]["packet"]
        document = packet(ref)
        package = row["writing_package"]
        # Release evaluation is the authority for the exact required contracts.
        from .admission import chapter_scope
        scope = chapter_scope(root, package["path"], plan_contracts=True)
        paths = set(scope["paths"])
        subjects = [s for s in document["subjects"] if
                    s["id"] == row["panel"]["subject_id"] or
                    (s["scope"] == "PACKAGE" and s["binding"] == package) or
                    (s["scope"] == "CONTRACT" and s["binding"]["path"] in paths)]
        # Split by whole review subject: never count a partial contract as read.
        groups, current, size = [], [], 0
        context = [row["candidate"], package]
        if "policy" in row:
            context.append(row["policy"])
        context_paths = {b["path"] for b in context}
        context_size = sum(len(bound_bytes(root, b)) for b in context)
        size = context_size
        for subject in subjects:
            count = 0 if subject["binding"]["path"] in context_paths else len(bound_bytes(root, subject["binding"]))
            if current and size + count > max_read_bytes:
                groups.append(current); current, size = [], context_size
            current.append(subject["id"]); size += count
        if current:
            groups.append(current)
        for group in groups:
            add("CHAPTER", ref, group, row["chapter"], context)
        for key in ("source_reviews", "corpus_reviews"):
            for review in row.get(key, []):
                identity = (review["packet"]["path"], review["packet"]["sha256"])
                shared.setdefault(identity, set()).add(review["subject_id"])
    for (path, sha), subjects in sorted(shared.items()):
        ref = {"path": path, "sha256": sha}
        kind = "CORPUS" if all(s["scope"] == "CORPUS" for s in packet(ref)["subjects"]) else "SOURCE"
        add(kind, ref, sorted(subjects))
    if "book_review" in request:
        from .book_review import subjects as book_subjects
        ref = request["book_review"]
        for subject in book_subjects(root, ref, chapters=[r["chapter"] for r in request["chapters"]]):
            add("BOOK", ref["packet"], [subject["id"]])
            if "chapters" in subject:
                for job in jobs[-2:]:
                    job["continuity"] = {"chapters": subject["chapters"],
                        "seams": [list(pair) for pair in zip(subject["chapters"], subject["chapters"][1:])]}
    if any(j["exceeds_budget"] for j in jobs):
        raise AssetError("review material exceeds reading budget; split complete subjects/continuity segments before dispatch")
    document = {"schema_version": 1, "kind": "AGENT_REVIEW_CAMPAIGN", "request": request_binding,
                "current_request_path": request_path, "review_basis_sha256": _review_basis(request),
                "batch_size": batch_size, "max_attempts": max_attempts, "max_read_bytes": max_read_bytes,
                "jobs": jobs, "authority_effect": "NONE", "usage": "RESEARCH_ONLY"}
    binding = _write_immutable(root, output, document)
    return {"status": "PASS", "plan": binding, "jobs": len(jobs), "batch_size": batch_size,
            "oversized_jobs": [j["id"] for j in jobs if j["exceeds_budget"]]}


def _load(root: Path, path: str) -> dict:
    value = json.loads(repository_path(root, path).read_bytes())
    errors = validate_instance(value, root / "schemas/review_campaign.schema.json")
    if errors:
        raise AssetError("invalid review campaign: " + "; ".join(errors))
    if value.get("kind") != "AGENT_REVIEW_CAMPAIGN" or value.get("schema_version") != 1:
        raise AssetError("invalid review campaign")
    if not 1 <= value["batch_size"] <= 6 or not 1 <= value["max_attempts"] <= 5:
        raise AssetError("invalid campaign execution limits")
    bound_bytes(root, value["request"])
    request = json.loads(bound_bytes(root, value["request"]))
    if _review_basis(request) != value["review_basis_sha256"]:
        raise AssetError("campaign frozen request/basis mismatch")
    _current_request(root, value)
    ids = [j["id"] for j in value["jobs"]]
    if not ids or len(set(ids)) != len(ids):
        raise AssetError("empty or duplicate campaign jobs")
    carriers, verified = {}, {}
    for job in value["jobs"]:
        if not job["id"].replace("-", "").isalnum():
            raise AssetError("invalid campaign job id")
        key = (job["packet"]["path"], job["packet"]["sha256"])
        if key not in verified:
            verified[key] = verify_packet(root, job["packet"])
        packet = verified[key]
        if not set(job["subjects"]) <= {s["id"] for s in packet["subjects"]}:
            raise AssetError("campaign subjects absent from packet")
        for ref in job["read_in_full"]:
            bound_bytes(root, ref)
        size = sum(len(bound_bytes(root, b)) for b in job["read_in_full"])
        if (job["reading_bytes"] != size or job["exceeds_budget"] != (size > value["max_read_bytes"])
                or size > value["max_read_bytes"]):
            raise AssetError("campaign reading budget exceeded or misreported; re-plan with bounded segments")
        if any(s["binding"] not in job["read_in_full"] for s in packet["subjects"] if s["id"] in job["subjects"]):
            raise AssetError("campaign omits assigned subject bytes")
        for sample in job["samples"]:
            if "reading" in sample:
                projection = json.loads(bound_bytes(root, sample["reading"]))
                key = (sample["binding"]["path"], sample["binding"]["sha256"])
                if key not in carriers:
                    carriers[key] = _sample_records(root, sample["binding"])
                selected = [r for r in carriers[key]
                            if sample["id"] in (r.get("id"), r.get("segment_id"))]
                if projection != {"sample_id": sample["id"], "carrier": sample["binding"], "records": selected}:
                    raise AssetError("campaign sample projection differs from carrier")
    if "book_review" in request:
        from .book_review import subjects as book_subjects
        ref = request["book_review"]
        segments = book_subjects(root, ref, chapters=[r["chapter"] for r in request["chapters"]])
        coverage = Counter(s for j in value["jobs"] if j["kind"] == "BOOK" for s in j["subjects"])
        if coverage != Counter({s["id"]: 2 for s in segments}):
            raise AssetError("campaign must assign two readers to every continuity segment")
        for job in (j for j in value["jobs"] if j["kind"] == "BOOK"):
            segment = next(s for s in segments if s["id"] == job["subjects"][0])
            if job["packet"] != ref["packet"] or len(job["subjects"]) != 1 or job["gate_effect"] != "NONE" or job["severity"] != "ADVISORY":
                raise AssetError("invalid continuity assignment")
            if "chapters" in segment and job.get("continuity") != {"chapters": segment["chapters"],
                    "seams": [list(pair) for pair in zip(segment["chapters"], segment["chapters"][1:])]}:
                raise AssetError("continuity assignment chapters/seams differ from packet")
    return value


def _matches(assignment: dict, opinion: dict) -> bool:
    return (opinion["reviewer"] == assignment["opinion_scaffold"]["reviewer"]
            and opinion["packet"] == assignment["job"]["packet"]
            and {r["subject_id"] for r in opinion["results"]} == set(assignment["job"]["subjects"]))


def _assignment(root: Path, document: dict, job: dict, attempt: int, model_label: str, mode: str) -> dict:
    sha = digest(canonical_bytes(document))
    skeleton = scaffold(root, job["packet"]["path"], reviewer_id=f"{sha[:12]}:{job['id']}",
                        session_id=f"review:{sha[:12]}:{job['id']}:{attempt}",
                        subjects=job["subjects"], model_label=model_label)
    return {"job": job, "execution_mode": mode, "opinion_scaffold": skeleton,
            "instructions": (
                "Read the assigned continuity segment in full and in order, including both chapters of every listed seam. Examine chronology, object custody, forms of address, character knowledge and unresolved callbacks. Cite chapters and exact passages for each problem. Every finding is ADVISORY. "
                if job["kind"] == "BOOK" else
                "Read the assigned bytes and all listed samples. Compare contracts with the attached candidate and package. Use BLOCKING for byte/integrity failures or A-W1-backed LOCKED violations; plan-card beats, P-Lock anchors and taste objections are ADVISORY under ADR 0004. "
            ) + "Read only the assigned subjects, not all subjects in the shared packet. Fill every verdict and notes, and all sample checks. If context or reading is incomplete, report NOT_CHECKED with the unread scope; never PASS. Return only the opinion JSON. Preserve assigned identity and bindings. Do not register or edit repository files yourself."}


def _events(root: Path, directory: str, job: dict) -> list[dict]:
    base = repository_path(root, f"{directory}/{job['id']}")
    events = []
    for assignment_file in sorted(base.glob("attempt-*-assignment.json")) if base.exists() else []:
        match = re.fullmatch(r"attempt-(\d+)-assignment\.json", assignment_file.name)
        if match is None:
            continue
        number = int(match[1])
        assignment_ref = _binding(root, assignment_file.relative_to(root).as_posix())
        assignment = json.loads(bound_bytes(root, assignment_ref))
        if number != len(events) + 1 or assignment["job"] != job:
            raise AssetError("campaign attempt sequence/assignment mismatch")
        file = base / f"attempt-{number}.json"
        if not file.exists():
            manual = assignment.get("execution_mode") == "AGENT_ENVIRONMENT"
            event = {"attempt": number, "status": "ASSIGNED" if manual else "INTERRUPTED", "retryable": not manual,
                     "assignment": assignment_ref, "record": None}
            # Also reconcile direct `agent-panel register` after an exported
            # assignment. A matching packet alone never credits campaign work.
            matches = []
            for registered in repository_path(root, "data/agent_panel/records").glob("*.json"):
                record = json.loads(registered.read_bytes())
                if _matches(assignment, record["opinion"]):
                    matches.append((registered, record))
            if len(matches) > 1:
                raise AssetError("multiple registered opinions for one campaign attempt")
            if matches:
                registered, record = matches[0]
                event.update(status="REGISTERED", retryable=False,
                    record=_binding(root, registered.relative_to(root).as_posix()), stdout=record["raw_output"])
        else:
            event = json.loads(file.read_bytes())
            if event["attempt"] != number or event["assignment"] != assignment_ref or (event["status"] == "REGISTERED") != bool(event["record"]):
                raise AssetError("campaign event/registration mismatch")
        for key in ("assignment", "stdout", "stderr"):
            if key in event:
                bound_bytes(root, event[key])
        if event.get("record"):
            record = json.loads(bound_bytes(root, event["record"]))
            opinion = json.loads(bound_bytes(root, event["stdout"]))
            _verify_opinion(root, opinion)
            receipt = repository_path(root, f"data/agent_panel/receipts/{event['record']['sha256']}.json")
            if (record["opinion"] != opinion or record["raw_output"]["sha256"] != event["stdout"]["sha256"]
                    or json.loads(receipt.read_bytes())["record"] != event["record"]
                    or not _matches(assignment, opinion)):
                raise AssetError("campaign registration differs from assigned work")
        events.append(event)
    return events


def _state(events: list[dict], maximum: int) -> str:
    if events and events[-1]["status"] == "REGISTERED":
        return "COMPLETE"
    if events and events[-1]["status"] == "ASSIGNED":
        return "ASSIGNED"
    if events and not events[-1]["retryable"]:
        return "FAILED"
    if len(events) >= maximum:
        return "EXHAUSTED"
    if events and events[-1].get("retry_after", 0) > time.time():
        return "RETRY_WAIT"
    return "PENDING"


def status(root: Path, path: str) -> dict:
    root = Path(root).resolve()
    document = _load(root, path)
    directory = f"data/agent_release/review-attempts/{digest(canonical_bytes(document))}"
    rows = []
    for job in document["jobs"]:
        events = _events(root, directory, job)
        rows.append({"id": job["id"], "status": _state(events, document["max_attempts"]), "attempts": len(events),
                     "assignment": events[-1]["assignment"] if events else None,
                     "record": events[-1]["record"] if events else None,
                     "retry_after": events[-1].get("retry_after") if events else None})
    return {"status": "PASS" if all(r["status"] == "COMPLETE" for r in rows) else
            "FAIL" if any(r["status"] in {"FAILED", "EXHAUSTED"} for r in rows) else "PENDING",
            "scope": "REVIEW_EXECUTION_ONLY", "jobs": rows, "attempt_directory": directory,
            "authority_effect": "NONE"}


def dispatch(root: Path, path: str, *, limit: int | None = None,
             model_label: str = "agent environment reader (declared)") -> dict:
    """Reserve a bounded batch for the parent agent; no provider or adapter."""
    from .review_intake import _intake_lock
    root = Path(root).resolve()
    with _intake_lock(root):
        document = _load(root, path)
        maximum = document["batch_size"]
        if limit is not None and not 1 <= limit <= maximum:
            raise AssetError("dispatch limit must be between 1 and campaign batch size")
        directory = f"data/agent_release/review-attempts/{digest(canonical_bytes(document))}"
        events = {j["id"]: _events(root, directory, j) for j in document["jobs"]}
        states = {key: _state(value, document["max_attempts"]) for key, value in events.items()}
        active = sum(state == "ASSIGNED" for state in states.values())
        slots = max(0, (limit if limit is not None else maximum) - active)
        assignments = []
        for job in document["jobs"]:
            if len(assignments) >= slots:
                break
            if states[job["id"]] != "PENDING":
                continue
            number = len(events[job["id"]]) + 1
            assignment = _assignment(root, document, job, number, model_label, "AGENT_ENVIRONMENT")
            binding = _write_immutable(root, f"{directory}/{job['id']}/attempt-{number}-assignment.json", assignment)
            assignments.append({"job_id": job["id"], "attempt": number, "assignment": binding})
    return {"status": "PASS", "scope": "REVIEW_DISPATCH_ONLY", "assignments": assignments,
            "active_assignments": active + len(assignments), "batch_size": maximum, "authority_effect": "NONE"}


def _active(root: Path, path: str, job_id: str) -> tuple[dict, str, dict, list[dict]]:
    document = _load(root, path)
    job = next((j for j in document["jobs"] if j["id"] == job_id), None)
    if job is None:
        raise AssetError("unknown campaign job")
    directory = f"data/agent_release/review-attempts/{digest(canonical_bytes(document))}"
    events = _events(root, directory, job)
    if _state(events, document["max_attempts"]) != "ASSIGNED":
        raise AssetError("job has no active exported assignment")
    return document, directory, job, events


def submit(root: Path, path: str, job_id: str, opinion_path: str, *, origin: str) -> dict:
    """Validate the returned original opinion and register it serially."""
    from .review_intake import _intake_lock
    root = Path(root).resolve()
    with _intake_lock(root):
        _, directory, _, events = _active(root, path, job_id)
        last = events[-1]
        assignment = json.loads(bound_bytes(root, last["assignment"]))
        file = Path(opinion_path)
        file = file if file.is_absolute() else repository_path(root, opinion_path)
        raw = file.read_bytes()
        opinion = json.loads(raw)
        _verify_opinion(root, opinion)
        if not _matches(assignment, opinion):
            raise AssetError("opinion differs from assigned reviewer, packet or subjects")
        base = f"{directory}/{job_id}/attempt-{len(events)}"
        stdout = _write_immutable(root, base + "-stdout.json", raw)
        record = register(root, repository_path(root, stdout["path"]), origin=origin)["record"]
        _write_immutable(root, base + ".json", {**last, "status": "REGISTERED", "retryable": False,
                                              "stdout": stdout, "record": record})
    return {"status": "PASS", "scope": "REVIEW_REGISTRATION_ONLY", "job_id": job_id,
            "record": record, "authority_effect": "NONE"}


def fail(root: Path, path: str, job_id: str, *, reason: str, status_code: int | None = None,
         interrupted: bool = False) -> dict:
    """Record an actual launch/transport failure before a bounded redispatch."""
    from .review_intake import _intake_lock
    root = Path(root).resolve()
    if not reason.strip():
        raise AssetError("failure reason required")
    with _intake_lock(root):
        _, directory, _, events = _active(root, path, job_id)
        last = events[-1]
        base = f"{directory}/{job_id}/attempt-{len(events)}"
        stderr = _write_immutable(root, base + "-stderr.txt", reason.encode())
        retryable = interrupted or status_code in TEMPORARY
        delay = min(30, 5 * 2 ** (len(events) - 1)) if retryable else 0
        _write_immutable(root, base + ".json", {**last, "status": "FAILED", "retryable": retryable,
            "status_code": status_code, "stderr": stderr, "error": reason,
            "retry_after": time.time() + delay})
    return status(root, path)


def run(root: Path, path: str, worker: list[str], *, timeout: float = 600,
        model_label: str = "local worker (declared)", backoff_seconds: float = 5) -> dict:
    if not worker or not 0 < timeout <= 3600 or not 0 <= backoff_seconds <= 30:
        raise AssetError("worker command and a timeout of at most 3600 seconds required")
    root = Path(root).resolve()
    document = _load(root, path)
    campaign_sha = digest(canonical_bytes(document))
    directory = f"data/agent_release/review-attempts/{campaign_sha}"
    registration_lock = threading.Lock()

    def execute(job):
        events = _events(root, directory, job)
        if events and events[-1]["status"] == "REGISTERED":
            return
        # A terminal worker/validation failure requires a new campaign, not
        # automatically spending the remaining transport retry budget.
        if events and not events[-1]["retryable"]:
            return
        for attempt in range(len(events) + 1, document["max_attempts"] + 1):
            _current_request(root, document)
            base = f"{directory}/{job['id']}/attempt-{attempt}"
            if events and events[-1].get("retry_after", 0) > time.time():
                time.sleep(min(30, events[-1]["retry_after"] - time.time()))
            assignment = _assignment(root, document, job, attempt, model_label, "SUBPROCESS")
            skeleton = assignment["opinion_scaffold"]
            assignment_ref = _write_immutable(root, base + "-assignment.json", assignment)
            started = time.monotonic()
            retryable, code = False, None
            try:
                result = subprocess.run(worker, input=canonical_bytes(assignment), cwd=root,
                                        capture_output=True, timeout=timeout, check=False)
                stdout, stderr, code = result.stdout, result.stderr, result.returncode
                if code:
                    try:
                        retryable = code == 75 or json.loads(stderr).get("status_code") in TEMPORARY
                    except (ValueError, AttributeError):
                        retryable = code == 75
            except subprocess.TimeoutExpired as exc:
                stdout, stderr, retryable = exc.stdout or b"", exc.stderr or b"", True
            except OSError as exc:
                stdout, stderr = b"", str(exc).encode()
            stdout_ref = _write_immutable(root, base + "-stdout.json", stdout)
            stderr_ref = _write_immutable(root, base + "-stderr.txt", stderr)
            record, error = None, None
            if code == 0:
                try:
                    opinion = json.loads(stdout)
                    _verify_opinion(root, opinion)
                    if (opinion["packet"] != skeleton["packet"] or opinion["reviewer"] != skeleton["reviewer"]
                            or {r["subject_id"] for r in opinion["results"]} != set(job["subjects"])):
                        raise AssetError("worker changed assigned reviewer, packet or subject coverage")
                    with registration_lock:
                        _current_request(root, document)
                        record = register(root, repository_path(root, stdout_ref["path"]),
                                          origin=f"review campaign {campaign_sha} job {job['id']} attempt {attempt}")["record"]
                except (KeyError, OSError, TypeError, ValueError) as exc:
                    error = str(exc)
            event = {"attempt": attempt, "status": "REGISTERED" if record else "FAILED", "exit_code": code,
                     "retryable": retryable, "seconds": round(time.monotonic() - started, 3),
                     "assignment": assignment_ref, "stdout": stdout_ref, "stderr": stderr_ref,
                     "record": record, "error": error}
            _write_immutable(root, base + ".json", event)
            if record or not retryable:
                break
            if attempt < document["max_attempts"]:
                time.sleep(min(30, backoff_seconds * 2 ** (attempt - 1)))

    # One campaign runner owns the store; independent jobs run in bounded batches.
    from .review_intake import _intake_lock
    with _intake_lock(root):
        if any(_state(_events(root, directory, j), document["max_attempts"]) == "ASSIGNED" for j in document["jobs"]):
            raise AssetError("exported agent assignments are active; finish or record their interruption first")
        with ThreadPoolExecutor(max_workers=document["batch_size"]) as pool:
            futures = [pool.submit(execute, job) for job in document["jobs"]]
            for future in as_completed(futures):
                future.result()
    return status(root, path)
