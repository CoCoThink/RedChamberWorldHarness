"""Actual excerpt checks; stored status flags cannot replace recomputation."""
from __future__ import annotations

from copy import deepcopy
import json
from typing import Any

from ..assets import AssetCatalog, AssetError
from ..assets.transactions import digest
from ..assets.paths import repository_path
from .extraction import ExtractionRepository, canonical_bytes, code_digest, validate


LOCATOR_KINDS = {"TEXT": "TEXT_SPANS", "PDF": "PDF_TEXT_SPANS", "HTML": "HTML_TEXT_SPANS", "EPUB": "EPUB_TEXT_SPANS"}


def source_digest(source: dict[str, Any]) -> str:
    # Verification metadata is an observation about the source, not part of its input.
    return digest(canonical_bytes({key: value for key, value in source.items() if key != "locator_verification"}))


class SourceLocatorVerifier:
    def __init__(self, catalog: AssetCatalog):
        self.catalog = catalog
        self.extractions = ExtractionRepository(catalog)
        self._loaded: dict[str, tuple[dict[str, Any], dict[str, dict[str, Any]]]] = {}
        self._manifest_shas: dict[str, str] = {}

    def extraction(self, manifest_ref: str) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
        if manifest_ref not in self._loaded:
            self._loaded[manifest_ref] = self.extractions.load(manifest_ref, rebuild=True)
            self._manifest_shas[manifest_ref] = self.catalog.resolve(manifest_ref).sha256
        else:
            manifest, _ = self._loaded[manifest_ref]
            manifest_asset = self.catalog.resolve(manifest_ref)
            output = self.catalog.resolve(manifest["output"]["asset_ref"])
            input_asset = self.catalog.resolve(manifest["input"]["asset_ref"])
            if (
                manifest_asset.sha256 != self._manifest_shas[manifest_ref]
                or output.sha256 != manifest["output"]["sha256"]
                or input_asset.sha256 != manifest["input"]["sha256"]
                or self.extractions.extractor(manifest["config"]["format"]) != manifest["extractor"]
                or digest(repository_path(self.catalog.root, manifest["dependency_lock"]["path"]).read_bytes()) != manifest["dependency_lock"]["sha256"]
            ):
                raise AssetError("STALE_EXTRACTION_INPUT_OR_TOOL")
        return self._loaded[manifest_ref]

    def verify(self, source: dict[str, Any]) -> dict[str, Any]:
        locator = source["locator"]
        report = {
            "schema_version": 1, "source_id": source["id"], "source_record_sha256": source_digest(source),
            "locator_sha256": digest(canonical_bytes(locator)),
            "verifier": {"name": "rcwh-source-locator", "version": 1, "code_sha256": code_digest("locators.py")},
            "status": "FAIL", "findings": [],
        }
        if locator.get("schema_version") != 2:
            report["findings"].append("LOCATOR_VERSION_UNVERIFIED: imported page/line assertions require a Locator v2")
            return report
        try:
            validate(self.catalog.root, source, "source")
            validate(self.catalog.root, locator, "locator_v2")
            if "container" not in source:
                raise AssetError("MISSING_LOCAL_CONTAINER")
            asset = self.catalog.resolve(source["container"]["ref"])
            if asset.sha256 != source["container"]["sha256"]:
                raise AssetError("CONTAINER_HASH_MISMATCH")
            if digest(source["text"].encode("utf-8")) != source["text_sha256"]:
                raise AssetError("EXCERPT_HASH_MISMATCH")
            manifest, units = self.extraction(locator["extraction_ref"])
            if manifest["input"] != {"asset_ref": asset.id, "sha256": asset.sha256}:
                raise AssetError("LOCATOR_CARRIER_MISMATCH")
            if locator["kind"] != LOCATOR_KINDS[manifest["config"]["format"]]:
                raise AssetError("LOCATOR_FORMAT_MISMATCH")
            if locator["output_sha256"] != manifest["output"]["sha256"]:
                raise AssetError("LOCATOR_OUTPUT_HASH_MISMATCH")
            positions = {reference: index for index, reference in enumerate(units)}
            previous = (-1, 0)
            chunks = []
            for span in locator["spans"]:
                if span["unit_ref"] not in units:
                    raise AssetError("UNKNOWN_TEXT_UNIT")
                text = units[span["unit_ref"]]["text"]
                if not 0 <= span["start"] < span["end"] <= len(text):
                    raise AssetError("LOCATOR_SPAN_OUT_OF_RANGE")
                position = positions[span["unit_ref"]]
                if (position, span["start"]) < previous:
                    raise AssetError("OVERLAPPING_OR_REORDERED_SPANS")
                previous = (position, span["end"])
                chunks.append(text[span["start"]:span["end"]])
            excerpt = locator["joiner"].join(chunks)
            actual_sha = digest(excerpt.encode("utf-8"))
            report.update(
                extraction={"manifest_ref": locator["extraction_ref"], "manifest_sha256": self.catalog.resolve(locator["extraction_ref"]).sha256,
                            "input": deepcopy(manifest["input"]), "output": deepcopy(manifest["output"]), "extractor": deepcopy(manifest["extractor"])},
                raw_excerpt=excerpt, raw_text_sha256=actual_sha, expected_text_sha256=source["text_sha256"],
            )
            if actual_sha != locator["raw_text_sha256"]:
                raise AssetError("LOCATOR_EXCERPT_HASH_MISMATCH")
            if excerpt != source["text"] or actual_sha != source["text_sha256"]:
                raise AssetError("EXCERPT_MISMATCH")
            report["status"] = "PASS"
            declared = source.get("locator_verification", {})
            if "report_ref" in declared:
                stored_asset = self.catalog.resolve(declared["report_ref"])
                if stored_asset.sha256 != declared.get("report_sha256") or declared.get("source_record_sha256") != report["source_record_sha256"]:
                    raise AssetError("STALE_VERIFICATION_REPORT_BINDING")
                stored = json.loads(stored_asset.path.read_bytes())
                validate(self.catalog.root, stored, "source_locator_report")
                if stored != report:
                    raise AssetError("STALE_OR_INCONSISTENT_VERIFICATION_REPORT")
        except (AssetError, OSError, KeyError, ValueError) as exc:
            report["status"] = "FAIL"
            report["findings"].append(str(exc))
        return report

    def locate(
        self, source: dict[str, Any], manifest_ref: str, *, unit_ref: str | None = None,
        allow_line_break_spans: bool = False,
    ) -> dict[str, Any]:
        manifest, units = self.extraction(manifest_ref)
        carrier = source.get("container", {})
        if manifest["input"] != {"asset_ref": carrier.get("ref"), "sha256": carrier.get("sha256")}:
            raise AssetError("LOCATOR_CARRIER_MISMATCH")
        text = source["text"]
        if not text or digest(text.encode("utf-8")) != source["text_sha256"]:
            raise AssetError("EMPTY_EXCERPT_OR_HASH_MISMATCH")
        if unit_ref is not None and unit_ref not in units:
            raise AssetError("UNKNOWN_TEXT_UNIT")
        if allow_line_break_spans and manifest["config"]["format"] != "PDF":
            raise AssetError("LINE_BREAK_SPANS_REQUIRE_PDF")
        candidates = []
        for reference, item in units.items():
            if unit_ref is not None and reference != unit_ref:
                continue
            original = item["text"]
            positions = [i for i, char in enumerate(original) if not (allow_line_break_spans and char == "\n")]
            searchable = "".join(original[i] for i in positions)
            start = searchable.find(text)
            while start >= 0:
                spans = []
                for offset in positions[start:start + len(text)]:
                    if spans and spans[-1]["end"] == offset:
                        spans[-1]["end"] += 1
                    else:
                        spans.append({"unit_ref": reference, "start": offset, "end": offset + 1})
                candidates.append(spans[0] if len(spans) == 1 else {"spans": spans})
                start = searchable.find(text, start + 1)
        payload = {"source_id": source["id"], "status": "FAIL", "candidates": candidates, "findings": [], "authority_effect": "NONE"}
        if len(candidates) != 1:
            payload["findings"].append("EXCERPT_NOT_FOUND" if not candidates else "AMBIGUOUS_LOCATOR")
            return payload
        locator = {
            "schema_version": 2, "kind": LOCATOR_KINDS[manifest["config"]["format"]],
            "extraction_ref": manifest_ref, "output_sha256": manifest["output"]["sha256"],
            "spans": candidates[0].get("spans", [candidates[0]]), "joiner": "", "raw_text_sha256": source["text_sha256"],
        }
        proposed = deepcopy(source)
        proposed["locator"] = locator
        # A new proposal has not inherited an old verification report.
        proposed["locator_verification"] = {"status": "UNVERIFIED", "reason": "New Locator v2 proposal; verification is recomputed."}
        report = self.verify(proposed)
        payload.update(status=report["status"], locator=locator, verification_report=report, findings=report["findings"])
        return payload
