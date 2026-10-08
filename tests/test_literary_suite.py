from pathlib import Path
from copy import deepcopy
import hashlib
import json

import pytest

from rcwh.competition import CompetitionRegistry
from rcwh.literary_eval import evaluate_literary_candidate
from rcwh.literary_suite import LiteraryEvaluatorSuite


ROOT = Path(__file__).resolve().parents[1]


def suite() -> LiteraryEvaluatorSuite:
    return LiteraryEvaluatorSuite.from_repo(ROOT)


def test_suite_has_screening_authority_and_never_auto_passes():
    payload = suite().summary()
    assert payload["authority"] == "LITERARY_SCREENING_ONLY"
    assert payload["automatic_literary_pass"] is False


def test_culture_not_museum_deletion_test_flags_display_only_and_accepts_action_attachment():
    rt = suite()
    museum = rt.culture_deletion_test("琴棋书画，茶具香炉，古砚名帖，色色齐备。")
    assert museum["status"] == "FLAG_MUSEUM_RISK"
    assert museum["suspect_spans"]
    attached = rt.culture_deletion_test(
        "宝玉把旧砚收进匣里，麝月又把茶具洗净递给宝钗。"
    )
    assert attached["status"] == "PASS"
    assert attached["culture_spans"] >= 1


def test_explicit_exposition_detector_blocks_high_confidence_authorial_explanation():
    payload = suite().exposition_detector(
        "众人散后，作者又补一句：这正说明富贵不过一梦。"
    )
    assert payload["status"] == "FAIL_EXPLICIT_EXPOSITION"
    assert "这正说明" in payload["hits"]


def test_ambiguity_preservation_blocks_downstream_closure_of_open_evidence():
    payload = suite().ambiguity_preservation(
        "书中至此已经清楚：《十独吟》的作者就是黛玉。"
    )
    assert payload["status"] == "FAIL_AMBIGUITY_CLOSURE"
    assert payload["guard_hits"][0]["id"] == "ten-du-author-open"
    generic = suite().ambiguity_preservation("原稿一定如此，别无可说。")
    assert generic["status"] == "FAIL_AMBIGUITY_CLOSURE"


def test_structural_variation_flags_mechanical_uniformity_without_auto_failure():
    text = "\n\n".join(
        [
            "他进来。他坐下。他问话。他出去。",
            "她进来。她坐下。她问话。她出去。",
            "人进来。人坐下。人问话。人出去。",
            "客进来。客坐下。客问话。客出去。",
            "又进来。又坐下。又问话。又出去。",
            "再进来。再坐下。再问话。再出去。",
        ]
        * 8
    )
    payload = suite().structural_variation(text)
    assert payload["status"] == "FLAG_STRUCTURE_RISK"
    assert payload["automatic_failure"] is False
    assert payload["risks"]


def test_prose_suite_distinguishes_hard_blockers_from_human_flags():
    hard = suite().evaluate_prose("她终于明白人生的意义在于一切皆空。", "hard")
    assert hard["status"] == "REJECT_BEFORE_BLIND_READ"
    assert "EXPLICIT_EXPOSITION" in hard["blockers"]

    flagged = suite().evaluate_prose(
        ("琴棋书画，茶具香炉，古砚名帖，色色齐备。\n\n" * 30),
        "museum",
    )
    assert flagged["status"] == "READY_WITH_HUMAN_FLAGS"
    assert "CULTURE_MUSEUM_RISK" in flagged["human_flags"]
    assert flagged["automatic_literary_pass"] is False


def test_poetry_abc_lane_is_machine_screen_only_and_has_no_auto_winner():
    candidates = {
        "A": "竹影侵窗纸\n灯花落旧书\n小炉声渐歇\n夜久未闻呼",
        "B": "井水寒侵手\n旧衣补又穿\n门前人语近\n灯下线声迟",
        "C": "风动空庭竹\n茶凉半盏余\n旧笺收未竟\n月影过阶虚",
    }
    payload = suite().poetry_screen(candidates)
    assert payload["lane"] == "POETRY_A_B_C"
    assert payload["lane_status"] == "READY_FOR_BLIND_READ"
    assert len(payload["candidate_results"]) == 3
    assert payload["automatic_winner"] is False
    assert all(x["automatic_winner"] is False for x in payload["candidate_results"])
    assert all(x["automatic_literary_pass"] is False for x in payload["candidate_results"])


def test_poetry_lane_rejects_evidence_label_contamination_before_blind_read():
    candidates = {
        "A": "A-W1硬锁在此\n所以诗里照写",
        "B": "井水寒侵手\n旧衣补又穿",
        "C": "风动空庭竹\n茶凉半盏余",
    }
    payload = suite().poetry_screen(candidates)
    a = payload["candidate_results"][0]
    assert a["status"] == "REJECT_BEFORE_BLIND_READ"
    assert "EVIDENCE_LABEL_CONTAMINATION" in a["blockers"]
    assert payload["lane_status"] == "BLOCKED"


