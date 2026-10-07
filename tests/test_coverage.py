from pathlib import Path

from rcwh.coverage import CoverageAuditRuntime, P0_INVENTORY_SHA256
from rcwh.implementation_alignment import ImplementationAlignmentRuntime
from rcwh.literary_ecology import LiteraryEcologyRuntime
from rcwh.object_network import ObjectNetworkRuntime
from rcwh.reconstruction import ReconstructionRegistry
from rcwh.registry import MigrationRegistry
from rcwh.regression import run_r4_evidence_regression
from rcwh.world import WorldRuntime


ROOT = Path(__file__).resolve().parents[1]
STABLE_SHA = "4645da79b1bed76f54be281c50b5df648f599ea41541fb7855685753b6a85320"


def audit() -> CoverageAuditRuntime:
    return CoverageAuditRuntime.from_repo(ROOT)


def test_p0_inventory_digest_and_exact_249_records():
    rt = audit()
    assert rt.inventory_sha256 == P0_INVENTORY_SHA256
    assert len(rt.records) == 249
    assert len(set(rt.records)) == 249


def test_pre_migration_p0_census_is_frozen_exactly():
    summary = audit().summary()
    assert summary["pre_migration_coverage"] == {
        "FULL": 9,
        "PARTIAL": 105,
        "MINIMAL": 1,
        "NONE": 134,
    }
    assert summary["authority"] == {
        "REFERENCE": 233,
        "CURRENT": 14,
        "SOURCE_AUTHORITY": 2,
    }


def test_m7_effective_p0_coverage_is_249_full_with_zero_gaps():
    summary = audit().summary(MigrationRegistry.from_repo(ROOT))
    assert summary["p0_total"] == 249
    assert summary["effective_coverage"] == {"FULL": 249}
    assert summary["concrete_source_paths"] == 249
    assert summary["unresolved"] == 0
    assert audit().gaps() == []


def test_p0_layer_census_matches_handover_inventory():
    assert audit().summary()["layers"] == {
        "EVIDENCE": 29,
        "EVIDENCE_LITERARY": 7,
        "GOVERNANCE": 5,
        "IMPLEMENTATION": 12,
        "LITERARY_ECOLOGY": 60,
        "LITERARY_EVIDENCE": 21,
        "LOCK": 18,
        "MECHANISM": 3,
        "PLANNING": 13,
        "RECONSTRUCTION": 49,
        "SOURCE": 2,
        "WORLD": 22,
        "WORLD_LITERARY": 8,
    }


def test_each_p0_record_has_concrete_zip_path_and_machine_binding():
    for record in audit().records.values():
        assert record["self_contained_path"].startswith(
            ("01_PRIMARY_SOURCES/", "02_CURRENT_RUNTIME/", "03_VALID_HISTORY/")
        )
        assert record["effective_coverage"] == "FULL"
        assert record["binding"]["surface"]
        assert record["binding"]["artifacts"]
        assert record["binding"]["query"].startswith("rcwh coverage target ")


def test_reference_history_is_bound_without_becoming_current_authority():
    rt = audit()
    reference = [
        x for x in rt.records.values()
        if x["authority"] == "REFERENCE" and x["pre_migration_coverage"] != "FULL"
    ]
    assert reference
    assert all(
        x["coverage_mode"] == "VERSIONED_REFERENCE_BOUND_TO_EFFECTIVE_RUNTIME"
        for x in reference
    )
    current = [x for x in rt.records.values() if x["authority"] == "CURRENT"]
    assert len(current) == 14
    assert all(x["coverage_mode"] == "DIRECT_CURRENT_RUNTIME" for x in current)


