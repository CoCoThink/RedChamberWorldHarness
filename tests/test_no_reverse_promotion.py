from pathlib import Path

from rcwh.graph import ProvenanceGraph


def root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_open_never_compiles_to_must():
    graph = ProvenanceGraph.from_repo(root())
    for decision in graph.decisions.values():
        if decision["status"] == "OPEN":
            assert graph.permission(decision["id"]) == "OPEN"
            assert graph.decision_fully_source_backed(decision["id"]) is False


def test_current_is_not_reported_as_fully_source_backed_when_basis_is_mixed():
    graph = ProvenanceGraph.from_repo(root())
    mixed_current = [
        "decision:cliff-release:placement",
        "decision:zhen-sends-jade:same-jade",
        "decision:zhen-sends-jade:meeting",
        "decision:zhen-sends-jade:placement",
        "decision:fengjie-snow-jade:placement",
        "decision:ten-solitary-chants:placement",
        "decision:qingbang:current-format",
    ]
    for decision_id in mixed_current:
        assert graph.permission(decision_id) == "MAY"
        assert graph.decision_fully_source_backed(decision_id) is False


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
