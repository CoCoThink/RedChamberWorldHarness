"""Local, research-only model opinions. Never an independent-human admission lane.

All immutable receipts and records are inspected, not a coordinator-selected
favorable subset. A packet-scoped summary judges only records bound to that
packet; problems elsewhere in the store are reported, not imputed to it.
Only a negative verdict of BLOCKING severity (rcwh.findings) fails a subject;
softer negatives stay visible as advisories. A reviewer may supersede their own
earlier record; it remains in history but no longer counts.
Byte custody is verified; reviewer/model identity and context isolation are not.
"""
from __future__ import annotations

from contextlib import contextmanager
import json
import os
from pathlib import Path

from ..assets.paths import repository_path
from ..candidate_reviews import canonical_bytes, digest
from ..io import load_data
from ..schema import validate_instance


DIRECTORY = "data/agent_panel"
MINIMUM_REVIEWERS = 2
NEGATIVE = {"FAIL", "REJECT"}
BLOCKING = "BLOCKING"
LIMITATIONS = {
    "identity_basis": "DECLARED_REVIEWER_IDS_AND_SESSION_IDS_NOT_AUTHENTICATED",
    "model_identity": "DECLARED_NOT_VERIFIED",
    "context_isolation": "ASSERTION_NOT_PROVEN",
    "peer_independence": "DISTINCT_DECLARED_IDS_AND_SESSIONS_NOT_EXTERNAL_INDEPENDENCE",
}


def _base() -> dict:
    return {"scope": "AGENT_RESEARCH_REVIEW_PANEL", "authority_effect": "NONE",
            "evidence_effect": "NONE", "usage": "RESEARCH_ONLY",
            "independent_human_admission": False, "automatic_literary_pass": False,
            "minimum_reviewers": MINIMUM_REVIEWERS, "independence_limitations": dict(LIMITATIONS)}


def _json(raw: bytes) -> dict:
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError(f"duplicate JSON field: {key}")
            value[key] = item
        return value
    def invalid(value):
        raise ValueError(f"non-finite JSON value: {value}")
    value = json.loads(raw, object_pairs_hook=unique, parse_constant=invalid)
    if not isinstance(value, dict):
        raise ValueError("agent input must be a JSON object")
    return value


def _schema(root: Path, value: dict, name: str) -> None:
    errors = validate_instance(value, repository_path(root, f"schemas/{name}.schema.json"))
    if errors:
        raise ValueError(f"invalid {name}: " + "; ".join(errors))


def _original(path: Path) -> bytes:
    path = path.absolute()
    if path.is_symlink() or any(p.is_symlink() for p in path.parents) or not path.is_file():
        raise ValueError("FILE input must be a regular file without symlinks")
    return path.read_bytes()


def _bound(root: Path, binding: dict) -> bytes:
    if set(binding) != {"path", "sha256"}:
        raise ValueError("binding must contain only path and sha256")
    path = repository_path(root, binding["path"])
    if not path.is_file():
        raise ValueError(f"missing bound file: {binding['path']}")
    raw = path.read_bytes()
    if digest(raw) != binding["sha256"]:
        raise ValueError(f"stale bound file: {binding['path']}")
    return raw


def _unique_rows(rows: list, key: str, description: str) -> dict:
    result = {row[key]: row for row in rows}
    if len(result) != len(rows):
        raise ValueError(f"duplicate {description}")
    return result


def _sample_records(root: Path, binding: dict) -> list | None:
    """Parse a bound sample carrier using the canonical packet rules."""
    raw = _bound(root, binding)
    path = repository_path(root, binding["path"])
    if path.suffix == ".jsonl":
        return [_json(line) for line in raw.splitlines() if line.strip()]
    if path.suffix in {".json", ".yaml", ".yml"}:
        document = load_data(path)
        if isinstance(document, list):
            return document
        if isinstance(document, dict):
            keys = ("segments", "samples", "sources")
            present = [key for key in keys if key in document]
            if len(present) > 1:
                raise ValueError("sample product has ambiguous record containers")
            if present:
                records = document[present[0]]
                if not isinstance(records, list):
                    raise ValueError("sample product record container must be a list")
                return records
            return [document]
        raise ValueError("sample product must contain records")
    # Images and other whole-file samples have no record membership to check.
    return None