def test_poetry_blind_packet_contains_no_internal_labels_or_evidence_metadata():
    candidates = {
        "A": "竹影侵窗纸\n灯花落旧书",
        "B": "井水寒侵手\n旧衣补又穿",
        "C": "风动空庭竹\n茶凉半盏余",
    }
    packet = suite().poetry_blind_packet(candidates)
    assert packet["kind"] == "POETRY_BLIND_READ"
    assert packet["sealed"] is True
    assert suite().blind_output_violations(packet) == []
    assert all(set(x) == {"token", "text"} for x in packet["candidates"])
    rendered = str(packet)
    assert "internal_label" not in rendered
    assert "P-Lock" not in rendered
    assert "A-W1" not in rendered
    assert "六字段" not in rendered


def test_ch89_blind_packet_is_separate_from_competition_evidence_and_candidate_labels():
    competitions = CompetitionRegistry.from_repo(ROOT)
    record = competitions.records["comp:43-0:ch89:pressure-test"]
    packet = suite().competition_blind_packet(record)
    assert packet["kind"] == "LITERARY_BLIND_READ"
    assert packet["chapter"] == 89
    assert {x["token"] for x in packet["candidates"]} == {"BR-14", "BR-58", "BR-91"}
    assert all(set(x) == {"token", "text", "sha256"} for x in packet["candidates"])
    assert suite().blind_output_violations(packet) == []
    rendered = str(packet)
    for leaked in (
        "ch89-A",
        "ch89-B",
        "ch89-C",
        "plock:ch89",
        "PROVENANCE",
        "machine_expected_status",
        "SIX_FIELD_REGRESSION",
    ):
        assert leaked not in rendered


def test_existing_literary_candidate_pipeline_includes_v05_suite_without_auto_promotion():
    text = (
        ROOT / "artifacts/43-0/ch89/candidates/ch89_B_full.md"
    ).read_text(encoding="utf-8")
    payload = evaluate_literary_candidate(
        ROOT,
        "plock:ch89:small-life-after-confiscation",
        text,
        "ch89-B",
    )
    assert payload["machine_status"] == "READY_FOR_BLIND_READ"
    assert payload["literary_suite"]["status"] in {
        "READY_FOR_BLIND_READ",
        "READY_WITH_HUMAN_FLAGS",
    }
    assert payload["literary_suite"]["automatic_literary_pass"] is False
    assert payload["promotion_eligible"] is False


def test_issue5_suite_integrity_passes_current_competitions():
    assert suite().validate_integrity(CompetitionRegistry.from_repo(ROOT)) == []


@pytest.mark.parametrize("chapter", [86, 89])
def test_blind_export_is_exact_anonymous_and_refuses_existing_directory(tmp_path, chapter):
    record = CompetitionRegistry.from_repo(ROOT).records[f"comp:43-0:ch{chapter}:pressure-test"]
    target = tmp_path / "review"
    packet = suite().competition_blind_packet(record, target)
    assert json.loads((target / "packet.json").read_text()) == packet
    originals = {c["blind_token"]: (ROOT / c["artifact"]["path"]).read_bytes() for c in record["candidates"]}
    assert {p.name for p in target.iterdir()} == {"packet.json", *(f"{token}.md" for token in originals)}
    for item in packet["candidates"]:
        assert set(item) == {"token", "artifact", "sha256"}
        raw = (target / item["artifact"]).read_bytes()
        assert raw == originals[item["token"]]
        assert hashlib.sha256(raw).hexdigest() == item["sha256"]
    assert suite().blind_output_violations(packet) == []
    with pytest.raises(FileExistsError):
        suite().competition_blind_packet(record, target)
    assert json.loads((target / "packet.json").read_text()) == packet


@pytest.mark.parametrize("fault", ["identity", "token_path", "duplicate_token"])
def test_invalid_blind_input_is_rejected_before_export(tmp_path, fault):
    record = deepcopy(CompetitionRegistry.from_repo(ROOT).records["comp:43-0:ch89:pressure-test"])
    if fault == "identity":
        record["candidates"][0]["artifact"]["git_blob_sha"] = "0" * 40
    elif fault == "token_path":
        record["candidates"][0]["blind_token"] = "../identity"
    else:
        record["candidates"][1]["blind_token"] = record["candidates"][0]["blind_token"]
    target = tmp_path / "review"
    with pytest.raises(ValueError):
        suite().competition_blind_packet(record, target)
    assert not target.exists()
