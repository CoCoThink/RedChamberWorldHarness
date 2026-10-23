"""Bound source excerpts, surrounding text and images for actual source readers."""
from __future__ import annotations

from functools import lru_cache
import json

import fitz

from ..candidate_reviews import canonical_bytes, digest


@lru_cache(maxsize=32)
def page_image(raw: bytes, number: int) -> bytes:
    with fitz.open(stream=raw, filetype="pdf") as document:
        return document[number - 1].get_pixmap(dpi=140).tobytes("jpeg", jpg_quality=85)


def context_units(source, units):
    refs = source.get("witness", {}).get("context_units", [])
    if (not isinstance(refs, list) or any(not isinstance(ref, str) or ref not in units for ref in refs)
            or len(set(refs)) != len(refs)):
        raise ValueError("invalid witness context units")
    return refs


def contexts(source, units):
    extra = context_units(source, units)
    refs = {s["unit_ref"] for s in source["locator"]["spans"]} | set(extra)
    selected = []
    for ref in (ref for ref in units if ref in refs):
        spans = [s for s in source["locator"]["spans"] if s["unit_ref"] == ref]
        text = units[ref]["text"]
        if ref in extra:
            start, end = 0, len(text)
        else:
            start, end = max(0, min(s["start"] for s in spans) - 500), min(len(text), max(s["end"] for s in spans) + 500)
        selected.append({"unit_ref": ref, "start": start, "end": end, "text": text[start:end]})
    return selected


def prepare(catalog, source, base, write, cache=None):
    from ..corpus.extraction import ExtractionRepository
    root = catalog.root
    carrier = catalog.resolve(source["container"]["ref"])
    extraction = catalog.resolve(source["locator"]["extraction_ref"])
    cache = {} if cache is None else cache
    if extraction.id not in cache:
        cache[extraction.id] = ExtractionRepository(catalog).load(extraction.id, rebuild=False)
    manifest, units = cache[extraction.id]
    output = catalog.resolve(manifest["output"]["asset_ref"])
    def binding(asset):
        return {"path": asset.relative_path, "sha256": asset.sha256}
    selected = contexts(source, units)
    images = []
    if manifest["config"]["format"] == "PDF":
        for number in sorted({int(s["unit_ref"].rsplit(":", 1)[1]) for s in selected}):
            raw = page_image(carrier.path.read_bytes(), number)
            image = write(root, f"{base}/source-pages/{digest(raw)}.jpg", raw)
            images.append({"binding": image, "original": binding(carrier), "page": number})
    else:
        # Agent transcriptions may have separately retained facsimile crops.
        for ref in catalog.assets[carrier.id].get("derived_from", []):
            if catalog.assets[ref]["media_type"].startswith("image/"):
                original = catalog.resolve(ref)
                images.append({"binding": binding(original), "original": binding(original), "page": None})
    value = {"schema_version": 1, "kind": "SOURCE_READING_EVIDENCE", "source_ref": source["id"],
             "source_sha256": digest(canonical_bytes(source)), "carrier": binding(carrier),
             "extraction": binding(extraction), "output": binding(output), "locator": source["locator"],
             "contexts": selected, "images": images,
             "boundary": "Check only what the fixed carrier supports. Agent transcription is not an independently verified transcription; images and bibliography must be checked separately."}
    return write(root, f"{base}/source-evidence/{digest(canonical_bytes(value))}.json", value)


def verify(source, evidence, read, *, rebuild_images: bool = True):
    value = json.loads(read(evidence))
    if (value["schema_version"] != 1 or value["kind"] != "SOURCE_READING_EVIDENCE"
            or value["source_ref"] != source["id"] or value["source_sha256"] != digest(canonical_bytes(source))
            or value["locator"] != source["locator"] or value["carrier"]["sha256"] != source["container"]["sha256"]):
        raise ValueError("source reading evidence differs from source")
    raw = read(value["carrier"])
    manifest = json.loads(read(value["extraction"]))
    if (manifest["input"] != {"asset_ref": source["container"]["ref"], "sha256": value["carrier"]["sha256"]}
            or manifest["output"]["sha256"] != value["output"]["sha256"]
            or manifest["output"]["sha256"] != source["locator"]["output_sha256"]):
        raise ValueError("source reading extraction mismatch")
    units = {r["unit_ref"]: r for r in (json.loads(line) for line in read(value["output"]).splitlines() if line.strip())}
    selected = contexts(source, units)
    if value["contexts"] != selected:
        raise ValueError("source reading context differs from fixed extraction")
    excerpt = source["locator"]["joiner"].join(units[s["unit_ref"]]["text"][s["start"]:s["end"]] for s in source["locator"]["spans"])
    if excerpt != source["text"]:
        raise ValueError("source reading excerpt mismatch")
    if manifest["config"]["format"] == "PDF" and {i["page"] for i in value["images"]} != {
            int(s["unit_ref"].rsplit(":", 1)[1]) for s in selected}:
        raise ValueError("source reading omits an original PDF page")
    for image in value["images"]:
        original, rendered = read(image["original"]), read(image["binding"])
        if image["page"] is not None:
            if image["original"] != value["carrier"] or (rebuild_images and rendered != page_image(original, image["page"])):
                raise ValueError("source page image differs from original carrier")
        elif original != rendered:
            raise ValueError("source facsimile differs from retained original")
    return value
