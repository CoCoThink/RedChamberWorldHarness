"""Opt-in, byte-bound agent overlays; no source mutation or editorial attestations.

Author with ``draft_contract`` then explicitly ``write_contract`` to a new
``data/planning/contracts/<selection>/<id>.vN.json``. A selection must contain
one revision per seed. UNKNOWN is an epistemic marker, never a matched value.
Replay below checks only declared targets against supported registered events;
it neither proves prose nor manufactures scene-local entry state.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from ..assets.paths import repository_path
from ..evaluation.state import SceneStateAdapter, SceneStateProjector, canonical_target, normalized
from ..io import load_data
from ..knowledge import KNOWLEDGE_PATH
from ..schema import validate_instance
from .references import BOUNDARY, digest, verify_record, write_new

CONTRACT_DIRECTORY = "data/planning/contracts"
WORLD_INPUTS = (
    "data/project/scope.json",
    *(f"data/world/m3_{name}.json" for name in ("core", "locations", "presence", "body", "resources", "knowledge")),
    "data/objects/m4.json", KNOWLEDGE_PATH,
)


def file_binding(root: Path, ref: str) -> dict:
    return {"path": ref, "sha256": digest(repository_path(root, ref).read_bytes())}


def _directory(root: Path, ref: str) -> Path:
    path = repository_path(root, ref)
    base = repository_path(root, CONTRACT_DIRECTORY)
    if path == base or not path.is_relative_to(base):
        raise ValueError("contract selection must be a subdirectory of data/planning/contracts")
    return path


def draft_contract(root: Path, seed_ref: str, source_packet: str, *, revision: str = "v1") -> dict:
    """Return an honest UNKNOWN scaffold, without writing or inventing edits."""
    root = root.resolve()
    seed = load_data(repository_path(root, seed_ref))
    plan_ref = seed["chapter_plan_ref"]
    available = all(repository_path(root, ref).is_file() for ref in WORLD_INPUTS)
    registered = sorted(path.relative_to(root).as_posix() for path in (root / "data/objects").glob("*.yaml"))
    world = {"status": "BOUND" if available else "UNKNOWN",
             "inputs": [file_binding(root, ref) for ref in (*WORLD_INPUTS, *registered) if repository_path(root, ref).is_file()]}
    if not available:
        world["reason"] = "selected adapter inputs unavailable; no substitute world inferred"
    return {**BOUNDARY, "schema_version": 1, "kind": "AGENT_SCENE_CONTRACT", "revision": revision,
            "id": seed["id"], "chapter": seed["chapter"], "order": seed["order"],
            "chapter_plan_ref": plan_ref, "status": "DRAFT_GENERATED",
            "bindings": {"source_packet": file_binding(root, source_packet), "seed": file_binding(root, seed_ref),
                         "chapter_plan": file_binding(root, plan_ref), "world": world},
            "entry_from": "UNKNOWN", "entry_checkpoint": {"kind": "UNKNOWN", "chapter": None},
            "participants": [], "participants_status": "UNKNOWN", "required_objects": [],
            "references": {"participants": [], "objects": [], "knowledge": []},
            "entry_state": [], "preconditions": [], "exit_state": [], "required_beats": [], "forbidden_beats": [],
            "event_refs": [], "object_transition_refs": [], "knowledge_event_refs": [], "knowledge_binding": None,
            "unresolved": ["entry_from", "entry_checkpoint", "participants", "entry_state", "exit_state", "event_bindings"]}


def write_contract(root: Path, contract: dict, *, directory: str) -> str:
    """Create a new revision with xb; never overwrite an earlier revision."""
    root = root.resolve()
    errors = validate_instance(contract, root / "schemas/agent_scene_contract.schema.json")
    if errors:
        raise ValueError("invalid agent contract: " + "; ".join(errors))
    base = _directory(root, directory)
    path = base / f"{contract['id']}.{contract['revision']}.json"
    write_new(path, contract)
    return path.relative_to(root.resolve()).as_posix()


class AgentContracts:
    """Explicit selection only. Ambiguous revisions fail rather than pick latest."""

    def __init__(self, root: Path, directory: str):
        self.root = root.resolve()
        self.directory = directory
        path = _directory(self.root, directory)
        if not path.is_dir():
            raise ValueError(f"contract selection does not exist: {directory}")
        self.by_seed = {}
        ids = set()
        for file in sorted(path.glob("*.json")):
            contract = load_data(repository_path(self.root, file.relative_to(self.root).as_posix()))
            errors = validate_instance(contract, self.root / "schemas/agent_scene_contract.schema.json")
            if errors:
                raise ValueError(f"{file.name}: " + "; ".join(errors))
            if file.name != f"{contract['id']}.{contract['revision']}.json":
                raise ValueError(f"contract filename must bind id and revision: {file.name}")
            seed = contract["bindings"]["seed"]["path"]
            if seed in self.by_seed or contract["id"] in ids:
                raise ValueError(f"ambiguous selected contract revisions: {contract['id']}")
            ids.add(contract["id"])
            self.by_seed[seed] = (file.relative_to(self.root).as_posix(), contract)

    def get(self, seed_ref: str):
        return self.by_seed.get(seed_ref)


def _status(checks: list[dict], *, empty: str = "NOT_CHECKED") -> str:
    statuses = {row["status"] for row in checks}
    return "FAIL" if "FAIL" in statuses else "PENDING" if "PENDING" in statuses else "NOT_CHECKED" if "NOT_CHECKED" in statuses else "PASS" if statuses else empty


def inspect_contract(root: Path, contract: dict, ref: str, *, seed_ref: str, plan_ref: str) -> dict:
    """Return three distinct tiers. All findings are read-only staging diagnostics."""
    root = root.resolve()
    declared, replay = [], []
    def add(rows, status, code, detail):
        rows.append({"status": status, "code": code, "ref": ref, "detail": detail})
    def declaration(status, code, detail):
        add(declared, status, code, detail)
    def deterministic(status, code, detail):
        add(replay, status, code, detail)

    errors = validate_instance(contract, root / "schemas/agent_scene_contract.schema.json")
    for error in errors:
        declaration("FAIL", "INVALID_AGENT_CONTRACT", error)
    if errors:
        return _report(ref, declared, replay)
    bindings = contract["bindings"]
    inputs = [bindings[key] for key in ("source_packet", "seed", "chapter_plan")]
    inputs += bindings["world"]["inputs"]
    if bindings.get("prose"):
        inputs.append(bindings["prose"])
    for binding in inputs:
        try:
            actual = file_binding(root, binding["path"])
            if actual != binding:
                declaration("FAIL", "CONTRACT_INPUT_BYTES_CHANGED", binding["path"])
        except (OSError, ValueError) as exc:
            declaration("FAIL", "CONTRACT_INPUT_UNAVAILABLE", str(exc))
    if bindings["seed"]["path"] != seed_ref or bindings["chapter_plan"]["path"] != plan_ref or contract["chapter_plan_ref"] != plan_ref:
        declaration("FAIL", "CONTRACT_SOURCE_BINDING_MISMATCH", "seed/plan paths differ from selected declarations")
    try:
        seed = load_data(repository_path(root, seed_ref))
        if any(contract[key] != seed[key] for key in ("id", "chapter", "order")):
            declaration("FAIL", "CONTRACT_SEED_ID_MISMATCH", "id/chapter/order differs from immutable seed")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        declaration("FAIL", "CONTRACT_SEED_UNAVAILABLE", str(exc))
    paths = [binding["path"] for binding in bindings["world"]["inputs"]]
    if len(paths) != len(set(paths)):
        declaration("FAIL", "DUPLICATE_WORLD_INPUT", "world input paths must be unique")
    if bindings["world"]["status"] == "UNKNOWN":
        declaration("PENDING", "CONTRACT_WORLD_UNKNOWN", bindings["world"].get("reason", "world not bound"))
    elif not set(WORLD_INPUTS) <= set(paths):
        declaration("FAIL", "CONTRACT_WORLD_BINDING_INCOMPLETE", "all selected adapter inputs must be byte-bound")
    registered_paths = {path.relative_to(root).as_posix() for path in (root / "data/objects").glob("*.yaml")}
    if bindings["world"]["status"] == "BOUND" and not registered_paths <= set(paths):
        declaration("FAIL", "CONTRACT_OBJECT_BINDING_INCOMPLETE", "adapter registered object inputs must be byte-bound")
    for condition in contract["entry_state"] + contract["preconditions"] + contract["exit_state"]:
        for basis in condition["basis"]:
            if basis["path"].startswith("data/planning/") or basis["path"].startswith("data/scenes/"):
                declaration("FAIL", "CONTRACT_DECLARATION_NOT_STATE_BASIS", basis["ref"])
    if contract["status"] == "DRAFT_GENERATED":
        declaration("PENDING", "CONTRACT_DRAFT_GENERATED", "generation is not an edit or verification")
    if contract["unresolved"]:
        declaration("PENDING", "CONTRACT_UNRESOLVED", ", ".join(contract["unresolved"]))
    if contract["entry_from"] == "UNKNOWN":
        declaration("PENDING", "CONTRACT_PREDECESSOR_UNKNOWN", "no predecessor inferred")
    if contract["participants_status"] != "KNOWN" or not contract["participants"]:
        declaration("PENDING", "CONTRACT_PARTICIPANTS_UNRESOLVED", "no justified participant set")

    records = []
    for group in contract["references"].values():
        records.extend(group)
    for field in ("entry_state", "preconditions", "exit_state"):
        seen = set()
        if field != "preconditions" and not contract[field]:
            declaration("PENDING", "CONTRACT_STATE_UNDECLARED", field)
        for condition in contract[field]:
            target = canonical_target(condition["equals"])
            if target in seen:
                declaration("FAIL", "CONTRACT_DUPLICATE_STATE_TARGET", f"{field}: {target}")
            seen.add(target)
            records.extend(condition["basis"])
            if condition["status"] != "KNOWN" or _unknown(condition["value"]):
                declaration("PENDING", "CONTRACT_STATE_UNKNOWN", f"{field}: {target}")
    for item in records:
        for error in verify_record(root, item):
            declaration("FAIL", "CONTRACT_REFERENCE_INVALID", f"{item.get('ref')}: {error}")
    _entity_bindings(contract, declaration)

    if any(row["status"] == "FAIL" for row in declared) or bindings["world"]["status"] != "BOUND":
        deterministic("NOT_CHECKED", "CONTRACT_REPLAY_INPUTS_UNAVAILABLE", "invalid/unbound inputs cannot be replayed")
    else:
        try:
            projector = SceneStateProjector(root)
            _replay(contract, projector, deterministic)
        except (OSError, KeyError, ValueError, TypeError) as exc:
            deterministic("NOT_CHECKED", "CONTRACT_REPLAY_UNAVAILABLE", str(exc))
    if not any(row["status"] == "FAIL" for row in declared):
        declaration("PASS", "CONTRACT_BINDINGS_DECLARED", "byte/reference consistency only; not semantic support")
    return _report(ref, declared, replay)


def _unknown(value):
    return value is None or isinstance(value, str) and value.upper() in {"UNKNOWN", "UNSPECIFIED", "PENDING"}


def _entity_bindings(contract, add):
    allowed = {"participants": {"data/world/m3_core.json", KNOWLEDGE_PATH},
               "objects": {"data/objects/m4.json"}, "knowledge": {KNOWLEDGE_PATH}}
    prefixes = {"participants": "/characters/", "objects": "/objects/", "knowledge": "/facts/"}
    known = {}
    for group, records in contract["references"].items():
        known[group] = set()
        for item in records:
            identity = item["value"].get("id") if isinstance(item["value"], dict) else None
            registered = group == "objects" and item["path"].startswith("data/objects/") and item["path"].endswith(".yaml") and item["pointer"] == ""
            pointer_parts = item["pointer"].split("/")
            registry_record = (item["path"] in allowed[group] and item["pointer"].startswith(prefixes[group])
                               and len(pointer_parts) == 3 and pointer_parts[-1].isdigit())
            if identity and (registered or registry_record):
                known[group].add(identity)
            else:
                add("FAIL", "CONTRACT_ENTITY_REFERENCE_INVALID", item["ref"])
    for group, identities in (("participants", contract["participants"]), ("objects", contract["required_objects"])):
        for identity in identities:
            if identity not in known[group]:
                add("FAIL", "CONTRACT_ENTITY_UNGROUNDED", f"{group}: {identity}")
    for field in ("entry_state", "preconditions", "exit_state"):
        for condition in contract[field]:
            parts = canonical_target(condition["equals"]).split(".")
            group = "objects" if parts[0] == "object" else "participants"
            if parts[1] not in known[group]:
                add("FAIL", "CONTRACT_STATE_ENTITY_UNGROUNDED", condition["equals"])
            if parts[0] == "character" and parts[2] == "knowledge" and (len(parts) != 4 or parts[3] not in known["knowledge"]):
                add("FAIL", "CONTRACT_KNOWLEDGE_UNGROUNDED", condition["equals"])


def _flatten(prefix, value, values):
    if isinstance(value, dict):
        for key, item in value.items():
            _flatten(f"{prefix}.{key}", item, values)
    else:
        values[prefix] = normalized(value)


def _replay(contract, projector, add):
    if contract["chapter"] not in projector.world.presence or contract["chapter"] not in projector.objects.chapter_scope:
        add("NOT_CHECKED", "CONTRACT_WORLD_SCOPE_UNSUPPORTED", "selected adapter world/object runtimes do not support this chapter")
        return
    checkpoint = contract["entry_checkpoint"]
    expected = max(projector.world.data["baseline"]["chapter"], contract["chapter"] - 1)
    if checkpoint != {"kind": "CHAPTER_ENTRY", "chapter": expected} or contract["order"] != 1:
        add("NOT_CHECKED", "CONTRACT_ENTRY_CHECKPOINT_UNSUPPORTED", "only explicit first-scene chapter entry is supported; no local/predecessor state injected")
        return
    # Suppress local declarations: adapter entry_state otherwise overwrites actual
    # runtime state and would make a declaration compare equal to itself.
    adapter = SceneStateAdapter(projector.root, {**contract, "entry_state": []}, projector=projector)
    entry, exit_values = dict(adapter.values), dict(adapter.values)
    for actor in contract["participants"]:
        if actor not in projector.world.characters and actor not in projector.knowledge.characters:
            add("FAIL", "CONTRACT_UNKNOWN_PARTICIPANT", actor)
    world_events = {event["id"]: event for event in projector.world.data.get("events", [])}
    object_events = {event["id"]: event for event in projector.objects.transitions}
    world_order = [event["id"] for event in sorted(world_events.values(), key=lambda event: event["sequence"]) if event["chapter"] == contract["chapter"]]
    object_order = [event["id"] for event in projector.objects.transitions if event["chapter"] == contract["chapter"]]
    world_supported = _ordered_prefix(contract["event_refs"], world_order, add, "WORLD")
    object_supported = _ordered_prefix(contract["object_transition_refs"], object_order, add, "OBJECT")
    if not world_supported or not object_supported:
        return  # Non-prefix events are not an actual checkpoint replay.
    affected = set()
    replayed = []
    for identity in contract["event_refs"]:
        event = world_events.get(identity)
        if event is None or event["chapter"] != contract["chapter"]:
            add("FAIL", "CONTRACT_WORLD_EVENT_INVALID", identity)
            continue
        for effect in event.get("effects", []):
            parts = effect["set"].split(".")
            if len(parts) < 3 or parts[0] != "characters" or parts[1] not in projector.world.characters:
                add("NOT_CHECKED", "CONTRACT_WORLD_EFFECT_UNSUPPORTED", f"{identity}: {effect['set']}")
                continue
            target = canonical_target("character." + ".".join(parts[1:]))
            for existing in list(exit_values):
                if existing == target or existing.startswith(target + "."):
                    del exit_values[existing]
            updates = {}
            _flatten(target, effect.get("value"), updates)
            exit_values.update(updates)
            affected.update(updates)
        replayed.append(identity)
    states = {identity: projector.objects.snapshot(identity, expected)["state"] for identity in projector.objects.objects}
    for identity in contract["object_transition_refs"]:
        event = object_events.get(identity)
        if event is None or event["chapter"] != contract["chapter"] or event["object_id"] not in states:
            add("FAIL", "CONTRACT_OBJECT_EVENT_INVALID", identity)
            continue
        state = states[event["object_id"]]
        try:
            projector.objects._assert_from_matches(state, event)
        except ValueError as exc:
            add("FAIL", "CONTRACT_OBJECT_FROM_MISMATCH", str(exc))
            return
        if state.get("location") != event["to"].get("location") and event.get("movement") not in {"EXPLICIT", "OPEN_BOUNDARY", "DISCOVERY_FROM_UNKNOWN"}:
            add("FAIL", "CONTRACT_OBJECT_MOVEMENT_UNSUPPORTED", identity)
        prefix = f"object.{event['object_id']}."
        for target in list(exit_values):
            if target.startswith(prefix):
                del exit_values[target]
        _flatten(prefix.rstrip("."), event["to"], exit_values)
        affected.update(target for target in exit_values if target.startswith(prefix))
        states[event["object_id"]] = deepcopy(event["to"])
        replayed.append(identity)
    knowledge = contract["knowledge_binding"]
    knowledge_targets = {canonical_target(row["equals"]) for field in ("entry_state", "preconditions", "exit_state") for row in contract[field] if ".knowledge." in row["equals"]}
    if knowledge:
        source = projector.knowledge.scenes.get(knowledge["scene_id"])
        if source is None or source["chapter"] != contract["chapter"]:
            add("FAIL", "CONTRACT_KNOWLEDGE_SCENE_INVALID", knowledge["scene_id"])
        else:
            ordered = [event["id"] for event in sorted(source.get("events", []), key=lambda event: event["sequence"])]
            _ordered_prefix(contract["knowledge_event_refs"], ordered, add, "KNOWLEDGE")
            if contract["knowledge_event_refs"] == ordered[:len(contract["knowledge_event_refs"])]:
                end = contract["knowledge_event_refs"][-1] if contract["knowledge_event_refs"] else "ENTRY"
                for target in knowledge_targets:
                    _, actor, _, fact = target.split(".")
                    entry[target] = normalized(projector.knowledge.status(source["id"], actor, fact, "ENTRY"))
                    exit_values[target] = normalized(projector.knowledge.status(source["id"], actor, fact, end))
                    affected.add(target)
                replayed.extend(contract["knowledge_event_refs"])
                if contract["knowledge_event_refs"] and not knowledge_targets:
                    add("PENDING", "CONTRACT_KNOWLEDGE_TARGETS_UNDECLARED", "bound acquisitions have no explicit state comparison targets")
    elif knowledge_targets or contract["knowledge_event_refs"]:
        add("NOT_CHECKED", "CONTRACT_KNOWLEDGE_CHECKPOINT_UNBOUND", "knowledge requires an explicit registered source scene")
    comparisons = 0
    for field in ("entry_state", "preconditions", "exit_state"):
        for condition in contract[field]:
            target = canonical_target(condition["equals"])
            values = exit_values if field == "exit_state" else entry
            actual = values.get(target)
            if condition["status"] != "KNOWN" or _unknown(condition["value"]) or target not in values or _unknown(actual):
                add("PENDING", "CONTRACT_REPLAY_STATE_UNKNOWN", f"{field}: {target}; actual={actual!r}")
            elif field == "exit_state" and target not in affected:
                add("NOT_CHECKED", "CONTRACT_EXIT_TRANSITION_UNSUPPORTED", f"{target}: no bound event; persistence not inferred")
            else:
                comparisons += 1
                matches = actual == normalized(condition["value"])
                add("PASS" if matches else "FAIL", "CONTRACT_REPLAY_STATE_MATCH" if matches else "CONTRACT_REPLAY_STATE_MISMATCH", f"{field}: {target}; declared={condition['value']!r}, actual={actual!r}")
    if not comparisons or not replayed or not contract["entry_state"] or not contract["exit_state"]:
        add("PENDING", "CONTRACT_REPLAY_COVERAGE_INCOMPLETE", "requires supported explicit entry/exit targets and bound events; empty data is not replay success")
    if contract["status"] == "DRAFT_GENERATED" or contract["unresolved"] or contract["participants_status"] != "KNOWN" or not contract["participants"]:
        add("PENDING", "CONTRACT_REPLAY_DRAFT_INCOMPLETE", "draft/unresolved contract cannot receive an aggregate replay PASS")


def _ordered_prefix(selected, ordered, add, kind):
    if any(identity not in ordered for identity in selected):
        add("FAIL", f"CONTRACT_{kind}_EVENT_INVALID", "unknown event or event outside the selected chapter/scene")
        return False
    if selected != ordered[:len(selected)]:
        add("NOT_CHECKED", f"CONTRACT_{kind}_EVENT_ORDER_UNSUPPORTED", "selected events are not a consecutive prefix at the supported entry checkpoint")
        return False
    return True


def _report(ref, declared, replay):
    semantic = [{"status": "NOT_CHECKED", "code": "CONTRACT_PROSE_SEMANTICS_NOT_CHECKED", "ref": ref,
                 "detail": "byte-bound prose, if supplied, is not semantic replay; no provider or human attestation inferred"}]
    return {**BOUNDARY, "ref": ref,
            "declared_compatibility": {"status": _status(declared), "checks": declared},
            "deterministic_world_state_replay": {"status": _status(replay), "scope": "SUPPORTED_DECLARED_TARGETS_AND_REGISTERED_EVENT_PREFIXES_ONLY", "checks": replay},
            "prose_supported_semantic_replay": {"status": "NOT_CHECKED", "checks": semantic}}
