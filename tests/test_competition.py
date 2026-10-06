from copy import deepcopy
from pathlib import Path

from rcwh.competition import CompetitionRegistry, PIPELINE
from rcwh.io import load_data
from rcwh.plocks import LiteraryProtectionRegistry
from rcwh.regression import run_r4_evidence_regression
from rcwh.schema import validate_instance


def root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_production_43_0_order_is_frozen():
    registry = CompetitionRegistry.from_repo(root())
    records = sorted(
        [x for x in registry.records.values() if x["mode"] == "PRODUCTION_43_0"],
        key=lambda x: x["sequence"],
    )
    assert [x["chapter"] for x in records] == [86, 89, 92, 97]
    assert records[0]["state"] == "ADJUDICATED"
    assert records[0]["workflow_progress"]["BASELINE_EXCERPT"] == "PASS"
    assert records[0]["workflow_progress"]["STRUCTURAL_REORDER"] == "PASS"
    assert records[0]["workflow_progress"]["SMALL_TRIAL"] == "PASS"
    assert records[0]["workflow_progress"]["SIX_FIELD_REGRESSION"] == "PASS"
    assert records[0]["workflow_progress"]["PLOCK_REGRESSION"] == "PASS"
    assert records[0]["workflow_progress"]["BLIND_READ"] == "PASS"
    assert [x["label"] for x in records[0]["candidates"]] == ["A", "B", "C"]
    assert records[1]["state"] == "READY_FOR_CANDIDATES"
    assert all(x["state"] == "BLOCKED_BY_PREDECESSOR" for x in records[2:])
    assert all(x["pipeline"] == PIPELINE for x in records)


def test_real_ch86_candidates_complete_blind_gate_and_b_is_winner():
    registry = CompetitionRegistry.from_repo(root())
    payload = registry.evaluate_record(
        root(), registry.records["comp:43-0:ch86:pressure-test"]
    )
    assert {x["label"]: x["machine_status"] for x in payload["candidate_results"]} == {
        "A": "READY_FOR_BLIND_READ",
        "B": "READY_FOR_BLIND_READ",
        "C": "READY_FOR_BLIND_READ",
    }
    assert all(x["machine_matches_ledger"] for x in payload["candidate_results"])
    assert all(x["six_field_pass"] for x in payload["candidate_results"])
    assert all(x["human_plock_status"] == "PASS" for x in payload["candidate_results"])
    assert all(x["blind_read_status"] == "PASS" for x in payload["candidate_results"])
    assert all(x["reviewer_blinded"] is True for x in payload["candidate_results"])
    assert all(x["adjudication_eligible"] is True for x in payload["candidate_results"])
    assert payload["adjudication"]["outcome"] == "WINNER"
    assert payload["adjudication"]["winner_candidate_id"] == "ch86-B"
    assert payload["adjudication"]["promotion_state"] == "PROMOTION_CANDIDATE"
    assert payload["consistency_errors"] == []
    assert payload["stable_active_mutated"] is False


def test_production_ledger_validates_against_stable_active():
    registry = CompetitionRegistry.from_repo(root())
    plocks = LiteraryProtectionRegistry.from_repo(root())
    stable = run_r4_evidence_regression(root())["stable_active"]
    assert registry.validate_integrity(root(), plocks, stable) == []


def test_fixture_schema_and_machine_results_match():
    schema = load_data(root() / "schemas" / "competition.schema.json")
    records = CompetitionRegistry.load_file(
        root() / "examples" / "competitions" / "ch86_evaluator_demo.yaml"
    )
    assert len(records) == 1
    assert validate_instance(records[0], schema) == []
    payload = CompetitionRegistry({}).evaluate_record(root(), records[0])
    statuses = {x["label"]: x["machine_status"] for x in payload["candidate_results"]}
    assert statuses == {
        "A": "READY_FOR_BLIND_READ",
        "B": "REPLACEMENT_CASE",
        "C": "REJECT_BEFORE_BLIND_READ",
    }
    assert all(x["machine_matches_ledger"] for x in payload["candidate_results"])


def test_machine_ready_is_not_adjudication_eligible():
    record = CompetitionRegistry.load_file(
        root() / "examples" / "competitions" / "ch86_evaluator_demo.yaml"
    )[0]
    payload = CompetitionRegistry({}).evaluate_record(root(), record)
    a = next(x for x in payload["candidate_results"] if x["label"] == "A")
    assert a["machine_status"] == "READY_FOR_BLIND_READ"
    assert a["adjudication_eligible"] is False
    assert a["automatic_promotion"] is False
    assert payload["stable_active_mutated"] is False


def test_declared_winner_without_gates_is_inconsistent():
    record = CompetitionRegistry.load_file(
        root() / "examples" / "competitions" / "ch86_evaluator_demo.yaml"
    )[0]
    broken = deepcopy(record)
    broken["adjudication"] = {
        "outcome": "WINNER",
        "winner_candidate_id": "fixture86-A",
        "promotion_state": "PROMOTION_CANDIDATE",
    }
    payload = CompetitionRegistry({}).evaluate_record(root(), broken)
    assert payload["consistency_errors"]
    assert "has not passed all promotion gates" in payload["consistency_errors"][0]


def test_competition_never_mutates_stable_active():
    registry = CompetitionRegistry.from_repo(root())
    payload = registry.evaluate_record(
        root(), registry.records["comp:43-0:ch86:pressure-test"]
    )
    assert payload["stable_active_effect"] == "SEPARATE_PROMOTION_ONLY"
    assert payload["stable_active_mutated"] is False
    assert payload["adjudication"]["promotion_state"] == "PROMOTION_CANDIDATE"


def test_fixture_git_blob_identity_is_checked():
    schema = load_data(root() / "schemas" / "competition.schema.json")
    record = CompetitionRegistry.load_file(
        root() / "examples" / "competitions" / "ch86_evaluator_demo.yaml"
    )[0]
    assert validate_instance(record, schema) == []
    broken = deepcopy(record)
    broken["candidates"][0]["artifact"]["git_blob_sha"] = "0" * 40
    plocks = LiteraryProtectionRegistry.from_repo(root())
    stable = run_r4_evidence_regression(root())["stable_active"]
    errors = CompetitionRegistry({}).validate_record(
        root(), broken, plocks, stable, production=False
    )
    assert any("git blob identity mismatch" in x for x in errors)
