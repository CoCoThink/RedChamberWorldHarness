from pathlib import Path
import json

from rcwh.competition import CompetitionRegistry
from rcwh.literary_eval import evaluate_literary_candidate
from rcwh.registry import MigrationRegistry


ROOT = Path(__file__).resolve().parents[1]
STABLE_SHA = "4645da79b1bed76f54be281c50b5df648f599ea41541fb7855685753b6a85320"
COMP_ID = "comp:43-0:ch89:pressure-test"


def record():
    return CompetitionRegistry.from_repo(ROOT).records[COMP_ID]


def test_post_m8_literary_resume_is_explicit_and_stable_body_is_not_mutated():
    state = json.loads(
        (ROOT / "data/project_state/literary_43_0_resume.json").read_text(encoding="utf-8")
    )
    assert state["status"] == "ACTIVE"
    assert state["migration_freeze_released"] is True
    assert state["literary_resume_started"] is True
    assert state["initiated_after"]["full_migration_m8"] == "PASS"
    assert state["stable_active"]["sha256"] == STABLE_SHA
    assert state["stable_active"]["changed"] is False
    assert MigrationRegistry.from_repo(ROOT).current_summary()["stable_active_sha256"] == STABLE_SHA


def test_ch89_full_candidates_are_registered_with_six_field_pass_only():
    rec = record()
    assert rec["state"] == "IN_REVIEW"
    assert rec["workflow_progress"] == {
        "BASELINE_EXCERPT": "PASS",
        "STRUCTURAL_REORDER": "PASS",
        "SMALL_TRIAL": "PASS",
        "SIX_FIELD_REGRESSION": "PASS",
        "PLOCK_REGRESSION": "PENDING",
        "BLIND_READ": "PENDING",
    }
    assert [x["id"] for x in rec["candidates"]] == ["ch89-A", "ch89-B", "ch89-C"]
    assert all(all(v == "PASS" for v in x["six_field"].values()) for x in rec["candidates"])
    assert all(x["human_plock"]["status"] == "PENDING" for x in rec["candidates"])
    assert all(x["blind_read"]["status"] == "PENDING" for x in rec["candidates"])
    assert all(x["blind_read"]["reviewer_blinded"] is False for x in rec["candidates"])
    assert rec["adjudication"]["outcome"] == "PENDING"
    assert rec["adjudication"]["promotion_state"] == "NOT_ELIGIBLE"


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


def test_ch89_blind_pack_is_opaque_but_byte_identical_to_candidate_texts():
    mapping = json.loads(
        (ROOT / "artifacts/43-0/ch89/blind/MAPPING.json").read_text(encoding="utf-8")
    )
    assert mapping["sealed_for_review"] is True
    assert set(mapping["tokens"]) == {"BR-58", "BR-14", "BR-91"}
    by_label = {x["label"]: x for x in record()["candidates"]}
    for token, label in mapping["tokens"].items():
        blind = (ROOT / f"artifacts/43-0/ch89/blind/{token}.md").read_bytes()
        candidate = (ROOT / by_label[label]["artifact"]["path"]).read_bytes()
        assert blind == candidate


def test_ch89_competition_is_consistent_but_not_adjudication_eligible_yet():
    registry = CompetitionRegistry.from_repo(ROOT)
    payload = registry.evaluate_record(ROOT, registry.records[COMP_ID])
    assert payload["consistency_errors"] == []
    assert all(x["machine_status"] == "READY_FOR_BLIND_READ" for x in payload["candidate_results"])
    assert all(x["six_field_pass"] is True for x in payload["candidate_results"])
    assert all(x["adjudication_eligible"] is False for x in payload["candidate_results"])
    assert payload["adjudication"]["outcome"] == "PENDING"
    assert payload["stable_active_mutated"] is False
