from copy import deepcopy
import json

import pytest
import yaml

from rcwh.assets import AssetCatalog, AssetError
from rcwh.assets.ingest import AssetIntake
from rcwh.assets.transactions import digest
from rcwh.corpus.extraction import ExtractionRepository, canonical_bytes
from rcwh.corpus.locators import source_digest
from rcwh.graph import ProvenanceGraph
from rcwh.provenance import ProvenanceRepository
from rcwh.provenance.migration import SourceClosureMigration, evidence_snapshot
from test_source_extraction import extraction_repo, setup_source, write_source


def migration_plan(root):
    built, source = setup_source(root)
    source["locator"] = {"chapter": 1, "parsed_lines": "obsolete"}
    write_source(root, source)
    return [{"source_id": source["id"], "before_sha256": source_digest(source),
             "container_ref": source["container"]["ref"], "extraction_ref": built["manifest_ref"]}]


def test_migration_preserves_all_evidence_and_registers_bound_reports(extraction_repo):
    root = extraction_repo
    plan = migration_plan(root)
    before = ProvenanceGraph.from_repo(root)
    service = SourceClosureMigration(root)
    proposal = service.propose(plan)
    assert ProvenanceGraph.from_repo(root).sources == before.sources
    audit = service.apply(proposal, audit_path="artifacts/migration/audit.json")
    after = ProvenanceGraph.from_repo(root)
    assert evidence_snapshot(after) == evidence_snapshot(before)
    source = next(iter(after.sources.values()))
    assert source["legacy_locator"] == {"chapter": 1, "parsed_lines": "obsolete"}
    report = AssetCatalog.from_repo(root).resolve(source["locator_verification"]["report_ref"])
    assert json.loads(report.path.read_bytes()) == audit["results"][0]["verification_report"]
    assert ProvenanceRepository.from_repo(root).verify_all()["status"] == "PASS"


def test_unchanged_migration_reuses_verified_report_without_new_receipts(extraction_repo):
    root = extraction_repo
    service = SourceClosureMigration(root)
    plan = migration_plan(root)
    service.apply(service.propose(plan), audit_path="artifacts/migration/first.json")
    before = ProvenanceGraph.from_repo(root).sources
    catalog_before = deepcopy(AssetCatalog.from_repo(root).assets)
    from rcwh.assets import CatalogStore
    receipts_before = CatalogStore(root).receipts_unlocked()
    source = next(iter(before.values()))
    plan[0]["before_sha256"] = source_digest(source)
    service.apply(service.propose(plan), audit_path="artifacts/migration/second.json")
    assert ProvenanceGraph.from_repo(root).sources == before
    assert AssetCatalog.from_repo(root).assets == catalog_before
    assert CatalogStore(root).receipts_unlocked() == receipts_before


def test_migration_does_not_rewrite_an_unmatched_excerpt(extraction_repo):
    root = extraction_repo
    plan = migration_plan(root)
    graph = ProvenanceGraph.from_repo(root)
    source = graph.sources[plan[0]["source_id"]]
    source.update(text="A paraphrase", text_sha256=digest(b"A paraphrase"))
    write_source(root, source)
    plan[0]["before_sha256"] = source_digest(source)
    service = SourceClosureMigration(root)
    proposal = service.propose(plan)
    assert proposal["verification_status"] == "PARTIAL"
    service.apply(proposal, audit_path="artifacts/migration/audit.json")
    current = ProvenanceGraph.from_repo(root).sources[source["id"]]
    assert current["text"] == "A paraphrase" and current["locator"] == source["locator"]
    assert current["locator_verification"]["status"] == "UNVERIFIED"
    assert ProvenanceRepository.from_repo(root).verify_all()["status"] == "FAIL"


def test_migration_rejects_forged_semantic_changes_and_stale_inputs(extraction_repo):
    root = extraction_repo
    plan = migration_plan(root)
    service = SourceClosureMigration(root)
    proposal = service.propose(plan)
    forged = deepcopy(proposal)
    forged["after_sources"][plan[0]["source_id"]]["witness"]["label"] = "Forged witness"
    with pytest.raises(AssetError, match="STALE_MIGRATION_PROPOSAL"):
        service.apply(forged, audit_path="artifacts/migration/audit.json")
    source = ProvenanceGraph.from_repo(root).sources[plan[0]["source_id"]]
    source["notes"] = "Changed evidence context"
    write_source(root, source)
    with pytest.raises(AssetError, match="STALE_MIGRATION_INPUT"):
        service.propose(plan)


def test_migration_cannot_shrink_the_current_root_set(extraction_repo):
    root = extraction_repo
    plan = migration_plan(root)
    other = deepcopy(ProvenanceGraph.from_repo(root).sources[plan[0]["source_id"]])
    other["id"] = "src:test:other"
    other["witness"]["label"] = "Another witness"
    (root / "data/provenance/sources/other.yaml").write_text(
        yaml.safe_dump({"schema_version": 1, "sources": [other]}), encoding="utf-8",
    )
    with pytest.raises(AssetError, match="MIGRATION_ROOT_SET_MISMATCH"):
        SourceClosureMigration(root).propose(plan)


