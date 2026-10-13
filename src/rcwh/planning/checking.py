"""Only explicit planning links are checked; no invented state propagation."""
from __future__ import annotations
from pathlib import Path
from ..assets.paths import repository_path
from ..io import load_data
from ..schema import validate_instance
from ..evaluation.state import canonical_target, normalized
from .chapters import ChapterPlans
from .references import BOUNDARY, verify_citation, verify_record


def check_selected(root: Path, chapters=None, *, directory=None, contracts_directory=None) -> dict:
    checks, scenes, plans = [], [], []
    contract_reports, effective_scenes, used_seeds, overlay_refs = [], {}, set(), {}
    overlays = None
    def add(status, code, ref, detail):
        checks.append({"status": status, "code": code, "ref": ref, "detail": detail})
    if contracts_directory is not None:
        from .contracts import AgentContracts
        try:
            overlays = AgentContracts(root, contracts_directory)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            add("FAIL", "CONTRACT_SELECTION_INVALID", contracts_directory, str(exc))
    runtime = ChapterPlans(root, directory)
    try:
        selected = list(chapters) if chapters is not None else [x["chapter"] for x in runtime.selected()]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        selected = []
        add("FAIL", "PLAN_READ_ERROR", runtime.directory, str(exc))
    for chapter in selected:
        ref = f"{runtime.directory}/ch{chapter}.json"
        try:
            plan = runtime.get(chapter)
            errors = validate_instance(plan, root / "schemas/chapter_plan.schema.json")
            for error in errors:
                add("FAIL", "INVALID_PLAN_STRUCTURE", ref, error)
            if errors:
                continue
            plans.append(plan)
            if plan.get("source"):
                for error in verify_citation(root, plan["source"]):
                    add("FAIL", error, ref, "card bytes/line references changed")
            if plan.get("card_fields") and [x["number"] for x in plan["card_fields"]] != list(range(1, 19)):
                add("FAIL", "CARD_FIELDS_INVALID", ref, "expected 18 ordered fields")
            for field in plan.get("card_fields", []):
                for error in verify_citation(root, field["citation"], field["text"]):
                    add("FAIL", error, ref, str(field["number"]))
            for source in plan.get("source_records", []):
                for error in verify_record(root, source):
                    add("FAIL", error, ref, source.get("ref", ""))
            if plan["status"] != "EDITED" or plan["unresolved"]:
                add("PENDING", "DRAFT_PLAN_UNRESOLVED", ref, ", ".join(plan["unresolved"]))
            if not plan["scenes"]:
                add("PENDING", "SCENE_COVERAGE_MISSING", ref, "no declared scenes")
            previous = None
            for index, item in enumerate(plan["scenes"], 1):
                if item["order"] != index:
                    add("FAIL", "SCENE_ORDER_MISMATCH", item["ref"], "list order must match declared consecutive order")
                scene = load_data(repository_path(root, item["ref"]))
                if scene.get("id") != item["id"] or scene.get("chapter") != chapter or scene.get("order", index) != index:
                    add("FAIL", "SCENE_BINDING_MISMATCH", item["ref"], "id/chapter/order differs from plan declaration")
                if scene.get("chapter_plan_ref", ref) != ref:
                    add("FAIL", "CHAPTER_PLAN_LINK_MISMATCH", item["ref"], ref)
                if scene.get("source_record"):
                    for error in verify_record(root, scene["source_record"]):
                        add("FAIL", error, item["ref"], "scene source changed")
                overlay_ref = None
                if overlays is not None:
                    selected_overlay = overlays.get(item["ref"])
                    if selected_overlay is None:
                        add("PENDING", "AGENT_CONTRACT_MISSING", item["ref"], "no explicit selected overlay; skeleton not promoted")
                    else:
                        from .contracts import inspect_contract
                        overlay_ref, scene = selected_overlay
                        used_seeds.add(item["ref"])
                        overlay_refs[item["ref"]] = overlay_ref
                        report = inspect_contract(root, scene, overlay_ref, seed_ref=item["ref"], plan_ref=ref)
                        contract_reports.append(report)
                        for tier in ("declared_compatibility", "deterministic_world_state_replay", "prose_supported_semantic_replay"):
                            for finding in report[tier]["checks"]:
                                add(**finding)
                effective_scenes[item["ref"]] = scene
                expected = previous[0]["ref"] if previous else plan["entry_ref"]
                actual = scene.get("entry_from")
                if not actual or actual == "UNKNOWN" or not expected:
                    add("PENDING", "SCENE_CHAIN_UNDECLARED", item["ref"], "no explicit predecessor binding")
                elif (actual not in {expected, previous[1]["id"] if previous else expected,
                                    overlay_refs.get(expected, expected)}
                      and not _identical_selected_predecessor(root, actual, overlay_refs.get(expected))):
                    add("FAIL", "SCENE_CHAIN_MISMATCH", item["ref"], f"expected {expected}, declared {actual}")
                else:
                    add("PASS", "SCENE_CHAIN_DECLARED", item["ref"], "declaration consistency only")
                if scene.get("entry_from") and not overlay_ref:
                    for error in validate_instance(scene, root / "schemas/scene_contract.schema.json"):
                        add("FAIL", "INVALID_SCENE_STRUCTURE", item["ref"], error)
                if previous:
                    _state_link(previous[1], scene, item["ref"], add)
                previous = (item, scene)
                scenes.append((item["ref"], scene))
            for existing in plan.get("existing_contracts", []):
                contract = load_data(repository_path(root, existing["ref"]))
                if contract.get("id") != existing["id"] or contract.get("chapter") != chapter:
                    add("FAIL", "EXISTING_CONTRACT_MISMATCH", existing["ref"], "id/chapter differs")
                if existing.get("placement_status") == "PENDING":
                    add("PENDING", "EXISTING_CONTRACT_PLACEMENT", existing["ref"], "not positioned into draft scene order")
                scenes.append((existing["ref"], contract))
        except (OSError, ValueError, KeyError, TypeError) as exc:
            add("FAIL", "PLAN_READ_ERROR", ref, str(exc))
    if len(selected) != len(set(selected)):
        add("FAIL", "DUPLICATE_CHAPTER_SELECTION", "chapters", "chapter selection must be unique")
    by_chapter = {x["chapter"]: x for x in plans}
    for chapter, plan in sorted(by_chapter.items()):
        prior = by_chapter.get(chapter - 1)
        if not prior or not prior["exit_ref"] or not plan["entry_ref"]:
            add("PENDING", "CHAPTER_BOUNDARY_UNDECLARED", f"ch{chapter}", "previous exit/entry absent or outside selection")
        elif prior["exit_ref"] != plan["entry_ref"]:
            add("FAIL", "CHAPTER_BOUNDARY_MISMATCH", f"ch{chapter}", f"{prior['exit_ref']} != {plan['entry_ref']}")
        else:
            add("PASS", "CHAPTER_BOUNDARY_DECLARED", f"ch{chapter}", "matching declaration; not semantic replay")
            if prior["scenes"] and plan["scenes"]:
                try:
                    exit_ref = prior["scenes"][-1]["ref"]
                    entry_ref = plan["scenes"][0]["ref"]
                    exit_scene = effective_scenes.get(exit_ref) or load_data(repository_path(root, exit_ref))
                    entry_scene = effective_scenes.get(entry_ref) or load_data(repository_path(root, entry_ref))
                    _state_link(exit_scene, entry_scene, f"ch{chapter}", add)
                except (OSError, ValueError, KeyError, TypeError) as exc:
                    add("FAIL", "CHAPTER_STATE_LINK_INVALID", f"ch{chapter}", str(exc))
    ids = [scene.get("id") for _, scene in scenes]
    if len(ids) != len(set(ids)):
        add("FAIL", "DUPLICATE_SCENE_ID", "scenes", "scene ids must be unique")
    if overlays is not None:
        for seed_ref, (overlay_ref, contract) in overlays.by_seed.items():
            if contract["chapter"] in selected and seed_ref not in used_seeds:
                add("FAIL", "CONTRACT_SEED_NOT_SELECTED", overlay_ref, seed_ref)
    _direct_checks(root, selected, scenes, add)
    checks.sort(key=lambda row: (row["ref"], row["code"], row["detail"]))
    statuses = {x["status"] for x in checks}
    result = {**BOUNDARY, "kind": "PLANNING_DECLARATION_CONSISTENCY", "status": "FAIL" if "FAIL" in statuses else "PENDING" if statuses & {"PENDING", "NOT_CHECKED"} else "PASS",
              "chapters": selected, "checks": checks, "semantic_verified_replay": "NOT_CHECKED", "automatic_repair": False}
    if contracts_directory is not None:
        from .contracts import _status
        replay_checks = [finding for report in contract_reports for finding in report["deterministic_world_state_replay"]["checks"]]
        other_tiers = {(finding["code"], finding["ref"], finding["detail"])
                       for report in contract_reports for tier in ("deterministic_world_state_replay", "prose_supported_semantic_replay")
                       for finding in report[tier]["checks"]}
        declared_checks = [finding for finding in checks if (finding["code"], finding["ref"], finding["detail"]) not in other_tiers]
        result.update({"contracts_directory": contracts_directory, "agent_contracts": contract_reports,
                       "declared_compatibility": {"status": _status(declared_checks), "scope": "DECLARATION_CONSISTENCY_ONLY"},
                       "deterministic_world_state_replay": {"status": _status(replay_checks), "scope": "SELECTED_OVERLAYS_ONLY_NOT_WHOLE_PLAN"},
                       "prose_supported_semantic_replay": {"status": "NOT_CHECKED"}})
    return result


