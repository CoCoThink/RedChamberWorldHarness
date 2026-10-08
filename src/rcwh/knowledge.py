from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .io import load_data
from .contracts import unique_index

BUCKETS = ("knows", "believes", "suspects", "does_not_know")


@dataclass
class CharacterKnowledgeRuntime:
    root: Path
    data: dict[str, Any]

    @classmethod
    def from_repo(cls, root: Path) -> "CharacterKnowledgeRuntime":
        return cls(root, load_data(root / "data/knowledge/v03_slice1.json") or {})

    @property
    def facts(self):
        return unique_index(self.data.get('facts', []), 'id')

    @property
    def characters(self):
        return unique_index(self.data.get('characters', []), 'id')

    @property
    def scenes(self):
        return unique_index(self.data.get('scenes', []), 'id')

    def summary(self) -> dict[str, Any]:
        policy = self.data["policy"]
        return {
            "id": self.data.get("id"),
            "characters": len(self.characters), "character_ids": sorted(self.characters),
            "facts": len(self.facts), "scenes": len(self.scenes),
            **policy,
        }

    def scene(self, scene_id: str, checkpoint: str | None = None) -> dict[str, Any]:
        scene = self.scenes.get(scene_id)
        if scene is None:
            raise KeyError(f"Unknown knowledge scene: {scene_id}")
        state = {
            cid: {k: set(v) for k, v in item.items()}
            for cid, item in deepcopy(scene["entry"]).items()
        }
        applied = []
        if checkpoint != "ENTRY":
            found = checkpoint is None
            for event in sorted(scene.get("events", []), key=lambda x: x["sequence"]):
                self._apply(state, event)
                applied.append(event["id"])
                if checkpoint == event["id"]:
                    found = True
                    break
            if not found:
                raise KeyError(f"Unknown checkpoint {checkpoint} for {scene_id}")
        return {
            "scene_id": scene_id, "chapter": scene["chapter"],
            "checkpoint": checkpoint or "FINAL", "applied_events": applied,
            "participants": scene["participants"],
            "states": {cid: {k: sorted(v) for k, v in s.items()}
                       for cid, s in sorted(state.items())},
        }

    def character(self, scene_id: str, character_id: str,
                  checkpoint: str | None = None) -> dict[str, Any]:
        scene = self.scene(scene_id, checkpoint)
        if character_id not in scene["states"]:
            raise KeyError(f"{character_id} is not a participant in {scene_id}")
        return {
            "scene_id": scene_id, "chapter": scene["chapter"],
            "checkpoint": scene["checkpoint"], "character_id": character_id,
            "state": scene["states"][character_id],
        }

    def status(self, scene_id: str, character_id: str, fact_id: str,
               checkpoint: str | None = "ENTRY") -> str:
        state = self.character(scene_id, character_id, checkpoint)["state"]
        return next((k for k in BUCKETS if fact_id in state[k]), "UNSPECIFIED")

    def voice(self, character_id: str) -> dict[str, Any]:
        if character_id not in self.characters:
            raise KeyError(f"Unknown first-slice character: {character_id}")
        return deepcopy(self.characters[character_id])

    def mask(self, character_id: str, text: str) -> dict[str, Any]:
        item = self.voice(character_id)
        hook = item["masking_hook"]
        hits = [x for x in hook.get("forbidden_text", []) if x in text]
        support = item["voice_profile"]["support"]
        result = "FAIL_FORBIDDEN_VOICE" if hits else (
            "ABSTAIN_SPARSE_CORPUS" if support == "SPARSE_ABSTAIN"
            else "READY_FOR_HUMAN_MASKING"
        )
        return {
            "character_id": character_id, "name": item["name"], "status": result,
            "support": support, "positive_traits": hook.get("positive_traits", []),
            "forbidden_hits": hits, "automatic_identity_pass": False,
        }

    def text_guard(self, scene_id: str, contract: dict[str, Any],
                   text: str) -> dict[str, Any]:
        findings, checks = [], []
        default = contract.get("knowledge_checkpoint", "ENTRY")
        for g in contract.get("knowledge_guards", []):
            cp = g.get("checkpoint", default)
            state = self.status(scene_id, g["actor"], g["fact"], cp)
            allowed = set(g.get("allowed_status", ["knows"]))
            hits = [x for x in g.get("any_text", []) if x in text]
            bad = bool(hits) and state not in allowed
            checks.append({
                "id": g["id"], "actor": g["actor"], "fact": g["fact"],
                "checkpoint": cp, "epistemic_status": state,
                "allowed_status": sorted(allowed), "modes": g.get("modes", ["ANY"]),
                "hits": hits, "violation": bad,
            })
            if bad:
                findings.append(
                    f"{g['id']}: {g['actor']}={state} for {g['fact']} at {cp}; hit={hits}"
                )
        return {"scene_id": scene_id, "status": "FAIL" if findings else "PASS",
                "checks": checks, "findings": findings}

    def validate_integrity(self, world: Any, literary: Any) -> list[str]:
        e = []
        if not self.characters or not self.facts or not self.scenes:
            e.append("knowledge characters, facts and scenes must be nonempty")
        policy = self.data["policy"]
        if policy.get("automatic_voice_identity") is not False:
            e.append("voice masking hook may not auto-identify speakers")
        for cid, item in self.characters.items():
            if cid not in world.characters and not item.get("world_binding_optional", False):
                e.append(f"missing World character: {cid}")
            if cid not in literary.voices and item["voice_profile"]["support"] != "SPARSE_ABSTAIN":
                e.append(f"missing supported voice profile: {cid}")
        if self.characters.get("qianxue", {}).get("voice_profile", {}).get("support") != "SPARSE_ABSTAIN":
            e.append("Qianxue must remain sparse/abstaining")

        facts = set(self.facts)
        event_ids = set()
        for sid, scene in self.scenes.items():
            if set(scene["entry"]) != set(scene["participants"]):
                e.append(f"{sid}: entry/participant mismatch")
            for cid in scene["participants"]:
                if cid not in self.characters:
                    e.append(f"{sid}: unknown participant {cid}")
            for cid, state in scene["entry"].items():
                self._check_state(sid, cid, state, facts, e)
            last = -1
            for ev in sorted(scene.get("events", []), key=lambda x: x["sequence"]):
                if ev["id"] in event_ids:
                    e.append(f"duplicate event: {ev['id']}")
                event_ids.add(ev["id"])
                if ev["sequence"] <= last:
                    e.append(f"{sid}: event sequence not increasing")
                last = ev["sequence"]
                for u in ev.get("updates", []):
                    if u["character"] not in scene["participants"]:
                        e.append(f"{sid}/{ev['id']}: target not participant")
                    for op in ("add", "remove"):
                        for bucket, vals in u.get(op, {}).items():
                            if bucket not in BUCKETS:
                                e.append(f"{sid}/{ev['id']}: invalid bucket {bucket}")
                            for fact in vals:
                                if fact not in facts:
                                    e.append(f"{sid}/{ev['id']}: unknown fact {fact}")
            try:
                self.scene(sid)
            except Exception as exc:
                e.append(f"{sid}: replay failed: {exc}")

        if self.status("ch92_delivery_gate", "xiaohong",
                       "detention_delivery_rules", "ENTRY") != "does_not_know":
            e.append("Xiaohong must enter ch92 without delivery rules")
        if self.status("ch92_delivery_gate", "xiaohong", "detention_delivery_rules",
                       "K92-XIAOHONG-ASKS-GATE-RULES") != "knows":
            e.append("Xiaohong must learn delivery rules via event")
        if self.status("ch92_delivery_gate", "xiaohong",
                       "baoyu_detention_whole_case", None) != "does_not_know":
            e.append("Xiaohong whole-case boundary drift")
        return e

    def _apply(self, state, event):
        for u in event.get("updates", []):
            s = state[u["character"]]
            for bucket, vals in u.get("remove", {}).items():
                for fact in vals:
                    s[bucket].discard(fact)
            for bucket, vals in u.get("add", {}).items():
                for fact in vals:
                    s[bucket].add(fact)
            self._conflict(event["id"], u["character"], s)

    @staticmethod
    def _conflict(scope, cid, state):
        if state["knows"] & state["does_not_know"]:
            raise ValueError(f"{scope}/{cid}: knowledge conflict")
        for bucket in ("believes", "suspects"):
            if state["knows"] & state[bucket]:
                raise ValueError(f"{scope}/{cid}: known fact remains {bucket}")

    @classmethod
    def _check_state(cls, sid, cid, state, facts, errors):
        if set(state) != set(BUCKETS):
            errors.append(f"{sid}/{cid}: four epistemic buckets required")
            return
        normalized = {k: set(v) for k, v in state.items()}
        for bucket, vals in normalized.items():
            for fact in vals:
                if fact not in facts:
                    errors.append(f"{sid}/{cid}: unknown fact {fact} in {bucket}")
        try:
            cls._conflict(sid, cid, normalized)
        except ValueError as exc:
            errors.append(str(exc))


