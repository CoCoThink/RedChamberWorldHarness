from __future__ import annotations

from copy import deepcopy
import io
import json
import platform
from pathlib import Path
import shutil
import subprocess
from zipfile import ZipFile, ZipInfo

import pytest
import yaml

from rcwh.assets import AssetCatalog, AssetError, CatalogStore
from rcwh.assets.ingest import AssetIntake
from rcwh.assets.transactions import digest
from rcwh.cli import main
from rcwh.corpus.extraction import ExtractionConfigError, ExtractionRepository, canonical_bytes
from rcwh.corpus.locators import SourceLocatorVerifier
from rcwh.provenance import ProvenanceRepository


ROOT = Path(__file__).resolve().parents[1]


def make_epub(*, duplicate=False, outside=False):
    output = io.BytesIO()
    with ZipFile(output, "w") as archive:
        files = {
            "mimetype": "application/epub+zip",
            "META-INF/container.xml": '<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles><rootfile full-path="OEBPS/content.opf"/></rootfiles></container>',
            "OEBPS/content.opf": '<package xmlns="http://www.idpf.org/2007/opf"><manifest><item id="b" href="second.xhtml" media-type="application/xhtml+xml"/><item id="a" href="first.xhtml" media-type="application/xhtml+xml"/></manifest><spine><itemref idref="a"/><itemref idref="b"/></spine></package>',
            "OEBPS/first.xhtml": '<html><head><title>第一章</title></head><body><p>甲😀&nbsp;乙<br/>引文材料</p></body></html>',
            "OEBPS/second.xhtml": '<html><body><p>末章</p></body></html>',
        }
        if outside:
            files["../outside.txt"] = "escape"
        for name, text in files.items():
            archive.writestr(ZipInfo(name), text.encode("utf-8"))
        if duplicate:
            with pytest.warns(UserWarning):
                archive.writestr(ZipInfo("OEBPS/first.xhtml"), b"duplicate")
    return output.getvalue()


def make_pdf(*, empty=False):
    import pymupdf
    document = pymupdf.open()
    page = document.new_page()
    if not empty:
        page.insert_text((72, 72), "Alpha original")
        document.new_page().insert_text((72, 72), "Beta excerpt")
    raw = document.tobytes()
    document.close()
    return raw


@pytest.fixture
def extraction_repo(tmp_path):
    root = tmp_path / "repo"
    (root / "schemas").mkdir(parents=True)
    for name in (
        "asset_catalog", "asset_origin", "asset_receipt", "source", "implementation", "extraction_config",
        "extraction_manifest", "extraction_unit", "locator_v2", "source_locator_report",
        "source_capture", "source_migration_plan",
        "source_excerpt_correction_plan", "source_excerpt_review",
    ):
        shutil.copyfile(ROOT / f"schemas/{name}.schema.json", root / f"schemas/{name}.schema.json")
    (root / "requirements").mkdir()
    shutil.copyfile(ROOT / "requirements/extraction.lock.json", root / "requirements/extraction.lock.json")
    (root / "sources").mkdir()
    raw = b"Initial fixed asset"
    (root / "sources/initial.txt").write_bytes(raw)
    sha = digest(raw)
    asset = {
        "id": "asset:test:initial", "path": "sources/initial.txt", "sha256": sha, "bytes": len(raw),
        "media_type": "text/plain", "kind": "PROJECT_REFERENCE", "immutable": True, "origin_refs": ["origin:test:initial"],
    }
    origin = {
        "id": "origin:test:initial", "asset_ref": asset["id"], "sha256": sha, "batch_id": "test",
        "origin_type": "TEST", "origin_container": "test", "original_path": "initial.txt", "disposition": "RETAINED",
    }
    (root / "data/catalog").mkdir(parents=True)
    for path, data in CatalogStore(root).serialized_records({asset["id"]: asset}, {origin["id"]: origin}).items():
        (root / path).write_bytes(data)
    return root


