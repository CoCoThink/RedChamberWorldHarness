from pathlib import Path

from rcwh.open_interfaces import OpenInterfaceRegistry
from rcwh.reconstruction import ReconstructionRegistry
from rcwh.assets import AssetCatalog
from rcwh.workflow import ProjectState


ROOT = Path(__file__).resolve().parents[1]


def recon() -> ReconstructionRegistry:
    return ReconstructionRegistry.from_repo(ROOT)


def test_m2_has_complete_rp_and_timeline_cardinality():
    r = recon()
    assert r.r_nodes and r.p_edges
    assert set(r.timeline) == set(recon().chapter_scope)
    assert set(r.chapters) == set(recon().chapter_scope)


def test_all_current_chapter_cards_follow_configured_pressure_sequence():
    r = recon()
    assert {x for x, item in r.chapters.items() if item["pressure_test"]} == set(ProjectState.from_repo(ROOT).owner("literary")["sequence"])
    for chapter in recon().chapter_scope:
        item = r.chapter(chapter)
        assert item["source_ref"] == r.data["sources"]["chapter_plan"]["asset_ref"]
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


def test_reconstruction_sources_resolve_to_local_assets():
    migration = AssetCatalog.from_repo(ROOT)
    r = recon()
    for source in r.data["sources"].values():
        assert source["asset_ref"] in migration.assets
        assert migration.assets[source["asset_ref"]]["sha256"] == source["sha256"]


def test_reconstruction_integrity_passes():
    migration = AssetCatalog.from_repo(ROOT)
    opens = OpenInterfaceRegistry.from_repo(ROOT)
    assert recon().validate_integrity(migration, opens) == []
