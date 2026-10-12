"""Small, deterministic fixtures: never rebuild the production corpus by default."""
import argparse
import json
import os
from pathlib import Path

import pytest

from rcwh.application import diagnostics
from rcwh.assets import AssetCatalog, AssetError
from rcwh.candidate_reviews import digest
from rcwh.evaluation.style import style_diagnostics
from rcwh.evaluation import style_reference as sr

ROOT = Path(__file__).resolve().parents[1]
DATASET = "corpus:tiny-style:v1"


def _segment(chapter, text, kind="MAIN_TEXT", identity=None):
    return {"chapter": chapter, "text": text, "kind": kind,
            "segment_id": identity or f"tiny:{chapter}:{digest(text.encode())[:12]}"}


@pytest.fixture
def tiny_corpus(tmp_path, monkeypatch):
    """Real catalog byte verification, patched repository/audit contract endpoints."""
    manifest = {"dataset_ref": DATASET, "readiness": "CANDIDATE_PENDING_HUMAN_AUDIT",
                "build_config": {"document": {"chapters": [1, 2, 3, 4]}}}
    raw = json.dumps(manifest).encode()
    path = tmp_path / "manifest.json"
    path.write_bytes(raw)
    ref = "asset:sha256:" + digest(raw)
    catalog = AssetCatalog(tmp_path, {ref: {"path": "manifest.json", "sha256": digest(raw), "bytes": len(raw)}}, {})
    binding = {"manifest_ref": ref, "manifest_sha256": digest(raw)}
    segments = [_segment(1, "了甲“的乙”"), _segment(2, "了了甲甲“的的乙乙”"),
                _segment(3, "甲甲“乙乙”"), _segment(4, "了了了甲“的的的乙”"),
                _segment(1, "然后然后然后了了了“姑娘姑娘”", "ZHIPI"),
                _segment(1, "然后然后", "EDITORIAL"), _segment(2, "然后然后", "VARIANT"),
                _segment(None, "然后然后", "APPENDIX"), _segment(4, "然后然后", "UNCLASSIFIED")]
    calls = []
    state = {"status": "PENDING", "manifest": manifest, "binding": binding, "segments": segments}
    monkeypatch.setattr(sr.AssetCatalog, "from_repo", classmethod(lambda cls, root: catalog))
    monkeypatch.setattr(sr.CorpusRepository, "registry", lambda self: {DATASET: state["binding"]})

    def load(self, dataset_ref, *, rebuild=True):
        calls.append(("load", dataset_ref, rebuild))
        lines = [{"record_type": "FILE_SCOPE"}, *state["segments"]]
        return state["manifest"], {"segments.jsonl": b"\n".join(json.dumps(row, ensure_ascii=False).encode() for row in lines)}

    def summary(self, dataset_ref, *, rebuild=True):
        calls.append(("audit", dataset_ref, rebuild))
        return {"status": state["status"], "review_count": 0, "authority_effect": "NONE"}

    monkeypatch.setattr(sr.CorpusRepository, "load", load)
    monkeypatch.setattr(sr.CorpusAudit, "summary", summary)
    return tmp_path, state, calls


