from pathlib import Path

from rcwh.object_network import ObjectNetworkRuntime
from rcwh.reconstruction import ReconstructionRegistry
from rcwh.assets import AssetCatalog
from rcwh.workflow import ProjectState


ROOT = Path(__file__).resolve().parents[1]


def objects() -> ObjectNetworkRuntime:
    return ObjectNetworkRuntime.from_repo(ROOT)


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
    assert report["transitions_checked"] == len(objects().transitions)


def test_object_sources_are_registered_or_reconstruction_nodes():
    registry = AssetCatalog.from_repo(ROOT)
    reconstruction = ReconstructionRegistry.from_repo(ROOT)
    r_ids = {item["id"] for item in reconstruction.data["r_nodes"]}
    for item in objects().objects.values():
        for ref in item["source_refs"]:
            if ref.startswith("asset:"):
                assert ref in registry.assets
            elif ref.startswith("R"):
                assert ref in r_ids
            else:
                raise AssertionError(f"unsupported source ref {ref}")


def test_object_integrity_passes_against_local_assets():
    registry = AssetCatalog.from_repo(ROOT)
    reconstruction = ReconstructionRegistry.from_repo(ROOT)
    assert objects().validate_integrity(ROOT, registry, reconstruction) == []


def test_object_trace_resolves_document_and_reconstruction_sources():
    registry = AssetCatalog.from_repo(ROOT)
    reconstruction = ReconstructionRegistry.from_repo(ROOT)
    payload = objects().trace("OBJ-TONGLING-JADE", registry, reconstruction)
    assert payload["trace_complete"] is True
    kinds = {item["kind"] for item in payload["resolved_sources"]}
    assert kinds == {"asset", "reconstruction_evidence"}
    assert any(
        item["ref"] == "asset:sha256:2b5f2bcae5ce0269b0f33f4d89cad32c03d5ad77b388232da28e6fa446f5ed9d" and item["sha256"].startswith("2b5f2bcae5ce")
        for item in payload["resolved_sources"]
        if item["kind"] == "asset"
    )
    assert any(
        item["ref"] == "R01" and "终点" in item["boundary"]
        for item in payload["resolved_sources"]
        if item["kind"] == "reconstruction_evidence"
    )


def _scoped_repository(tmp_path, *, chapters=None, baseline=80, transitions=()):
    import json
    from copy import deepcopy

    data = deepcopy(objects().data)
    data["baseline_chapter"] = baseline
    data["transitions"].extend(transitions)
    scope = json.loads((ROOT / "data/project/scope.json").read_text())
    if chapters is not None:
        scope["chapters"] = chapters
    for relative, value in [("data/objects/m4.json", data), ("data/project/scope.json", scope)]:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(value), encoding="utf-8")
    (tmp_path / "schemas").mkdir(exist_ok=True)
    (tmp_path / "schemas/project_scope.schema.json").write_bytes((ROOT / "schemas/project_scope.schema.json").read_bytes())
    return tmp_path


def test_configured_extension_accepts_real_transition_and_cli_defaults_to_last_chapter(tmp_path, monkeypatch, capsys):
    import json
    from copy import deepcopy
    import pytest
    from rcwh.cli import main
    from rcwh.schema import validate_instance

    runtime = objects()
    identity = "OBJ-MEDICINE-BOWL-86"
    state = runtime.snapshot(identity)["state"]
    extension = deepcopy(runtime.by_object[identity][-1])
    extension.update(id="OT-EXTENSION", chapter=101, sequence=0, movement="NONE")
    extension["from"] = deepcopy(state)
    extension["to"] = {**state, "status": "TEST_EXTENSION_OBSERVED"}
    repo = _scoped_repository(tmp_path, chapters=[*runtime.chapter_scope, 101], transitions=[extension])
    selected = ObjectNetworkRuntime.from_repo(repo)
    assert validate_instance(selected.data, ROOT / "schemas/object_network.schema.json") == []
    assert selected.validate_integrity(ROOT, AssetCatalog.from_repo(ROOT), ReconstructionRegistry.from_repo(ROOT)) == []
    assert selected.snapshot(identity)["state"]["status"] == "TEST_EXTENSION_OBSERVED"
    for query in [("get", identity), ("jade",)]:
        monkeypatch.setattr("sys.argv", ["rcwh", "--root", str(repo), "object", *query, "--json"])
        with pytest.raises(SystemExit) as result:
            main()
        assert result.value.code == 0
        assert json.loads(capsys.readouterr().out)["chapter"] == 101


