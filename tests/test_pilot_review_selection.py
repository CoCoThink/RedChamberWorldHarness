"""Synthetic, small pilot selections; these are not actual literary reviews."""
from copy import deepcopy
import json
from pathlib import Path
import shutil

import pytest

from rcwh.candidate_reviews import canonical_bytes, digest
from rcwh.evaluation.comparison import DIMENSIONS, comparative_reviews, load_comparative_packet, validate_comparative_review
from rcwh.evaluation.pilot import PilotStudy, REVIEW_SELECTION_PATH, STUDY_PATH, selected_reviews
from rcwh.evaluation.style import style_diagnostics
from rcwh.schema import validate_instance

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas/pilot_review_selection.schema.json"


def save(root, relative, value):
    raw = canonical_bytes(value)
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return {"path": relative, "sha256": digest(raw)}


@pytest.fixture
def pilot(tmp_path):
    schema = tmp_path / "schemas/pilot_review_selection.schema.json"
    schema.parent.mkdir()
    shutil.copyfile(SCHEMA, schema)
    source = save(tmp_path, "inputs/task.json", {"task": "Synthetic fixture"})
    arms = []
    for index, workflow in enumerate(("IMPROVED_HARNESS", "IMPROVED_HARNESS", "DIRECT_WRITING")):
        drafts = []
        for chapter in (85, 86, 87):
            text = f"第{chapter}回 测试\n话说人物道：“此乃测试。”路线{index}。"
            raw = text.encode()
            relative = f"drafts/{index}-{chapter}.txt"
            path = tmp_path / relative
            path.parent.mkdir(exist_ok=True)
            path.write_bytes(raw)
            drafts.append({"chapter": chapter, "text": {"path": relative, "sha256": digest(raw)},
                           "entry": {}, "exit": {}, "intent_spans": [{"start": 0, "end": 1, "quote": text[0]}]})
        arms.append({"id": f"route-{index}", "workflow": workflow, "drafts": drafts, "costs": {"basis": "SYNTHETIC"},
                     "causal_choices": [{"chapter": 85, "actor": "actor", "action": f"action-{index}",
                                        "recipient": "recipient", "consequence": "consequence"}]})
    save(tmp_path, STUDY_PATH, {"chapters": [85, 86, 87], "inputs": [source], "arms": arms,
                              "budget": {"minimum_trial_characters_per_chapter": 1}, "review_questions": ["Synthetic question"],
                              "authors": [{"principal_id": "fixture:author", "source_id": "fixture:author-source"}]})
    study = PilotStudy(tmp_path)
    study.export(tmp_path / "export")
    return study


def selection(study, reviews=()):
    root = study.root
    value = {"schema_version": 1, "export_root": "export", "packet_sha256": digest((root / "export/public/packet.json").read_bytes()),
             "mapping_sha256": digest((root / "export/coordinator/mapping.json").read_bytes()),
             "reviews": list(reviews), "authority_effect": "NONE"}
    save(root, REVIEW_SELECTION_PATH, value)
    return value


def opinion(study, number):
    packet, mapping, texts = load_comparative_packet(study.root / "export")
    tokens = list(texts)
    return {"id": f"fixture:{number}", "report_kind": "REVIEW_OPINION", "packet_sha256": mapping["packet_sha256"],
            "context_sha256": packet["context_sha256"],
            "reviewer": {"principal_id": f"fixture:reader:{number}", "source_id": f"fixture:reader-source:{number}",
                         "kind": "INDEPENDENT_HUMAN", "mapping_unseen_during_review": True, "independent_of_authors": True},
            "ranking": [[tokens[0]], tokens[1:]], "recommendation": "NEITHER",
            "observations": {token: {dimension: {"reason": "Synthetic receipt, not a literary opinion.",
                             "spans": [{"start": 0, "end": 1, "quote": text[0]}]} for dimension in DIMENSIONS}
                             for token, text in texts.items()}}


def register(study, number, submitted=None, root=None):
    root = study.root if root is None else root
    submitted = opinion(study, number) if submitted is None else submitted
    raw = save(root, f"data/evaluation/pilot85_87/reviews/raw/{number}.json", submitted)
    return save(root, f"data/evaluation/pilot85_87/reviews/{number}.json",
                {**submitted, "raw_review": raw, "authority_effect": "NONE"})


