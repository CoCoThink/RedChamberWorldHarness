from copy import deepcopy
from pathlib import Path

from rcwh.graph import ProvenanceGraph
from rcwh.history import HistoricalMechanismRegistry
from rcwh.literals import LiteralRegistry
from rcwh.open_interfaces import OpenInterfaceRegistry


def root() -> Path:
    return Path(__file__).resolve().parents[1]


def registries():
    graph = ProvenanceGraph.from_repo(root())
    literals = LiteralRegistry.from_repo(root())
    mechanisms = HistoricalMechanismRegistry.from_repo(root())
    opens = OpenInterfaceRegistry.from_repo(root())
    return graph, literals, mechanisms, opens


def test_open_interfaces_preserve_uncertainty_and_referential_integrity():
    graph, literals, mechanisms, opens = registries()
    assert opens.interfaces
    assert all(x["state"] == "OPEN_LOCKED" for x in opens.interfaces.values())
    assert opens.validate_integrity(graph, literals, mechanisms) == []


def test_open_locked_is_not_pending_or_unreviewed():
    _, _, _, opens = registries()
    for item in opens.interfaces.values():
        assert item["state"] == "OPEN_LOCKED"
        assert item["uncertainty"]
        assert item["forbidden_hardening"]
        assert item["reopen_triggers"]


def test_current_decisions_remain_current_may():
    graph, _, _, opens = registries()
    for item in opens.interfaces.values():
        for decision_id in item.get("current_decision_refs", []):
            decision = graph.decisions[decision_id]
            assert decision["status"] == "CURRENT"
            assert decision["constraint"] == "MAY"


def test_open_decisions_remain_open_open():
    graph, _, _, opens = registries()
    for item in opens.interfaces.values():
        for decision_id in item.get("open_decision_refs", []):
            decision = graph.decisions[decision_id]
            assert decision["status"] == "OPEN"
            assert decision["constraint"] == "OPEN"


def test_open_registry_detects_hardening_of_current_choice():
    graph, literals, mechanisms, opens = registries()
    broken_graph = deepcopy(graph)
    decision_id = "decision:zhen-sends-jade:meeting"
    broken_graph.decisions[decision_id]["status"] = "LOCKED"
    broken_graph.decisions[decision_id]["constraint"] = "MUST"
    broken_graph.decisions[decision_id]["reversible"] = False
    errors = opens.validate_integrity(broken_graph, literals, mechanisms)
    assert any("CURRENT/MAY" in e for e in errors)


def test_ol011_keeps_jade_identity_open():
    graph, _, _, opens = registries()
    item = opens.interfaces["OL-011"]
    assert "decision:fengjie-snow-jade:jade-identity" in item["open_decision_refs"]
    assert graph.decisions["decision:fengjie-snow-jade:jade-identity"]["status"] == "OPEN"


def test_ol024_keeps_qingbang_formal_title_open():
    graph, _, _, opens = registries()
    item = opens.interfaces["OL-024"]
    assert "decision:qingbang:formal-title" in item["open_decision_refs"]
    assert graph.decisions["decision:qingbang:formal-title"]["constraint"] == "OPEN"


def test_ol018_does_not_implement_guazhou_w2_chain():
    _, _, _, opens = registries()
    item = opens.interfaces["OL-018"]
    text = " ".join(item["forbidden_hardening"])
    assert "W2" in text
    assert "完整悲剧机制" in text


def test_ol028_protects_all_pc_and_tg_from_reverse_promotion():
    _, _, _, opens = registries()
    item = opens.interfaces["OL-028"]
    text = " ".join(item["forbidden_hardening"])
    assert "81—100" in text
    assert "TG" in text
