from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .io import load_data
from .contracts import unique_index, coverage_errors, validate_plan_constraints


@dataclass
class WorldRuntime:
    data: dict[str, Any]
    characters: dict[str, dict[str, Any]]
    locations: dict[str, dict[str, Any]]
    relations: dict[str, dict[str, Any]]
    institutions: dict[str, dict[str, Any]]
    presence: dict[int, dict[str, Any]]
    body: dict[int, dict[str, Any]]
    flows: dict[int, dict[str, Any]]
    economy_stages: list[dict[str, Any]]
    knowledge_rules: list[dict[str, Any]]
    longlines: list[dict[str, Any]]

    @classmethod
    def from_repo(cls, root: Path) -> "WorldRuntime":
        core = load_data(root / "data" / "world" / "m3_core.json") or {}
        loc = load_data(root / "data" / "world" / "m3_locations.json") or {}
        presence_doc = load_data(root / "data" / "world" / "m3_presence.json") or {}
        body_doc = load_data(root / "data" / "world" / "m3_body.json") or {}
        res = load_data(root / "data" / "world" / "m3_resources.json") or {}
        know = load_data(root / "data" / "world" / "m3_knowledge.json") or {}
        data = {
            **core,
            "locations": loc.get("locations", []),
            "presence_matrix": presence_doc.get("presence_matrix", []),
            "body_matrix": body_doc.get("body_matrix", []),
            "economy_stages": res.get("economy_stages", []),
            "resource_flows": res.get("resource_flows", []),
            "knowledge_rules": know.get("knowledge_rules", []),
            "longlines": know.get("longlines", []),
        }
        return cls(
            data=data,
            characters=unique_index(data.get('characters', []), 'id'),
            locations=unique_index(data.get('locations', []), 'id'),
            relations=unique_index(data.get('relations', []), 'id'),
            institutions=unique_index(data.get('institutions', []), 'id'),
            presence=unique_index(data.get('presence_matrix', []), 'chapter'),
            body=unique_index(data.get('body_matrix', []), 'chapter'),
            flows=unique_index(data.get('resource_flows', []), 'chapter'),
            economy_stages=data.get("economy_stages", []),
            knowledge_rules=data.get("knowledge_rules", []),
            longlines=data.get("longlines", []),
        )

    def snapshot(self, chapter: int) -> dict[str, Any]:
        if chapter not in self.presence and chapter != self.data["baseline"]["chapter"]:
            raise KeyError(f"Chapter outside configured World runtime: {chapter}")
        state = deepcopy(self.data["baseline"])
        for event in sorted(self.data.get("events", []), key=lambda x: (x["chapter"], x["sequence"])):
            if event["chapter"] > chapter:
                break
            for effect in event.get("effects", []):
                _assign(state, effect["set"], deepcopy(effect.get("value")))
        return state

    def character_state(self, character_id: str, chapter: int) -> dict[str, Any]:
        if character_id not in self.characters:
            raise KeyError(f"Unknown world character: {character_id}")
        state = self.snapshot(chapter)["characters"][character_id]
        item = deepcopy(self.characters[character_id])
        item["chapter"] = chapter
        item["state"] = deepcopy(state)
        item["presence"] = self._presence_for_name(item["name"], chapter)
        item["knowledge"] = self.knowledge(character_id, chapter)
        return item

    def knowledge(self, character_id: str, chapter: int) -> dict[str, Any]:
        if character_id not in self.characters:
            raise KeyError(f"Unknown world character: {character_id}")
        groups = set(self.characters[character_id].get("groups", []))
        rules = []
        for rule in self.knowledge_rules:
            if rule["chapter"] > chapter:
                continue
            targets = set(rule["targets"])
            if character_id in targets or groups.intersection(targets):
                rules.append(rule)
        return {
            "character_id": character_id,
            "chapter": chapter,
            "rules": rules,
            "boundary": "Absence of a rule is not proof of knowledge; M3 records only source-supported asymmetries.",
        }

    def chapter(self, chapter: int) -> dict[str, Any]:
        if chapter not in self.presence:
            raise KeyError(f"Unknown world chapter: {chapter}")
        snapshot = self.snapshot(chapter)
        return {
            "chapter": chapter,
            "presence": self.presence[chapter],
            "body": self.body[chapter],
            "resource_flow": self.flows[chapter],
            "economy": self.economy(chapter)["stage"],
            "global_state": snapshot["global"],
            "knowledge_rules": [x for x in self.knowledge_rules if x["chapter"] == chapter],
        }

    def location(self, location_id: str) -> dict[str, Any]:
        if location_id not in self.locations:
            raise KeyError(f"Unknown world location: {location_id}")
        return self.locations[location_id]

    def relation(self, relation_id: str, chapter: int) -> dict[str, Any]:
        if relation_id not in self.relations:
            raise KeyError(f"Unknown world relation: {relation_id}")
        return {
            "relation": self.relations[relation_id],
            "chapter": chapter,
            "state": self.snapshot(chapter)["relations"][relation_id],
        }

    def economy(self, chapter: int) -> dict[str, Any]:
        if chapter not in self.flows:
            raise KeyError(f"Chapter outside configured economy runtime: {chapter}")
        stage = next(
            x for x in self.economy_stages
            if x["chapter_start"] <= chapter <= x["chapter_end"]
        )
        return {"chapter": chapter, "stage": stage, "flow": self.flows[chapter]}

    def summary(self) -> dict[str, Any]:
        return {
            "chapters": len(self.presence),
            "characters": len(self.characters),
            "locations": len(self.locations),
            "relations": len(self.relations),
            "institutions": len(self.institutions),
            "events": len(self.data.get("events", [])),
            "knowledge_rules": len(self.knowledge_rules),
            "longlines": len(self.longlines),
        }

    def validate_integrity(self, catalog: Any, reconstruction: Any) -> list[str]:
        errors: list[str] = []
        expected_chapters = set(reconstruction.chapter_scope)
        for label, view in [("presence", self.presence), ("body", self.body), ("resource flows", self.flows)]:
            errors.extend(coverage_errors(view, expected_chapters, "world " + label))
        if not self.characters or not self.locations or not self.institutions:
            errors.append("world characters, locations and institutions must be nonempty")
        unique_index(self.economy_stages)
        unique_index(self.data.get("events", []))
        errors.extend(coverage_errors(self.data["baseline"]["characters"], self.characters, "world baseline characters"))
        errors.extend(coverage_errors(self.data["baseline"]["relations"], self.relations, "world baseline relations"))

        for name, source in self.data.get("sources", {}).items():
            doc = catalog.assets.get(source["asset_ref"])
            if doc is None:
                errors.append(f"World source {name}: unregistered document {source['asset_ref']}")
            elif doc["sha256"] != source["sha256"]:
                errors.append(f"World source {name}: SHA256 mismatch")

        for chapter in expected_chapters:
            if chapter not in reconstruction.chapters:
                errors.append(f"chapter {chapter}: missing Reconstruction chapter")

        for rel in self.relations.values():
            if rel["a"] not in self.characters or rel["b"] not in self.characters:
                errors.append(f"{rel['id']}: relation endpoint missing")

        try:
            snapshots = {chapter: self.snapshot(chapter) for chapter in sorted(expected_chapters)}
        except (KeyError, ValueError, TypeError) as exc:
            errors.append(f"World replay failed: {exc}")
            return errors
        errors.extend(validate_plan_constraints(catalog, "world", {"snapshots": snapshots}))
        for chapter, state in snapshots.items():
            if state["global"].get("human_access_to_outer_frame_knowledge") is not False:
                errors.append(f"chapter {chapter}: outer-frame knowledge may not leak into human world")
        return errors

    def _presence_for_name(self, name: str, chapter: int) -> str:
        if chapter not in self.presence:
            return "OUTSIDE_M3_RANGE"
        item = self.presence[chapter]
        if name and name in item.get("main_source", ""):
            return "MAIN_SOURCE"
        if name and name in item.get("natural_source", ""):
            return "NATURAL_SOURCE"
        return "NOT_LISTED_AS_SCENE_PARTICIPANT"


