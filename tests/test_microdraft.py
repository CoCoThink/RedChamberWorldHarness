from pathlib import Path
from rcwh.literary_stress import ScenarioLiteraryStressRuntime
from rcwh.literary_suite import LiteraryEvaluatorSuite
from rcwh.microdraft import ControlledMicrodraftRuntime
from rcwh.narrative_discourse import NarrativeDiscourseRuntime
ROOT=Path(__file__).resolve().parents[1]
def lab(): return ControlledMicrodraftRuntime.from_repo(ROOT)
def discourse(): return NarrativeDiscourseRuntime.from_repo(ROOT)
def stress(): return ScenarioLiteraryStressRuntime.from_repo(ROOT)
def suite(): return LiteraryEvaluatorSuite.from_repo(ROOT)

def test_p6_has_one_microdraft_per_p5_card():
    cards={(sid,p["id"]) for sid,contract in stress().contracts.items() for p in contract["probes"]}
    got={(x["scenario_id"],x["probe_id"]) for x in lab().data["drafts"]}
    assert got==cards

def test_p6_all_microdrafts_machine_ready_without_auto_pass():
    payload=lab().evaluate_all(discourse(),stress(),suite())
    assert payload["status"]=="PASS"
    assert payload["draft_count"]==len(lab().drafts)
    assert payload["ready_count"]==len(lab().drafts)
    assert payload["blocker_count"]==0
    assert payload["winner"] is None
    assert payload["automatic_literary_pass"] is False
    assert payload["automatic_winner"] is False

def test_p6_cells_cover_declared_design_and_upstream_routes():
    payload=lab().evaluate_all(discourse(),stress(),suite())
    assert {x["cell_id"] for x in payload["cells"]}=={x["id"] for x in lab().data["design"]["cells"]}
    assert {x["candidate_count"] for x in payload["cells"]}=={len(stress().contracts)}

def test_blind_packets_do_not_leak_route_or_probe_metadata():
    for cell in lab().data["design"]["cells"]:
        packet=lab().cell_packet(cell["id"])
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

def test_p6_machine_cannot_eliminate_routes_or_change_canonical_authority(production_unchanged):
    assert lab().data["policy"]["route_elimination_by_machine"] is False
    assert lab().data["policy"]["canonical_prose_effect"]=="NONE"
    lab().evaluate_all(discourse(), stress(), suite())

def test_p6_integrity():
    assert lab().validate_integrity(discourse(),stress(),suite())==[]
