from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any

from ..assets import AssetCatalog, AssetError
from ..graph import ProvenanceGraph
from ..schema import validate_instance
from ..corpus.extraction import canonical_bytes
from ..corpus.locators import SourceLocatorVerifier, source_digest


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
            errors.extend(f"{source['id']}: {finding}" for finding in self.capture_findings(source))
            errors.extend(f"{source['id']}: {finding}" for finding in self.revision_findings(source))
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
            if source["locator"].get("schema_version") == 2:
                findings = validate_instance(source["locator"], self.catalog.root / "schemas/locator_v2.schema.json")
                errors.extend(f"{source['id']}: invalid Locator v2: {finding}" for finding in findings)
                if not findings:
                    try:
                        self.catalog.resolve(source["locator"]["extraction_ref"])
                    except (AssetError, OSError) as exc:
                        errors.append(f"{source['id']}: invalid extraction asset: {exc}")
            declared = source.get("locator_verification", {})
            if "report_ref" in declared:
                try:
                    report_asset = self.catalog.resolve(declared["report_ref"])
                    if report_asset.sha256 != declared.get("report_sha256"):
                        errors.append(f"{source['id']}: verification report SHA disagrees with asset")
                except (AssetError, OSError) as exc:
                    errors.append(f"{source['id']}: invalid verification report asset: {exc}")
        for item in self.graph.implementations.values():
            locator = item["locator"]
            try:
                asset = self.catalog.resolve(locator["asset_ref"])
                if asset.sha256 != locator["file_sha256"]:
                    errors.append(f"{item['id']}: implementation SHA disagrees with asset")
            except (KeyError, AssetError, OSError) as exc:
                errors.append(f"{item['id']}: invalid implementation asset: {exc}")
        return errors

    def capture_findings(self, source: dict[str, Any]) -> list[str]:
        if "carrier_capture" not in source:
            return []
        try:
            binding = source["carrier_capture"]
            asset = self.catalog.resolve(binding["ref"])
            if asset.sha256 != binding["sha256"]:
                raise AssetError("CAPTURE_HASH_MISMATCH")
            capture = json.loads(asset.path.read_bytes())
            errors = validate_instance(capture, self.catalog.root / "schemas/source_capture.schema.json")
            if errors:
                raise AssetError("INVALID_SOURCE_CAPTURE: " + "; ".join(errors))
            if capture["carrier"] != source.get("container"):
                raise AssetError("CAPTURE_CARRIER_MISMATCH")
        except (AssetError, OSError, ValueError, KeyError) as exc:
            return [str(exc)]
        return []

    def revision_findings(self, source: dict[str, Any]) -> list[str]:
        from .corrections import revision_findings

        return revision_findings(self.graph, self.catalog, source)

    def source_report(
        self, source: dict[str, Any], *, locators: bool = False,
        verifier: SourceLocatorVerifier | None = None,
    ) -> dict[str, Any]:
        report: dict[str, Any] = {"source_id": source["id"], "findings": []}
        report["findings"].extend(self.capture_findings(source))
        revision_errors = self.revision_findings(source)
        report["findings"].extend(revision_errors)
        if "excerpt_revision" in source:
            report["excerpt_revision"] = {**source["excerpt_revision"], "status": "FAIL" if revision_errors else "PASS"}
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
        verification = source.get("locator_verification", {"status": "UNVERIFIED"})
        report["locator_verification"] = verification
        if locators:
            result = (verifier or SourceLocatorVerifier(self.catalog)).verify(source)
            report["declared_locator_verification"] = verification
            report["verification_report"] = result
            report["locator_verification"] = {
                "status": "VERIFIED" if result["status"] == "PASS" else (
                    "STALE" if any("STALE" in finding for finding in result["findings"]) else "UNVERIFIED"
                ),
                "reason": "Exact excerpt verified from reproducible extraction" if result["status"] == "PASS" else "; ".join(result["findings"]),
            }
            report["findings"].extend(result["findings"])
        report["status"] = "FAIL" if report["findings"] else "PASS"
        return report

    def check(self, *, locators: bool = False) -> dict[str, Any]:
        verifier = SourceLocatorVerifier(self.catalog) if locators else None
        reports = [
            self.source_report(s, locators=locators, verifier=verifier)
            for s in sorted(self.graph.sources.values(), key=lambda x: x["id"])
        ]
        errors = self.graph.validate_integrity() + self.validate_assets()
        if not reports:
            errors.append("EMPTY_ROOT_SET: source closure requires explicit source records")
        return {
            "profile": "source-locators" if locators else "source-content",
            "status": "PASS" if not errors and all(r["status"] == "PASS" for r in reports) else "FAIL",
            "roots": len(reports),
            "root_set_digest": hashlib.sha256(canonical_bytes([
                {"source_id": source["id"], "source_record_sha256": source_digest(source)}
                for source in sorted(self.graph.sources.values(), key=lambda item: item["id"])
            ])).hexdigest(),
            "local_containers": sum("asset" in r for r in reports),
            "unresolved_sources": sum(r["status"] != "PASS" for r in reports),
            "graph_findings": errors,
            "sources": reports,
        }

    def verify_all(self, *, require_tracked: bool = False) -> dict[str, Any]:
        report = self.check(locators=True)
        report["profile"] = "sources-verify-all"
        report["missing_carriers"] = sum("asset" not in source for source in report["sources"])
        report["unverified_locators"] = sum(source["locator_verification"]["status"] != "VERIFIED" for source in report["sources"])
        report["stale_locators"] = sum(source["locator_verification"]["status"] == "STALE" for source in report["sources"])
        findings = self.catalog.validate(require_tracked=require_tracked)
        if require_tracked:
            result = subprocess.run(["git", "ls-files", "-z"], cwd=self.catalog.root, capture_output=True, check=False)
            tracked = set(result.stdout.decode("utf-8").split("\0")) if result.returncode == 0 else set()
            required = {
                path.relative_to(self.catalog.root).as_posix()
                for path in (self.catalog.root / "data/provenance/sources").glob("*.yaml")
            }
            if any(source["locator"].get("schema_version") == 2 for source in self.graph.sources.values()):
                required.update({
                    "requirements/extraction.lock.json", "schemas/extraction_manifest.schema.json",
                    "schemas/extraction_unit.schema.json", "schemas/extraction_config.schema.json",
                    "schemas/locator_v2.schema.json", "schemas/source_locator_report.schema.json", "schemas/source.schema.json",
                })
            if any("carrier_capture" in source for source in self.graph.sources.values()):
                required.add("schemas/source_capture.schema.json")
            if any("excerpt_revision" in source for source in self.graph.sources.values()):
                required.add("schemas/source_excerpt_review.schema.json")
                required.update(
                    path.relative_to(self.catalog.root).as_posix()
                    for name in ("claims", "decisions", "implementations", "axes")
                    for path in (self.catalog.root / f"data/provenance/{name}").glob("*.yaml")
                )
            findings.extend(f"untracked source verification input: {path}" for path in sorted(required - tracked))
        if findings:
            report["storage_findings"] = findings
            report["status"] = "FAIL"
        return report

    def trace(self, node_id: str) -> dict[str, Any]:
        trace = self.graph.trace(node_id)
        sources = [trace["source"]] if "source" in trace else trace.get("sources", [])
        reports = [self.source_report(s) for s in sources]
        verifier = SourceLocatorVerifier(self.catalog)
        locator_reports = [self.source_report(s, locators=True, verifier=verifier) for s in sources]
        locator_status = "VERIFIED" if locator_reports and all(r["status"] == "PASS" for r in locator_reports) else (
            "UNVERIFIED" if all(s["locator"].get("schema_version") != 2 for s in sources) else "FAIL"
        )
        return {
            "node_id": node_id, "provenance": trace, "source_assets": reports,
            "content_status": "PASS" if all(r["status"] == "PASS" for r in reports) else "FAIL",
            "locator_status": locator_status, "source_locators": locator_reports,
        }