def _identical_selected_predecessor(root: Path, actual: str, selected: str | None) -> bool:
    """Relocated immutable copies may name their original byte-identical source."""
    if selected is None or not isinstance(actual, str):
        return False
    try:
        original = repository_path(root, actual)
        current = repository_path(root, selected)
        if original == current:
            return True
        return original.is_file() and original.read_bytes() == current.read_bytes()
    except (OSError, ValueError):
        return False


def _state_link(previous, current, ref, add):
    agent = any(scene.get("kind") == "AGENT_SCENE_CONTRACT" for scene in (previous, current))
    def states(rows):
        values = {}
        for row in rows or []:
            target = canonical_target(row["equals"])
            if target in values:
                raise ValueError(f"duplicate state target {target}")
            value = row["value"]
            if agent and (row.get("status", "KNOWN") != "KNOWN" or value is None or isinstance(value, str) and value.upper() in {"UNKNOWN", "PENDING", "UNSPECIFIED"}):
                add("PENDING", "EXIT_ENTRY_STATE_UNKNOWN", ref, target)
                continue
            values[target] = normalized(value)
        return values
    exit_values = states(previous.get("exit_state"))
    entry_values = states((current.get("entry_state") or []) + (current.get("preconditions") or [])) if not current.get("entry_state") else states(current["entry_state"])
    common = exit_values.keys() & entry_values.keys()
    if not common:
        add("PENDING", "EXIT_ENTRY_STATE_UNBOUND", ref, "no common explicit state targets")
    for target in sorted(common):
        add("PASS" if exit_values[target] == entry_values[target] else "FAIL", "EXIT_ENTRY_STATE_MATCH" if exit_values[target] == entry_values[target] else "EXIT_ENTRY_STATE_MISMATCH", ref, target)


