from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import shutil

import pymupdf
import pytest

from rcwh.assets import AssetCatalog, AssetError
from rcwh.assets.ingest import AssetIntake
from rcwh.assets.transactions import digest
from rcwh.corpus.dataset import CorpusRepository
from rcwh.corpus.extraction import ExtractionRepository, canonical_bytes, validate
from rcwh.corpus.inputs import CorpusInputs
from rcwh.corpus.layers import classify, pdf_runs
from test_corpus_dataset import BUILD, INPUTS, corpus_repo, rows
from test_corpus_inputs import samples
from test_source_extraction import extraction_repo


ROOT = Path(__file__).resolve().parents[1]
RULES = {"top_band_fraction": 0.11, "bottom_band_fraction": 0.10,
         "page_number_patterns": [r"[0-9]{1,4}"], "running_headers": ["Declared Header"]}


def save(root, config):
    (root / BUILD).write_bytes(canonical_bytes(config))


@pytest.fixture
def furniture_repo(extraction_repo):
    root = extraction_repo
    for schema in ("corpus_build", "corpus_segment", "corpus_inputs", "corpus_manifest", "corpus_dataset"):
        shutil.copyfile(ROOT / f"schemas/{schema}.schema.json", root / f"schemas/{schema}.schema.json")
    with pymupdf.open() as pdf:
        pdf.new_page().insert_text((72, 72), "Edition and style legend")
        page = pdf.new_page()
        page.insert_text((72, 100), "第一回", fontname="china-s", fontsize=20)
        page.insert_text((72, 125), "甲正文。", fontname="china-s", fontsize=14)
        # Extraction order, not geometric order, defines the declared variant boundary.
        page.insert_text((72, 160), "附录：第一回 异文。", fontname="china-s", fontsize=10)
        page.insert_text((72, 200), "普通小字异文。", fontname="china-s", fontsize=8)
        page.insert_text((72, 235), "123", fontsize=8)
        page.insert_text((72, 270), "Declared Header", fontsize=8)
        page.insert_text((72, 805), "17", fontsize=8)
        # Adjacent differently styled spans must match as a single line.
        page.insert_text((72, 55), "Declared ", fontsize=8)
        page.insert_text((72 + pymupdf.get_text_length("Declared ", fontsize=8), 55), "Header", fontsize=8, color=(1, 0, 0))
        page.insert_text((72, 70), "Undeclared Header", fontsize=8)
        for is_appendix in (False, True):
            page = pdf.new_page()
            if not is_appendix:
                page.insert_text((72, 100), "第二回", fontname="china-s", fontsize=20)
            page.insert_text((72, 130), "乙正文。", fontname="china-s", fontsize=14)
            page.insert_text((72, 170), "普通小字附录。", fontname="china-s", fontsize=8)
            page.insert_text((72, 200), "123", fontsize=8)
            page.insert_text((72, 240), "Declared Header", fontsize=8)
            page.insert_text((72, 55), "Declared Header", fontsize=14)
            page.insert_text((72, 70), "Undeclared Header", fontsize=8)
            page.insert_text((72, 805), "18", fontsize=14)
        raw_pdf = pdf.tobytes()
        font = pdf[1].get_text("dict")["blocks"][1]["lines"][0]["spans"][0]["font"]
    inputs = {"schema_version": 1, "id": "corpus-inputs:test:furniture:v1", "expected_chapters": [1, 2],
              "pilot_chapters": [1, 2], "selection_reason": "Declared test inputs", "inventory_report": None}
    for name, raw in (("pdf", raw_pdf), ("epub", samples()[1])):
        path = root.parent / f"furniture.{name}"
        path.write_bytes(raw)
        receipt = AssetIntake(root).ingest(path, origin=f"test:furniture:{name}", kind="PRIMARY_TEXT_CONTAINER")
        manifest = ExtractionRepository(AssetCatalog.from_repo(root)).build(receipt["asset_ref"])
        inputs[name] = {"asset_ref": receipt["asset_ref"], "sha256": receipt["sha256"],
                        "extraction_ref": manifest["manifest_ref"], "extraction_sha256": manifest["manifest_ref"].split(":")[-1],
                        "use": "MAIN" if name == "pdf" else "COMPARISON",
                        "edition_evidence": ["pdf:page:1"] if name == "pdf" else ["epub:OEBPS/version.xhtml"]}
    inputs["pdf"]["body_pages"] = [2, 3]
    (root / INPUTS).parent.mkdir(parents=True)
    (root / INPUTS).write_bytes(canonical_bytes(inputs))
    inventory = CorpusInputs(AssetCatalog.from_repo(root)).inventory(INPUTS)
    path = root.parent / "furniture-inventory.json"
    path.write_bytes(canonical_bytes(inventory))
    receipt = AssetIntake(root).ingest(path, origin="test:furniture:inventory", kind="REVIEW_RECORD")
    inputs["inventory_report"] = {"asset_ref": receipt["asset_ref"], "sha256": receipt["sha256"]}
    (root / INPUTS).write_bytes(canonical_bytes(inputs))
    _, units = ExtractionRepository(AssetCatalog.from_repo(root)).load(inputs["pdf"]["extraction_ref"])
    config = {"schema_version": 2, "dataset_ref": "corpus:front80:test:furniture:v2", "scope": "PILOT",
              "inputs": {"path": INPUTS, "sha256": digest((root / INPUTS).read_bytes())}, "chapters": [1, 2],
              "appendices": [{"section_ref": "appendix:test", "pages": [4, 4]}],
              "variant_starts": [{"chapter": 1, "unit_ref": "pdf:page:2", "offset": units["pdf:page:2"]["text"].index("附录："), "expected_prefix": "附录：第一回"}],
              "layer_policy": {"evidence_units": ["pdf:page:1"], "main_color": 0, "annotation_colors": [16711680],
                               "annotation_fonts": [font], "main_fonts": [font, "Helvetica"], "main_size_range": [13, 17],
                               "watermark_fonts": [], "witness_labels": {"庚": "庚辰本"}, "page_furniture": deepcopy(RULES)}}
    (root / BUILD).parent.mkdir(parents=True)
    save(root, config)
    return root, config, inputs, units


