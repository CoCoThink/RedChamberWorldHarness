"""Reproducible input inventory; chapter slices still contain mixed text layers."""
from __future__ import annotations

import io
import json
import posixpath
import re
import subprocess
from typing import Any
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from ..assets import AssetCatalog, AssetError
from ..assets.paths import repository_path
from ..assets.transactions import digest
from .adapters import MarkupText, zip_path
from .extraction import ExtractionRepository, canonical_bytes, code_digest, validate


CHINESE = {char: value for value, char in enumerate("零一二三四五六七八九")}
HEADING = re.compile(r"第\s*([一二三四五六七八九十百〇零0-9\s]+)回")
PDF_HEADING = re.compile(r"(?m)^第[ \t]*([一二三四五六七八九十百〇零0-9 \t]+)回[ \t]*$")


def chapter_number(raw: str) -> int:
    text = re.sub(r"\s", "", raw).replace("〇", "零")
    if text.isdigit():
        return int(text)
    # Editorial notes also use abbreviated labels such as 第二六回.
    if text and all(char in CHINESE for char in text):
        return int("".join(str(CHINESE[char]) for char in text))
    if text == "一百":
        return 100
    if "十" in text:
        tens, ones = text.split("十")
        return (CHINESE[tens] if tens else 1) * 10 + (CHINESE[ones] if ones else 0)
    return CHINESE[text]


class StructureParser(MarkupText):
    """Uses the existing text mapper to expose omitted images at exact offsets."""
    def __init__(self, source: str):
        super().__init__(source)
        self.headings: list[dict[str, Any]] = []
        self.images: list[dict[str, Any]] = []
        self.active: dict[str, Any] | None = None

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag in {"h1", "h2", "h3"}:
            self.active = {"tag": tag, "start": self.length, "raw_start": self.source_offset()}
        if tag == "img":
            index = self.stack[-1][2].get(tag, 0) + 1
            self.images.append({
                "dom_path": f"{self.stack[-1][1]}/img[{index}]", "text_offset": self.length,
                "raw_start": self.source_offset(), "raw_end": self.source_offset() + len(self.get_starttag_text()),
                "src": attributes.get("src"), "alt": attributes.get("alt"),
                "font_patch": "font_patch" in (attributes.get("class") or "").split(),
            })
        super().handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if self.active and tag == self.active["tag"]:
            self.headings.append({**self.active, "end": self.length, "text": "".join(self.chunks)[self.active["start"]:self.length]})
            self.active = None
        super().handle_endtag(tag)


def chapter_record(chapter: int, spans: list[dict[str, Any]], units: dict) -> tuple[dict, str]:
    text = "".join(units[s["unit_ref"]]["text"][s["start"]:s["end"]] for s in spans)
    # Comparison is an explicit view, never a normalized source or novel body.
    view = re.sub(r"\s", "", text)
    return {
        "chapter": chapter, "spans": spans, "raw_characters": len(text),
        "raw_sha256": digest(text.encode()), "comparison_characters": len(view),
        "comparison_sha256": digest(view.encode()), "layer_status": "MIXED_UNCLASSIFIED",
    }, view


