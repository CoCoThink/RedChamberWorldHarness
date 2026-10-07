from pathlib import Path

from rcwh.competition import CompetitionRegistry
from rcwh.completion import CompletionGateRuntime
from rcwh.literary_production import LiteraryProductionRuntime, STABLE_SHA
from rcwh.registry import MigrationRegistry


ROOT = Path(__file__).resolve().parents[1]


def production() -> LiteraryProductionRuntime:
    return LiteraryProductionRuntime.from_repo(ROOT)


def competitions() -> CompetitionRegistry:
    return CompetitionRegistry.from_repo(ROOT)


def test_post_m8_literary_production_is_explicitly_authorized_and_active():
    summary = production().summary()
    assert summary["status"] == "ACTIVE"
    assert summary["authorized_by"]["milestone"] == "M8"
    assert summary["authorized_by"]["completion_gate"] == "PASS"
    assert summary["authorized_by"]["main_merge_verified"] is True
    assert summary["stable_sha256"] == STABLE_SHA
    assert summary["stable_mutated"] is False


def test_ch89_phase2_is_adjudicated_with_b_winner_only_as_promotion_candidate():
    record = competitions().records["comp:43-0:ch89:pressure-test"]
    assert record["state"] == "ADJUDICATED"
    assert record["workflow_progress"] == {
        "BASELINE_EXCERPT": "PASS",
        "STRUCTURAL_REORDER": "PASS",
        "SMALL_TRIAL": "PASS",
        "SIX_FIELD_REGRESSION": "PASS",
        "PLOCK_REGRESSION": "PASS",
        "BLIND_READ": "PASS",
    }
    assert record["adjudication"]["outcome"] == "WINNER"
    assert record["adjudication"]["winner_candidate_id"] == "ch89-B"
    assert record["adjudication"]["promotion_state"] == "PROMOTION_CANDIDATE"
    assert record["stable_active_effect"] == "SEPARATE_PROMOTION_ONLY"


def test_ch89_candidates_preserve_six_field_and_replacement_review_semantics():
    record = competitions().records["comp:43-0:ch89:pressure-test"]
    by_id = {x["id"]: x for x in record["candidates"]}
    assert set(by_id) == {"ch89-A", "ch89-B", "ch89-C"}
    assert {x["blind_token"] for x in by_id.values()} == {"BR-17", "BR-52", "BR-88"}
    for candidate in by_id.values():
        assert candidate["machine_expected_status"] == "REPLACEMENT_CASE"
        assert all(value == "PASS" for value in candidate["six_field"].values())
        assert candidate["human_plock"]["status"] == "REPLACEMENT_ACCEPTED"
        assert candidate["blind_read"]["status"] == "PASS"
        assert candidate["blind_read"]["reviewer_blinded"] is True


def test_ch89_competition_evaluator_accepts_b_as_eligible_without_promoting_stable():
    payload = competitions().evaluate_record(
        ROOT,
        competitions().records["comp:43-0:ch89:pressure-test"],
    )
    assert payload["consistency_errors"] == []
    assert payload["adjudication"]["winner_candidate_id"] == "ch89-B"
    assert payload["adjudication"]["promotion_state"] == "PROMOTION_CANDIDATE"
    assert payload["stable_active_mutated"] is False
    results = {x["id"]: x for x in payload["candidate_results"]}
    assert all(x["machine_status"] == "REPLACEMENT_CASE" for x in results.values())
    assert all(x["adjudication_eligible"] is True for x in results.values())


def test_ch92_becomes_the_single_active_competition_and_ch97_remains_blocked():
    records = competitions().records
    assert records["comp:43-0:ch92:pressure-test"]["state"] == "READY_FOR_CANDIDATES"
    assert records["comp:43-0:ch92:pressure-test"]["candidates"] == []
    assert records["comp:43-0:ch97:pressure-test"]["state"] == "BLOCKED_BY_PREDECESSOR"
    active = [
        record["chapter"]
        for record in records.values()
        if record.get("mode") == "PRODUCTION_43_0"
        and record["state"] in {"READY_FOR_CANDIDATES", "IN_REVIEW"}
    ]
    assert active == [92]


def test_live_production_state_matches_competition_ledger():
    runtime = production()
    registry = competitions()
    assert runtime.chapters[86]["winner"] == "ch86-B"
    assert runtime.chapters[89]["winner"] == "ch89-B"
    assert runtime.chapters[92]["state"] == "READY_FOR_CANDIDATES"
    assert runtime.chapters[97]["state"] == "BLOCKED_BY_PREDECESSOR"
    assert runtime.validate_integrity(
        CompletionGateRuntime.from_repo(ROOT),
        registry,
    ) == []


def test_historical_m8_gate_remains_pass_after_literary_resume():
    gate = CompletionGateRuntime.from_repo(ROOT)
    assert gate.state["status"] == "PASS"
    assert gate.state["completion_gate"]["overall"] == "PASS"
    assert gate.state["literature"]["resume_started"] is False
    # Gate snapshot remains historical; live resume is a separate post-M8 state.
    assert production().data["status"] == "ACTIVE"


def test_registry_stable_pointer_is_unchanged_after_ch89_adjudication():
    current = MigrationRegistry.from_repo(ROOT).current_summary()
    assert current["stable_active_sha256"] == STABLE_SHA
    assert production().data["stable_active"]["mutated"] is False
    assert production().data["ch89_phase2"]["stable_promotion"] is False