def _direct_checks(root, selected, scenes, add):
    """Reuse bounded runtime checks where its selected world actually applies."""
    from ..evaluation.continuity import _scene
    from ..evaluation.state import SceneStateProjector
    if (root / "data/world/m3_core.json").exists():
        try:
            projector = SceneStateProjector(root)
            scope = load_data(root / "data/project/scope.json")["chapters"]
            for ref, scene in scenes:
                if scene.get("kind") == "AGENT_SCENE_CONTRACT":
                    continue  # Dedicated overlay inspection excludes self-injected entry declarations.
                if scene.get("kind") == "SCENE_SKELETON":
                    add("PENDING", "SCENE_STATE_UNRESOLVED", ref, "draft skeleton is not a complete contract")
                elif scene["chapter"] in scope:
                    report = {"checks": []}
                    _scene(scene, ref, report, set(), projector, root)
                    for item in report["checks"]:
                        if item["code"] != "SCENE_CHAIN_UNDECLARED":
                            add(**item)
                else:
                    add("PENDING", "WORLD_SCOPE_UNSUPPORTED", ref, "selected production world cannot verify this chapter")
        except (OSError, KeyError, ValueError, TypeError) as exc:
            add("FAIL", "DIRECT_STATE_CHECK_ERROR", "world", str(exc))
    else:
        add("PENDING", "WORLD_REFERENCE_UNAVAILABLE", "world", "no selected world; no default fabricated")
    from ..knowledge import KNOWLEDGE_PATH
    knowledge_path = root / KNOWLEDGE_PATH
    if knowledge_path.exists():
        knowledge_scenes = load_data(knowledge_path).get("scenes", [])
        known_events = {event["id"]: (row, event) for row in knowledge_scenes for event in row.get("events", [])}
        for ref, scene in scenes:
            previous_sequence = None
            for identity in scene.get("knowledge_event_refs", []):
                if identity not in known_events:
                    add("FAIL", "INVALID_KNOWLEDGE_EVENT_REFERENCE", ref, identity)
                    continue
                source_scene, event = known_events[identity]
                if source_scene["chapter"] != scene["chapter"]:
                    add("FAIL", "KNOWLEDGE_EVENT_CHAPTER_MISMATCH", ref, identity)
                if previous_sequence is not None and event["sequence"] <= previous_sequence:
                    add("FAIL", "KNOWLEDGE_ACQUISITION_ORDER_MISMATCH", ref, identity)
                previous_sequence = event["sequence"]
            for guard in scene.get("knowledge_guards", []):
                checkpoint = guard.get("checkpoint", scene.get("knowledge_checkpoint"))
                if checkpoint not in {None, "ENTRY", "FINAL"} and checkpoint not in known_events:
                    add("FAIL", "INVALID_KNOWLEDGE_CHECKPOINT", ref, str(checkpoint))
        for source_scene in knowledge_scenes:
            if source_scene["chapter"] not in selected:
                continue
            if not any(scene.get("id") == source_scene["id"] or (scene.get("knowledge_binding") or {}).get("scene_id") == source_scene["id"] for _, scene in scenes):
                add("PENDING", "KNOWLEDGE_SCENE_UNCOVERED", source_scene["id"], "knowledge acquisitions have no direct selected scene")
            for event in source_scene.get("events", []):
                if not any(event["id"] in scene.get("knowledge_event_refs", []) for _, scene in scenes):
                    add("PENDING", "KNOWLEDGE_EVENT_ORDER_UNBOUND", event["id"], "no plan-scene acquisition binding; source event order is not propagated")
    for path, key, binding, code in [("data/objects/m4.json", "transitions", "object_transition_refs", "OBJECT_TRAJECTORY_SCENE_MISSING"), ("data/world/m3_core.json", "events", "event_refs", "WORLD_EVENT_SCENE_MISSING")]:
        if not (root / path).exists():
            continue
        records = load_data(root / path).get(key, [])
        known = {x["id"]: x for x in records}
        for ref, scene in scenes:
            for identity in scene.get(binding, []):
                if identity not in known or known[identity]["chapter"] != scene["chapter"]:
                    add("FAIL", "INVALID_DIRECT_EVENT_REFERENCE", ref, identity)
        for row in records:
            if row["chapter"] in selected and not any(row["id"] in scene.get(binding, []) for _, scene in scenes):
                add("PENDING", code, f"{path}#{row['id']}", "event has no explicit scene binding; no prose match inferred")
