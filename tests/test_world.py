from pathlib import Path

from rcwh.reconstruction import ReconstructionRegistry
from rcwh.registry import MigrationRegistry
from rcwh.runtime import WorldState
from rcwh.world import WorldRuntime


ROOT = Path(__file__).resolve().parents[1]


def world() -> WorldRuntime:
    return WorldRuntime.from_repo(ROOT)


def test_m3_world_cardinalities_and_query_surface():
    summary = world().summary()
    assert summary["chapters"] == 20
    assert summary["characters"] == 28
    assert summary["locations"] == 15
    assert summary["relations"] == 10
    assert summary["institutions"] == 9
    assert summary["completion"]["world_queryable"] is True
    assert summary["completion"]["event_replay"] is True
    assert summary["completion"]["completion_gate_ready"] is False


def test_world_replay_tracks_baoyu_legal_residence_and_marriage_state():
    w = world()
    assert w.character_state("baoyu", 87)["state"]["marital_status"] == "MARRIED_BAOCHAI"
    assert w.character_state("baoyu", 89)["state"]["location"] == "S06"
    assert w.character_state("baoyu", 92)["state"]["legal_status"] == "DETAINED_PENDING_INQUIRY"
    assert w.character_state("baoyu", 92)["state"]["location"] == "S07"
    assert w.character_state("baoyu", 93)["state"]["legal_status"] == "RELEASED_NO_RESTORATION"
    assert w.character_state("baoyu", 95)["state"]["location"] == "S09"
    assert w.character_state("baoyu", 99)["state"]["location"] == "S13"


def test_world_replay_tracks_deaths_without_hardening_open_cause():
    w = world()
    assert w.character_state("daiyu", 86)["state"]["life_state"] == "DEAD"
    assert w.character_state("fengjie", 93)["state"]["life_state"] == "DEAD"
    assert (
        w.relation("rel:xiangyun_weiruolan", 97)["state"]["status"]
        == "COHABITATION_INTERRUPTED_CAUSE_OPEN"
    )


def test_world_resource_stages_preserve_double_winter_and_non_reversal():
    w = world()
    assert w.economy(89)["stage"]["id"] == "E1"
    assert w.economy(92)["stage"]["id"] == "E2"
    assert w.economy(95)["stage"]["id"] == "E3"
    assert w.economy(96)["stage"]["id"] == "E4"
    assert w.economy(100)["stage"]["id"] == "E5"
    assert "不能逆转贫困" in w.economy(96)["flow"]["money_state"]


def test_knowledge_query_records_asymmetry_not_omniscience():
    w = world()
    xh = w.knowledge("xiaohong", 92)
    assert any(rule["kind"] == "RULE_KNOWLEDGE" for rule in xh["rules"])
    assert any("不掌握全案" in rule["note"] for rule in xh["rules"])
    by = w.knowledge("baoyu", 99)
    assert any(rule["fact"] == "baoyu_departure_intent" for rule in by["rules"])


def test_outer_frame_knowledge_never_leaks_into_human_runtime():
    w = world()
    assert w.snapshot(100)["global"]["human_access_to_outer_frame_knowledge"] is False
    bc = w.knowledge("baochai", 100)
    assert any(rule["kind"] == "FORBIDDEN_KNOWLEDGE" for rule in bc["rules"])


def test_presence_and_location_are_queryable_without_inventing_new_space():
    w = world()
    assert w.character_state("xiaohong", 92)["presence"] == "MAIN_SOURCE"
    assert w.character_state("xiaohong", 95)["presence"] == "NOT_LISTED_AS_SCENE_PARTICIPANT"
    assert w.location("S07")["name"] == "监所/狱神庙空间"


def test_existing_worldstate_loads_full_world_runtime_without_breaking_scene_state():
    state = WorldState.from_repo(ROOT)
    assert state.world_runtime is not None
    assert state.snapshot_at(92)["characters"]["baoyu"]["legal_status"] == "DETAINED_PENDING_INQUIRY"
    assert state.resolve("character.daiyu.resources.physical_strength") == "critical"


def test_m3_sources_are_registered_and_traceable():
    registry = MigrationRegistry.from_repo(ROOT)
    w = world()
    for source in w.data["sources"].values():
        assert source["document_ref"] in registry.documents
        assert registry.documents[source["document_ref"]]["sha256"] == source["sha256"]
    assert len(registry.documents) == len(registry.content_hashes) == 65


def test_world_integrity_passes_against_reconstruction():
    registry = MigrationRegistry.from_repo(ROOT)
    reconstruction = ReconstructionRegistry.from_repo(ROOT)
    assert world().validate_integrity(registry, reconstruction) == []