def compile_rows(root):
    manifest, products = CorpusRepository(AssetCatalog.from_repo(root)).compile(BUILD)
    return manifest, products, rows(products["segments.jsonl"])


def test_v1_bytes_and_segmentation_unchanged_without_new_policy(corpus_repo):
    root, config, _ = corpus_repo
    manifest, products, segments = compile_rows(root)
    assert manifest["builder"]["version"] == 1
    assert all(s["classification"]["method"] == "DECLARED_PDF_TYPOGRAPHY_V1" for s in segments)
    config["schema_version"] = 2
    save(root, config)
    v2_manifest, v2_products, _ = compile_rows(root)
    assert v2_manifest["builder"]["version"] == 1
    for name, raw in products.items():
        expected = raw.replace(b"DECLARED_PDF_TYPOGRAPHY_V1", b"DECLARED_PDF_TYPOGRAPHY_V2") if name == "segments.jsonl" else raw
        assert v2_products[name] == expected


def test_v1_run_shape_stays_frozen_and_v2_adds_only_line_context():
    with pymupdf.open() as pdf:
        page = pdf.new_page()
        page.insert_text((72, 55), "Declared ", fontsize=8)
        page.insert_text((72 + pymupdf.get_text_length("Declared ", fontsize=8), 55), "Header", fontsize=8, color=(1, 0, 0))
        expected = page.get_text()
        v1 = pdf_runs(pdf, 1, expected)
        v2 = pdf_runs(pdf, 1, expected, include_line_context=True)
        assert all(set(run) == {"start", "end", "text", "style", "bbox"} for run in v1)
        assert [{k: v for k, v in run.items() if k != "line"} for run in v2] == v1
        assert len(v2) == 3 and all(r["line"]["text"] == "Declared Header" for r in v2)


