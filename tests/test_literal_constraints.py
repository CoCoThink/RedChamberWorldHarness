from copy import deepcopy
from pathlib import Path

from rcwh.graph import ProvenanceGraph
from rcwh.literals import LiteralRegistry


def root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_literal_registry_integrity():
    graph = ProvenanceGraph.from_repo(root())
    literals = LiteralRegistry.from_repo(root())
    assert literals.validate_integrity(graph) == []


def test_novel_exact_literals_have_active_implementations():
    graph = ProvenanceGraph.from_repo(root())
    literals = LiteralRegistry.from_repo(root())
    for item in literals.constraints.values():
        if "NOVEL_EXACT" in item["targets"]:
            assert item["required_in_active_prose"] is True
            assert item["implementation_refs"]
            for impl_id in item["implementation_refs"]:
                assert impl_id in graph.implementations


def test_ten_solitary_chants_name_and_boundary_are_distinct():
    graph = ProvenanceGraph.from_repo(root())
    literals = LiteralRegistry.from_repo(root())
    item = literals.constraints["literal:ten-solitary-chants:name"]
    assert set(item["targets"]) == {"NAME_EXACT", "BOUNDARY"}
    assert item["boundary"]["claim_ref"] == "claim:ten-solitary-chants:after-ch64"
    assert graph.decisions["decision:ten-solitary-chants:placement"]["status"] == "CURRENT"


def test_keep_sheyue_requires_post_marriage_boundary():
    graph = ProvenanceGraph.from_repo(root())
    literals = LiteralRegistry.from_repo(root())
    item = literals.constraints["literal:sheyue:keep-sheyue"]
    assert "NOVEL_EXACT" in item["targets"]
    assert "BOUNDARY" in item["targets"]
    assert "袭人出嫁之后" in item["boundary"]["description"]
    assert graph.decisions["decision:sheyue-speech:boundary"]["constraint"] == "MUST"


def test_qingbang_source_exact_does_not_force_prose_title():
    graph = ProvenanceGraph.from_repo(root())
    literals = LiteralRegistry.from_repo(root())
    item = literals.constraints["literal:qingbang:source-phrase"]
    assert item["targets"] == ["SOURCE_EXACT"]
    assert item["required_in_active_prose"] is False
    assert item["implementation_refs"] == []
    assert graph.decisions["decision:qingbang:formal-title"]["status"] == "OPEN"


def test_source_exact_cannot_be_silently_promoted_to_required_prose():
    graph = ProvenanceGraph.from_repo(root())
    literals = LiteralRegistry.from_repo(root())
    broken = deepcopy(literals)
    broken.constraints["literal:qingbang:source-phrase"]["required_in_active_prose"] = True
    errors = broken.validate_integrity(graph)
    assert any("SOURCE_EXACT alone" in e for e in errors)