def test_default_diagnostics_byte_compatible_with_legacy_output():
    text = "第八十六回  守残灯侍儿误候  留冷药痴子来迟\n\n话说宝玉道：“姑娘，且说给我听。”"
    poem = "灯下无人语，窗前有旧书。"
    expected = {
        "report_kind": "COMPUTED_CHECK", "scope": "STYLE_OBSERVATIONS", "status": "OBSERVED",
        "candidate_sha256": digest(text.encode()), "character_count": len(text),
        "title_track": {"title": "守残灯侍儿误候  留冷药痴子来迟", "halves": ["守残灯侍儿误候", "留冷药痴子来迟"],
                        "han_lengths": [7, 7], "equal_length": True,
                        "semantic_parallelism": "PENDING_READING", "chapter_function": "PENDING_READING"},
        "prose_track": {"paragraph_lengths": [23, 17], "quoted_utterances": 1,
                        "narrator_markers": {"话说": 1, "且说": 0, "却说": 0, "原来": 0, "不在话下": 0, "欲知后事": 0},
                        "address_forms": {"姑娘": 1}, "address_relationship_consistency": "PENDING_ATTRIBUTED_READING"},
        "poetry_track": [{"text_sha256": digest(poem.encode()), "verses": ["灯下无人语", "窗前有旧书"],
                          "line_lengths": [5, 5], "rhyme_and_tonal_pattern": "PENDING_EXPERT_READING", "voice": "PENDING_EXPERT_READING"}],
        "reference_distribution": "UNAVAILABLE_UNTIL_CORPUS_AUDITED",
        "literary_quality_verified": False, "authority_effect": "NONE"}
    serialize = lambda report: json.dumps(report, ensure_ascii=False, indent=2)
    assert serialize(style_diagnostics(text, [poem])) == serialize(expected)
    assert serialize(style_diagnostics(text, [poem], reference=None)) == serialize(expected)


def test_small_corpus_rates_quantiles_and_main_text_only(tiny_corpus):
    root, state, calls = tiny_corpus
    profile = sr.reference_profile(root, DATASET)
    assert calls == [("load", DATASET, False), ("audit", DATASET, False)]
    assert profile["chapter_count"] == 4
    assert profile["main_text_segment_count"] == 4
    for layer, word in (("narration", "了"), ("dialogue", "的")):
        measured = profile["layers"][layer]
        assert measured["han_characters"] == 12
        feature = measured["features"]["declared_words"][word]
        assert feature["count"] == 6 and feature["rate_per_10k_han"] == 5000
        distribution = feature["chapter_distribution"]
        assert [row["rate_per_10k_han"] for row in distribution["chapters"]] == [5000, 5000, 0, 7500]
        assert [distribution[key] for key in ("minimum", "q1", "median", "q3", "maximum")] == [0, 3750, 5000, 5625, 7500]
        assert distribution["defined_chapters"] == distribution["total_chapters"] == 4
        assert measured["features"]["declared_words"]["然后"]["count"] == 0
    assert profile["readiness"] == "CANDIDATE_PENDING_HUMAN_AUDIT"
    assert profile["human_audit_status"] == "PENDING" and profile["provisional"] is True
    assert profile["feature_set"] == "style-reference-features:v1"
    assert "EXPLORATORY" in profile["feature_policy"]["word_list_basis"]
    assert profile["authority_effect"] == profile["evidence_effect"] == "NONE"
    assert profile["verdict"] is None


def test_audit_status_is_live_and_never_a_gate(tiny_corpus):
    root, state, calls = tiny_corpus
    for status in ("PENDING", "PASS", "FAIL"):
        state["status"] = status
        profile = sr.reference_profile(root, DATASET)
        assert profile["human_audit_status"] == status
        assert profile["provisional"] == (status != "PASS")
        report = style_diagnostics("然后然后然后“姑娘姑娘姑娘”", reference=profile)
        assert report["status"] == "OBSERVED" and report["literary_quality_verified"] is False
        assert report["reference_distribution"]["verdict"] is None
        feature = report["reference_distribution"]["overall"]["layers"]["narration"]["features"]["declared_words"]["然后"]
        assert feature["observations"] == ["OUTSIDE_FRONT80_CHAPTER_RANGE"]
    assert len(calls) == 6


def test_no_cache_bypass_and_manifest_binding_checked(tiny_corpus):
    root, state, calls = tiny_corpus
    sr.reference_profile(root, DATASET)
    state["binding"]["manifest_sha256"] = "0" * 64
    with pytest.raises(AssetError, match="MANIFEST_BINDING_MISMATCH"):
        sr.reference_profile(root, DATASET)
    assert len(calls) == 2


