"""Scene entry views over the selected world, object and knowledge runtimes."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from ..assets.paths import repository_path
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


def _flatten(prefix: str, value: Any, origin: str, values: dict, origins: dict) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            _flatten(f"{prefix}.{key}", item, origin, values, origins)
    else:
        values[prefix] = normalized(value)
        origins[prefix] = origin


class SceneStateProjector:
    """Shared projection, not a merger of independent truth layers."""

    def __init__(self, root: Path):
        self.root = root
        self.world = WorldRuntime.from_repo(root)
        self.objects = ObjectNetworkRuntime.from_repo(root)
        self.knowledge = CharacterKnowledgeRuntime.from_repo(root)
        self.registered_objects = {
            path.relative_to(root).as_posix(): load_data(path)
            for path in sorted((root / "data/objects").glob("*.yaml"))
        }

    def entry(self, contract: dict) -> tuple[dict, dict]:
        chapter = contract["chapter"]
        snapshot = self.world.snapshot(max(self.world.data["baseline"]["chapter"], chapter - 1))
        values, origins = {}, {}
        for cid, state in snapshot["characters"].items():
            _flatten(f"character.{cid}", state, "SELECTED_WORLD_ENTRY", values, origins)
        for identity in self.objects.objects:
            state = self.objects.snapshot(identity, max(self.objects.data["baseline_chapter"], chapter - 1))["state"]
            _flatten(f"object.{identity}", state, "SELECTED_OBJECT_NETWORK_ENTRY", values, origins)
        for obj in self.registered_objects.values():
            _flatten(f"object.{obj['id']}", obj.get("state", {}), "REGISTERED_OBJECT_ENTRY", values, origins)
        for condition in contract.get("entry_state", []):
            target = canonical_target(condition["equals"])
            values[target] = normalized(condition["value"])
            origins[target] = "SCENE_LOCAL_RECONSTRUCTION_INPUT"
        return values, origins

    def bridge_overlaps(self, chapter: int) -> list[dict]:
        """Compare explicit bridges at a chapter end, without alias substitution."""
        rows = []
        seen = set()
        for identity, obj in sorted(self.objects.objects.items()):
            if not obj.get("legacy_ref"):
                continue
            path = repository_path(self.root, obj["legacy_ref"])
            legacy = load_data(path)
            if legacy["id"] in seen:
                raise ValueError(f"duplicate object bridge: {legacy['id']}")
            seen.add(legacy["id"])
            refinements = self._location_refinements(identity, obj)
            selected, registered = {}, {}
            _flatten("", self.objects.snapshot(identity, chapter)["state"], "", selected, {})
            _flatten("", legacy.get("state", {}), "", registered, {})
            for field in sorted(selected.keys() | registered.keys()):
                present = field in selected and field in registered
                status = "MATCH" if present and selected[field] == registered[field] else "DIFFERENT" if present else "UNKNOWN"
                refinement = refinements.get((registered.get(field), selected.get(field))) if field == ".location" else None
                if status == "DIFFERENT" and refinement:
                    status = "REFINES"
                rows.append({
                    "object_id": identity, "legacy_id": legacy["id"], "legacy_ref": obj["legacy_ref"],
                    "chapter": chapter, "checkpoint": "CHAPTER_END", "field": field.lstrip("."),
                    "selected_present": field in selected, "registered_present": field in registered,
                    "selected": selected.get(field), "registered": registered.get(field),
                    "status": status, "refinement": refinement if status == "REFINES" else None,
                    "authority_effect": "NONE",
                })
        return rows

    def _location_refinements(self, identity: str, obj: dict) -> dict:
        """Declared spatial containment only; never an equivalence or alias."""
        result = {}
        for item in obj.get("legacy_location_refinements", []):
            if (not isinstance(item, dict) or item.get("relation") != "CONTAINED_IN"
                    or not item.get("legacy_value") or not item.get("basis_segments")):
                raise ValueError(f"{identity}: invalid legacy location refinement")
            if item.get("within") not in self.world.locations:
                raise ValueError(f"{identity}: refinement within unknown location {item.get('within')}")
            key = (normalized(item["legacy_value"]), normalized(item["within"]))
            if key in result:
                raise ValueError(f"{identity}: duplicate legacy location refinement")
            result[key] = {"relation": "CONTAINED_IN", "legacy_value": item["legacy_value"],
                           "within": item["within"], "basis_segments": list(item["basis_segments"])}
        return result


class SceneStateAdapter:
    def __init__(self, root: Path, contract: dict, *, projector: SceneStateProjector | None = None):
        self.projector = projector or SceneStateProjector(root)
        self.world = self.projector.world
        self.values, self.origins = self.projector.entry(contract)
        self.knowledge = self.projector.knowledge
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

    def snapshot(self, *, request_version: int = 1) -> dict:
        if request_version not in {1, 2}:
            raise ValueError(f"unsupported semantic request version: {request_version}")
        result = {
            "values": deepcopy(self.values), "origins": dict(self.origins),
            "knowledge": self.knowledge.scene(self.contract["id"], "ENTRY") if self.contract["id"] in self.knowledge.scenes else None,
            "truth_layer": "RECONSTRUCTION_AND_CHARACTER", "evidence_effect": "NONE",
        }
        if request_version == 2:
            result["fact_registry"] = sorted(self.knowledge.facts)
        return result
