"""Additive policy tests; no generated chapter policies or release integration."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil

import pytest

from rcwh.agent_policies import derive_agent_anchors, evaluate_agent_policy, validate_agent_policy
from rcwh.assets import AssetCatalog
from rcwh.io import load_data
from rcwh.promotion import load_promotion_policy, policy_supported
from rcwh.schema import validate_instance


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas/agent_chapter_policy.schema.json"


@pytest.fixture
def rules(tmp_path):
    for directory in ("data/provenance", "data/literals", "data/plocks", "data/implementation_alignment",
                      "data/promotion/policies"):
        shutil.copytree(ROOT / directory, tmp_path / directory)
    (tmp_path / "data/project").mkdir()
    (tmp_path / "schemas").mkdir()
    for path in ("data/project/scope.json", "schemas/project_scope.schema.json"):
        shutil.copyfile(ROOT / path, tmp_path / path)
    return tmp_path


def candidate(chapter, body="正文。", title="工作回目可变"):
    return f"# 第{chapter}回 {title}\n\n{body}\n"


def stable_chapter(chapter):
    m6 = load_data(ROOT / "data/implementation_alignment/m6.json")
    row = next(row for row in m6["stable_release"]["chapters"] if row["chapter"] == chapter)
    raw = AssetCatalog.from_repo(ROOT).resolve(m6["stable_release"]["asset_ref"]).path.read_bytes()
    return b"".join(raw.splitlines(keepends=True)[row["line_start"] - 1:row["line_end"]])


@pytest.mark.parametrize("chapter", range(81, 101))
def test_projection_schema_and_byte_bound_local_pointers(chapter):
    policy = derive_agent_anchors(ROOT, chapter)
    assert validate_instance(policy, SCHEMA) == []
    assert validate_agent_policy(ROOT, policy, chapter) == []
    assert policy["qualification"] == "MODEL" and policy["authority_effect"] == "NONE"
    bindings = {item["path"]: item["sha256"] for item in policy["inputs"]}
    for item in policy["anchors"] + policy["forbidden"] + policy["semantic_obligations"]:
        for ref in item["basis"]:
            assert ref["chapter"] == chapter
            assert ref["sha256"] == bindings[ref["path"]]
            assert ref["sha256"] == hashlib.sha256((ROOT / ref["path"]).read_bytes()).hexdigest()
            value = load_data(ROOT / ref["path"])
            for token in ref["pointer"].split("/")[1:]:
                token = token.replace("~1", "/").replace("~0", "~")
                value = value[int(token)] if isinstance(value, list) else value[token]


@pytest.mark.parametrize("chapter", [86, 89, 92, 97, 100])
def test_plock_has_no_opt_out_or_projection_removal(chapter):
    policy = derive_agent_anchors(ROOT, chapter)
    assert policy["plock"]["required"]
    fields = ["plock", "semantic_obligations"] + (["anchors"] if policy["anchors"] else [])
    for field in fields:
        broken = deepcopy(policy)
        broken[field] = {"required": False, "ref": None, "basis": []} if field == "plock" else []
        assert validate_agent_policy(ROOT, broken, chapter)
    broken = deepcopy(policy)
    broken["plock"]["ref"] = "plock:ch86:other"
    assert validate_agent_policy(ROOT, broken, chapter)


def test_missing_frozen_registry_cannot_yield_empty_anchor_pass(rules):
    shutil.rmtree(rules / "data/literals")
    with pytest.raises(ValueError, match="frozen rule registry missing"):
        derive_agent_anchors(rules, 87)


def test_missing_required_lock_is_not_an_unprotected_policy(rules):
    file = rules / "data/plocks/r4_literary.yaml"
    file.write_text("literary_locks: []\n", encoding="utf-8")
    with pytest.raises(ValueError, match="mandatory P-Lock"):
        derive_agent_anchors(rules, 92)


def test_chapter_mismatch_and_cross_chapter_pointer_cannot_pass():
    policy = derive_agent_anchors(ROOT, 87)
    assert validate_agent_policy(ROOT, policy, 88) == ["agent policy chapter mismatch"]
    broken = deepcopy(policy)
    broken["chapter"] = 88
    assert validate_agent_policy(ROOT, broken, 88)
    broken = deepcopy(policy)
    broken["anchors"][0]["basis"][0]["pointer"] = "/literal_constraints/2/text"
    assert validate_agent_policy(ROOT, broken, 87)
    assert evaluate_agent_policy(ROOT, policy, 87, candidate(88))["status"] == "FAIL"


def test_stale_input_bytes_and_missing_hashes_fail(rules):
    policy = derive_agent_anchors(rules, 87)
    source = rules / "data/literals/r4_literal_core.yaml"
    source.write_bytes(source.read_bytes() + b"\n# byte-only change\n")
    assert any("inputs" in error for error in validate_agent_policy(rules, policy, 87))
    policy = derive_agent_anchors(rules, 87)
    policy["inputs"].pop()
    assert validate_agent_policy(rules, policy, 87)


def test_source_only_is_neither_anchor_nor_substring_ban():
    policy = derive_agent_anchors(ROOT, 100)
    assert not any("警幻情榜" in item["texts"] for item in policy["anchors"])
    assert not any("source-phrase" in str(item["rule"]) for item in policy["forbidden"])
    assert any(item["kind"] == "SOURCE_ONLY" and item["rule"]["text"] == "警幻情榜"
               for item in policy["semantic_obligations"])
    raw = stable_chapter(100).decode("utf-8")
    raw = raw.replace("石在，字在。", "警幻情榜只作为讨论词出现。石在，字在。")
    report = evaluate_agent_policy(ROOT, policy, 100, raw)
    assert report["anchor_status"] == "PASS"
    assert report["status"] == "PASS" and report["semantic_status"] == "NOT_IMPLEMENTED"
    # Legacy explicit book sentinel is left in its old exact gate, not silently
    # generalized into all chapter-local SOURCE_ONLY bans.
    legacy = load_promotion_policy(ROOT, 86)
    assert legacy["forbidden_book_strings"] == ["警幻情榜"]


@pytest.mark.parametrize("chapter", [86, 89, 92, 97, 100])
def test_actual_baseline_anchor_pass_is_a_research_policy_pass(chapter):
    policy = derive_agent_anchors(ROOT, chapter)
    policy["status"] = "PASS"
    report = evaluate_agent_policy(ROOT, policy, chapter, stable_chapter(chapter))
    assert report["anchor_status"] == "PASS", report["findings"]
    # Unimplemented semantic reading is reported as INFO, not a holding gate.
    assert report["status"] == report["chapter_safety_status"] == "PASS"
    assert report["semantic_status"] == "NOT_IMPLEMENTED"
    assert report["automatic_policy_pass"] is False


def test_ch89_terminal_scene_not_expanded_to_character_level_suffix():
    policy = derive_agent_anchors(ROOT, 89)
    report = evaluate_agent_policy(ROOT, policy, 89, stable_chapter(89))
    # Original rule /literary_locks/1/exact_anchors/0 says P1_TERMINAL,
    # not no-following-characters. 麝月's same-scene reply is not machine FAIL.
    assert report["anchor_status"] == "PASS" and report["status"] == "PASS"
    item = next(item for item in policy["semantic_obligations"] if item["kind"] == "TERMINAL_PLACEMENT")
    assert item["basis"][0]["pointer"] == "/literary_locks/1/exact_anchors/0"
    assert item["rule"]["mode"] == "P1_TERMINAL"


@pytest.mark.parametrize("chapter", [86, 100])
def test_terminal_function_and_explanatory_tail_remain_semantic(chapter):
    policy = derive_agent_anchors(ROOT, chapter)
    raw = stable_chapter(chapter).decode("utf-8")
    report = evaluate_agent_policy(ROOT, policy, chapter, raw + "\n作者解释。\n")
    assert report["anchor_status"] == "PASS"
    assert report["semantic_status"] == "NOT_IMPLEMENTED" and report["chapter_safety_status"] == "PASS"
    assert any(item["kind"] == "TERMINAL_PLACEMENT" for item in policy["semantic_obligations"])
    if chapter == 100:
        assert any(item["basis"][0]["pointer"] == "/literary_locks/4/forbidden_drift/1"
                   for item in policy["forbidden"])


def test_required_prose_literal_not_satisfied_by_heading_only():
    policy = derive_agent_anchors(ROOT, 87)
    text = candidate(87, title="落叶萧萧，寒烟漠漠")
    assert evaluate_agent_policy(ROOT, policy, 87, text)["anchor_status"] == "FAIL"


def test_source_and_m6_title_variants_not_baseline_only():
    policy = derive_agent_anchors(ROOT, 90)
    item = next(item for item in policy["anchors"] if item["mode"] == "HEADING_EXACT")
    assert set(item["texts"]) == {"薛宝钗借词含讽谏，王熙凤知命强英雄", "薛宝钗借词含讽谏　王熙凤知命强英雄"}
    for title in item["texts"]:
        assert evaluate_agent_policy(ROOT, policy, 90, candidate(90, title=title))["anchor_status"] == "PASS"
    assert evaluate_agent_policy(ROOT, policy, 90, candidate(90, title="改掉原字"))["anchor_status"] == "FAIL"
    policy = derive_agent_anchors(ROOT, 88)
    assert not any(item["mode"] == "HEADING_EXACT" for item in policy["anchors"])
    text = candidate(88, "好歹留着麝月。", "花袭人有始有终　另一半工作回目")
    assert evaluate_agent_policy(ROOT, policy, 88, text)["anchor_status"] == "PASS"
    policy = derive_agent_anchors(ROOT, 81)
    assert evaluate_agent_policy(ROOT, policy, 81, candidate(81, title="新工作回目"))["anchor_status"] == "PASS"


def test_free_text_and_unknown_modes_are_obligations_not_machine_pass(rules):
    file = rules / "data/plocks/r4_literary.yaml"
    text = file.read_text(encoding="utf-8").replace("mode: P1_DIALOGUE", "mode: UNKNOWN", 1)
    file.write_text(text, encoding="utf-8")
    policy = derive_agent_anchors(rules, 86)
    assert any(item["kind"] == "UNKNOWN" for item in policy["semantic_obligations"])
    assert any(item["kind"] == "FORBIDDEN_DRIFT" for item in policy["semantic_obligations"])
    policy["status"] = "UNKNOWN"
    report = evaluate_agent_policy(rules, policy, 86, stable_chapter(86))
    assert report["anchor_status"] == "PASS"
    assert report["status"] == "PASS"
    broken = deepcopy(policy)
    broken["semantic_obligations"][0]["status"] = "PASS"
    assert validate_agent_policy(rules, broken, 86)


def test_unknown_literal_value_is_never_a_matched_anchor(rules):
    file = rules / "data/literals/r4_literal_core.yaml"
    file.write_text(file.read_text(encoding="utf-8").replace("text: 落叶萧萧，寒烟漠漠", "text: UNKNOWN"), encoding="utf-8")
    policy = derive_agent_anchors(rules, 87)
    assert not any("UNKNOWN" in item["texts"] for item in policy["anchors"])
    assert any(item["kind"] == "UNKNOWN" for item in policy["semantic_obligations"])
    report = evaluate_agent_policy(rules, policy, 87, candidate(87, "UNKNOWN"))
    assert report["anchor_status"] == "PASS" and report["status"] == "PASS"


def test_bound_declared_review_status_is_not_a_dedicated_reading(rules):
    policy = derive_agent_anchors(rules, 81)
    raw = json.dumps({"status": "PASS", "chapter": 81, "claim": "semantic reading done"}).encode()
    (rules / "review.json").write_bytes(raw)
    policy["review_refs"] = [{"path": "review.json", "sha256": hashlib.sha256(raw).hexdigest()}]
    policy["status"] = "PASS"
    assert validate_agent_policy(rules, policy, 81) == []
    report = evaluate_agent_policy(rules, policy, 81, candidate(81))
    assert report["status"] == "PASS"  # Machine anchors only; declaration grants nothing extra.
    assert not report["review_refs_verified_as_readings"]
    (rules / "review.json").write_bytes(b"{}")
    assert validate_agent_policy(rules, policy, 81)


def test_invalid_schema_and_unsafe_review_ref_fail(rules):
    policy = derive_agent_anchors(rules, 81)
    policy["authority_effect"] = "EVIDENCE"
    assert validate_agent_policy(rules, policy, 81)
    policy = derive_agent_anchors(rules, 81)
    policy["review_refs"] = [{"path": "../escape", "sha256": "0" * 64}]
    assert validate_agent_policy(rules, policy, 81)


def test_legacy_exact_changed_set_preconditions_remain_unchanged():
    policy = load_promotion_policy(ROOT, 86)
    assert policy_supported(policy, 86, {86}, "plock:ch86:cold-medicine")
    assert not policy_supported(policy, 86, {86, 89}, "plock:ch86:cold-medicine")
    assert not policy_supported(policy, 89, {89}, "plock:ch86:cold-medicine")


def test_plock_anchor_loss_is_replaceable_advisory_but_evidence_literal_blocks():
    policy = derive_agent_anchors(ROOT, 100)
    raw = stable_chapter(100).decode("utf-8")
    report = evaluate_agent_policy(ROOT, policy, 100, raw.replace("石在，字在。", "石头还在。"),
                                   replacement_reason="competing ending reviewed")
    assert report["status"] == "PASS" and report["anchor_status"] == "REPLACEMENT_CASE"
    assert report["replacement_reason"] == "competing ending reviewed"
    assert {f["severity"] for f in report["graded_findings"]} == {"ADVISORY"}
    # 情不情 is a NOVEL_EXACT literal backed by an A-W1 LOCKED decision.
    report = evaluate_agent_policy(ROOT, policy, 100, raw.replace("情不情", "情痴"))
    assert report["status"] == "FAIL" and report["anchor_status"] == "FAIL"
    assert "BLOCKING" in {f["severity"] for f in report["graded_findings"]}
