from pathlib import Path
import pytest
from rcwh.revision_ablation import CrossRouteRevisionAblationRuntime
from rcwh.microdraft import ControlledMicrodraftRuntime
from rcwh.blind_microdraft_review import BlindMicrodraftReviewRuntime
from rcwh.narrative_discourse import NarrativeDiscourseRuntime
from rcwh.literary_stress import ScenarioLiteraryStressRuntime
from rcwh.literary_suite import LiteraryEvaluatorSuite
ROOT=Path(__file__).resolve().parents[1]
def p8(): return CrossRouteRevisionAblationRuntime.from_repo(ROOT)
def p6(): return ControlledMicrodraftRuntime.from_repo(ROOT)
def p7(): return BlindMicrodraftReviewRuntime.from_repo(ROOT)
def discourse(): return NarrativeDiscourseRuntime.from_repo(ROOT)
def stress(): return ScenarioLiteraryStressRuntime.from_repo(ROOT)
def suite(): return LiteraryEvaluatorSuite.from_repo(ROOT)

def test_p8_pairs_cover_all_p6_tokens():
    assert set(p8().pairs)==set(p6().drafts)

def test_p8_all_pairs_are_ablation_ready_and_no_route_decision():
    result=p8().evaluate_all(p6(),p7(),discourse(),stress(),suite())
    assert result["status"]=="PASS"
    assert result["pair_count"]==len(p6().drafts)
    assert result["ready_count"]==len(p6().drafts)
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
        row=p8().pair(token,p6(),p7(),discourse(),stress(),suite())
        assert (row["scenario_id"],row["probe_id"],row["cell_id"]) == (base["scenario_id"],base["probe_id"],base["cell_id"])
        card=discourse().card(row["scenario_id"],row["probe_id"],stress())
        assert base["primary_focalizer"]==card["sjuzet_plan"]["primary_focalizer"]

def test_p8_revised_texts_pass_existing_literary_machine_screen():
    for token in p8().pairs:
        row=p8().pair(token,p6(),p7(),discourse(),stress(),suite())
        assert row["literary_status"]!="REJECT_BEFORE_BLIND_READ"

def test_p8_integrity_and_authority_boundaries(production_unchanged):
    assert p8().validate_integrity(p6(),p7(),discourse(),stress(),suite())==[]


@pytest.mark.parametrize("fault", ["baseline_identity", "baseline_content", "review_identity", "review_content"])
def test_revision_cannot_silently_follow_changed_upstream_records(fault):
    lab, review, revision = p6(), p7(), p8()
    if fault == "baseline_identity":
        lab.data["id"] += ":changed"
    elif fault == "baseline_content":
        next(iter(lab.drafts.values()))["scenario_id"] += "-changed"
    elif fault == "review_identity":
        review.data["id"] += ":changed"
    else:
        review.data["revision_targets"][0]["note"] = "changed after revision"
    with pytest.raises(ValueError, match="snapshot binding drift"):
        revision.pair(next(iter(revision.pairs)), lab, review, discourse(), stress(), suite())
    assert revision.validate_integrity(lab, review, discourse(), stress(), suite())