def _assign(state: dict[str, Any], dotted: str, value: Any) -> None:
    parts = dotted.split(".")
    cur: Any = state
    for part in parts[:-1]:
        if part not in cur:
            raise KeyError(part)
        cur = cur[part]
    cur[parts[-1]] = value


def format_world(kind: str, payload: dict[str, Any]) -> str:
    if kind == "summary":
        return "\n".join([
            "WORLD M3",
            f"chapters: {payload['chapters']}",
            f"characters: {payload['characters']}",
            f"locations: {payload['locations']}",
            f"relations: {payload['relations']}",
            f"institutions: {payload['institutions']}",
            f"events: {payload['events']}",
            f"knowledge rules: {payload['knowledge_rules']}",
        ])
    if kind == "character":
        state = payload["state"]
        return "\n".join([
            f"CHARACTER {payload['id']} / {payload['name']} @ ch{payload['chapter']}",
            f"presence: {payload['presence']}",
            f"location: {state.get('location')}",
            f"life: {state.get('life_state')}",
            f"legal: {state.get('legal_status')}",
            f"marital: {state.get('marital_status')}",
            f"role: {state.get('household_role')}",
            f"body: {state.get('body_state')}",
            f"knowledge_rules: {len(payload['knowledge']['rules'])}",
        ])
    return "\n".join(f"{k}: {v}" for k, v in payload.items())
