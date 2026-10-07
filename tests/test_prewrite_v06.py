from pathlib import Path

from rcwh.literary_ecology import LiteraryEcologyRuntime
from rcwh.mechanism_adapters import HistoricalAdapterRuntime
from rcwh.plocks import LiteraryProtectionRegistry
from rcwh.prewrite import EXPECTED_EXECUTION_ORDER, STABLE_SHA, V5PrewriteRuntime
from rcwh.reconstruction import ReconstructionRegistry
from rcwh.registry import MigrationRegistry


ROOT = Path(__file__).resolve().parents[1]


def runtime() -> V5PrewriteRuntime:
    return V5PrewriteRuntime.from_repo(ROOT)


def deps():
    return (
        MigrationRegistry.from_repo(ROOT),
        ReconstructionRegistry.from_repo(ROOT),
        LiteraryEcologyRuntime.from_repo(ROOT),
        LiteraryProtectionRegistry.from_repo(ROOT),
        HistoricalAdapterRuntime.from_repo(ROOT),
    )


def test_issue6_summary_and_actual_v52_execution_order():
    payload = runtime().summary()
    assert payload["status"] == "PASS_CANDIDATE"
    assert payload["authority"] == "STAGING_ONLY"
    assert payload["evidence_effect"] == "NONE"
    assert payload["stable_active_effect"] == "NONE"
    assert payload["execution_order"] == EXPECTED_EXECUTION_ORDER
    assert payload["execution_order"] == [33, 34, 35, 40, 39, 38, 37, 36, 41, 42]
    assert payload["feeds_staging"] is True
    assert payload["becomes_evidence"] is False


def test_step33_imports_six_audited_ecology_profiles_without_recomputing_evidence():
    rt = runtime()
    literary = LiteraryEcologyRuntime.from_repo(ROOT)
    payload = rt.corpus()
    assert payload["mode"] == "IMPORTED_AUDITED_PROFILE"
    assert len(payload["profiles"]) == 6
    assert payload["authority"] == "STAGING_BASELINE_ONLY"
    assert payload["evidence_effect"] == "NONE"
    for item in payload["profiles"]:
        assert item["source_ref"] in literary.data["sources"]
        assert item["frozen_conclusions"]


def test_step34_has_exact_twenty_by_twelve_gap_cards_and_expected_aggregates():
    rt = runtime()
    assert set(rt.gaps) == set(range(81, 101))
    assert len(rt.data["gap_dimensions"]) == 12
    assert all(len(card["states"]) == 12 for card in rt.gaps.values())

    assert rt.gaps[86]["states"]["main_process"] == "MISSING"
    assert rt.gaps[90]["states"]["poetry"] == "NOT_APPLICABLE"
    assert rt.gaps[100]["states"]["chapter_frame"] == "MISSING"
    assert all(rt.gaps[ch]["states"]["comic_folk"] == "SUFFICIENT" for ch in range(81, 101))

    counts = {name: 0 for name in ("SUFFICIENT", "THIN", "MISSING", "NOT_APPLICABLE")}
    for card in rt.gaps.values():
        counts[card["states"]["economy"]] += 1
    assert counts == {
        "SUFFICIENT": 0,
        "THIN": 9,
        "MISSING": 11,
        "NOT_APPLICABLE": 0,
    }


def test_step35_plans_all_twenty_chapters_and_85_candidate_scenes():
    rt = runtime()
    assert set(rt.planners) == set(range(81, 101))
    assert sum(len(x["candidate_scenes"]) for x in rt.planners.values()) == 85

    ch92 = rt.scenes(92)
    assert ch92["core_process"] == "认单→留质→问讯→羁押生活→外部递物→待释"
    assert [x["id"] for x in ch92["candidate_scenes"]] == [
        "92-S1",
        "92-S2",
        "92-S3",
        "92-S4",
        "92-S5",
        "92-S6",
    ]
    assert ch92["evidence_effect"] == "NONE"
    assert ch92["may_create_evidence"] is False


