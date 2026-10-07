from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .io import load_data


STABLE_SHA = "4645da79b1bed76f54be281c50b5df648f599ea41541fb7855685753b6a85320"


@dataclass
class LiteraryProductionRuntime:
    root: Path
    data: dict[str, Any]
    chapters: dict[int, dict[str, Any]]

    @classmethod
    def from_repo(cls, root: Path) -> "LiteraryProductionRuntime":
        data = load_data(root / "data" / "project_state" / "literary_resume_v1.json") or {}
        chapters = {
            item["chapter"]: item
            for item in data.get("live_pipeline", {}).get("chapters", [])
        }
        return cls(root=root, data=data, chapters=chapters)

    def summary(self) -> dict[str, Any]:
        stable = self.data.get("stable_active", {})
        pipeline = self.data.get("live_pipeline", {})
        return {
            "id": self.data.get("id"),
            "status": self.data.get("status"),
            "authorized_by": self.data.get("authorized_by"),
            "stable_sha256": stable.get("sha256"),
            "stable_mutated": stable.get("mutated"),
            "active_chapter": pipeline.get("active_chapter"),
            "chapter_states": {
                ch: item["state"] for ch, item in sorted(self.chapters.items())
            },
            "ch89_phase2": self.data.get("ch89_phase2"),
            "next_action": self.data.get("next_action"),
        }

    def chapter(self, chapter: int, competitions: Any) -> dict[str, Any]:
        if chapter not in self.chapters:
            raise KeyError(f"Literary production pipeline covers 86/89/92/97: {chapter}")
        state = self.chapters[chapter]
        competition_id = f"comp:43-0:ch{chapter}:pressure-test"
        return {
            "live_state": state,
            "competition": competitions.records[competition_id],
        }

    def validate_integrity(self, completion: Any, competitions: Any) -> list[str]:
        errors: list[str] = []
        if self.data.get("status") != "ACTIVE":
            errors.append("post-M8 literary production state must be ACTIVE")
        auth = self.data.get("authorized_by", {})
        if auth.get("milestone") != "M8" or auth.get("completion_gate") != "PASS":
            errors.append("literary production may start only after M8 Completion Gate PASS")
        if completion.state.get("status") != "PASS":
            errors.append("persisted M8 state must remain PASS")
        if completion.state.get("completion_gate", {}).get("overall") != "PASS":
            errors.append("persisted M8 completion gate must remain PASS")

        stable = self.data.get("stable_active", {})
        if stable.get("sha256") != STABLE_SHA or stable.get("mutated") is not False:
            errors.append("post-M8 pressure testing may not mutate stable ACTIVE")
        if stable.get("promotion_required") is not True:
            errors.append("stable changes must remain behind a separate promotion gate")

        expected_states = {
            86: ("ADJUDICATED", "ch86-B", "PROMOTION_CANDIDATE"),
            89: ("ADJUDICATED", "ch89-B", "PROMOTION_CANDIDATE"),
            92: ("READY_FOR_CANDIDATES", None, "NOT_ELIGIBLE"),
            97: ("BLOCKED_BY_PREDECESSOR", None, "NOT_ELIGIBLE"),
        }
        if set(self.chapters) != set(expected_states):
            errors.append("live 43-0 pipeline must contain 86/89/92/97 exactly")

        for chapter, expected in expected_states.items():
            item = self.chapters.get(chapter)
            if item is None:
                continue
            state, winner, promotion = expected
            if (item.get("state"), item.get("winner"), item.get("promotion_state")) != expected:
                errors.append(f"chapter {chapter}: literary production state drift")
            record = competitions.records.get(f"comp:43-0:ch{chapter}:pressure-test")
            if record is None:
                errors.append(f"chapter {chapter}: missing live competition record")
                continue
            if record["state"] != state:
                errors.append(f"chapter {chapter}: competition state != literary production state")
            adj = record["adjudication"]
            if adj["winner_candidate_id"] != winner:
                errors.append(f"chapter {chapter}: winner mismatch")
            if adj["promotion_state"] != promotion:
                errors.append(f"chapter {chapter}: promotion-state mismatch")
            if record["baseline"]["sha256"] != STABLE_SHA:
                errors.append(f"chapter {chapter}: competition baseline SHA drift")
            if record["stable_active_effect"] != "SEPARATE_PROMOTION_ONLY":
                errors.append(f"chapter {chapter}: competition may not directly mutate stable")

        if self.data.get("live_pipeline", {}).get("active_chapter") != 92:
            errors.append("Chapter 92 must be the single active pressure-test chapter after ch89 adjudication")
        if self.data.get("ch89_phase2", {}).get("winner") != "ch89-B":
            errors.append("Chapter 89 Phase 2 winner must be ch89-B")
        if self.data.get("ch89_phase2", {}).get("stable_promotion") is not False:
            errors.append("Chapter 89 adjudication may not imply stable promotion")
        return errors


def format_literary_production(kind: str, payload: Any) -> str:
    if kind == "summary":
        return "\n".join([
            "POST-M8 LITERARY PRODUCTION",
            f"status: {payload['status']}",
            f"authorized_by: {payload['authorized_by']['milestone']} / {payload['authorized_by']['completion_gate']}",
            f"stable_sha256: {payload['stable_sha256']}",
            f"stable_mutated: {str(payload['stable_mutated']).lower()}",
            f"active_chapter: {payload['active_chapter']}",
            f"ch89: {payload['chapter_states'][89]} / winner={payload['ch89_phase2']['winner']}",
            f"ch92: {payload['chapter_states'][92]}",
            f"ch97: {payload['chapter_states'][97]}",
            f"next_action: {payload['next_action']}",
        ])
    if kind == "chapter":
        live = payload["live_state"]
        adj = payload["competition"]["adjudication"]
        return "\n".join([
            f"LITERARY PRODUCTION CH{live['chapter']}",
            f"state: {live['state']}",
            f"winner: {adj['winner_candidate_id']}",
            f"promotion_state: {adj['promotion_state']}",
            f"stable_effect: {live['stable_effect']}",
        ])
    return str(payload)
