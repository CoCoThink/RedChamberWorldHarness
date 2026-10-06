from pathlib import Path

from rcwh.open_interfaces import OpenInterfaceRegistry
from rcwh.reconstruction import ReconstructionRegistry
from rcwh.registry import MigrationRegistry


ROOT = Path(__file__).resolve().parents[1]


def recon() -> ReconstructionRegistry:
    return ReconstructionRegistry.from_repo(ROOT)


def test_m2_has_complete_rp_and_timeline_cardinality():
    r = recon()
    assert set(r.r_nodes) == {f"R{i:02d}" for i in range(1, 44)}
    assert set(r.p_edges) == {f"P{i:02d}" for i in range(1, 12)}
    assert set(r.timeline) == set(range(81, 101))
    assert set(r.chapters) == set(range(81, 101))


def test_all_current_chapter_cards_are_machine_queryable_and_pressure_set_is_frozen():
    r = recon()
    assert {x for x, item in r.chapters.items() if item["pressure_test"]} == {86, 89, 92, 97}
    for chapter in range(81, 101):
        item = r.chapter(chapter)
        assert item["source_ref"] == "doc:23861cce04ac"
        assert item["source_lines"][0] < item["source_lines"][1]
        assert item["key_constraints"]
        assert item["semantic_coverage"] == "PARTIAL_STRUCTURED"


def test_t0_title_wording_and_placement_are_not_collapsed():
    item = recon().chapter(90)
    assert item["title"] == "薛宝钗借词含讽谏　王熙凤知命强英雄"
    assert item["title_status"] == "T0_WORDING_PLACEMENT_PC"


def test_double_winter_and_ordinary_life_buffer_survive():
    r = recon()
    assert r.timeline_at(91)["time_window"] == "家败后的第一冬"
    assert r.timeline_at(95)["time_window"] == "家败后的第二冬"
    assert "普通生活" in r.timeline_at(99)["time_window"]


def test_jade_model_keeps_91_identity_open_and_old_u1_downgraded():
    jade = recon().data["jade_logistics"]
    assert jade["current_model"] == "U3P_PARTIAL_CONVERGENCE"
    assert jade["old_u1_status"] == "DOWNGRADED"
    ch91 = next(x for x in jade["stages"] if x["chapter"] == 91)
    assert ch91["identity"] == "OPEN"


def test_prison_model_is_real_detention_without_automatic_collective_liability_or_rescue():
    prison = recon().data["prison_case"]
    assert prison["model_id"] == "J1"
    assert "男丁自动连坐" in prison["forbidden"]
    assert "权贵救出" in prison["forbidden"]
    assert "劫狱" in prison["forbidden"]
    assert prison["chain"][-1].startswith("回贫寒临时住处")


def test_legacy_o01_o10_map_to_current_open28_and_o03_is_revised():
    r = recon()
    opens = OpenInterfaceRegistry.from_repo(ROOT)
    refs = set()
    for old in r.legacy_open.values():
        refs.update(old["current_open_refs"])
    assert refs <= set(opens.interfaces)
    assert r.legacy("O03")["mapping_relation"] == "REVISED_OLD_U1_DOWNGRADED"


def test_m2_sources_are_registered_and_current_markdown_islands_are_zero():
    migration = MigrationRegistry.from_repo(ROOT)
    r = recon()
    for source in r.data["sources"].values():
        assert source["document_ref"] in migration.documents
        assert migration.documents[source["document_ref"]]["sha256"] == source["sha256"]
    assert migration.current_summary()["current_markdown_islands"] == 0
    assert migration.current_summary()["completion_gate_ready"] is False


def test_reconstruction_integrity_passes():
    migration = MigrationRegistry.from_repo(ROOT)
    opens = OpenInterfaceRegistry.from_repo(ROOT)
    assert recon().validate_integrity(migration, opens) == []
