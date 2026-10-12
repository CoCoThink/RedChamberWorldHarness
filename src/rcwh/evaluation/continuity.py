"""Bounded, read-only continuity and direct state-reference diagnostics.

Scene exits are declarations, not replayed events. Neither chapter ordering nor
prose in reconstruction/prewrite inputs establishes a scene-to-scene chain.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ..contracts import project_chapters, unique_index
from ..io import load_data
from ..knowledge import KNOWLEDGE_PATH
from ..prewrite import V5PrewriteRuntime
from ..reconstruction import ReconstructionRegistry
from ..schema import validate_instance
from .state import SceneStateAdapter, SceneStateProjector, canonical_target, normalized


BOUNDARY = {
    "authority_effect": "NONE",
    "evidence_effect": "NONE",
    "scope": "STAGING_DIAGNOSTIC_ONLY",
    "production_block": False,
}
STATE_FIELDS = ("entry_state", "preconditions", "exit_state")


def diagnostic_failure(kind: str, error: Exception) -> dict:
    return {**BOUNDARY, "kind": kind, "status": "FAIL", "findings": [str(error)],
            "inspected_refs": []}


def _target(value: Any) -> str:
    if not isinstance(value, str) or any(not part or part.strip() != part for part in value.split(".")):
        raise ValueError(f"unsupported scene state target: {value!r}")
    target = canonical_target(value)
    if len(target.split(".")) < 3:
        raise ValueError(f"unsupported scene state target: {value!r}")
    return target


def _reference_error(target: str, projector: SceneStateProjector) -> str | None:
    parts = target.split(".")
    if parts[0] == "object":
        identities = set(projector.objects.objects) | {obj["id"] for obj in projector.registered_objects.values()}
        return None if parts[1] in identities else f"unknown object: {parts[1]}"
    if parts[1] not in projector.world.characters:
        return f"unknown character: {parts[1]}"
    if parts[2] == "knowledge":
        if len(parts) != 4:
            return f"knowledge target must identify exactly one fact: {target}"
        if parts[3] not in projector.knowledge.facts:
            return f"unknown knowledge fact: {parts[3]}"
    return None


def _finding(report: dict, status: str, code: str, ref: str, detail: str) -> None:
    report["checks"].append({"status": status, "code": code, "ref": ref, "detail": detail})


def _finish(report: dict, refs: set[str]) -> dict:
    report["checks"].sort(key=lambda row: (row["ref"], row["code"], row["detail"]))
    statuses = {row["status"] for row in report["checks"]}
    report["status"] = "FAIL" if "FAIL" in statuses else "PENDING" if "PENDING" in statuses else "PASS"
    report["findings"] = [f"{row['code']}: {row['ref']}: {row['detail']}"
                          for row in report["checks"] if row["status"] != "PASS"]
    report["inspected_refs"] = sorted(refs)
    return report


def _conditions(contract: dict, scene_ref: str, report: dict, refs: set[str],
                projector: SceneStateProjector) -> tuple[list[dict], bool]:
    rows, valid = [], True
    for field in STATE_FIELDS:
        conditions = contract.get(field, [])
        if not isinstance(conditions, list):
            _finding(report, "FAIL", "INVALID_CONDITIONS", f"{scene_ref}#{field}", "expected an array")
            valid = False
            continue
        seen: dict[str, Any] = {}
        for index, condition in enumerate(conditions):
            ref = f"{scene_ref}#{field}/{index}"
            refs.add(ref)
            try:
                if not isinstance(condition, dict) or "value" not in condition:
                    raise ValueError("condition requires equals and an explicit value (null is allowed)")
                target = _target(condition.get("equals"))
                refs.add(target)
                error = _reference_error(target, projector)
                if error:
                    raise ValueError(error)
                if target in seen:
                    raise ValueError(f"duplicate canonical target: {target}")
                seen[target] = normalized(condition["value"])
                rows.append({"field": field, "target": target, "value": normalized(condition["value"]), "ref": ref})
            except ValueError as exc:
                _finding(report, "FAIL", "INVALID_STATE_REFERENCE", ref, str(exc))
                valid = False
    return rows, valid


def _knowledge_value(contract: dict, target: str, projector: SceneStateProjector,
                     report: dict, ref: str) -> tuple[bool, Any]:
    _, actor, _, fact = target.split(".")
    knowledge = projector.knowledge
    if contract["id"] not in knowledge.scenes:
        _finding(report, "PENDING", "KNOWLEDGE_SCENE_MISSING", ref, "no selected scene checkpoint")
        return False, None
    checkpoint = contract.get("knowledge_checkpoint")
    if not checkpoint:
        _finding(report, "PENDING", "KNOWLEDGE_CHECKPOINT_MISSING", ref, "no explicit checkpoint; no FINAL default is inferred")
        return False, None
    try:
        value = knowledge.status(contract["id"], actor, fact, checkpoint)
    except KeyError as exc:
        _finding(report, "FAIL", "INVALID_KNOWLEDGE_REFERENCE", ref, str(exc))
        return False, None
    if value == "UNSPECIFIED":
        _finding(report, "PENDING", "KNOWLEDGE_VALUE_MISSING", ref, "absence from buckets does not establish knowledge")
        return False, None
    return True, value


def _scene(contract: dict, scene_ref: str, report: dict, refs: set[str],
           projector: SceneStateProjector, root: Path) -> dict:
    errors = validate_instance(contract, root / "schemas/scene_contract.schema.json")
    for error in errors:
        _finding(report, "FAIL", "INVALID_SCENE_STRUCTURE", scene_ref, error)
    conditions, valid = _conditions(contract, scene_ref, report, refs, projector)
    references = [{"target": row["target"], "field": row["field"], "ref": row["ref"]} for row in conditions]
    scene = {"id": contract.get("id"), "chapter": contract.get("chapter"), "ref": scene_ref,
             "references": references, "state_checks": [], "exit_state_semantics": "DECLARATIONS_NOT_PROVED_EVENTS"}
    if errors or not valid:
        return scene
    for actor in contract["participants"]:
        if actor not in projector.world.characters:
            _finding(report, "FAIL", "UNKNOWN_PARTICIPANT", scene_ref, actor)
    object_ids = set(projector.objects.objects) | {obj["id"] for obj in projector.registered_objects.values()}
    for identity in contract.get("required_objects", []):
        if identity not in object_ids:
            _finding(report, "FAIL", "UNKNOWN_REQUIRED_OBJECT", scene_ref, identity)
    adapter = SceneStateAdapter(root, contract, projector=projector)
    for row in conditions:
        target, field, ref = row["target"], row["field"], row["ref"]
        if target.startswith("character.") and target.split(".")[2] == "knowledge":
            present, actual = _knowledge_value(contract, target, projector, report, ref)
        else:
            present = target in adapter.values
            actual = adapter.values.get(target)
        scene["state_checks"].append({**row, "present": present, "actual": actual,
                                      "origin": adapter.origins.get(target),
                                      "comparison": "DECLARATION_ONLY" if field == "exit_state" else "MATCH" if present and actual == row["value"] else "MISMATCH" if present else "UNKNOWN"})
        if not present:
            _finding(report, "PENDING", "STATE_VALUE_MISSING", ref, target)
        elif field == "preconditions" and actual != row["value"]:
            _finding(report, "FAIL", "PRECONDITION_CONTRADICTION", ref,
                     f"{target}: declared={row['value']!r}, actual={actual!r}")
    guard_ids = set()
    for index, guard in enumerate(contract.get("knowledge_guards", [])):
        ref = f"{scene_ref}#knowledge_guards/{index}"
        refs.add(ref)
        target = _target(f"character.{guard['actor']}.knowledge.{guard['fact']}")
        refs.add(target)
        references.append({"target": target, "field": "knowledge_guards", "ref": ref})
        error = _reference_error(target, projector)
        if guard["id"] in guard_ids:
            error = f"duplicate knowledge guard: {guard['id']}"
        guard_ids.add(guard["id"])
        if error:
            _finding(report, "FAIL", "INVALID_KNOWLEDGE_REFERENCE", ref, error)
            continue
        checkpoint_contract = {**contract, "knowledge_checkpoint": guard.get("checkpoint", contract.get("knowledge_checkpoint"))}
        _knowledge_value(checkpoint_contract, target, projector, report, ref)
    _finding(report, "PENDING", "SCENE_CHAIN_UNDECLARED", scene_ref,
             "no proved predecessor/checkpoint binding; no chapter-adjacency or sparse-scene chain inferred")
    if contract.get("exit_state"):
        _finding(report, "PENDING", "EXIT_EVENTS_UNPROVED", scene_ref, "exit values are contract declarations, not proved actual events")
    references.sort(key=lambda row: (row["target"], row["field"], row["ref"]))
    return scene


def _inspect(root: Path, chapter: int | None) -> tuple[dict, SceneStateProjector, set[str]]:
    scope = project_chapters(root)
    if chapter is not None and (type(chapter) is not int or chapter not in scope):
        raise ValueError(f"chapter outside configured project scope: {chapter}")
    selected = (chapter,) if chapter is not None else scope
    refs = {"data/project/scope.json", "data/reconstruction/m2.json", "data/prewrite/v06.json",
            "data/objects/m4.json", KNOWLEDGE_PATH, "schemas/scene_contract.schema.json"}
    refs.update(f"data/world/{name}.json" for name in ("m3_core", "m3_locations", "m3_presence", "m3_body", "m3_resources", "m3_knowledge"))
    report = {**BOUNDARY, "kind": "BOUNDED_SPARSE_CONTINUITY", "chapter": chapter,
              "checks": [], "scenes": [], "source_context": [], "bridge_overlaps": [],
              "scene_chains": [], "automatic_repair": False}
    reconstruction = ReconstructionRegistry.from_repo(root)
    prewrite = V5PrewriteRuntime.from_repo(root)
    projector = SceneStateProjector(root)
    refs.update(projector.registered_objects)
    contracts = []
    for path in sorted((root / "data/scenes").glob("*.yaml")):
        contract = load_data(path)
        scene_ref = path.relative_to(root).as_posix()
        refs.add(scene_ref)
        if not isinstance(contract, dict):
            _finding(report, "FAIL", "INVALID_SCENE_STRUCTURE", scene_ref, "expected an object")
            continue
        if type(contract.get("chapter")) is not int or contract["chapter"] not in scope:
            _finding(report, "FAIL", "SCENE_OUTSIDE_SCOPE", scene_ref, str(contract.get("chapter")))
        elif contract["chapter"] in selected:
            contracts.append((contract, scene_ref))
    seen_ids = set()
    for contract, scene_ref in sorted(contracts, key=lambda item: (item[0]["chapter"], str(item[0].get("id")), item[1])):
        identity = contract.get("id")
        if not isinstance(identity, str) or not identity.strip():
            _finding(report, "FAIL", "INVALID_SCENE_ID", scene_ref, "expected a nonempty scene id")
            continue
        if identity in seen_ids:
            _finding(report, "FAIL", "DUPLICATE_SCENE_ID", scene_ref, identity)
        seen_ids.add(identity)
        report["scenes"].append(_scene(contract, scene_ref, report, refs, projector, root))
    covered = sorted({contract["chapter"] for contract, _ in contracts})
    missing = sorted(set(selected) - set(covered))
    report["coverage"] = {"scope_chapters": list(scope), "requested_chapters": list(selected),
                          "scene_contracts": len(contracts), "covered_chapters": covered,
                          "missing_chapters": missing, "complete": not missing}
    if missing:
        _finding(report, "PENDING", "SPARSE_SCENE_COVERAGE", "data/scenes", f"missing scene contracts for chapters {missing}")
    chain = unique_index(reconstruction.data.get("central_state_chain", []), "chapter")
    for current in selected:
        contexts = (("reconstruction_chapter", reconstruction.chapters), ("reconstruction_timeline", reconstruction.timeline),
                    ("reconstruction_state", reconstruction.states), ("central_state_chain", chain),
                    ("prewrite_gap", prewrite.gaps), ("prewrite_scene_plan", prewrite.planners))
        for label, collection in contexts:
            item = collection.get(current)
            context_ref = f"{label}:ch{current}"
            refs.add(context_ref)
            if item is None:
                _finding(report, "PENDING", "SOURCE_CONTEXT_MISSING", context_ref, "no selected record")
                report["source_context"].append({"ref": context_ref, "present": False, "checkpoint": None})
                continue
            if item.get("source_ref"):
                refs.add(item["source_ref"])
            # Existing sources mix before/end-state and prose. Do not manufacture a
            # canonical time or target mapping from their labels or chapter number.
            report["source_context"].append({"ref": context_ref, "present": True, "checkpoint": None,
                                             "comparison": "UNMAPPED_SOURCE_CONTEXT"})
            _finding(report, "PENDING", "SOURCE_CHECKPOINT_UNDECLARED", context_ref,
                     "no explicit canonical scene/checkpoint binding; source prose is not replayed")
        overlaps = projector.bridge_overlaps(current)
        report["bridge_overlaps"].extend(overlaps)
        for overlap in overlaps:
            refs.add(overlap["legacy_ref"])
            if overlap["status"] not in {"MATCH", "REFINES"}:
                _finding(report, "PENDING", "BRIDGE_MANUAL_REVIEW", overlap["legacy_ref"],
                         f"ch{current}/{overlap['field']}: {overlap['status']}; independent IDs are not auto-aliased")
    return report, projector, refs


def continuity_report(root: Path, chapter: int | None = None) -> dict:
    """Inspect sparse declared scene state, never promote or repair it."""
    try:
        report, _, refs = _inspect(root, chapter)
        return _finish(report, refs)
    except (KeyError, OSError, TypeError, ValueError) as exc:
        return diagnostic_failure("BOUNDED_SPARSE_CONTINUITY", exc)


def impact_report(root: Path, target: str) -> dict:
    """Return only exact canonical contract references to one state target."""
    try:
        target = _target(target)
        report, projector, refs = _inspect(root, None)
        report["kind"] = "DIRECT_STATE_IMPACT"
        report["target"] = target
        refs.add(target)
        error = _reference_error(target, projector)
        if error:
            _finding(report, "FAIL", "INVALID_IMPACT_TARGET", target, error)
        direct = [{"scene_id": scene["id"], "chapter": scene["chapter"], **reference}
                  for scene in report["scenes"] for reference in scene["references"]
                  if reference["target"] == target]
        report["direct_references"] = sorted(direct, key=lambda row: (row["chapter"], row["scene_id"], row["field"], row["ref"]))
        report["affected_scene_ids"] = sorted({row["scene_id"] for row in direct})
        report["inference"] = "EXACT_CANONICAL_REFERENCES_ONLY"
        report["transitive_impact"] = "NOT_INFERRED"
        if not error and not direct:
            _finding(report, "PENDING", "NO_DIRECT_REFERENCES", target, "sparse absence is not proof of no impact")
        if not error and target.split(".")[2] != "knowledge":
            values, _ = projector.entry({"chapter": projector.world.data["baseline"]["chapter"] + 1})
            report["target_present"] = target in values
            report["target_value"] = values.get(target)
            if target not in values:
                _finding(report, "PENDING", "STATE_VALUE_MISSING", target, "known entity but no selected baseline field")
        return _finish(report, refs)
    except (KeyError, OSError, TypeError, ValueError) as exc:
        return diagnostic_failure("DIRECT_STATE_IMPACT", exc)
