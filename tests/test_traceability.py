from pathlib import Path

from rcwh.graph import ProvenanceGraph


def root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_provenance_graph_integrity():
    graph = ProvenanceGraph.from_repo(root())
    assert graph.validate_integrity() == []


def test_locked_decisions_are_fully_source_backed():
    graph = ProvenanceGraph.from_repo(root())
    locked = [d for d in graph.decisions.values() if d["status"] == "LOCKED"]
    assert locked
    for decision in locked:
        trace = graph.trace(decision["id"])
        assert trace["fully_source_backed"] is True
        assert trace["sources"]
        assert trace["permission"] in {"MUST", "MUST_NOT"}


def test_cliff_release_trace_distinguishes_placement_from_evidence():
    graph = ProvenanceGraph.from_repo(root())

    hard = graph.trace("decision:cliff-release:function")
    placement = graph.trace("decision:cliff-release:placement")

    assert hard["fully_source_backed"] is True
    assert hard["permission"] == "MUST"

    assert placement["fully_source_backed"] is False
    assert placement["permission"] == "MAY"
    assert any(c["id"] == "claim:cliff-release:chapter-99" for c in placement["claims"])


def test_implementation_traces_back_to_sources():
    graph = ProvenanceGraph.from_repo(root())
    trace = graph.trace("impl:active:ch98:zhen-jade")
    assert trace["decisions"]
    assert any(c["id"] == "claim:zhen-sends-jade:event" for c in trace["claims"])
    assert any(s["id"] == "src:jimao:ch18:zhen-baoyu-sends-jade" for s in trace["sources"])