def receive(root, format_name, *, raw=None):
    samples = {
        "TEXT": ("sample.txt", "序😀\r\n引文材料\r\n末行".encode("utf-8"), "引文材料"),
        "HTML": ("sample.html", '<html><head><title>Ignore</title><script>hidden</script></head><body><p>甲😀&amp;乙<br/>引文材料</p><p> 末行 </p></body></html>'.encode(), "引文材料"),
        "EPUB": ("sample.epub", make_epub(), "引文材料"),
        "PDF": ("sample.pdf", make_pdf(), "Beta excerpt"),
    }
    filename, sample, quote = samples[format_name]
    file = root.parent / filename
    file.write_bytes(sample if raw is None else raw)
    receipt = AssetIntake(root).ingest(file, origin=f"test:{format_name}", kind="PRIMARY_TEXT_CONTAINER")
    return receipt["asset_ref"], receipt["sha256"], quote


def write_source(root, source):
    directory = root / "data/provenance/sources"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "test.yaml").write_text(yaml.safe_dump({"schema_version": 1, "sources": [source]}, allow_unicode=True), encoding="utf-8")


def setup_source(root, format_name="TEXT"):
    asset_ref, sha, quote = receive(root, format_name)
    built = ExtractionRepository(AssetCatalog.from_repo(root)).build(asset_ref)
    source = {
        "id": "src:test:quote", "type": "NOVEL_TEXT", "title": "Test quote", "witness": {"label": "fixed witness"},
        "container": {"ref": asset_ref, "sha256": sha}, "locator": {"legacy_lines": "unknown"},
        "text": quote, "text_sha256": digest(quote.encode()),
        "locator_verification": {"status": "UNVERIFIED", "reason": "no alignment yet"},
    }
    proposal = SourceLocatorVerifier(AssetCatalog.from_repo(root)).locate(source, built["manifest_ref"])
    assert proposal["status"] == "PASS"
    source["locator"] = proposal["locator"]
    write_source(root, source)
    return built, source


@pytest.mark.parametrize("format_name", ["TEXT", "HTML", "EPUB", "PDF"])
def test_fixed_extraction_and_actual_source_verification_round_trip(extraction_repo, format_name):
    root = extraction_repo
    built, source = setup_source(root, format_name)
    catalog = AssetCatalog.from_repo(root)
    repository = ExtractionRepository(catalog)
    manifest, units = repository.load(built["manifest_ref"], rebuild=True)
    assert manifest["config"]["format"] == format_name
    assert all(item["input"] == manifest["input"] for item in units.values())
    assert catalog.validate() == []
    before = {key: deepcopy(value) for key, value in catalog.assets.items()}
    again = repository.build(source["container"]["ref"])
    assert again == built
    assert AssetCatalog.from_repo(root).assets == before
    verification = ProvenanceRepository.from_repo(root).verify_all()
    assert verification["status"] == "PASS"
    assert verification["unverified_locators"] == verification["missing_carriers"] == 0
    report = verification["sources"][0]["verification_report"]
    assert report["raw_excerpt"] == source["text"]
    assert report["expected_text_sha256"] == source["text_sha256"]
    assert ProvenanceRepository.from_repo(root).trace(source["id"])["locator_status"] == "VERIFIED"


def test_existing_output_identity_is_preserved_in_recipe_and_rebuild(extraction_repo):
    root = extraction_repo
    asset_ref, _, _ = receive(root, "TEXT")
    _, raw = ExtractionRepository(AssetCatalog.from_repo(root)).compile(asset_ref)
    output_ref = "asset:test:previous-extraction"
    sha = digest(raw)
    path = "corpus/previous-units.jsonl"
    (root / "corpus").mkdir()
    (root / path).write_bytes(raw)
    store = CatalogStore(root)
    assets, origins = store.read()
    assets[output_ref] = {
        "id": output_ref, "path": path, "sha256": sha, "bytes": len(raw),
        "media_type": "application/x-ndjson", "kind": "CORPUS_DERIVATIVE", "immutable": True,
        "origin_refs": ["origin:test:previous-extraction"], "derived_from": [asset_ref],
    }
    origins["origin:test:previous-extraction"] = {
        "id": "origin:test:previous-extraction", "asset_ref": output_ref, "sha256": sha,
        "batch_id": "test", "origin_type": "TEST", "origin_container": asset_ref,
        "original_path": path, "disposition": "RETAINED",
    }
    for relative, data in store.serialized_records(assets, origins).items():
        (root / relative).write_bytes(data)
    built = ExtractionRepository(AssetCatalog.from_repo(root)).build(asset_ref)
    assert built["manifest"]["output"]["asset_ref"] == output_ref
    catalog = AssetCatalog.from_repo(root)
    assert catalog.validate() == []
    assert sum(record["sha256"] == sha for record in catalog.assets.values()) == 1
    assert ExtractionRepository(catalog).load(built["manifest_ref"])[0] == built["manifest"]
    assert ExtractionRepository(catalog).build(asset_ref) == built


