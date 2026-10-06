from copy import deepcopy
from pathlib import Path

from rcwh.graph import ProvenanceGraph


def root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_locked_decision_cannot_hide_an_unestablished_basis():
    graph = ProvenanceGraph.from_repo(root())
    broken = deepcopy(graph)
    decision = broken.decisions["decision:cliff-release:function"]
    decision["based_on"].append("claim:cliff-release:chapter-99")
    errors = broken.validate_integrity()
    assert any("non-supported basis" in e for e in errors)


def test_status_and_constraint_are_separate():
    graph = ProvenanceGraph.from_repo(root())
    assert graph.decisions["decision:cliff-release:function"]["constraint"] == "MUST"
    assert graph.decisions["decision:cliff-release:placement"]["constraint"] == "MAY"
    assert graph.decisions["decision:cliff-release:formal-title"]["constraint"] == "OPEN"


def test_no_duplicate_source_fingerprint():
    graph = ProvenanceGraph.from_repo(root())
    assert not any("duplicate source" in e for e in graph.validate_integrity())
