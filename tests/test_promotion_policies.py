import json
from pathlib import Path

import pytest

from rcwh.promotion import load_promotion_policy, policy_supported
from rcwh.schema import validate_instance


ROOT = Path(__file__).resolve().parents[1]


def test_only_legacy_ch86_policy_is_declared_and_schema_valid():
    paths = list((ROOT / "data/promotion/policies").glob("*.json"))
    assert [p.name for p in paths] == ["ch86.json"]
    policy = load_promotion_policy(ROOT, 86)
    assert validate_instance(policy, ROOT / "schemas/promotion_policy.schema.json") == []
    assert policy_supported(policy, 86, {86}, "plock:ch86:cold-medicine")
    assert len(policy["required_book_strings"]) == 12
    assert policy["forbidden_book_strings"] == ["警幻情榜"]
    assert len(policy["carry_over_anchors"]) == 4


@pytest.mark.parametrize("chapter,changed,plock", [
    (89, {89}, "plock:ch86:cold-medicine"),
    (86, {86, 89}, "plock:ch86:cold-medicine"),
    (86, {89}, "plock:ch86:cold-medicine"),
    (86, {86}, "plock:ch89:other"),
])
def test_exact_chapter_policy_preconditions(chapter, changed, plock):
    assert not policy_supported(load_promotion_policy(ROOT, 86), chapter, changed, plock)


def test_unknown_or_unsupported_policy_never_grants_safety_pass():
    policy = load_promotion_policy(ROOT, 86)
    for key, value in (("status", "UNKNOWN"), ("evaluator", "DECLARED_PASS")):
        unsupported = {**policy, key: value}
        assert not policy_supported(unsupported, 86, {86}, "plock:ch86:cold-medicine")
    assert load_promotion_policy(ROOT, 89) is None
    assert not policy_supported(None, 89, {89}, "plock:ch89:other")


def test_invalid_policy_record_is_not_treated_as_pass(tmp_path):
    directory = tmp_path / "data/promotion/policies"
    directory.mkdir(parents=True)
    (tmp_path / "schemas").mkdir()
    (tmp_path / "schemas/promotion_policy.schema.json").write_bytes((ROOT / "schemas/promotion_policy.schema.json").read_bytes())
    policy = load_promotion_policy(ROOT, 86)
    policy["chapter"] = 89
    (directory / "ch86.json").write_text(json.dumps(policy), encoding="utf-8")
    with pytest.raises(ValueError, match="chapter mismatch"):
        load_promotion_policy(tmp_path, 86)


def test_ch86_data_extraction_preserves_frozen_content_regression():
    from rcwh.promotion import PromotionRegistry
    registry = PromotionRegistry.from_repo(ROOT)
    record = registry.records["promotion:ch86:b:v1-5-candidate"]
    report = registry.evaluate(ROOT, record["id"])
    assert report["overall"] == "PENDING"
    assert report["gates"] == {
        "COMPETITION_ELIGIBILITY": "PENDING", "EVIDENCE_CORE": "PASS", "BASELINE_IDENTITY": "PASS",
        "BOOK_STRUCTURE": "PASS", "NON_TARGET_INTEGRITY": "PASS", "R4F_HARD_INTERFACES": "PASS",
        "PLOCK": "PASS", "STABLE_POINTER_UNCHANGED": "PASS",
    }
    assert report["pending_checks"] == ["COMPETITION_ELIGIBILITY"]
    assert report["pending_reasons"] == []
    assert report["findings"] == []
    assert report["candidate_sha256"] == record["candidate"]["sha256"]
