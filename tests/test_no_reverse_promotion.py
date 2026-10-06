from pathlib import Path

from rcwh.graph import ProvenanceGraph


def root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_open_never_compiles_to_must():
    graph = ProvenanceGraph.from_repo(root())
    for decision in graph.decisions.values():
        if decision["status"] == "OPEN":
            assert graph.permission(decision["id"]) != "MUST"
            assert graph.evidence_proven(decision["id"]) is False


def test_current_is_not_reported_as_evidence_proven():
    graph = ProvenanceGraph.from_repo(root())
    for decision in graph.decisions.values():
        if decision["status"] == "CURRENT":
            assert graph.permission(decision["id"]) == "MAY"
            assert graph.evidence_proven(decision["id"]) is False


def test_qingbang_source_phrase_does_not_lock_formal_title():
    graph = ProvenanceGraph.from_repo(root())
    source_phrase = graph.claims["claim:qingbang:source-phrase-jinghuan-qingbang"]
    formal_title = graph.decisions["decision:qingbang:formal-title"]

    assert source_phrase["status"] == "SUPPORTED"
    assert formal_title["status"] == "OPEN"
    assert graph.permission(formal_title["id"]) == "OPEN"


def test_ten_solitary_chants_open_attributes_remain_open():
    graph = ProvenanceGraph.from_repo(root())
    for decision_id in [
        "decision:ten-solitary-chants:author",
        "decision:ten-solitary-chants:form",
        "decision:ten-solitary-chants:count",
        "decision:ten-solitary-chants:subjects",
    ]:
        assert graph.decisions[decision_id]["status"] == "OPEN"
        assert graph.permission(decision_id) == "OPEN"
