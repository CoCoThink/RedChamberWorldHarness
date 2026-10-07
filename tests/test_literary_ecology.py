from pathlib import Path

from rcwh.literary_ecology import LiteraryEcologyRuntime
from rcwh.registry import MigrationRegistry


ROOT = Path(__file__).resolve().parents[1]


def ecology() -> LiteraryEcologyRuntime:
    return LiteraryEcologyRuntime.from_repo(ROOT)


def test_m5_summary_cardinalities_and_completion_boundary():
    summary = ecology().summary()
    assert summary["dimensions"] == 13
    assert summary["voice_profiles"] == 18
    assert summary["techniques"] == 16
    assert summary["evidence_nodes"] == 15
    assert summary["g_layer_decisions"] == 16
    assert summary["post80_chapters"] == 20
    assert summary["author_rhyme_chapters"] == 20
    assert summary["source_documents"] == 27
    completion = summary["completion"]
    assert completion["literary_ecology_queryable"] is True
    assert completion["source_traceable"] is True
    assert completion["p0_full_coverage"] is False
    assert completion["stable_active_changed"] is False
    assert completion["completion_gate_ready"] is False


def test_ten_du_yin_locks_existence_but_not_author_form_or_absolute_post80_placement():
    ten = ecology().ten_du_yin()
    assert ten["existence"] == "A_LOCKED"
    assert ten["after_chapter_64"] == "LOCKED"
    assert ten["post80"] == "WORKING_HIGH_FIT_NOT_LOCKED"
    assert ten["author_status"] == "OPEN_EVIDENCE_C_WORKING"
    assert ten["current_c_author"] == "daiyu"
    assert ten["shape"]["ten_poems"] == "C_WORKING"
    assert "不得因当前85主案" in ten["invariant"]


def test_qingbang_locks_two_literals_but_not_formal_title_or_sixty_person_roster():
    q = ecology().qingbang()
    assert q["formal_title_status"] == "OPEN"
    assert q["level_system"]["complete_rosters_locked"] is False
    assert q["level_system"]["each_level_twelve_locked"] is False
    assert q["level_system"]["total_sixty_locked"] is False
    known = {(x["character_id"], x["literal"]) for x in q["known_evaluations"]}
    assert known == {("baoyu", "情不情"), ("daiyu", "情情")}
    assert q["baoyu_position"].endswith("仍属C。")


def test_xu_zhuangzi_preserves_future_step_without_forcing_baoyu_to_read_it():
    xz = ecology().xu_zhuangzi()
    assert xz["baoyu_ch21_saw_text"] is False
    assert xz["not_seen_is_future_step"] == "LOCKED"
    assert xz["future_baoyu_sight"] == "OPEN"
    assert "终身仍不见" in xz["alternatives"]


def test_g_layer_preserves_no_farewell_text_and_rejects_duplicate_death_poems():
    runtime = ecology()
    assert runtime.g("G07")["decision"] == "无字胜出"
    assert runtime.g("G10")["decision"] == "淘汰"
    assert runtime.g("G11")["decision"] == "淘汰"
    assert runtime.g("G16")["decision"] == "无诗方案在作者层竞选胜出"


def test_author_rhyme_map_has_only_ch92_explicit_b_exception_and_no_terminal_poem():
    runtime = ecology()
    b_winners = [
        ch for ch, item in runtime.author_rhyme.items()
        if item["winner"].startswith("B")
    ]
    assert b_winners == [92]
    assert runtime.author_rhyme[92]["winner"] == "B_PRESERVE_EXISTING"
    assert runtime.author_rhyme[100]["winner"] == "C_TERMINAL_LOCK"
    assert runtime.author_rhyme[100]["mode"] == "无终篇韵文"


def test_voice_profiles_keep_person_specific_post80_boundaries():
    runtime = ecology()
    daiyu = runtime.voice("daiyu")
    fengjie = runtime.voice("fengjie")
    assert "俏语" in daiyu["post80_forbidden"]
    assert "气若游丝" in daiyu["post80_forbidden"]
    assert "速度和算计" in fengjie["post80_forbidden"]
    assert "纯弱" not in fengjie["voice"]


def test_chapter_text_ecology_is_queryable_without_turning_current_texts_into_evidence():
    runtime = ecology()
    ch92 = runtime.chapter(92)
    assert "到名纸" in ch92["text_ecology"]["texts"]
    assert ch92["author_rhyme"]["winner"] == "B_PRESERVE_EXISTING"
    ch99 = runtime.chapter(99)
    assert "无诀别文本" in ch99["text_ecology"]["texts"]
    assert ch99["author_rhyme"]["winner"] == "C_STRONG_LOCK"


def test_search_crosses_evidence_and_g_layer_without_collapsing_them():
    payload = ecology().search("\u7edd\u547d\u8bd7")
    assert payload["count"] >= 1
    kinds = {x["kind"] for x in payload["hits"]}
    assert "g" in kinds
    assert any(x["kind"] == "g" for x in payload["hits"])


def test_evidence_trace_resolves_ten_du_yin_sources_to_registered_sha_paths():
    registry = MigrationRegistry.from_repo(ROOT)
    payload = ecology().trace("evidence", "A01", registry)
    assert payload["trace_complete"] is True
    refs = {x["ref"] for x in payload["resolved_sources"]}
    assert "doc:0f2651a5c0f1" in refs
    assert "doc:5fddcda466a4" in refs
    assert all(x["kind"] == "document" for x in payload["resolved_sources"])
    assert all(len(x["sha256"]) == 64 for x in payload["resolved_sources"])


def test_m5_registry_expansion_keeps_current_markdown_zero_and_gate_closed():
    registry = MigrationRegistry.from_repo(ROOT)
    current = registry.current_summary()
    assert len(registry.documents) == len(registry.content_hashes) == 65
    assert current["literary_ecology_queryable"] is True
    assert current["literary_ecology_source_documents"] == 29
    assert current["current_markdown_islands"] == 0
    assert current["completion_gate_ready"] is False


def test_m5_integrity_passes():
    registry = MigrationRegistry.from_repo(ROOT)
    assert ecology().validate_integrity(registry) == []
