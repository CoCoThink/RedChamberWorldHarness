from pathlib import Path

from rcwh.graph import ProvenanceGraph


def root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_provenance_graph_integrity():
    graph = ProvenanceGraph.from_repo(root())
    assert graph.validate_integrity() == []


def test_locked_decisions_trace_to_sources():
    graph = ProvenanceGraph.from_repo(root())
    locked = [d for d in graph.decisions.values() if d["status"] == "LOCKED"]
    assert locked
    for decision in locked:
        trace = graph.trace(decision["id"])
        assert trace["evidence_proven"] is True
        assert trace["sources"]


def test_cliff_release_trace_distinguishes_placement_from_evidence():
    graph = ProvenanceGraph.from_repo(root())

    hard = graph.trace("decision:cliff-release:function")
    placement = graph.trace("decision:cliff-release:placement")

    assert hard["evidence_proven"] is True
    assert hard["permission"] == "MUST"

    assert placement["evidence_proven"] is False
    assert placement["permission"] == "MAY"
    assert any(c["id"] == "claim:cliff-release:chapter-99" for c in placement["claims"])
