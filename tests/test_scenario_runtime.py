from pathlib import Path

from rcwh.graph import ProvenanceGraph
from rcwh.history import HistoricalMechanismRegistry
from rcwh.hypotheses import HypothesisRuntime
from rcwh.open_interfaces import OpenInterfaceRegistry
from rcwh.scenarios import ScenarioRuntime

ROOT = Path(__file__).resolve().parents[1]

CORE_OPEN = {
    "OL-005", "OL-007", "OL-009", "OL-012", "OL-014",
    "OL-011", "OL-018", "OL-020", "OL-021", "OL-023",
}


def hypotheses() -> HypothesisRuntime:
    return HypothesisRuntime.from_repo(ROOT)


def scenarios() -> ScenarioRuntime:
    return ScenarioRuntime.from_repo(ROOT)


def test_p1_has_two_or_more_alternatives_for_ten_core_open_interfaces():
    coverage = hypotheses().alternative_coverage()
    assert CORE_OPEN.issubset(coverage)
    assert all(coverage[x] >= 2 for x in CORE_OPEN)


def test_p1_has_at_least_eight_admissible_scenario_bundles():
    items = [x for x in scenarios().scenarios.values() if x["status"] == "ADMISSIBLE"]
    assert len(items) >= 8


def test_current_c_is_only_a_reference_and_gets_no_bonus():
    current = [
        x for x in scenarios().scenarios.values()
        if x["current_c_relation"] == "CURRENT_C_REFERENCE"
    ]
    assert len(current) == 1
    policy = current[0]["search_policy"]
    assert policy == {
        "search_priority": "NONE",
        "evidence_bonus": "NONE",
        "baseline_convenience_bonus": "NONE",
    }


def test_scenario_runtime_preserves_open_and_rejects_internal_exclusivity():
    opens = OpenInterfaceRegistry.from_repo(ROOT)
    assert scenarios().validate_integrity(hypotheses(), opens) == []
    for scenario in scenarios().scenarios.values():
        qrefs = [hypotheses().hypotheses[x]["question_ref"] for x in scenario["hypotheses"]]
        assert len(qrefs) == len(set(qrefs))
        assert scenario["open_interfaces"]["closed_by_scenario"] == []


def test_p1_hypothesis_runtime_resolves_reconstruction_refs_when_given_registry():
    from rcwh.reconstruction import ReconstructionRegistry
    runtime = hypotheses()
    errors = runtime.validate_integrity(
        ProvenanceGraph.from_repo(ROOT),
        OpenInterfaceRegistry.from_repo(ROOT),
        HistoricalMechanismRegistry.from_repo(ROOT),
        ReconstructionRegistry.from_repo(ROOT),
    )
    assert errors == []


def test_scenario_frontier_has_no_single_total_score_before_replay():
    payload = scenarios().frontier()
    assert payload["status"] == "NOT_RANKED_BEFORE_P2_REPLAY"
    assert payload["single_total_score"] is False


def test_scenario_compare_is_structural_not_ranked():
    payload = scenarios().compare(
        ["SCN-CURRENT-C", "SCN-JADE-MULTILAYER"], hypotheses()
    )
    assert payload["ranking"] is None
    assert payload["differences"]


def test_p1_summary_reports_shadow_only_and_replay_pending():
    payload = scenarios().summary(hypotheses())
    assert payload["status"] == "SHADOW_ONLY"
    assert payload["core_open_with_two_or_more_alternatives"] >= 10
    assert payload["world_replay"] == "PENDING_P2"
    assert payload["automatic_winner"] is False
