from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .io import load_data


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
            characters={x["id"]: x for x in data.get("characters", [])},
            locations={x["id"]: x for x in data.get("locations", [])},
            relations={x["id"]: x for x in data.get("relations", [])},
            institutions={x["id"]: x for x in data.get("institutions", [])},
            presence={x["chapter"]: x for x in data.get("presence_matrix", [])},
            body={x["chapter"]: x for x in data.get("body_matrix", [])},
            flows={x["chapter"]: x for x in data.get("resource_flows", [])},
            economy_stages=data.get("economy_stages", []),
            knowledge_rules=data.get("knowledge_rules", []),
            longlines=data.get("longlines", []),
        )

    def snapshot(self, chapter: int) -> dict[str, Any]:
        if chapter < 80 or chapter > 100:
            raise KeyError(f"World runtime only covers chapter 80..100: {chapter}")
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
        if chapter < 81 or chapter > 100:
            raise KeyError(f"Economy runtime only covers chapter 81..100: {chapter}")
        stage = next(
            x for x in self.economy_stages
            if x["chapter_start"] <= chapter <= x["chapter_end"]
        )
        return {"chapter": chapter, "stage": stage, "flow": self.flows[chapter]}

    def summary(self) -> dict[str, Any]:
        return {
            "milestone": self.data["milestone"],
            "status": self.data["status"],
            "chapters": len(self.presence),
            "characters": len(self.characters),
            "locations": len(self.locations),
            "relations": len(self.relations),
            "institutions": len(self.institutions),
            "events": len(self.data.get("events", [])),
            "knowledge_rules": len(self.knowledge_rules),
            "longlines": len(self.longlines),
            "completion": self.data["completion"],
        }

    def validate_integrity(self, migration_registry: Any, reconstruction: Any) -> list[str]:
        errors: list[str] = []
        if self.data.get("milestone") != "M3":
            errors.append("World runtime milestone must be M3")
        expected_chapters = set(range(81, 101))
        if set(self.presence) != expected_chapters:
            errors.append("World presence matrix must contain 81..100 exactly")
        if set(self.body) != expected_chapters:
            errors.append("World body matrix must contain 81..100 exactly")
        if set(self.flows) != expected_chapters:
            errors.append("World resource-flow matrix must contain 81..100 exactly")
        if set(self.locations) != {f"S{i:02d}" for i in range(1, 16)}:
            errors.append("World location network must remain S01..S15 exactly")
        if {x["id"] for x in self.economy_stages} != {f"E{i}" for i in range(6)}:
            errors.append("World economy stages must remain E0..E5 exactly")
        if len(self.characters) != 28:
            errors.append(f"World character registry must contain 28 modeled characters; got {len(self.characters)}")
        if len(self.relations) != 10:
            errors.append(f"World relation registry must contain 10 core relations; got {len(self.relations)}")
        if len(self.institutions) != 9:
            errors.append(f"World institution registry must contain 9 systems; got {len(self.institutions)}")

        for name, source in self.data.get("sources", {}).items():
            doc = migration_registry.documents.get(source["document_ref"])
            if doc is None:
                errors.append(f"World source {name}: unregistered document {source['document_ref']}")
            elif doc["sha256"] != source["sha256"]:
                errors.append(f"World source {name}: SHA256 mismatch")

        for chapter in expected_chapters:
            if chapter not in reconstruction.chapters:
                errors.append(f"chapter {chapter}: missing Reconstruction chapter")

        for rel in self.relations.values():
            if rel["a"] not in self.characters or rel["b"] not in self.characters:
                errors.append(f"{rel['id']}: relation endpoint missing")

        try:
            end = self.snapshot(100)
        except Exception as exc:
            errors.append(f"World replay failed: {exc}")
            return errors

        if self.snapshot(86)["characters"]["daiyu"]["life_state"] != "DEAD":
            errors.append("Daiyu must be dead by end of chapter 86 in current runtime")
        if self.snapshot(87)["relations"]["rel:baoyu_baochai"]["status"] != "ACTIVE_SPOUSES":
            errors.append("Baoyu/Baochai spouse relation must be active by chapter 87 current model")
        if self.snapshot(92)["characters"]["baoyu"]["legal_status"] != "DETAINED_PENDING_INQUIRY":
            errors.append("Baoyu chapter 92 legal state must be detained-pending-inquiry")
        if self.snapshot(93)["characters"]["baoyu"]["legal_status"] != "RELEASED_NO_RESTORATION":
            errors.append("Baoyu chapter 93 must be released without restoration")
        if self.snapshot(93)["characters"]["fengjie"]["life_state"] != "DEAD":
            errors.append("Fengjie must be dead by end of chapter 93 current model")
        if self.snapshot(94)["characters"]["qiaojie"]["location"] != "S08":
            errors.append("Qiaojie must be in Liu rural household by chapter 94 current model")
        if self.snapshot(95)["global"]["economy_stage"] != "E3":
            errors.append("Chapter 95 must be stable true-poverty stage E3")
        if self.snapshot(99)["characters"]["baoyu"]["location"] != "S13":
            errors.append("Baoyu must be at the outer-city temple by chapter 99 current model")
        if self.relation("rel:xiangyun_weiruolan", 97)["state"]["status"] != "COHABITATION_INTERRUPTED_CAUSE_OPEN":
            errors.append("Xiangyun/Wei cause must remain OPEN in chapter 97")
        if end["global"].get("human_access_to_outer_frame_knowledge") is not False:
            errors.append("Outer-frame knowledge may not leak into human world")
        if self.data.get("completion", {}).get("completion_gate_ready"):
            errors.append("M3 may not mark overall Completion Gate ready")
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
        c = payload["completion"]
        return "\n".join([
            "WORLD M3",
            f"status: {payload['status']}",
            f"chapters: {payload['chapters']}/20",
            f"characters: {payload['characters']}",
            f"locations: {payload['locations']}/15",
            f"relations: {payload['relations']}",
            f"institutions: {payload['institutions']}",
            f"events: {payload['events']}",
            f"knowledge rules: {payload['knowledge_rules']}",
            f"queryable: {str(c['world_queryable']).lower()}",
            f"Completion Gate ready: {str(c['completion_gate_ready']).lower()}",
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
