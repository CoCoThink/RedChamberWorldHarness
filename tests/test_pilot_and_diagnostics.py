"""Actual trial material plus synthetic ranking receipts; no invented readers."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import sys

import pytest

from rcwh.candidate_reviews import canonical_bytes, digest
from rcwh.evaluation.characters import CharacterProfiles
from rcwh.evaluation.comparison import DIMENSIONS, comparative_reviews
from rcwh.evaluation.pilot import PilotStudy, STUDY_PATH
from rcwh.evaluation.style import style_diagnostics

ROOT = Path(__file__).resolve().parents[1]


def fixture_study(tmp_path):
    study = PilotStudy(ROOT)
    for binding in study.data["inputs"]:
        p = tmp_path / binding["path"]; p.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / binding["path"], p)
    for arm in study.data["arms"]:
        for chapter in arm["drafts"]:
            p = tmp_path / chapter["text"]["path"]; p.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / chapter["text"]["path"], p)
    p = tmp_path / STUDY_PATH; shutil.copyfile(ROOT / STUDY_PATH, p)
    return PilotStudy(tmp_path)


def binding(root, name, value):
    raw = canonical_bytes(value); p = root/name; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(raw)
    return {"path": name, "sha256": digest(raw)}


def reviews(export_root):
    raw = (export_root/"public/packet.json").read_bytes(); packet = json.loads(raw)
    tokens = [c["token"] for c in packet["candidates"]]
    submissions = []
    for reader in range(2):
        observations = {}
        for c in packet["candidates"]:
            text = (export_root/"public"/c["file"]).read_bytes().decode()
            observations[c["token"]] = {d: {"reason": "Synthetic ranking receipt, not real literary opinion.",
                                                   "spans": [{"start": 0, "end": 30, "quote": text[:30]}]} for d in DIMENSIONS}
        value = {"id": f"fixture:{reader}", "report_kind": "REVIEW_OPINION", "packet_sha256": digest(raw), "context_sha256": packet["context_sha256"],
                 "reviewer": {"principal_id": f"fixture:human:{reader}", "source_id": f"fixture:source:{reader}",
                              "kind": "INDEPENDENT_HUMAN", "mapping_unseen_during_review": True, "independent_of_authors": True},
                 "ranking": [[tokens[0]], tokens[1:]], "recommendation": "NEITHER", "observations": observations}
        submissions.append(value)
    return submissions


def save_reviews(root, submissions):
    result = []
    for i, review in enumerate(submissions):
        raw = {k: v for k,v in review.items() if k not in {"raw_review", "authority_effect"}}
        review["raw_review"] = binding(root, f"submissions/{i}-original.json", raw)
        result.append(binding(root, f"submissions/{i}.json", review))
    return result


def test_actual_three_chapter_trials_are_bound_and_cannot_claim_harness_effect():
    result = PilotStudy(ROOT).summary()
    assert result["chapters"] == [85,86,87]
    assert len(result["drafts"]) == 9
    assert all(d["length"] >= 500 for d in result["drafts"])
    assert result["route_comparisons"][0]["left_only"] and result["route_comparisons"][0]["right_only"]
    assert result["status"] == "PENDING"
    assert result["controlled_workflow_effect"] == "NOT_ESTIMABLE"
    assert result["valid_independent_review_count"] == 0


@pytest.mark.parametrize("fault", ["same_route", "nonconsecutive", "discontinuity", "text", "span", "context"])
def test_trial_catches_fake_route_and_input_drift(tmp_path, fault):
    study = fixture_study(tmp_path)
    if fault == "same_route": study.data["arms"][1]["causal_choices"] = deepcopy(study.data["arms"][0]["causal_choices"])
    if fault == "nonconsecutive": study.data["chapters"][2] = 89
    if fault == "discontinuity": study.data["arms"][0]["drafts"][1]["entry"]["daiyu.life"] = "DEAD"
    if fault == "text": (tmp_path/study.data["arms"][0]["drafts"][0]["text"]["path"]).write_text("changed")
    if fault == "span": study.data["arms"][0]["drafts"][0]["intent_spans"][0]["quote"] = "invented"
    if fault == "context": (tmp_path/study.data["inputs"][0]["path"]).write_text("{}")
    with pytest.raises(ValueError): study.summary()


def test_export_separates_mapping_and_randomizes_each_round(tmp_path):
    study = PilotStudy(ROOT)
    study.export(tmp_path/"one"); study.export(tmp_path/"two")
    packet = json.loads((tmp_path/"one/public/packet.json").read_bytes())
    second = json.loads((tmp_path/"two/public/packet.json").read_bytes())
    assert {c["token"] for c in packet["candidates"]}.isdisjoint(c["token"] for c in second["candidates"])
    anonymous = (tmp_path/"one/public/packet.json").read_text()
    assert all(s not in anonymous for s in ("agent:codex", "direct-example", "medical", "books", "IMPROVED_HARNESS"))
    assert comparative_reviews(tmp_path/"one", [])["status"] == "PENDING"
    with pytest.raises(FileExistsError): study.export(tmp_path/"one")


def test_two_comparative_readers_preserve_ties_and_neither(tmp_path):
    PilotStudy(ROOT).export(tmp_path/"export")
    report = comparative_reviews(tmp_path/"export", save_reviews(tmp_path/"export", reviews(tmp_path/"export")))
    assert report["status"] == "PASS" and report["review_count"] == 2
    assert any(r["outcomes"] == ["TIE", "TIE"] for r in report["pairwise"])
    assert all(r["recommendation"] == "NEITHER" for r in report["reviews"])
    assert report["automatic_winner"] is None


@pytest.mark.parametrize("fault", ["duplicate", "author_source", "model", "missing_rank", "span", "stale"])
def test_comparative_review_identity_coverage_and_binding(tmp_path, fault):
    PilotStudy(ROOT).export(tmp_path/"export"); submissions = reviews(tmp_path/"export")
    if fault == "duplicate": submissions[1]["reviewer"]["source_id"] = submissions[0]["reviewer"]["source_id"]
    if fault == "author_source": submissions[0]["reviewer"]["source_id"] = "agent:codex"
    if fault == "model": submissions[0]["reviewer"]["kind"] = "MODEL"
    if fault == "missing_rank": submissions[0]["ranking"].pop()
    if fault == "span": next(iter(submissions[0]["observations"].values()))[DIMENSIONS[0]]["spans"][0]["quote"] = "invented"
    if fault == "stale": submissions[0]["packet_sha256"] = "0"*64
    assert comparative_reviews(tmp_path/"export", save_reviews(tmp_path/"export", submissions))["status"] == "FAIL"


def test_mapping_and_current_study_context_cannot_change_after_blind_export(tmp_path):
    PilotStudy(ROOT).export(tmp_path/"export")
    with pytest.raises(ValueError, match="stale"): comparative_reviews(tmp_path/"export", [], "0"*64)
    p=tmp_path/"export/coordinator/mapping.json"; value=json.loads(p.read_bytes()); value["authors"][0]["source_id"]="other"
    p.write_bytes(canonical_bytes(value))
    with pytest.raises(ValueError, match="mapping"): comparative_reviews(tmp_path/"export", [])


@pytest.mark.parametrize("fault", ["false_string", "numeric_identity", "empty_review_id"])
def test_malformed_custody_declarations_cannot_count_as_independent_reading(tmp_path, fault):
    PilotStudy(ROOT).export(tmp_path/"export")
    submissions = reviews(tmp_path/"export")
    if fault == "false_string": submissions[0]["reviewer"]["mapping_unseen_during_review"] = "false"
    if fault == "numeric_identity": submissions[0]["reviewer"]["principal_id"] = 123
    if fault == "empty_review_id": submissions[0]["id"] = " "
    assert comparative_reviews(tmp_path/"export", save_reviews(tmp_path/"export", submissions))["status"] == "FAIL"


def test_direct_author_request_has_same_frozen_route_without_trial_feedback():
    study = PilotStudy(ROOT)
    direct = study.author_request("DIRECT_WRITING", "medical")
    old = study.author_request("LEGACY_HARNESS", "medical")
    improved = study.author_request("IMPROVED_HARNESS", "medical")
    for request in (old, improved):
        assert request["constraints"] == direct["constraints"] and request["route"] == direct["route"]
        assert request["budget"] == direct["budget"] and request["feedback"] == []
    assert "drafts" not in json.dumps(direct)
    assert direct["workflow_support"] is None
    assert old["workflow_support"]["kind"] != improved["workflow_support"]["kind"]


def test_failed_author_program_is_recorded_and_not_adopted(tmp_path):
    payload = PilotStudy(ROOT).run_author("DIRECT_WRITING", "medical", [sys.executable,"-c","print('{}')"], tmp_path/"trace.json")
    assert payload["status"] == "FAIL" and payload["literary_acceptance"] == "PENDING"
    trace = json.loads((tmp_path/"trace.json").read_bytes())
    assert trace["program_invocations"] == 1 and trace["stdout"] == "{}\n"


def test_style_tracks_observations_without_word_quotas_or_quality_pass():
    text = '第八十六回  守残灯侍儿误候  留冷药痴子来迟\n\n话说宝玉道：“姑娘，且说给我听。”'
    report = style_diagnostics(text, ["灯下无人语，窗前有旧书。"])
    assert report["title_track"]["equal_length"] is True
    assert report["prose_track"]["narrator_markers"]["且说"] == 0
    assert report["poetry_track"][0]["line_lengths"] == [5,5]
    assert report["literary_quality_verified"] is False


def test_character_coverage_resolves_zijuan_and_abstains_for_sparse_roles():
    profiles = CharacterProfiles(ROOT)
    report = profiles.summary()
    assert report["characters"] == 29 and report["registered_voices"] == 18
    assert profiles.profile("zijuan")["coverage"] == "REGISTERED_VOICE"
    assert profiles.profile("wei_ruolan")["coverage"] == "SPARSE_ABSTAIN"
    assert profiles.profile("liwan")["supplement"]["examples"]
    assert all(hook["resolved"] for hook in report["hooks"])
