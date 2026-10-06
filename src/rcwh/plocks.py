from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .graph import ProvenanceGraph
from .history import HistoricalMechanismRegistry
from .io import load_data
from .literals import LiteralRegistry
from .open_interfaces import OpenInterfaceRegistry


@dataclass
class LiteraryProtectionRegistry:
    locks: dict[str, dict[str, Any]]

    @classmethod
    def from_repo(cls, root: Path) -> "LiteraryProtectionRegistry":
        result: dict[str, dict[str, Any]] = {}
        path = root / "data" / "plocks"
        if path.exists():
            for file in sorted(path.glob("*.yaml")):
                doc = load_data(file) or {}
                for item in doc.get("literary_locks", []):
                    item_id = item["id"]
                    if item_id in result:
                        raise ValueError(f"Duplicate P-Lock id: {item_id}")
                    result[item_id] = item
        return cls(result)

    def validate_integrity(
        self,
        graph: ProvenanceGraph,
        literals: LiteralRegistry,
        mechanisms: HistoricalMechanismRegistry,
        opens: OpenInterfaceRegistry,
        stable_active: dict[str, Any],
    ) -> list[str]:
        errors: list[str] = []

        for lock_id, lock in self.locks.items():
            if lock.get("state") != "P_LOCKED":
                errors.append(f"{lock_id}: state must be P_LOCKED")
            if lock.get("authority") != "LITERARY_PROTECTION_ONLY":
                errors.append(f"{lock_id}: authority must remain literary-only")
            if lock.get("generation_effect") != "PROTECT_AGAINST_REGRESSION":
                errors.append(f"{lock_id}: invalid generation effect")
            if lock.get("replacement_rule") != (
                "COMPETITION_PLUS_SIX_FIELD_PLUS_PLOCK_PLUS_BLIND_READ"
            ):
                errors.append(f"{lock_id}: invalid replacement rule")

            locator = lock.get("active_prose_locator", {})
            if locator.get("file_ref") != stable_active["file_ref"]:
                errors.append(f"{lock_id}: prose locator not on stable ACTIVE file")
            if locator.get("file_sha256") != stable_active["sha256"]:
                errors.append(f"{lock_id}: prose locator SHA not on stable ACTIVE baseline")

            for impl_id in lock.get("implementation_refs", []):
                if impl_id not in graph.implementations:
                    errors.append(f"{lock_id}: unknown implementation {impl_id}")

            context = lock.get("upstream_context", {})
            for decision_id in context.get("decision_refs", []):
                if decision_id not in graph.decisions:
                    errors.append(f"{lock_id}: unknown context decision {decision_id}")
            for open_id in context.get("open_interface_refs", []):
                if open_id not in opens.interfaces:
                    errors.append(f"{lock_id}: unknown OPEN interface {open_id}")
            for mechanism_id in context.get("mechanism_refs", []):
                if mechanism_id not in mechanisms.mechanisms:
                    errors.append(f"{lock_id}: unknown historical mechanism {mechanism_id}")
            for literal_id in context.get("literal_refs", []):
                if literal_id not in literals.constraints:
                    errors.append(f"{lock_id}: unknown literal constraint {literal_id}")

            feature_ids = [x["id"] for x in lock.get("required_features", [])]
            if len(feature_ids) != len(set(feature_ids)):
                errors.append(f"{lock_id}: duplicate required feature id")

        # P-Locks are downstream. They may never become Decision evidence.
        plock_ids = set(self.locks)
        for decision_id, decision in graph.decisions.items():
            bad = [x for x in decision.get("based_on", []) if x in plock_ids]
            if bad:
                errors.append(
                    f"{decision_id}: Decision may not use downstream P-Lock as evidence {bad}"
                )

        return errors

    def describe(self, lock_id: str) -> dict[str, Any]:
        if lock_id not in self.locks:
            raise KeyError(f"Unknown P-Lock: {lock_id}")
        return self.locks[lock_id]


def format_plock(lock: dict[str, Any]) -> str:
    out = [
        "LITERARY P-LOCK",
        f"id: {lock['id']}",
        f"chapter: {lock['chapter']}",
        f"title: {lock['title']}",
        f"state: {lock['state']}",
        f"authority: {lock['authority']}",
        f"legacy_ref: {lock.get('legacy_ref')}",
        "",
        "EXACT ANCHORS",
    ]
    anchors = lock.get("exact_anchors", [])
    if anchors:
        for anchor in anchors:
            out.append(f"- [{anchor['mode']}] {anchor['text']}")
    else:
        out.append("- none")

    out.extend(["", "REQUIRED FEATURES"])
    for feature in lock["required_features"]:
        out.append(
            f"- {feature['id']} [{feature['mode']}]: {feature['description']}"
        )

    out.extend(["", "FORBIDDEN DRIFT"])
    for item in lock["forbidden_drift"]:
        out.append(f"- {item}")

    out.extend(
        [
            "",
            f"replacement_rule: {lock['replacement_rule']}",
            f"active_prose: {lock['active_prose_locator']}",
        ]
    )
    return "\n".join(out)