class CorpusInputs:
    def __init__(self, catalog: AssetCatalog):
        self.catalog = catalog
        self.root = catalog.root

    def config(self, relative: str) -> dict:
        config = json.loads(repository_path(self.root, relative).read_bytes())
        validate(self.root, config, "corpus_inputs")
        expected = config["expected_chapters"]
        if expected != sorted(expected) or expected != list(range(expected[0], expected[-1] + 1)):
            raise AssetError("NONCONTIGUOUS_CHAPTER_SCOPE")
        if config["pilot_chapters"] != sorted(config["pilot_chapters"]) or not set(config["pilot_chapters"]) <= set(expected):
            raise AssetError("INVALID_PILOT_SCOPE")
        if config["pdf"]["use"] != "MAIN" or config["epub"]["use"] != "COMPARISON":
            raise AssetError("UNSUPPORTED_INPUT_SELECTION: inventory v1 requires PDF MAIN and EPUB COMPARISON")
        if config["pdf"]["asset_ref"] == config["epub"]["asset_ref"]:
            raise AssetError("DUPLICATE_INPUT_WITNESS")
        return config

    def load_input(self, record: dict, format_name: str) -> tuple[dict, dict]:
        asset = self.catalog.resolve(record["asset_ref"])
        manifest_asset = self.catalog.resolve(record["extraction_ref"])
        if asset.sha256 != record["sha256"] or manifest_asset.sha256 != record["extraction_sha256"]:
            raise AssetError("CORPUS_INPUT_HASH_MISMATCH")
        manifest, units = ExtractionRepository(self.catalog).load(record["extraction_ref"], rebuild=True)
        if manifest["input"] != {"asset_ref": asset.id, "sha256": asset.sha256} or manifest["config"]["format"] != format_name:
            raise AssetError("CORPUS_INPUT_EXTRACTION_MISMATCH")
        if "pdf_pages" in manifest["config"]:
            raise AssetError("INCOMPLETE_INPUT_EXTRACTION: use the complete carrier")
        return manifest, units

    @staticmethod
    def evidence(record: dict, units: dict) -> list[dict]:
        result = []
        for ref in record["edition_evidence"]:
            if ref not in units:
                raise AssetError(f"MISSING_EDITION_EVIDENCE: {ref}")
            unit = units[ref]
            result.append({"unit_ref": ref, "text_sha256": unit["text_sha256"], "text": unit["text"]})
        return result

    def pdf(self, record: dict, units: dict) -> tuple[dict, dict[int, str]]:
        start, end = record["body_pages"]
        if start > end or f"pdf:page:{end}" not in units:
            raise AssetError("INVALID_PDF_BODY_SCOPE")
        refs = [f"pdf:page:{page}" for page in range(start, end + 1)]
        if any(ref not in units for ref in refs):
            raise AssetError("INCOMPLETE_PDF_BODY_SCOPE")
        heads = [(chapter_number(m[1]), index, m.start()) for index, ref in enumerate(refs) for m in PDF_HEADING.finditer(units[ref]["text"])]
        chapters, views = [], {}
        for index, (chapter, page_index, offset) in enumerate(heads):
            next_page, next_offset = heads[index + 1][1:] if index + 1 < len(heads) else (len(refs) - 1, len(units[refs[-1]]["text"]))
            spans = [{"unit_ref": refs[i], "start": offset if i == page_index else 0,
                      "end": next_offset if i == next_page else len(units[refs[i]]["text"])}
                     for i in range(page_index, next_page + 1)]
            spans = [s for s in spans if s["start"] < s["end"]]
            chapter_data, view = chapter_record(chapter, spans, units)
            chapters.append(chapter_data); views[chapter] = view
        import pymupdf
        with pymupdf.open(stream=self.catalog.resolve(record["asset_ref"]).path.read_bytes(), filetype="pdf") as document:
            metadata = document.metadata
        variant_matches = []
        for ref in refs:
            text = units[ref]["text"]
            for m in re.finditer(r"附录[：:]\s*第\s*([一二三四五六七八九十百]+)回", text):
                variant_matches.append({"chapter": chapter_number(m[1]), "unit_ref": ref, "start": m.start(), "end": m.end(), "label": m[0]})
        return {
            "unit_count": len(units), "metadata": metadata,
            "edition_evidence": self.evidence(record, units), "chapters": chapters,
            "unselected_units": [ref for ref in units if ref not in refs],
            "excluded_sections": [
                {"role": "FRONT_MATTER", "units": [ref for ref in units if int(ref.rsplit(":", 1)[1]) < start]},
                {"role": "APPENDIX", "units": [ref for ref in units if int(ref.rsplit(":", 1)[1]) > end]},
            ],
            "embedded_variants": variant_matches,
            "body_scope": record["body_pages"],
            "limitations": ["Slices retain page headers, commentary, variant text and editorial material; MAIN_TEXT classification is pending.",
                            "PDF metadata dates describe the file and do not establish the edition date."],
        }, views

    def epub(self, record: dict, units: dict) -> tuple[dict, dict[int, str]]:
        raw = self.catalog.resolve(record["asset_ref"]).path.read_bytes()
        chapters, views, spine, images, variant_candidates = [], {}, [], [], []
        with ZipFile(io.BytesIO(raw)) as archive:
            container = ET.fromstring(archive.read("META-INF/container.xml"))
            opf_path = next(e.attrib["full-path"] for e in container.iter() if e.tag.rsplit("}", 1)[-1] == "rootfile")
            package = ET.fromstring(archive.read(opf_path))
            metadata = [{"field": e.tag.rsplit("}", 1)[-1], "text": e.text, "attributes": e.attrib}
                        for meta in package if meta.tag.rsplit("}", 1)[-1] == "metadata" for e in meta]
            for order, (ref, unit) in enumerate(units.items(), 1):
                member = ref.removeprefix("epub:")
                member_raw = archive.read(member)
                parser = StructureParser(member_raw.decode("utf-8")); parser.feed(parser.source); parser.close()
                if "".join(parser.chunks) != unit["text"]:
                    raise AssetError("STRUCTURE_TEXT_MAPPING_MISMATCH")
                labels = [h for h in parser.headings if HEADING.fullmatch(h["text"].strip())]
                if len(labels) > 1:
                    raise AssetError(f"AMBIGUOUS_EPUB_CHAPTER: {ref}")
                chapter = chapter_number(HEADING.fullmatch(labels[0]["text"].strip())[1]) if labels else None
                spine.append({"order": order, "unit_ref": ref, "member_sha256": digest(member_raw),
                              "chapter": chapter, "headings": parser.headings})
                if chapter is not None:
                    row, view = chapter_record(chapter, [{"unit_ref": ref, "start": 0, "end": len(unit["text"])}], units)
                    chapters.append(row); views[chapter] = view
                    # Repeated chapter labels inside one spine member are candidates,
                    # not automatically another chapter or adopted variant.
                    for match in HEADING.finditer(unit["text"]):
                        if match.start() != labels[0]["start"]:
                            variant_candidates.append({"unit_ref": ref, "chapter": chapter_number(match[1]),
                                                       "start": match.start(), "end": match.end(),
                                                       "context": unit["text"][max(0, match.start() - 40):match.end() + 55]})
                for image in parser.images:
                    src = urlsplit(image["src"] or "")
                    if src.scheme or src.netloc or not src.path:
                        raise AssetError(f"UNSUPPORTED_EPUB_IMAGE_REFERENCE: {ref}")
                    image_member = zip_path(posixpath.normpath(posixpath.join(posixpath.dirname(member), unquote(src.path))))
                    images.append({**image, "unit_ref": ref, "chapter": chapter, "member": image_member,
                                   "member_sha256": digest(archive.read(image_member)), "extracted_text": "", "ocr_applied": False})
        return {
            "unit_count": len(units), "package_path": opf_path, "metadata": metadata,
            "edition_evidence": self.evidence(record, units), "chapters": chapters,
            "spine": spine, "images": images, "font_patch_occurrences": sum(i["font_patch"] for i in images),
            "embedded_chapter_label_candidates": variant_candidates,
            "unselected_units": [s["unit_ref"] for s in spine if s["chapter"] is None],
            "limitations": ["Images, including font_patch witness labels, produce no text in the current extractor.",
                            "Chapter headings may contain embedded annotations; no annotation removal or OCR has been applied."],
        }, views

    def inventory(self, relative: str) -> dict[str, Any]:
        config = self.config(relative)
        result, views, manifests = {}, {}, {}
        for format_name in ("pdf", "epub"):
            record = config[format_name]
            manifests[format_name], units = self.load_input(record, format_name.upper())
            result[format_name], views[format_name] = getattr(self, format_name)(record, units)
            found = [row["chapter"] for row in result[format_name]["chapters"]]
            if found != config["expected_chapters"]:
                raise AssetError(f"CHAPTER_COVERAGE_MISMATCH: {format_name}: {found}")
        comparison = []
        for chapter in config["expected_chapters"]:
            left, right = views["pdf"][chapter], views["epub"][chapter]
            first = next((i for i, (a, b) in enumerate(zip(left, right)) if a != b), min(len(left), len(right)))
            equal = left == right
            comparison.append({"chapter": chapter, "equal": equal, "pdf_characters": len(left), "epub_characters": len(right),
                               "first_difference": None if equal else {"offset": first, "pdf": left[max(0, first - 12):first + 28], "epub": right[max(0, first - 12):first + 28]}})
        binding = {k: v for k, v in config.items() if k != "inventory_report"}
        return {
            "schema_version": 1, "input_set_id": config["id"], "input_config_sha256": digest(canonical_bytes(binding)),
            "inventory_code_sha256": code_digest("inputs.py"),
            "extractions": {name: {"id": m["id"], "extractor": m["extractor"], "output": m["output"]} for name, m in manifests.items()},
            "selection": binding, "witnesses": result, "comparison": comparison,
            "comparison_transform": "REMOVE_UNICODE_WHITESPACE_ONLY_FROM_MIXED_CHAPTER_SLICES",
            "edition_equivalence": "NOT_ESTABLISHED", "corpus_status": "NOT_BUILT", "authority_effect": "NONE",
        }

    def verify(self, relative: str, *, require_tracked: bool = False) -> dict[str, Any]:
        config = self.config(relative)
        binding = config["inventory_report"]
        if binding is None:
            raise AssetError("MISSING_REGISTERED_INPUT_INVENTORY")
        report = self.catalog.resolve(binding["asset_ref"])
        if report.sha256 != binding["sha256"] or self.catalog.assets[report.id]["kind"] != "REVIEW_RECORD":
            raise AssetError("INVALID_INPUT_INVENTORY_BINDING")
        inventory = self.inventory(relative)
        if report.path.read_bytes() != canonical_bytes(inventory):
            raise AssetError("STALE_INPUT_INVENTORY: rebuild the inventory and review a new immutable record")
        findings = self.catalog.validate(require_tracked=require_tracked)
        if require_tracked:
            tracked = subprocess.run(["git", "ls-files", "-z"], cwd=self.root, capture_output=True, check=False)
            required = {relative, "schemas/corpus_inputs.schema.json", "requirements/extraction.lock.json"}
            required.update(f"src/rcwh/corpus/{name}.py" for name in ("inputs", "extraction", "adapters"))
            required.update(f"schemas/{name}.schema.json" for name in ("extraction_config", "extraction_manifest", "extraction_unit"))
            files = set(tracked.stdout.decode().split("\0"))
            findings.extend(f"untracked corpus input dependency: {p}" for p in sorted(required - files))
        return {
            "status": "FAIL" if findings else "PASS", "scope": "FIXED_INPUT_SELECTION_AND_EXTRACTION_REBUILD",
            "input_set_id": config["id"], "findings": findings,
            "inventory_report": binding, "chapters_per_witness": len(config["expected_chapters"]),
            "main_asset_ref": config["pdf"]["asset_ref"], "comparison_asset_ref": config["epub"]["asset_ref"],
            "different_chapter_views": sum(not c["equal"] for c in inventory["comparison"]),
            "epub_font_patch_occurrences": inventory["witnesses"]["epub"]["font_patch_occurrences"],
            "pilot_chapters": config["pilot_chapters"], "edition_equivalence": inventory["edition_equivalence"],
            "corpus_status": "NOT_BUILT", "authority_effect": "NONE",
        }
