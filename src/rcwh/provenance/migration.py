"""Reviewed carrier/locator changes with an unchanged evidence graph."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any

import yaml

from ..assets import AssetCatalog, AssetError, CatalogStore
from ..assets.ingest import AssetIntake
from ..assets.paths import repository_path
from ..assets.transactions import commit_unlocked, digest, recover_unlocked
from ..corpus.extraction import canonical_bytes
from ..corpus.locators import SourceLocatorVerifier, source_digest
from ..graph import ProvenanceGraph
from ..schema import validate_instance
from .repository import ProvenanceRepository


REPRESENTATION_FIELDS = {"container", "carrier_capture", "locator", "legacy_locator", "locator_verification"}


def evidence_snapshot(graph: ProvenanceGraph) -> dict[str, Any]:
    return {
        "sources": {
            key: {name: value for name, value in record.items() if name not in REPRESENTATION_FIELDS}
            for key, record in graph.sources.items()
        },
        **{name: getattr(graph, name) for name in ("claims", "decisions", "implementations", "title_axes")},
    }


class SourceClosureMigration:
    def __init__(self, root: Path):
        self.root = root.resolve()

    def propose(self, bindings: list[dict[str, Any]]) -> dict[str, Any]:
        errors = validate_instance(bindings, self.root / "schemas/source_migration_plan.schema.json")
        if errors:
            raise AssetError("INVALID_MIGRATION_PLAN: " + "; ".join(errors))
        repository = ProvenanceRepository.from_repo(self.root)
        graph = repository.graph
        if len(bindings) != len(graph.sources) or {item["source_id"] for item in bindings} != set(graph.sources):
            raise AssetError("MIGRATION_ROOT_SET_MISMATCH: include every current Source exactly once")
        if graph.validate_integrity() or repository.validate_assets():
            raise AssetError("invalid provenance before migration")
        before = deepcopy(graph.sources)
        after = deepcopy(before)
        verifier = SourceLocatorVerifier(repository.catalog)
        results = []
        for binding in sorted(bindings, key=lambda item: item["source_id"]):
            source = after[binding["source_id"]]
            if source_digest(source) != binding["before_sha256"]:
                raise AssetError(f"STALE_MIGRATION_INPUT: {source['id']}")
            container = repository.catalog.resolve(binding["container_ref"])
            source["container"] = {"ref": container.id, "sha256": container.sha256}
            if "capture_ref" in binding:
                if binding["capture_ref"] is None:
                    # A locally authored transcription has no HTTP response of
                    # its own. The old capture remains in before_sources.
                    source.pop("carrier_capture", None)
                else:
                    capture = repository.catalog.resolve(binding["capture_ref"])
                    source["carrier_capture"] = {"ref": capture.id, "sha256": capture.sha256}
            findings = repository.capture_findings(source)
            if findings:
                raise AssetError("; ".join(findings))
            proposal = verifier.locate(
                source, binding["extraction_ref"],
                allow_line_break_spans=binding.get("allow_line_break_spans", False),
            )
            source["locator_verification"] = {"status": "UNVERIFIED", "reason": "; ".join(proposal["findings"]) or "Awaiting registration of actual verification report."}
            if proposal["status"] == "PASS":
                source.setdefault("legacy_locator", deepcopy(source["locator"]))
                source["locator"] = proposal["locator"]
                report = verifier.verify(source)
                if report["status"] != "PASS":
                    raise AssetError("proposed locator failed recomputation")
                manifest, units = verifier.extraction(binding["extraction_ref"])
                spans = source["locator"]["spans"]
                omitted = []
                for left, right in zip(spans, spans[1:]):
                    if left["unit_ref"] != right["unit_ref"]:
                        raise AssetError("unexpected cross-unit migration proposal")
                    text = units[left["unit_ref"]]["text"][left["end"]:right["start"]]
                    if not text or any(char != "\n" for char in text):
                        raise AssetError("migration may only omit explicit PDF LF breaks")
                    omitted.append({"unit_ref": left["unit_ref"], "start": left["end"], "end": right["start"], "text": text})
                results.append({"source_id": source["id"], "status": "PASS", "verification_report": report, "omitted_line_breaks": omitted})
            else:
                results.append({"source_id": source["id"], "status": "PENDING_EXCERPT_REVIEW", "extraction_ref": binding["extraction_ref"], "findings": proposal["findings"]})
        changed = deepcopy(graph)
        changed.sources = after
        semantic = evidence_snapshot(graph)
        if semantic != evidence_snapshot(changed):
            raise AssetError("MIGRATION_SEMANTIC_CHANGE")
        return {
            "schema_version": 1, "status": "PROPOSED", "bindings": bindings,
            "before_sources": before, "after_sources": after, "evidence_snapshot": semantic,
            "evidence_sha256": digest(canonical_bytes(semantic)), "results": results,
            "verification_status": "PASS" if all(item["status"] == "PASS" for item in results) else "PARTIAL",
            "authority_effect": "NONE",
        }

    def apply(self, proposal: dict[str, Any], *, audit_path: str) -> dict[str, Any]:
        target = repository_path(self.root, audit_path)
        if not audit_path.startswith("artifacts/migration/") or target.exists():
            raise AssetError("migration audit must use a new path under artifacts/migration/")
        # Rebuild the proposal before registering reports; caller snapshots cannot grant approval.
        fresh = self.propose(proposal["bindings"])
        if fresh != proposal:
            raise AssetError("STALE_MIGRATION_PROPOSAL")
        after = deepcopy(proposal["after_sources"])
        cache = self.root / ".rcwh-cache/source-migration-reports"
        cache.mkdir(parents=True, exist_ok=True)
        for result in proposal["results"]:
            if result["status"] != "PASS":
                continue
            report = result["verification_report"]
            previous = proposal["before_sources"][result["source_id"]].get("locator_verification", {})
            if previous.get("status") == "VERIFIED" and previous.get("source_record_sha256") == report["source_record_sha256"]:
                catalog = AssetCatalog.from_repo(self.root)
                stored = catalog.resolve(previous["report_ref"])
                if stored.sha256 == previous["report_sha256"] and json.loads(stored.path.read_bytes()) == report:
                    after[result["source_id"]]["locator_verification"] = deepcopy(previous)
                    continue
            raw = canonical_bytes(report)
            path = cache / f"{digest(raw)}.json"
            path.write_bytes(raw)
            receipt = AssetIntake(self.root).ingest(
                path, origin=f"source-verification:{result['source_id']}", kind="REVIEW_RECORD",
                receipt_key=f"source-verification:{digest(raw)}",
            )
            after[result["source_id"]]["locator_verification"] = {
                "status": "VERIFIED", "reason": "Exact excerpt recomputed from fixed carrier; omitted PDF line breaks recorded in migration audit.",
                "report_ref": receipt["asset_ref"], "report_sha256": receipt["sha256"],
                "source_record_sha256": report["source_record_sha256"],
            }
        store = CatalogStore(self.root)
        with store.lock(exclusive=True):
            recover_unlocked(store)
            current = ProvenanceGraph.from_repo(self.root)
            if current.sources != proposal["before_sources"] or evidence_snapshot(current) != proposal["evidence_snapshot"]:
                raise AssetError("STALE_MIGRATION_INPUT")
            current.sources = after
            if current.validate_integrity() or evidence_snapshot(current) != proposal["evidence_snapshot"]:
                raise AssetError("MIGRATION_SEMANTIC_CHANGE")
            assets, origins = store.read_unlocked()
            repository = ProvenanceRepository(current, AssetCatalog(self.root, assets, origins))
            if repository.validate_assets():
                raise AssetError("invalid migration bindings")
            verifier = SourceLocatorVerifier(repository.catalog)
            for result in proposal["results"]:
                if result["status"] == "PASS" and verifier.verify(after[result["source_id"]])["status"] != "PASS":
                    raise AssetError("registered verification report failed")
            changes = {}
            for path in sorted((self.root / "data/provenance/sources").glob("*.yaml")):
                document = yaml.safe_load(path.read_bytes())
                document["sources"] = [after[source["id"]] for source in document["sources"]]
                changes[path.relative_to(self.root).as_posix()] = yaml.safe_dump(document, allow_unicode=True, sort_keys=False).encode("utf-8")
            audit = {**proposal, "status": "APPLIED", "after_sources": after}
            if target.exists():
                raise AssetError("migration audit path already exists")
            changes[audit_path] = canonical_bytes(audit)
            commit_unlocked(store, changes)
        return audit