def test_text_newlines_unicode_and_character_offsets_are_preserved(extraction_repo):
    root = extraction_repo
    built, source = setup_source(root)
    _, units = ExtractionRepository(AssetCatalog.from_repo(root)).load(built["manifest_ref"])
    text = units["text:1"]["text"]
    assert text == "序😀\r\n引文材料\r\n末行"
    assert source["locator"]["spans"] == [{"unit_ref": "text:1", "start": 4, "end": 8}]
    assert len(text[:4].encode("utf-8")) != 4


def test_markup_nodes_and_epub_spine_order_remain_visible(extraction_repo):
    root = extraction_repo
    built, _ = setup_source(root, "EPUB")
    manifest, units = ExtractionRepository(AssetCatalog.from_repo(root)).load(built["manifest_ref"])
    assert manifest["unit_refs"] == ["epub:OEBPS/first.xhtml", "epub:OEBPS/second.xhtml"]
    first = units[manifest["unit_refs"][0]]
    assert first["text"] == "甲😀\u00a0乙\n引文材料"
    assert "第一章" not in first["text"]
    entity = next(node for node in first["nodes"] if node["origin"]["kind"] == "ENTITY")
    assert entity["origin"]["dom_path"] == "/html[1]/body[1]/p[1]"
    assert first["text"][entity["start"]:entity["end"]] == "\u00a0"
    assert any(node["origin"]["kind"] == "BR_TO_LF" for node in first["nodes"])


def test_pdf_selection_uses_physical_pages_and_keeps_newlines(extraction_repo):
    root = extraction_repo
    asset_ref, _, _ = receive(root, "PDF")
    repository = ExtractionRepository(AssetCatalog.from_repo(root))
    built = repository.build(asset_ref, {"pdf_pages": [2]})
    _, units = ExtractionRepository(AssetCatalog.from_repo(root)).load(built["manifest_ref"])
    assert list(units) == ["pdf:page:2"]
    assert units["pdf:page:2"]["text"] == "Beta excerpt\n"
    assert units["pdf:page:2"]["nodes"][0]["origin"]["pdf_page"] == 2
    with pytest.raises(AssetError, match="OUT_OF_RANGE"):
        repository.build(asset_ref, {"pdf_pages": [3]})
    with pytest.raises(ExtractionConfigError, match="ascending"):
        repository.build(asset_ref, {"pdf_pages": [2, 1]})


@pytest.mark.parametrize("format_name,raw,error", [
    ("PDF", b"broken pdf", "INVALID_PDF"),
    ("PDF", make_pdf(empty=True), "NO_EXTRACTABLE_TEXT"),
    ("EPUB", b"not a zip", "INVALID_EPUB"),
    ("EPUB", make_epub(outside=True), "UNSAFE_EPUB_MEMBER"),
    ("EPUB", make_epub(duplicate=True), "DUPLICATE_EPUB_MEMBER"),
    ("HTML", b"<html><head><script>only script</script></head><body></body></html>", "NO_EXTRACTABLE_TEXT"),
    ("TEXT", b"\xff\xfe", "INVALID_UTF8"),
])
def test_bad_inputs_fail_without_registering_outputs(extraction_repo, format_name, raw, error):
    root = extraction_repo
    asset_ref, _, _ = receive(root, format_name, raw=raw)
    before = deepcopy(AssetCatalog.from_repo(root).assets)
    with pytest.raises(AssetError, match=error):
        ExtractionRepository(AssetCatalog.from_repo(root)).build(asset_ref, {"format": format_name})
    assert AssetCatalog.from_repo(root).assets == before


