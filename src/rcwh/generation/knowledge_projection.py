"""Narrow, version-bound character-knowledge inputs for an individual task."""
from copy import deepcopy
from pathlib import Path

from ..candidate_reviews import canonical_bytes, digest
from ..knowledge_versions import KNOWLEDGE_VERSIONS, load_knowledge_version
from ..knowledge import BUCKETS
from .records import append_bytes, binding

KIND = "CHARACTER_KNOWLEDGE_PROJECTION"
RULES = ("src/rcwh/generation/knowledge_projection.py",
         "src/rcwh/knowledge_versions.py", "src/rcwh/knowledge.py")


def _index(items, field="id"):
    result = {}
    for item in items:
        key = item[field]
        if key in result:
            raise ValueError(f"duplicate knowledge projection {field}: {key}")
        result[key] = item
    return result


def _validate_event_order(events):
    sequences = [event.get("sequence") for event in events]
    if any(type(sequence) is not int or sequence < 0 for sequence in sequences):
        raise ValueError("knowledge event sequence must be a nonnegative integer")
    if len(sequences) != len(set(sequences)):
        raise ValueError("duplicate knowledge event sequence")


def rule_bindings(root: Path):
    return {path: binding(root, path)["sha256"] for path in RULES}


def project(root: Path, *, version: str, scene_id: str, checkpoints: list[str]):
    if version not in KNOWLEDGE_VERSIONS:
        raise ValueError(f"unknown character knowledge version: {version}")
    if not isinstance(checkpoints, list) or not checkpoints or checkpoints[0] != "ENTRY":
        raise ValueError("knowledge projection requires ENTRY and explicit checkpoints")
    if any(not isinstance(cp, str) or not cp for cp in checkpoints) or len(checkpoints) != len(set(checkpoints)):
        raise ValueError("knowledge projection checkpoints must be unique nonempty strings")
    runtime = load_knowledge_version(root, version)
    scene = runtime.scenes.get(scene_id)
    if scene is None:
        raise ValueError(f"unknown scene for {version}: {scene_id}")
    events = _index(scene.get("events", []))
    _validate_event_order(events.values())
    if not set(checkpoints) <= {"ENTRY", *events}:
        raise ValueError("unknown knowledge checkpoint")
    latest = max((events[cp]["sequence"] for cp in checkpoints if cp != "ENTRY"), default=None)
    selected_events = sorted((deepcopy(e) for e in events.values()
                              if latest is not None and e["sequence"] <= latest),
                             key=lambda e: e["sequence"])
    selected_scene = {**deepcopy(scene), "events": selected_events}

    referenced = {fact for state in selected_scene["entry"].values()
                  for bucket in BUCKETS for fact in state[bucket]}
    for event in selected_events:
        for update in event["updates"]:
            for operation in ("add", "remove"):
                referenced.update(fact for values in update[operation].values() for fact in values)
    facts = runtime.facts
    if not referenced <= facts.keys():
        raise ValueError("knowledge projection references undefined facts")
    selected = {key: deepcopy(value) for key, value in runtime.data.items()
                if key not in {"facts", "characters", "scenes"}}
    selected.update(
        facts=[deepcopy(facts[f]) for f in sorted(referenced)],
        characters=[deepcopy(runtime.characters[c]) for c in sorted(selected_scene["participants"])],
        scenes=[selected_scene],
    )
    projected_runtime = type(runtime)(root, selected)
    snapshots = {cp: projected_runtime.scene(scene_id, cp) for cp in checkpoints}
    carrier_path = KNOWLEDGE_VERSIONS[version]
    return {
        "kind": KIND,
        "protocol_version": 1,
        "knowledge_version": version,
        "carrier": binding(root, carrier_path),
        "rules": rule_bindings(root),
        "scene_id": scene_id,
        "fact_ids": sorted(referenced),
        "checkpoints": snapshots,
        "runtime": selected,
        "authority_effect": "NONE",
        "semantic_review": "NOT_COMPLETED",
    }


def verify(root: Path, document: dict):
    if (document.get("kind") != KIND or type(document.get("protocol_version")) is not int
            or document.get("protocol_version") != 1):
        raise ValueError("unsupported knowledge projection")
    expected = project(root, version=document["knowledge_version"], scene_id=document["scene_id"],
                       checkpoints=list(document["checkpoints"]))
    if canonical_bytes(document) != canonical_bytes(expected):
        raise ValueError("STALE_KNOWLEDGE_PROJECTION: version, carrier, facts, checkpoints or rules changed")


def create(root: Path, *, version: str, scene_id: str, checkpoints: list[str]):
    document = project(root, version=version, scene_id=scene_id, checkpoints=checkpoints)
    raw = canonical_bytes(document)
    projection = append_bytes(root, "data/writing/knowledge-projections/" + digest(raw) + ".json", raw)
    receipt = append_bytes(root, "artifacts/knowledge-projections/" + digest(raw) + ".json",
                           canonical_bytes({"kind": "KNOWLEDGE_PROJECTION_RECEIPT",
                                            "projection": projection,
                                            "source": document["carrier"],
                                            "rules": document["rules"],
                                            "authority_effect": "NONE"}))
    return {"projection": projection, "receipt": receipt, "status": "PASS",
            "authority_effect": "NONE", "semantic_review": "NOT_COMPLETED"}


def prepare_request(root: Path, *, projection_path: str, task: dict):
    """Freeze a task against one exact knowledge projection and its digest."""
    from ..assets.paths import repository_path
    from ..io import load_data

    projection = load_data(repository_path(root, projection_path))
    verify(root, projection)
    request = {"kind": "KNOWLEDGE_BOUND_WRITING_REQUEST", "protocol_version": 1,
               "task": deepcopy(task), "knowledge_projection": binding(root, projection_path),
               "knowledge_version": projection["knowledge_version"],
               "authority_effect": "NONE", "production_admission": "NOT_GRANTED"}
    raw = canonical_bytes(request)
    request_ref = append_bytes(root, "data/writing/knowledge-requests/" + digest(raw) + ".json", raw)
    return {"request": request_ref, "request_sha256": digest(raw), "status": "PASS",
            "authority_effect": "NONE", "production_admission": "NOT_GRANTED"}


def verify_request(root: Path, request_path: str):
    """Verify that a frozen task still names its exact projection and rules."""
    from ..assets.paths import repository_path
    from ..io import load_data

    request_raw = repository_path(root, request_path).read_bytes()
    request = load_data(repository_path(root, request_path))
    if Path(request_path).stem != digest(request_raw):
        raise ValueError("STALE_KNOWLEDGE_REQUEST: request content digest mismatch")
    if (request.get("kind") != "KNOWLEDGE_BOUND_WRITING_REQUEST"
            or type(request.get("protocol_version")) is not int
            or request.get("protocol_version") != 1
            or request.get("authority_effect") != "NONE"
            or request.get("production_admission") != "NOT_GRANTED"):
        raise ValueError("unsupported or authority-bearing knowledge request")
    projection_ref = request["knowledge_projection"]
    raw = repository_path(root, projection_ref["path"]).read_bytes()
    if digest(raw) != projection_ref["sha256"]:
        raise ValueError("STALE_KNOWLEDGE_REQUEST: projection digest changed")
    projection = load_data(repository_path(root, projection_ref["path"]))
    verify(root, projection)
    if request.get("knowledge_version") != projection["knowledge_version"]:
        raise ValueError("STALE_KNOWLEDGE_REQUEST: knowledge version mismatch")
    return request
