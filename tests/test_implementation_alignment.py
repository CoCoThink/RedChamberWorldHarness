from pathlib import Path

from rcwh.competition import CompetitionRegistry
from rcwh.implementation_alignment import ImplementationAlignmentRuntime
from rcwh.literary_ecology import LiteraryEcologyRuntime
from rcwh.object_network import ObjectNetworkRuntime
from rcwh.plocks import LiteraryProtectionRegistry
from rcwh.workflow import ProjectState
from copy import deepcopy
import hashlib
from rcwh.reconstruction import ReconstructionRegistry
from rcwh.assets import AssetCatalog
from rcwh.world import WorldRuntime


ROOT = Path(__file__).resolve().parents[1]



def runtime() -> ImplementationAlignmentRuntime:
    return ImplementationAlignmentRuntime.from_repo(ROOT)


def test_summary_identifies_selected_release():
    summary = runtime().summary()
    assert summary["stable_release"] == ProjectState.from_repo(ROOT).release().data["id"]
    assert summary["stable_sha256"] == ProjectState.from_repo(ROOT).release().data["text_sha256"]


def test_stable_body_locators_cover_actual_selected_release_without_gaps():
    rt = runtime()
    manifest = ProjectState.from_repo(ROOT).release()
    raw = AssetCatalog.from_repo(ROOT).resolve(manifest.data["text_asset_ref"]).path.read_bytes()
    lines = raw.decode("utf-8").splitlines(keepends=True)
    expected = 1
    for ch in rt.chapter_scope:
        item = rt.chapters[ch]
        assert item["line_start"] == expected
        fragment = "".join(lines[item["line_start"] - 1:item["line_end"]]).encode("utf-8")
        assert hashlib.sha256(fragment).hexdigest() == item["sha256"]
        expected = item["line_end"] + 1
    assert expected - 1 == len(lines)


def test_all_twenty_chapters_have_plan_protection_and_machine_alignment():
    rt = runtime()
    for ch in runtime().chapter_scope:
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
    assert specialized == {lock["id"] for lock in LiteraryProtectionRegistry.from_repo(ROOT).locks.values()
                           if lock["state"] == "P_LOCKED" and lock["chapter"] in rt.chapter_scope}


def test_alignment_uses_live_competition_records_without_a_freeze_snapshot():
    rt = runtime()
    records = CompetitionRegistry.from_repo(ROOT).records
    assert "competition_fixtures" not in rt.data
    for chapter, record in rt.competitions.items():
        assert rt.competition(chapter) == records[record["id"]]


def test_m6_source_trace_resolves_to_self_contained_document_paths():
    registry = AssetCatalog.from_repo(ROOT)
    payload = runtime().trace("source", "asset:release:stable:v1.4:readable", registry)
    assert payload["trace_complete"] is True
    source = payload["resolved_sources"][0]
    assert source["sha256"] == ProjectState.from_repo(ROOT).release().data["text_sha256"]
    assert source["path"].startswith("releases/stable/")


def test_m6_integrity_passes_against_all_runtime_layers():
    registry = AssetCatalog.from_repo(ROOT)
    reconstruction = ReconstructionRegistry.from_repo(ROOT)
    world = WorldRuntime.from_repo(ROOT)
    objects = ObjectNetworkRuntime.from_repo(ROOT)
    literary = LiteraryEcologyRuntime.from_repo(ROOT)
    plocks = LiteraryProtectionRegistry.from_repo(ROOT)
    competitions = CompetitionRegistry.from_repo(ROOT)
    assert runtime().validate_integrity(
        ROOT,
        registry,
        reconstruction,
        world,
        objects,
        literary,
        plocks,
        competitions,
    ) == []


def alignment_errors(rt, plocks=None):
    return rt.validate_integrity(
        ROOT, AssetCatalog.from_repo(ROOT), ReconstructionRegistry.from_repo(ROOT),
        WorldRuntime.from_repo(ROOT), ObjectNetworkRuntime.from_repo(ROOT),
        LiteraryEcologyRuntime.from_repo(ROOT), plocks or LiteraryProtectionRegistry.from_repo(ROOT),
        CompetitionRegistry.from_repo(ROOT),
    )


def test_new_registered_protection_requires_matching_declaration_without_fixed_count():
    rt = runtime()
    plocks = LiteraryProtectionRegistry.from_repo(ROOT)
    new = deepcopy(next(iter(plocks.locks.values())))
    new["id"] = "plock:test:additional-protection"
    plocks.locks[new["id"]] = new
    assert any("specialized P-Lock coverage" in e for e in alignment_errors(rt, plocks))
    rt.data["specialized_plocks"].append({"id": new["id"], "chapter": new["chapter"]})
    assert alignment_errors(rt, plocks) == []
    rt.data["specialized_plocks"][-1]["chapter"] += 1
    assert any("chapter binding drift" in e for e in alignment_errors(rt, plocks))


def test_alignment_rejects_release_identity_and_object_location_drift():
    rt = runtime()
    rt.data["stable_release"]["release_id"] = "release:unselected"
    rt.data["object_query_locations"][str(rt.chapter_scope[0])] = "missing-location"
    errors = alignment_errors(rt)
    assert any("differs from selected release" in e for e in errors)
    assert any("unknown object-query" in e for e in errors)
