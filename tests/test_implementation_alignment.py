from pathlib import Path

from rcwh.competition import CompetitionRegistry
from rcwh.implementation_alignment import ImplementationAlignmentRuntime
from rcwh.literary_ecology import LiteraryEcologyRuntime
from rcwh.object_network import ObjectNetworkRuntime
from rcwh.plocks import LiteraryProtectionRegistry
from rcwh.promotion import PromotionRegistry
from rcwh.reconstruction import ReconstructionRegistry
from rcwh.registry import MigrationRegistry
from rcwh.world import WorldRuntime


ROOT = Path(__file__).resolve().parents[1]
STABLE_SHA = "4645da79b1bed76f54be281c50b5df648f599ea41541fb7855685753b6a85320"


def runtime() -> ImplementationAlignmentRuntime:
    return ImplementationAlignmentRuntime.from_repo(ROOT)


def test_m6_summary_and_completion_boundary():
    summary = runtime().summary()
    assert summary["status"] == "PASS"
    assert summary["stable_release"] == "stable-active-v4.1"
    assert summary["stable_sha256"] == STABLE_SHA
    assert summary["chapters"] == 20
    assert summary["chapter_plans"] == 20
    assert summary["implementation_facts"] == 39
    assert summary["chapter_protections"] == 20
    assert summary["cross_chapter_protections"] == 5
    assert summary["competition_fixtures"] == 4
    assert summary["completion"]["literature_frozen"] is True
    assert summary["completion"]["p0_full_coverage"] is False
    assert summary["completion"]["completion_gate_ready"] is False


def test_stable_body_locators_cover_exactly_2684_lines_without_gaps():
    chapters = [runtime().chapters[ch] for ch in range(81, 101)]
    expected = 1
    for item in chapters:
        assert item["line_start"] == expected
        assert item["line_end"] >= item["line_start"]
        expected = item["line_end"] + 1
    assert expected - 1 == 2684
    assert chapters[0]["line_start"] == 1
    assert chapters[-1]["line_end"] == 2684


def test_stable_chapter_hashes_match_reviewed_promotion_baseline_fixture():
    rt = runtime()
    promotion = PromotionRegistry.from_repo(ROOT).records[
        "promotion:ch86:b:v1-5-candidate"
    ]
    assert promotion["baseline"]["sha256"] == STABLE_SHA
    for ch in range(81, 101):
        assert rt.chapters[ch]["sha256"] == promotion["baseline_chapter_sha256"][str(ch)]


def test_source_normalization_keeps_stale_v13_header_distinct_from_effective_v14_release():
    norm = runtime().data["source_normalization"]
    assert norm["stale_header_body_sha256"] == "bd15b087dc6ac701a83312007d1cc77453f22f1ffe7791dc77d787c9fc532664"
    assert norm["effective_stable_body_sha256"] == STABLE_SHA
    assert norm["stale_header_body_sha256"] != norm["effective_stable_body_sha256"]


def test_all_twenty_chapters_have_plan_protection_and_machine_alignment():
    rt = runtime()
    for ch in range(81, 101):
        payload = rt.chapter(ch)
        assert payload["stable_body"]["chapter"] == ch
        assert payload["plan"]["chapter"] == ch
        assert payload["protection"]["chapter"] == ch
        assert payload["alignment"]["chapter"] == ch
        assert payload["alignment"]["reconstruction_query"].endswith(str(ch))
        assert payload["alignment"]["world_query"].endswith(str(ch))
        assert payload["alignment"]["literary_ecology_query"].endswith(str(ch))


def test_title_axis_boundaries_are_preserved_in_implementation_alignment():
    rt = runtime()
    assert rt.plans[90]["title_source"] == "T0完整未来回目；当前第90为PC"
    assert "T2稿名" in rt.plans[92]["title_source"]
    assert "STRUCTURE硬证" in rt.plans[100]["title_source"]
    assert "正式榜名OPEN" in rt.plans[100]["title_source"]


