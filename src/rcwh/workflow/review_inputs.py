"""Content-addressed custody of the exact inputs of a registered opinion."""
from __future__ import annotations

import json
from pathlib import Path

from ..assets.paths import repository_path
from ..candidate_reviews import canonical_bytes, digest


def capture(root: Path, files: dict[tuple[str, str], bytes]) -> tuple[dict, dict[str, bytes]]:
    writes, rows = {}, []
    for (path, sha), raw in sorted(files.items()):
        repository_path(root, path)
        if digest(raw) != sha:
            raise ValueError("review snapshot input digest mismatch")
        blob = {"path": f"data/agent_panel/blobs/{sha}", "sha256": sha}
        writes[blob["path"]] = raw
        rows.append({"original": {"path": path, "sha256": sha}, "snapshot": blob})
    raw = canonical_bytes({"schema_version": 1, "kind": "REVIEW_INPUT_SNAPSHOT", "files": rows})
    binding = {"path": f"data/agent_panel/snapshots/{digest(raw)}.json", "sha256": digest(raw)}
    writes[binding["path"]] = raw
    return binding, writes


def reader(root: Path, binding: dict):
    def bound(ref):
        raw = repository_path(root, ref["path"]).read_bytes()
        if digest(raw) != ref["sha256"]:
            raise ValueError(f"review snapshot digest mismatch: {ref['path']}")
        return raw
    if binding["path"] != f"data/agent_panel/snapshots/{binding['sha256']}.json":
        raise ValueError("non-content-addressed review snapshot")
    value = json.loads(bound(binding))
    if set(value) != {"schema_version", "kind", "files"} or value["schema_version"] != 1 or value["kind"] != "REVIEW_INPUT_SNAPSHOT":
        raise ValueError("invalid review input snapshot")
    files = {}
    for row in value["files"]:
        original, blob = row["original"], row["snapshot"]
        key = (original["path"], original["sha256"])
        repository_path(root, original["path"])
        if (key in files or set(row) != {"original", "snapshot"} or set(original) != {"path", "sha256"}
                or blob != {"path": f"data/agent_panel/blobs/{key[1]}", "sha256": key[1]}):
            raise ValueError("invalid or duplicate review snapshot entry")
        files[key] = bound(blob)
    def read(ref):
        try:
            return files[(ref["path"], ref["sha256"])]
        except KeyError as exc:
            raise ValueError(f"review input missing from snapshot: {ref['path']}") from exc
    return read