def test_catalog_detects_tampered_manifest_bytes(tiny_corpus):
    root, state, calls = tiny_corpus
    sr.reference_profile(root, DATASET)
    (root / "manifest.json").write_text("{}")
    with pytest.raises(AssetError, match="byte mismatch"):
        sr.reference_profile(root, DATASET)
    assert len(calls) == 2


def test_repository_product_verification_failure_propagates(tiny_corpus, monkeypatch):
    root, _, _ = tiny_corpus
    def rejected(self, dataset_ref, *, rebuild=True):
        assert rebuild is False
        raise AssetError("CORPUS_PRODUCT_BINDING_MISMATCH")
    monkeypatch.setattr(sr.CorpusRepository, "load", rejected)
    with pytest.raises(AssetError, match="PRODUCT_BINDING_MISMATCH"):
        sr.reference_profile(root, DATASET)


def test_audit_binding_failure_propagates(tiny_corpus, monkeypatch):
    root, _, _ = tiny_corpus
    def rejected(self, dataset_ref, *, rebuild=True):
        assert rebuild is False
        raise AssetError("STALE_CORPUS_AUDIT_MANIFEST")
    monkeypatch.setattr(sr.CorpusAudit, "summary", rejected)
    with pytest.raises(AssetError, match="STALE_CORPUS_AUDIT_MANIFEST"):
        sr.reference_profile(root, DATASET)


@pytest.mark.parametrize("text, narration, dialogue", [
    ("甲乙“丙丁‘戊己’庚辛”壬癸", ["甲乙", "壬癸"], ["丙丁", "戊己", "庚辛"]),
    ("甲乙「丙丁『戊己』庚辛」壬癸", ["甲乙", "壬癸"], ["丙丁", "戊己", "庚辛"]),
    ("甲乙“丙丁”壬癸“戊己”", ["甲乙", "壬癸"], ["丙丁", "戊己"]),
    ("甲\n乙\n\n丙 丁", ["甲乙", "丙丁"], []),
    ("“甲乙\n\n丙丁”", [], ["甲乙", "丙丁"]),
])
def test_nested_quotes_and_paragraph_segmentation(text, narration, dialogue):
    split = sr.segment_prose(text)
    assert split["layers"] == {"narration": narration, "dialogue": dialogue, "unknown": []}
    assert split["issues"] == [] and split["status"] == "BALANCED_QUOTES"


@pytest.mark.parametrize("text, code", [
    ("甲乙“丙丁", "UNCLOSED_QUOTE"),
    ("甲乙“丙丁‘戊己”壬癸", "MISMATCHED_CLOSING_QUOTE"),
    ("甲乙”壬癸", "UNMATCHED_CLOSING_QUOTE"),
    ("甲乙‘丙丁", "UNCLOSED_QUOTE"),
])
def test_malformed_quotes_are_reported_and_quarantined(text, code):
    split = sr.segment_prose(text)
    assert code in [issue["code"] for issue in split["issues"]]
    assert split["status"] == "QUOTE_ISSUES_PRESENT"
    assert split["layers"]["unknown"]
    assert not split["layers"]["dialogue"]
    total = sum(len(sr.HAN.findall(piece)) for pieces in split["layers"].values() for piece in pieces)
    assert total == len(sr.HAN.findall(text))


def test_reference_and_candidate_quote_issues_are_visible(tiny_corpus):
    root, state, _ = tiny_corpus
    state["segments"][0]["text"] = "甲乙“丙丁"
    profile = sr.reference_profile(root, DATASET)
    assert profile["segmentation"]["unknown_han_characters"] == 2
    assert profile["segmentation"]["unknown_han_fraction"] == pytest.approx(2 / 24)
    assert profile["segmentation"]["issues"][0]["segment_id"] == state["segments"][0]["segment_id"]
    report = sr.compare_reference("甲乙”壬癸", profile)
    assert report["candidate_segmentation"]["status"] == "QUOTE_ISSUES_PRESENT"
    assert report["candidate_segmentation"]["unknown_han_characters"] == 2
    assert report["overall"]["layers"]["narration"]["han_characters"] == 2