@pytest.mark.parametrize("change", [
    lambda c: c.update(schema_version=1),
    lambda c: c.update(schema_version=3),
    lambda c: c["layer_policy"]["page_furniture"].update(running_header=["typo"]),
    lambda c: c["layer_policy"]["page_furniture"].update(top_band_fraction=0.5),
    lambda c: c["layer_policy"]["page_furniture"].pop("page_number_patterns"),
    lambda c: c["layer_policy"]["page_furniture"].update(running_headers=[" header\nbody"]),
])
def test_schema_rejects_v1_new_rules_and_malformed_rules(corpus_repo, change):
    root, config, _ = corpus_repo
    config["schema_version"] = 2
    config["layer_policy"]["page_furniture"] = deepcopy(RULES)
    change(config)
    with pytest.raises(AssetError, match="INVALID_CORPUS_BUILD"):
        validate(root, config, "corpus_build")


@pytest.mark.parametrize("pattern,error", [("[", "INVALID_PAGE_FURNITURE_PATTERN"), (".*", "EMPTY_PAGE_FURNITURE_PATTERN")])
def test_bad_regex_fails_before_compile(corpus_repo, pattern, error):
    root, config, _ = corpus_repo
    config["schema_version"] = 2
    config["layer_policy"]["page_furniture"] = {**RULES, "page_number_patterns": [pattern]}
    save(root, config)
    with pytest.raises(AssetError, match=error):
        CorpusRepository(AssetCatalog.from_repo(root)).config(BUILD)


def test_edge_lines_isolated_without_demoting_variant_or_body(furniture_repo):
    root, config, inputs, units = furniture_repo
    manifest, products, segments = compile_rows(root)
    assert manifest["builder"]["version"] == 1
    assert all(s["classification"]["method"] == "DECLARED_PDF_TYPOGRAPHY_V2" for s in segments)
    furniture = [s for s in segments if any("EDGE_STRIP" in r for r in s["classification"]["reasons"])]
    assert {s["text"].strip() for s in furniture} == {"17", "18", "Declared Header"}
    assert len(furniture) == 4
    header = next(s for s in furniture if s["chapter"] == 1 and s["text"] == "Declared Header\n")
    assert len(header["classification"]["styles"]) == 2
    assert len(header["locator"]["spans"]) == 1
    for segment in furniture:
        assert len(segment["locator"]["spans"]) == 1
        span = segment["locator"]["spans"][0]
        text = units[span["unit_ref"]]["text"]
        assert span["start"] == 0 or text[span["start"] - 1] == "\n"
        assert text[span["end"] - 1] == "\n"
    assert all(s["kind"] == "EDITORIAL" and s["chapter"] != 2 for s in furniture)
    for segment in segments:
        reconstructed = "".join(units[s["unit_ref"]]["text"][s["start"]:s["end"]] for s in segment["locator"]["spans"])
        assert segment["text"] == reconstructed
        assert segment["text_sha256"] == digest(reconstructed.encode())
        assert segment["locator"]["transforms"] == []
    assert any("普通小字异文。" in s["text"] and "123" in s["text"] and "Declared Header" in s["text"] and s["kind"] == "VARIANT" for s in segments)
    assert any("普通小字附录。" in s["text"] and "123" in s["text"] and "Declared Header" in s["text"] and s["kind"] == "APPENDIX" for s in segments)
    assert any("Undeclared Header" in s["text"] and s["kind"] == "VARIANT" for s in segments)
    assert any("Undeclared Header" in s["text"] and s["kind"] == "APPENDIX" for s in segments)
    config["schema_version"] = 1
    config["layer_policy"].pop("page_furniture")
    save(root, config)
    _, v1_products, v1_segments = compile_rows(root)
    for chapter in (1, 2):
        assert products[f"chapters/ch{chapter:02d}.json"] == v1_products[f"chapters/ch{chapter:02d}.json"]
    assert [s for s in segments if s["chapter"] == 2] == [
        {**s, "classification": {**s["classification"], "method": "DECLARED_PDF_TYPOGRAPHY_V2"}}
        for s in v1_segments if s["chapter"] == 2]
    for kind in ("VARIANT", "APPENDIX"):
        old_text = "".join(s["text"] for s in v1_segments if s["kind"] == kind)
        new_text = "".join(s["text"] for s in segments if s["kind"] == kind or s in furniture and
                           (s["chapter"] is None if kind == "APPENDIX" else s["chapter"] == 1))
        assert old_text == new_text


