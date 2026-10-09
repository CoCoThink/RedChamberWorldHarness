from copy import deepcopy
from pathlib import Path
import json

from rcwh.competition import CompetitionRegistry
from rcwh.literary_eval import evaluate_literary_candidate
from rcwh.workflow import ProjectState
from rcwh.literary_suite import LiteraryEvaluatorSuite


ROOT = Path(__file__).resolve().parents[1]
COMP_ID = "comp:43-0:ch89:pressure-test"


def record():
    return CompetitionRegistry.from_repo(ROOT).records[COMP_ID]


def test_post_m8_literary_resume_is_explicit_and_stable_body_is_not_mutated():
    state = json.loads(
        (ROOT / "data/project_state/literary_43_0_resume.json").read_text(encoding="utf-8")
    )
    assert state["status"] == "ACTIVE"
    assert state["literary_resume_started"] is True
    assert state["stable_active"]["sha256"] == ProjectState.from_repo(ROOT).release().data["text_sha256"]
    assert ProjectState.from_repo(ROOT).release().validate_storage() == []


def test_ch89_full_candidates_have_unique_identities_and_blind_tokens():
    candidates = record()["candidates"]
    assert candidates
    assert len({x["id"] for x in candidates}) == len(candidates)
    assert len({x["blind_token"] for x in candidates}) == len(candidates)
    assert all(all(v == "PASS" for v in x["six_field"].values()) for x in candidates)


def test_ch89_candidates_pass_machine_literary_precheck_without_auto_literary_pass():
    rec = record()
    for candidate in rec["candidates"]:
        text = (ROOT / candidate["artifact"]["path"]).read_text(encoding="utf-8")
        payload = evaluate_literary_candidate(
            ROOT,
            rec["plock_ref"],
            text,
            candidate_name=candidate["id"],
        )
        assert payload["machine_status"] == "READY_FOR_BLIND_READ"
        assert payload["automatic_literary_pass"] is False
        assert payload["promotion_eligible"] is False
        assert payload["protected_anchor_losses"] == []
        assert payload["feature_signal_gaps"] == []


def test_ch89_terminal_plock_is_literal_last_line_after_quote_normalization():
    for candidate in record()["candidates"]:
        text = (ROOT / candidate["artifact"]["path"]).read_text(encoding="utf-8").rstrip()
        normalized = text.rstrip("”’\"'")
        assert normalized.endswith("谁家的水桶还在井边？")
        assert "麝月忙起身道：“又是我的。”提着灯便出去了。" not in text[-120:]


def test_ch89_blind_pack_is_opaque_but_byte_identical_to_candidate_texts(tmp_path):
    mapping = {candidate["blind_token"]: candidate["label"] for candidate in record()["candidates"]}
    output = tmp_path / "review"
    LiteraryEvaluatorSuite.from_repo(ROOT).competition_blind_packet(record(), output)
    by_label = {x["label"]: x for x in record()["candidates"]}
    for token, label in mapping.items():
        blind = (output / f"{token}.md").read_bytes()
        candidate = (ROOT / by_label[label]["artifact"]["path"]).read_bytes()
        assert blind == candidate


def test_ch89_missing_reviews_cannot_be_replaced_by_machine_pass():
    registry = CompetitionRegistry.from_repo(ROOT)
    rec = deepcopy(registry.records[COMP_ID])
    rec["state"] = "IN_REVIEW"
    rec["workflow_progress"].update(PLOCK_REGRESSION="PENDING", BLIND_READ="PENDING")
    rec["adjudication"].update(outcome="PENDING", winner_candidate_id=None, promotion_state="NOT_ELIGIBLE")
    for candidate in rec["candidates"]:
        candidate["human_plock"]["status"] = "PENDING"
        candidate["blind_read"].update(status="PENDING", reviewer_blinded=False)
    payload = registry.evaluate_record(ROOT, rec)
    assert payload["consistency_errors"] == []
    assert all(x["machine_status"] == "READY_FOR_BLIND_READ" for x in payload["candidate_results"])
    assert all(x["six_field_pass"] is False for x in payload["candidate_results"])
    assert all(all(v == "PASS" for v in x["declared_gates"]["six_field"].values()) for x in payload["candidate_results"])
    assert all(x["adjudication_eligible"] is False for x in payload["candidate_results"])
    assert payload["adjudication"]["outcome"] == "PENDING"
    assert payload["stable_active_mutated"] is False
