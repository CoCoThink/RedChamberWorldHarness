from copy import deepcopy
from pathlib import Path

from rcwh.graph import ProvenanceGraph


def root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_all_jingcang_transcripts_are_w2():
    graph = ProvenanceGraph.from_repo(root())
    sources = [s for s in graph.sources.values() if s["type"] == "EARLY_TRANSCRIPT"]
    assert sources
    for source in sources:
        assert source["tier"] == "W2_TRANSCRIPT"


def test_w2_only_claims_use_transcript_weak_modality():
    graph = ProvenanceGraph.from_repo(root())
    w2_claims = [c for c in graph.claims.values() if graph.claim_is_w2_only(c["id"])]
    assert w2_claims
    for claim in w2_claims:
        assert claim["modality"] == "TRANSCRIPT_WEAK"


def test_w2_only_claim_cannot_bear_locked_decision():
    graph = ProvenanceGraph.from_repo(root())
    broken = deepcopy(graph)
    broken.decisions["decision:test:w2-hardening"] = {
        "id": "decision:test:w2-hardening",
        "statement": "非法：把W2单独升级为硬约束",
        "based_on": ["claim:w2:miaoyu-guazhou:transcript"],
        "status": "LOCKED",
        "constraint": "MUST",
        "reversible": False,
    }
    errors = broken.validate_integrity()
    assert any("W2-only" in e for e in errors)


def test_qingbang_locked_structure_does_not_depend_on_w2():
    graph = ProvenanceGraph.from_repo(root())
    hard = graph.decisions["decision:qingbang:final-structure"]
    assert hard["status"] == "LOCKED"
    assert graph.decision_lock_eligible(hard["id"]) is True
    assert "claim:w2:qingbang-confirmation:transcript" not in hard["based_on"]


def test_zheng_qianyuan_is_t2_w2_and_open():
    graph = ProvenanceGraph.from_repo(root())
    axis = graph.title_axes["axis:t2w2:zheng-qianyuan"]
    assert axis["class"] == "T2_W2"
    claim_id = axis["claim_refs"][0]
    assert graph.claim_is_w2_only(claim_id) is True
    decision = graph.decisions[axis["formal_title_decision_ref"]]
    assert decision["status"] == "OPEN"
    assert decision["constraint"] == "OPEN"


def test_guazhou_remains_open_and_unimplemented():
    graph = ProvenanceGraph.from_repo(root())
    decision = graph.decisions["decision:w2:miaoyu-guazhou"]
    assert decision["status"] == "OPEN"
    assert decision.get("implementation_refs", []) == []