@pytest.mark.parametrize("mutation,error", [
    (lambda s: s["locator"]["spans"][0].update(end=9999), "OUT_OF_RANGE"),
    (lambda s: s["locator"]["spans"][0].update(unit_ref="missing"), "UNKNOWN_TEXT_UNIT"),
    (lambda s: s["locator"].update(output_sha256="0" * 64), "OUTPUT_HASH_MISMATCH"),
    (lambda s: s["locator"].update(raw_text_sha256="0" * 64), "EXCERPT_HASH_MISMATCH"),
    (lambda s: s["locator"].update(kind="PDF_TEXT_SPANS"), "FORMAT_MISMATCH"),
    (lambda s: s["locator"].update(joiner="invented words"), "INVALID_LOCATOR_V2"),
    (lambda s: s.update(text="伪造引文", text_sha256=digest("伪造引文".encode())), "EXCERPT_MISMATCH"),
])
def test_locator_drift_and_fabricated_text_cannot_pass(extraction_repo, mutation, error):
    root = extraction_repo
    _, source = setup_source(root)
    mutation(source)
    result = SourceLocatorVerifier(AssetCatalog.from_repo(root)).verify(source)
    assert result["status"] == "FAIL"
    assert any(error in finding for finding in result["findings"])


def test_explicit_multiple_spans_must_be_ordered_and_nonoverlapping(extraction_repo):
    root = extraction_repo
    built, source = setup_source(root)
    source.update(text="引文…末行", text_sha256=digest("引文…末行".encode()))
    source["locator"].update(
        spans=[{"unit_ref": "text:1", "start": 4, "end": 6}, {"unit_ref": "text:1", "start": 10, "end": 12}],
        joiner="…", raw_text_sha256=source["text_sha256"],
    )
    verifier = SourceLocatorVerifier(AssetCatalog.from_repo(root))
    assert verifier.verify(source)["status"] == "PASS"
    source["locator"]["spans"].reverse()
    assert "OVERLAPPING_OR_REORDERED_SPANS" in verifier.verify(source)["findings"]


def test_pdf_line_break_proposal_records_explicit_spans_without_changing_excerpt(extraction_repo):
    root = extraction_repo
    import pymupdf
    document = pymupdf.open()
    document.new_page().insert_text((72, 72), "Alpha\nBeta")
    raw = document.tobytes()
    document.close()
    asset_ref, sha, _ = receive(root, "PDF", raw=raw)
    built = ExtractionRepository(AssetCatalog.from_repo(root)).build(asset_ref)
    source = {
        "id": "src:test:wrapped", "type": "NOVEL_TEXT", "title": "Wrapped PDF", "witness": {"label": "test"},
        "container": {"ref": asset_ref, "sha256": sha}, "text": "AlphaBeta", "text_sha256": digest(b"AlphaBeta"),
        "locator": {}, "locator_verification": {"status": "UNVERIFIED", "reason": "pending"},
    }
    verifier = SourceLocatorVerifier(AssetCatalog.from_repo(root))
    before = deepcopy(source)
    assert verifier.locate(source, built["manifest_ref"])["findings"] == ["EXCERPT_NOT_FOUND"]
    proposal = verifier.locate(source, built["manifest_ref"], allow_line_break_spans=True)
    assert proposal["status"] == "PASS" and source == before
    assert len(proposal["locator"]["spans"]) == 2
    assert proposal["verification_report"]["raw_excerpt"] == "AlphaBeta"
    source["text"] = "Alpha Beta"
    source["text_sha256"] = digest(b"Alpha Beta")
    assert verifier.locate(source, built["manifest_ref"], allow_line_break_spans=True)["status"] == "FAIL"


def test_ambiguous_exact_matches_are_not_automatically_selected(extraction_repo):
    root = extraction_repo
    asset_ref, sha, quote = receive(root, "TEXT", raw="引文材料\n引文材料".encode())
    built = ExtractionRepository(AssetCatalog.from_repo(root)).build(asset_ref)
    source = {"id": "src:test", "container": {"ref": asset_ref, "sha256": sha}, "text": quote, "text_sha256": digest(quote.encode())}
    located = SourceLocatorVerifier(AssetCatalog.from_repo(root)).locate(source, built["manifest_ref"])
    assert located["status"] == "FAIL" and located["findings"] == ["AMBIGUOUS_LOCATOR"]
    assert len(located["candidates"]) == 2
    source.update(text="does not occur", text_sha256=digest(b"does not occur"))
    assert SourceLocatorVerifier(AssetCatalog.from_repo(root)).locate(source, built["manifest_ref"])["findings"] == ["EXCERPT_NOT_FOUND"]


