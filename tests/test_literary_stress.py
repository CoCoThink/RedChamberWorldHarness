from pathlib import Path

from rcwh.hypotheses import HypothesisRuntime
from rcwh.literary_ecology import LiteraryEcologyRuntime
from rcwh.literary_production import LiteraryProductionRuntime, STABLE_SHA
from rcwh.literary_stress import ScenarioLiteraryStressRuntime
from rcwh.pareto import ParetoEvaluationRuntime
from rcwh.scenario_replay import CounterfactualReplayRuntime
from rcwh.scenarios import ScenarioRuntime
from rcwh.world import WorldRuntime

ROOT = Path(__file__).resolve().parents[1]

FRONTIER = {
    "SCN-CURRENT-C",
    "SCN-LATE-MARRIAGE",
    "SCN-JADE-MULTILAYER",
    "SCN-MINIMAL-CAUSE-OPEN",
}


def stress():
    return ScenarioLiteraryStressRuntime.from_repo(ROOT)


def ecology():
    return LiteraryEcologyRuntime.from_repo(ROOT)


def test_p4_covers_exactly_the_p3_robust_frontier():
    pareto = ParetoEvaluationRuntime.from_repo(ROOT)
    hypotheses = HypothesisRuntime.from_repo(ROOT)
    scenarios = ScenarioRuntime.from_repo(ROOT)
    replay = CounterfactualReplayRuntime.from_repo(ROOT)
    world = WorldRuntime.from_repo(ROOT)
    frontier = pareto.frontier(hypotheses, scenarios, replay, world)
    assert set(frontier["robust_frontier_intersection"]) == FRONTIER
    assert set(stress().contracts) == FRONTIER


def test_all_four_scenarios_have_ready_stress_contracts():
    payload = stress().evaluate_all(ecology())
    assert payload["status"] == "PASS"
    assert len(payload["scenarios"]) == 4
    assert all(x["status"] == "STRESS_CONTRACT_READY" for x in payload["scenarios"])
    assert all(x["probe_count"] == 5 for x in payload["scenarios"])
    assert payload["winner"] is None
    assert payload["automatic_literary_pass"] is False


def test_p4_has_eight_dimensions_and_twenty_scene_level_probes():
    assert len(stress().dimensions) == 8
    assert sum(len(x["probes"]) for x in stress().contracts.values()) == 20


def test_every_contract_hits_every_literary_dimension_at_least_twice():
    for scenario_id in FRONTIER:
        payload = stress().evaluate(scenario_id, ecology())
        assert min(payload["coverage"]["dimension_hits"].values()) >= 2


def test_late_marriage_stress_contract_keeps_resource_life_in_the_center():
    payload = stress().evaluate("SCN-LATE-MARRIAGE", ecology())
    assert payload["coverage"]["unique_ordinary_actions"] >= 12
    contract = stress().contracts["SCN-LATE-MARRIAGE"]
    wedding = next(x for x in contract["probes"] if x["id"] == "L-P3")
    assert {"借锅", "称米", "挪床", "凑灯油"}.issubset(set(wedding["ordinary_actions"]))
    assert "LS-D08" in wedding["stress_dimensions"]


def test_multilayer_jade_requires_logistics_not_narrator_identity_explanation():
    contract = stress().contracts["SCN-JADE-MULTILAYER"]
    p2 = next(x for x in contract["probes"] if x["id"] == "J-P2")
    assert "不得由叙述者说‘此玉非彼玉’" == p2["anti_exposition_rule"]
    assert "TECH-15" in p2["technique_refs"]
    assert "LS-D04" in p2["stress_dimensions"]


def test_minimal_open_route_requires_concrete_procedure_not_vagueness():
    contract = stress().contracts["SCN-MINIMAL-CAUSE-OPEN"]
    p2 = next(x for x in contract["probes"] if x["id"] == "M-P2")
    assert "具体牵连事项" in p2["withheld_information"]
    assert {"等门", "递饭", "退药", "记问讯时辰"}.issubset(set(p2["ordinary_actions"]))
    assert "不得用‘其中缘故不可细说’逃避场景" == p2["anti_exposition_rule"]


def test_p4_compare_never_ranks_or_selects_winner():
    payload = stress().compare("SCN-CURRENT-C", "SCN-LATE-MARRIAGE", ecology())
    assert payload["ranking"] is None
    assert payload["winner"] is None
    assert payload["structural_differences"]


def test_p4_integrity_and_canonical_literary_state_unchanged():
    errors = stress().validate_integrity(
        ParetoEvaluationRuntime.from_repo(ROOT),
        HypothesisRuntime.from_repo(ROOT),
        ScenarioRuntime.from_repo(ROOT),
        CounterfactualReplayRuntime.from_repo(ROOT),
        WorldRuntime.from_repo(ROOT),
        ecology(),
    )
    assert errors == []
    literary = LiteraryProductionRuntime.from_repo(ROOT)
    assert literary.data["stable_active"]["sha256"] == STABLE_SHA
    assert literary.data["stable_active"]["changed"] is False
    assert literary.data["chapter89"]["plock_manual_review"] == "PENDING"
    assert literary.data["chapter89"]["blind_read"] == "PENDING"


def test_p4_project_state_is_pass_and_records_ci_gate():
    from rcwh.io import load_data

    state = load_data(ROOT / "data" / "project_state" / "scenario_literary_stress_v010.json")
    assert state["status"] == "PASS"
    assert state["authority"] == "SHADOW_ONLY"
    assert state["next_gate"] == "P5_NARRATIVE_DISCOURSE_RUNTIME"
    assert set(state["effects"].values()) == {"NONE"}
    assert state["ci"] == {
        "run_id": 37644227669,
        "conclusion": "SUCCESS",
        "pytest": "264 passed / 0 failed",
        "validate": "PASS",
    }
