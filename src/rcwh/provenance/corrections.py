"""Explicit excerpt corrections, separate from representation-only migration.

Text comes only from reproducible spans. Documented claim judgments are supplied
by a named reviewer; the service checks their scope and freshness, not their truth.
"""
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


CORRECTION_FIELDS = {"text", "text_sha256", "locator", "legacy_locator", "locator_verification", "excerpt_revision"}


def protected_snapshot(graph: ProvenanceGraph) -> dict[str, Any]:
    return {
        "sources": {
            key: {name: value for name, value in record.items() if name not in CORRECTION_FIELDS}
            for key, record in graph.sources.items()
        },
        **{name: getattr(graph, name) for name in ("claims", "decisions", "implementations", "title_axes")},
    }


def source_impact(graph: ProvenanceGraph, source_id: str) -> dict[str, Any]:
    trace = graph.trace(source_id)
    decision_ids = {item["id"] for item in trace["decisions"]}
    implementation_ids = {
        reference for item in trace["decisions"] for reference in item.get("implementation_refs", [])
    }
    trace["implementations"] = [
        item for item in graph.implementations.values()
        if item["id"] in implementation_ids or decision_ids.intersection(item.get("decision_refs", []))
    ]
    implementation_ids.update(item["id"] for item in trace["implementations"])
    claim_ids = {item["id"] for item in trace["claims"]}
    trace["title_axes"] = [
        item for item in graph.title_axes.values()
        if claim_ids.intersection(item.get("claim_refs", []))
        or decision_ids.intersection({item.get("placement_decision_ref"), item.get("formal_title_decision_ref")})
        or implementation_ids.intersection(item.get("implementation_refs", []))
    ]
    return {
        name: sorted(trace[name], key=lambda item: item["id"])
        for name in ("claims", "decisions", "implementations", "title_axes")
    }


def revision_findings(graph: ProvenanceGraph, catalog: AssetCatalog, source: dict[str, Any]) -> list[str]:
    """A revised excerpt must keep its immutable review and current impact binding."""
    if "excerpt_revision" not in source:
        return []
    try:
        binding = source["excerpt_revision"]
        asset = catalog.resolve(binding["ref"])
        if asset.sha256 != binding["sha256"] or catalog.assets[asset.id]["kind"] != "REVIEW_RECORD":
            raise AssetError("CORRECTION_REVIEW_ASSET_MISMATCH")
        review = json.loads(asset.path.read_bytes())
        errors = validate_instance(review, catalog.root / "schemas/source_excerpt_review.schema.json")
        if errors:
            raise AssetError("INVALID_EXCERPT_REVIEW: " + "; ".join(errors))
        before = review["before_source"]
        if (
            review["source_id"] != source["id"] or before["id"] != source["id"]
            or source_digest(before) != review["before_sha256"]
            or review["before_sha256"] != binding["previous_source_sha256"]
        ):
            raise AssetError("CORRECTION_PREDECESSOR_MISMATCH")
        if review["after_excerpt"] != {key: source[key] for key in ("text", "text_sha256", "locator")}:
            raise AssetError("STALE_CORRECTION_EXCERPT")
        operation = review.get("operation", "REPLACE_EXCERPT")
        if (before["text"] == source["text"]) != (operation == "REFRESH_IMPACT_REVIEW"):
            raise AssetError("CORRECTION_OPERATION_MISMATCH")
        if (
            {key: value for key, value in before.items() if key not in CORRECTION_FIELDS}
            != {key: value for key, value in source.items() if key not in CORRECTION_FIELDS}
        ):
            raise AssetError("CORRECTION_AUTHORITY_CHANGE")
        impact = source_impact(graph, source["id"])
        if review["impact"] != impact or review["impact_sha256"] != digest(canonical_bytes(impact)):
            raise AssetError("STALE_CORRECTION_IMPACT_REVIEW")
        validate_claim_reviews(impact, review["claim_reviews"])
    except (AssetError, OSError, ValueError, KeyError, TypeError) as exc:
        return [str(exc)]
    return []


def validate_claim_reviews(impact: dict[str, Any], reviews: list[dict[str, Any]]) -> None:
    claims = {claim["id"]: claim for claim in impact["claims"]}
    if len(reviews) != len(claims) or {review["claim_id"] for review in reviews} != set(claims):
        raise AssetError("CORRECTION_CLAIM_REVIEW_SCOPE_MISMATCH")
    for review in reviews:
        if review["claim_sha256"] != digest(canonical_bytes(claims[review["claim_id"]])):
            raise AssetError("STALE_CORRECTION_CLAIM_REVIEW")


