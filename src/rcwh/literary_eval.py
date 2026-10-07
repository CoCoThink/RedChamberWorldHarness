from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .io import load_data
from .literary_suite import LiteraryEvaluatorSuite
from .plocks import LiteraryProtectionRegistry
from .regression import run_r4_evidence_regression


@dataclass
class LiteraryEvaluationProfileRegistry:
    profiles: dict[str, dict[str, Any]]

    @classmethod
    def from_repo(cls, root: Path) -> "LiteraryEvaluationProfileRegistry":
        result: dict[str, dict[str, Any]] = {}
        path = root / "data" / "literary_eval"
        if path.exists():
            for file in sorted(path.glob("*.yaml")):
                doc = load_data(file) or {}
                for item in doc.get("literary_evaluation_profiles", []):
                    item_id = item["id"]
                    if item_id in result:
                        raise ValueError(f"Duplicate literary evaluation profile id: {item_id}")
                    result[item_id] = item
        return cls(result)

    def by_plock(self, plock_ref: str) -> dict[str, Any]:
        matches = [x for x in self.profiles.values() if x["plock_ref"] == plock_ref]
        if not matches:
            raise KeyError(f"No literary evaluation profile for {plock_ref}")
        if len(matches) != 1:
            raise ValueError(f"Multiple literary evaluation profiles for {plock_ref}")
        return matches[0]

    def validate_integrity(self, plocks: LiteraryProtectionRegistry) -> list[str]:
        errors: list[str] = []
        seen_plocks: set[str] = set()
        for profile_id, profile in self.profiles.items():
            lock_id = profile["plock_ref"]
            if lock_id not in plocks.locks:
                errors.append(f"{profile_id}: unknown P-Lock {lock_id}")
                continue
            if lock_id in seen_plocks:
                errors.append(f"{profile_id}: duplicate profile for P-Lock {lock_id}")
            seen_plocks.add(lock_id)

            features = {x["id"] for x in plocks.locks[lock_id]["required_features"]}
            for signal in profile.get("feature_signals", []):
                if signal["feature_ref"] not in features:
                    errors.append(
                        f"{profile_id}: signal references unknown P-Lock feature "
                        f"{signal['feature_ref']}"
                    )
        return errors


def _signal_group(text: str, terms: list[str]) -> dict[str, Any]:
    hits = [term for term in terms if term in text]
    return {"terms": terms, "hits": hits, "present": bool(hits)}