def test_queries_reject_scope_holes_and_use_explicit_baseline(tmp_path):
    import pytest

    scope = [chapter for chapter in objects().chapter_scope if chapter != 90]
    runtime = ObjectNetworkRuntime.from_repo(_scoped_repository(tmp_path, chapters=scope, baseline=75))
    assert runtime.snapshot("OBJ-TONGLING-JADE", 75)["applied_transitions"] == []
    for chapter in [74, 80, 90, 101]:
        for query in (lambda: runtime.snapshot("OBJ-TONGLING-JADE", chapter),
                      lambda: runtime.jade(chapter), lambda: runtime.at_location("S02", chapter)):
            with pytest.raises(KeyError, match="outside configured object scope"):
                query()


def test_transition_in_undeclared_chapter_fails_validation(tmp_path):
    from copy import deepcopy

    runtime = objects()
    transition = deepcopy(runtime.transitions[0])
    transition.update(id="OT-OUTSIDE-SCOPE", chapter=101)
    selected = ObjectNetworkRuntime.from_repo(_scoped_repository(tmp_path, transitions=[transition]))
    errors = selected.validate_integrity(ROOT, AssetCatalog.from_repo(ROOT), ReconstructionRegistry.from_repo(ROOT))
    assert any("OT-OUTSIDE-SCOPE: chapter 101 outside configured object scope" in error for error in errors)


def test_missing_protected_checkpoint_is_a_failure_not_a_skipped_check(tmp_path):
    selected = ObjectNetworkRuntime.from_repo(_scoped_repository(tmp_path, chapters=list(range(81, 100))))
    errors = selected.validate_integrity(ROOT, AssetCatalog.from_repo(ROOT), ReconstructionRegistry.from_repo(ROOT))
    assert any("protected object checkpoint unavailable" in error for error in errors)


def test_invalid_object_baseline_cannot_be_loaded(tmp_path):
    import pytest

    for baseline in [None, True, -1, 81, 100]:
        repo = _scoped_repository(tmp_path, baseline=baseline)
        with pytest.raises(ValueError, match="baseline_chapter"):
            ObjectNetworkRuntime.from_repo(repo)


def test_existing_identity_frame_and_resource_protections_reject_drift():
    from copy import deepcopy

    catalog = AssetCatalog.from_repo(ROOT)
    reconstruction = ReconstructionRegistry.from_repo(ROOT)
    snow = objects()
    snow.objects["OBJ-SNOW-JADE-91"]["identity_status"] = "MERGED"
    assert any("snow jade identity must remain OPEN" in e for e in snow.validate_integrity(ROOT, catalog, reconstruction))
    for identity, chapter, field, value, expected in [
        ("OBJ-TONGLING-JADE", 100, "frame_status", "LOST", "hard terminal outer-frame"),
        ("OBJ-RICE-JAR-95", 96, "quantity_state", "FULL_RESTORATION", "measured/partial"),
    ]:
        runtime = objects()
        state = runtime.snapshot(identity, chapter)["state"]
        probe = deepcopy(runtime.by_object[identity][-1])
        probe.update(id="OT-PROTECTION-PROBE", chapter=chapter, sequence=9999, movement="NONE")
        probe["from"] = deepcopy(state)
        probe["to"] = {**state, field: value}
        runtime.transitions.append(probe)
        runtime.by_object[identity].append(probe)
        errors = runtime.validate_integrity(ROOT, catalog, reconstruction)
        assert any(expected in error for error in errors)
