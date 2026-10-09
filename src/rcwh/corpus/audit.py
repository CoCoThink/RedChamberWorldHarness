"""Human layer acceptance is a separate, input-bound review contract."""
from __future__ import annotations

import json

from ..assets import AssetCatalog, AssetError
from ..assets.paths import repository_path
from ..assets.transactions import digest
from ..io import load_data
from .dataset import CorpusRepository
from .extraction import validate


class CorpusAudit:
    def __init__(self, catalog: AssetCatalog):
        self.catalog = catalog
        self.root = catalog.root

    def summary(self, dataset_ref: str, *, rebuild: bool = True) -> dict:
        path = f"data/corpus/audits/{digest(dataset_ref.encode())}.json"
        pending = {"status": "PENDING", "scope": "CORPUS_HUMAN_LAYER_AUDIT", "dataset_ref": dataset_ref,
                   "review_count": 0, "authority_effect": "NONE"}
        if not (self.root/path).is_file(): return pending
        selected = load_data(repository_path(self.root, path)); validate(self.root, selected, "corpus_audit_selection")
        if selected["dataset_ref"] != dataset_ref: raise AssetError("CORPUS_AUDIT_DATASET_MISMATCH")
        def bound(binding):
            raw = repository_path(self.root, binding["path"]).read_bytes()
            if digest(raw) != binding["sha256"]: raise AssetError("STALE_CORPUS_AUDIT_RECORD")
            return json.loads(raw)
        protocol = bound(selected["protocol"]); validate(self.root, protocol, "corpus_audit_protocol")
        corpus = CorpusRepository(self.catalog)
        binding = corpus.registry()[dataset_ref]
        if protocol["dataset_ref"] != dataset_ref or protocol["manifest_sha256"] != binding["manifest_sha256"]:
            raise AssetError("STALE_CORPUS_AUDIT_MANIFEST")
        manifest, products = corpus.load(dataset_ref, rebuild=rebuild)
        index = {s["segment_id"]: s for s in (json.loads(line) for line in products["segments.jsonl"].splitlines()[1:])}
        samples = {s["segment_id"]: s for s in protocol["samples"]}
        if len(samples) != len(protocol["samples"]): raise AssetError("DUPLICATE_CORPUS_AUDIT_SAMPLE")
        for identity, sample in samples.items():
            if identity not in index or index[identity]["text_sha256"] != sample["text_sha256"]:
                raise AssetError("STALE_CORPUS_AUDIT_SAMPLE")
        if {index[s]["chapter"] for s in samples if index[s]["kind"] == "MAIN_TEXT"} != set(manifest["build_config"]["document"]["chapters"]):
            raise AssetError("CORPUS_AUDIT_MUST_SAMPLE_EACH_CHAPTER_MAIN_TEXT")
        available = {s["kind"] for s in index.values() if s["text"].strip()}
        if available - {index[s]["kind"] for s in samples}:
            raise AssetError("CORPUS_AUDIT_MISSING_TEXT_LAYER")
        quality = json.loads(products["quality_report.json"])
        if quality["technical_findings"]: raise AssetError("CORPUS_TECHNICAL_FINDINGS_UNRESOLVED")
        reviewers = set(); ids = set(); findings = []
        for binding in selected["reviews"]:
            review = bound(binding); validate(self.root, review, "corpus_audit_review")
            if (review["dataset_ref"], review["manifest_sha256"], review["protocol_sha256"]) != (dataset_ref, protocol["manifest_sha256"], selected["protocol"]["sha256"]):
                raise AssetError("STALE_CORPUS_HUMAN_REVIEW")
            if review["reviewer"]["id"] in reviewers or review["id"] in ids: raise AssetError("DUPLICATE_CORPUS_HUMAN_REVIEW")
            reviewers.add(review["reviewer"]["id"]); ids.add(review["id"])
            checks = {row["segment_id"]: row for row in review["checks"]}
            if len(checks) != len(review["checks"]) or set(checks) != set(samples): raise AssetError("INCOMPLETE_CORPUS_HUMAN_REVIEW")
            raw_asset = self.catalog.resolve(review["raw_review"]["asset_ref"])
            if raw_asset.sha256 != review["raw_review"]["sha256"] or self.catalog.assets[raw_asset.id]["kind"] != "REVIEW_RECORD":
                raise AssetError("INVALID_RAW_CORPUS_REVIEW")
            projection = {key: value for key, value in review.items() if key not in {"schema_version", "id", "raw_review", "authority_effect"}}
            if json.loads(raw_asset.path.read_bytes()) != projection: raise AssetError("RAW_CORPUS_REVIEW_MISMATCH")
            rejected = [key for key in ("main_boundaries_confirmed", "unknown_witnesses_acknowledged", "unaligned_segments_acknowledged") if not review[key]]
            if rejected:
                findings.append({"review_id": review["id"], "rejected_checks": rejected})
            for identity, row in checks.items():
                rejected = [key for key in ("layer_valid", "locator_valid", "context_valid") if not row[key]]
                if rejected:
                    findings.append({"review_id": review["id"], "segment_id": identity, "rejected_checks": rejected, "notes": row["notes"]})
        return {**pending, "status": "FAIL" if findings else "PASS" if len(reviewers) >= protocol["minimum_reviewers"] else "PENDING",
                "review_count": len(reviewers), "sample_count": len(samples), "manifest_sha256": protocol["manifest_sha256"],
                "minimum_reviewers": protocol["minimum_reviewers"], "findings": findings,
                "independence_basis": "SUBMITTED_REVIEWER_ATTESTATIONS", "unresolved_witnesses": quality["unknown_annotation_witnesses"],
                "unaligned_segments": quality["unaligned_segments"]}
