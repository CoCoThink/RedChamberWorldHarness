from copy import deepcopy
from pathlib import Path

from rcwh.graph import ProvenanceGraph
from rcwh.history import HistoricalMechanismRegistry


def root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_h01_h06_verdicts_are_exact():
    registry = HistoricalMechanismRegistry.from_repo(root())
    assert {k: v["verdict"] for k, v in registry.mechanisms.items()} == {
        "H01": "PASS-WITH-CAUTION",
        "H02": "PASS",
        "H03": "PASS-BOUNDARY",
        "H04": "PASS",
        "H05": "PASS",
        "H06": "PASS-SOFT",
    }


def test_historical_mechanisms_are_feasibility_only():
    graph = ProvenanceGraph.from_repo(root())
    registry = HistoricalMechanismRegistry.from_repo(root())
    assert registry.validate_integrity(graph) == []
    for mechanism in registry.mechanisms.values():
        assert mechanism["effect"] == "FEASIBILITY_ONLY"
        for claim_id in mechanism["claim_refs"]:
            assert graph.claims[claim_id]["authority_scope"] == "HISTORICAL_FEASIBILITY"


def test_historical_claim_cannot_silently_become_narrative_decision():
    graph = ProvenanceGraph.from_repo(root())
    broken = deepcopy(graph)
    broken.decisions["decision:test:history-to-plot"] = {
        "id": "decision:test:history-to-plot",
        "statement": "非法：因为史料允许所以小说必须这样写",
        "based_on": ["claim:history:h04:rental-mechanism"],
        "status": "LOCKED",
        "constraint": "MUST",
        "reversible": False,
    }
    errors = broken.validate_integrity()
    assert any("historical-feasibility" in e for e in errors)


def test_locked_historical_boundary_can_only_be_negative():
    graph = ProvenanceGraph.from_repo(root())
    broken = deepcopy(graph)
    broken.decisions["decision:test:positive-history-boundary"] = {
        "id": "decision:test:positive-history-boundary",
        "statement": "非法：历史可行性强迫正向剧情",
        "based_on": ["claim:history:h01:controlled-access"],
        "domain": "HISTORICAL_BOUNDARY",
        "status": "LOCKED",
        "constraint": "MUST",
        "reversible": False,
    }
    errors = broken.validate_integrity()
    assert any("never positive plot MUST" in e for e in errors)


def test_h06_is_secondary_soft_not_primary():
    graph = ProvenanceGraph.from_repo(root())
    registry = HistoricalMechanismRegistry.from_repo(root())
    h06 = registry.mechanisms["H06"]
    assert h06["evidence_basis"] == "SECONDARY_SOFT"
    source_types = registry._source_types_for_claims(graph, h06["claim_refs"])
    assert source_types == {"SECONDARY_RESEARCH"}


def test_h01_keeps_qianxue_access_controlled():
    registry = HistoricalMechanismRegistry.from_repo(root())
    h01 = registry.mechanisms["H01"]
    assert any("旧仆" in item and "探监权" in item for item in h01["rejects"])
    assert "impl:active:ch92:historical-detention-access" in h01["implementation_refs"]


def test_h03_exact_mourning_duration_stays_open():
    h03 = HistoricalMechanismRegistry.from_repo(root()).mechanisms["H03"]
    text = " ".join(h03["open"] + h03["cannot_prove"])
    assert "27" in text
    assert "100" in text
    assert "9个月" in text


def test_h04_h05_specific_numbers_do_not_harden():
    registry = HistoricalMechanismRegistry.from_repo(root())
    h04 = " ".join(registry.mechanisms["H04"]["open"] + registry.mechanisms["H04"]["cannot_prove"])
    h05 = " ".join(registry.mechanisms["H05"]["open"] + registry.mechanisms["H05"]["cannot_prove"])
    assert "租金" in h04 or "赁钱" in h04
    assert "两碗半" in h05
