"""Explicit legacy custody migration and current writing-input compatibility.

Migration appends a receipt; it never changes a request, draft, author or prose.
Unmigrated v1 drafts retain their original strict verification behavior.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

from ..assets.paths import repository_path
from ..candidate_reviews import canonical_bytes, digest
from ..schema import validate_instance
from .records import append_bytes, binding, bound_bytes
from .snapshots import InputSnapshot, freeze_inputs

HISTORY_DIRECTORY = "data/writing/history"


def receipt_path(draft: dict) -> str:
    return f"{HISTORY_DIRECTORY}/{digest(canonical_bytes(draft))}.json"


def legacy_receipt(root: Path, draft: dict) -> dict | None:
    path = repository_path(root, receipt_path(draft))
    if not path.exists():
        return None
    receipt = json.loads(path.read_bytes())
    errors = validate_instance(receipt, root / "schemas/writing_history.schema.json")
    if errors:
        raise ValueError("invalid writing history receipt: " + "; ".join(errors))
    if bound_bytes(root, receipt["draft"]) != canonical_bytes(draft):
        raise ValueError("writing history receipt draft identity mismatch")
    basis = receipt["compatibility_basis"]
    if basis is not None:
        from .dependencies import without_governance
        from .session import _runtime_observations
        prepared = json.loads(bound_bytes(root, draft["prepared_request"]))
        normalized, _ = _runtime_observations(without_governance(prepared["task"]), basis["task"])
        if basis["context"] != prepared["context"] or canonical_bytes(normalized) != canonical_bytes(basis["task"]):
            raise ValueError("writing history compatibility basis differs from original request")
    return receipt


def snapshot_for_draft(root: Path, draft: dict) -> InputSnapshot | None:
    if draft["schema_version"] == 2:
        return InputSnapshot(root, draft["input_snapshot"])
    receipt = legacy_receipt(root, draft)
    return InputSnapshot(root, receipt["input_snapshot"]) if receipt is not None else None


def session_refs(prepared: dict, run: dict) -> list[dict]:
    return [ref for ref in [*prepared["inputs"], prepared["template"], prepared["package"],
                           prepared["parent"], prepared["feedback"], run["request_source"], run["imported_text"]]
            if ref is not None]


def historical_artifact_paths(root: Path, draft: dict, *, _seen: set[str] | None = None) -> set[str]:
    """Physical closure uses blobs, never historical logical paths or old assets."""
    from .writing import load_draft

    key = digest(canonical_bytes(draft))
    seen = set() if _seen is None else _seen
    if key in seen:
        raise ValueError("writing historical artifact lineage cycle")
    seen.add(key)
    snapshot = snapshot_for_draft(root, draft)
    if snapshot is None:
        raise ValueError("historical artifact closure requires a writing snapshot")
    snapshot.verify()
    paths = {snapshot.ref["path"], draft["run"]["path"], draft["candidate"]["path"]}
    paths.update(ref["path"] for ref in snapshot.entries.values())
    for field in ("prepared_request", "raw_run"):
        if field in draft:
            bound_bytes(root, draft[field])
            paths.add(draft[field]["path"])
    if draft["schema_version"] == 1:
        paths.add(receipt_path(draft))
    if draft["parent"] is not None:
        bound_bytes(root, draft["parent"])
        parent, _ = load_draft(root, draft["parent"]["path"])
        paths.add(draft["parent"]["path"])
        paths.update(historical_artifact_paths(root, parent, _seen=seen))
    return paths


def compatibility_basis(rendered: dict, context: dict) -> dict:
    return {"renderer_version": 2, "context": deepcopy(context), "task": deepcopy(rendered["task"]),
            "inputs": deepcopy(rendered["inputs"]), "dependency_records": deepcopy(rendered["dependency_records"])}


def freeze_history(root: Path, relative: str, *, _seen: set[str] | None = None) -> dict:
    """Freeze a currently verifiable v1 lineage before mutable inputs move on."""
    from .session import EXECUTION_BASIS, _render_context, verify_prepared_request
    from .writing import load_draft

    draft_ref = binding(root, relative)
    seen = set() if _seen is None else _seen
    if draft_ref["sha256"] in seen:
        raise ValueError("writing history lineage cycle")
    seen.add(draft_ref["sha256"])
    draft = json.loads(bound_bytes(root, draft_ref))
    if draft["schema_version"] == 2:
        load_draft(root, relative)
        return {"status": "PASS", "draft": draft_ref, "input_snapshot": draft["input_snapshot"], "migration": "NOT_NEEDED"}
    existing = legacy_receipt(root, draft)
    if existing is not None:
        load_draft(root, relative)
        return {"status": "PASS", "draft": draft_ref, "receipt": binding(root, receipt_path(draft)),
                "input_snapshot": existing["input_snapshot"], "migration": "ALREADY_FROZEN"}
    # Check original semantics before appending a receipt, not after selecting a
    # less restrictive dependency set. No stale-input exception is waived.
    load_draft(root, relative)
    if draft.get("execution_basis") != EXECUTION_BASIS:
        raise ValueError("legacy history migration requires a session-authored draft")
    if draft["parent"] is not None:
        freeze_history(root, draft["parent"]["path"], _seen=seen)
    run = json.loads(bound_bytes(root, draft["run"]))
    prepared = json.loads(bound_bytes(root, run["prepared_request"]))
    verify_prepared_request(root, prepared)
    basis = None
    if prepared["context"]["operation"] == "draft":
        basis = compatibility_basis(_render_context(root, prepared["context"], version=2), prepared["context"])
    snapshot = freeze_inputs(root, session_refs(prepared, run))
    receipt = {"schema_version": 1, "kind": "WRITING_HISTORY_MIGRATION", "draft": draft_ref,
               "input_snapshot": snapshot, "compatibility_basis": basis,
               "validation": "V1_FRESH_RENDERER_AND_EXACT_INPUT_BYTES", "authority_effect": "NONE"}
    ref = append_bytes(root, receipt_path(draft), canonical_bytes(receipt))
    load_draft(root, relative)
    return {"status": "PASS", "draft": draft_ref, "receipt": ref, "input_snapshot": snapshot,
            "migration": "FROZEN_WITHOUT_REWRITING"}


def current_compatibility(root: Path, relative: str) -> dict:
    from .session import _render_context, _runtime_observations
    from .writing import load_draft

    result = {"status": "FAIL", "scope": "CURRENT_WRITING_INPUT_COMPATIBILITY", "compatibility": "NOT_CHECKED",
              "changed_inputs": [], "changed_records": [], "findings": [], "authority_effect": "NONE"}
    seen = set()
    try:
        while True:
            ref = binding(root, relative)
            if ref["sha256"] in seen:
                raise ValueError("writing compatibility lineage cycle")
            seen.add(ref["sha256"])
            draft, _ = load_draft(root, relative)
            if draft["parent"] is None:
                break
            relative = draft["parent"]["path"]
        if draft["schema_version"] == 2 and "prepared_request" in draft:
            prepared = json.loads(bound_bytes(root, draft["prepared_request"]))
            basis = compatibility_basis(prepared, prepared["context"])
        elif draft["schema_version"] == 2 and "selection_context" in draft:
            basis = compatibility_basis(draft, draft["selection_context"])
        else:
            receipt = legacy_receipt(root, draft)
            basis = receipt["compatibility_basis"] if receipt is not None else None
        if basis is None:
            result["findings"] = ["NO_VERSIONED_COMPATIBILITY_BASIS: freeze legacy session history first"]
            return result
        for ref in basis["inputs"] + [draft["template"]]:
            try:
                bound_bytes(root, ref)
            except (OSError, ValueError):
                result["changed_inputs"].append(ref["path"])
        fresh = _render_context(root, basis["context"], version=2)
        normalized, variations = _runtime_observations(basis["task"], fresh["task"])
        same = (canonical_bytes(normalized) == canonical_bytes(fresh["task"])
                and basis["inputs"] == fresh["inputs"] and basis["dependency_records"] == fresh["dependency_records"]
                and draft["template"] == fresh["template"])
        before = {row["path"]: row["sha256"] for row in basis["inputs"] + [draft["template"]]}
        after = {row["path"]: row["sha256"] for row in fresh["inputs"] + [fresh["template"]]}
        old_records = {(r["kind"], r["id"]): r["sha256"] for r in basis["dependency_records"]}
        new_records = {(r["kind"], r["id"]): r["sha256"] for r in fresh["dependency_records"]}
        result.update(status="PASS" if same else "FAIL", compatibility="CURRENT" if same else "STALE",
                      changed_inputs=sorted(path for path in before.keys() | after.keys() if before.get(path) != after.get(path)),
                      changed_records=[{"kind": key[0], "id": key[1]} for key in sorted(old_records.keys() | new_records.keys())
                                       if old_records.get(key) != new_records.get(key)],
                      runtime_observation_variations=variations)
        if not same:
            result["findings"].append("CURRENT_WRITING_INPUTS_DIFFER: historical custody remains valid")
    except (OSError, KeyError, TypeError, ValueError) as exc:
        result.update(compatibility="STALE", findings=[str(exc)])
    return result