def format_knowledge(kind: str, p: dict[str, Any]) -> str:
    if kind == "summary":
        return "\n".join([
            "CHARACTER KNOWLEDGE v0.3",
            f"characters: {p['characters']}", f"facts: {p['facts']}",
            f"scenes: {p['scenes']}",
            f"automatic voice identity: {str(p['automatic_voice_identity']).lower()}",
        ])
    if kind == "character":
        s = p["state"]
        return "\n".join([
            f"KNOWLEDGE {p['character_id']} @ {p['scene_id']} / {p['checkpoint']}",
            f"knows: {', '.join(s['knows']) or 'none'}",
            f"believes: {', '.join(s['believes']) or 'none'}",
            f"suspects: {', '.join(s['suspects']) or 'none'}",
            f"does_not_know: {', '.join(s['does_not_know']) or 'none'}",
        ])
    if kind == "voice":
        v = p["voice_profile"]
        return "\n".join([f"VOICE {p['id']} / {p['name']}", f"support: {v['support']}",
                           f"voice: {v['voice']}", f"forbidden: {v['post80_forbidden']}"])
    if kind == "mask":
        return "\n".join([f"VOICE MASK {p['character_id']} / {p['name']}",
                           f"status: {p['status']}", f"support: {p['support']}",
                           f"forbidden_hits: {', '.join(p['forbidden_hits']) or 'none'}"])
    return str(p)
