import json
import shutil

import pytest

from rcwh.assets import AssetCatalog, AssetError
from rcwh.assets.ingest import AssetIntake
from rcwh.assets.transactions import digest
from rcwh.corpus.extraction import canonical_bytes
from rcwh.corpus.locators import source_digest
from rcwh.provenance import ProvenanceRepository
from rcwh.provenance.audit import SourceAudit
from test_source_extraction import ROOT, extraction_repo, setup_source, write_source


@pytest.fixture
def audit_source_repo(extraction_repo):
    root = extraction_repo
    for name in ("source_audit_protocol", "source_audit_selection", "source_audit_review"):
        shutil.copyfile(ROOT/f"schemas/{name}.schema.json", root/f"schemas/{name}.schema.json")
    _, source = setup_source(root)
    audit = SourceAudit(ProvenanceRepository.from_repo(root))
    protocol = {"schema_version": 1, "id": "source-audit:test", "graph_sha256": audit.graph_digest(),
                "sources": [{"source_ref": source["id"], "source_record_sha256": source_digest(source)}], "authority_effect": "NONE"}
    path = "data/provenance/audits/protocol.json"; (root/path).parent.mkdir(parents=True); (root/path).write_bytes(canonical_bytes(protocol))
    selected = {"schema_version": 1, "protocol": {"path": path, "sha256": digest((root/path).read_bytes())}, "reviews": [], "authority_effect": "NONE"}
    (root/SourceAudit.selection_path).write_bytes(canonical_bytes(selected))
    return root, source, protocol, selected


def submit_fixture(root, selected, source, *, rejected_check=None, reviewer_id="fixture:reader"):
    raw = {"protocol_sha256": selected["protocol"]["sha256"], "reviewer": {"id": reviewer_id, "kind": "INDEPENDENT_HUMAN", "independent_of_corrections": True},
           "results": [{"source_ref": source["id"], "carrier_edition_confirmed": True, "excerpt_valid": True, "witness_tier_unchanged": True, "claim_impact_reviewed": True, "notes": "Synthetic fixture only"}]}
    if rejected_check:
        raw["results"][0][rejected_check] = False
    path = root.parent/"raw-evidence.json"; path.write_bytes(canonical_bytes(raw)); receipt = AssetIntake(root).ingest(path, origin="test:synthetic-evidence-review", kind="REVIEW_RECORD")
    record = {"schema_version": 1, "id": f"source-review:{reviewer_id}", **raw, "raw_review": {"asset_ref": receipt["asset_ref"], "sha256": receipt["sha256"]}, "authority_effect": "NONE"}
    relative = f"data/provenance/audits/{digest(reviewer_id.encode())}.json"; (root/relative).write_bytes(canonical_bytes(record))
    selected["reviews"].append({"path": relative, "sha256": digest((root/relative).read_bytes())}); (root/SourceAudit.selection_path).write_bytes(canonical_bytes(selected))
    return relative, record


def test_independent_source_audit_needs_raw_submission(audit_source_repo):
    root, source, _, selected = audit_source_repo
    assert SourceAudit(ProvenanceRepository.from_repo(root)).summary()["status"] == "PENDING"
    submit_fixture(root, selected, source)
    assert SourceAudit(ProvenanceRepository.from_repo(root)).summary()["status"] == "PASS"


def test_source_audit_cli_reports_pending_without_fabricating_review(audit_source_repo, monkeypatch, capsys):
    root, _, _, _ = audit_source_repo
    from rcwh.cli import main
    monkeypatch.setattr("sys.argv", ["rcwh", "--root", str(root), "sources", "audit"])
    with pytest.raises(SystemExit) as result: main()
    report = json.loads(capsys.readouterr().out)
    assert result.value.code == 0 and report["status"] == "PENDING" and report["review_count"] == 0


@pytest.mark.parametrize("check", ["carrier_edition_confirmed", "excerpt_valid", "witness_tier_unchanged", "claim_impact_reviewed"])
def test_real_negative_source_submission_is_retained_and_blocks_acceptance(audit_source_repo, check):
    root, source, _, selected = audit_source_repo
    _, review = submit_fixture(root, selected, source, rejected_check=check)
    result = SourceAudit(ProvenanceRepository.from_repo(root)).summary()
    assert result["status"] == "FAIL" and result["review_count"] == 1
    assert result["pending_source_ids"] == [source["id"]]
    assert result["findings"][0]["rejected_checks"] == [check]
    from rcwh.assets.receipts import ReceiptLedger
    assert review["id"] in ReceiptLedger(AssetCatalog.from_repo(root)).binding_refs(review["raw_review"])


def test_positive_coverage_cannot_erase_a_selected_source_rejection(audit_source_repo):
    root, source, _, selected = audit_source_repo
    submit_fixture(root, selected, source)
    submit_fixture(root, selected, source, rejected_check="excerpt_valid", reviewer_id="fixture:other-reader")
    result = SourceAudit(ProvenanceRepository.from_repo(root)).summary()
    assert result["status"] == "FAIL" and result["review_count"] == 2
    assert result["findings"][0]["source_ref"] == source["id"]


@pytest.mark.parametrize("target", ["source", "graph", "raw-review", "scope"])
def test_source_audit_inputs_and_interpretations_cannot_drift(audit_source_repo, target):
    root, source, protocol, selected = audit_source_repo
    relative, record = submit_fixture(root, selected, source)
    if target == "source": source["title"] = "changed witness context"; write_source(root, source)
    elif target == "raw-review":
        record["results"][0]["notes"] = "invented"; (root/relative).write_bytes(canonical_bytes(record)); selected["reviews"][0]["sha256"] = digest((root/relative).read_bytes()); (root/SourceAudit.selection_path).write_bytes(canonical_bytes(selected))
    else:
        if target == "graph": protocol["graph_sha256"] = "0"*64
        else:
            source["locator"] = {"legacy": "pending"}; write_source(root, source)
            protocol["sources"] = [{"source_ref": "src:other", "source_record_sha256": "0"*64}]
        (root/selected["protocol"]["path"]).write_bytes(canonical_bytes(protocol)); selected["protocol"]["sha256"] = digest((root/selected["protocol"]["path"]).read_bytes()); (root/SourceAudit.selection_path).write_bytes(canonical_bytes(selected))
    with pytest.raises(AssetError): SourceAudit(ProvenanceRepository.from_repo(root)).summary()
