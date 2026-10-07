from pathlib import Path

from rcwh.registry import MigrationRegistry


ROOT = Path(__file__).resolve().parents[1]
STABLE_SHA = "4645da79b1bed76f54be281c50b5df648f599ea41541fb7855685753b6a85320"


def registry() -> MigrationRegistry:
    return MigrationRegistry.from_repo(ROOT)


def test_package_registry_has_exact_19_inventory_packages():
    reg = registry()
    assert len(reg.packages) == 19
    assert reg.packages["pkg:stable-active-v4.1"]["classification"] == "CURRENT_CANONICAL"
    assert reg.packages["pkg:stable-active-v4.1"]["sha256"] == "83c96f328d106e29ba3457d817bc5f96d939d21d3c6ed95595d2187ad0fb50ed"


def test_superseded_and_revoked_packages_cannot_drive_current_runtime():
    reg = registry()
    blocked = {
        "pkg:r4-phase3-rg97-v1.0",
        "pkg:r4-phase6-current-v1.0",
        "pkg:r4-phase7-r4f-v1.0",
        "pkg:r4-phase7-r4f-v1.1",
        "pkg:stable-active-v4.0",
    }
    for package_id in blocked:
        package = reg.packages[package_id]
        assert package["runtime_authority"] == "NO"
        assert package["allow_current_import"] is False


def test_document_registry_covers_v41_package_and_current_runtime_one_to_one():
    reg = registry()
    v41 = {
        doc_id
        for doc_id, doc in reg.documents.items()
        if doc.get("v4_1_package_member")
    }
    current = [doc for doc in reg.documents.values() if doc.get("current_runtime_path")]
    assert len(v41) == 23
    assert len(current) == 15
    assert all(doc["authority"] == "CURRENT" for doc in current)
    assert all(doc["runtime_authority"] == "YES" for doc in current)


def test_content_hash_registry_deduplicates_by_sha_not_filename():
    reg = registry()
    assert len(reg.content_hashes) == len(reg.documents) == 65
    for doc in reg.documents.values():
        item = reg.content_hash(doc["sha256"])
        assert item["deduplication_key"] == "SHA256"
        assert item["canonical_document_ref"] == doc["id"]


def test_current_authority_is_registry_complete_and_m8_gate_signed():
    current = registry().current_summary()
    assert current["stable_active_sha256"] == STABLE_SHA
    assert current["v4_1_package_file_count"] == 23
    assert current["current_runtime_document_count"] == 15
    assert current["registry_coverage"] == "FULL"
    assert current["semantic_coverage_counts"] == {
        "FULL": 15,
        "PARTIAL": 0,
        "MINIMAL": 0,
        "NONE": 0,
    }
    assert current["completion_gate_ready"] is True
    assert current["completion_gate_status"] == "PASS"
    assert current["coverage_report_signed_off"] is True
    assert current["literature_resume_authorized"] is True


def test_m6_keeps_current_markdown_zero_and_promotes_four_implementation_sources_to_full():
    reg = registry()
    current = [reg.documents[x] for x in reg.current_summary()["current_runtime_document_refs"]]
    islands = [doc for doc in current if doc["machine_representation"]["markdown_only"]]
    assert islands == []
    plan = reg.documents["doc:23861cce04ac"]
    assert plan["machine_representation"]["semantic_coverage"] == "FULL"
    assert reg.documents["doc:b90e41f44edb"]["machine_representation"]["semantic_coverage"] == "FULL"
    assert reg.documents["doc:4645da79b1be"]["machine_representation"]["semantic_coverage"] == "FULL"
    assert reg.documents["doc:626917a3603d"]["machine_representation"]["semantic_coverage"] == "FULL"
    assert reg.current_summary()["implementation_alignment_queryable"] is True
    assert reg.current_summary()["literature_frozen"] is True
    assert reg.current_summary()["current_markdown_islands"] == 0


def test_all_v41_package_files_have_explicit_machine_landings():
    reg = registry()
    members = [
        doc
        for doc in reg.documents.values()
        if doc.get("v4_1_package_member")
    ]
    assert len(members) == 23
    for doc in members:
        machine = doc["machine_representation"]
        assert machine["target_node"]
        assert machine["target_path"]
        assert machine["migration_action"]


def test_registry_integrity_passes():
    assert registry().validate_integrity() == []
