from pathlib import Path

from rcwh.graph import ProvenanceGraph
from rcwh.history import HistoricalMechanismRegistry
from rcwh.hypotheses import HypothesisRuntime
from rcwh.open_interfaces import OpenInterfaceRegistry


ROOT = Path(__file__).resolve().parents[1]


def runtime() -> HypothesisRuntime:
    return HypothesisRuntime.from_repo(ROOT)


def test_h04_phase0_alternatives_survive_p1_expansion():
    assert {
        "HYP-O09-A", "HYP-O09-B", "HYP-O09-C",
        "HYP-G0", "HYP-G1", "HYP-G2",
    }.issubset(runtime().hypotheses)
    assert all(x["status"] == "ADMISSIBLE" for x in runtime().hypotheses.values())


def test_hypotheses_are_downstream_only_and_do_not_close_open():
    graph = ProvenanceGraph.from_repo(ROOT)
    mechanisms = HistoricalMechanismRegistry.from_repo(ROOT)
    open_interfaces = OpenInterfaceRegistry.from_repo(ROOT)
    assert runtime().validate_integrity(graph, open_interfaces, mechanisms) == []
    for item in runtime().hypotheses.values():
        assert item["authority"] == "HYPOTHESIS_ONLY"
        assert item["evidence_effect"] == "NONE"
        assert item["stable_active_effect"] == "NONE"
        assert item["current_c_effect"] == "NONE"
        assert open_interfaces.interfaces[item["question_ref"]]["state"] == "OPEN_LOCKED"


def test_h04_source_fidelity_backfill_has_roles_housing_and_property_boundary():
    kinds = {x["kind"] for x in runtime().source_backfill["typed_backfills"]}
    assert kinds == {
        "MARRIAGE_ROLE_MODEL",
        "HOUSING_FEASIBILITY_MATRIX",
        "HISTORICAL_BOUNDARY",
    }
    role = next(x for x in runtime().source_backfill["typed_backfills"] if x["kind"] == "MARRIAGE_ROLE_MODEL")
    assert role["payload"]["roles"] == ["批准", "名义主婚", "出钱/出物", "实际操办"]
    housing = next(x for x in runtime().source_backfill["typed_backfills"] if x["kind"] == "HOUSING_FEASIBILITY_MATRIX")
    assert housing["payload"]["options"]


def test_h04_new_property_scope_backfill_is_search_only_and_does_not_mutate_r4_graph():
    graph = ProvenanceGraph.from_repo(ROOT)
    boundary = next(
        x for x in runtime().source_backfill["typed_backfills"]
        if x["kind"] == "HISTORICAL_BOUNDARY"
    )["payload"]
    source = boundary["source_candidate"]
    claim = boundary["claim_candidate"]
    assert source["type"] == "HISTORICAL_PRIMARY_REFERENCE"
    assert source["authority"] == "SEARCH_INPUT_ONLY"
    assert claim["authority_scope"] == "HISTORICAL_FEASIBILITY_SHADOW"
    assert claim["evidence_effect"] == "NONE"
    assert claim["id"] not in graph.claims
    assert source["id"] not in graph.sources
    assert boundary["promotion_policy"].startswith("DO_NOT_INSERT_INTO_FROZEN_R4_GRAPH")


def test_h04_audit_uses_canonical_source_sha_and_no_authority_effect():
    audit = runtime().fidelity_audit
    assert audit["source_document"]["sha256"] == "8786bbf96f258a201be9deb5baa8d2cd58b12f9082b30bda52a8f76437c15ee9"
    assert audit["authority"] == "SHADOW_ONLY"
    assert all(x["authority_effect"] == "NONE" for x in audit["entries"])


def test_phase0_does_not_mutate_stable_or_ch89_gate(production_unchanged):
    assert runtime().summary()["stable_active_effect"] == "NONE"




def test_v07_json_schemas_validate_new_data():
    from rcwh.io import load_data
    from rcwh.schema import validate_instance

    hypothesis_schema = load_data(ROOT / "schemas" / "hypothesis.schema.json")
    hypothesis_doc = load_data(ROOT / "data" / "hypotheses" / "h04_v07.json")
    for item in hypothesis_doc["hypotheses"]:
        assert validate_instance(item, hypothesis_schema) == []

    assert validate_instance(
        load_data(ROOT / "data" / "fidelity" / "audit_registry.json"),
        load_data(ROOT / "schemas" / "fidelity_audit.schema.json"),
    ) == []
    assert validate_instance(
        load_data(ROOT / "data" / "fidelity" / "hypothesis_source_backfill.json"),
        load_data(ROOT / "schemas" / "hypothesis_source_backfill.schema.json"),
    ) == []