def test_no_selection_preserves_original_complete_summary(pilot):
    expected = {"status": "PENDING", "scope": "CONSECUTIVE_RESEARCH_TRIAL", "chapters": [85, 86, 87],
                "context_sha256": digest(canonical_bytes(pilot.context())),
                "drafts": [], "route_comparisons": [{"left": "route-0", "right": "route-1",
                    "left_only": [(85, "actor", "action-0", "recipient", "consequence")],
                    "right_only": [(85, "actor", "action-1", "recipient", "consequence")],
                    "scope": "DECLARED_CAUSAL_PLAN_DIFFERENCE", "text_realisation": "PENDING_READING"}],
                "direct_control_status": "CONTAMINATED_INTERNAL_EXAMPLE_REQUIRES_FRESH_AUTHOR_RUN",
                "controlled_workflow_effect": "NOT_ESTIMABLE", "valid_independent_review_count": 0,
                "costs": [{"arm": arm["id"], "record": arm["costs"]} for arm in pilot.data["arms"]],
                "remaining": ["FRESH_DIRECT_AND_OLD_WORKFLOW_CONTROL", "INDEPENDENT_SEMANTIC_READINGS", "TWO_COMPARATIVE_READERS", "REVISION_AND_REREVIEW"],
                "authority_effect": "NONE", "stable_active_mutated": False}
    for arm in pilot.data["arms"]:
        for chapter in arm["drafts"]:
            raw = (pilot.root / chapter["text"]["path"]).read_bytes()
            expected["drafts"].append({"arm": arm["id"], "chapter": chapter["chapter"], "sha256": digest(raw),
                                      "length": len(raw.decode()), "intent_links": "CONSISTENT",
                                      "semantic_realisation": "PENDING_INDEPENDENT_READING", "style": style_diagnostics(raw.decode())})
    assert canonical_bytes(pilot.summary()) == canonical_bytes(expected)


@pytest.mark.parametrize("count", [0, 1, 2])
def test_registered_reviews_count_without_automatic_literary_acceptance(pilot, count):
    study_bytes = (pilot.root / STUDY_PATH).read_bytes()
    original_context = digest(canonical_bytes(pilot.context()))
    selection(pilot, [register(pilot, number) for number in range(count)])
    report = pilot.summary()
    assert report["status"] == "PENDING"
    assert report["valid_independent_review_count"] == count
    assert ("TWO_COMPARATIVE_READERS" in report["remaining"]) == (count < 2)
    assert report["comparative_reading"]["status"] == ("PASS" if count == 2 else "PENDING")
    assert report["comparative_reading"]["automatic_winner"] is None
    assert report["comparative_reading"]["literary_acceptance"] == "PENDING"
    assert report["authority_effect"] == "NONE"
    assert report["context_sha256"] == original_context
    assert (pilot.root / STUDY_PATH).read_bytes() == study_bytes
    assert selected_reviews(pilot.root, original_context) == report["comparative_reading"]


def test_legacy_review_root_output_is_unchanged(pilot):
    export = pilot.root / "export"
    reviews = [register(pilot, n, root=export) for n in range(2)]
    report = comparative_reviews(export, reviews)
    submission = opinion(pilot, 0)
    tokens = sorted(submission["observations"])
    positions = {token: index for index, group in enumerate(submission["ranking"]) for token in group}
    assert report == {"status": "PASS", "report_kind": "COMPUTED_CHECK", "scope": "COMPARATIVE_READING_ONLY",
                      "review_count": 2, "minimum_reviewers": 2, "reviews": [opinion(pilot, n) for n in range(2)],
                      "pairwise": [{"left": left, "right": right, "outcomes": ["TIE" if positions[left] == positions[right] else left if positions[left] < positions[right] else right] * 2, "agreement": True}
                                   for index, left in enumerate(tokens) for right in tokens[index + 1:]],
                      "findings": [], "automatic_winner": None, "literary_acceptance": "PENDING",
                      "independence_basis": "SUBMITTED_IDENTITIES_AND_CUSTODY_ATTESTATIONS", "authority_effect": "NONE"}
    assert report == comparative_reviews(export, reviews, review_root=export)


@pytest.mark.parametrize("fault", ["context", "packet_hash", "mapping_hash", "mapping_commitment", "extra_key", "bad_authority", "unsafe_export", "malformed_json"])
def test_invalid_selection_or_export_fails_closed(pilot, fault):
    value = selection(pilot)
    if fault == "context":
        changed = deepcopy(pilot.data)
        changed["review_questions"].append("Context changed")
        save(pilot.root, STUDY_PATH, changed)
    elif fault in {"packet_hash", "mapping_hash"}:
        value["packet_sha256" if fault == "packet_hash" else "mapping_sha256"] = "0" * 64
    elif fault == "mapping_commitment":
        path = pilot.root / "export/coordinator/mapping.json"
        mapping = json.loads(path.read_bytes())
        mapping["authors"][0]["source_id"] = "changed"
        save(pilot.root, "export/coordinator/mapping.json", mapping)
        value["mapping_sha256"] = digest(path.read_bytes())
    elif fault == "extra_key":
        value["unapproved"] = True
    elif fault == "bad_authority":
        value["authority_effect"] = "PASS"
    elif fault == "unsafe_export":
        value["export_root"] = "../export"
    save(pilot.root, REVIEW_SELECTION_PATH, value)
    if fault == "malformed_json":
        (pilot.root / REVIEW_SELECTION_PATH).write_text("{")
    report = PilotStudy(pilot.root).summary()
    assert report["status"] == "FAIL"
    assert report["findings"]
    assert report["valid_independent_review_count"] == 0
    with pytest.raises((ValueError, OSError)):
        selected_reviews(pilot.root, report["context_sha256"])


