"""Content-addressed writing custody, independent of mutable repository paths.

Snapshots preserve bytes, not provider execution or literary qualification.
Creation checks live bindings; historical reads only use the declared blobs.
"""
from __future__ import annotations

import json
from pathlib import Path

from ..candidate_reviews import canonical_bytes, digest
from ..schema import validate_instance
from .records import append_bytes, bound_bytes

DIRECTORY = "artifacts/writing-inputs"


def publish(root: Path, directory: str, raw: bytes, suffix: str = "json") -> dict:
    from ..assets.paths import repository_path

    ref = {"path": f"{directory}/{digest(raw)}.{suffix}", "sha256": digest(raw)}
    path = repository_path(root, ref["path"])
    if path.exists():
        if bound_bytes(root, ref) != raw:
            raise ValueError("writing snapshot content collision")
        return ref
    try:
        return append_bytes(root, ref["path"], raw)
    except FileExistsError:
        if bound_bytes(root, ref) != raw:
            raise ValueError("writing snapshot content collision")
        return ref


def unique_refs(refs: list[dict | None]) -> list[dict]:
    selected = {}
    for ref in refs:
        if ref is None:
            continue
        key = (ref["path"], ref["sha256"])
        selected[key] = dict(ref)
    return [selected[key] for key in sorted(selected)]


class InputSnapshot:
    def __init__(self, root: Path, ref: dict):
        self.root, self.ref = root, ref
        self.document = json.loads(bound_bytes(root, ref))
        errors = validate_instance(self.document, root / "schemas/writing_input_snapshot.schema.json")
        if errors:
            raise ValueError("invalid writing input snapshot: " + "; ".join(errors))
        for record in self.document["records"]:
            if record["value"].get("id") != record["id"] or digest(canonical_bytes(record["value"])) != record["sha256"]:
                raise ValueError("writing snapshot record identity mismatch")
        self.entries = {}
        for entry in self.document["entries"]:
            original, blob = entry["original"], entry["blob"]
            key = (original["path"], original["sha256"])
            if key in self.entries:
                raise ValueError("duplicate writing snapshot input")
            if blob != blob_ref(original["sha256"]):
                raise ValueError("writing snapshot blob identity mismatch")
            self.entries[key] = blob

    def contains(self, ref: dict) -> bool:
        return (ref["path"], ref["sha256"]) in self.entries

    def read(self, ref: dict) -> bytes:
        from ..assets.paths import validate_relative_path

        validate_relative_path(ref["path"])
        key = (ref["path"], ref["sha256"])
        if key not in self.entries:
            raise ValueError(f"missing historical writing input: {ref['path']}")
        return bound_bytes(self.root, self.entries[key])

    def verify(self, expected: list[dict] | None = None) -> None:
        if expected is not None:
            actual = [entry["original"] for entry in self.document["entries"]]
            if actual != unique_refs(expected):
                raise ValueError("writing snapshot input manifest mismatch")
        for path, sha in self.entries:
            self.read({"path": path, "sha256": sha})


def blob_ref(sha: str) -> dict:
    return {"path": f"{DIRECTORY}/blobs/{sha}.bin", "sha256": sha}


def freeze_inputs(root: Path, refs: list[dict | None], *, inherited: InputSnapshot | None = None,
                  records: list[dict] | None = None) -> dict:
    """Publish a manifest last; memory is bounded by the largest input file.

    An interrupted capture can leave unreferenced blobs, never a complete draft
    or a manifest pretending that the missing inputs were captured.
    """
    selected = unique_refs(refs)
    entries = []
    for ref in selected:
        raw = inherited.read(ref) if inherited is not None and inherited.contains(ref) else bound_bytes(root, ref)
        blob = publish(root, f"{DIRECTORY}/blobs", raw, "bin")
        entries.append({"original": ref, "blob": blob})
    value = {"schema_version": 1, "kind": "WRITING_INPUT_SNAPSHOT", "entries": entries,
             "records": records or [], "authority_effect": "NONE"}
    return publish(root, f"{DIRECTORY}/manifests", canonical_bytes(value))
