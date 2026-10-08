from pathlib import Path

from rcwh.literary_eval import (
    LiteraryEvaluationProfileRegistry,
    evaluate_literary_candidate,
)
from rcwh.plocks import LiteraryProtectionRegistry


def root() -> Path:
    return Path(__file__).resolve().parents[1]


def text(name: str) -> str:
    return (root() / "examples" / "literary" / name).read_text(encoding="utf-8")


def test_profiles_resolve_to_plocks():
    plocks = LiteraryProtectionRegistry.from_repo(root())
    profiles = LiteraryEvaluationProfileRegistry.from_repo(root())
    assert profiles.validate_integrity(plocks) == []
    assert profiles.profiles


def test_preserved_candidate_is_ready_but_never_auto_passed():
    result = evaluate_literary_candidate(
        root(),
        "plock:ch86:cold-medicine",
        text("ch86_preserved.txt"),
        "A",
    )
    assert result["machine_status"] == "READY_FOR_BLIND_READ"
    assert result["automatic_literary_pass"] is False
    assert result["promotion_eligible"] is False
    assert result["evidence_core_regression"] == "PASS"
    assert result["protected_anchor_losses"] == []


def test_changed_terminal_becomes_replacement_case_not_automatic_failure():
    result = evaluate_literary_candidate(
        root(),
        "plock:ch86:cold-medicine",
        text("ch86_replacement_case.txt"),
        "B",
    )
    assert result["machine_status"] == "REPLACEMENT_CASE"
    assert result["protected_anchor_losses"]
    assert "CANDIDATE_COMPETITION" in result["next_gates"]
    assert "HUMAN_BLIND_READ" in result["next_gates"]


def test_explicit_drift_is_rejected_before_blind_read():
    result = evaluate_literary_candidate(
        root(),
        "plock:ch86:cold-medicine",
        text("ch86_blocked.txt"),
        "C",
    )
    assert result["machine_status"] == "REJECT_BEFORE_BLIND_READ"
    assert {x["id"] for x in result["blockers"]} >= {
        "explicit-death-poem",
        "explicit-philosophical-closure",
    }


def test_signal_gap_does_not_pretend_to_be_literary_failure():
    result = evaluate_literary_candidate(
        root(),
        "plock:ch86:cold-medicine",
        "药碗还在。药不是还没吃么？再温一温。今儿早起她还说药苦。\n"
        "那盏药早已冷透，再没有人去温。",
        "thin",
    )
    assert result["machine_status"] == "READY_FOR_BLIND_READ"
    assert "unfinished-writing" in result["feature_signal_gaps"]
    assert result["promotion_eligible"] is False


def test_terminal_anchor_must_actually_be_terminal():
    candidate = (
        "药不是还没吃么？再温一温。今儿早起她还说药苦。\n"
        "那盏药早已冷透，再没有人去温。\n"
        "作者又解释了一段。"
    )
    result = evaluate_literary_candidate(
        root(), "plock:ch86:cold-medicine", candidate, "tail-added"
    )
    assert result["machine_status"] == "REPLACEMENT_CASE"
    assert "那盏药早已冷透，再没有人去温。" in result["protected_anchor_losses"]