def test_steps36_to41_are_machine_bound_but_remain_staging_only():
    rt = runtime()
    _, _, literary, _, adapters = deps()
    for step in range(36, 42):
        payload = rt.step(step, 100, literary, adapters)
        assert payload["authority"] == "STAGING_ONLY"
        assert payload["evidence_effect"] == "NONE"
        assert payload["stable_active_effect"] == "NONE"

    step36 = rt.step(36, 100, literary, adapters)
    assert step36["author_verse_policy"]["chapter"] == 100
    step37 = rt.step(37, 100, literary, adapters)
    assert step37["text_ecology"]["chapter"] == 100
    assert "A01" in step37["global_evidence_nodes"]
    step40 = rt.step(40, 89, literary, adapters)
    assert step40["four_chains"] == ["people", "money", "material", "information"]
    step41 = rt.step(41, 100, literary, adapters)
    assert step41["ambiguity_required"] is True
    assert step41["qingbang_boundary"]["formal_title_status"] == "OPEN"


def test_step42_generates_machine_readable_contract_for_every_chapter():
    rt = runtime()
    registry, reconstruction, literary, plocks, adapters = deps()
    contracts = [
        rt.contract(ch, reconstruction, literary, plocks, adapters, registry)
        for ch in range(81, 101)
    ]
    assert len(contracts) == 20
    assert {x["chapter"] for x in contracts} == set(range(81, 101))
    for contract in contracts:
        assert contract["id"] == f"prewrite:ch{contract['chapter']}:v0.6"
        assert contract["authority"] == "STAGING_ONLY"
        assert contract["evidence_effect"] == "NONE"
        assert contract["stable_active_effect"] == "NONE"
        assert contract["stable_active_sha256"] == STABLE_SHA
        assert contract["hard_context"]["anchor_refs"]
        assert contract["step34_gap_card"]["states"]
        assert contract["step35_scene_plan"]["candidate_scenes"]
        assert contract["step36_author_verse"]["chapter"] == contract["chapter"]
        assert contract["step37_text_ecology"]["chapter"] == contract["chapter"]
        assert contract["staging"]["ready"] is True
        assert contract["staging"]["automatic_prose_generation"] is False
        assert contract["staging"]["automatic_promotion"] is False


def test_ch89_and_ch100_contracts_preserve_current_boundary_specifics():
    rt = runtime()
    registry, reconstruction, literary, plocks, adapters = deps()

    ch89 = rt.contract(89, reconstruction, literary, plocks, adapters, registry)
    assert "plock:ch89:small-life-after-confiscation" in ch89["plock_refs"]
    assert ch89["step34_gap_card"]["states"]["economy"] == "MISSING"
    assert ch89["step35_scene_plan"]["action"] == "重点重构"

    ch100 = rt.contract(100, reconstruction, literary, plocks, adapters, registry)
    assert ch100["title_status"] == "TG_FINAL_LIST_FUNCTION_HARD_NAME_OPEN"
    assert ch100["step41_metaphysics"]["qingbang_boundary"]["formal_title_status"] == "OPEN"
    assert ch100["step36_author_verse"]["chapter"] == 100


def test_staging_packet_can_feed_step43_but_has_no_evidence_or_release_permission():
    rt = runtime()
    registry, reconstruction, literary, plocks, adapters = deps()
    packet = rt.staging_packet(
        89, reconstruction, literary, plocks, adapters, registry
    )
    assert packet["kind"] == "V5_PREWRITE_STAGING_PACKET"
    assert packet["authority"] == "STAGING_ONLY"
    assert packet["evidence_effect"] == "NONE"
    assert packet["stable_active_effect"] == "NONE"
    assert packet["staging_lane"] == "staging"
    assert packet["write_permissions"] == {
        "staging_artifacts": True,
        "evidence": False,
        "reconstruction_truth": False,
        "open_interfaces": False,
        "stable_active": False,
        "promotion": False,
    }
    assert packet["next_gate"] == "STEP43_CANDIDATE_WORKFLOW"


def test_prewrite_source_refs_are_registered_and_runtime_integrity_passes():
    rt = runtime()
    registry, reconstruction, literary, plocks, adapters = deps()
    assert rt.validate_integrity(
        registry, reconstruction, literary, plocks, adapters
    ) == []


def test_issue6_does_not_change_stable_active():
    registry = MigrationRegistry.from_repo(ROOT)
    assert registry.current_summary()["stable_active_sha256"] == STABLE_SHA
