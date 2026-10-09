from copy import deepcopy
import json
import shutil

import pytest
import yaml

from rcwh.assets import AssetCatalog, AssetError
from rcwh.assets.ingest import AssetIntake
from rcwh.assets.transactions import digest
from rcwh.corpus.extraction import canonical_bytes
from rcwh.corpus.locators import SourceLocatorVerifier, source_digest
from rcwh.graph import ProvenanceGraph
from rcwh.provenance import ProvenanceRepository
from rcwh.provenance.corrections import SourceExcerptCorrection, protected_snapshot
from test_source_extraction import ROOT, extraction_repo, setup_source, write_source


def write_claim(root, claim):
    shutil.copyfile(ROOT / "schemas/claim.schema.json", root / "schemas/claim.schema.json")
    directory = root / "data/provenance/claims"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "test.yaml").write_text(yaml.safe_dump({"schema_version": 1, "claims": [claim]}))


def correction_plan(root):
    _, source = setup_source(root)
    actual_locator = deepcopy(source["locator"])
    source.update(text="Old edited excerpt.", text_sha256=digest(b"Old edited excerpt."))
    source["locator"] = {"section": "legacy citation"}
    write_source(root, source)
    claim = {
        "id": "claim:test:dependent", "statement": "A supported claim", "kind": "TEST",
        "support": [{"source": source["id"], "relation": "DIRECT"}], "status": "SUPPORTED",
    }
    write_claim(root, claim)
    return {
        "schema_version": 1, "reviewer": {"kind": "AGENT_TEXT_REVIEW", "name": "Test reviewer"},
        "corrections": [{
            "source_id": source["id"], "before_sha256": source_digest(source), "locator": actual_locator,
            "rationale": "Replace an edited excerpt with fixed-carrier text.",
            "limitations": ["A locator check does not authenticate a witness."],
            "claim_reviews": [{"claim_id": claim["id"], "claim_sha256": digest(canonical_bytes(claim)),
                               "result": "RETAIN_EXISTING_ASSERTION", "rationale": "Documented review of the existing assertion."}],
        }],
    }


def test_correction_keeps_predecessor_and_authority_with_separate_actual_report(extraction_repo):
    root = extraction_repo
    plan = correction_plan(root)
    before = ProvenanceGraph.from_repo(root)
    service = SourceExcerptCorrection(root)
    proposal = service.propose(plan)
    assert ProvenanceGraph.from_repo(root).sources == before.sources
    audit = service.apply(proposal, audit_path="artifacts/migration/correction.json")
    after = ProvenanceGraph.from_repo(root)
    source = next(iter(after.sources.values()))
    assert source["text"] == "引文材料"
    assert protected_snapshot(before) == protected_snapshot(after)
    catalog = AssetCatalog.from_repo(root)
    review = json.loads(catalog.resolve(source["excerpt_revision"]["ref"]).path.read_bytes())
    assert review["before_source"] == before.sources[source["id"]]
    assert review["impact"]["claims"] == list(before.claims.values())
    assert audit["review_kind"] == "AGENT_TEXT_REVIEW"
    assert ProvenanceRepository.from_repo(root).verify_all()["status"] == "PASS"


@pytest.mark.parametrize("tamper", ["omit", "duplicate", "stale"])
def test_correction_requires_every_affected_claim_at_its_current_digest(extraction_repo, tamper):
    plan = correction_plan(extraction_repo)
    reviews = plan["corrections"][0]["claim_reviews"]
    if tamper == "omit":
        reviews.clear()
    elif tamper == "duplicate":
        reviews.append(deepcopy(reviews[0]))
    else:
        reviews[0]["claim_sha256"] = "0" * 64
    with pytest.raises(AssetError, match="CORRECTION_CLAIM_REVIEW"):
        SourceExcerptCorrection(extraction_repo).propose(plan)


def test_correction_refuses_hidden_content_skips(extraction_repo):
    plan = correction_plan(extraction_repo)
    locator = plan["corrections"][0]["locator"]
    span = locator["spans"][0]
    locator["spans"] = [{**span, "end": span["start"] + 1}, {**span, "start": span["start"] + 2}]
    with pytest.raises(AssetError, match="UNDECLARED_CONTENT_OMISSION"):
        SourceExcerptCorrection(extraction_repo).propose(plan)


@pytest.mark.parametrize("change", ["excerpt", "authority", "impact"])
def test_correction_proposal_cannot_be_forged(extraction_repo, change):
    service = SourceExcerptCorrection(extraction_repo)
    proposal = service.propose(correction_plan(extraction_repo))
    source = next(iter(proposal["after_sources"].values()))
    if change == "excerpt":
        source["text"] = "Made up"
    elif change == "authority":
        source["tier"] = "W1_DIRECT"
    else:
        proposal["results"][0]["review"]["claim_reviews"][0]["rationale"] = "Forged review"
    with pytest.raises(AssetError, match="STALE_CORRECTION_PROPOSAL"):
        service.apply(proposal, audit_path="artifacts/migration/correction.json")


