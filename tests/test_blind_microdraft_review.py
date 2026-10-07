from pathlib import Path
from rcwh.blind_microdraft_review import BlindMicrodraftReviewRuntime
from rcwh.microdraft import ControlledMicrodraftRuntime
from rcwh.literary_production import LiteraryProductionRuntime, STABLE_SHA
ROOT=Path(__file__).resolve().parents[1]
def p7(): return BlindMicrodraftReviewRuntime.from_repo(ROOT)
def p6(): return ControlledMicrodraftRuntime.from_repo(ROOT)

def test_p7_covers_all_twenty_p6_tokens_and_five_rankings():
    assert len(p7().data["reviews"])==20
    assert {x["token"] for x in p7().data["reviews"]}==set(p6().drafts)
    assert set(p7().data["cell_rankings"])=={"W1","W2","W3","W4","W5"}

def test_p7_rankings_match_top2_flags():
    for cid,ranking in p7().data["cell_rankings"].items():
        assert len(ranking)==4 and len(set(ranking))==4
        for rank,token in enumerate(ranking,1):
            row=next(x for x in p7().data["reviews"] if x["token"]==token)
            assert row["rank"]==rank
            assert row["top2"]==(rank<=2)

def test_p7_descriptive_route_summary_is_not_a_winner_selection():
    s=p7().data["scenario_summary"]
    assert s["SCN-CURRENT-C"]["rank_sum"]==11
    assert s["SCN-MINIMAL-CAUSE-OPEN"]["rank_sum"]==11
    assert s["SCN-LATE-MARRIAGE"]["rank_sum"]==12
    assert s["SCN-JADE-MULTILAYER"]["rank_sum"]==16
    assert p7().data["interpretation_policy"]["rank_sum_is_descriptive_only"] is True
    assert p7().data["interpretation_policy"]["one_reviewer_can_select_route"] is False
    assert p7().summary()["winner"] is None

def test_p7_keeps_jade_route_for_targeted_repair_not_elimination():
    row=p7().data["scenario_summary"]["SCN-JADE-MULTILAYER"]
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

def test_p7_integrity_and_canonical_authority_unchanged():
    assert p7().validate_integrity(p6())==[]
    literary=LiteraryProductionRuntime.from_repo(ROOT)
    assert literary.data["stable_active"]["sha256"]==STABLE_SHA
    assert literary.data["stable_active"]["changed"] is False
    assert literary.data["chapter89"]["plock_manual_review"]=="PENDING"
    assert literary.data["chapter89"]["blind_read"]=="PENDING"