def _sample_record(root: Path, sample: dict, cache: dict) -> None:
    """Verify real JSON/JSONL record membership, parsing each product once."""
    binding = sample["binding"]
    key = (binding["path"], binding["sha256"])
    if key not in cache:
        cache[key] = _sample_records(root, binding)
    rows = cache[key]
    if rows is not None:
        _check_sample(rows, sample["id"])


def _check_sample(rows: list, identity: str) -> None:
    matches = [row for row in rows if isinstance(row, dict)
               and identity in (row.get("segment_id"), row.get("id"))]
    if len(matches) != 1:
        raise ValueError(f"sample not uniquely present in actual product: {identity}")
    row = matches[0]
    if "text" in row and "text_sha256" in row and digest(row["text"].encode()) != row["text_sha256"]:
        raise ValueError(f"sample text digest mismatch: {identity}")


def verify_packet(root: Path, binding: dict) -> dict:
    """Verify the packet FILE bytes, every subject, and every declared sample."""
    packet = _json(_bound(root, binding))
    _schema(root, packet, "agent_packet")
    _unique_rows(packet["subjects"], "id", "packet subject")
    sample_cache = {}
    for subject in packet["subjects"]:
        _bound(root, subject["binding"])
        path = repository_path(root, subject["binding"]["path"])
        if subject["scope"] == "SOURCE":
            document = load_data(path)
            rows = document.get("sources", [document]) if isinstance(document, dict) else []
            matches = [row for row in rows if row.get("id") == subject["source_ref"]]
            if len(matches) != 1:
                raise ValueError(f"source_ref not uniquely present in raw source records: {subject['source_ref']}")
            source = matches[0]
            if not isinstance(source.get("text"), str) or digest(source["text"].encode()) != source.get("text_sha256"):
                raise ValueError(f"source excerpt digest mismatch: {subject['source_ref']}")
        elif subject["scope"] == "CORPUS":
            manifest = load_data(path)
            if not isinstance(manifest, dict) or manifest.get("dataset_ref") != subject["dataset_ref"]:
                raise ValueError(f"corpus manifest dataset mismatch: {subject['id']}")
        samples = subject.get("samples", [])
        _unique_rows(samples, "id", f"sample in {subject['id']}")
        for sample in samples:
            _sample_record(root, sample, sample_cache)
    return packet


def _verify_opinion(root: Path, opinion: dict) -> dict:
    _schema(root, opinion, "agent_review")
    if opinion.get("report_kind") != "AGENT_REVIEW_OPINION":
        raise ValueError("FILE input must be the actual AGENT_REVIEW_OPINION, not a filing envelope")
    packet = verify_packet(root, opinion["packet"])
    if opinion["reviewer"]["session_id"] == packet["coordinator_session_id"]:
        raise ValueError("reviewer session must differ from coordinator_session_id")
    subjects = {row["id"]: row for row in packet["subjects"]}
    results = _unique_rows(opinion["results"], "subject_id", "review subject")
    for identity, result in results.items():
        subject = subjects.get(identity)
        if subject is None or result["subject_sha256"] != subject["binding"]["sha256"]:
            raise ValueError(f"review subject binding mismatch: {identity}")
        samples = {row["id"]: row for row in subject.get("samples", [])}
        checks = _unique_rows(result["sample_checks"], "sample_id", "sample check")
        for sample_id, check in checks.items():
            if sample_id not in samples or check["sha256"] != samples[sample_id]["binding"]["sha256"]:
                raise ValueError(f"review sample binding mismatch: {sample_id}")
    return packet


def _declared_packet(root: Path, binding: dict | None) -> dict | None:
    """Best-effort packet of a broken record, so its failure is charged to it."""
    try:
        record = _json(_original(repository_path(root, binding["path"])))
        packet = record["opinion"]["packet"]
        return packet if isinstance(packet, dict) else None
    except (KeyError, OSError, TypeError, ValueError):
        return None


