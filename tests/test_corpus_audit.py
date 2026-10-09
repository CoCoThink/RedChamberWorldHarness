import json
import shutil

import pytest

from rcwh.assets import AssetCatalog, AssetError
from rcwh.assets.ingest import AssetIntake
from rcwh.assets.transactions import digest
from rcwh.corpus.audit import CorpusAudit
from rcwh.corpus.dataset import CorpusRepository
from rcwh.corpus.extraction import canonical_bytes
from test_corpus_dataset import ROOT, DATASET, BUILD, corpus_repo, rows
from test_source_extraction import extraction_repo


@pytest.fixture
def audit_repo(corpus_repo):
    root, _, _ = corpus_repo
    for name in ("corpus_audit_protocol", "corpus_audit_selection", "corpus_audit_review"):
        shutil.copyfile(ROOT/f"schemas/{name}.schema.json", root/f"schemas/{name}.schema.json")
    built = CorpusRepository(AssetCatalog.from_repo(root)).build(BUILD, "corpus/front80/test-v1")
    corpus = CorpusRepository(AssetCatalog.from_repo(root)); _, products = corpus.load(DATASET)
    segments = [s for s in rows(products["segments.jsonl"]) if s["text"].strip()]
    protocol = {"schema_version": 1, "id": "corpus-audit:test", "dataset_ref": DATASET,
                "manifest_sha256": built["manifest_sha256"], "minimum_reviewers": 1,
                "samples": [{"segment_id": s["segment_id"], "text_sha256": s["text_sha256"], "reason": "Each declared layer"} for s in segments], "authority_effect": "NONE"}
    protocol_path = "data/corpus/audit-protocols/test.json"; (root/protocol_path).parent.mkdir(parents=True); (root/protocol_path).write_bytes(canonical_bytes(protocol))
    selected = {"schema_version": 1, "dataset_ref": DATASET, "protocol": {"path": protocol_path, "sha256": digest((root/protocol_path).read_bytes())}, "reviews": [], "authority_effect": "NONE"}
    selected_path = f"data/corpus/audits/{digest(DATASET.encode())}.json"; (root/selected_path).parent.mkdir(parents=True); (root/selected_path).write_bytes(canonical_bytes(selected))
    return root, protocol, selected, selected_path


def approve_fixture(root, protocol, selected, selected_path, *, rejected_check=None, reviewer_id="fixture:reader"):
    # Synthetic attestations exercise validation only, never become repo reviews.
    raw = {"dataset_ref": DATASET, "manifest_sha256": protocol["manifest_sha256"], "protocol_sha256": selected["protocol"]["sha256"],
           "reviewer": {"id": reviewer_id, "kind": "INDEPENDENT_HUMAN", "independent_of_builder": True},
           "main_boundaries_confirmed": True, "unknown_witnesses_acknowledged": True, "unaligned_segments_acknowledged": True,
           "checks": [{"segment_id": s["segment_id"], "layer_valid": True, "locator_valid": True, "context_valid": True, "notes": "fixture checked"} for s in protocol["samples"]]}
    if rejected_check in {"main_boundaries_confirmed", "unknown_witnesses_acknowledged", "unaligned_segments_acknowledged"}:
        raw[rejected_check] = False
    elif rejected_check:
        raw["checks"][0][rejected_check] = False
    file = root.parent/"audit-raw.json"; file.write_bytes(canonical_bytes(raw)); item = AssetIntake(root).ingest(file, origin="test:synthetic-audit", kind="REVIEW_RECORD")
    review = {"schema_version": 1, "id": f"corpus-review:{reviewer_id}", **raw, "raw_review": {"asset_ref": item["asset_ref"], "sha256": item["sha256"]}, "authority_effect": "NONE"}
    path = f"data/corpus/audits/review-{digest(reviewer_id.encode())}.json"; (root/path).write_bytes(canonical_bytes(review)); selected["reviews"].append({"path": path, "sha256": digest((root/path).read_bytes())}); (root/selected_path).write_bytes(canonical_bytes(selected))
    return path, review


