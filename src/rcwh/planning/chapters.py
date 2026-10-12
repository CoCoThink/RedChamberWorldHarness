"""Deterministic imports and declaration checks, separate from semantic replay."""
from __future__ import annotations

import re
from pathlib import Path

from ..assets.paths import repository_path
from ..io import load_data
from ..schema import validate_instance
from .references import BOUNDARY, citation, record, verify_citation, verify_record, write_new

CARD_PATH = "sources/project/cea77d0ec8777a39/81—100_二十回全幅补完卡_v2.6_引用标识修复版.md"
HEADER = re.compile(r"^# \d+\. 第(\d+|一百)回全幅补完卡(?:【[^】]+】)?\s*$")
FIELD = re.compile(r"^\*\*(\d+)｜(.+?)\*\*.*$")


def parse_cards(raw: bytes, source_path: str = CARD_PATH) -> list[dict]:
    """Retain exact field bytes, including headings/newlines; offsets are byte offsets."""
    lines = raw.splitlines(keepends=True)
    decoded = [line.decode("utf-8") for line in lines]
    headers = [(i, 100 if m[1] == "一百" else int(m[1])) for i, line in enumerate(decoded) if (m := HEADER.fullmatch(line.rstrip("\r\n")))]
    if not headers or len({chapter for _, chapter in headers}) != len(headers):
        raise ValueError("missing or duplicate chapter card headers")
    result = []
    for start, chapter in headers:
        end = next((i for i in range(start + 1, len(lines)) if decoded[i].startswith("# ")), len(lines))
        title = next((line[3:].strip() for line in decoded[start + 1:end] if line.startswith("## ")), None)
        title_status = next((line.strip()[2:-2].split("｜", 1)[1] for line in decoded[start + 1:end] if line.startswith("**标题来源｜") and line.strip().endswith("**")), None)
        fields = [(i, m) for i in range(start + 1, end) if (m := FIELD.fullmatch(decoded[i].rstrip("\r\n")))]
        if [int(m[1]) for _, m in fields] != list(range(1, 19)) or not title or not title_status:
            raise ValueError(f"chapter {chapter}: expected title and exactly 18 ordered fields")
        projected = []
        for index, (position, match) in enumerate(fields):
            stop = fields[index + 1][0] if index + 1 < len(fields) else end
            # Markdown separators outside the card are not part of field 18.
            if index == 17:
                stop = next((i for i in range(position + 1, end) if decoded[i].strip() == "---"), stop)
            text = b"".join(lines[position:stop]).decode("utf-8")
            projected.append({"number": int(match[1]), "name": match[2], "text": text,
                              "citation": citation(source_path, raw, position + 1, stop)})
        result.append({"chapter": chapter, "title": title, "title_status": title_status,
                       "source": citation(source_path, raw, start + 1, end), "card_fields": projected})
    return result


CONTEXTS = {
    "data/reconstruction/m2.json": ("chapters", "timeline", "current_states_84_96", "central_state_chain"),
    "data/implementation_alignment/m6.json": ("chapter_plans", "chapter_protections", "implementation_facts"),
    "data/prewrite/v06.json": ("gap_cards", "omitted_scene_plans"),
    "data/literary_ecology/m5.json": ("author_rhyme_chapters",),
}


