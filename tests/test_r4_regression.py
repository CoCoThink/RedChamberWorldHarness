from copy import deepcopy
from pathlib import Path

from rcwh.graph import ProvenanceGraph
from rcwh.regression import run_r4_evidence_regression


def root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_full_r4_evidence_core_regression_passes():
    result = run_r4_evidence_regression(root())
    assert result["overall"] == "PASS"
    assert all(gate["status"] == "PASS" for gate in result["gates"])


def test_stable_active_sha_is_release_locked():
    result = run_r4_evidence_regression(root())
    assert result["stable_active"]["sha256"] == (
        "4645da79b1bed76f54be281c50b5df648f599ea41541fb7855685753b6a85320"
    )


def test_completion_hard_anchors_are_first_class_provenance_nodes():
    graph = ProvenanceGraph.from_repo(root())
    for decision_id in [
        "decision:daiyu:death-direction",
        "decision:prison:baoyu-interface",
        "decision:xiaohong:great-help",
        "decision:qianxue:prison-return",
    ]:
        assert graph.decisions[decision_id]["status"] == "LOCKED"
        assert graph.decision_fully_source_backed(decision_id) is True
        assert graph.decision_lock_eligible(decision_id) is True


def test_regression_detects_reverse_promotion():
    graph = ProvenanceGraph.from_repo(root())
    broken = deepcopy(graph)
    decision = broken.decisions["decision:qingbang:formal-title"]
    decision["status"] = "LOCKED"
    decision["constraint"] = "MUST"
    decision["reversible"] = False
    assert broken.validate_integrity() != []
