from __future__ import annotations

from copy import deepcopy
import io
import json
from pathlib import Path
import shutil
import socket
import subprocess
from zipfile import ZipFile, ZipInfo

import pytest

from rcwh.assets import AssetCatalog, AssetError
from rcwh.assets.ingest import AssetIntake
from rcwh.cli import main
from rcwh.corpus.extraction import ExtractionRepository, canonical_bytes
from rcwh.corpus.inputs import CorpusInputs
from test_source_extraction import extraction_repo


ROOT = Path(__file__).resolve().parents[1]
CONFIG = "data/corpus/inputs/pilot.json"


def samples():
    import pymupdf
    pdf = pymupdf.open()
    pdf.new_page().insert_text((72, 72), "Edition 2018")
    for chapter in ("一", "二"):
        pdf.new_page().insert_text((72, 72), f"第{chapter}回\n甲正文批注", fontname="china-s")
    raw_pdf = pdf.tobytes(); pdf.close()
    raw_epub = io.BytesIO()
    with ZipFile(raw_epub, "w") as archive:
        files = {
            "mimetype": b"application/epub+zip",
            "META-INF/container.xml": b'<container><rootfile full-path="OEBPS/book.opf"/></container>',
            "OEBPS/book.opf": b'<package><metadata><date>2016</date></metadata><manifest><item id="v" href="version.xhtml" media-type="application/xhtml+xml"/><item id="a" href="a.xhtml" media-type="application/xhtml+xml"/><item id="b" href="b.xhtml" media-type="application/xhtml+xml"/></manifest><spine><itemref idref="v"/><itemref idref="a"/><itemref idref="b"/></spine></package>',
            "OEBPS/version.xhtml": b'<html><body>Edition 2016</body></html>',
            "OEBPS/a.xhtml": '<html><body><h3>第一回</h3><h2>题<span>嵌批。</span>目</h2><p><img class="font_patch" alt="庚辰本" src="glyph.png"/>甲正文&nbsp;批注</p></body></html>'.encode(),
            "OEBPS/b.xhtml": '<html><body><h3>第二回</h3><p>乙正文</p></body></html>'.encode(),
            "OEBPS/glyph.png": b"retained image bytes",
        }
        for name, raw in files.items():
            archive.writestr(ZipInfo(name), raw)
    return raw_pdf, raw_epub.getvalue()


def save(root, config):
    path = root / CONFIG
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(config))


def bind_inventory(root, config):
    catalog = AssetCatalog.from_repo(root)
    inventory = CorpusInputs(catalog).inventory(CONFIG)
    path = root.parent / "inventory.json"
    path.write_bytes(canonical_bytes(inventory))
    receipt = AssetIntake(root).ingest(path, origin="test:input-inventory", kind="REVIEW_RECORD")
    config["inventory_report"] = {"asset_ref": receipt["asset_ref"], "sha256": receipt["sha256"]}
    save(root, config)
    return inventory


@pytest.fixture
def input_repo(extraction_repo):
    root = extraction_repo
    shutil.copyfile(ROOT / "schemas/corpus_inputs.schema.json", root / "schemas/corpus_inputs.schema.json")
    config = {"schema_version": 1, "id": "corpus-inputs:test:v1", "expected_chapters": [1, 2],
              "pilot_chapters": [1], "selection_reason": "Later declared PDF, earlier EPUB for comparison", "inventory_report": None}
    for name, raw in zip(("pdf", "epub"), samples()):
        file = root.parent / f"book.{name}"; file.write_bytes(raw)
        receipt = AssetIntake(root).ingest(file, origin=f"test:{name}", kind="PRIMARY_TEXT_CONTAINER")
        built = ExtractionRepository(AssetCatalog.from_repo(root)).build(receipt["asset_ref"])
        config[name] = {"asset_ref": receipt["asset_ref"], "sha256": receipt["sha256"],
                        "extraction_ref": built["manifest_ref"], "extraction_sha256": built["manifest_ref"].split(":")[-1],
                        "use": "MAIN" if name == "pdf" else "COMPARISON",
                        "edition_evidence": ["pdf:page:1"] if name == "pdf" else ["epub:OEBPS/version.xhtml"]}
    config["pdf"]["body_pages"] = [2, 3]
    save(root, config)
    inventory = bind_inventory(root, config)
    return root, config, inventory


def test_actual_offline_rebuild_spine_glyph_gaps_and_no_authority(input_repo, monkeypatch):
    root, config, inventory = input_repo
    before = deepcopy(AssetCatalog.from_repo(root).assets)
    def offline(*args, **kwargs):
        raise AssertionError("network access is forbidden")
    monkeypatch.setattr(socket, "create_connection", offline)
    monkeypatch.setattr(socket, "getaddrinfo", offline)
    inputs = CorpusInputs(AssetCatalog.from_repo(root))
    result = inputs.verify(CONFIG)
    assert result["status"] == "PASS"
    assert result["corpus_status"] == "NOT_BUILT" and result["authority_effect"] == "NONE"
    assert result["edition_equivalence"] == "NOT_ESTABLISHED"
    assert inventory["witnesses"]["epub"]["spine"][1]["headings"][1]["text"] == "题嵌批。目"
    image = inventory["witnesses"]["epub"]["images"][0]
    assert image["alt"] == "庚辰本" and image["extracted_text"] == "" and not image["ocr_applied"]
    assert image["dom_path"].endswith("/p[1]/img[1]")
    assert result["epub_font_patch_occurrences"] == 1
    assert inventory["witnesses"]["pdf"]["unselected_units"] == ["pdf:page:1"]
    assert inputs.inventory(CONFIG) == inventory
    assert AssetCatalog.from_repo(root).assets == before


