from pathlib import Path
from rcwh.literary_stress import ScenarioLiteraryStressRuntime
from rcwh.literary_suite import LiteraryEvaluatorSuite
from rcwh.microdraft import ControlledMicrodraftRuntime
from rcwh.narrative_discourse import NarrativeDiscourseRuntime
from rcwh.literary_production import LiteraryProductionRuntime, STABLE_SHA
ROOT=Path(__file__).resolve().parents[1]
def lab(): return ControlledMicrodraftRuntime.from_repo(ROOT)
def discourse(): return NarrativeDiscourseRuntime.from_repo(ROOT)
def stress(): return ScenarioLiteraryStressRuntime.from_repo(ROOT)
def suite(): return LiteraryEvaluatorSuite.from_repo(ROOT)

def test_p6_has_exactly_twenty_microdrafts_one_per_p5_card():
    assert len(lab().drafts)==20
    cards={(sid,p["id"]) for sid,contract in stress().contracts.items() for p in contract["probes"]}
    got={(x["scenario_id"],x["probe_id"]) for x in lab().data["drafts"]}
    assert got==cards

def test_p6_all_microdrafts_machine_ready_without_auto_pass():
    payload=lab().evaluate_all(discourse(),stress(),suite())
    assert payload["status"]=="PASS"
    assert payload["draft_count"]==20
    assert payload["ready_count"]==20
    assert payload["blocker_count"]==0
    assert payload["winner"] is None
    assert payload["automatic_literary_pass"] is False
    assert payload["automatic_winner"] is False

def test_p6_has_five_blind_cells_with_four_variants_each():
    payload=lab().evaluate_all(discourse(),stress(),suite())
    assert len(payload["cells"])==5
    assert {x["candidate_count"] for x in payload["cells"]}=={4}

def test_blind_packets_do_not_leak_route_or_probe_metadata():
    for i in range(1,6):
        packet=lab().cell_packet(f"W{i}")
        assert lab().blind_packet_violations(packet)==[]
        raw=repr(packet)
        assert "scenario_id" not in raw and "probe_id" not in raw and "SCN-CURRENT-C" not in raw

def test_each_microdraft_preserves_p5_primary_focalizer_binding():
    for token,spec in lab().drafts.items():
        screen=lab().screen(token,discourse(),stress(),suite())
        assert not any(x["kind"]=="FOCALIZER_BINDING_DRIFT" for x in screen["blockers"])
        card=discourse().card(spec["scenario_id"],spec["probe_id"],stress())
        assert spec["primary_focalizer"]==card["sjuzet_plan"]["primary_focalizer"]

def test_each_microdraft_hits_three_required_life_or_object_anchors():
    for token in lab().drafts:
        assert len(lab().screen(token,discourse(),stress(),suite())["anchor_hits"])>=3

def test_p6_machine_cannot_eliminate_routes_or_change_canonical_authority():
    assert lab().data["policy"]["route_elimination_by_machine"] is False
    assert lab().data["policy"]["canonical_prose_effect"]=="NONE"
    literary=LiteraryProductionRuntime.from_repo(ROOT)
    assert literary.data["stable_active"]["sha256"]==STABLE_SHA
    assert literary.data["stable_active"]["changed"] is False
    assert literary.data["chapter89"]["plock_manual_review"]=="PENDING"
    assert literary.data["chapter89"]["blind_read"]=="PENDING"

def test_p6_integrity():
    assert lab().validate_integrity(discourse(),stress(),suite())==[]


def test_p6_project_state_is_pass_and_records_gate_ci():
    from rcwh.io import load_data

    state = load_data(ROOT / "data" / "project_state" / "controlled_microdraft_v012.json")
    assert state["status"] == "PASS"
    assert state["authority"] == "SHADOW_ONLY"
    assert state["next_gate"] == "P7_BLIND_MICRODRAFT_REVIEW"
    assert set(state["effects"].values()) == {"NONE"}
    assert state["ci"] == {
        "run_id": 37648871831,
        "conclusion": "SUCCESS",
        "pytest": "285 passed / 0 failed",
        "validate": "PASS",
    }
