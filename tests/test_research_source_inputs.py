"""Byte-bound research fixtures exercise the real loader and locator verifier.

Only CatalogStore.metadata_paths is narrowed to fixture metadata. Neither graph,
source_report, schema validation, asset resolution nor extraction is mocked.
"""
from copy import deepcopy
import json
from pathlib import Path
import shutil

import pytest

from rcwh.assets import AssetCatalog, CatalogStore
from rcwh.assets.transactions import digest
from rcwh.corpus.extraction import ExtractionRepository, canonical_bytes
from rcwh.graph import ProvenanceGraph
from rcwh.provenance.research_inputs import ResearchSourceInputs


ROOT = Path(__file__).resolve().parents[1]


class ResearchFixture:
    def __init__(self, root):
        self.root = root
        self.catalog = AssetCatalog(root, {}, {})
        self.source = {
            "id": "src:research:new", "type": "HISTORICAL_PRIMARY",
            "title": "Fixture witness", "tier": "EDITORIAL",
            "witness": {"label": "Fixture only"},
            "bibliography": {"citation": "Fixture historical source"},
            "locator": {"page": 1}, "text": "引文材料",
            "text_sha256": digest("引文材料".encode()),
            "locator_verification": {"status": "UNVERIFIED", "reason": "Research only"},
        }
        self.claim = {
            "id": "claim:research:new", "statement": "Fixture feasibility, not narrative fact",
            "kind": "RESEARCH", "authority_scope": "HISTORICAL_FEASIBILITY",
            "support": [{"source": self.source["id"], "relation": "DIRECT"}],
            "status": "SUPPORTED",
        }
        self.spec = {
            "schema_version": 1, "id": "research:fixture", "kind": "RESEARCH_SOURCE_SET",
            "chapters": [81], "qualification": "MODEL", "authority_effect": "NONE",
            "source_bindings": [], "claim_bindings": [], "reading_refs": [],
            "asset_bindings": [],
        }
        self.sources = [self.source]
        self.claims = [self.claim]

    def write(self, path, raw):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        return {"path": path, "sha256": digest(raw)}

    def document(self, path, document):
        return self.write(path, canonical_bytes(document))

    def publish_records(self):
        self.spec["source_bindings"] = [self.document(
            "research/sources.json", {"schema_version": 1, "sources": self.sources})]
        self.spec["claim_bindings"] = [self.document(
            "research/claims.json", {"schema_version": 1, "claims": self.claims})] if self.claims else []

    def publish_spec(self):
        return self.document("research/set.json", self.spec)

    def report(self, *, chapter=81, mode="RESEARCH"):
        self.publish_records()
        return self.load(self.publish_spec(), chapter=chapter, mode=mode)

    def load(self, binding, **kwargs):
        return ResearchSourceInputs(self.catalog).report(binding, chapter=kwargs.pop("chapter", 81), **kwargs)

    def asset(self, ref, path, raw, *, derived_from=None):
        binding = {"asset_ref": ref, **self.write(path, raw)}
        self.catalog.assets[ref] = {
            "id": ref, "path": path, "sha256": binding["sha256"], "bytes": len(raw),
            "media_type": "text/plain", "kind": "CORPUS_DERIVATIVE" if derived_from is not None else "PRIMARY_TEXT_CONTAINER",
            "immutable": True, "origin_refs": [],
            **({"derived_from": derived_from} if derived_from is not None else {}),
        }
        return binding

    def extraction(self, *, unregistered=()):
        """Compile a real TEXT extraction, then optionally withhold registration."""
        carrier = self.asset("asset:test:carrier", "research/carrier.txt", "序😀\n引文材料\n末行".encode())
        self.source["container"] = {"ref": carrier["asset_ref"], "sha256": carrier["sha256"]}
        manifest, units_raw = ExtractionRepository(self.catalog).compile(carrier["asset_ref"])
        units = self.asset(manifest["output"]["asset_ref"], "research/units.jsonl", units_raw,
                           derived_from=[carrier["asset_ref"]])
        raw = canonical_bytes(manifest)
        extraction = self.asset(f"asset:sha256:{digest(raw)}", "research/manifest.json", raw,
                                derived_from=[carrier["asset_ref"], units["asset_ref"]])
        unit = json.loads(units_raw.splitlines()[0])
        start = unit["text"].index(self.source["text"])
        self.source["locator"] = {
            "schema_version": 2, "kind": "TEXT_SPANS", "extraction_ref": extraction["asset_ref"],
            "output_sha256": units["sha256"],
            "spans": [{"unit_ref": unit["unit_ref"], "start": start, "end": start + len(self.source["text"])}],
            "joiner": "", "raw_text_sha256": self.source["text_sha256"],
        }
        bindings = {"carrier": carrier, "manifest": extraction, "units": units}
        for name in unregistered:
            binding = bindings[name]
            del self.catalog.assets[binding["asset_ref"]]
            self.spec["asset_bindings"].append(binding)
        return bindings

    def legacy_source(self, source):
        self.document("data/provenance/sources/legacy.yaml", {"schema_version": 1, "sources": [source]})