def test_partial_variant_line_is_not_page_furniture(furniture_repo):
    root, config, _, units = furniture_repo
    # A boundary inside an edge line must not authorize demotion of its tail.
    offset = units["pdf:page:2"]["text"].index("Declared Header", units["pdf:page:2"]["text"].index("17"))
    config["variant_starts"][0].update(offset=offset + len("Declared "), expected_prefix="Header")
    save(root, config)
    _, _, segments = compile_rows(root)
    assert not any("RUNNING_HEADER_LINE" in r for s in segments if s["chapter"] == 1 for r in s["classification"]["reasons"])
    assert any("Header" in s["text"] and s["kind"] == "VARIANT" for s in segments if s["chapter"] == 1)


@pytest.mark.parametrize("version,variant,appendix,in_scope", [(1, True, False, True), (2, False, False, True), (2, True, False, False)])
def test_new_rule_requires_v2_declared_scope_and_whole_line(version, variant, appendix, in_scope):
    policy = {"watermark_fonts": [], "main_color": 0, "main_fonts": ["Helvetica"], "main_size_range": [13, 17],
              "annotation_colors": [16711680], "annotation_fonts": ["Other"], "page_furniture": RULES}
    run = {"text": "123", "style": {"font": "Helvetica", "size": 14, "color": 0},
           "line": {"text": "123", "bbox": [10, 780, 30, 790], "page_bbox": [0, 0, 595, 842]}}
    kind, reason = classify(run, policy, variant=variant, appendix=appendix, schema_version=version, line_in_scope=in_scope)
    assert kind == ("VARIANT" if variant else "MAIN_TEXT") and "EDGE_STRIP" not in reason


@pytest.mark.parametrize("text,bbox,expected", [
    ("123正文", [10, 780, 80, 790], "VARIANT"),
    ("Declared Header extra", [10, 50, 80, 60], "VARIANT"),
    ("123", [10, 730, 80, 780], "VARIANT"),
    ("Declared Header", [10, 50, 80, 100], "VARIANT"),
    ("123", [10, 780, 80, 790], "EDITORIAL"),
])
def test_matching_is_whole_line_and_whole_bbox_not_run_font(text, bbox, expected):
    policy = {"watermark_fonts": [], "main_color": 0, "main_fonts": ["Helvetica"], "main_size_range": [13, 17],
              "annotation_colors": [16711680], "annotation_fonts": ["Other"], "page_furniture": RULES}
    run = {"text": "123", "style": {"font": "UnknownSmallFont", "size": 8, "color": 0},
           "line": {"text": text, "bbox": bbox, "page_bbox": [0, 0, 595, 842]}}
    kind, _ = classify(run, policy, variant=True, appendix=False, schema_version=2, line_in_scope=True)
    assert kind == expected


def test_candidate_is_additive_and_conservative():
    v1 = json.loads((ROOT / "data/corpus/builds/front80-v1-candidate.json").read_bytes())
    v2 = json.loads((ROOT / "data/corpus/builds/front80-v2-candidate.json").read_bytes())
    validate(ROOT, v2, "corpus_build")
    assert v2["dataset_ref"] != v1["dataset_ref"] and v2["schema_version"] == 2
    assert v2["layer_policy"]["page_furniture"]["running_headers"] == ["撫琴居红楼梦脂评汇校本"]
    del v2["layer_policy"]["page_furniture"]
    v2.update(schema_version=1, dataset_ref=v1["dataset_ref"])
    assert v2 == v1
