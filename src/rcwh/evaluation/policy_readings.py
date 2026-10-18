"""Atomic local reading bundles; custody and attributed findings, not admission.

A complete bundle is published with one directory rename under a shared reader /
exclusive writer lock. Raw adverse declarations remain visible if another bundle
member is damaged. Stale validator versions block clearance, not future intake.
"""
from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
import os
from pathlib import Path
import stat
import tempfile

from ..assets.paths import repository_path
from ..candidate_reviews import canonical_bytes, digest
from ..schema import validate_instance
from .policy_evidence import SCHEMA, _bound, check_policy_evidence, strict_json

DIRECTORY = "data/evaluation/policy_evidence"
LOCK = ".rcwh-cache/policy-evidence.lock"


def _regular_bytes(root: Path, relative: str) -> bytes:
    path = repository_path(root, relative)
    if not stat.S_ISREG(path.stat().st_mode):
        raise ValueError(f"not a regular registry file: {relative}")
    return path.read_bytes()


def _base() -> dict:
    return {"kind": "POLICY_READING_CUSTODY_SUMMARY", "status": "PENDING",
            "integrity_status": "PASS", "semantic_status": "PENDING",
            "identity_eligibility": "PENDING_NOT_IMPLEMENTED",
            "release_gate_eligibility": "PENDING", "qualification": "MODEL",
            "authority_effect": "NONE", "evidence_effect": "NONE",
            "independent_human_admission": False, "automatic_literary_pass": False,
            "records": [], "findings": [], "active_negative_declarations": [],
            "historical_negative_declarations": [], "pending_applicability": [],
            "unverified_negative_declarations": [], "replay_pending": [],
            "inventory_completeness": "PENDING_NO_INDEPENDENT_EXPECTED_BUNDLE_ANCHOR",
            "limitations": ["Attributed violations are not established semantic failures.",
                            "Custody is not authenticated identity or actual reading.",
                            "No positive-reader counting or release consumer.",
                            "Deleting an entire bundle cannot be detected without an independently bound expected inventory."]}


@contextmanager
def _registry_lock(root: Path, *, writer: bool = True):
    path = repository_path(root, LOCK)
    if writer:
        path.parent.mkdir(parents=True, exist_ok=True)
        repository_path(root, LOCK)
    elif not path.exists():
        # Empty/uninitialized registries need no lock. A published registry
        # without its lock is invalid, but still scanned for raw declarations.
        yield False
        return
    if path.exists() and not stat.S_ISREG(path.stat().st_mode):
        raise ValueError("policy registry lock is not a regular file")
    with path.open("a+b" if writer else "rb") as handle:
        if os.name == "nt":
            import msvcrt
            if writer and path.stat().st_size == 0:
                handle.write(b"\0")
                handle.flush()
            handle.seek(0)
            mode = msvcrt.LK_NBLCK if writer else msvcrt.LK_NBRLCK
            msvcrt.locking(handle.fileno(), mode, 1)
        else:
            import fcntl
            mode = fcntl.LOCK_EX if writer else fcntl.LOCK_SH
            fcntl.flock(handle.fileno(), mode | fcntl.LOCK_NB)
        try:
            yield True
        finally:
            if os.name == "nt":
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _bundle_id(request_raw: bytes, raw: bytes) -> str:
    return digest(canonical_bytes({"request": digest(request_raw), "raw_reading": digest(raw)}))


def _finish(report):
    report["integrity_status"] = "FAIL" if report["findings"] else "PASS"
    report["status"] = "FAIL" if report["findings"] or any(
        record.get("current_subject") and record.get("machine_status") == "FAIL"
        for record in report["records"]) else "PENDING"
    return report