def test_invalid_audit_destination_has_no_intake_side_effects(extraction_repo):
    root = extraction_repo
    service = SourceClosureMigration(root)
    proposal = service.propose(migration_plan(root))
    before = deepcopy(AssetCatalog.from_repo(root).assets)
    with pytest.raises(AssetError, match="audit must use a new path"):
        service.apply(proposal, audit_path="data/provenance/sources/audit.yaml")
    assert AssetCatalog.from_repo(root).assets == before


def test_capture_metadata_cannot_bind_a_different_carrier(extraction_repo):
    root = extraction_repo
    plan = migration_plan(root)
    capture = {
        "schema_version": 1, "kind": "HTTP_CAPTURE", "requested_url": "https://example.org/source",
        "final_url": "https://example.org/source", "retrieved_at": "2026-10-09T00:00:00Z",
        "response": {"status": 200, "headers": {"Content-Type": "text/plain"}},
        "carrier": {"ref": "asset:test:initial", "sha256": AssetCatalog.from_repo(root).assets["asset:test:initial"]["sha256"]},
        "selection_note": "test fixed snapshot",
    }
    path = root.parent / "capture.json"
    path.write_bytes(canonical_bytes(capture))
    receipt = AssetIntake(root).ingest(path, origin="test:capture", kind="IMPORT_RECORD")
    plan[0]["capture_ref"] = receipt["asset_ref"]
    with pytest.raises(AssetError, match="CAPTURE_CARRIER_MISMATCH"):
        SourceClosureMigration(root).propose(plan)


def test_local_transcription_rebinding_must_explicitly_remove_old_http_capture(extraction_repo):
    root = extraction_repo
    plan = migration_plan(root)
    source = ProvenanceGraph.from_repo(root).sources[plan[0]["source_id"]]
    capture = {
        "schema_version": 1, "kind": "HTTP_CAPTURE", "requested_url": "https://example.org/source",
        "final_url": "https://example.org/source", "retrieved_at": "2026-10-09T00:00:00Z",
        "response": {"status": 200, "headers": {"Content-Type": "text/plain"}},
        "carrier": deepcopy(source["container"]), "selection_note": "original downloaded carrier",
    }
    capture_path = root.parent / "original-capture.json"
    capture_path.write_bytes(canonical_bytes(capture))
    received = AssetIntake(root).ingest(capture_path, origin="test:capture", kind="IMPORT_RECORD")
    source["carrier_capture"] = {"ref": received["asset_ref"], "sha256": received["sha256"]}
    write_source(root, source)
    transcript_path = root.parent / "transcription.txt"
    transcript_path.write_text("Transcribed locally: " + source["text"], encoding="utf-8")
    transcript = AssetIntake(root).ingest(transcript_path, origin="test:transcription", kind="CORPUS_DERIVATIVE")
    built = ExtractionRepository(AssetCatalog.from_repo(root)).build(transcript["asset_ref"])
    plan[0].update(before_sha256=source_digest(source), container_ref=transcript["asset_ref"], extraction_ref=built["manifest_ref"])
    service = SourceClosureMigration(root)
    with pytest.raises(AssetError, match="CAPTURE_CARRIER_MISMATCH"):
        service.propose(plan)
    plan[0]["capture_ref"] = None
    audit = service.apply(service.propose(plan), audit_path="artifacts/migration/local-transcription.json")
    current = ProvenanceGraph.from_repo(root).sources[source["id"]]
    assert "carrier_capture" not in current
    assert audit["before_sources"][source["id"]]["carrier_capture"] == source["carrier_capture"]
    assert AssetCatalog.from_repo(root).resolve(received["asset_ref"]).path.read_bytes() == canonical_bytes(capture)
    assert evidence_snapshot(ProvenanceGraph.from_repo(root)) == audit["evidence_snapshot"]
    assert ProvenanceRepository.from_repo(root).verify_all()["status"] == "PASS"


def test_migration_transaction_recovers_sources_and_audit_together(extraction_repo, monkeypatch):
    root = extraction_repo
    plan = migration_plan(root)
    from rcwh.assets import transactions
    original = transactions.apply_operation

    def interrupted(store, directory, operation):
        original(store, directory, operation)
        if operation["path"].startswith("data/provenance/sources/"):
            raise OSError("interrupted Source write")

    monkeypatch.setattr(transactions, "apply_operation", interrupted)
    service = SourceClosureMigration(root)
    with pytest.raises(OSError, match="interrupted Source write"):
        service.apply(service.propose(plan), audit_path="artifacts/migration/audit.json")
    with pytest.raises(AssetError, match="unfinished asset transaction"):
        AssetCatalog.from_repo(root)
    monkeypatch.setattr(transactions, "apply_operation", original)
    assert AssetIntake(root).recover()["recovered_transactions"]
    assert json.loads((root / "artifacts/migration/audit.json").read_bytes())["status"] == "APPLIED"
    assert ProvenanceRepository.from_repo(root).verify_all()["status"] == "PASS"
