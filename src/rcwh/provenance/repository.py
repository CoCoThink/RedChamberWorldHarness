from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Any

from ..assets import AssetCatalog, AssetError
from ..graph import ProvenanceGraph
from ..schema import validate_instance


@dataclass
class ProvenanceRepository:
    graph: ProvenanceGraph
    catalog: AssetCatalog

    @classmethod
    def from_repo(cls, root: Path) -> "ProvenanceRepository":
        graph = ProvenanceGraph.from_repo(root)
        if not graph.sources:
            raise AssetError("source profile has no roots in data/provenance/sources")
        for records, schema_name in (
            (graph.sources, "source"), (graph.claims, "claim"),
            (graph.decisions, "decision"), (graph.implementations, "implementation"),
            (graph.title_axes, "title_axis"),
        ):
            for item in records.values():
                errors = validate_instance(item, root / f"schemas/{schema_name}.schema.json")
                if errors:
                    raise AssetError(f"{item['id']}: invalid provenance schema: " + "; ".join(errors))
        return cls(graph, AssetCatalog.from_repo(root))

    def validate_assets(self) -> list[str]:
        """Validate declared bindings, without pretending citations are local files."""
        errors = []
        for source in self.graph.sources.values():
            actual = hashlib.sha256(source["text"].encode("utf-8")).hexdigest()
            if actual != source["text_sha256"]:
                errors.append(f"{source['id']}: excerpt hash mismatch")
            if "container" in source:
                try:
                    asset = self.catalog.resolve(source["container"]["ref"])
                    if asset.sha256 != source["container"]["sha256"]:
                        errors.append(f"{source['id']}: container SHA disagrees with asset")
                except (AssetError, OSError) as exc:
                    errors.append(f"{source['id']}: {exc}")
        for item in self.graph.implementations.values():
            locator = item["locator"]
            try:
                asset = self.catalog.resolve(locator["asset_ref"])
                if asset.sha256 != locator["file_sha256"]:
                    errors.append(f"{item['id']}: implementation SHA disagrees with asset")
            except (KeyError, AssetError, OSError) as exc:
                errors.append(f"{item['id']}: invalid implementation asset: {exc}")
        return errors

    def source_report(self, source: dict[str, Any], *, locators: bool = False) -> dict[str, Any]:
        report: dict[str, Any] = {"source_id": source["id"], "findings": []}
        if "container" not in source:
            report["findings"].append("MISSING_LOCAL_CONTAINER: bibliography is not a local carrier")
        else:
            try:
                asset = self.catalog.resolve(source["container"]["ref"])
                report["asset"] = asset.summary()
                if asset.sha256 != source["container"]["sha256"]:
                    report["findings"].append("CONTAINER_HASH_MISMATCH")
            except (AssetError, OSError) as exc:
                report["findings"].append(str(exc))
        if hashlib.sha256(source["text"].encode("utf-8")).hexdigest() != source["text_sha256"]:
            report["findings"].append("EXCERPT_HASH_MISMATCH")
        report["locator"] = source["locator"]
        # A migrated page/line assertion is not a verified extraction alignment.
        verification = source.get("locator_verification", {"status": "UNVERIFIED"})
        report["locator_verification"] = verification
        if locators:
            report["findings"].append(
                "LOCATOR_VERIFICATION_NOT_IMPLEMENTED: page/text alignment still requires corpus tooling"
            )
        report["status"] = "FAIL" if report["findings"] else "PASS"
        return report

    def check(self, *, locators: bool = False) -> dict[str, Any]:
        reports = [
            self.source_report(s, locators=locators)
            for s in sorted(self.graph.sources.values(), key=lambda x: x["id"])
        ]
        errors = self.graph.validate_integrity() + self.validate_assets()
        if not reports:
            errors.append("EMPTY_ROOT_SET: source closure requires explicit source records")
        return {
            "profile": "source-locators" if locators else "source-content",
            "status": "PASS" if not errors and all(r["status"] == "PASS" for r in reports) else "FAIL",
            "roots": len(reports),
            "local_containers": sum("asset" in r for r in reports),
            "unresolved_sources": sum(r["status"] != "PASS" for r in reports),
            "graph_findings": errors,
            "sources": reports,
        }

    def trace(self, node_id: str) -> dict[str, Any]:
        trace = self.graph.trace(node_id)
        sources = [trace["source"]] if "source" in trace else trace.get("sources", [])
        reports = [self.source_report(s) for s in sources]
        return {
            "node_id": node_id, "provenance": trace, "source_assets": reports,
            "content_status": "PASS" if all(r["status"] == "PASS" for r in reports) else "FAIL",
            "locator_status": "UNVERIFIED",
        }