def test_bigrams_never_bridge_paragraphs_quote_runs_or_punctuation():
    split = sr.segment_prose("甲乙\n\n丙丁“戊己‘庚辛’壬癸”子丑“寅卯”辰巳，午未")
    narration = sr._measure(split["layers"]["narration"])["bigrams"]
    dialogue = sr._measure(split["layers"]["dialogue"])["bigrams"]
    assert set(narration) == {"甲乙", "丙丁", "子丑", "辰巳", "午未"}
    assert set(dialogue) == {"戊己", "庚辛", "壬癸", "寅卯"}


def test_bigrams_do_not_bridge_corpus_segments_or_chapters(tiny_corpus):
    root, state, _ = tiny_corpus
    state["segments"] = [_segment(1, "甲" * 5), _segment(1, "乙" * 5), _segment(2, "丙" * 5),
                         _segment(3, "甲甲甲甲甲甲"), _segment(4, "乙乙乙乙乙乙")]
    profile = sr.reference_profile(root, DATASET)
    assert set(profile["layers"]["narration"]["top_han_bigrams"]) == {"甲甲", "乙乙"}
    report = sr.compare_reference("# 第一回 标题\n甲甲甲甲甲甲\n# 第二回 标题\n乙乙乙乙乙乙", profile)
    assert report["candidate_chapter_count"] == 2
    assert report["overall"]["layers"]["narration"]["han_characters"] == 12


def test_bigram_minimum_counts_top_300_and_both_directions(tiny_corpus):
    root, state, _ = tiny_corpus
    state["segments"] = [_segment(1, "甲乙，" * 10 + "丙丁，" * 5 + "戊己，" * 4),
                         _segment(2, "“甲乙，" + "丙丁，" * 10 + "甲乙，" * 4 + "”")]
    profile = sr.reference_profile(root, DATASET)
    assert list(profile["layers"]["narration"]["top_han_bigrams"]) == ["甲乙", "丙丁"]
    assert profile["layers"]["dialogue"]["top_han_bigrams"]["丙丁"]["count"] == 10
    report = sr.compare_reference("丙丁，" * 10, profile)
    deviations = report["overall"]["layers"]["narration"]["bigram_deviations"]
    assert deviations["higher"][0]["bigram"] == "丙丁"
    assert deviations["lower"][0]["bigram"] == "甲乙" and deviations["lower"][0]["count"] == 0
    rare = sr.compare_reference("甲乙，", profile)["overall"]["layers"]["narration"]["bigram_deviations"]
    assert not any(row["bigram"] == "甲乙" for rows in rare.values() for row in rows)
    # More than 300 mechanically selected features; stable count/lexical tie order.
    words = [chr(0x4e00 + i) + chr(0x5000 + i) for i in range(305)]
    state["segments"] = [_segment(1, "，".join(word for word in words for _ in range(5)))]
    selected = sr.reference_profile(root, DATASET)["layers"]["narration"]["top_han_bigrams"]
    assert len(selected) == 300 and list(selected) == sorted(words)[:300]


def test_empty_layer_has_null_rates_not_zero_or_outside(tiny_corpus):
    root, state, _ = tiny_corpus
    state["segments"] = [_segment(1, "甲乙")]
    profile = sr.reference_profile(root, DATASET)
    reference = profile["layers"]["dialogue"]["features"]["declared_words"]["的"]
    assert reference["count"] == 0 and reference["rate_per_10k_han"] is None
    assert reference["chapter_distribution"]["defined_chapters"] == 0
    report = sr.compare_reference("", profile)
    feature = report["overall"]["layers"]["dialogue"]["features"]["declared_words"]["的"]
    assert feature["rate_per_10k_han"] is None and feature["observations"] == []
    assert report["verdict"] is None


