"""Build the immutable v0.4 chapter-86 knowledge successor from the pinned v0.3 source."""
import json
from pathlib import Path

from rcwh.candidate_reviews import canonical_bytes

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "data/knowledge/v03_slice2.json"
SOURCE_SHA256 = "37db9f32aad64636f33eb70a73130160260914e8a4ca987e03f6c45170fa88e7"
OUTPUT = "data/knowledge/v04_ch86.json"
LEGACY_FACT = "daiyu_death_exact_moment"
NEW_FACTS = {
    "death_occurred": "黛玉死亡已经发生",
    "death_relative_account": "亲历者所述死亡相对经过；不含钟点或医学判断",
    "death_precise_time": "可确定的精确死亡钟点或可测量瞬间",
    "death_physiological_detail": "可确定的生理死亡细节",
    "death_medical_cause": "医学判定的死亡原因",
}


def build(root=ROOT):
    import hashlib

    source_path = root / SOURCE
    source_bytes = source_path.read_bytes()
    if hashlib.sha256(source_bytes).hexdigest() != SOURCE_SHA256:
        raise ValueError("pinned v0.3 knowledge source changed")
    data = json.loads(source_bytes)
    data["id"] = "character-truth:v0.4:ch86"
    facts = [fact for fact in data["facts"] if fact["id"] != LEGACY_FACT]
    if len(facts) == len(data["facts"]):
        raise ValueError("expected legacy fact is missing")
    facts.extend({"id": fact_id, "label": label, "epistemic": "CURRENT_SCENE_FACT"}
                 for fact_id, label in NEW_FACTS.items())
    data["facts"] = facts

    scene = next(scene for scene in data["scenes"] if scene["id"] == "ch86_last_night")
    scene["id"] = "ch86_last_night_v04"
    buckets = ("knows", "believes", "suspects", "does_not_know")
    for state in scene["entry"].values():
        legacy_was_unknown = LEGACY_FACT in state["does_not_know"]
        for bucket in buckets:
            state[bucket] = [fact for fact in state[bucket] if fact != LEGACY_FACT]
        if legacy_was_unknown:
            state["does_not_know"].extend(NEW_FACTS)
            state["does_not_know"].sort()

    for event in scene["events"]:
        if event["id"] == "K86-DEATH-OCCURS":
            event["id"] = "K86-V04-DEATH-WITNESSED"
            for update in event["updates"]:
                if update["character"] == "zijuan":
                    update["add"]["knows"] = ["death_occurred", "death_relative_account"]
                    update["remove"]["does_not_know"] = ["death_occurred", "death_relative_account"]
        elif event["id"] == "K86-BAOYU-LEARNS-AFTER-ARRIVAL":
            event["id"] = "K86-V04-BAOYU-LEARNS-DEATH-ACCOUNT"
            update = event["updates"][0]
            update["add"]["knows"] = ["death_occurred", "death_relative_account"]
            update["remove"]["does_not_know"] = ["death_occurred", "death_relative_account"]

    raw = canonical_bytes(data)
    return raw


if __name__ == "__main__":
    target = ROOT / OUTPUT
    raw = build(ROOT)
    if target.exists() and target.read_bytes() != raw:
        raise ValueError("refusing to overwrite different knowledge version: " + OUTPUT)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
    print(f"wrote immutable {OUTPUT} ({len(raw)} bytes)")