def test_implementation_facts_remain_downstream_and_reversible():
    rt = runtime()
    assert rt.fact("IF-017")["identity"] == "PC"
    assert rt.fact("IF-033")["identity"] == "C"
    assert rt.fact("IF-039")["identity"] == "G/P-Lock"
    assert all(item["reversible"] is True for item in rt.facts.values())
    assert "Evidence" in rt.data["epistemic_rule"]


def test_full_chapter_protection_table_and_specialized_plock_bridge_coexist():
    rt = runtime()
    assert rt.protection(89)["level"] == "P1"
    assert "水桶" in rt.protection(89)["must_preserve"]
    assert rt.protection(92)["level"] == "P1"
    assert "救援队" in rt.protection(92)["forbidden_drift"]
    specialized = {x["id"] for x in rt.data["specialized_plocks"]}
    assert specialized == {
        "plock:ch86:cold-medicine",
        "plock:ch89:small-life-after-confiscation",
        "plock:ch92:procedure-density",
        "plock:ch97:miaoyu-object-progression",
        "plock:ch100:record-keeper-ending",
    }


def test_pressure_production_is_frozen_exactly_at_handover_state():
    rt = runtime()
    assert rt.competition(86)["state"] == "ADJUDICATED"
    assert rt.competition(86)["winner"] == "ch86-B"
    assert rt.competition(86)["freeze_effect"] == "DO_NOT_PROMOTE_DURING_FULL_MIGRATION"
    assert rt.competition(89)["state"] == "IN_REVIEW"
    assert rt.competition(89)["progress"] == "PHASE1_ONLY"
    assert rt.competition(89)["freeze_effect"] == "DO_NOT_CONTINUE_PHASE2"
    assert rt.competition(92)["freeze_effect"] == "DO_NOT_START"
    assert rt.competition(97)["freeze_effect"] == "DO_NOT_START"


def test_current_registry_marks_four_m6_sources_semantically_full_but_gate_closed():
    registry = MigrationRegistry.from_repo(ROOT)
    for ref in [
        "doc:b90e41f44edb",
        "doc:4645da79b1be",
        "doc:626917a3603d",
        "doc:23861cce04ac",
    ]:
        assert registry.documents[ref]["machine_representation"]["semantic_coverage"] == "FULL"
        assert registry.documents[ref]["machine_representation"]["markdown_only"] is False
    current = registry.current_summary()
    assert current["implementation_alignment_queryable"] is True
    assert current["literature_frozen"] is True
    assert current["completion_gate_ready"] is False


def test_m6_source_trace_resolves_to_self_contained_document_paths():
    registry = MigrationRegistry.from_repo(ROOT)
    payload = runtime().trace("source", "4645da79b1be", registry)
    assert payload["trace_complete"] is True
    source = payload["resolved_sources"][0]
    assert source["sha256"] == STABLE_SHA
    assert source["self_contained_path"].startswith("02_CURRENT_RUNTIME/IMPLEMENTATION/")
    assert source["semantic_coverage"] == "FULL"


def test_m6_integrity_passes_against_all_runtime_layers():
    registry = MigrationRegistry.from_repo(ROOT)
    reconstruction = ReconstructionRegistry.from_repo(ROOT)
    world = WorldRuntime.from_repo(ROOT)
    objects = ObjectNetworkRuntime.from_repo(ROOT)
    literary = LiteraryEcologyRuntime.from_repo(ROOT)
    plocks = LiteraryProtectionRegistry.from_repo(ROOT)
    competitions = CompetitionRegistry.from_repo(ROOT)
    promotions = PromotionRegistry.from_repo(ROOT)
    assert runtime().validate_integrity(
        ROOT,
        registry,
        reconstruction,
        world,
        objects,
        literary,
        plocks,
        competitions,
        promotions,
    ) == []