def _scan(root: Path, request: dict | None, *, locked: bool) -> dict:
    report = _base()
    directory = repository_path(root, DIRECTORY)
    if request is not None:
        from .policy_evidence import build_policy_evidence_request
        try:
            rebuilt = build_policy_evidence_request(root, request["context"]["selection"], request["chapter"])
            if canonical_bytes(request) != canonical_bytes(rebuilt):
                raise ValueError("altered summary request")
        except (OSError, ValueError, KeyError, TypeError) as exc:
            report["findings"].append(str(exc))
    if not directory.exists():
        return _finish(report)
    if not locked:
        report["findings"].append("published registry has no coordination lock")
    for child in sorted(directory.iterdir()):
        try:
            safe = repository_path(root, child.relative_to(root).as_posix())
            if child.name != "bundles" or not safe.is_dir():
                raise ValueError("unexpected registry entry")
        except (OSError, ValueError) as exc:
            report["findings"].append(f"{child.relative_to(root)}: {exc}")
    try:
        bundles = repository_path(root, f"{DIRECTORY}/bundles")
        paths = sorted(bundles.iterdir()) if bundles.exists() else []
    except (OSError, ValueError) as exc:
        report["findings"].append(str(exc))
        return _finish(report)
    for path in paths:
        relative = path.relative_to(root).as_posix()
        record = {"bundle": relative, "custody_status": "FAIL", "current_subject": False,
                  "machine_status": "PENDING", "negative_declarations": []}
        reading = frozen = None
        raw = request_raw = None
        issues = []
        # Scan each safe member independently; a damaged receipt must not prevent
        # inspection of a still readable raw adverse declaration.
        try:
            safe = repository_path(root, relative)
            if not safe.is_dir():
                raise ValueError("bundle is not a directory")
            members = {item.name for item in safe.iterdir()}
            if members != {"request.json", "raw.json", "receipt.json"}:
                issues.append("bundle has missing or extra members")
            for item in safe.iterdir():
                try:
                    repository_path(root, item.relative_to(root).as_posix())
                except ValueError as exc:
                    issues.append(str(exc))
        except (OSError, ValueError) as exc:
            report["findings"].append(f"{relative}: {exc}")
            continue
        try:
            raw = _regular_bytes(root, relative + "/raw.json")
            reading = strict_json(raw)
            record["raw_reading"] = {"path": relative + "/raw.json", "sha256": digest(raw)}
            if isinstance(reading, dict):
                record["reader"] = deepcopy(reading.get("reader"))
                checks = reading.get("checks", [])
                if isinstance(checks, list):
                    record["negative_declarations"] = [deepcopy(row) for row in checks
                        if isinstance(row, dict) and row.get("finding") == "VIOLATED"]
            errors = validate_instance(reading, SCHEMA)
            if errors:
                raise ValueError("invalid raw reading: " + "; ".join(errors))
        except (OSError, ValueError, KeyError, TypeError) as exc:
            issues.append(str(exc))
            reading = None
        try:
            request_raw = _regular_bytes(root, relative + "/request.json")
            frozen = strict_json(request_raw)
            if not isinstance(frozen, dict):
                raise ValueError("stored request must be an object")
            payload = {key: value for key, value in frozen.items() if key != "request_sha256"}
            if digest(canonical_bytes(payload)) != frozen["request_sha256"]:
                raise ValueError("stored request canonical preimage differs")
            if digest(canonical_bytes(frozen["context"])) != frozen["context_sha256"] or digest(canonical_bytes(frozen["manifest"])) != frozen["manifest_sha256"]:
                raise ValueError("stored context or manifest differs")
            record["request"] = {"path": relative + "/request.json", "sha256": digest(request_raw)}
        except (OSError, ValueError, KeyError, TypeError) as exc:
            issues.append(str(exc))
            frozen = None
        try:
            receipt_raw = _regular_bytes(root, relative + "/receipt.json")
            receipt = strict_json(receipt_raw)
            expected = {"schema_version": 1, "kind": "POLICY_READING_RECEIPT",
                        "request_sha256": digest(request_raw), "raw_sha256": digest(raw),
                        "origin": receipt["origin"], "authority_effect": "NONE"}
            if (canonical_bytes(receipt) != canonical_bytes(expected)
                    or not isinstance(receipt["origin"], str) or not receipt["origin"].strip()):
                raise ValueError("invalid receipt metadata or payload hashes")
            if path.name != _bundle_id(request_raw, raw):
                raise ValueError("bundle identity does not bind payloads")
            record["receipt"] = {"path": relative + "/receipt.json", "sha256": digest(receipt_raw)}
        except (OSError, ValueError, KeyError, TypeError) as exc:
            issues.append(str(exc))
        if frozen is not None and reading is not None:
            if any(reading[key] != frozen[key] for key in ("request_sha256", "context_sha256", "manifest_sha256")) or reading["candidate_sha256"] != frozen["context"]["selected"]["candidate"]["sha256"]:
                issues.append("raw reading differs from frozen request")
        if not issues:
            record["custody_status"] = "PASS"
            try:
                checked = check_policy_evidence(root, frozen, record["raw_reading"])
                record["checked"] = checked
                record["machine_status"] = checked["machine"]["status"]
            except (OSError, ValueError, KeyError, TypeError) as exc:
                # Input/code evolution is not damage to the saved raw bundle.
                report["replay_pending"].append({"bundle": relative, "reason": str(exc)})
        report["findings"].extend(f"{relative}: {issue}" for issue in issues)
        if frozen is not None:
            candidate_sha = frozen["context"]["selected"]["candidate"]["sha256"]
            policy_sha = frozen["context"]["selected"]["policy"]["sha256"]
            same = request is None or (candidate_sha == request["context"]["selected"]["candidate"]["sha256"] and policy_sha == request["context"]["selected"]["policy"]["sha256"])
            same_chapter = request is None or frozen["chapter"] == request["chapter"]
            record.update(candidate_sha256=candidate_sha, policy_sha256=policy_sha, current_subject=same)
        else:
            same = same_chapter = False
        for negative in record["negative_declarations"]:
            kept = {"bundle": relative, "raw_reading": record["raw_reading"], "reader": record.get("reader"), "check": negative}
            if issues or frozen is None:
                report["unverified_negative_declarations"].append(kept)
            elif same:
                report["active_negative_declarations"].append(kept)
            else:
                report["historical_negative_declarations"].append(kept)
            if not issues and request is not None and same_chapter and (not same or frozen["context_sha256"] != request["context_sha256"]):
                report["pending_applicability"].append({"bundle": relative,
                    "reason": "NEGATIVE_REQUIRES_EXPLICIT_CONTEXT_OR_VERSION_CROSSWALK"})
        report["records"].append(record)
    return _finish(report)


