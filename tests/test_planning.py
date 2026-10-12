import argparse
import json
from pathlib import Path
import shutil

import pytest

from rcwh.application.plan import add_commands
from rcwh.planning.chapters import CARD_PATH, ChapterPlans, check_plans, import_cards, parse_cards
from rcwh.planning.hints import build_hint_ledger, threads_report
from rcwh.planning.books import compare_books
from rcwh.planning.references import verify_citation, verify_record
from rcwh.schema import validate_instance

ROOT = Path(__file__).resolve().parents[1]


def fixture_repo(tmp_path):
    shutil.copytree(ROOT / "schemas", tmp_path / "schemas")
    return tmp_path


def store(root, path, value):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value), encoding="utf-8")


def plan(chapter, scenes, entry=None, exit=None):
    return {"chapter": chapter, "title": "fixture", "title_status": "WORKING", "status": "DRAFT_IMPORTED", "authority_effect": "NONE",
            "scenes": scenes, "entry_ref": entry, "exit_ref": exit, "threads": [], "protections": [], "open_refs": [], "unresolved": []}


def test_actual_source_all_twenty_eighteen_fields(production_unchanged):
    raw = (ROOT / CARD_PATH).read_bytes()
    cards = parse_cards(raw)
    assert [x["chapter"] for x in cards] == list(range(81, 101))
    for card in cards:
        assert len(card["card_fields"]) == 18
        assert not verify_citation(ROOT, card["source"])
        imported = ChapterPlans(ROOT).get(card["chapter"])
        assert imported["status"] == "DRAFT_IMPORTED"
        assert not validate_instance(imported, ROOT / "schemas/chapter_plan.schema.json")
        assert imported["card_fields"] == card["card_fields"]
        for field in card["card_fields"]:
            assert not verify_citation(ROOT, field["citation"], field["text"])
        for source in imported["source_records"]:
            assert not verify_record(ROOT, source)
        assert {x["path"] for x in imported["source_records"]} == {"data/reconstruction/m2.json", "data/implementation_alignment/m6.json", "data/prewrite/v06.json", "data/literary_ecology/m5.json"}
        for scene in imported["scenes"]:
            value = json.loads((ROOT / scene["ref"]).read_text())
            assert value["kind"] == "SCENE_SKELETON"
            assert value["participants"] is None and value["exit_state"] is None
            assert not verify_record(ROOT, value["source_record"])
    assert sum(len(ChapterPlans(ROOT).get(x)["existing_contracts"]) for x in range(81, 101)) == 3


def test_fixture_parser_retains_crlf_and_inline_fields():
    raw = ("# 1. 第79回全幅补完卡\r\n## title\r\n**标题来源｜TG**\r\n" + "".join(f"**{i}｜field{i}** inline{i}\r\nbody{i}\r\n" for i in range(1, 19)) + "---\r\n# next\r\n").encode()
    card = parse_cards(raw, "source.md")[0]
    for field in card["card_fields"]:
        start, end = field["citation"]["byte_range"]
        assert field["text"].encode() == raw[start:end]
    with pytest.raises(ValueError, match="18"):
        parse_cards(raw.replace(b"**18", b"**19"))


def test_import_xb_no_overwrite(tmp_path):
    with pytest.raises(FileExistsError):
        import_cards(ROOT)
    root = fixture_repo(tmp_path)
    for path in [CARD_PATH, "data/reconstruction/m2.json", "data/implementation_alignment/m6.json", "data/prewrite/v06.json", "data/literary_ecology/m5.json"]:
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / path, target)
    result = import_cards(root)
    assert len(result["chapters"]) == 20
    before = (root / "data/planning/chapters/ch86.json").read_bytes()
    with pytest.raises(FileExistsError):
        import_cards(root)
    assert (root / "data/planning/chapters/ch86.json").read_bytes() == before


def test_chain_order_state_and_chapter_boundary(tmp_path):
    root = fixture_repo(tmp_path)
    store(root, "plans/ch79.json", plan(79, [{"id": "a", "order": 1, "ref": "scenes/a.json"}, {"id": "b", "order": 2, "ref": "scenes/b.json"}], "ENTRY", "EXIT"))
    store(root, "plans/ch80.json", plan(80, [], "DIFFERENT", None))
    store(root, "scenes/a.json", {"id": "a", "chapter": 79, "order": 1, "entry_from": "ENTRY", "exit_state": [{"equals": "object.o.state.holder", "value": "alice"}]})
    store(root, "scenes/b.json", {"id": "b", "chapter": 79, "order": 2, "entry_from": "wrong", "entry_state": [{"equals": "object.o.holder", "value": "bob"}]})
    report = check_plans(root, [79, 80], directory="plans")
    codes = {x["code"] for x in report["checks"]}
    assert {"SCENE_CHAIN_MISMATCH", "EXIT_ENTRY_STATE_MISMATCH", "CHAPTER_BOUNDARY_MISMATCH"} <= codes
    assert report["semantic_verified_replay"] == "NOT_CHECKED"
    assert ChapterPlans(root, "plans").get(79)["chapter"] == 79
    assert not validate_instance(plan(150, []), ROOT / "schemas/chapter_plan.schema.json")
    broken = plan(79, [{"id": "a", "order": 2, "ref": "scenes/a.json"}])
    store(root, "plans/ch79.json", broken)
    assert "SCENE_ORDER_MISMATCH" in {x["code"] for x in check_plans(root, [79], directory="plans")["checks"]}


