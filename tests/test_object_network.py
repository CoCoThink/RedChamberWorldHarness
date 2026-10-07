from pathlib import Path

from rcwh.object_network import ObjectNetworkRuntime
from rcwh.reconstruction import ReconstructionRegistry
from rcwh.registry import MigrationRegistry


ROOT = Path(__file__).resolve().parents[1]


def objects() -> ObjectNetworkRuntime:
    return ObjectNetworkRuntime.from_repo(ROOT)


def test_m4_object_network_cardinality_and_query_surface():
    summary = objects().summary()
    assert summary["objects"] == 17
    assert summary["transitions"] == 29
    assert summary["identity_edges"] == 1
    assert summary["containment_edges"] == 2
    assert summary["completion"]["object_queryable"] is True
    assert summary["completion"]["transition_replay"] is True
    assert summary["completion"]["completion_gate_ready"] is False


def test_tongling_jade_has_continuous_current_c_route_until_sashou_boundary():
    runtime = objects()
    assert runtime.snapshot("OBJ-TONGLING-JADE", 80)["state"]["location"] == "S02"
    assert runtime.snapshot("OBJ-TONGLING-JADE", 89)["state"]["location"] == "S06"
    assert runtime.snapshot("OBJ-TONGLING-JADE", 95)["state"]["location"] == "S09"
    ch98 = runtime.snapshot("OBJ-TONGLING-JADE", 98)["state"]
    assert ch98["holder"] == "baoyu"
    assert ch98["location"] == "S09"
    assert ch98["status"] == "RETURNED"
    ch99 = runtime.snapshot("OBJ-TONGLING-JADE", 99)["state"]
    assert ch99["holder"] == "UNKNOWN"
    assert ch99["location"] == "UNKNOWN"
    assert ch99["status"] == "EARTHLY_ROUTE_OPEN_AFTER_SA_SHOU"


def test_chapter91_snow_jade_never_auto_merges_with_tongling_jade():
    runtime = objects()
    snow = runtime.snapshot("OBJ-SNOW-JADE-91", 91)
    tongling = runtime.snapshot("OBJ-TONGLING-JADE", 91)
    assert snow["object"]["identity_status"] == "OPEN_MAY_OR_MAY_NOT_BE_TONGLING"
    assert snow["state"]["location"] == "S05"
    assert tongling["state"]["location"] == "S06"
    edge = runtime.identity_edges[0]
    assert edge["relation"] == "MAY_BE_SAME_AS"
    assert edge["status"] == "OPEN_LOCKED_NONMERGE"


def test_terminal_stone_frame_state_does_not_fabricate_earthly_transport():
    runtime = objects()
    state = runtime.snapshot("OBJ-TONGLING-JADE", 100)["state"]
    assert state["location"] == "UNKNOWN"
    assert state["holder"] == "UNKNOWN"
    assert state["frame_status"] == "RETURNED_TO_ESSENCE_QINGGENG_FRAME"


def test_detention_delivery_package_has_explicit_route_into_s07():
    runtime = objects()
    before = runtime.snapshot("OBJ-DETENTION-DELIVERY-PACKAGE", 91)["state"]
    assert before["status"] == "NOT_ASSEMBLED"
    delivered = runtime.snapshot("OBJ-DETENTION-DELIVERY-PACKAGE", 92)["state"]
    assert delivered["holder"] == "baoyu"
    assert delivered["location"] == "S07"
    assert delivered["status"] == "DELIVERED_UNDER_RULES"


def test_resource_objects_preserve_non_restorative_aid():
    runtime = objects()
    rice95 = runtime.snapshot("OBJ-RICE-JAR-95", 95)["state"]
    rice96 = runtime.snapshot("OBJ-RICE-JAR-95", 96)["state"]
    coal96 = runtime.snapshot("OBJ-CHARCOAL-BASKET-95", 96)["state"]
    assert rice95["quantity_state"] == "LOW"
    assert rice96["quantity_state"] == "MEASURED_USE_HALF_AID"
    assert coal96["quantity_state"] == "PARTIALLY_REPLENISHED"


def test_medicine_bowl_bridge_retains_cold_medicine_continuity():
    runtime = objects()
    assert runtime.snapshot("OBJ-MEDICINE-BOWL-86", 85)["state"]["temperature"] == "warm"
    assert runtime.snapshot("OBJ-MEDICINE-BOWL-86", 86)["state"]["temperature"] == "cold"
    assert runtime.objects["OBJ-MEDICINE-BOWL-86"]["legacy_ref"] == "data/objects/medicine_bowl.yaml"


def test_every_location_change_is_explicit_or_open_boundary():
    report = objects().continuity_report()
    assert report["status"] == "PASS"
    assert report["findings"] == []
    assert report["transitions_checked"] == 29


def test_object_sources_are_registered_or_reconstruction_nodes():
    registry = MigrationRegistry.from_repo(ROOT)
    reconstruction = ReconstructionRegistry.from_repo(ROOT)
    r_ids = {item["id"] for item in reconstruction.data["r_nodes"]}
    for item in objects().objects.values():
        for ref in item["source_refs"]:
            if ref.startswith("doc:"):
                assert ref in registry.documents
            elif ref.startswith("R"):
                assert ref in r_ids
            else:
                raise AssertionError(f"unsupported source ref {ref}")


def test_m4_integrity_passes_and_registry_keeps_completion_gate_closed():
    registry = MigrationRegistry.from_repo(ROOT)
    reconstruction = ReconstructionRegistry.from_repo(ROOT)
    assert objects().validate_integrity(ROOT, registry, reconstruction) == []
    current = registry.current_summary()
    assert current["object_queryable"] is True
    assert current["current_markdown_islands"] == 0
    assert current["completion_gate_ready"] is False


def test_object_trace_resolves_document_and_reconstruction_sources():
    registry = MigrationRegistry.from_repo(ROOT)
    reconstruction = ReconstructionRegistry.from_repo(ROOT)
    payload = objects().trace("OBJ-TONGLING-JADE", registry, reconstruction)
    assert payload["trace_complete"] is True
    kinds = {item["kind"] for item in payload["resolved_sources"]}
    assert kinds == {"document", "reconstruction_evidence"}
    assert any(
        item["ref"] == "doc:2b5f2bcae5ce" and item["sha256"].startswith("2b5f2bcae5ce")
        for item in payload["resolved_sources"]
        if item["kind"] == "document"
    )
    assert any(
        item["ref"] == "R01" and "终点" in item["boundary"]
        for item in payload["resolved_sources"]
        if item["kind"] == "reconstruction_evidence"
    )
