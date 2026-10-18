"""Evidence-floor severities: only internal first-hand hard locks block."""
from pathlib import Path

import pytest

from rcwh.findings import (ADVISORY, BLOCKING, INFO, INPUT_MISSING, NEEDS_OWNER, NEEDS_REVIEWER,
                           NOT_IMPLEMENTED, WARNING, Finding, combine, gate_status,
                           severity_for_decision, strongest)
from rcwh.graph import ProvenanceGraph

ROOT = Path(__file__).resolve().parents[1]


def graph(source_type="EARLY_COMMENT", tier="W1_DIRECT", status="LOCKED", constraint="MUST",
          claim_status="SUPPORTED"):
    return ProvenanceGraph(
        sources={"s": {"id": "s", "type": source_type, "tier": tier}},
        claims={"c": {"id": "c", "status": claim_status, "support": [{"source": "s", "relation": "DIRECT"}]}},
        decisions={"d": {"id": "d", "status": status, "constraint": constraint, "based_on": ["c"]}},
        implementations={}, title_axes={})


@pytest.mark.parametrize("kwargs,expected", [
    ({}, BLOCKING),
    ({"source_type": "NOVEL_TEXT", "tier": "W1_SEEN", "constraint": "MUST_NOT"}, BLOCKING),
    ({"source_type": "HISTORICAL_PRIMARY", "tier": None}, WARNING),
    ({"source_type": "EARLY_TRANSCRIPT", "tier": "W2_TRANSCRIPT"}, WARNING),
    ({"claim_status": "CONTESTED"}, WARNING),
    ({"status": "CURRENT", "constraint": "MAY"}, ADVISORY),
    ({"status": "OPEN", "constraint": "OPEN"}, ADVISORY),
])
def test_decision_severity_follows_evidence_grade(kwargs, expected):
    assert severity_for_decision(graph(**kwargs), "d") == expected


def test_unknown_or_missing_decision_is_only_author_preference():
    assert severity_for_decision(graph(), None) == ADVISORY
    assert severity_for_decision(graph(), "absent") == ADVISORY
    assert severity_for_decision(None, "d") == ADVISORY


def test_only_blocking_findings_fail():
    soft = [Finding("CARD_BEAT_UNMET", ADVISORY, replaceable=True), Finding("B", WARNING), Finding("I", INFO)]
    assert gate_status(soft) == "PASS"
    assert gate_status(soft + [Finding("LOCK", BLOCKING)]) == "FAIL"
    assert gate_status([{"code": "x", "severity": "ADVISORY"}]) == "PASS"


def test_pending_reasons_by_scope():
    assert gate_status(pending=[NOT_IMPLEMENTED]) == "PASS"
    assert gate_status(pending=[INPUT_MISSING]) == "PENDING"
    assert gate_status(pending=[NEEDS_REVIEWER]) == "PENDING"
    assert gate_status(pending=[NEEDS_OWNER]) == "PASS"
    assert gate_status(pending=[NEEDS_OWNER], scope="stable") == "PENDING"
    assert gate_status([Finding("LOCK", BLOCKING)], [INPUT_MISSING]) == "FAIL"


def test_combine_and_strongest():
    assert combine(["PASS", "PASS"]) == "PASS"
    assert combine(["PASS", "PENDING"]) == "PENDING"
    assert combine(["PENDING", "FAIL"]) == "FAIL"
    assert combine([]) == "PENDING"
    assert strongest([ADVISORY, WARNING]) == WARNING
    assert strongest([]) == ADVISORY


def test_unknown_severity_rejected():
    with pytest.raises(ValueError):
        Finding("x", "FATAL")


def test_repository_locked_decisions_are_graded():
    g = ProvenanceGraph.from_repo(ROOT)
    locked = [d for d, v in g.decisions.items() if v.get("status") == "LOCKED"]
    grades = {severity_for_decision(g, d) for d in locked}
    assert locked and grades <= {BLOCKING, WARNING}
    assert all(severity_for_decision(g, d) == ADVISORY
               for d, v in g.decisions.items() if v.get("status") != "LOCKED")