def test_wrong_carrier_cannot_use_another_extraction(extraction_repo):
    root = extraction_repo
    _, source = setup_source(root)
    source["container"] = {"ref": "asset:test:initial", "sha256": AssetCatalog.from_repo(root).assets["asset:test:initial"]["sha256"]}
    report = SourceLocatorVerifier(AssetCatalog.from_repo(root)).verify(source)
    assert report["status"] == "FAIL" and "LOCATOR_CARRIER_MISMATCH" in report["findings"]


def test_stored_status_is_ignored_and_stale_reports_are_blocked(extraction_repo):
    root = extraction_repo
    built, source = setup_source(root)
    intake = AssetIntake(root)
    report = SourceLocatorVerifier(AssetCatalog.from_repo(root)).verify(source)
    report_file = root.parent / "verification.json"
    report_file.write_bytes(canonical_bytes(report))
    received = intake.ingest(report_file, origin="test:verification", kind="PROJECT_RESEARCH")
    source["locator_verification"] = {
        "status": "VERIFIED", "reason": "Bound report", "report_ref": received["asset_ref"],
        "report_sha256": received["sha256"], "source_record_sha256": report["source_record_sha256"],
    }
    assert SourceLocatorVerifier(AssetCatalog.from_repo(root)).verify(source)["status"] == "PASS"
    source["witness"]["label"] = "changed witness"
    failed = SourceLocatorVerifier(AssetCatalog.from_repo(root)).verify(source)
    assert failed["status"] == "FAIL" and "STALE_VERIFICATION_REPORT_BINDING" in failed["findings"]
    source["locator_verification"] = {"status": "VERIFIED", "reason": "self-reported"}
    assert SourceLocatorVerifier(AssetCatalog.from_repo(root)).verify(source)["status"] == "FAIL"


@pytest.mark.parametrize("format_name", ["TEXT", "HTML", "EPUB", "PDF"])
@pytest.mark.parametrize("change", ["python_patch", "code", "lock_format", "dependency"])
def test_toolchain_changes_require_content_comparison_not_manifest_replacement(extraction_repo, monkeypatch, format_name, change):
    root = extraction_repo
    built, _ = setup_source(root, format_name)
    catalog = AssetCatalog.from_repo(root)
    original = catalog.resolve(built["manifest_ref"]).path.read_bytes()
    import rcwh.corpus.extraction as extraction
    if change == "python_patch":
        other_patch = "3.12.13" if built["manifest"]["extractor"]["python"].endswith("3.12.3") else "3.12.3"
        monkeypatch.setattr(extraction.platform, "python_version", lambda: other_patch)
    elif change == "code":
        monkeypatch.setattr(extraction, "code_digest", lambda *args: "0" * 64)
    elif change == "lock_format":
        path = root / "requirements/extraction.lock.json"
        path.write_bytes(path.read_bytes() + b"\n")
    else:
        version = extraction.importlib.metadata.version
        monkeypatch.setattr(extraction.importlib.metadata, "version", lambda name: "different-installed-version" if name == "PyMuPDF" else version(name))
    repository = ExtractionRepository(catalog)
    manifest, units = repository.load(built["manifest_ref"])
    assert manifest == built["manifest"] and units
    observation = repository.rebuild_reports[built["manifest_ref"]]
    assert observation["status"] == "PASS"
    if change != "dependency" or format_name == "PDF":
        assert observation["toolchain_diff"]
    assert catalog.resolve(built["manifest_ref"]).path.read_bytes() == original


def test_changed_rebuild_bytes_fail_even_when_executor_identity_is_unchanged(extraction_repo, monkeypatch):
    root = extraction_repo
    built, _ = setup_source(root)
    import rcwh.corpus.extraction as extraction
    original = extraction.extract_units
    def changed(raw, config):
        units = original(raw, config)
        units[0]["text"] = units[0]["text"].replace("引文材料", "虚构材料")
        units[0]["text_sha256"] = digest(units[0]["text"].encode())
        return units
    repository = ExtractionRepository(AssetCatalog.from_repo(root))
    repository.load(built["manifest_ref"])
    monkeypatch.setattr(extraction, "extract_units", changed)
    with pytest.raises(AssetError, match="EXTRACTION_REBUILD_MISMATCH"):
        repository.load(built["manifest_ref"])
    assert built["manifest_ref"] not in repository.rebuild_reports


