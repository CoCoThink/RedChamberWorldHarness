"""Bound review opinions for the existing competition gates.

This verifies submitted identities and custody attestations, not a person's
identity or the literary truth of an opinion. It never manufactures reviews.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .assets.catalog import repository_path
from .io import load_data
from .literary_suite import LiteraryEvaluatorSuite
from .schema import validate_instance


SIX_FIELDS = ["PROVENANCE", "ROLE", "MODALITY", "TARGET", "PLACEMENT", "IMPLEMENTATION"]
REVIEW_CHECKS = SIX_FIELDS + ["HUMAN_PLOCK", "BLIND_READ"]
CONTEXT_DOMAINS = (
    "project", "reconstruction", "world", "knowledge", "objects", "scenes",
    "literary_eval", "plocks", "mechanisms", "mechanism_adapters", "provenance",
)


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def bound_data(root: Path, binding: dict[str, str]) -> Any:
    path = repository_path(root, binding["path"])
    if digest(path.read_bytes()) != binding["sha256"]:
        raise ValueError(f"review input identity mismatch: {binding['path']}")
    return load_data(path)


def candidate_bytes(root: Path, candidate: dict[str, Any]) -> bytes:
    from .competition import git_blob_sha

    artifact = candidate["artifact"]
    if artifact["kind"] != "REPO_FILE":
        raise ValueError("current reviews require a repository candidate")
    raw = repository_path(root, artifact["path"]).read_bytes()
    if git_blob_sha(raw) != artifact["git_blob_sha"]:
        raise ValueError("review candidate content identity mismatch")
    return raw


def verified_author_model(root: Path, author: dict, candidate_raw: bytes) -> dict:
    """Read model family from the bound execution, never an unbound label."""
    run = bound_data(root, author["run"])
    errors = validate_instance(run, root / "schemas/candidate_model_run.schema.json")
    if errors:
        raise ValueError("invalid model run: " + "; ".join(errors))
    if run["source_id"] != author["source_id"]:
        raise ValueError("author/model source identity mismatch")
    for key in ("prompt", "input", "output"):
        if digest(run[key].encode("utf-8")) != run[f"{key}_sha256"]:
            raise ValueError(f"model {key} identity mismatch")
    if run["output"].encode("utf-8") != candidate_raw:
        raise ValueError("model output does not match authored candidate")
    return run["model"]


def context_sha256(root: Path, record: dict[str, Any]) -> str:
    """Freeze substantive context without including mutable opinions or flags."""
    inputs = {}
    for domain in CONTEXT_DOMAINS:
        for path in sorted((root / "data" / domain).rglob("*")):
            if path.is_file() and path.suffix in {".json", ".yaml", ".yml"}:
                relative = path.relative_to(root).as_posix()
                inputs[relative] = digest(repository_path(root, relative).read_bytes())
    candidates = [{
        "id": c["id"], "blind_token": c["blind_token"],
        "sha256": digest(candidate_bytes(root, c)), "authors": c.get("authors", []),
        "semantic_readings": c.get("semantic_readings", []),
    } for c in record["candidates"]]
    return digest(canonical_bytes({
        "competition": record["id"], "chapter": record["chapter"],
        "baseline": record["baseline"], "plock_ref": record["plock_ref"],
        "protocol": record.get("review_protocol"), "candidates": candidates,
        "inputs": inputs,
    }))


def review_packet(root: Path, record: dict[str, Any]) -> dict[str, Any]:
    """The coordinator receives context bindings; readers receive only packet."""
    protocol = bound_data(root, record["review_protocol"])
    errors = validate_instance(protocol, root / "schemas" / "candidate_review_protocol.schema.json")
    if errors:
        raise ValueError("invalid review protocol: " + "; ".join(errors))
    suite = LiteraryEvaluatorSuite.from_repo(root)
    packet = suite.competition_blind_packet(record)
    packet["review_questions"] = protocol["questions"]
    leaks = suite.blind_output_violations(packet)
    rendered = canonical_bytes(packet).decode("utf-8")
    for candidate in record["candidates"]:
        identities = [candidate["id"], candidate["artifact"]["path"]]
        for author in candidate.get("authors", []):
            identities.extend([author.get("principal_id"), author.get("source_id")])
        leaks.extend(f"candidate/author identity in anonymous packet: {identity}"
                     for identity in identities if identity and identity in rendered)
    if leaks:
        raise ValueError("anonymous review packet leaks metadata: " + "; ".join(leaks))
    return {
        "context_sha256": context_sha256(root, record),
        "required_checks": REVIEW_CHECKS,
        "protocol": record["review_protocol"], "packet_sha256": digest(canonical_bytes(packet)),
        "packet": packet,
    }


def raw_opinion(review: dict[str, Any]) -> dict[str, Any]:
    """Exact original structured opinion, before adding filing metadata."""
    return {k: v for k, v in review.items() if k not in {"id", "schema_version", "raw_review", "authority_effect"}}


class CandidateReviewService:
    def __init__(self, root: Path, record: dict[str, Any]):
        self.root = root
        self.record = record
        self.protocol = None
        self.prepared = None
        self.findings: list[str] = []
        self.missing: list[str] = []
        self.author_principals: set[str] = set()
        self.author_sources: set[str] = set()
        if not record.get("review_protocol"):
            self.missing.append("no bound review protocol")
        else:
            try:
                self.prepared = review_packet(root, record)
                self.protocol = bound_data(root, record["review_protocol"])
            except (KeyError, OSError, ValueError) as exc:
                self.findings.append(str(exc))
        for candidate in record["candidates"]:
            authors = candidate.get("authors", [])
            if not authors:
                self.missing.append(f"{candidate['id']}: author identity is not recorded")
            for author in authors:
                try:
                    errors = validate_instance(author, root / "schemas" / "candidate_author.schema.json")
                    if errors:
                        raise ValueError("invalid author: " + "; ".join(errors))
                    self.author_principals.add(author["principal_id"])
                    self.author_sources.add(author["source_id"])
                    if author["kind"] == "MODEL":
                        verified_author_model(root, author, candidate_bytes(root, candidate))
                except (KeyError, OSError, ValueError) as exc:
                    self.findings.append(f"{candidate['id']}: {exc}")

    def evaluate(self, candidate: dict[str, Any], machine_status: str) -> dict[str, Any]:
        findings = list(self.findings)
        missing = list(self.missing)
        valid = []
        principals: set[str] = set()
        sources: set[str] = set()
        ids: set[str] = set()
        minimum = self.protocol["minimum_reviewers"] if self.protocol else 2
        try:
            raw = candidate_bytes(self.root, candidate)
            text = raw.decode("utf-8")
        except (KeyError, OSError, ValueError) as exc:
            findings.append(str(exc))
            raw, text = b"", ""
        for binding in candidate.get("review_records", []):
            try:
                review = bound_data(self.root, binding)
                errors = validate_instance(review, self.root / "schemas" / "candidate_review.schema.json")
                if errors:
                    raise ValueError("invalid review: " + "; ".join(errors))
                if self.prepared is None:
                    raise ValueError("review has no valid protocol/context")
                for key, expected in {
                    "candidate_sha256": digest(raw), "blind_token": candidate["blind_token"],
                    "context_sha256": self.prepared["context_sha256"],
                    "protocol": self.record["review_protocol"],
                }.items():
                    if review[key] != expected:
                        raise ValueError(f"stale or mismatched review {key}")
                packet = bound_data(self.root, review["packet"])
                if packet != self.prepared["packet"] or review["packet"]["sha256"] != self.prepared["packet_sha256"]:
                    raise ValueError("review packet does not match current blinded candidates")
                if bound_data(self.root, review["raw_review"]) != raw_opinion(review):
                    raise ValueError("submitted review differs from original opinion")
                reviewer = review["reviewer"]
                principal, source = reviewer["principal_id"], reviewer["source_id"]
                if principal in self.author_principals or source in self.author_sources:
                    raise ValueError("reviewer shares an author principal or source")
                if principal in principals or source in sources or review["id"] in ids:
                    raise ValueError("duplicate reviewer principal, source, or review id")
                for name, check in review["checks"].items():
                    if name != "HUMAN_PLOCK" and check["status"] == "REPLACEMENT_ACCEPTED":
                        raise ValueError("replacement acceptance applies only to HUMAN_PLOCK")
                    for span in check["evidence_spans"]:
                        if not 0 <= span["start"] < span["end"] <= len(text) or text[span["start"]:span["end"]] != span["quote"]:
                            raise ValueError(f"invalid candidate evidence span for {name}")
                principals.add(principal)
                sources.add(source)
                ids.add(review["id"])
                valid.append(review)
            except (KeyError, OSError, ValueError) as exc:
                findings.append(f"{binding.get('path')}: {exc}")
        if len(valid) < minimum:
            missing.append(f"independent reviewers: {len(valid)}/{minimum}")
        checks = {}
        for name in REVIEW_CHECKS:
            values = [r["checks"][name]["status"] for r in valid]
            wanted = "REPLACEMENT_ACCEPTED" if name == "HUMAN_PLOCK" and machine_status == "REPLACEMENT_CASE" else "PASS"
            if any(v != wanted for v in values):
                checks[name] = "FAIL"
                findings.append(f"review opinion rejects {name} or does not accept required replacement")
            else:
                checks[name] = wanted if not findings and not missing else "PENDING"
        status = "FAIL" if findings else "PENDING" if missing else "PASS"
        # A malformed submission must not leave individual checks looking qualified.
        if findings:
            checks = {name: "FAIL" for name in REVIEW_CHECKS}
        return {
            "report_kind": "REVIEW_OPINION", "status": status,
            "candidate_sha256": digest(raw) if raw else None,
            "context_sha256": self.prepared["context_sha256"] if self.prepared else None,
            "review_count": len(valid), "minimum_reviewers": minimum,
            "check_statuses": checks, "findings": findings, "pending": missing,
            "independence_basis": "SUBMITTED_IDENTITIES_AND_CUSTODY_ATTESTATIONS",
            "review_ids": sorted(ids), "authority_effect": "NONE",
        }
