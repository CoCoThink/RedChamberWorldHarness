from pathlib import Path

from rcwh.hypotheses import HypothesisRuntime
from rcwh.literary_production import STABLE_SHA, LiteraryProductionRuntime
from rcwh.pareto import ParetoEvaluationRuntime
from rcwh.scenario_replay import CounterfactualReplayRuntime
from rcwh.scenarios import ScenarioRuntime
from rcwh.world import WorldRuntime

ROOT = Path(__file__).resolve().parents[1]


def hypotheses():
    return HypothesisRuntime.from_repo(ROOT)


def scenarios():
    return ScenarioRuntime.from_repo(ROOT)


def replay():
    return CounterfactualReplayRuntime.from_repo(ROOT)


def world():
    return WorldRuntime.from_repo(ROOT)


def pareto():
    return ParetoEvaluationRuntime.from_repo(ROOT)


EXPECTED_FRONTIER = {
    "SCN-CURRENT-C",
    "SCN-LATE-MARRIAGE",
    "SCN-JADE-MULTILAYER",
    "SCN-MINIMAL-CAUSE-OPEN",
}


def test_p3_has_eight_axes_and_no_total_score():
    data = pareto().data
    assert len(data["full_axes"]) == 8
    assert len(data["mechanism_axes"]) == 6
    assert data["pareto_policy"]["no_total_score"] is True
    assert data["pareto_policy"]["no_automatic_winner"] is True


def test_p3_frontier_is_robust_to_expert_axis_addition():
    payload = pareto().frontier(hypotheses(), scenarios(), replay(), world())
    assert set(payload["mechanism_frontier"]) == EXPECTED_FRONTIER
    assert set(payload["full_frontier"]) == EXPECTED_FRONTIER
    assert set(payload["robust_frontier_intersection"]) == EXPECTED_FRONTIER
    assert payload["winner"] is None
    assert payload["single_total_score"] is False


def test_minimal_open_vector_preserves_open_and_has_high_literary_room():
    item = pareto().evaluate_scenario(
        "SCN-MINIMAL-CAUSE-OPEN", hypotheses(), scenarios(), replay(), world()
    )
    assert item["vector"] == {
        "evidence_fit": 1,
        "contradiction_risk": 0,
        "open_consumption": 6,
        "historical_cost": 4,
        "world_coherence": 0,
        "chapter_economy": 4,
        "front80_structural_echo": 5,
        "literary_fertility": 5,
    }
    assert item["details"]["literary_fertility"]["authority"] == "HEURISTIC_NOT_EVIDENCE"


def test_current_c_is_frontier_reference_not_automatic_winner():
    item = pareto().evaluate_scenario(
        "SCN-CURRENT-C", hypotheses(), scenarios(), replay(), world()
    )
    assert item["vector"] == {
        "evidence_fit": 3,
        "contradiction_risk": 1,
        "open_consumption": 9,
        "historical_cost": 4,
        "world_coherence": 1,
        "chapter_economy": 2,
        "front80_structural_echo": 5,
        "literary_fertility": 4,
    }
    assert item["automatic_winner"] is False
    assert item["single_total_score"] is False


def test_late_marriage_dominates_early_marriage_without_becoming_winner():
    payload = pareto().compare(
        "SCN-LATE-MARRIAGE",
        "SCN-EARLY-MARRIAGE",
        hypotheses(), scenarios(), replay(), world(),
    )
    assert payload["left_dominates_right"] is True
    assert payload["right_dominates_left"] is False
    assert payload["winner"] is None


def test_w2_guazhou_is_dominated_but_not_deleted_or_promoted_to_evidence():
    payload = pareto().frontier(hypotheses(), scenarios(), replay(), world())
    assert payload["full_dominated_by"]["SCN-MIAOYU-GUAZHOU-W2"]
    item = pareto().evaluate_scenario(
        "SCN-MIAOYU-GUAZHOU-W2", hypotheses(), scenarios(), replay(), world()
    )
    assert item["evidence_effect"] == "NONE"
    assert item["open_interface_effect"] == "NONE"


def test_p3_integrity_and_literary_authority_boundaries():
    assert pareto().validate_integrity(hypotheses(), scenarios(), replay(), world()) == []
    literary = LiteraryProductionRuntime.from_repo(ROOT)
    assert literary.data["stable_active"]["sha256"] == STABLE_SHA
    assert literary.data["stable_active"]["changed"] is False
    assert literary.data["chapter89"]["plock_manual_review"] == "PENDING"
    assert literary.data["chapter89"]["blind_read"] == "PENDING"