def import_cards(root: Path, *, source_path: str = CARD_PATH, output: str = "data/planning") -> dict:
    root = root.resolve()
    cards = parse_cards(repository_path(root, source_path).read_bytes(), source_path)
    if source_path == CARD_PATH and [x["chapter"] for x in cards] != list(range(81, 101)):
        raise ValueError("canonical import must contain chapters 81–100")
    context = {path: load_data(repository_path(root, path)) for path in CONTEXTS}
    contracts = []
    for path in sorted((root / "data/scenes").glob("*.yaml")):
        value = load_data(path)
        contracts.append((path.relative_to(root).as_posix(), value))
    writes = []
    for card in cards:
        chapter = card["chapter"]
        sources = [record(root, path, f"/{key}/{i}", item) for path, keys in CONTEXTS.items()
                   for key in keys for i, item in enumerate(context[path].get(key, [])) if item.get("chapter") == chapter]
        planner = next((x for x in sources if x["path"] == "data/prewrite/v06.json" and x["pointer"].startswith("/omitted_scene_plans/")), None)
        candidates = planner["value"].get("candidate_scenes", []) if planner else []
        scenes = []
        for order, candidate in enumerate(candidates, 1):
            ref = f"{output}/scenes/{candidate['id']}.json"
            source = record(root, planner["path"], f"{planner['pointer']}/candidate_scenes/{order - 1}", candidate)
            skeleton = {**BOUNDARY, "id": candidate["id"], "chapter": chapter, "title": candidate["title"],
                        "kind": "SCENE_SKELETON", "status": "DRAFT_IMPORTED", "order": order,
                        "chapter_plan_ref": f"{output}/chapters/ch{chapter}.json", "source_record": source,
                        "entry_from": None, "function": None, "participants": None, "required_objects": None,
                        "entry_state": None, "exit_state": None, "event_refs": [], "object_transition_refs": [],
                        "knowledge_event_refs": [], "unresolved": ["entry_from", "function", "participants", "required_objects", "entry_state", "exit_state", "event_bindings", "object_bindings", "knowledge_bindings"],
                        "order_basis": "SOURCE_LIST_ORDER_NOT_VERIFIED_CHRONOLOGY"}
            scenes.append({"id": candidate["id"], "order": order, "ref": ref})
            writes.append((ref, skeleton))
        existing = [{"id": value["id"], "ref": path, "placement_status": "PENDING"}
                    for path, value in contracts if value["chapter"] == chapter]
        plan = {**BOUNDARY, **card, "status": "DRAFT_IMPORTED", "source_records": sources,
                "scenes": scenes, "existing_contracts": existing, "entry_ref": None, "exit_ref": None,
                "threads": [], "protections": [x["ref"] for x in sources if x["pointer"].startswith("/chapter_protections/")],
                "open_refs": [], "unresolved": ["entry_ref", "exit_ref", "threads", "open_refs", "scene_chronology", "existing_contract_placement"],
                "order_basis": "SOURCE_LIST_ORDER_NOT_VERIFIED_CHRONOLOGY"}
        writes.append((f"{output}/chapters/ch{chapter}.json", plan))
    paths = [(repository_path(root, ref), value) for ref, value in writes]
    # Refuse any preexisting output before starting; xb is the final race guard.
    for path, _ in paths:
        if path.exists():
            raise FileExistsError(f"refusing to overwrite {path}")
    for path, value in paths:
        write_new(path, value)
    return {**BOUNDARY, "status": "DRAFT_IMPORTED", "chapters": [x["chapter"] for x in cards],
            "files": [ref for ref, _ in writes], "automatic_edit": False}


class ChapterPlans:
    def __init__(self, root: Path, directory: str | None = None):
        self.root = root.resolve()
        self.directory = directory or "data/planning/chapters"

    def get(self, chapter: int) -> dict:
        if type(chapter) is not int or chapter < 1:
            raise ValueError("chapter must be a positive integer")
        value = load_data(repository_path(self.root, f"{self.directory}/ch{chapter}.json"))
        if value["chapter"] != chapter:
            raise ValueError("CHAPTER_PLAN_ID_MISMATCH")
        return value

    def selected(self, chapters=None) -> list[dict]:
        if chapters is None:
            chapters = sorted(load_data(path)["chapter"] for path in repository_path(self.root, self.directory).glob("ch*.json"))
        return [self.get(chapter) for chapter in chapters]


def parse_chapters(value: str) -> list[int]:
    chapters = []
    for part in value.split(","):
        ends = part.split("-")
        if len(ends) > 2:
            raise ValueError("invalid chapter selector")
        a, b = int(ends[0]), int(ends[-1])
        if a < 1 or b < a:
            raise ValueError("invalid chapter range")
        chapters.extend(range(a, b + 1))
    return sorted(set(chapters))


def check_plans(root: Path, chapters=None, *, directory: str | None = None) -> dict:
    from .checking import check_selected
    return check_selected(root, chapters, directory=directory)
