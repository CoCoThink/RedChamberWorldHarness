"""Frozen expected-bundle inventories, effective only with a trusted binding.

An inventory is an observed checkpoint, not an authenticated append-only log. Its
exact external binding must be retained by the selecting owner. Creating a new
inventory from surviving files cannot establish that nothing was deleted before
that first checkpoint. No release or semantic consumer is added here.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from ..assets.paths import repository_path
from ..candidate_reviews import canonical_bytes, digest
from ..schema import validate_instance
from .policy_evidence import strict_json
from .policy_readings import DIRECTORY, _finish, _registry_lock, _regular_bytes, _scan

SCHEMA = Path(__file__).resolve().parents[3] / "schemas/policy_reading_inventory.schema.json"
MEMBERS = ("raw.json", "receipt.json", "request.json")


def _load_chain(root: Path, anchor: dict) -> list[dict]:
    if anchor is None:
        raise ValueError("external inventory anchor is required")
    chain, seen = [], set()
    current = anchor
    while current is not None:
        if not isinstance(current, dict) or set(current) != {"path", "sha256"}:
            raise ValueError("inventory anchor requires exact path and sha256")
        raw = _regular_bytes(root, current["path"])
        if digest(raw) != current["sha256"]:
            raise ValueError("stale policy inventory anchor")
        if current["sha256"] in seen:
            raise ValueError("inventory predecessor cycle")
        seen.add(current["sha256"])
        value = strict_json(raw)
        errors = validate_instance(value, SCHEMA)
        if errors:
            raise ValueError("invalid policy inventory: " + "; ".join(errors))
        if type(value["schema_version"]) is not int or value["schema_version"] != 1:
            raise ValueError("inventory version must be an integer")
        identities = [row["bundle"] for row in value["bundles"]]
        if identities != sorted(set(identities)):
            raise ValueError("inventory bundle paths must be sorted and unique")
        for row in value["bundles"]:
            if [ref["path"] for ref in row["members"]] != [row["bundle"] + "/" + name for name in MEMBERS]:
                raise ValueError("inventory members must cover each exact bundle member")
            # Check paths without reading historical bundle members: an ancestor
            # remains usable as an expectation after a later bundle deletion.
            for ref in row["members"]:
                repository_path(root, ref["path"])
        chain.append(value)
        current = value["previous"]
    for newer, older in zip(chain, chain[1:]):
        actual = {row["bundle"]: row for row in newer["bundles"]}
        for row in older["bundles"]:
            if canonical_bytes(actual.get(row["bundle"])) != canonical_bytes(row):
                raise ValueError("inventory successor removes or alters an expected bundle")
    return chain


def build_policy_inventory(root: Path, *, previous: dict | None = None) -> dict:
    """Return a full in-memory checkpoint; caller separately freezes its bytes.

    A successor must retain every predecessor expectation. No writes occur, and
    malformed custody or missing older members prevents a new checkpoint.
    """
    root = root.resolve()
    with _registry_lock(root, writer=False) as locked:
        report = _scan(root, None, locked=locked)
        if report["integrity_status"] != "PASS":
            raise ValueError("cannot freeze invalid policy reading custody")
        rows = []
        for record in sorted(report["records"], key=lambda row: row["bundle"]):
            path = record["bundle"]
            rows.append({"bundle": path, "members": [
                {"path": path + "/" + name, "sha256": digest(_regular_bytes(root, path + "/" + name))}
                for name in MEMBERS]})
        if previous is not None:
            older = _load_chain(root, previous)[0]
            actual = {row["bundle"]: row for row in rows}
            for row in older["bundles"]:
                if canonical_bytes(actual.get(row["bundle"])) != canonical_bytes(row):
                    raise ValueError("cannot drop or alter a previously anchored bundle")
        return {"schema_version": 1, "kind": "POLICY_READING_INVENTORY",
                "directory": DIRECTORY, "previous": deepcopy(previous), "bundles": rows,
                "authority_effect": "NONE", "evidence_effect": "NONE", "qualification": "MODEL",
                "scope": "EXACT_OBSERVED_REGISTRY_CHECKPOINT_NOT_AUTHENTICATED_GLOBAL_HISTORY"}


def check_policy_inventory(root: Path, anchor: dict, request: dict | None = None) -> dict:
    """Compare all observed bundles against an externally retained exact anchor.

    The caller owns the trust decision for anchor. This check never chooses a
    latest file or treats a new unbound favorable inventory as authoritative.
    """
    root = root.resolve()
    with _registry_lock(root, writer=False) as locked:
        report = _scan(root, request, locked=locked)
        report["inventory_anchor"] = deepcopy(anchor)
        report["missing_expected_members"] = []
        report["unexpected_bundles"] = []
        report["inventory_completeness"] = "FAIL"
        try:
            inventory = _load_chain(root, anchor)[0]
            expected = {row["bundle"]: row for row in inventory["bundles"]}
            base = repository_path(root, DIRECTORY + "/bundles")
            actual = {path.relative_to(root).as_posix() for path in base.iterdir()} if base.exists() else set()
            report["unexpected_bundles"] = sorted(actual - set(expected))
            for bundle in expected.values():
                for ref in bundle["members"]:
                    try:
                        raw = _regular_bytes(root, ref["path"])
                        if digest(raw) != ref["sha256"]:
                            raise ValueError("anchored member hash differs")
                    except (OSError, ValueError) as exc:
                        report["missing_expected_members"].append({"expected": ref, "reason": str(exc)})
            if report["missing_expected_members"] or report["unexpected_bundles"]:
                report["findings"].append("registry differs from exact externally bound inventory")
            elif report["integrity_status"] == "PASS":
                report["inventory_completeness"] = "PASS_EXACT_EXTERNALLY_BOUND_CHECKPOINT"
        except (OSError, ValueError, KeyError, TypeError) as exc:
            report["findings"].append(f"inventory anchor: {exc}")
        report["limitations"].extend([
            "Anchor trust comes from the selecting owner, not its filename or this function.",
            "This checkpoint does not detect omissions predating its first trusted binding.",
            "Missing raw declarations cannot be reconstructed from hashes; their absence remains explicit failure."])
        return _finish(report)