@pytest.mark.parametrize("change", ["claim", "new-dependent"])
def test_downstream_changes_invalidate_the_correction_review(extraction_repo, change):
    root = extraction_repo
    service = SourceExcerptCorrection(root)
    service.apply(service.propose(correction_plan(root)), audit_path="artifacts/migration/correction.json")
    claim = next(iter(ProvenanceGraph.from_repo(root).claims.values()))
    if change == "claim":
        claim["statement"] = "A new assertion not reviewed against this revision"
        write_claim(root, claim)
    else:
        other = deepcopy(claim)
        other["id"] = "claim:test:new"
        (root / "data/provenance/claims/new.yaml").write_text(yaml.safe_dump({"schema_version": 1, "claims": [other]}))
    report = ProvenanceRepository.from_repo(root).verify_all()
    assert report["status"] == "FAIL"
    assert any("STALE_CORRECTION_IMPACT_REVIEW" in finding for finding in report["sources"][0]["findings"])


def test_even_a_new_locator_report_cannot_hide_an_unreviewed_revision(extraction_repo):
    root = extraction_repo
    service = SourceExcerptCorrection(root)
    service.apply(service.propose(correction_plan(root)), audit_path="artifacts/migration/correction.json")
    repository = ProvenanceRepository.from_repo(root)
    source = next(iter(repository.graph.sources.values()))
    source["locator"]["spans"][0]["end"] -= 1
    source["text"] = source["text"][:-1]
    source["text_sha256"] = source["locator"]["raw_text_sha256"] = digest(source["text"].encode())
    source["locator_verification"] = {"status": "UNVERIFIED", "reason": "Recomputed edited locator"}
    assert SourceLocatorVerifier(repository.catalog).verify(source)["status"] == "PASS"
    write_source(root, source)
    report = ProvenanceRepository.from_repo(root).verify_all()
    assert report["status"] == "FAIL"
    assert "STALE_CORRECTION_EXCERPT" in report["sources"][0]["findings"]


def test_stale_impact_can_receive_a_new_review_without_rewriting_the_excerpt(extraction_repo):
    root = extraction_repo
    service = SourceExcerptCorrection(root)
    plan = correction_plan(root)
    service.apply(service.propose(plan), audit_path="artifacts/migration/correction.json")
    graph = ProvenanceGraph.from_repo(root)
    source = next(iter(graph.sources.values()))
    old_binding = deepcopy(source["excerpt_revision"])
    claim = next(iter(graph.claims.values()))
    claim["statement"] = "A revised, explicitly reviewed assertion"
    write_claim(root, claim)
    item = plan["corrections"][0]
    item["before_sha256"] = source_digest(source)
    item["locator"] = deepcopy(source["locator"])
    item["claim_reviews"][0]["claim_sha256"] = digest(canonical_bytes(claim))
    item["claim_reviews"][0]["rationale"] = "New documented review for the revised assertion."
    proposal = service.propose(plan)
    assert proposal["results"][0]["review"]["operation"] == "REFRESH_IMPACT_REVIEW"
    service.apply(proposal, audit_path="artifacts/migration/refreshed-review.json")
    current = ProvenanceGraph.from_repo(root).sources[source["id"]]
    assert current["text"] == source["text"]
    assert current["excerpt_revision"] != old_binding
    review = json.loads(AssetCatalog.from_repo(root).resolve(current["excerpt_revision"]["ref"]).path.read_bytes())
    assert review["before_source"]["excerpt_revision"] == old_binding
    assert ProvenanceRepository.from_repo(root).verify_all()["status"] == "PASS"


def test_correction_transaction_recovers_source_and_audit_together(extraction_repo, monkeypatch):
    root = extraction_repo
    service = SourceExcerptCorrection(root)
    proposal = service.propose(correction_plan(root))
    from rcwh.assets import transactions
    original = transactions.apply_operation

    def interrupted(store, directory, operation):
        original(store, directory, operation)
        if operation["path"].startswith("data/provenance/sources/"):
            raise OSError("interrupted correction")

    monkeypatch.setattr(transactions, "apply_operation", interrupted)
    with pytest.raises(OSError, match="interrupted correction"):
        service.apply(proposal, audit_path="artifacts/migration/correction.json")
    monkeypatch.setattr(transactions, "apply_operation", original)
    assert AssetIntake(root).recover()["recovered_transactions"]
    assert json.loads((root / "artifacts/migration/correction.json").read_bytes())["status"] == "APPLIED"
    assert ProvenanceRepository.from_repo(root).verify_all()["status"] == "PASS"


def test_invalid_correction_audit_destination_has_no_intake_side_effects(extraction_repo):
    service = SourceExcerptCorrection(extraction_repo)
    proposal = service.propose(correction_plan(extraction_repo))
    before = deepcopy(AssetCatalog.from_repo(extraction_repo).assets)
    with pytest.raises(AssetError, match="audit must use a new path"):
        service.apply(proposal, audit_path="data/provenance/sources/correction.yaml")
    assert AssetCatalog.from_repo(extraction_repo).assets == before
