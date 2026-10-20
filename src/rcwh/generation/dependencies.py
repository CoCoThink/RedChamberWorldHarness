"""Selected writing material; catalog layout and audit ledgers are not context.

Record identities bind selected Source/Claim/Asset objects instead of the YAML
shards containing them. Typed local references and asset ancestry are followed.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from ..assets.paths import repository_path
from ..candidate_reviews import canonical_bytes, digest
from ..io import load_data
from .records import bound_bytes


class WritingDependencies:
    def __init__(self, root: Path, catalog, graph):
        self.root, self.catalog, self.graph = root, catalog, graph
        self.files: set[str] = set()
        self.records: dict[tuple[str, str], dict] = {}

    def record(self, kind: str, value: dict) -> None:
        identity = value["id"]
        key = (kind, identity)
        row = {"kind": kind, "id": identity, "sha256": digest(canonical_bytes(value)), "value": deepcopy(value)}
        if key in self.records:
            if self.records[key] != row:
                raise ValueError(f"conflicting selected writing record: {identity}")
            return
        self.records[key] = row
        self.walk(value)
        if kind == "CLAIM":
            for edge in value.get("support", []):
                source = edge["source"]
                if source in self.graph.sources:
                    self.record("SOURCE", self.graph.sources[source])

    def file(self, ref: dict) -> None:
        bound_bytes(self.root, ref)
        self.files.add(ref["path"])

    def asset(self, identity: str) -> None:
        key = ("ASSET", identity)
        if key in self.records:
            return
        asset = self.catalog.resolve(identity)
        value = self.catalog.assets[identity]
        self.record("ASSET", {"id": identity, "sha256": asset.sha256,
                              "derived_from": sorted(value.get("derived_from", []))})
        self.file({"path": asset.path.relative_to(self.root).as_posix(), "sha256": asset.sha256})
        if asset.path.suffix in {".json", ".yaml", ".yml"}:
            # An immutable producer manifest describes an earlier toolchain.
            # Its old lock/config path is not a binding to today's file at that
            # path. Follow registered content identities and declared ancestry.
            self.asset_references(load_data(asset.path))
        for parent in value.get("derived_from", []):
            self.asset(parent)

    def asset_references(self, value) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if key not in {"origin", "origin_container", "original_path", "url", "retrieved_from"}:
                    self.asset_references(child)
        elif isinstance(value, list):
            for child in value:
                self.asset_references(child)
        elif isinstance(value, str) and value.startswith("asset:"):
            if value in getattr(self.catalog, "assets", {}):
                self.asset(value)

    def walk(self, value) -> None:
        if isinstance(value, dict):
            if isinstance(value.get("path"), str) and isinstance(value.get("sha256"), str):
                self.file({"path": value["path"], "sha256": value["sha256"]})
            for key, child in value.items():
                if key in {"origin", "origin_container", "original_path", "url", "retrieved_from"}:
                    continue
                self.walk(child)
        elif isinstance(value, list):
            for child in value:
                self.walk(child)
        elif isinstance(value, str) and value.startswith("asset:"):
            # Unregistered supplementary references remain explicitly unresolved.
            if value in getattr(self.catalog, "assets", {}):
                self.asset(value)

    def selected(self, package: dict, report: dict) -> None:
        for selected in package.get("assets", []):
            self.asset(selected["asset_ref"])
        for selected in package["sources"]:
            self.record("SOURCE", self.graph.sources[selected["source_ref"]])
        for selected in package.get("research_source_sets", []):
            self.file(selected)
            spec = load_data(repository_path(self.root, selected["path"]))
            for field in ("source_bindings", "claim_bindings", "reading_refs", "asset_bindings"):
                self.walk(spec.get(field, []))
        for supplement in report.get("supplemental_source_sets", []):
            for kind in ("sources", "claims"):
                for record in supplement["records"][kind]:
                    self.record("SOURCE" if kind == "sources" else "CLAIM", record)

    def manifest_records(self) -> list[dict]:
        return [self.records[key] for key in sorted(self.records)]


def without_governance(task: dict) -> dict:
    """Versioned v2 context: readiness is observed outside the author prompt."""
    result = deepcopy(task)
    result.pop("input_readiness", None)
    for supplement in result.get("supplemental_source_sets", []):
        supplement.pop("paths", None)
    return result
