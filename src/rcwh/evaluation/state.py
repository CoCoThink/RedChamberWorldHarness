"""Scene entry views over the selected world, object and knowledge runtimes."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from ..io import load_data
from ..knowledge import CharacterKnowledgeRuntime
from ..world import WorldRuntime
from ..object_network import ObjectNetworkRuntime


def canonical_target(target: str) -> str:
    parts = target.split(".")
    if len(parts) < 3 or parts[0] not in {"character", "object"}:
        raise ValueError(f"unsupported scene state target: {target}")
    if parts[0] == "object" and parts[2] == "state":
        parts.pop(2)
    return ".".join(parts)


def normalized(value: Any) -> Any:
    return value.lower() if isinstance(value, str) else value


class SceneStateAdapter:
    def __init__(self, root: Path, contract: dict):
        self.world = WorldRuntime.from_repo(root)
        chapter = contract["chapter"]
        snapshot = self.world.snapshot(max(self.world.data["baseline"]["chapter"], chapter - 1))
        self.values: dict[str, Any] = {}
        self.origins: dict[str, str] = {}

        def flatten(prefix, value, origin):
            if isinstance(value, dict):
                for key, item in value.items():
                    flatten(f"{prefix}.{key}", item, origin)
            else:
                self.values[prefix] = normalized(value)
                self.origins[prefix] = origin

        for cid, state in snapshot["characters"].items():
            flatten(f"character.{cid}", state, "SELECTED_WORLD_ENTRY")
        objects = ObjectNetworkRuntime.from_repo(root)
        for identity in objects.objects:
            flatten(f"object.{identity}", objects.snapshot(identity, max(objects.data["baseline_chapter"], chapter - 1))["state"], "SELECTED_OBJECT_NETWORK_ENTRY")
        for path in sorted((root / "data/objects").glob("*.yaml")):
            obj = load_data(path)
            flatten(f"object.{obj['id']}", obj.get("state", {}), "REGISTERED_OBJECT_ENTRY")
        # Scene-local conditions are reconstruction inputs, never evidence.
        for condition in contract.get("entry_state", []):
            target = canonical_target(condition["equals"])
            self.values[target] = normalized(condition["value"])
            self.origins[target] = "SCENE_LOCAL_RECONSTRUCTION_INPUT"
        self.knowledge = CharacterKnowledgeRuntime.from_repo(root)
        self.contract = contract

    def resolve(self, target: str) -> Any:
        return self.values[canonical_target(target)]

    def assert_contract_preconditions(self, contract: dict) -> list[str]:
        findings = []
        for condition in contract.get("preconditions", []):
            try:
                actual = self.resolve(condition["equals"])
                if actual != normalized(condition["value"]):
                    findings.append(f"precondition mismatch: {condition['equals']}={actual}")
            except (KeyError, ValueError) as exc:
                findings.append(f"unresolved precondition: {exc}")
        for cid in contract["participants"]:
            if cid not in self.world.characters:
                findings.append(f"missing selected World participant: {cid}")
        return findings

    def snapshot(self) -> dict:
        return {
            "values": deepcopy(self.values), "origins": dict(self.origins),
            "knowledge": self.knowledge.scene(self.contract["id"], "ENTRY") if self.contract["id"] in self.knowledge.scenes else None,
            "truth_layer": "RECONSTRUCTION_AND_CHARACTER", "evidence_effect": "NONE",
        }