@pytest.mark.parametrize("number, expected", [("八十一", 81), ("九十九", 99), ("一百", 100), ("十", 10),
                                              ("一〇〇", 100), ("１００", 100), ("壹佰", 100), ("两百", 200)])
def test_markdown_chinese_chapter_numbers(number, expected):
    chapters, preamble = sr.candidate_chapters(f"导言\n# 第{number}回　标题\n正文\n")
    assert len(chapters) == 1 and chapters[0]["chapter"] == expected
    assert chapters[0]["title"] == "标题" and "标题" not in chapters[0]["text"]
    assert preamble == "导言\n"


def test_multi_chapter_report_and_overall_exclude_titles_and_preamble(tiny_corpus):
    root, _, _ = tiny_corpus
    profile = sr.reference_profile(root, DATASET)
    text = "导言了了了\n# 第八十一回　了了了\n了甲\n\n# 第八十二回　了了了\n甲甲"
    report = sr.compare_reference(text, profile)
    assert [row["chapter"] for row in report["chapters"]] == [81, 82]
    assert report["overall"]["layers"]["narration"]["han_characters"] == 4
    feature = report["overall"]["layers"]["narration"]["features"]["declared_words"]["了"]
    assert feature["count"] == 1 and feature["rate_per_10k_han"] == 2500
    assert report["candidate_segmentation"]["excluded_preamble_han_characters"] == 5
    retained = report["reference_layers"]["narration"]
    assert retained["chapter_order"] == [1, 2, 3, 4]
    assert retained["chapter_han_characters"] == [2, 4, 2, 4]
    columns = retained["features"]["declared_words"]["了"]["chapter_distribution"]["chapters"]
    assert columns == {"counts": [1, 2, 0, 3], "rates_per_10k_han": [5000, 5000, 0, 7500]}
    assert "chapters" not in feature["reference"]["chapter_distribution"]


def test_baseline_has_20_chapter_reports_without_loading_real_corpus(tiny_corpus):
    root, _, _ = tiny_corpus
    profile = sr.reference_profile(root, DATASET)
    text = (ROOT / "releases/stable/v1.4/readable/baseline.md").read_text()
    report = sr.compare_reference(text, profile)
    assert report["candidate_chapter_count"] == 20
    assert [row["chapter"] for row in report["chapters"]] == list(range(81, 101))
    for name in ("narration", "dialogue"):
        assert report["overall"]["layers"][name]["han_characters"] == sum(row["layers"][name]["han_characters"] for row in report["chapters"])


def _parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root")
    diagnostics.add_commands(parser.add_subparsers(dest="command", required=True))
    return parser


def test_cli_reference_root_and_observation_exit_zero(tiny_corpus, capsys):
    root, state, calls = tiny_corpus
    state["status"] = "FAIL"  # An audit rejection is metadata, not a style gate.
    path = root / "candidate.md"
    path.write_text("# 第八十一回 标题\n然后然后然后“姑娘姑娘姑娘”")
    args = _parser().parse_args(["--root", str(root), "diagnostics", "style", str(path), "--reference", DATASET])
    assert args.func(args) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "OBSERVED"
    assert report["reference_distribution"]["human_audit_status"] == "FAIL"
    assert report["reference_distribution"]["verdict"] is None
    assert calls == [("load", DATASET, False), ("audit", DATASET, False)]


def test_cli_no_reference_does_not_access_corpus(tmp_path, monkeypatch, capsys):
    def forbidden(*args, **kwargs):
        pytest.fail("default diagnostics must not access the reference corpus")
    monkeypatch.setattr(diagnostics, "reference_profile", forbidden)
    path = tmp_path / "candidate.txt"
    path.write_text("话说甲乙“姑娘。”")
    args = _parser().parse_args(["--root", str(tmp_path), "diagnostics", "style", str(path)])
    assert args.func(args) == 0
    assert capsys.readouterr().out == json.dumps(style_diagnostics(path.read_text()), ensure_ascii=False, indent=2) + "\n"


