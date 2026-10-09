"""Recompute the Cao facsimile chain; manuscript reading is an agent attestation."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from rcwh.assets import AssetCatalog, AssetError
from rcwh.assets.paths import repository_path
from rcwh.assets.transactions import digest
from rcwh.corpus.extraction import ExtractionRepository, canonical_bytes
from rcwh.corpus.locators import source_digest
from rcwh.provenance import ProvenanceRepository
from rcwh.provenance.audit import SourceAudit
from rcwh.schema import validate_instance


def verify(root: Path, bundle_path: str) -> dict:
    import pymupdf

    repository = ProvenanceRepository.from_repo(root)
    catalog = repository.catalog
    bundle = json.loads(repository_path(root, bundle_path).read_bytes())

    def bound(binding):
        asset = catalog.resolve(binding["ref"])
        if asset.sha256 != binding["sha256"]:
            raise AssetError("FACSIMILE_BINDING_HASH_MISMATCH")
        return asset

    collation_asset = bound(bundle["collation"])
    collation = json.loads(collation_asset.path.read_bytes())
    if collation["kind"] != "AGENT_FACSIMILE_COLLATION" or collation["reviewer"]["kind"] != "AGENT_TEXT_REVIEW":
        raise AssetError("INVALID_FACSIMILE_COLLATION_KIND")
    if collation["witness"]["accession"] != "故宮005664" or collation["witness"]["independent_witnesses"] != 1:
        raise AssetError("FACSIMILE_WITNESS_MISMATCH")
    if bundle["bindings"] != collation["fixed_downloads"] or bundle["images"] != collation["embedded_images"]:
        raise AssetError("FACSIMILE_BUNDLE_MISMATCH")
    for fixed in bundle["bindings"].values():
        carrier = bound(fixed["carrier"])
        capture = json.loads(bound(fixed["capture"]).path.read_bytes())
        errors = validate_instance(capture, root / "schemas/source_capture.schema.json")
        if errors or capture["carrier"] != fixed["carrier"] or capture["requested_url"] != fixed["url"]:
            raise AssetError("FACSIMILE_HTTP_CAPTURE_MISMATCH")
    for figure in bundle["images"].values():
        carrier = bound(figure["carrier"])
        image = bound(figure["image"])
        if catalog.assets[image.id].get("derived_from") != [carrier.id]:
            raise AssetError("FACSIMILE_IMAGE_DERIVATION_MISMATCH")
        with pymupdf.open(carrier.path) as pdf:
            page = pdf[figure["physical_page"] - 1]
            if figure["pdf_image_xref"] not in {item[0] for item in page.get_images()}:
                raise AssetError("FACSIMILE_IMAGE_NOT_ON_DECLARED_PAGE")
            original = pdf.extract_image(figure["pdf_image_xref"])
            if original["image"] != image.path.read_bytes() or (original["width"], original["height"]) != (figure["width"], figure["height"]):
                raise AssetError("FACSIMILE_IMAGE_BYTES_MISMATCH")
    transcript = bound(bundle["transcript"])
    required_parents = {v[k]["ref"] for v in bundle["bindings"].values() for k in ("carrier", "capture")}
    required_parents.add(collation_asset.id)
    required_parents.update(v["image"]["ref"] for v in bundle["images"].values())
    if set(catalog.assets[transcript.id].get("derived_from", [])) != required_parents:
        raise AssetError("FACSIMILE_TRANSCRIPT_DERIVATION_MISMATCH")
    manifest, units = ExtractionRepository(catalog).load(bundle["extraction_ref"], rebuild=True)
    if manifest["input"] != {"asset_ref": transcript.id, "sha256": transcript.sha256} or manifest["config"]["format"] != "TEXT":
        raise AssetError("FACSIMILE_TRANSCRIPT_EXTRACTION_MISMATCH")
    rows = []
    for result in collation["results"]:
        source = repository.graph.sources[result["source_ref"]]
        if source_digest(source) != bundle["sources"][source["id"]]:
            raise AssetError("STALE_FACSIMILE_SOURCE")
        text = result["transcribed_text"]
        if text != source["text"] or digest(text.encode()) != result["transcribed_text_sha256"]:
            raise AssetError("FACSIMILE_SOURCE_TRANSCRIPTION_MISMATCH")
        if "carrier_capture" in source or source["container"] != bundle["transcript"]:
            raise AssetError("FACSIMILE_LOCAL_TRANSCRIPT_CARRIER_MISMATCH")
        if "".join(r["text"] for r in result["image_regions"]) != text:
            raise AssetError("FACSIMILE_COLUMN_COVERAGE_MISMATCH")
        for region in result["image_regions"]:
            image = bundle["images"][region["image_key"]]
            x0, y0, x1, y1 = region["box"]
            if not 0 <= x0 < x1 <= image["width"] or not 0 <= y0 < y1 <= image["height"]:
                raise AssetError("FACSIMILE_REGION_OUT_OF_RANGE")
        report = repository.source_report(source, locators=True)
        if report["status"] != "PASS":
            raise AssetError("FACSIMILE_SOURCE_LOCATOR_FAILED: " + "; ".join(report["findings"]))
        rows.append({"source_id": source["id"], "status": "PASS", "source_sha256": source_digest(source), "text_sha256": source["text_sha256"]})
    if set(bundle["sources"]) != {row["source_id"] for row in rows} or len(rows) != 3:
        raise AssetError("FACSIMILE_EXCERPT_SET_MISMATCH")
    return {"status": "PASS", "scope": "FIXED_FACSIMILE_AND_AGENT_TRANSCRIPTION_CHAIN",
            "bundle_sha256": digest(repository_path(root, bundle_path).read_bytes()), "sources": rows,
            "independent_witnesses": 1, "embedded_images_recomputed": len(bundle["images"]),
            "image_reading_basis": "NAMED_AGENT_VISUAL_COLLATION_ATTESTATION",
            "mechanical_check_proves": "Fixed downloads, embedded image bytes, derivation chain, declared column coverage and exact transcript spans",
            "independent_source_audit": SourceAudit(repository).summary(), "authority_effect": "NONE"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--bundle", default="artifacts/migration/cao-facsimile-20261009/bundle-v1.json")
    args = parser.parse_args()
    try:
        report = verify(args.root.resolve(), args.bundle)
    except (AssetError, OSError, ValueError, KeyError, IndexError) as exc:
        report = {"status": "FAIL", "findings": [str(exc)]}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return int(report["status"] != "PASS")


if __name__ == "__main__":
    raise SystemExit(main())