def test_locator_cache_rebuilds_after_executor_change_and_catches_changed_output(extraction_repo, monkeypatch):
    root = extraction_repo
    built, source = setup_source(root)
    verifier = SourceLocatorVerifier(AssetCatalog.from_repo(root))
    assert verifier.verify(source)["status"] == "PASS"
    import rcwh.corpus.extraction as extraction
    other_patch = "3.12.13" if built["manifest"]["extractor"]["python"].endswith("3.12.3") else "3.12.3"
    monkeypatch.setattr(extraction.platform, "python_version", lambda: other_patch)
    observation = verifier.verify(source)
    assert observation["status"] == "PASS" and observation["rebuild"]["toolchain_diff"]
    original = extraction.extract_units
    def changed(raw, config):
        units = original(raw, config)
        units[0]["text"] = units[0]["text"].replace("引文材料", "虚构材料")
        units[0]["text_sha256"] = digest(units[0]["text"].encode())
        return units
    monkeypatch.setattr(extraction, "extract_units", changed)
    monkeypatch.setattr(extraction, "code_digest", lambda *args: "0" * 64)
    report = verifier.verify(source)
    assert report["status"] == "FAIL" and "EXTRACTION_REBUILD_MISMATCH" in report["findings"]


def test_historical_locator_report_keeps_binding_after_verifier_code_change(extraction_repo, monkeypatch):
    root = extraction_repo
    _, source = setup_source(root)
    report = SourceLocatorVerifier(AssetCatalog.from_repo(root)).verify(source)
    report.pop("rebuild")  # Historical v1 reports did not contain an observation.
    file = root.parent / "historic-verification.json"
    file.write_bytes(canonical_bytes(report))
    received = AssetIntake(root).ingest(file, origin="test:historic-verification", kind="REVIEW_RECORD")
    source["locator_verification"] = {
        "status": "VERIFIED", "report_ref": received["asset_ref"], "report_sha256": received["sha256"],
        "source_record_sha256": report["source_record_sha256"], "reason": "Historical bound report",
    }
    monkeypatch.setattr("rcwh.corpus.locators.code_digest", lambda *args: "0" * 64)
    current = SourceLocatorVerifier(AssetCatalog.from_repo(root)).verify(source)
    assert current["status"] == "PASS" and current["raw_excerpt"] == source["text"]
    assert AssetCatalog.from_repo(root).resolve(received["asset_ref"]).path.read_bytes() == canonical_bytes(report)


def test_semantic_lock_change_is_rejected_despite_identical_old_output(extraction_repo):
    root = extraction_repo
    built, _ = setup_source(root)
    path = root / "requirements/extraction.lock.json"
    lock = json.loads(path.read_bytes()); lock["text"]["unicode_normalization"] = "NFC"
    path.write_bytes(canonical_bytes(lock))
    with pytest.raises(ExtractionConfigError, match="unsupported extraction dependency lock"):
        ExtractionRepository(AssetCatalog.from_repo(root)).load(built["manifest_ref"])


def test_extraction_transaction_can_be_recovered_after_output_write(extraction_repo, monkeypatch):
    root = extraction_repo
    asset_ref, _, _ = receive(root, "TEXT")
    from rcwh.assets import transactions
    original = transactions.apply_operation

    def interrupt(store, directory, operation):
        original(store, directory, operation)
        raise OSError("interrupted extraction")

    monkeypatch.setattr(transactions, "apply_operation", interrupt)
    with pytest.raises(OSError, match="interrupted extraction"):
        ExtractionRepository(AssetCatalog.from_repo(root)).build(asset_ref)
    with pytest.raises(AssetError, match="unfinished asset transaction"):
        AssetCatalog.from_repo(root)
    monkeypatch.setattr(transactions, "apply_operation", original)
    assert len(AssetIntake(root).recover()["recovered_transactions"]) == 1
    built = ExtractionRepository(AssetCatalog.from_repo(root)).build(asset_ref)
    assert ExtractionRepository(AssetCatalog.from_repo(root)).load(built["manifest_ref"])[0] == built["manifest"]


