"""Receipt facts and current bindings; state is calculated, never self-reported."""
from __future__ import annotations

import subprocess
import json
from typing import Any

from ..graph import ProvenanceGraph
from ..schema import validate_instance
from .catalog import AssetCatalog
from .paths import AssetError, repository_path
from .store import CatalogStore


class ReceiptLedger:
    def __init__(self, catalog: AssetCatalog, records: dict[str, dict[str, Any]] | None = None):
        self.catalog = catalog
        self.store = CatalogStore(catalog.root)
        if records is None:
            with self.store.lock():
                self.store.assert_ready()
                records = self.store.receipts_unlocked()
        self.records = records

    def validate(self) -> list[str]:
        errors = []
        origins = set()
        for receipt_id, record in self.records.items():
            problems = validate_instance(record, self.catalog.root / "schemas/asset_receipt.schema.json")
            if problems:
                errors.append(f"{receipt_id}: " + "; ".join(problems))
                continue
            asset = self.catalog.assets.get(record["asset_ref"])
            origin = self.catalog.origins.get(record["origin_ref"])
            if asset is None or (asset["sha256"], asset["bytes"], asset["media_type"]) != (
                record["sha256"], record["bytes"], record["media_type"],
            ):
                errors.append(f"{receipt_id}: receipt disagrees with asset")
            if origin is None or any((
                origin["asset_ref"] != record["asset_ref"], origin["sha256"] != record["sha256"],
                origin["origin_container"] != record["origin"], origin["original_path"] != record["original_path"],
            )):
                errors.append(f"{receipt_id}: receipt disagrees with origin")
            if record["origin_ref"] in origins:
                errors.append(f"{receipt_id}: origin belongs to multiple receipts")
            origins.add(record["origin_ref"])
            classification = record["classification"]
            if asset and (
                (classification is None) != (asset["kind"] == "UNCLASSIFIED_INPUT")
                or (classification is not None and classification["kind"] != asset["kind"])
            ):
                errors.append(f"{receipt_id}: classification disagrees with asset")
        return errors

    def binding_refs(self, record: dict[str, Any]) -> list[str]:
        graph = ProvenanceGraph.from_repo(self.catalog.root)
        if graph.validate_integrity():
            return []
        result = []
        for schema, records, field, ref_key, sha_key in (
            ("source", graph.sources, "container", "ref", "sha256"),
            ("implementation", graph.implementations, "locator", "asset_ref", "file_sha256"),
        ):
            for item in records.values():
                binding = item.get(field, {})
                if binding.get(ref_key) == record["asset_ref"] and binding.get(sha_key) == record["sha256"]:
                    if not validate_instance(item, self.catalog.root / f"schemas/{schema}.schema.json"):
                        result.append(item["id"])
        from ..literary_inputs import LiteraryInputs
        from ..paired_review import PairedReview
        from ..io import load_data
        inputs = LiteraryInputs(self.catalog)
        for path in sorted((self.catalog.root / "data/writing/packages").glob("*.json")):
            try:
                binding = {"asset_ref": record["asset_ref"], "sha256": record["sha256"]}
                if binding not in load_data(repository_path(self.catalog.root, path.relative_to(self.catalog.root).as_posix())).get("assets", []):
                    continue
                package = inputs.package(path.relative_to(self.catalog.root).as_posix())
                if package["status"] == "PASS" and binding in package["package"]["assets"]:
                    result.append(package["package"]["id"])
            except (AssetError, OSError, ValueError, KeyError):
                pass
        selection = self.catalog.root / PairedReview.selection_path
        if selection.is_file():
            try:
                review = PairedReview(self.catalog)
                summary = review.selected_summary()
                if summary["status"] in {"PASS", "PENDING"}:
                    for binding in load_data(selection)["reviews"]:
                        item = json.loads(review.bound_file(binding))
                        if item["raw_review"] == {"asset_ref": record["asset_ref"], "sha256": record["sha256"]}:
                            result.append(item["id"])
            except (AssetError, OSError, ValueError, KeyError):
                pass
        from ..corpus.audit import CorpusAudit
        for path in sorted((self.catalog.root / "data/corpus/audits").glob("*.json")):
            if len(path.stem) != 64: continue
            try:
                selected = load_data(repository_path(self.catalog.root, path.relative_to(self.catalog.root).as_posix()))
                candidates = []
                for binding in selected.get("reviews", []):
                    item = load_data(repository_path(self.catalog.root, binding["path"]))
                    if item.get("raw_review") == {"asset_ref": record["asset_ref"], "sha256": record["sha256"]}:
                        candidates.append(item)
                if candidates and CorpusAudit(self.catalog).summary(selected["dataset_ref"])["status"] in {"PASS", "PENDING", "FAIL"}:
                    result.extend(item["id"] for item in candidates)
            except (AssetError, OSError, ValueError, KeyError):
                pass
        from ..provenance.audit import SourceAudit
        source_selection = self.catalog.root / SourceAudit.selection_path
        if source_selection.is_file():
            try:
                selected = load_data(repository_path(self.catalog.root, SourceAudit.selection_path))
                candidates = []
                for binding in selected.get("reviews", []):
                    item = load_data(repository_path(self.catalog.root, binding["path"]))
                    if item.get("raw_review") == {"asset_ref": record["asset_ref"], "sha256": record["sha256"]}:
                        candidates.append(item)
                if candidates:
                    from ..provenance import ProvenanceRepository
                    if SourceAudit(ProvenanceRepository.from_repo(self.catalog.root)).summary()["status"] in {"PASS", "PENDING", "FAIL"}:
                        result.extend(item["id"] for item in candidates)
            except (AssetError, OSError, ValueError, KeyError):
                pass
        return sorted(result)

    def describe(self, receipt_id: str) -> dict[str, Any]:
        if receipt_id not in self.records:
            raise AssetError(f"unknown receipt: {receipt_id}")
        errors = self.validate()
        if errors:
            raise AssetError("invalid receipt ledger: " + "; ".join(errors))
        record = self.records[receipt_id]
        asset = self.catalog.resolve(record["asset_ref"])
        refs = self.binding_refs(record)
        classified = record["classification"] is not None
        state = "BOUND" if classified and refs else "CLASSIFIED" if classified else "RECEIVED"
        required = {asset.relative_path, *self.store.metadata_paths()}
        result = subprocess.run(
            ["git", "ls-files", "-z"], cwd=self.catalog.root, capture_output=True, check=False,
        )
        tracked = set(result.stdout.decode("utf-8").split("\0")) if result.returncode == 0 else set()
        return {
            **record, "classification_status": state, "binding_refs": refs,
            "asset": asset.summary(), "tracked": required <= tracked,
            "untracked_paths": sorted(required - tracked), "authority_effect": "NONE",
        }