@pytest.fixture
def research(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    (root / "schemas").mkdir(parents=True)
    for name in (
        "research_source_set", "source", "claim", "decision", "implementation", "title_axis",
        "locator_v2", "extraction_manifest", "extraction_config", "extraction_unit", "source_locator_report",
        "source_capture", "source_excerpt_review",
    ):
        shutil.copyfile(ROOT / f"schemas/{name}.schema.json", root / f"schemas/{name}.schema.json")
    (root / "requirements").mkdir()
    shutil.copyfile(ROOT / "requirements/extraction.lock.json", root / "requirements/extraction.lock.json")
    fixture = ResearchFixture(root)
    fixture.document("data/catalog/fixture.json", {"assets": []})
    monkeypatch.setattr(CatalogStore, "metadata_paths", lambda self: {"data/catalog/fixture.json"})
    return fixture


def assert_failed(report, finding):
    assert report["status"] == report["integrity_status"] == "FAIL", report
    assert report["records"] == {"sources": [], "claims": []}
    assert any(finding in item for item in report["findings"]), report["findings"]


def assert_pending(report):
    assert report["status"] == report["evidence_readiness"] == "PENDING", report
    assert report["integrity_status"] == "PASS"
    assert report["qualification"] == "MODEL"
    assert report["authority_effect"] == "NONE"
    assert not report["findings"]
    assert all(row["status"] == "PENDING" for row in report["source_reports"])


def test_minimal_real_loader_does_not_overlay_legacy_graph(research):
    old = deepcopy(research.source)
    old["id"] = "src:legacy:unchanged"
    research.legacy_source(old)
    before = {p.relative_to(research.root): p.read_bytes() for p in research.root.rglob("*") if p.is_file()}
    report = research.report()
    assert_pending(report)
    assert report["records"]["sources"] == [research.source]
    assert report["records"]["claims"] == [research.claim]
    assert ProvenanceGraph.from_repo(research.root).sources == {old["id"]: old}
    assert all((research.root / path).read_bytes() == raw for path, raw in before.items())
    assert "schemas/research_source_set.schema.json" in report["paths"]
    assert "data/catalog/fixture.json" in report["paths"]


@pytest.mark.parametrize("path", ["../outside.json", "/tmp/outside.json", "research/../set.json", "research\\set.json"])
@pytest.mark.parametrize("target", ["set", "source"])
def test_path_traversal_rejected(research, path, target):
    research.publish_records()
    if target == "source":
        research.spec["source_bindings"][0]["path"] = path
        binding = research.publish_spec()
    else:
        binding = {"path": path, "sha256": "0" * 64}
    assert_failed(research.load(binding), "unsafe repository path")


@pytest.mark.parametrize("directory_link", [False, True])
def test_symlink_rejected_even_when_target_is_inside_repository(research, directory_link):
    research.publish_records()
    if directory_link:
        (research.root / "linked").symlink_to(research.root / "research", target_is_directory=True)
        path = "linked/sources.json"
    else:
        (research.root / "research/link.json").symlink_to(research.root / "research/sources.json")
        path = "research/link.json"
    research.spec["source_bindings"][0]["path"] = path
    assert_failed(research.load(research.publish_spec()), "symlink is not an asset")


@pytest.mark.parametrize("target", ["set", "source", "claim", "reading", "asset"])
def test_stale_byte_binding_rejected(research, target):
    research.publish_records()
    if target == "set":
        binding = research.publish_spec()
        (research.root / binding["path"]).write_bytes(b"{}")
    else:
        if target in {"source", "claim"}:
            record_binding = research.spec[f"{target}_bindings"][0]
        elif target == "reading":
            record_binding = research.document("research/reading.json", {"status": "PASS"})
            research.spec["reading_refs"] = [record_binding]
        else:
            record_binding = {"asset_ref": "asset:test:bound", **research.write("research/bound.txt", b"original")}
            research.spec["asset_bindings"] = [record_binding]
        (research.root / record_binding["path"]).write_bytes(b"changed bytes")
        binding = research.publish_spec()
    assert_failed(research.load(binding), "STALE_RESEARCH_INPUT")


@pytest.mark.parametrize("target", ["source", "claim"])
def test_old_id_collision_rejected(research, target):
    if target == "source":
        research.legacy_source(deepcopy(research.source))
    else:
        research.document("data/provenance/claims/legacy.yaml", {"schema_version": 1, "claims": [deepcopy(research.claim)]})
    assert_failed(research.report(), "RESEARCH_RECORD_OLD_ID_COLLISION")


@pytest.mark.parametrize("target", ["sources", "claims", "cross_type"])
def test_duplicate_supplementary_id_rejected(research, target):
    if target == "cross_type":
        research.claim["id"] = research.source["id"]
    else:
        getattr(research, target).append(deepcopy(getattr(research, target)[0]))
    assert_failed(research.report(), "DUPLICATE_RESEARCH_RECORD_ID")


@pytest.mark.parametrize("support, finding", [
    ([], "RESEARCH_CLAIM_MISSING_SUPPORT"),
    ([{"source": "src:missing:dependency", "relation": "DIRECT"}], "RESEARCH_CLAIM_UNKNOWN_SUPPORT"),
])
def test_claim_missing_dependency_rejected(research, support, finding):
    research.claim["support"] = support
    assert_failed(research.report(), finding)


def test_claim_reachable_legacy_source_is_byte_checked(research):
    old = deepcopy(research.source)
    old["id"] = "src:legacy:dependency"
    old["text_sha256"] = "0" * 64
    research.legacy_source(old)
    research.claim["support"] = [{"source": old["id"], "relation": "CONTEXTUAL"}]
    assert_failed(research.report(), "SOURCE_TEXT_SHA_MISMATCH: src:legacy:dependency")


def test_source_text_hash_tampering_rejected_with_fresh_document_binding(research):
    research.source["text"] = "改写但未更新文本哈希"
    assert_failed(research.report(), "SOURCE_TEXT_SHA_MISMATCH")


@pytest.mark.parametrize("chapter, finding", [(82, "CHAPTER_OUT_OF_SCOPE"), (True, "INVALID_RESEARCH_CHAPTER"), ("81", "INVALID_RESEARCH_CHAPTER")])
def test_chapter_scope(research, chapter, finding):
    assert_failed(research.report(chapter=chapter), finding)


@pytest.mark.parametrize("mode", ["WRITING", "MODEL", "RESEARCH ", "research"])
def test_nonresearch_mode_rejected(research, mode):
    assert_failed(research.report(mode=mode), "REQUIRES_RESEARCH_MODE")


@pytest.mark.parametrize("target", ["source", "claim", "nested"])
def test_explicit_mappings_forbidden_recursively(research, target):
    record = research.claim if target == "claim" else research.source
    if target == "nested":
        record["extra"] = [{"Explicit_Mappings": {"old": "new"}}]
    else:
        record["explicit_mappings"] = {"old": "new"}
    assert_failed(research.report(), "RESEARCH_SUPERSESSION_FORBIDDEN")


def test_explicit_mappings_forbidden_in_source_set_schema(research):
    research.spec["explicit_mappings"] = {"old": "new"}
    assert_failed(research.report(), "INVALID_RESEARCH_SOURCE_SET")


@pytest.mark.parametrize("target", ["source", "claim"])
def test_authority_upgrade_rejected(research, target):
    getattr(research, target)["authority_effect"] = "ADOPTED"
    assert_failed(research.report(), "RESEARCH_RECORD_AUTHORITY_UPGRADE")


@pytest.mark.parametrize("tier", ["W1_DIRECT", "W1_SEEN"])
def test_derivative_cannot_impersonate_original_witness(research, tier):
    research.source["container_role"] = "MODEL_TRANSCRIPTION_DERIVATIVE_NOT_OFFICIAL_TEXT_LAYER"
    research.source["tier"] = tier
    assert_failed(research.report(), "RESEARCH_DERIVATIVE_IDENTITY_UPGRADE")


@pytest.mark.parametrize("original", ["image", "pdf"])
def test_derivative_text_carrier_cannot_equal_original_facsimile(research, original):
    text = research.asset("asset:test:transcription", "research/transcription.txt", b"transcribed text")
    other = research.asset("asset:test:other", "research/other.bin", b"distinct facsimile bytes")
    research.source["container"] = {"ref": text["asset_ref"], "sha256": text["sha256"]}
    research.source["container_role"] = "MODEL_TRANSCRIPTION_DERIVATIVE_NOT_OFFICIAL_TEXT_LAYER"
    facsimile = {
        "binding_status": "MODEL_READING_PENDING", "physical_page": 1, "printed_page": "1",
        "image_xref": 1, "independent_historical_witness_count": 1,
    }
    for kind in ("image", "pdf"):
        binding = text if kind == original else other
        facsimile[f"{kind}_asset_ref"] = binding["asset_ref"]
        facsimile[f"{kind}_sha256"] = binding["sha256"]
    research.source["facsimile_binding"] = facsimile
    assert_failed(research.report(), "RESEARCH_DERIVATIVE_IS_NOT_ORIGINAL_FACSIMILE")


@pytest.mark.parametrize("reading_refs", [False, True])
def test_declared_pass_and_reading_ref_bytes_never_upgrade_evidence(research, reading_refs):
    research.extraction()
    research.spec["status"] = "PASS"
    if reading_refs:
        # Deliberately not a reading schema: loader promises byte identity only.
        research.spec["reading_refs"] = [research.document("research/reading.json", {"status": "PASS", "qualification": "W1_DIRECT"})]
    report = research.report()
    assert_pending(report)
    computed = report["source_reports"][0]["computed_source_report"]
    assert computed["status"] == computed["verification_report"]["status"] == "PASS"
    assert computed["verification_report"]["raw_excerpt"] == research.source["text"]
    assert report["reading_refs"] == research.spec["reading_refs"]
    assert any("READING_REFS_BYTE_IDENTITY_ONLY" in note for note in report["limitations"])
    assert any("NO_READING_REFERENCES" in note for note in report["limitations"]) is not reading_refs


@pytest.mark.parametrize("bound", [False, True])
def test_unregistered_carrier_remains_pending_with_integrity_pass(research, bound):
    binding = {"asset_ref": "asset:test:unregistered", **research.write("research/unregistered.txt", b"local bytes")}
    research.source["container"] = {"ref": binding["asset_ref"], "sha256": binding["sha256"]}
    if bound:
        research.spec["asset_bindings"] = [binding]
    report = research.report()
    assert_pending(report)
    assert report["unregistered_asset_refs"] == [binding["asset_ref"]]
    assert (binding["path"] in report["paths"]) is bound
    assert any("ASSET_REGISTRATION_PENDING" in note for note in report["limitations"])


@pytest.mark.parametrize("target", ["carrier", "manifest", "units"])
def test_registered_stale_asset_is_hard_failure(research, target):
    binding = research.extraction()[target]
    (research.root / binding["path"]).write_bytes(b"changed bytes")
    assert_failed(research.report(), "byte mismatch")


def test_valid_unregistered_explicit_bound_extraction_is_pending(research):
    bindings = research.extraction(unregistered=("manifest", "units"))
    report = research.report()
    assert_pending(report)
    assert set(report["unregistered_asset_refs"]) == {
        bindings[name]["asset_ref"] for name in ("manifest", "units")
    }
    assert all(binding["path"] in report["paths"] for binding in bindings.values())
    assert "schemas/extraction_unit.schema.json" in report["paths"]


@pytest.mark.parametrize("unregistered", [False, True])
def test_empty_span_rejected_before_registration_checks(research, unregistered):
    research.extraction(unregistered=("manifest", "units") if unregistered else ())
    research.source["locator"]["spans"][0].update(start=2, end=2)
    assert_failed(research.report(), "INVALID_RESEARCH_LOCATOR_SPAN")


@pytest.mark.parametrize("mutation, finding", [
    ("wrong_slice", "EXCERPT_MISMATCH"),
    ("out_of_range", "LOCATOR_SPAN_OUT_OF_RANGE"),
    ("unknown_unit", "UNKNOWN_TEXT_UNIT"),
    ("raw_hash", "LOCATOR_EXCERPT_HASH_MISMATCH"),
    ("reordered", "OVERLAPPING_OR_REORDERED_SPANS"),
])
@pytest.mark.parametrize("unregistered", [False, True])
def test_bound_extraction_span_validation(research, mutation, finding, unregistered):
    research.extraction(unregistered=("manifest", "units") if unregistered else ())
    locator = research.source["locator"]
    span = locator["spans"][0]
    if mutation == "wrong_slice":
        span.update(start=0, end=1)
        locator["raw_text_sha256"] = digest("序".encode())
    elif mutation == "out_of_range":
        span["end"] = 99999
    elif mutation == "unknown_unit":
        span["unit_ref"] = "unit:does-not-exist"
    elif mutation == "raw_hash":
        locator["raw_text_sha256"] = "0" * 64
    else:
        locator["spans"] = [deepcopy(span), deepcopy(span)]
    assert_failed(research.report(), finding)