def test_missing_or_tampered_output_cannot_verify(extraction_repo):
    root = extraction_repo
    built, source = setup_source(root)
    catalog = AssetCatalog.from_repo(root)
    path = catalog.resolve(built["manifest"]["output"]["asset_ref"]).path
    original = path.read_bytes()
    verifier = SourceLocatorVerifier(catalog)
    assert verifier.verify(source)["status"] == "PASS"
    path.write_bytes(original + b"invented")
    assert verifier.verify(source)["status"] == "FAIL"
    assert SourceLocatorVerifier(AssetCatalog.from_repo(root)).verify(source)["status"] == "FAIL"
    path.unlink()
    with pytest.raises(AssetError, match="missing file"):
        ExtractionRepository(AssetCatalog.from_repo(root)).load(built["manifest_ref"])


def test_tracked_source_closure_includes_extraction_and_config(extraction_repo):
    root = extraction_repo
    setup_source(root)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    report = ProvenanceRepository.from_repo(root).verify_all(require_tracked=True)
    assert report["status"] == "FAIL"
    assert any("untracked source verification input" in finding for finding in report["storage_findings"])
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    assert ProvenanceRepository.from_repo(root).verify_all(require_tracked=True)["status"] == "PASS"


def test_source_check_and_unified_verify_agree_and_empty_roots_fail(extraction_repo):
    root = extraction_repo
    setup_source(root)
    repository = ProvenanceRepository.from_repo(root)
    assert repository.check(locators=True)["status"] == repository.verify_all()["status"] == "PASS"
    assert len(repository.verify_all()["root_set_digest"]) == 64
    repository.graph.sources.clear()
    assert repository.verify_all()["status"] == "FAIL"
    assert any("EMPTY_ROOT_SET" in finding for finding in repository.verify_all()["graph_findings"])


def test_cli_extract_locate_verify_and_report_export(extraction_repo, monkeypatch, capsys):
    root = extraction_repo
    asset_ref, sha, quote = receive(root, "TEXT")
    source = {
        "id": "src:test:cli", "type": "NOVEL_TEXT", "title": "test", "witness": {"label": "test"},
        "container": {"ref": asset_ref, "sha256": sha}, "text": quote, "text_sha256": digest(quote.encode()),
        "locator": {"lines": "unknown"}, "locator_verification": {"status": "UNVERIFIED", "reason": "pending"},
    }
    write_source(root, source)

    def run(*arguments):
        monkeypatch.setattr("sys.argv", ["rcwh", "--root", str(root), *arguments])
        with pytest.raises(SystemExit) as result:
            main()
        return result.value.code, json.loads(capsys.readouterr().out)

    code, built = run("corpus", "extract", asset_ref)
    assert code == 0
    code, shown = run("corpus", "show", built["manifest_ref"], "--unit", "text:1")
    assert code == 0 and quote in shown["unit"]["text"]
    assert shown["rebuild"]["status"] == "PASS"
    assert shown["rebuild"]["current_toolchain"]["extractor"]["python"].endswith(platform.python_version())
    code, proposal = run("sources", "locate", source["id"], "--extraction", built["manifest_ref"])
    assert code == 0 and proposal["status"] == "PASS"
    assert ProvenanceRepository.from_repo(root).graph.sources[source["id"]]["locator"] == {"lines": "unknown"}
    source["locator"] = proposal["locator"]
    write_source(root, source)
    code, verified = run("sources", "verify-all")
    assert code == 0 and verified["status"] == "PASS"
    code, profile = run("self-contained", "check", "--profile", "source-locators")
    assert code == 0 and profile["status"] == verified["status"]
    assert profile["root_set_digest"] == verified["root_set_digest"]
    report_file = root.parent / "exported-report.json"
    code, result = run("sources", "verify", source["id"], "--report-output", str(report_file))
    assert code == 0 and json.loads(report_file.read_bytes())["status"] == "PASS"
    assert run("sources", "verify", source["id"], "--report-output", str(report_file))[0] == 1
    assert run("corpus", "extract", asset_ref, "--format", "TEXT", "--pdf-pages", "1")[0] == 2
