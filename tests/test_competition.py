from copy import deepcopy
from pathlib import Path
import hashlib
import json

import pytest

from rcwh.competition import CompetitionRegistry, PIPELINE
from rcwh.io import load_data
from rcwh.plocks import LiteraryProtectionRegistry
from rcwh.regression import run_r4_evidence_regression
from rcwh.schema import validate_instance


def root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_historical_ch86_opinions_do_not_grant_current_qualification():
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
    assert not any(x["six_field_pass"] for x in payload["candidate_results"])
    assert all(x["human_plock_status"] == "PENDING" for x in payload["candidate_results"])
    assert all(x["blind_read_status"] == "PENDING" for x in payload["candidate_results"])
    assert not any(x["adjudication_eligible"] for x in payload["candidate_results"])
    assert all(x["declared_gates"]["blind_read"]["status"] == "PASS" for x in payload["candidate_results"])
    assert payload["adjudication"]["outcome"] == "PENDING"
    assert payload["adjudication"]["promotion_state"] == "NOT_ELIGIBLE"
    assert payload["adjudication_qualification"] == "PENDING"
    assert payload["declared_adjudication"]["winner_candidate_id"] == "ch86-B"
    assert payload["consistency_errors"] == []
    assert payload["stable_active_mutated"] is False


def test_production_ledger_validates_against_stable_active():
    registry = CompetitionRegistry.from_repo(root())
    plocks = LiteraryProtectionRegistry.from_repo(root())
    stable = run_r4_evidence_regression(root())["stable_active"]
    assert registry.validate_integrity(root(), plocks, stable) == []


def test_all_declared_pass_flags_cannot_qualify_a_current_winner():
    registry = CompetitionRegistry.from_repo(root())
    record = registry.records["comp:43-0:ch86:pressure-test"]
    record.pop("adjudication_basis")
    assert all(c["blind_read"]["reviewer_blinded"] for c in record["candidates"])
    payload = registry.evaluate_record(root(), record)
    assert payload["adjudication_qualification"] == "FAIL"
    assert not any(c["adjudication_eligible"] for c in payload["candidate_results"])
    assert any("not passed all promotion gates" in e for e in payload["consistency_errors"])


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
        "C": "REPLACEMENT_CASE",
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
    assert payload["adjudication"]["promotion_state"] == "NOT_ELIGIBLE"


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


def test_ch86_b_promotion_content_passes_but_review_qualification_is_pending():
    from rcwh.promotion import PromotionRegistry
    registry = PromotionRegistry.from_repo(root())
    record = registry.records["promotion:ch86:b:v1-5-candidate"]
    assert record["stable_active_effect"] == "NONE"
    payload = registry.evaluate(root(), record["id"])
    assert payload["overall"] == "PENDING"
    assert payload["gates"]["COMPETITION_ELIGIBILITY"] == "PENDING"
    assert all(value == "PASS" for name, value in payload["gates"].items() if name != "COMPETITION_ELIGIBILITY")
    assert payload["pending_checks"] == ["COMPETITION_ELIGIBILITY"]
    assert payload["findings"] == []
    assert payload["stable_active_mutated"] is False
    assert payload["release_action"] == "SEPARATE_EXPLICIT_PROMOTION_REQUIRED"


def test_ch86_promotion_changes_only_chapter_86():
    from rcwh.promotion import PromotionRegistry
    registry = PromotionRegistry.from_repo(root())
    record = registry.records["promotion:ch86:b:v1-5-candidate"]
    assert record["allowed_changed_chapters"] == [86]
    assert record["baseline"]["sha256"] == "4645da79b1bed76f54be281c50b5df648f599ea41541fb7855685753b6a85320"


def test_assembled_promotion_matches_reviewed_sha_and_preserves_other_chapters():
    from rcwh.assets import AssetCatalog
    from rcwh.contracts import project_chapters
    from rcwh.promotion import PromotionRegistry, _split_chapters
    registry = PromotionRegistry.from_repo(root())
    record = next(iter(registry.records.values()))
    raw = registry.build_candidate(root(), record["id"])
    assert hashlib.sha256(raw).hexdigest() == record["candidate"]["sha256"]
    baseline = AssetCatalog.from_repo(root()).resolve(record["baseline"]["asset_ref"]).path.read_bytes()
    before = _split_chapters(baseline.decode(), project_chapters(root()))
    after = _split_chapters(raw.decode(), project_chapters(root()))
    assert {ch for ch in before if before[ch] != after[ch]} == set(record["allowed_changed_chapters"])


@pytest.mark.parametrize("fault", ["baseline", "chapter", "assembled", "scope"])
def test_promotion_build_rejects_changed_input_identity(fault):
    from rcwh.promotion import PromotionRegistry
    registry = PromotionRegistry.from_repo(root())
    record = next(iter(registry.records.values()))
    if fault == "baseline":
        record["baseline"]["sha256"] = "0" * 64
    elif fault == "chapter":
        record["candidate"]["replacements"][0]["sha256"] = "0" * 64
    elif fault == "assembled":
        record["candidate"]["sha256"] = "0" * 64
    else:
        record["allowed_changed_chapters"] = [89]
    with pytest.raises(ValueError):
        registry.build_candidate(root(), record["id"])


def test_promotion_cli_exports_exact_candidate_and_refuses_overwrite(tmp_path, monkeypatch, capsys):
    from rcwh.cli import main
    from rcwh.promotion import PromotionRegistry
    registry = PromotionRegistry.from_repo(root())
    record = next(iter(registry.records.values()))
    target = tmp_path / "candidate.md"
    monkeypatch.setattr("sys.argv", ["rcwh", "--root", str(root()), "promotion", record["id"], "--output", str(target), "--json"])
    with pytest.raises(SystemExit) as exported:
        main()
    assert exported.value.code == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["stable_active_mutated"] is False
    assert payload["overall"] == "PENDING"
    assert hashlib.sha256(target.read_bytes()).hexdigest() == record["candidate"]["sha256"]
    with pytest.raises(SystemExit) as refused:
        main()
    assert refused.value.code == 1
    assert json.loads(capsys.readouterr().out)["overall"] == "FAIL"
    assert hashlib.sha256(target.read_bytes()).hexdigest() == record["candidate"]["sha256"]