@pytest.mark.parametrize("fault", ["record_hash", "raw_hash", "raw_mismatch", "stale_context", "duplicate", "missing_record", "unsafe_record", "unsafe_raw", "malformed_opinion"])
def test_invalid_registered_bindings_are_reported_not_ignored(pilot, fault):
    first = register(pilot, 0)
    submitted = opinion(pilot, 1)
    if fault == "stale_context":
        submitted["context_sha256"] = "0" * 64
    if fault == "duplicate":
        submitted["reviewer"]["source_id"] = opinion(pilot, 0)["reviewer"]["source_id"]
    if fault == "malformed_opinion":
        next(iter(submitted["observations"].values()))[DIMENSIONS[0]]["reason"] = 7
    second = register(pilot, 1, submitted)
    path = pilot.root / second["path"]
    record = json.loads(path.read_bytes())
    if fault in {"raw_hash", "unsafe_raw"}:
        record["raw_review"]["sha256" if fault == "raw_hash" else "path"] = "0" * 64 if fault == "raw_hash" else "../outside.json"
        second = save(pilot.root, second["path"], record)
    if fault == "record_hash":
        second["sha256"] = "0" * 64
    if fault == "missing_record":
        path.unlink()
    if fault == "unsafe_record":
        second["path"] = "../outside.json"
    if fault == "raw_mismatch":
        submitted["recommendation"] = "CONTINUE"
        save(pilot.root, record["raw_review"]["path"], submitted)
        record["raw_review"]["sha256"] = digest((pilot.root / record["raw_review"]["path"]).read_bytes())
        second = save(pilot.root, second["path"], record)
    selection(pilot, [first, second])
    report = pilot.summary()
    assert report["status"] == "FAIL" and report["findings"]
    assert report["valid_independent_review_count"] == (0 if fault == "unsafe_record" else 1)
    assert "TWO_COMPARATIVE_READERS" in report["remaining"]


@pytest.mark.parametrize("relative", ["public/packet.json", "coordinator/mapping.json", "candidate", REVIEW_SELECTION_PATH])
def test_symlink_packet_mapping_candidate_and_selection_are_rejected(pilot, relative):
    selection(pilot)
    if relative == "candidate":
        candidate = load_comparative_packet(pilot.root / "export")[0]["candidates"][0]
        relative = "public/" + candidate["file"]
    path = pilot.root / relative if relative == REVIEW_SELECTION_PATH else pilot.root / "export" / relative
    original = path.read_bytes()
    target = pilot.root / "link-target"
    target.write_bytes(original)
    path.unlink()
    path.symlink_to(target)
    report = pilot.summary()
    assert report["status"] == "FAIL"
    assert any("symlink" in finding for finding in report["findings"])


def test_pure_preflight_requires_no_raw_receipt_and_performs_no_writes(pilot):
    packet, mapping, texts = load_comparative_packet(pilot.root / "export")
    submitted = opinion(pilot, 0)
    before = sorted(path.relative_to(pilot.root).as_posix() for path in pilot.root.rglob("*") if path.is_file())
    assert validate_comparative_review(submitted, packet, mapping, texts) is None
    submitted["reviewer"]["independent_of_authors"] = False
    with pytest.raises(ValueError, match="dependence"):
        validate_comparative_review(submitted, packet, mapping, texts)
    assert sorted(path.relative_to(pilot.root).as_posix() for path in pilot.root.rglob("*") if path.is_file()) == before


def test_submission_from_exported_template_preserves_none_authority_and_original_bytes(pilot):
    template = json.loads((pilot.root / "export/public/reading-template.json").read_bytes())
    template.update(opinion(pilot, 0))
    assert template["authority_effect"] == "NONE"
    binding = register(pilot, 0, template)
    raw_path = pilot.root / "data/evaluation/pilot85_87/reviews/raw/0.json"
    raw_bytes = raw_path.read_bytes()
    selection(pilot, [binding])
    report = pilot.summary()
    assert report["status"] == "PENDING" and report["valid_independent_review_count"] == 1
    assert report["comparative_reading"]["reviews"] == [opinion(pilot, 0)]
    assert raw_path.read_bytes() == raw_bytes


@pytest.mark.parametrize("fault", ["extra_field", "authority", "embedded_raw"])
def test_submitted_metadata_cannot_add_authority_or_receipts(pilot, fault):
    submitted = opinion(pilot, 0)
    if fault == "extra_field":
        submitted["unapproved"] = True
    elif fault == "authority":
        submitted["authority_effect"] = "PASS"
    else:
        submitted["raw_review"] = {"path": "other.json", "sha256": "0" * 64}
    selection(pilot, [register(pilot, 0, submitted)])
    report = pilot.summary()
    assert report["status"] == "FAIL" and report["findings"]
    assert report["valid_independent_review_count"] == 0


def test_default_selection_binds_actual_existing_packet():
    value = json.loads((ROOT / REVIEW_SELECTION_PATH).read_bytes())
    assert validate_instance(value, SCHEMA) == []
    report = selected_reviews(ROOT, digest(canonical_bytes(PilotStudy(ROOT).context())))
    assert report["status"] == "PENDING" and report["review_count"] == 0