def test_target_queries_bind_literary_world_and_reconstruction_surfaces():
    rt = audit()
    voice = rt.target("literary.voice_corpus")
    assert voice["surface"] == "LITERARY_ECOLOGY"
    assert voice["effective_coverage"] == "FULL"
    world = rt.target("world.object_flow.jade")
    assert world["surface"] == "WORLD"
    assert "data/objects/m4.json" in world["artifacts"]
    chapter_plan = rt.target("reconstruction.chapter_plan")
    assert chapter_plan["surface"] == "RECONSTRUCTION"
    assert "data/implementation_alignment/m6.json" in chapter_plan["artifacts"]


def test_layer_queries_are_full_and_preserve_document_counts():
    rt = audit()
    literary = rt.layer("LITERARY_ECOLOGY")
    assert literary["documents"] == 60
    assert literary["full"] == 60
    assert literary["coverage"] == "FULL"
    reconstruction = rt.layer("RECONSTRUCTION")
    assert reconstruction["documents"] == 49
    assert reconstruction["full"] == 49
    world = rt.layer("WORLD")
    assert world["documents"] == 22
    assert world["full"] == 22


def test_all_current_runtime_documents_are_full_and_no_markdown_islands_remain():
    registry = MigrationRegistry.from_repo(ROOT)
    current = registry.current_summary()
    assert current["semantic_coverage_counts"] == {
        "FULL": 15,
        "PARTIAL": 0,
        "MINIMAL": 0,
        "NONE": 0,
    }
    assert current["current_markdown_islands"] == 0
    assert current["unresolved_authority_conflicts"] == 0
    assert current["stable_active_sha256"] == STABLE_SHA


def test_negative_archive_never_reactivates_superseded_or_revoked_packages():
    registry = MigrationRegistry.from_repo(ROOT)
    negative = audit().negative_archive
    assert negative["stable_active_effect"] == "NONE"
    for fixture in negative["package_fixtures"]:
        package = registry.packages[fixture["id"]]
        assert package["runtime_authority"] == "NO"
        assert package["allow_current_import"] is False


def test_m7_regression_passes_but_signoff_and_completion_gate_remain_for_m8():
    registry = MigrationRegistry.from_repo(ROOT)
    payload = audit().regression(
        registry,
        ReconstructionRegistry.from_repo(ROOT),
        WorldRuntime.from_repo(ROOT),
        ObjectNetworkRuntime.from_repo(ROOT),
        LiteraryEcologyRuntime.from_repo(ROOT),
        ImplementationAlignmentRuntime.from_repo(ROOT),
        run_r4_evidence_regression(ROOT),
    )
    assert payload["overall"] == "PASS"
    assert all(x == "PASS" for x in payload["checks"].values())
    assert payload["coverage_signoff"] == "PENDING_M8"
    assert payload["completion_gate_ready"] is False


def test_m7_project_state_keeps_literature_frozen_and_m8_pending():
    state = audit().project_state
    assert state["milestones"]["M0"] == "PASS"
    assert state["milestones"]["M6"] == "PASS"
    assert state["milestones"]["M7"] == "PASS_CANDIDATE"
    assert state["milestones"]["M8"] == "PENDING"
    assert state["literature_freeze"]["active"] is True
    assert state["literature_freeze"]["ch89"] == "PHASE1_ONLY_DO_NOT_CONTINUE"
    assert state["literature_freeze"]["ch92"] == "DO_NOT_START"
    assert state["literature_freeze"]["ch97"] == "DO_NOT_START"
    assert state["p0_coverage"]["signed_off"] is False
    assert state["completion_gate_ready"] is False


def test_m7_integrity_passes_against_all_runtime_layers():
    registry = MigrationRegistry.from_repo(ROOT)
    assert audit().validate_integrity(
        registry,
        ReconstructionRegistry.from_repo(ROOT),
        WorldRuntime.from_repo(ROOT),
        ObjectNetworkRuntime.from_repo(ROOT),
        LiteraryEcologyRuntime.from_repo(ROOT),
        ImplementationAlignmentRuntime.from_repo(ROOT),
        run_r4_evidence_regression(ROOT),
    ) == []
