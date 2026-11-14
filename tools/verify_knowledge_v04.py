"""Verify the versioned chapter-86 knowledge migration without changing v0.3."""
import hashlib
from pathlib import Path

from rcwh.knowledge import CharacterKnowledgeRuntime
from rcwh.world import WorldRuntime
from rcwh.literary_ecology import LiteraryEcologyRuntime
from prepare_knowledge_v04 import OUTPUT, SOURCE, SOURCE_SHA256, build

ROOT = Path(__file__).resolve().parents[1]


def verify(root=ROOT):
    old_path = root / SOURCE
    old_before = hashlib.sha256(old_path.read_bytes()).hexdigest()
    if old_before != SOURCE_SHA256:
        raise ValueError("legacy v0.3 knowledge bytes changed")
    expected = build(root)
    new_path = root / OUTPUT
    if new_path.read_bytes() != expected:
        raise ValueError("v0.4 knowledge carrier does not match pinned migration")

    legacy = CharacterKnowledgeRuntime.from_version(root, "v0.3:slice2")
    current = CharacterKnowledgeRuntime.from_version(root, "v0.4:ch86")
    if "daiyu_death_exact_moment" not in legacy.facts:
        raise ValueError("legacy fact missing from historical version")
    if "daiyu_death_exact_moment" in current.facts:
        raise ValueError("legacy fact was aliased into v0.4")
    world = WorldRuntime.from_repo(root)
    literary = LiteraryEcologyRuntime.from_repo(root)
    if current.validate_integrity(world, literary):
        raise ValueError("v0.4 knowledge graph integrity failed")

    scene = "ch86_last_night_v04"
    pairs = ("death_occurred", "death_relative_account")
    for fact in pairs:
        if current.status(scene, "zijuan", fact, "K86-V04-DEATH-WITNESSED") != "knows":
            raise ValueError("witness update missing: " + fact)
        if current.status(scene, "baoyu", fact, "K86-V04-BAOYU-LEARNS-DEATH-ACCOUNT") != "knows":
            raise ValueError("recipient update missing: " + fact)
    for actor in ("zijuan", "baoyu"):
        for fact in ("death_precise_time", "death_physiological_detail", "death_medical_cause"):
            if current.status(scene, actor, fact, None) != "does_not_know":
                raise ValueError(f"unsupported precision promoted: {actor}/{fact}")
    if current.status(scene, "baoyu", "daiyu_death_exact_moment", None) != "UNSPECIFIED":
        raise ValueError("legacy identifier silently resolved in v0.4")
    if hashlib.sha256(old_path.read_bytes()).hexdigest() != old_before:
        raise ValueError("verification mutated legacy v0.3 source")
    return {"status": "PASS", "legacy_sha256": old_before,
            "knowledge_version": current.data["id"],
            "new_sha256": hashlib.sha256(new_path.read_bytes()).hexdigest(),
            "legacy_alias": "REJECTED", "production_admission": "NOT_GRANTED"}


if __name__ == "__main__":
    import json
    print(json.dumps(verify(), ensure_ascii=False, sort_keys=True))