def test_no_human_review_means_pending_and_fixture_approval_is_separate(audit_repo):
    root, protocol, selected, path = audit_repo
    assert CorpusAudit(AssetCatalog.from_repo(root)).summary(DATASET)["status"] == "PENDING"
    approve_fixture(root, protocol, selected, path)
    result = CorpusAudit(AssetCatalog.from_repo(root)).summary(DATASET)
    assert result["status"] == "PASS" and result["sample_count"] == len(protocol["samples"])
    assert CorpusRepository(AssetCatalog.from_repo(root)).verify(DATASET)["readiness"] == "CANDIDATE_PENDING_HUMAN_AUDIT"


@pytest.mark.parametrize("check", ["main_boundaries_confirmed", "unknown_witnesses_acknowledged", "unaligned_segments_acknowledged", "layer_valid", "locator_valid", "context_valid"])
def test_real_negative_corpus_review_is_bound_and_prevents_acceptance(audit_repo, check):
    root, protocol, selected, path = audit_repo
    _, review = approve_fixture(root, protocol, selected, path, rejected_check=check)
    result = CorpusAudit(AssetCatalog.from_repo(root)).summary(DATASET)
    assert result["status"] == "FAIL" and result["review_count"] == 1
    assert result["findings"][0]["rejected_checks"] == [check]
    from rcwh.assets.receipts import ReceiptLedger
    assert review["id"] in ReceiptLedger(AssetCatalog.from_repo(root)).binding_refs(review["raw_review"])


def test_minimum_approvals_cannot_erase_a_selected_corpus_rejection(audit_repo):
    root, protocol, selected, path = audit_repo
    approve_fixture(root, protocol, selected, path)
    approve_fixture(root, protocol, selected, path, rejected_check="layer_valid", reviewer_id="fixture:other-reader")
    result = CorpusAudit(AssetCatalog.from_repo(root)).summary(DATASET)
    assert result["status"] == "FAIL" and result["review_count"] == 2
    assert result["findings"][0]["rejected_checks"] == ["layer_valid"]


@pytest.mark.parametrize("target", ["stale-manifest", "missing-chapter", "missing-layer", "incomplete-review", "raw-disagreement"])
def test_corpus_audit_rejects_stale_or_incomplete_review(audit_repo, target):
    root, protocol, selected, selected_path = audit_repo
    if target in {"stale-manifest", "missing-chapter", "missing-layer"}:
        if target == "stale-manifest": protocol["manifest_sha256"] = "0"*64
        else:
            _, products = CorpusRepository(AssetCatalog.from_repo(root)).load(DATASET)
            index = {s["segment_id"]: s for s in rows(products["segments.jsonl"])}
            protocol["samples"] = [s for s in protocol["samples"] if not (index[s["segment_id"]]["kind"]=="MAIN_TEXT" and index[s["segment_id"]]["chapter"]==2)] if target=="missing-chapter" else [s for s in protocol["samples"] if index[s["segment_id"]]["kind"]!="ZHIPI"]
        (root/selected["protocol"]["path"]).write_bytes(canonical_bytes(protocol)); selected["protocol"]["sha256"] = digest((root/selected["protocol"]["path"]).read_bytes()); (root/selected_path).write_bytes(canonical_bytes(selected))
    else:
        path, review = approve_fixture(root, protocol, selected, selected_path)
        if target == "incomplete-review": review["checks"] = review["checks"][:1]
        else: review["checks"][0]["notes"] = "invented changed note"
        (root/path).write_bytes(canonical_bytes(review)); selected["reviews"][0]["sha256"] = digest((root/path).read_bytes()); (root/selected_path).write_bytes(canonical_bytes(selected))
    with pytest.raises(AssetError): CorpusAudit(AssetCatalog.from_repo(root)).summary(DATASET)
