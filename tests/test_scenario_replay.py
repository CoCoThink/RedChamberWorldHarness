from pathlib import Path

from rcwh.hypotheses import HypothesisRuntime
from rcwh.literary_production import STABLE_SHA, LiteraryProductionRuntime
from rcwh.scenario_replay import CounterfactualReplayRuntime
from rcwh.scenarios import ScenarioRuntime
from rcwh.world import WorldRuntime

ROOT = Path(__file__).resolve().parents[1]


def runtime() -> CounterfactualReplayRuntime:
    return CounterfactualReplayRuntime.from_repo(ROOT)


def scenarios() -> ScenarioRuntime:
    return ScenarioRuntime.from_repo(ROOT)


def world() -> WorldRuntime:
    return WorldRuntime.from_repo(ROOT)


def test_p2_replays_all_ten_seed_scenarios_without_hard_blockers():
    payload = runtime().evaluate_all(scenarios(), world())
    assert payload["status"] == "PASS"
    assert len(payload["scenarios"]) == 10
    assert all(row["blockers"] == 0 for row in payload["scenarios"])


def test_current_c_reference_is_exact_m3_world_state_not_a_bonus_prior():
    for chapter in range(81, 101):
        replay = runtime().snapshot("SCN-CURRENT-C", chapter, scenarios(), world())
        assert replay["state"] == world().snapshot(chapter)
    result = runtime().evaluate("SCN-CURRENT-C", scenarios(), world())
    assert result["automatic_winner"] is False
    assert result["single_total_score"] is False


def test_g0_marriage_occurs_before_daiyu_death_in_replay_only():
    snap = runtime().snapshot("SCN-EARLY-MARRIAGE", 83, scenarios(), world())
    assert snap["state"]["relations"]["rel:baoyu_baochai"]["status"] == "ACTIVE_SPOUSES"
    assert snap["state"]["characters"]["daiyu"]["life_state"] == "ACTIVE"
    assert snap["annotations"]["marriage_chapter"] == 83
    assert world().snapshot(83)["relations"]["rel:baoyu_baochai"]["status"] == "NOT_MARRIED"


def test_g2_late_marriage_separates_baochai_residence_until_marriage():
    s93 = runtime().snapshot("SCN-LATE-MARRIAGE", 93, scenarios(), world())
    s94 = runtime().snapshot("SCN-LATE-MARRIAGE", 94, scenarios(), world())
    assert s93["state"]["relations"]["rel:baoyu_baochai"]["status"] == "NOT_MARRIED"
    assert s93["state"]["characters"]["baochai"]["location"] == "SCN-LOC-XUE-TEMP"
    assert s94["state"]["relations"]["rel:baoyu_baochai"]["status"] == "ACTIVE_SPOUSES"
    assert s94["state"]["characters"]["baochai"]["location"] == s94["state"]["characters"]["baoyu"]["location"]


def test_fengjie_alive_powerless_can_coexist_with_qiaojie_rescue():
    snap = runtime().snapshot("SCN-FENGJIE-ALIVE-POWERLESS", 94, scenarios(), world())
    assert snap["state"]["characters"]["fengjie"]["life_state"] == "ACTIVE"
    assert snap["annotations"]["fengjie_protection_capacity"] == "NONE"
    assert snap["state"]["characters"]["qiaojie"]["location"] == "S08"
    result = runtime().evaluate("SCN-FENGJIE-ALIVE-POWERLESS", scenarios(), world())
    assert not result["blockers"]


def test_jade_multilayer_keeps_identity_open_and_no_object_teleportation():
    snap91 = runtime().snapshot("SCN-JADE-MULTILAYER", 91, scenarios(), world())
    snap98 = runtime().snapshot("SCN-JADE-MULTILAYER", 98, scenarios(), world())
    assert snap91["object_state"]["snow_jade_identity"] == "DISTINCT_ASSUMED_FOR_REPLAY"
    assert snap98["object_state"]["sent_jade_identity"] == "OPEN"
    result = runtime().evaluate("SCN-JADE-MULTILAYER", scenarios(), world())
    assert not [x for x in result["blockers"] if x["kind"] == "OBJECT_TELEPORTATION"]


def test_guazhou_route_is_a_pressure_not_a_hard_fact_or_blocker():
    snap = runtime().snapshot("SCN-MIAOYU-GUAZHOU-W2", 97, scenarios(), world())
    assert snap["state"]["characters"]["miaoyu"]["location"] == "SCN-LOC-GUAZHOU-FERRY"
    result = runtime().evaluate("SCN-MIAOYU-GUAZHOU-W2", scenarios(), world())
    assert any(x["kind"] == "W2_DEPENDENCY" for x in result["pressures"])
    assert not result["blockers"]


def test_compact_terminal_route_delays_departure_until_chapter_100():
    s99 = runtime().snapshot("SCN-TERMINAL-COMPACT", 99, scenarios(), world())
    s100 = runtime().snapshot("SCN-TERMINAL-COMPACT", 100, scenarios(), world())
    assert s99["state"]["relations"]["rel:baoyu_baochai"]["status"] == "ACTIVE_SPOUSES"
    assert s99["state"]["characters"]["baoyu"]["location"] == "S09"
    assert s100["state"]["relations"]["rel:baoyu_baochai"]["status"] == "SPOUSES_SEPARATED_BY_BAOYU_DEPARTURE"
    assert s100["state"]["global"]["outer_frame"] == "S15_OPEN"


def test_p2_integrity_and_authority_boundaries():
    errors = runtime().validate_integrity(HypothesisRuntime.from_repo(ROOT), scenarios(), world())
    assert errors == []
    literary = LiteraryProductionRuntime.from_repo(ROOT)
    assert literary.data["stable_active"]["sha256"] == STABLE_SHA
    assert literary.data["stable_active"]["changed"] is False
    assert literary.data["chapter89"]["plock_manual_review"] == "PENDING"
    assert literary.data["chapter89"]["blind_read"] == "PENDING"


def test_p2_project_state_is_pass_and_next_gate_is_p3():
    from rcwh.io import load_data
    state = load_data(ROOT / "data" / "project_state" / "scenario_replay_v08.json")
    assert state["status"] == "PASS"
    assert state["authority"] == "SHADOW_ONLY"
    assert state["next_gate"] == "P3_PARETO_EVALUATION"
    assert set(state["effects"].values()) == {"NONE"}
    assert state["ci"]["run_id"] == 37638097185
    assert state["ci"]["validate"] == "PASS"
