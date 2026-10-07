from pathlib import Path
from rcwh.revision_ablation import CrossRouteRevisionAblationRuntime
from rcwh.microdraft import ControlledMicrodraftRuntime
from rcwh.blind_microdraft_review import BlindMicrodraftReviewRuntime
from rcwh.narrative_discourse import NarrativeDiscourseRuntime
from rcwh.literary_stress import ScenarioLiteraryStressRuntime
from rcwh.literary_suite import LiteraryEvaluatorSuite
from rcwh.literary_production import LiteraryProductionRuntime, STABLE_SHA
ROOT=Path(__file__).resolve().parents[1]
def p8(): return CrossRouteRevisionAblationRuntime.from_repo(ROOT)
def p6(): return ControlledMicrodraftRuntime.from_repo(ROOT)
def p7(): return BlindMicrodraftReviewRuntime.from_repo(ROOT)
def discourse(): return NarrativeDiscourseRuntime.from_repo(ROOT)
def stress(): return ScenarioLiteraryStressRuntime.from_repo(ROOT)
def suite(): return LiteraryEvaluatorSuite.from_repo(ROOT)

def test_p8_has_twenty_balanced_pairs_covering_all_p6_tokens():
    assert len(p8().pairs)==20
    assert set(p8().pairs)==set(p6().drafts)
    counts={}
    for row in p8().data["pairs"]:
        counts[row["scenario_id"]]=counts.get(row["scenario_id"],0)+1
    assert set(counts.values())=={5}

def test_p8_all_pairs_are_ablation_ready_and_no_route_decision():
    result=p8().evaluate_all(p6(),p7(),discourse(),stress(),suite())
    assert result["status"]=="PASS"
    assert result["pair_count"]==20
    assert result["ready_count"]==20
    assert result["blocker_count"]==0
    assert result["winner"] is None
    assert result["route_eliminated"] is False
    assert result["literary_superiority_claim"] is None

def test_p8_revised_texts_do_not_increase_p7_antipattern_counts():
    for token in p8().pairs:
        row=p8().pair(token,p6(),p7(),discourse(),stress(),suite())
        assert row["anti_patterns_after"]["total"] <= row["anti_patterns_before"]["total"]

def test_p8_strictly_repairs_the_five_most_engineered_p7_drafts():
    for token in p8().data["strict_reduction_tokens"]:
        row=p8().pair(token,p6(),p7(),discourse(),stress(),suite())
        assert row["anti_patterns_after"]["total"] < row["anti_patterns_before"]["total"]

def test_p8_preserves_route_probe_cell_and_focalizer_bindings():
    for token,spec in p8().pairs.items():
        base=p6().drafts[token]
        assert (spec["scenario_id"],spec["probe_id"],spec["cell_id"]) == (base["scenario_id"],base["probe_id"],base["cell_id"])
        card=discourse().card(spec["scenario_id"],spec["probe_id"],stress())
        assert base["primary_focalizer"]==card["sjuzet_plan"]["primary_focalizer"]

def test_p8_revised_texts_pass_existing_literary_machine_screen():
    for token in p8().pairs:
        row=p8().pair(token,p6(),p7(),discourse(),stress(),suite())
        assert row["literary_status"]!="REJECT_BEFORE_BLIND_READ"

def test_p8_integrity_and_authority_boundaries():
    assert p8().validate_integrity(p6(),p7(),discourse(),stress(),suite())==[]
    literary=LiteraryProductionRuntime.from_repo(ROOT)
    assert literary.data["stable_active"]["sha256"]==STABLE_SHA
    assert literary.data["stable_active"]["changed"] is False
    assert literary.data["chapter89"]["plock_manual_review"]=="PENDING"
    assert literary.data["chapter89"]["blind_read"]=="PENDING"


def test_p8_project_state_is_pass_and_records_gate_ci():
    from rcwh.io import load_data
    state=load_data(ROOT / "data" / "project_state" / "revision_ablation_v014.json")
    assert state["status"]=="PASS"
    assert state["authority"]=="SHADOW_ONLY"
    assert state["next_gate"]=="P9_PAIRED_BLIND_REVISION_REVIEW"
    assert set(state["effects"].values())=={"NONE"}
    assert state["ci"]=={
        "run_id":37659740928,
        "conclusion":"SUCCESS",
        "pytest":"301 passed / 0 failed",
        "validate":"PASS",
    }