def _records(root: Path) -> tuple[list[dict], list[dict]]:
    """Read EVERY receipt and EVERY record; an unreceipted record cannot vanish."""
    reports, valid = [], []
    seen = set()
    receipts = repository_path(root, f"{DIRECTORY}/receipts")
    records = repository_path(root, f"{DIRECTORY}/records")
    for path in sorted(receipts.iterdir()) if receipts.exists() else []:
        relative = path.relative_to(root).as_posix()
        report = {"receipt": relative, "status": "FAIL", "findings": []}
        try:
            receipt_raw = _original(repository_path(root, relative))
            receipt = _json(receipt_raw)
            if set(receipt) != {"schema_version", "record"} or receipt["schema_version"] != 1:
                raise ValueError("invalid agent receipt")
            binding = receipt["record"]
            report["record"] = binding
            expected = f"{DIRECTORY}/records/{binding['sha256']}.json"
            if binding["path"] != expected or path.name != f"{binding['sha256']}.json":
                raise ValueError("non-content-addressed agent receipt/record")
            if binding["path"] in seen:
                raise ValueError("duplicate agent receipt")
            seen.add(binding["path"])
            record = _json(_bound(root, binding))
            _schema(root, record, "agent_review")
            if record.get("record_kind") != "REGISTERED_AGENT_REVIEW":
                raise ValueError("registered record must be a filing envelope")
            report["raw_output"] = record["raw_output"]
            expected_raw = f"{DIRECTORY}/raw/{record['raw_output']['sha256']}.json"
            if record["raw_output"]["path"] != expected_raw:
                raise ValueError("non-content-addressed raw agent output")
            raw_opinion = _json(_bound(root, record["raw_output"]))
            if raw_opinion != record["opinion"] or record["packet"] != raw_opinion["packet"]:
                raise ValueError("raw agent output does not match structured opinion")
            packet = _verify_opinion(root, raw_opinion)
            report["status"] = "PASS"
            valid.append({"record": binding, "raw_output": record["raw_output"],
                          "opinion": raw_opinion, "packet": packet})
        except (KeyError, OSError, TypeError, ValueError) as exc:
            report["findings"].append(str(exc))
            report["packet"] = _declared_packet(root, report.get("record"))
        reports.append(report)
    for path in sorted(records.iterdir()) if records.exists() else []:
        relative = path.relative_to(root).as_posix()
        if relative not in seen:
            reports.append({"record": {"path": relative}, "status": "FAIL",
                            "findings": ["unreceipted agent review record; cannot omit existing opinions"]})
    return reports, valid


def _count(reviewers: list[dict]) -> int:
    """Maximum matching: neither alias IDs nor reused sessions create peers."""
    sessions: dict[str, set[str]] = {}
    for reviewer in reviewers:
        sessions.setdefault(reviewer["id"], set()).add(reviewer["session_id"])
    matched: dict[str, str] = {}
    def assign(identity: str, seen: set[str]) -> bool:
        for session in sorted(sessions[identity]):
            if session in seen:
                continue
            seen.add(session)
            if session not in matched or assign(matched[session], seen):
                matched[session] = identity
                return True
        return False
    return sum(assign(identity, set()) for identity in sorted(sessions))


def _identities(opinions: list[dict]) -> list[dict]:
    return [{"id": identity, "session_id": session} for identity, session in
            sorted({(o["reviewer"]["id"], o["reviewer"]["session_id"]) for o in opinions})]


def _same_subject(left: dict, right: dict) -> bool:
    return all(left.get(key) == right.get(key) for key in ("scope", "binding", "source_ref", "dataset_ref"))


def _superseded(records: list[dict]) -> tuple[dict[str, dict], list[str]]:
    """Map superseded record paths to their replacing record; reject foreign claims."""
    by_path = {r["record"]["path"]: r for r in records}
    replaced, findings = {}, []
    for record in records:
        for old in record["opinion"].get("supersedes", []):
            target = by_path.get(old["path"])
            if target is None or target["record"] != old:
                findings.append(f"{record['record']['path']}: supersedes unknown record {old['path']}")
            elif target["opinion"]["reviewer"]["id"] != record["opinion"]["reviewer"]["id"]:
                findings.append(f"{record['record']['path']}: cannot supersede another reviewer's record")
            elif old["path"] == record["record"]["path"]:
                findings.append(f"{record['record']['path']}: cannot supersede itself")
            else:
                replaced[old["path"]] = record["record"]
    return replaced, findings


