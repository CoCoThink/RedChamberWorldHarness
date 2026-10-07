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
    governance: dict[str, Any]

    @classmethod
    def from_repo(cls, root: Path) -> "LiteraryProductionRuntime":
        return cls(
            root=root,
            data=load_data(root / "data" / "project_state" / "literary_43_0_resume.json") or {},
            governance=load_data(root / "data" / "project_state" / "repository_governance_20261007.json") or {},
        )

    def summary(self) -> dict[str, Any]:
        ch89 = self.data.get("chapter89", {})
        return {
            "phase": self.data.get("phase"),
            "status": self.data.get("status"),
            "authorized_after": self.data.get("initiated_after"),
            "stable_sha256": self.data.get("stable_active", {}).get("sha256"),
            "stable_changed": self.data.get("stable_active", {}).get("changed"),
            "migration_freeze_released": self.data.get("migration_freeze_released"),
            "literary_resume_started": self.data.get("literary_resume_started"),
            "active_chapter": 89,
            "chapter_states": {
                86: self.data.get("chapter86", {}).get("pressure_test"),
                89: ch89.get("pressure_test"),
                92: self.data.get("chapter92"),
                97: self.data.get("chapter97"),
            },
            "ch89_gates": {
                "six_field": ch89.get("six_field"),
                "machine_literary_evaluation": ch89.get("machine_literary_evaluation"),
                "manual_plock": ch89.get("plock_manual_review"),
                "blind_read": ch89.get("blind_read"),
                "adjudication": "PENDING",
            },
            "next_gate": self.data.get("next_gate"),
        }

    def chapter(self, chapter: int, competitions: Any) -> dict[str, Any]:
        if chapter not in {86, 89, 92, 97}:
            raise KeyError(f"Literary production pipeline covers 86/89/92/97: {chapter}")
        if chapter == 86:
            live = self.data["chapter86"]
        elif chapter == 89:
            live = self.data["chapter89"]
        else:
            live = {"state": self.data[f"chapter{chapter}"]}
        return {
            "chapter": chapter,
            "live_state": live,
            "competition": competitions.records[f"comp:43-0:ch{chapter}:pressure-test"],
        }

    def quarantine(self) -> dict[str, Any]:
        forks = self.governance.get("quarantined_forks", [])
        return {
            "status": "PASS" if forks else "FAIL",
            "canonical_literary_branch": self.governance.get("authoritative_branches", {}).get("literary_work"),
            "quarantined_forks": forks,
            "safe_delete_when_tool_available": self.governance.get("safe_delete_when_tool_available", []),
        }

    def validate_integrity(self, completion: Any, competitions: Any) -> list[str]:
        errors: list[str] = []
        if self.data.get("status") != "ACTIVE":
            errors.append("post-M8 literary production must be ACTIVE")
        if self.data.get("phase") != "43-0-resume":
            errors.append("canonical literary phase must be 43-0-resume")

        init = self.data.get("initiated_after", {})
        if init.get("full_migration_m8") != "PASS" or init.get("main_post_merge") != "PASS":
            errors.append("literary production may start only after M8 and post-merge PASS")
        if completion.state.get("status") != "PASS":
            errors.append("persisted M8 state must remain PASS")
        if completion.state.get("completion_gate", {}).get("overall") != "PASS":
            errors.append("persisted Completion Gate must remain PASS")

        stable = self.data.get("stable_active", {})
        if stable.get("sha256") != STABLE_SHA or stable.get("changed") is not False:
            errors.append("literary pressure testing may not mutate stable ACTIVE")
        if self.data.get("migration_freeze_released") is not True:
            errors.append("post-M8 literary resume must explicitly release the migration freeze")
        if self.data.get("literary_resume_started") is not True:
            errors.append("post-M8 literary resume state must explicitly start literary work")
        if self.data.get("sequence") != [86, 89, 92, 97]:
            errors.append("43-0 sequence must remain 86/89/92/97")

        ch86 = competitions.records.get("comp:43-0:ch86:pressure-test")
        if ch86 is None or ch86["state"] != "ADJUDICATED":
            errors.append("Chapter 86 must remain adjudicated")
        elif ch86["adjudication"]["winner_candidate_id"] != "ch86-B":
            errors.append("Chapter 86 winner must remain ch86-B")

        ch89 = competitions.records.get("comp:43-0:ch89:pressure-test")
        live89 = self.data.get("chapter89", {})
        if ch89 is None:
            errors.append("Chapter 89 competition missing")
        else:
            if ch89["state"] != "IN_REVIEW":
                errors.append("Chapter 89 must remain IN_REVIEW until human gates finish")
            if ch89["workflow_progress"].get("SIX_FIELD_REGRESSION") != "PASS":
                errors.append("Chapter 89 six-field regression must be PASS")
            if ch89["workflow_progress"].get("PLOCK_REGRESSION") != "PENDING":
                errors.append("Chapter 89 manual P-Lock gate must remain PENDING")
            if ch89["workflow_progress"].get("BLIND_READ") != "PENDING":
                errors.append("Chapter 89 blind read must remain PENDING")
            if ch89["adjudication"]["outcome"] != "PENDING":
                errors.append("Chapter 89 adjudication must remain PENDING")
            if ch89["adjudication"]["winner_candidate_id"] is not None:
                errors.append("Chapter 89 cannot have a winner before real blind review")
        if live89.get("six_field") != "PASS":
            errors.append("live Chapter 89 six-field state must be PASS")
        if live89.get("plock_manual_review") != "PENDING":
            errors.append("live Chapter 89 manual P-Lock state must be PENDING")
        if live89.get("blind_read") != "PENDING":
            errors.append("live Chapter 89 blind-read state must be PENDING")

        for chapter in (92, 97):
            record = competitions.records.get(f"comp:43-0:ch{chapter}:pressure-test")
            if record is None or record["state"] != "BLOCKED_BY_PREDECESSOR":
                errors.append(f"Chapter {chapter} must remain BLOCKED_BY_PREDECESSOR")
            if self.data.get(f"chapter{chapter}") != "BLOCKED_BY_PREDECESSOR":
                errors.append(f"live Chapter {chapter} state drift")

        q = self.quarantine()
        if q["status"] != "PASS":
            errors.append("repository governance must quarantine divergent literary forks")
        if q.get("canonical_literary_branch") != "literary/43-0-resume":
            errors.append("canonical literary branch must remain literary/43-0-resume")
        fork = next((x for x in q["quarantined_forks"] if x.get("branch") == "literary/43-0-ch89-phase2"), None)
        if fork is None:
            errors.append("divergent Chapter 89 fork must remain explicitly quarantined")
        elif fork.get("merge_policy") != "DO_NOT_MERGE":
            errors.append("quarantined Chapter 89 fork must not be mergeable authority")

        return errors


def format_literary_production(kind: str, payload: Any) -> str:
    if kind == "summary":
        gates = payload["ch89_gates"]
        return "\n".join([
            "POST-M8 LITERARY PRODUCTION",
            f"phase: {payload['phase']}",
            f"status: {payload['status']}",
            f"stable_sha256: {payload['stable_sha256']}",
            f"stable_changed: {str(payload['stable_changed']).lower()}",
            f"active_chapter: {payload['active_chapter']}",
            f"ch89: six-field={gates['six_field']} machine={gates['machine_literary_evaluation']} "
            f"manual-plock={gates['manual_plock']} blind={gates['blind_read']} adjudication={gates['adjudication']}",
            f"ch92: {payload['chapter_states'][92]}",
            f"ch97: {payload['chapter_states'][97]}",
            f"next_gate: {payload['next_gate']}",
        ])
    if kind == "quarantine":
        return "\n".join([
            f"REPOSITORY LITERARY QUARANTINE: {payload['status']}",
            f"canonical: {payload['canonical_literary_branch']}",
            f"quarantined forks: {len(payload['quarantined_forks'])}",
            f"safe-delete branches: {len(payload['safe_delete_when_tool_available'])}",
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
