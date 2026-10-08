from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .competition import CompetitionRegistry, PIPELINE
from .contracts import unique_index, project_chapters
from .workflow import ProjectState


@dataclass
class LiteraryProductionRuntime:
    root: Path
    data: dict[str, Any]

    @classmethod
    def from_repo(cls, root: Path) -> "LiteraryProductionRuntime":
        return cls(root, ProjectState.from_repo(root).owner("literary"))

    def _production(self, competitions: Any) -> dict[int, dict[str, Any]]:
        return unique_index([r for r in competitions.records.values() if r["mode"] == "PRODUCTION_43_0"], "chapter")

    def summary(self) -> dict[str, Any]:
        competitions = CompetitionRegistry.from_repo(self.root)
        records = self._production(competitions)
        active = next((records[ch] for ch in self.data["sequence"]
                       if records[ch]["state"] in {"READY_FOR_CANDIDATES", "IN_REVIEW"}), None)
        if active:
            unresolved = next((stage for stage in PIPELINE if active["workflow_progress"][stage] != "PASS"), "ADJUDICATION")
            next_gate = f"CH{active['chapter']}_{unresolved}"
        else:
            next_gate = "COMPETITION_SEQUENCE_REVIEW"
        return {
            "phase": self.data.get("phase"),
            "status": self.data.get("status"),
            "stable_sha256": self.data.get("stable_active", {}).get("sha256"),
            "literary_resume_started": self.data.get("literary_resume_started"),
            "active_chapter": active["chapter"] if active else None,
            "chapter_states": {ch: records[ch]["state"] for ch in self.data["sequence"]},
            "active_gates": self.gates(active["chapter"], competitions) if active else None,
            "next_gate": next_gate,
        }

    def gates(self, chapter: int, competitions: Any | None = None) -> dict[str, Any]:
        if chapter not in self.data["sequence"]:
            raise KeyError(f"Chapter outside configured literary sequence: {chapter}")
        competitions = competitions or CompetitionRegistry.from_repo(self.root)
        record = self._production(competitions)[chapter]
        rows = competitions.evaluate_record(self.root, record)["candidate_results"]
        if any(row["machine_status"] == "REJECT_BEFORE_BLIND_READ" for row in rows):
            machine = "FAIL"
        elif rows and all(row["machine_status"] in {"READY_FOR_BLIND_READ", "REPLACEMENT_CASE"} for row in rows):
            machine = "PASS"
        else:
            machine = "PENDING"
        return {
            "six_field": record["workflow_progress"]["SIX_FIELD_REGRESSION"],
            "machine_literary_evaluation": machine,
            "manual_plock": record["workflow_progress"]["PLOCK_REGRESSION"],
            "blind_read": record["workflow_progress"]["BLIND_READ"],
            "adjudication": record["adjudication"]["outcome"],
        }

    def chapter(self, chapter: int, competitions: Any) -> dict[str, Any]:
        if chapter not in self.data["sequence"]:
            raise KeyError(f"Chapter outside configured literary sequence: {chapter}")
        record = self._production(competitions)[chapter]
        return {
            "chapter": chapter,
            "live_state": {"state": record["state"], "workflow_progress": record["workflow_progress"]},
            "competition": record,
            "gates": self.gates(chapter, competitions),
        }

    def validate_integrity(self, competitions: Any) -> list[str]:
        errors: list[str] = []
        if self.data.get("status") != "ACTIVE":
            errors.append("literary production must be ACTIVE")
        stable = self.data.get("stable_active", {})
        release = ProjectState.from_repo(self.root).release()
        errors.extend(release.validate_storage())
        if stable.get("sha256") != release.data["text_sha256"]:
            errors.append("literary pressure testing may not mutate stable ACTIVE")
        if self.data.get("literary_resume_started") is not True:
            errors.append("literary workflow selection must explicitly start literary work")
        sequence = self.data.get("sequence", [])
        records = self._production(competitions)
        ordered = sorted(records.values(), key=lambda r: r["sequence"])
        if not sequence or len(sequence) != len(set(sequence)):
            errors.append("literary sequence must be nonempty and unique")
        if sequence != [r["chapter"] for r in ordered]:
            errors.append("literary sequence must match production competition order")
        if not set(sequence) <= set(project_chapters(self.root)):
            errors.append("literary sequence outside configured project scope")
        for record in ordered:
            evaluation = competitions.evaluate_record(self.root, record)
            errors.extend(f"{record['id']}: {e}" for e in evaluation["consistency_errors"])
            if record["state"] == "ADJUDICATED" and record["adjudication"]["outcome"] == "PENDING":
                errors.append(f"{record['id']}: adjudicated record cannot have pending adjudication")
            if record["adjudication"]["outcome"] != "PENDING" and record["state"] != "ADJUDICATED":
                errors.append(f"{record['id']}: completed adjudication requires ADJUDICATED state")
            candidates = evaluation["candidate_results"]
            for stage, key, values in [("PLOCK_REGRESSION", "human_plock_status", {"PASS", "REPLACEMENT_ACCEPTED", "FAIL"}),
                                       ("BLIND_READ", "blind_read_status", {"PASS", "FAIL"})]:
                if record["workflow_progress"][stage] == "PASS" and (not candidates or any(c[key] not in values for c in candidates)):
                    errors.append(f"{record['id']}: {stage} completion lacks actual candidate reviews")
            if record["workflow_progress"]["BLIND_READ"] == "PASS" and any(not c["reviewer_blinded"] for c in candidates):
                errors.append(f"{record['id']}: completed blind review lacks blinded reviewer")

        return errors


def format_literary_production(kind: str, payload: Any) -> str:
    if kind == "summary":
        return "\n".join([
            "LITERARY PRODUCTION",
            f"phase: {payload['phase']}",
            f"status: {payload['status']}",
            f"stable_sha256: {payload['stable_sha256']}",
            f"active_chapter: {payload['active_chapter']}",
            *[f"ch{ch}: {state}" for ch, state in payload["chapter_states"].items()],
            f"next_gate: {payload['next_gate']}",
        ])
    if kind == "chapter":
        comp = payload["competition"]
        return "\n".join([
            f"LITERARY PRODUCTION CH{payload['chapter']}",
            f"competition_state: {comp['state']}",
            f"winner: {comp['adjudication']['winner_candidate_id']}",
            f"promotion_state: {comp['adjudication']['promotion_state']}",
            f"stable_effect: {comp['stable_active_effect']}",
        ])
    return str(payload)