def policy_reading_summary(root: Path, request: dict | None = None) -> dict:
    """Read the fixed complete registry under the same lock used by writers."""
    root = root.resolve()
    try:
        with _registry_lock(root, writer=False) as locked:
            return _scan(root, request, locked=locked)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        report = _base()
        report.update(status="FAIL", integrity_status="FAIL", findings=[str(exc)])
        return report


def _publish_bundle(root: Path, request_raw: bytes, raw: bytes, origin: str) -> str:
    identity = _bundle_id(request_raw, raw)
    relative = f"{DIRECTORY}/bundles/{identity}"
    destination = repository_path(root, relative)
    destination.parent.mkdir(parents=True, exist_ok=True)
    repository_path(root, relative)
    # Staging is outside the scanned registry. An interrupted stage is not an
    # opinion and does not prevent retrying the exact submission. No cleanup of
    # somebody else's files or historical payloads is performed.
    staging_root = repository_path(root, ".rcwh-cache/policy-evidence-staging")
    staging_root.mkdir(parents=True, exist_ok=True)
    repository_path(root, ".rcwh-cache/policy-evidence-staging")
    stage = Path(tempfile.mkdtemp(prefix="submission-", dir=staging_root))
    receipt = {"schema_version": 1, "kind": "POLICY_READING_RECEIPT",
               "request_sha256": digest(request_raw), "raw_sha256": digest(raw),
               "origin": origin, "authority_effect": "NONE"}
    for name, content in (("request.json", request_raw), ("raw.json", raw), ("receipt.json", canonical_bytes(receipt))):
        with (stage / name).open("xb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
    os.rename(stage, destination)
    return relative


def register_policy_reading(root: Path, request: dict, file: Path, *, origin: str,
                            dry_run: bool = False) -> dict:
    """Publish one complete immutable bundle; no asset/catalog or release write."""
    root, file = root.resolve(), file.absolute()
    if (not isinstance(origin, str) or not origin.strip() or not file.is_relative_to(root)
            or file.is_symlink() or any(p.is_symlink() for p in file.parents) or not file.is_file()):
        raise ValueError("policy reading requires an explicit repository FILE and origin")
    raw = _regular_bytes(root, file.relative_to(root).as_posix())
    ref = {"path": file.relative_to(root).as_posix(), "sha256": digest(raw)}
    checked = check_policy_evidence(root, request, ref)
    if file.read_bytes() != raw:
        raise ValueError("raw reading changed during validation")
    request_raw = canonical_bytes(request)
    if dry_run:
        current = policy_reading_summary(root)
        if current["integrity_status"] != "PASS":
            raise ValueError("existing policy reading custody invalid")
        return {"status": "PENDING", "written": False, "dry_run": True, "checked": checked, "authority_effect": "NONE"}
    with _registry_lock(root):
        current = _scan(root, None, locked=True)
        if current["integrity_status"] != "PASS":
            raise ValueError("existing policy reading custody invalid: " + "; ".join(current["findings"]))
        relative = f"{DIRECTORY}/bundles/{_bundle_id(request_raw, raw)}"
        if any(record["bundle"] == relative for record in current["records"]):
            return {"status": "PENDING", "written": False, "bundle": relative, "authority_effect": "NONE"}
        # Recheck selected bytes after acquiring the write lock, before publish.
        check_policy_evidence(root, request, ref)
        _publish_bundle(root, request_raw, raw, origin)
        return {"status": "PENDING", "written": True, "bundle": relative,
                "authority_effect": "NONE", "independent_human_admission": False}
