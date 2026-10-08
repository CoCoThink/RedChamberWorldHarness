from pathlib import Path
from copy import deepcopy
import shutil
import pytest
from rcwh.blind_microdraft_review import BlindMicrodraftReviewRuntime
from rcwh.microdraft import ControlledMicrodraftRuntime
ROOT=Path(__file__).resolve().parents[1]
def p7(): return BlindMicrodraftReviewRuntime.from_repo(ROOT)
def p6(): return ControlledMicrodraftRuntime.from_repo(ROOT)

def test_p7_covers_all_twenty_p6_tokens_and_five_rankings():
    assert {x["token"] for x in p7().data["reviews"]}==set(p6().drafts)
    assert set(p7().data["cell_rankings"])=={x["cell_id"] for x in p6().drafts.values()}

def test_p7_rankings_match_top2_flags():
    for cid,ranking in p7().data["cell_rankings"].items():
        assert ranking and len(ranking)==len(set(ranking))
        for rank,token in enumerate(ranking,1):
            row=p7().token(token)
            assert row["rank"]==rank
            assert row["top2"]==(rank<=2)

def test_p7_descriptive_route_summary_is_not_a_winner_selection():
    s=p7().summary()["scenario_summary"]
    assert s["SCN-CURRENT-C"]["rank_sum"]==11
    assert s["SCN-MINIMAL-CAUSE-OPEN"]["rank_sum"]==11
    assert s["SCN-LATE-MARRIAGE"]["rank_sum"]==12
    assert s["SCN-JADE-MULTILAYER"]["rank_sum"]==16
    assert p7().data["interpretation_policy"]["rank_sum_is_descriptive_only"] is True
    assert p7().data["interpretation_policy"]["one_reviewer_can_select_route"] is False
    assert p7().summary()["winner"] is None

def test_p7_keeps_jade_route_for_targeted_repair_not_elimination():
    row=p7().scenario("SCN-JADE-MULTILAYER")["summary"]
    assert row["status"]=="KEEP_FOR_TARGETED_REPAIR"
    assert row["first_place_count"]==1
    assert row["top2_count"]==1
    assert p7().data["policy"]["automatic_route_elimination"] is False

def test_p7_extracts_global_revision_controls_from_review():
    ids={x["id"] for x in p7().data["revision_targets"]}
    assert {"RT-01","RT-02","RT-03","RT-04","RT-05"}.issubset(ids)
    assert p7().data["cross_cell_findings"]["dominant_strategy"].startswith("以家务、饭药钱")

def test_p7_raw_review_is_preserved_and_mapping_unsealed_only_after_review():
    raw=p7().raw_review()
    assert "MD-W4-43" in raw
    assert "时间线核对表" in raw
    assert "跨 cell 总体观察" in raw
    assert p7().data["source_basis"]["mapping_unsealed_after_review"] is True

def test_p7_integrity_and_canonical_authority_unchanged(production_unchanged):
    assert p7().validate_integrity(p6())==[]


@pytest.mark.parametrize("field", ["scenario_id", "probe_id", "cell_id", "primary_focalizer", "artifact"])
def test_review_rejects_rebinding_a_reviewed_draft(field):
    lab = p6()
    token = next(iter(lab.drafts))
    lab.drafts[token][field] = "changed-after-review"
    assert p7().validate_integrity(lab)
    with pytest.raises((ValueError, OSError), match="snapshot|changed-after-review"):
        p7().mapping(lab)


def test_review_rejects_changed_prose_even_when_mapping_is_unchanged(tmp_path):
    lab = p6()
    for spec in lab.drafts.values():
        target = tmp_path / spec["artifact"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / spec["artifact"], target)
    lab.root = tmp_path
    assert p7().mapping(lab)
    original_mapping = deepcopy(lab.data["drafts"])
    path = tmp_path / next(iter(lab.drafts.values()))["artifact"]
    path.write_bytes(path.read_bytes() + "\n新添一句。".encode())
    assert lab.data["drafts"] == original_mapping
    with pytest.raises(ValueError, match="snapshot binding drift"):
        p7().mapping(lab)


def test_blind_mapping_cannot_be_unsealed_before_review():
    review = p7()
    review.data["source_basis"]["mapping_unsealed_after_review"] = False
    with pytest.raises(ValueError, match="only be unsealed after review"):
        review.mapping(p6())


def test_rank_edits_update_token_and_scenario_views_without_duplicate_statistics():
    review = p7()
    ranking = next(iter(review.data["cell_rankings"].values()))
    first, last = ranking[0], ranking[-1]
    scenario_id = review.token(first)["scenario_id"]
    before = review.scenario(scenario_id)["summary"]
    ranking[0], ranking[-1] = last, first
    assert review.token(first)["rank"] == len(ranking)
    assert review.token(first)["top2"] is False
    after = review.summary()["scenario_summary"][scenario_id]
    assert after["rank_sum"] == before["rank_sum"] + len(ranking) - 1
    assert after["first_place_count"] == before["first_place_count"] - 1
    assert after["top2_count"] == before["top2_count"] - 1
    assert after["note"] == before["note"]


def test_qualified_verdict_keeps_original_wording_and_declared_category():
    review = p7()
    original = next(row for row in review.data["reviews"] if row["verdict"] == "EDGE(偏弱)")
    row = review.token(original["token"])
    assert row["verdict"] == "EDGE(偏弱)"
    scenario = review.scenario(row["scenario_id"])
    assert scenario["summary"]["verdict_counts"]["EDGE"] == sum(
        review.data["verdict_categories"][r["verdict"]] == "EDGE" for r in scenario["cells"])


@pytest.mark.parametrize("fault", ["duplicate", "missing", "wrong_cell", "unknown_verdict"])
def test_review_rejects_ambiguous_or_incomplete_rankings(fault):
    review = p7()
    first, second = list(review.data["cell_rankings"].values())[:2]
    if fault == "duplicate":
        first.append(first[0])
    elif fault == "missing":
        first.pop()
    elif fault == "wrong_cell":
        first[0], second[0] = second[0], first[0]
    else:
        review.data["reviews"][0]["verdict"] = "UNCLASSIFIED"
    with pytest.raises(ValueError):
        review.summary()