def _subject_summary(subject: dict, records: list[dict], packet_binding: dict,
                     superseded: dict[str, dict] | None = None) -> dict:
    superseded = superseded or {}
    opinions, history = [], []
    for record in records:
        declared = {s["id"]: s for s in record["packet"]["subjects"]}
        for row in record["opinion"]["results"]:
            if _same_subject(subject, declared[row["subject_id"]]):
                opinion = {"record": record["record"], "raw_output": record["raw_output"],
                           "packet": record["opinion"]["packet"],
                           "same_packet_context": record["opinion"]["packet"] == packet_binding,
                           "reviewer": record["opinion"]["reviewer"], **row}
                if record["record"]["path"] in superseded:
                    history.append({**opinion, "superseded_by": superseded[record["record"]["path"]]})
                else:
                    opinions.append(opinion)
    pending, findings, advisories, coverage = [], [], [], []
    full = []
    for opinion in opinions:
        rejected = [c["sample_id"] for c in opinion["sample_checks"] if c["verdict"] in NEGATIVE]
        advisory_only = subject.get("review_policy") == "ADVISORY"
        blocking = not advisory_only and opinion.get("severity", BLOCKING) == BLOCKING
        if (opinion["verdict"] in NEGATIVE and blocking) or (rejected and not advisory_only):
            findings.append({"record": opinion["record"], "verdict": opinion["verdict"],
                             "severity": BLOCKING,
                             "rejected_samples": rejected, "notes": opinion["notes"]})
        elif opinion["verdict"] in NEGATIVE:
            # A full reading that found only non-blocking problems still counts
            # as a review; its objections are kept as replaceable advisories.
            advisories.append({"record": opinion["record"], "verdict": opinion["verdict"],
                               "severity": "ADVISORY" if advisory_only else opinion["severity"], "notes": opinion["notes"]})
        if not opinion["same_packet_context"]:
            pending.append({"record": opinion["record"], "reason": "DIFFERENT_PACKET_CONTEXT_FOR_SAME_SUBJECT_BYTES"})
        if opinion["verdict"] != "PASS" and opinion["verdict"] not in NEGATIVE:
            pending.append({"record": opinion["record"], "reason": opinion["verdict"]})
        if not opinion["reviewer"]["context_isolation"]["asserted"]:
            pending.append({"record": opinion["record"], "reason": "CONTEXT_ISOLATION_NOT_ASSERTED"})
        checks = {c["sample_id"]: c for c in opinion["sample_checks"]}
        accepted = opinion["verdict"] == "PASS" or (opinion["verdict"] in NEGATIVE and not blocking)
        if (opinion["same_packet_context"] and accepted and opinion["reviewer"]["context_isolation"]["asserted"]
                and all(checks.get(s["id"], {}).get("verdict") == "PASS" for s in subject.get("samples", []))):
            full.append(opinion)
        for check in checks.values():
            if check["verdict"] not in NEGATIVE | {"PASS"}:
                pending.append({"record": opinion["record"], "sample_id": check["sample_id"],
                                "reason": check["verdict"]})
    for sample in subject.get("samples", []):
        checked = [o for o in opinions if o["same_packet_context"] and o["verdict"] == "PASS"
                   and o["reviewer"]["context_isolation"]["asserted"]
                   and any(c["sample_id"] == sample["id"] and c["verdict"] == "PASS" for c in o["sample_checks"])]
        rejected = any(c["sample_id"] == sample["id"] and c["verdict"] in NEGATIVE
                       for o in opinions for c in o["sample_checks"])
        count = _count([o["reviewer"] for o in checked])
        coverage.append({"sample_id": sample["id"], "binding": sample["binding"],
                         "status": "FAIL" if rejected else "PASS" if count >= MINIMUM_REVIEWERS else "PENDING",
                         "distinct_reviewer_count": count, "reviewers": _identities(checked)})
    count = _count([o["reviewer"] for o in full])
    if count < MINIMUM_REVIEWERS:
        pending.append({"reason": "TWO_DISTINCT_FULL_SUBJECT_REVIEWERS_REQUIRED", "actual": count})
    state = "FAIL" if findings else "PENDING" if pending or any(c["status"] != "PASS" for c in coverage) else "PASS"
    return {**subject, "status": state, "review_count": len(opinions),
            "distinct_reviewer_count": count, "full_reviewers": _identities(full),
            "sample_coverage": coverage, "opinions": opinions, "findings": findings,
            "advisories": advisories, "superseded_opinions": history, "pending": pending}


