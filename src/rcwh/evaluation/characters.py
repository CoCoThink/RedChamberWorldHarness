"""One character view resolves selected World, voice and knowledge profiles."""
from pathlib import Path

from ..io import load_data
from ..knowledge import CharacterKnowledgeRuntime
from ..literary_ecology import LiteraryEcologyRuntime
from ..world import WorldRuntime


class CharacterProfiles:
    def __init__(self, root: Path):
        self.root = root
        self.world = WorldRuntime.from_repo(root)
        self.voices = LiteraryEcologyRuntime.from_repo(root).voices
        self.knowledge = CharacterKnowledgeRuntime.from_repo(root)
        path = root / "data/evaluation/character_supplements.json"
        self.supplements = {c["id"]: c for c in load_data(path)["characters"]} if path.exists() else {}

    def profile(self, identity: str) -> dict:
        character = self.world.characters[identity]
        voice = self.voices.get(identity)
        supplement = self.supplements.get(identity)
        knowledge = self.knowledge.voice(identity) if identity in self.knowledge.characters else None
        sparse = knowledge and knowledge.get("voice_profile", {}).get("support") == "SPARSE_ABSTAIN"
        return {"id": identity, "name": character["name"], "world": character, "voice": voice,
                "supplement": supplement, "knowledge": knowledge,
                "coverage": "REGISTERED_VOICE" if voice else "SPARSE_ABSTAIN" if sparse or not supplement or not supplement["examples"] else "PROVISIONAL_EXAMPLES",
                "literary_verification": "PENDING_INDEPENDENT_READING", "authority_effect": "NONE"}

    def summary(self) -> dict:
        rows = [self.profile(cid) for cid in self.world.characters]
        hooks = []
        for path in sorted((self.root / "data/scenes").glob("*.yaml")):
            contract = load_data(path)
            for cid in contract.get("voice_profile_hooks", []):
                hooks.append({"scene": contract["id"], "character": cid,
                              "resolved": cid in self.world.characters and (cid in self.voices or cid in self.supplements or cid in self.knowledge.characters),
                              "coverage": self.profile(cid)["coverage"] if cid in self.world.characters else "MISSING_WORLD_IDENTITY"})
        return {"characters": len(rows), "registered_voices": len(self.voices),
                "knowledge_profiles": len(self.knowledge.characters), "profiles": rows, "hooks": hooks,
                "status": "PENDING", "authority_effect": "NONE"}