def evaluate_literary_candidate(
    root: Path,
    plock_id: str,
    text: str,
    candidate_name: str = "candidate",
) -> dict[str, Any]:
    regression = run_r4_evidence_regression(root)
    plocks = LiteraryProtectionRegistry.from_repo(root)
    profiles = LiteraryEvaluationProfileRegistry.from_repo(root)
    suite = LiteraryEvaluatorSuite.from_repo(root)

    if plock_id not in plocks.locks:
        raise KeyError(f"Unknown P-Lock: {plock_id}")
    lock = plocks.locks[plock_id]
    profile = profiles.by_plock(plock_id)

    blockers: list[dict[str, Any]] = []
    for check in profile.get("blocker_checks", []):
        hits = [term for term in check["any_text"] if term in text]
        if hits:
            blockers.append(
                {
                    "id": check["id"],
                    "hits": hits,
                    "reason": check["reason"],
                }
            )

    suite_result = suite.evaluate_prose(text, candidate_name)
    if suite_result["status"] == "REJECT_BEFORE_BLIND_READ":
        for blocker in suite_result["blockers"]:
            blockers.append(
                {
                    "id": f"suite:{blocker.lower()}",
                    "hits": [],
                    "reason": "v0.5 literary evaluator suite hard blocker",
                }
            )

    anchor_results: list[dict[str, Any]] = []
    anchor_losses: list[str] = []
    stripped = text.rstrip()
    for anchor in lock.get("exact_anchors", []):
        if anchor["mode"] == "P1_TERMINAL":
            # Terminal dialogue may end with a typographic closing quote after the
            # protected literal. Strip closing quote marks only; do not permit
            # trailing narrative prose after the protected terminal line.
            terminal = stripped.rstrip("”’\"'")
            preserved = terminal.endswith(anchor["text"])
        else:
            preserved = anchor["text"] in text
        anchor_results.append(
            {
                "text": anchor["text"],
                "mode": anchor["mode"],
                "preserved": preserved,
            }
        )
        if not preserved:
            anchor_losses.append(anchor["text"])

    signal_results: list[dict[str, Any]] = []
    signal_gaps: list[str] = []
    signal_map = {
        item["feature_ref"]: item for item in profile.get("feature_signals", [])
    }
    for feature in lock["required_features"]:
        signal_spec = signal_map.get(feature["id"])
        if not signal_spec:
            signal_results.append(
                {
                    "feature_ref": feature["id"],
                    "mode": feature["mode"],
                    "machine_signal": "UNPROFILED",
                    "groups": [],
                }
            )
            continue
        groups = [_signal_group(text, group) for group in signal_spec["groups"]]
        present = all(group["present"] for group in groups)
        signal_results.append(
            {
                "feature_ref": feature["id"],
                "mode": feature["mode"],
                "machine_signal": "PRESENT" if present else "INCOMPLETE",
                "groups": groups,
                "notes": signal_spec.get("notes"),
            }
        )
        if not present:
            signal_gaps.append(feature["id"])

    observations = []
    for obs in profile.get("observations", []):
        counts = {term: text.count(term) for term in obs["terms"] if term in text}
        observations.append(
            {
                "id": obs["id"],
                "label": obs["label"],
                "counts": counts,
                "interpretation": "OBSERVATION_ONLY",
            }
        )

    if regression["overall"] != "PASS":
        machine_status = "INFRASTRUCTURE_BLOCKED"
    elif blockers:
        machine_status = "REJECT_BEFORE_BLIND_READ"
    elif anchor_losses:
        machine_status = "REPLACEMENT_CASE"
    else:
        machine_status = "READY_FOR_BLIND_READ"

    next_gates = []
    if machine_status == "REPLACEMENT_CASE":
        next_gates.extend(
            [
                "CANDIDATE_COMPETITION",
                "SIX_FIELD_REGRESSION",
                "PLOCK_REPLACEMENT_REVIEW",
                "HUMAN_BLIND_READ",
            ]
        )
    elif machine_status == "READY_FOR_BLIND_READ":
        next_gates.extend(["SIX_FIELD_REGRESSION", "HUMAN_PLOCK_REVIEW", "HUMAN_BLIND_READ"])
    elif machine_status == "REJECT_BEFORE_BLIND_READ":
        next_gates.append("REVISE_CANDIDATE")

    return {
        "candidate": candidate_name,
        "plock": plock_id,
        "profile": profile["id"],
        "evidence_core_regression": regression["overall"],
        "machine_status": machine_status,
        "automatic_literary_pass": False,
        "promotion_eligible": False,
        "blockers": blockers,
        "protected_anchor_results": anchor_results,
        "protected_anchor_losses": anchor_losses,
        "feature_signal_results": signal_results,
        "feature_signal_gaps": signal_gaps,
        "observations": observations,
        "literary_suite": suite_result,
        "manual_review": [
            {
                "feature_ref": feature["id"],
                "mode": feature["mode"],
                "question": feature["description"],
                "required": True,
            }
            for feature in lock["required_features"]
        ],
        "next_gates": next_gates,
        "note": (
            "Machine signals can detect explicit drift, likely loss, explicit exposition, "
            "ambiguity closure, and review risks, but they never prove literary adequacy. "
            "A candidate cannot be promoted without human P-Lock review and blind read."
        ),
    }


def format_literary_evaluation(payload: dict[str, Any]) -> str:
    out = [
        "LITERARY CANDIDATE EVALUATION",
        f"candidate: {payload['candidate']}",
        f"plock: {payload['plock']}",
        f"profile: {payload['profile']}",
        f"evidence_core_regression: {payload['evidence_core_regression']}",
        f"machine_status: {payload['machine_status']}",
        "automatic_literary_pass: false",
        "promotion_eligible: false",
        "",
        "BLOCKERS",
    ]
    if payload["blockers"]:
        for item in payload["blockers"]:
            out.append(f"- {item['id']}: hits={item['hits']} — {item['reason']}")
    else:
        out.append("- none")

    out.extend(["", "PROTECTED ANCHORS"])
    for item in payload["protected_anchor_results"]:
        state = "PRESERVED" if item["preserved"] else "LOST/REPLACEMENT-REVIEW"
        out.append(f"- [{item['mode']}] {state}: {item['text']}")

    out.extend(["", "FEATURE SIGNALS"])
    for item in payload["feature_signal_results"]:
        out.append(
            f"- {item['feature_ref']} [{item['mode']}]: {item['machine_signal']}"
        )

    suite = payload.get("literary_suite")
    if suite:
        out.extend(["", "V0.5 LITERARY SUITE"])
        out.append(f"- status: {suite['status']}")
        out.append(f"- blockers: {suite['blockers']}")
        out.append(f"- human_flags: {suite['human_flags']}")

    out.extend(["", "OBSERVATIONS"])
    if payload["observations"]:
        for item in payload["observations"]:
            out.append(f"- {item['label']}: {item['counts']} (observation only)")
    else:
        out.append("- none")

    out.extend(["", "MANDATORY HUMAN REVIEW"])
    for item in payload["manual_review"]:
        out.append(f"- {item['feature_ref']}: {item['question']}")

    out.extend(["", "NEXT GATES"])
    if payload["next_gates"]:
        out.extend(f"- {x}" for x in payload["next_gates"])
    else:
        out.append("- none")

    out.extend(["", payload["note"]])
    return "\n".join(out)
