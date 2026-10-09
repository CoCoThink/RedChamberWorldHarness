from copy import deepcopy
from io import BytesIO
import json
import shutil
from types import SimpleNamespace
from zipfile import ZipFile

import pytest

from rcwh.assets import AssetCatalog, AssetError
from rcwh.assets.ingest import AssetIntake
from rcwh.assets.transactions import digest
from rcwh.corpus.extraction import canonical_bytes
from rcwh.paired_review import PairedReview
from test_source_extraction import ROOT, extraction_repo


@pytest.fixture
def paired_repo(extraction_repo, monkeypatch):
    root = extraction_repo
    for name in ("paired_review", "paired_review_protocol", "paired_review_selection"):
        shutil.copyfile(ROOT/f"schemas/{name}.schema.json", root/f"schemas/{name}.schema.json")
    pairs = []; drafts = {}
    for i in range(2):
        base, revised = f"artifacts/base-{i}.md", f"artifacts/revised-{i}.md"
        (root/base).parent.mkdir(parents=True, exist_ok=True); (root/base).write_text(f"原文 {i}。\n"); (root/revised).write_text(f"修订 {i}。\n")
        pairs.append({"baseline_token": f"MD-W{i}", "revised_token": f"RV-W{i}", "revised_artifact": revised})
        drafts[f"MD-W{i}"] = {"artifact": base}
    experiment = {"source_basis": {"p6_ref": "p6:test", "p6_snapshot_sha256": "a"*64}, "pairs": pairs}
    lab = SimpleNamespace(drafts=drafts, require_snapshot=lambda *args: None)
    project = SimpleNamespace(experiment=lambda: experiment, capability=lambda: {"status": "PASS"})
    monkeypatch.setattr("rcwh.paired_review.ProjectState.from_repo", lambda _: project)
    monkeypatch.setattr("rcwh.paired_review.ControlledMicrodraftRuntime.from_repo", lambda _: lab)
    exp_path = "data/evaluation/experiment.json"; (root/exp_path).parent.mkdir(parents=True); (root/exp_path).write_bytes(canonical_bytes(experiment))
    protocol = {"schema_version": 1, "id": "paired-review:test:v1", "minimum_reviewers": 2, "author_ids": ["author"],
                "questions": ["Which text reads better?"], "dimensions": ["voice"], "seed": "test-seed",
                "experiment": {"path": exp_path, "sha256": digest((root/exp_path).read_bytes())}, "authority_effect": "NONE"}
    proto_path = "data/evaluation/protocol.json"; (root/proto_path).write_bytes(canonical_bytes(protocol))
    packet, mapping = PairedReview(AssetCatalog.from_repo(root)).packet(proto_path)
    refs = []
    for name, raw in (("packet.zip", packet), ("mapping.json", canonical_bytes(mapping))):
        path = root.parent/name; path.write_bytes(raw); item = AssetIntake(root).ingest(path, origin=f"test:{name}", kind="REVIEW_RECORD")
        refs.append({"asset_ref": item["asset_ref"], "sha256": item["sha256"]})
    selection = {"schema_version": 1, "id": "paired-selection:test", "protocol": {"path": proto_path, "sha256": digest((root/proto_path).read_bytes())},
                 "packet": refs[0], "mapping": refs[1], "reviews": [], "authority_effect": "NONE"}
    (root/PairedReview.selection_path).write_bytes(canonical_bytes(selection))
    return root, selection, mapping


def submit(root, selected, mapping, reviewer):
    projection = {"reviewer": {"id": reviewer, "kind": "INDEPENDENT_HUMAN", "independent_of_authors": True, "mapping_unseen_during_review": True},
                  "protocol_sha256": selected["protocol"]["sha256"], "packet_sha256": selected["packet"]["sha256"],
                  "pairs": [{"pair_id": row["pair_id"], "preference": "A", "scores": {"voice": {"A": 4, "B": 3}}, "reason": "A reads naturally"} for row in mapping["pairs"]]}
    raw = root.parent/f"{reviewer}.json"; raw.write_bytes(canonical_bytes(projection))
    receipt = AssetIntake(root).ingest(raw, origin=f"test:reviewer:{reviewer}", kind="REVIEW_RECORD")
    review = {"schema_version": 1, "id": f"review:{reviewer}", **projection, "raw_review": {"asset_ref": receipt["asset_ref"], "sha256": receipt["sha256"]}, "authority_effect": "NONE"}
    path = f"data/evaluation/{reviewer}.json"; (root/path).write_bytes(canonical_bytes(review))
    selected["reviews"].append({"path": path, "sha256": digest((root/path).read_bytes())}); (root/PairedReview.selection_path).write_bytes(canonical_bytes(selected))
    return path, review


def test_packet_is_reproducible_balanced_and_has_no_route_metadata(paired_repo):
    root, selected, mapping = paired_repo
    review = PairedReview(AssetCatalog.from_repo(root)); first = review.packet(selected["protocol"]["path"]); second = review.packet(selected["protocol"]["path"])
    assert first == second and {p["baseline_label"] for p in mapping["pairs"]} == {"A", "B"}
    with ZipFile(BytesIO(first[0])) as archive:
        assert len(archive.namelist()) == 5
        assert all(term not in archive.read(name).decode() for name in archive.namelist() for term in ("MD-W", "RV-W", "baseline", "scenario_id", "artifacts/"))
    assert review.selected_summary()["status"] == "PENDING"


def test_two_submitted_reviews_are_signals_without_automatic_winner(paired_repo):
    root, selected, mapping = paired_repo
    submit(root, selected, mapping, "reader-1"); assert PairedReview(AssetCatalog.from_repo(root)).selected_summary()["status"] == "PENDING"
    submit(root, selected, mapping, "reader-2")
    result = PairedReview(AssetCatalog.from_repo(root)).selected_summary()
    assert result["status"] == "PASS" and result["review_count"] == 2
    assert result["preferences"] == {"BASELINE": 2, "REVISED": 2, "TIE": 0, "NEITHER": 0}
    assert result["winner"] is None and result["automatic_literary_pass"] is False


@pytest.mark.parametrize("target", ["scores", "incomplete", "author", "duplicate", "binding", "changed-draft"])
def test_review_cannot_outlive_inputs_or_disagree_with_raw_submission(paired_repo, target):
    root, selected, mapping = paired_repo
    path, review = submit(root, selected, mapping, "reader-1")
    if target == "changed-draft": (root/mapping["pairs"][0]["inputs"]["A"]["path"]).write_text("changed original")
    elif target == "duplicate":
        selected["reviews"].append(selected["reviews"][0]); (root/PairedReview.selection_path).write_bytes(canonical_bytes(selected))
    else:
        if target == "scores": review["pairs"][0]["scores"]["voice"]["A"] = 1
        elif target == "incomplete": review["pairs"] = review["pairs"][:1]
        elif target == "author": review["reviewer"]["id"] = "author"
        else: review["packet_sha256"] = "0"*64
        (root/path).write_bytes(canonical_bytes(review)); selected["reviews"][0]["sha256"] = digest((root/path).read_bytes()); (root/PairedReview.selection_path).write_bytes(canonical_bytes(selected))
    with pytest.raises((AssetError, ValueError)): PairedReview(AssetCatalog.from_repo(root)).selected_summary()