@pytest.mark.parametrize("change,error", [
    (lambda c: c["pdf"].update(sha256="0" * 64), "INPUT_HASH_MISMATCH"),
    (lambda c: c["pdf"].update(extraction_ref=c["epub"]["extraction_ref"], extraction_sha256=c["epub"]["extraction_sha256"]), "EXTRACTION_MISMATCH"),
    (lambda c: c.update(selection_reason="Changed choice without new review"), "STALE_INPUT_INVENTORY"),
    (lambda c: c["pdf"].update(body_pages=[3, 2]), "INVALID_PDF_BODY_SCOPE"),
    (lambda c: c["pdf"].update(body_pages=[3, 3]), "CHAPTER_COVERAGE_MISMATCH"),
    (lambda c: c["epub"].update(edition_evidence=["epub:missing.xhtml"]), "MISSING_EDITION_EVIDENCE"),
    (lambda c: c.update(inventory_report=None), "MISSING_REGISTERED_INPUT_INVENTORY"),
    (lambda c: c["inventory_report"].update(sha256="0" * 64), "INVALID_INPUT_INVENTORY_BINDING"),
    (lambda c: c.update(inventory_report={"asset_ref": c["pdf"]["asset_ref"], "sha256": c["pdf"]["sha256"]}), "INVALID_INPUT_INVENTORY_BINDING"),
    (lambda c: c.update(pilot_chapters=[3]), "INVALID_PILOT_SCOPE"),
    (lambda c: c["epub"].update(use="MAIN"), "UNSUPPORTED_INPUT_SELECTION"),
    (lambda c: c["epub"].update(adopted=True), "INVALID_CORPUS_INPUTS"),
])
def test_fixed_inputs_fail_closed_on_binding_scope_or_review_changes(input_repo, change, error):
    root, config, _ = input_repo
    change(config); save(root, config)
    with pytest.raises(AssetError, match=error):
        CorpusInputs(AssetCatalog.from_repo(root)).verify(CONFIG)


def test_missing_carrier_and_mutated_epub_are_not_accepted(input_repo):
    root, config, _ = input_repo
    catalog = AssetCatalog.from_repo(root)
    epub = catalog.resolve(config["epub"]["asset_ref"])
    raw = epub.path.read_bytes()
    epub.path.unlink()
    with pytest.raises(AssetError, match="missing file"):
        CorpusInputs(catalog).verify(CONFIG)
    epub.path.write_bytes(raw + b"bookmark mutation")
    with pytest.raises(AssetError, match="byte mismatch"):
        CorpusInputs(catalog).verify(CONFIG)


def test_runtime_dependency_and_inventory_code_drift_preserve_content_binding(input_repo, monkeypatch):
    root, _, _ = input_repo
    original = ExtractionRepository.extractor
    def changed(self, format_name):
        result = original(self, format_name)
        return {**result, "python": "different runtime"}
    monkeypatch.setattr(ExtractionRepository, "extractor", changed)
    monkeypatch.setattr("rcwh.corpus.inputs.code_digest", lambda *args: "0" * 64)
    result = CorpusInputs(AssetCatalog.from_repo(root)).verify(CONFIG)
    assert result["status"] == "PASS" and result["toolchain_diff"]
    assert all(r["toolchain_diff"] for r in result["extraction_rebuilds"])


def test_omitted_or_repeated_epub_chapter_is_not_silently_counted(input_repo):
    root, config, _ = input_repo
    catalog = AssetCatalog.from_repo(root)
    original = catalog.resolve(config["epub"]["asset_ref"]).path.read_bytes()
    changed = io.BytesIO()
    with ZipFile(io.BytesIO(original)) as source, ZipFile(changed, "w") as target:
        for member in source.infolist():
            raw = source.read(member.filename)
            if member.filename == "OEBPS/b.xhtml":
                raw = raw.replace("第二回".encode(), "第一回".encode())
            target.writestr(member, raw)
    file = root.parent / "duplicate-chapter.epub"; file.write_bytes(changed.getvalue())
    receipt = AssetIntake(root).ingest(file, origin="test:duplicate-chapter", kind="PRIMARY_TEXT_CONTAINER")
    built = ExtractionRepository(AssetCatalog.from_repo(root)).build(receipt["asset_ref"])
    config["epub"].update(asset_ref=receipt["asset_ref"], sha256=receipt["sha256"],
                          extraction_ref=built["manifest_ref"], extraction_sha256=built["manifest_ref"].split(":")[-1])
    save(root, config)
    with pytest.raises(AssetError, match="CHAPTER_COVERAGE_MISMATCH"):
        CorpusInputs(AssetCatalog.from_repo(root)).inventory(CONFIG)


def test_cli_build_is_exclusive_and_tracked_gate_includes_input_config(input_repo, capsys, monkeypatch):
    root, _, _ = input_repo
    def run(arguments):
        monkeypatch.setattr("sys.argv", ["rcwh", "--root", str(root), *arguments])
        with pytest.raises(SystemExit) as result:
            main()
        return result.value.code
    assert run(["corpus", "inputs", CONFIG]) == 0
    assert json.loads(capsys.readouterr().out)["chapters_per_witness"] == 2
    output = root.parent / "new-inventory.json"
    args = ["corpus", "input-inventory", CONFIG, "--output", str(output)]
    assert run(args) == 0
    capsys.readouterr()
    assert run(args) == 1
    assert "File exists" in capsys.readouterr().out
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    result = CorpusInputs(AssetCatalog.from_repo(root)).verify(CONFIG, require_tracked=True)
    assert result["status"] == "FAIL"
    assert f"untracked corpus input dependency: {CONFIG}" in result["findings"]
