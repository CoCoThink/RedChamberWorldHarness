from pathlib import Path

from rcwh.graph import ProvenanceGraph


def root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_t_axis_core_classes_are_machine_distinct():
    graph = ProvenanceGraph.from_repo(root())
    assert graph.title_axes["axis:t0:baochai-fengjie"]["class"] == "T0"
    assert graph.title_axes["axis:t1:xiren"]["class"] == "T1"
    assert graph.title_axes["axis:t2:prison-comfort"]["class"] == "T2"
    assert graph.title_axes["axis:t3:fengjie-snow-jade"]["class"] == "T3"
    assert graph.title_axes["axis:tg:ch92"]["class"] == "TG"


def test_t3_cannot_be_hard_promoted_to_formal_title():
    graph = ProvenanceGraph.from_repo(root())
    for axis in graph.title_axes.values():
        if axis["class"] != "T3":
            continue
        decision_id = axis.get("formal_title_decision_ref")
        if not decision_id:
            continue
        assert graph.decisions[decision_id]["constraint"] == "OPEN"


def test_tg_has_no_evidence_authority():
    graph = ProvenanceGraph.from_repo(root())
    for axis in graph.title_axes.values():
        if axis["class"] == "TG":
            assert axis["generated"] is True
            assert axis["claim_refs"] == []


def test_t0_wording_is_hard_but_chapter_number_is_not():
    graph = ProvenanceGraph.from_repo(root())
    wording = graph.decisions["decision:future-title:baochai-fengjie:wording"]
    placement = graph.decisions["decision:future-title:baochai-fengjie:placement"]
    assert wording["status"] == "LOCKED"
    assert wording["constraint"] == "MUST"
    assert graph.decision_fully_source_backed(wording["id"]) is True
    assert placement["status"] == "CURRENT"
    assert placement["constraint"] == "MAY"
    assert graph.decision_fully_source_backed(placement["id"]) is False


def test_t1_locks_only_known_heading_part():
    graph = ProvenanceGraph.from_repo(root())
    assert graph.decisions["decision:xiren:heading-part"]["constraint"] == "MUST"
    assert graph.decisions["decision:xiren:full-heading"]["constraint"] == "OPEN"


def test_title_axis_trace_reaches_source_and_implementation():
    graph = ProvenanceGraph.from_repo(root())
    trace = graph.trace("axis:t2:prison-comfort")
    assert trace["claims"]
    assert any(s["id"] == "src:gengchen:ch20:xiren-prison-drafts" for s in trace["sources"])
    assert any(i["id"] == "impl:active:ch92:title" for i in trace["implementations"])