def test_actual_plan_gaps_pending_not_verified():
    report = check_plans(ROOT, [85, 86, 87])
    assert report["status"] == "PENDING"
    assert {"OBJECT_TRAJECTORY_SCENE_MISSING", "WORLD_EVENT_SCENE_MISSING", "SCENE_CHAIN_UNDECLARED"} <= {x["code"] for x in report["checks"]}
    assert not any(x["status"] == "FAIL" for x in report["checks"])


def test_hint_seeds_checked_and_tampering_fails():
    ledger = build_hint_ledger(ROOT)
    assert len(ledger["hints"]) == 27
    ids = {x["id"] for x in ledger["hints"]}
    assert {f"m5:C{i:02}" for i in range(1, 7)} <= ids
    assert {f"m3:L{i:02}" for i in range(1, 11)} <= ids
    assert threads_report(ROOT, ledger=ledger)["status"] == "PENDING"
    ledger["hints"][0]["source_record"]["text_sha256"] = "0" * 64
    assert threads_report(ROOT, ledger=ledger)["status"] == "FAIL"


def test_hint_unknown_scene_beyond100_and_c05():
    ledger = build_hint_ledger(ROOT)
    c05 = next(x for x in ledger["hints"] if x["id"] == "m5:C05")
    c05["planned_responses"] = [{"chapter": 101, "scene": "unknown", "mode": "DIRECT", "creates_new_verdicts": True}]
    codes = {x["code"] for x in threads_report(ROOT, ledger=ledger)["checks"]}
    assert {"C05_NEW_VERDICTS_FORBIDDEN", "HINT_RESPONSE_BEYOND_CURRENT_MODEL", "HINT_RESPONSE_PLAN_MISSING"} <= codes


def test_books_deterministic_no_fake_replay():
    first = compare_books(ROOT)
    assert first == compare_books(ROOT)
    assert first["automatic_winner"] is None
    assert {x["total_chapters"] for x in first["books"]} == {100, 110}
    assert all(x["world_replay"]["status"] == "NOT_CHECKED" for x in first["books"])
    assert all(not x["findings"] for x in first["books"])
    assert first["front80_length_reference"]["status"] == "BYTE_CHECKED_REFERENCE_NOT_HUMAN_REVIEW"
    assert len(first["front80_length_reference"]["chapters"]) == 80
    book = json.loads((ROOT / "data/planning/books/current-100.json").read_text())
    book["event_allocations"][0]["chapter"] = 999
    assert compare_books(ROOT, books=[book])["status"] == "FAIL"


def test_direct_event_and_knowledge_order_fixture(tmp_path):
    from rcwh.knowledge import KNOWLEDGE_PATH
    root = fixture_repo(tmp_path)
    store(root, "plans/ch79.json", plan(79, [{"id": "s", "order": 1, "ref": "scenes/s.json"}]))
    store(root, "scenes/s.json", {"id": "s", "chapter": 79, "order": 1,
                                  "object_transition_refs": ["unknown"],
                                  "knowledge_event_refs": ["later", "earlier"]})
    store(root, "data/objects/m4.json", {"transitions": [{"id": "move", "chapter": 79}]})
    store(root, KNOWLEDGE_PATH, {"scenes": [{"id": "s", "chapter": 79, "events": [{"id": "earlier", "sequence": 1}, {"id": "later", "sequence": 2}]}]})
    codes = {x["code"] for x in check_plans(root, [79], directory="plans")["checks"]}
    assert {"INVALID_DIRECT_EVENT_REFERENCE", "OBJECT_TRAJECTORY_SCENE_MISSING", "KNOWLEDGE_ACQUISITION_ORDER_MISMATCH"} <= codes


def test_application_cli_parser_and_check(capsys):
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(ROOT))
    add_commands(parser.add_subparsers())
    for words in [["plan", "check", "--chapters", "85-87"], ["plan", "threads"], ["plan", "compare-books"]]:
        args = parser.parse_args(words)
        assert args.func(args) == 0
        assert json.loads(capsys.readouterr().out)["authority_effect"] == "NONE"