class SourceExcerptCorrection:
    def __init__(self, root: Path):
        self.root = root.resolve()

    def propose(self, plan: dict[str, Any]) -> dict[str, Any]:
        from .repository import ProvenanceRepository

        errors = validate_instance(plan, self.root / "schemas/source_excerpt_correction_plan.schema.json")
        if errors:
            raise AssetError("INVALID_CORRECTION_PLAN: " + "; ".join(errors))
        repository = ProvenanceRepository.from_repo(self.root)
        graph = repository.graph
        ids = [item["source_id"] for item in plan["corrections"]]
        if len(set(ids)) != len(ids) or not set(ids).issubset(graph.sources):
            raise AssetError("INVALID_CORRECTION_SOURCE_SET")
        refreshable = {
            source_id for source_id in ids
            if repository.revision_findings(graph.sources[source_id]) == ["STALE_CORRECTION_IMPACT_REVIEW"]
        }
        allowed_findings = {f"{source_id}: STALE_CORRECTION_IMPACT_REVIEW" for source_id in refreshable}
        if graph.validate_integrity() or set(repository.validate_assets()) - allowed_findings:
            raise AssetError("invalid provenance before excerpt correction")
        before, after = deepcopy(graph.sources), deepcopy(graph.sources)
        verifier = SourceLocatorVerifier(repository.catalog)
        results = []
        for item in sorted(plan["corrections"], key=lambda record: record["source_id"]):
            old = before[item["source_id"]]
            if source_digest(old) != item["before_sha256"]:
                raise AssetError("STALE_CORRECTION_INPUT: " + old["id"])
            locator = item["locator"]
            errors = validate_instance(locator, self.root / "schemas/locator_v2.schema.json")
            if errors:
                raise AssetError("INVALID_CORRECTION_LOCATOR: " + "; ".join(errors))
            manifest, units = verifier.extraction(locator["extraction_ref"])
            chunks, omitted = [], []
            previous = None
            for span in locator["spans"]:
                unit = units.get(span["unit_ref"])
                if unit is None or not 0 <= span["start"] < span["end"] <= len(unit["text"]):
                    raise AssetError("INVALID_CORRECTION_SPAN")
                if previous:
                    if previous["unit_ref"] != span["unit_ref"] or previous["end"] > span["start"]:
                        raise AssetError("CORRECTION_REQUIRES_CONTIGUOUS_EXCERPT")
                    gap = unit["text"][previous["end"]:span["start"]]
                    if gap and (manifest["config"]["format"] != "PDF" or any(char != "\n" for char in gap)):
                        raise AssetError("CORRECTION_UNDECLARED_CONTENT_OMISSION")
                    omitted.append({"unit_ref": span["unit_ref"], "start": previous["end"], "end": span["start"], "text": gap})
                chunks.append(unit["text"][span["start"]:span["end"]])
                previous = span
            if locator["joiner"] != "":
                raise AssetError("CORRECTION_REQUIRES_CONTIGUOUS_EXCERPT")
            text = "".join(chunks)
            if text == old["text"] and old["id"] not in refreshable:
                raise AssetError("CORRECTION_TEXT_UNCHANGED: use representation-only migration")
            source = after[old["id"]]
            source.setdefault("legacy_locator", deepcopy(old["locator"]))
            source.update(text=text, text_sha256=digest(text.encode("utf-8")), locator=deepcopy(locator))
            source["locator_verification"] = {"status": "UNVERIFIED", "reason": "New excerpt revision requires actual verification."}
            impact = source_impact(graph, old["id"])
            validate_claim_reviews(impact, item["claim_reviews"])
            review = {
                "schema_version": 1, "kind": "SOURCE_EXCERPT_CORRECTION", "source_id": old["id"],
                "operation": "REFRESH_IMPACT_REVIEW" if text == old["text"] else "REPLACE_EXCERPT",
                "before_source": old, "before_sha256": item["before_sha256"],
                "after_excerpt": {key: source[key] for key in ("text", "text_sha256", "locator")},
                "reviewer": plan["reviewer"], "rationale": item["rationale"], "limitations": item["limitations"],
                "claim_reviews": item["claim_reviews"], "impact": impact,
                "impact_sha256": digest(canonical_bytes(impact)), "omitted_line_breaks": omitted,
            }
            errors = validate_instance(review, self.root / "schemas/source_excerpt_review.schema.json")
            if errors:
                raise AssetError("INVALID_EXCERPT_REVIEW: " + "; ".join(errors))
            sha = digest(canonical_bytes(review))
            source["excerpt_revision"] = {"ref": "asset:sha256:" + sha, "sha256": sha, "previous_source_sha256": item["before_sha256"]}
            report = verifier.verify(source)
            if report["status"] != "PASS":
                raise AssetError("CORRECTION_LOCATOR_FAILED: " + "; ".join(report["findings"]))
            results.append({"source_id": old["id"], "review": review, "verification_report": report})
        changed = deepcopy(graph)
        changed.sources = after
        protected = protected_snapshot(graph)
        if protected_snapshot(changed) != protected:
            raise AssetError("CORRECTION_PROTECTED_EVIDENCE_CHANGE")
        return {
            "schema_version": 1, "status": "PROPOSED", "plan": deepcopy(plan),
            "before_sources": before, "after_sources": after, "protected_snapshot": protected,
            "protected_sha256": digest(canonical_bytes(protected)), "results": results,
            "authority_effect": "NONE", "review_kind": plan["reviewer"]["kind"],
        }

    def apply(self, proposal: dict[str, Any], *, audit_path: str) -> dict[str, Any]:
        from .repository import ProvenanceRepository

        target = repository_path(self.root, audit_path)
        if not audit_path.startswith("artifacts/migration/") or target.exists():
            raise AssetError("correction audit must use a new path under artifacts/migration/")
        if self.propose(proposal["plan"]) != proposal:
            raise AssetError("STALE_CORRECTION_PROPOSAL")
        after = deepcopy(proposal["after_sources"])
        cache = self.root / ".rcwh-cache/source-correction-records"
        cache.mkdir(parents=True, exist_ok=True)
        for result in proposal["results"]:
            for kind in ("review", "verification_report"):
                raw = canonical_bytes(result[kind])
                path = cache / f"{digest(raw)}.json"
                path.write_bytes(raw)
                receipt = AssetIntake(self.root).ingest(
                    path, origin=f"source-correction:{kind}:{result['source_id']}",
                    kind="REVIEW_RECORD", receipt_key=f"source-correction:{kind}:{digest(raw)}",
                )
                source = after[result["source_id"]]
                if kind == "review":
                    if (receipt["asset_ref"], receipt["sha256"]) != (source["excerpt_revision"]["ref"], source["excerpt_revision"]["sha256"]):
                        raise AssetError("CORRECTION_REVIEW_IDENTITY_MISMATCH")
                else:
                    source["locator_verification"] = {
                        "status": "VERIFIED", "reason": "Revised raw excerpt verified; correction and claim impact are recorded separately.",
                        "report_ref": receipt["asset_ref"], "report_sha256": receipt["sha256"],
                        "source_record_sha256": result[kind]["source_record_sha256"],
                    }
        store = CatalogStore(self.root)
        with store.lock(exclusive=True):
            recover_unlocked(store)
            current = ProvenanceGraph.from_repo(self.root)
            if current.sources != proposal["before_sources"] or protected_snapshot(current) != proposal["protected_snapshot"]:
                raise AssetError("STALE_CORRECTION_INPUT")
            current.sources = after
            if current.validate_integrity() or protected_snapshot(current) != proposal["protected_snapshot"]:
                raise AssetError("CORRECTION_PROTECTED_EVIDENCE_CHANGE")
            assets, origins = store.read_unlocked()
            repository = ProvenanceRepository(current, AssetCatalog(self.root, assets, origins))
            findings = repository.validate_assets()
            if findings:
                raise AssetError("; ".join(findings))
            verifier = SourceLocatorVerifier(repository.catalog)
            for result in proposal["results"]:
                if verifier.verify(after[result["source_id"]])["status"] != "PASS":
                    raise AssetError("registered correction verification failed")
            changes = {}
            for path in sorted((self.root / "data/provenance/sources").glob("*.yaml")):
                document = yaml.safe_load(path.read_bytes())
                if not any(item["id"] in {result["source_id"] for result in proposal["results"]} for item in document["sources"]):
                    continue
                document["sources"] = [after[source["id"]] for source in document["sources"]]
                changes[path.relative_to(self.root).as_posix()] = yaml.safe_dump(document, allow_unicode=True, sort_keys=False).encode("utf-8")
            audit = {**proposal, "status": "APPLIED", "after_sources": after}
            if target.exists():
                raise AssetError("correction audit path already exists")
            changes[audit_path] = canonical_bytes(audit)
            commit_unlocked(store, changes)
        return audit