def summary(root: Path, packet: str | Path | dict | None = None) -> dict:
    root = Path(root).resolve()
    try:
        reports, records = _records(root)
    except (KeyError, OSError, TypeError, ValueError) as exc:
        return {**_base(), "status": "FAIL", "record_integrity_status": "FAIL",
                "findings": [str(exc)], "pending": [], "panels": [], "records": []}
    store_findings = [f"{r.get('receipt', r.get('record'))}: {issue}" for r in reports for issue in r["findings"]]
    superseded, supersede_findings = _superseded(records)
    store_findings += supersede_findings
    store_integrity = "FAIL" if store_findings else "PASS"
    findings = list(store_findings) if packet is None else []
    packets: dict[tuple[str, str], dict] = {}
    for record in records:
        binding = record["opinion"]["packet"]
        packets[(binding["path"], binding["sha256"])] = record["packet"]
    if packet is not None:
        try:
            if isinstance(packet, dict):
                binding = packet
            else:
                path = Path(packet)
                relative = path.relative_to(root).as_posix() if path.is_absolute() else path.as_posix()
                binding = {"path": relative, "sha256": digest(repository_path(root, relative).read_bytes())}
            findings += [f"{r.get('receipt', r.get('record'))}: {issue}" for r in reports
                         if r.get("packet") == binding for issue in r["findings"]]
            document = verify_packet(root, binding)
            requested = (binding["path"], binding["sha256"])
            packets = {requested: document}
        except (KeyError, OSError, TypeError, ValueError) as exc:
            findings.append(str(exc))
            packets = {}
    panels = []
    for (path, sha), document in sorted(packets.items()):
        bound = [r for r in records if r["opinion"]["packet"] == {"path": path, "sha256": sha}]
        subjects = [_subject_summary(s, records, {"path": path, "sha256": sha}, superseded) for s in document["subjects"]]
        state = "FAIL" if any(s["status"] == "FAIL" for s in subjects) else (
            "PENDING" if any(s["status"] == "PENDING" for s in subjects) else "PASS")
        panels.append({"packet": {"path": path, "sha256": sha}, "id": document["id"],
                       "status": state, "subjects": subjects, "review_count": len(bound)})
    pending = [] if panels else ["NO_REGISTERED_AGENT_REVIEW_PACKET"]
    state = "FAIL" if findings or any(p["status"] == "FAIL" for p in panels) else (
        "PASS" if panels and all(p["status"] == "PASS" for p in panels) else "PENDING")
    # A packet-scoped view is judged by its own packet and records; store-wide
    # problems are surfaced separately and still fail `rcwh validate`.
    integrity = store_integrity if packet is None else ("FAIL" if findings else "PASS")
    return {**_base(), "status": state, "record_integrity_status": integrity,
            "store_integrity_status": store_integrity, "store_findings": store_findings,
            "findings": findings, "pending": pending, "panels": panels, "records": reports,
            "review_count": len(records)}


status = summary