def test_cli_invalid_reference_reports_integrity_failure(tiny_corpus, capsys):
    root, _, _ = tiny_corpus
    path = root / "candidate.txt"
    path.write_text("甲乙")
    args = _parser().parse_args(["--root", str(root), "diagnostics", "style", str(path), "--reference", "missing"])
    assert args.func(args) == 1
    assert json.loads(capsys.readouterr().out)["status"] == "FAIL"


def test_holdout_exclusions_select_features_and_scope_readiness(tiny_corpus):
    root, state, _ = tiny_corpus
    state["segments"] += [_segment(3, "秘密，" * 100), _segment(4, "秘密，" * 100)]
    profile = sr.reference_profile(root, DATASET, exclude_chapters=[4, 3, 4])
    assert profile["chapter_count"] == 2
    assert profile["main_text_segment_count"] == 2
    assert "秘密" not in profile["layers"]["narration"]["top_han_bigrams"]
    assert profile["reference_scope"]["included_chapters"] == [1, 2]
    assert profile["reference_scope"]["excluded_chapters"] == [3, 4]
    assert profile["reference_scope"]["readiness_scope"] == "SOURCE_DATASET"
    assert profile["reference_scope"]["subset_audit_status"] == "NOT_SEPARATELY_AUDITED"
    assert "NOT_TARGET_BLIND" in profile["feature_policy"]["holdout_policy"]["declared_words"]
    report = sr.compare_reference("甲乙", profile)
    assert report["reference_scope"] == profile["reference_scope"]
    assert report["reference_layers"]["narration"]["chapter_order"] == [1, 2]


def test_empty_exclusions_preserve_serialized_legacy_result(tiny_corpus):
    root, _, _ = tiny_corpus
    expected = json.dumps(sr.reference_profile(root, DATASET), ensure_ascii=False)
    for exclusions in (None, [], (), set()):
        assert json.dumps(sr.reference_profile(root, DATASET, exclude_chapters=exclusions), ensure_ascii=False) == expected
    assert "reference_scope" not in json.loads(expected)


def test_all_chapters_excluded_remains_empty_observation(tiny_corpus):
    root, _, _ = tiny_corpus
    profile = sr.reference_profile(root, DATASET, exclude_chapters=[1, 2, 3, 4])
    assert profile["chapter_count"] == profile["main_text_segment_count"] == 0
    assert sr.compare_reference("甲", profile)["reference_layers"]["dialogue"]["chapter_order"] == []
    assert profile["verdict"] is None


@pytest.mark.skipif(os.environ.get("RCWH_STYLE_REFERENCE_INTEGRATION") != "1", reason="opt-in immutable production corpus verification")
def test_actual_front80_reference_and_baseline():
    profile = sr.reference_profile(ROOT, "corpus:front80:v1-candidate")
    assert profile["chapter_count"] == 80
    assert profile["human_audit_status"] in {"PASS", "PENDING", "FAIL"}
    assert profile["authority_effect"] == profile["evidence_effect"] == "NONE" and profile["verdict"] is None
    for name in ("narration", "dialogue"):
        layer = profile["layers"][name]
        assert layer["han_characters"] > 0 and len(layer["top_han_bigrams"]) == 300
        assert layer["features"]["declared_words"]["了"]["chapter_distribution"]["total_chapters"] == 80
    report = style_diagnostics((ROOT / "releases/stable/v1.4/readable/baseline.md").read_text(), reference=profile)
    assert report["reference_distribution"]["candidate_chapter_count"] == 20
    assert report["status"] == "OBSERVED" and report["literary_quality_verified"] is False
