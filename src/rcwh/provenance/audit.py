"""Independent acceptance of excerpt corrections and edition bindings."""
from __future__ import annotations

import json

from ..assets import AssetError
from ..assets.paths import repository_path
from ..assets.transactions import digest
from ..corpus.extraction import canonical_bytes, validate
from ..corpus.locators import source_digest
from ..io import load_data
from .repository import ProvenanceRepository


class SourceAudit:
    selection_path = "data/provenance/audits/selection.json"

    def __init__(self, repository: ProvenanceRepository):
        self.repository = repository
        self.catalog = repository.catalog
        self.root = self.catalog.root

    def graph_digest(self):
        graph = self.repository.graph
        return digest(canonical_bytes({name: getattr(graph, name) for name in ("claims", "decisions", "implementations", "title_axes")}))

    def summary(self) -> dict:
        pending = {"status": "PENDING", "scope": "SOURCE_INDEPENDENT_EVIDENCE_AUDIT", "review_count": 0, "authority_effect": "NONE"}
        if not (self.root/self.selection_path).is_file(): return pending
        def bound(binding):
            raw = repository_path(self.root, binding["path"]).read_bytes()
            if digest(raw) != binding["sha256"]: raise AssetError("STALE_SOURCE_AUDIT_RECORD")
            return json.loads(raw)
        selected = load_data(repository_path(self.root, self.selection_path)); validate(self.root, selected, "source_audit_selection")
        protocol = bound(selected["protocol"]); validate(self.root, protocol, "source_audit_protocol")
        if protocol["graph_sha256"] != self.graph_digest(): raise AssetError("STALE_SOURCE_AUDIT_GRAPH")
        source_index = self.repository.graph.sources
        required = {s["id"] for s in source_index.values() if "excerpt_revision" in s or s["locator"].get("schema_version") != 2}
        declared = {s["source_ref"]: s for s in protocol["sources"]}
        if len(declared) != len(protocol["sources"]) or not required <= set(declared): raise AssetError("SOURCE_AUDIT_REQUIRED_SCOPE_MISSING")
        for identity, item in declared.items():
            if identity not in source_index or source_digest(source_index[identity]) != item["source_record_sha256"]:
                raise AssetError("STALE_SOURCE_AUDIT_SOURCE")
        covered = set(); reviewers = set(); ids = set(); findings = []
        for binding in selected["reviews"]:
            review = bound(binding); validate(self.root, review, "source_audit_review")
            if review["protocol_sha256"] != selected["protocol"]["sha256"]: raise AssetError("STALE_SOURCE_INDEPENDENT_REVIEW")
            if review["id"] in ids: raise AssetError("DUPLICATE_SOURCE_INDEPENDENT_REVIEW")
            ids.add(review["id"]); reviewers.add(review["reviewer"]["id"])
            rows = {row["source_ref"]: row for row in review["results"]}
            if len(rows) != len(review["results"]) or not set(rows) <= set(declared): raise AssetError("INVALID_SOURCE_AUDIT_REVIEW_SCOPE")
            raw = self.catalog.resolve(review["raw_review"]["asset_ref"])
            if raw.sha256 != review["raw_review"]["sha256"] or self.catalog.assets[raw.id]["kind"] != "REVIEW_RECORD": raise AssetError("INVALID_RAW_SOURCE_AUDIT")
            projection = {key: value for key, value in review.items() if key not in {"schema_version", "id", "raw_review", "authority_effect"}}
            if json.loads(raw.path.read_bytes()) != projection: raise AssetError("RAW_SOURCE_AUDIT_MISMATCH")
            for identity in rows:
                if self.repository.source_report(source_index[identity], locators=True)["status"] != "PASS": raise AssetError("SOURCE_AUDIT_LOCATOR_NOT_VERIFIED")
            for identity, row in rows.items():
                rejected = [key for key in ("carrier_edition_confirmed", "excerpt_valid", "witness_tier_unchanged", "claim_impact_reviewed") if not row[key]]
                if rejected:
                    findings.append({"review_id": review["id"], "source_ref": identity, "rejected_checks": rejected, "notes": row["notes"]})
                else:
                    covered.add(identity)
        return {**pending, "status": "FAIL" if findings else "PASS" if set(declared) <= covered else "PENDING", "review_count": len(ids),
                "required_source_ids": sorted(declared), "pending_source_ids": sorted(set(declared)-covered),
                "findings": findings,
                "independence_basis": "SUBMITTED_REVIEWER_ATTESTATIONS", "reviewers": sorted(reviewers)}
