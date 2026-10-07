from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .graph import ProvenanceGraph
from .history import HistoricalMechanismRegistry
from .io import load_data
from .open_interfaces import OpenInterfaceRegistry


@dataclass
class HypothesisRuntime:
    hypotheses: dict[str, dict[str, Any]]
    fidelity_audit: dict[str, Any]
    source_backfill: dict[str, Any]

    @classmethod
    def from_repo(cls, root: Path) -> "HypothesisRuntime":
        hypotheses: dict[str, dict[str, Any]] = {}
        path = root / "data" / "hypotheses"
        if path.exists():
            for file in sorted(path.glob("*.json")):
                doc = load_data(file) or {}
                for item in doc.get("hypotheses", []):
                    item_id = item["id"]
                    if item_id in hypotheses:
                        raise ValueError(f"Duplicate hypothesis id: {item_id}")
                    hypotheses[item_id] = item
        audit_path = root / "data" / "fidelity" / "audit_registry.json"
        backfill_path = root / "data" / "fidelity" / "hypothesis_source_backfill.json"
        return cls(
            hypotheses=hypotheses,
            fidelity_audit=load_data(audit_path) if audit_path.exists() else {},
            source_backfill=load_data(backfill_path) if backfill_path.exists() else {},
        )

    @staticmethod
    def _validate_ref(
        ref: str,
        graph: ProvenanceGraph,
        open_interfaces: OpenInterfaceRegistry,
        mechanisms: HistoricalMechanismRegistry,
        reconstruction: Any | None = None,
    ) -> bool:
        if ref.startswith("claim:"):
            return ref in graph.claims
        if ref.startswith("src:"):
            return ref in graph.sources
        if ref.startswith("OL-"):
            return ref in open_interfaces.interfaces
        if ref.startswith("H0") and len(ref) == 3:
            return ref in mechanisms.mechanisms
        if reconstruction is not None and ref.startswith("R") and len(ref) == 3:
            return ref in reconstruction.r_nodes
        if reconstruction is not None and ref.startswith("P") and len(ref) == 3:
            return ref in reconstruction.p_edges
        return True

    def validate_integrity(
        self,
        graph: ProvenanceGraph,
        open_interfaces: OpenInterfaceRegistry,
        mechanisms: HistoricalMechanismRegistry,
        reconstruction: Any | None = None,
    ) -> list[str]:
        errors: list[str] = []

        for hypothesis_id, item in self.hypotheses.items():
            if item.get("authority") != "HYPOTHESIS_ONLY":
                errors.append(f"{hypothesis_id}: authority must be HYPOTHESIS_ONLY")
            for field in ("evidence_effect", "stable_active_effect", "current_c_effect"):
                if item.get(field) != "NONE":
                    errors.append(f"{hypothesis_id}: {field} must be NONE")

            qref = item.get("question_ref")
            interface = open_interfaces.interfaces.get(qref)
            if interface is None:
                errors.append(f"{hypothesis_id}: unknown OPEN question_ref {qref}")
            elif interface.get("state") != "OPEN_LOCKED":
                errors.append(f"{hypothesis_id}: question_ref {qref} must remain OPEN_LOCKED")

            for ref in item.get("related_open_refs", []) + item.get("open_consumption", []):
                if ref not in open_interfaces.interfaces:
                    errors.append(f"{hypothesis_id}: unknown OPEN ref {ref}")
                elif open_interfaces.interfaces[ref].get("state") != "OPEN_LOCKED":
                    errors.append(f"{hypothesis_id}: OPEN ref {ref} is not OPEN_LOCKED")

            for ref in item.get("support_refs", []) + item.get("counter_refs", []):
                if not self._validate_ref(
                    ref, graph, open_interfaces, mechanisms, reconstruction
                ):
                    errors.append(f"{hypothesis_id}: unresolved support/counter ref {ref}")

            if item.get("status") == "ADMISSIBLE" and not item.get("cannot_prove"):
                errors.append(f"{hypothesis_id}: admissible hypothesis must declare cannot_prove")

        if self.fidelity_audit:
            if self.fidelity_audit.get("authority") != "SHADOW_ONLY":
                errors.append("fidelity audit must remain SHADOW_ONLY")
            for entry in self.fidelity_audit.get("entries", []):
                if entry.get("authority_effect") != "NONE":
                    errors.append(f"{entry.get('id')}: fidelity audit may not change authority")

        if self.source_backfill:
            if self.source_backfill.get("authority") != "SEARCH_INPUT_ONLY":
                errors.append("hypothesis source backfill must remain SEARCH_INPUT_ONLY")
            for item in self.source_backfill.get("typed_backfills", []):
                if item.get("authority") != "SEARCH_INPUT_ONLY":
                    errors.append(f"{item.get('id')}: backfill authority drift")

        return errors

    def alternatives(self, open_id: str) -> list[dict[str, Any]]:
        return [
            item for item in self.hypotheses.values()
            if item.get("question_ref") == open_id
            or open_id in item.get("related_open_refs", [])
        ]

    def get(self, hypothesis_id: str) -> dict[str, Any]:
        if hypothesis_id not in self.hypotheses:
            raise KeyError(f"Unknown hypothesis: {hypothesis_id}")
        return self.hypotheses[hypothesis_id]

    def alternative_coverage(self) -> dict[str, int]:
        result: dict[str, int] = {}
        for item in self.hypotheses.values():
            if item.get("status") != "ADMISSIBLE":
                continue
            qref = item["question_ref"]
            result[qref] = result.get(qref, 0) + 1
        return result

    def summary(self) -> dict[str, Any]:
        coverage = self.alternative_coverage()
        return {
            "status": "SHADOW_ONLY",
            "hypotheses": len(self.hypotheses),
            "admissible": sum(
                x.get("status") == "ADMISSIBLE" for x in self.hypotheses.values()
            ),
            "open_interfaces_with_alternatives": len(coverage),
            "open_interfaces_with_two_or_more": len(
                [x for x in coverage.values() if x >= 2]
            ),
            "evidence_effect": "NONE",
            "stable_active_effect": "NONE",
        }