@contextmanager
def _lock(root: Path):
    path = repository_path(root, ".rcwh-cache/agent-panel.lock")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as handle:
        if os.name == "nt":
            import msvcrt
            if not handle.read(1):
                handle.write(b"\0"); handle.flush()
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            if os.name == "nt":
                handle.seek(0); msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _store(root: Path, relative: str, raw: bytes) -> bool:
    path = repository_path(root, relative)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if _original(path) != raw:
            raise ValueError(f"immutable agent file already differs: {relative}")
        return False
    with path.open("xb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    return True


def scaffold(root: Path, packet: str | Path, *, reviewer_id: str, session_id: str,
             subjects: list[str] | None = None, model_label: str = "claude subagent (declared)") -> dict:
    """Opinion skeleton with exact bindings; it cannot be registered until filled in.

    Verdicts and notes are left empty, which the schema rejects, so an unreviewed
    skeleton never becomes a record. ``sample_checks`` is prefilled from the
    packet's declared samples (empty when a subject declares none).
    """
    root = Path(root).resolve()
    path = Path(packet)
    relative = path.relative_to(root).as_posix() if path.is_absolute() else path.as_posix()
    binding = {"path": relative, "sha256": digest(repository_path(root, relative).read_bytes())}
    document = verify_packet(root, binding)
    chosen = document["subjects"]
    if subjects is not None:
        known = {s["id"] for s in chosen}
        if set(subjects) - known:
            raise ValueError(f"unknown packet subjects: {sorted(set(subjects) - known)}")
        chosen = [s for s in chosen if s["id"] in subjects]
    return {"schema_version": 1, "report_kind": "AGENT_REVIEW_OPINION", "packet": binding,
            "reviewer": {"id": reviewer_id, "kind": "MODEL_SUBAGENT", "session_id": session_id,
                         "model": {"label": model_label, "verification": "DECLARED_NOT_VERIFIED"},
                         "context_isolation": {"asserted": True, "verification": "NOT_PROVEN"}},
            "results": [{"subject_id": s["id"], "subject_sha256": s["binding"]["sha256"],
                         "verdict": "", "notes": "",
                         **({"severity": "ADVISORY"} if s.get("review_policy") == "ADVISORY" else {}),
                         "sample_checks": [{"sample_id": x["id"], "sha256": x["binding"]["sha256"],
                                            "verdict": "", "notes": ""} for x in s.get("samples", [])]}
                        for s in chosen],
            "authority_effect": "NONE", "usage": "RESEARCH_ONLY", "independent_human_admission": False}


def register(root: Path, file: Path, *, origin: str, origin_kind: str = "FILE", dry_run: bool = False) -> dict:
    root = Path(root).resolve()
    if origin_kind != "FILE" or not origin.strip():
        raise ValueError("agent registration requires local FILE origin and a nonblank origin description")
    raw = _original(Path(file))
    opinion = _json(raw)
    _verify_opinion(root, opinion)
    current = summary(root)
    if current["record_integrity_status"] == "FAIL":
        raise ValueError("existing registered agent records invalid: " + "; ".join(current["findings"]))
    if opinion.get("supersedes"):
        _, valid = _records(root)
        by_path = {r["record"]["path"]: r for r in valid}
        for old in opinion["supersedes"]:
            target = by_path.get(old["path"])
            if target is None or target["record"] != old:
                raise ValueError(f"superseded record is not registered: {old['path']}")
            if target["opinion"]["reviewer"]["id"] != opinion["reviewer"]["id"]:
                raise ValueError("a reviewer can only supersede their own registered record")
    raw_binding = {"path": f"{DIRECTORY}/raw/{digest(raw)}.json", "sha256": digest(raw)}
    for existing in current["records"]:
        if existing.get("raw_output") == raw_binding:
            raise ValueError("raw agent opinion already registered; immutable records are not overwritten")
    record = {"schema_version": 1, "record_kind": "REGISTERED_AGENT_REVIEW",
              "origin_kind": "FILE", "origin": origin, "packet": opinion["packet"],
              "raw_output": raw_binding, "opinion": opinion, "authority_effect": "NONE",
              "usage": "RESEARCH_ONLY", "independent_human_admission": False}
    _schema(root, record, "agent_review")
    record_raw = canonical_bytes(record)
    binding = {"path": f"{DIRECTORY}/records/{digest(record_raw)}.json", "sha256": digest(record_raw)}
    receipt_path = f"{DIRECTORY}/receipts/{binding['sha256']}.json"
    receipt_raw = canonical_bytes({"schema_version": 1, "record": binding})
    if dry_run:
        return {**_base(), "status": "PASS", "operation": "REGISTRATION_PREFLIGHT_ONLY", "dry_run": True,
                "registered": False, "record": binding, "raw_output": raw_binding, "written_files": []}
    with _lock(root):
        # Repeat all byte/schema checks under the local writer lock.
        if _original(Path(file)) != raw:
            raise ValueError("raw agent output changed after preflight")
        _verify_opinion(root, opinion)
        now = summary(root)
        if now["record_integrity_status"] == "FAIL":
            raise ValueError("existing registered agent records invalid after preflight")
        if any(r.get("raw_output") == raw_binding for r in now["records"]):
            raise ValueError("raw agent opinion already registered")
        written = []
        for relative, data in ((raw_binding["path"], raw), (binding["path"], record_raw), (receipt_path, receipt_raw)):
            if _store(root, relative, data):
                written.append(relative)
    report = summary(root, packet=opinion["packet"])
    return {**_base(), "status": report["status"], "operation": "REGISTRATION_ONLY", "registered": True,
            "record": binding, "raw_output": raw_binding, "written_files": written,
            "panel_report": report}


class AgentPanel:
    def __init__(self, root: Path):
        self.root = Path(root).resolve()

    def summary(self, packet: str | Path | dict | None = None) -> dict:
        return summary(self.root, packet=packet)

    def register(self, file: Path, *, origin: str, origin_kind: str = "FILE", dry_run: bool = False) -> dict:
        return register(self.root, file, origin=origin, origin_kind=origin_kind, dry_run=dry_run)
