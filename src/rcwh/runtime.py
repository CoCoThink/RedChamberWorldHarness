from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .io import load_data
from .world import WorldRuntime


@dataclass
class WorldState:
    characters: dict[str, dict[str, Any]] = field(default_factory=dict)
    objects: dict[str, dict[str, Any]] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    world_runtime: WorldRuntime | None = None

    @classmethod
    def from_repo(cls, root: Path) -> "WorldState":
        state = cls()
        for path in sorted((root / "data" / "characters").glob("*.yaml")):
            data = load_data(path)
            state.characters[data["id"]] = data
        for path in sorted((root / "data" / "objects").glob("*.yaml")):
            data = load_data(path)
            state.objects[data["id"]] = data
        if (root / "data" / "world" / "m3_core.json").exists():
            state.world_runtime = WorldRuntime.from_repo(root)
        return state

    def resolve(self, dotted: str) -> Any:
        parts = dotted.split(".")
        if parts[0] == "character":
            cur: Any = self.characters[parts[1]]
            parts = parts[2:]
        elif parts[0] == "object":
            cur = self.objects[parts[1]]
            parts = parts[2:]
        else:
            cur = self.metadata
        for part in parts:
            cur = cur[part]
        return cur

    def assign(self, dotted: str, value: Any) -> None:
        parts = dotted.split(".")
        if parts[0] == "character":
            cur: Any = self.characters[parts[1]]
            parts = parts[2:]
        elif parts[0] == "object":
            cur = self.objects[parts[1]]
            parts = parts[2:]
        else:
            cur = self.metadata
        for part in parts[:-1]:
            cur = cur.setdefault(part, {})
        cur[parts[-1]] = value

    def check_condition(self, condition: dict[str, Any]) -> bool:
        if "equals" in condition:
            return self.resolve(condition["equals"]) == condition.get("value")
        raise ValueError(f"Unsupported condition: {condition}")

    def apply_event(self, event: dict[str, Any]) -> None:
        failed = [p for p in event.get("preconditions", []) if not self.check_condition(p)]
        if failed:
            raise ValueError(f"Event {event['id']} preconditions failed: {failed}")
        for effect in event.get("effects", []):
            if "set" in effect:
                self.assign(effect["set"], deepcopy(effect.get("value")))
            else:
                raise ValueError(f"Unsupported effect: {effect}")

    def snapshot_at(self, chapter: int) -> dict[str, Any]:
        if self.world_runtime is None:
            raise ValueError("Full World runtime is not loaded")
        return self.world_runtime.snapshot(chapter)

    def character_at(self, character_id: str, chapter: int) -> dict[str, Any]:
        if self.world_runtime is None:
            raise ValueError("Full World runtime is not loaded")
        return self.world_runtime.character_state(character_id, chapter)

    def assert_contract_preconditions(self, contract: dict[str, Any]) -> list[str]:
        findings = []
        for cond in contract.get("preconditions", []):
            try:
                ok = self.check_condition(cond)
            except Exception as exc:  # noqa: BLE001
                findings.append(f"Invalid precondition {cond}: {exc}")
                continue
            if not ok:
                findings.append(f"Precondition failed: {cond}")
        return findings
