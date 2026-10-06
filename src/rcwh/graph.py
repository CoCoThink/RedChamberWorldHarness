from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .io import load_data


@dataclass
class ProvenanceGraph:
    sources: dict[str, dict[str, Any]]
    claims: dict[str, dict[str, Any]]
    decisions: dict[str, dict[str, Any]]

    @classmethod
    def from_repo(cls, root: Path) -> "ProvenanceGraph":
        def load_dir(dirname: str, wrapper: str) -> dict[str, dict[str, Any]]:
            result: dict[str, dict[str, Any]] = {}
            path = root / "data" / dirname
            if not path.exists():
                return result
            for file in sorted(path.glob("*.yaml")):
                doc = load_data(file) or {}
                for item in doc.get(wrapper, []):
                    item_id = item["id"]
                    if item_id in result:
                        raise ValueError(f"Duplicate {wrapper[:-1]} id: {item_id}")
                    result[item_id] = item
            return result

        return cls(
            sources=load_dir("sources", "sources"),
            claims=load_dir("claims", "claims"),
            decisions=load_dir("decisions", "decisions"),
        )

    def validate_integrity(self) -> list[str]:
        errors: list[str] = []

        for claim_id, claim in self.claims.items():
            support = claim.get("support", [])
            if claim.get("status") == "SUPPORTED" and not support:
                errors.append(f"{claim_id}: SUPPORTED claim has no source support")
            for edge in support:
                source_id = edge["source"]
                if source_id not in self.sources:
                    errors.append(f"{claim_id}: unknown source {source_id}")

        for decision_id, decision in self.decisions.items():
            based_on = decision.get("based_on", [])
            for claim_id in based_on:
                if claim_id not in self.claims:
                    errors.append(f"{decision_id}: unknown claim {claim_id}")

            if decision.get("status") == "LOCKED":
                supported = [
                    self.claims[c]
                    for c in based_on
                    if c in self.claims and self.claims[c].get("status") == "SUPPORTED"
                ]
                if not supported:
                    errors.append(
                        f"{decision_id}: LOCKED decision must trace to at least one SUPPORTED claim"
                    )
                elif not any(c.get("support") for c in supported):
                    errors.append(
                        f"{decision_id}: LOCKED decision has no source-backed SUPPORTED claim"
                    )

        return errors

    def permission(self, decision_id: str) -> str:
        status = self.decisions[decision_id]["status"]
        return {
            "LOCKED": "MUST",
            "CURRENT": "MAY",
            "OPEN": "OPEN",
            "REJECTED": "MUST_NOT",
        }[status]

    def evidence_proven(self, decision_id: str) -> bool:
        decision = self.decisions[decision_id]
        if decision["status"] != "LOCKED":
            return False
        return any(
            claim_id in self.claims
            and self.claims[claim_id].get("status") == "SUPPORTED"
            and bool(self.claims[claim_id].get("support"))
            for claim_id in decision.get("based_on", [])
        )

    def trace(self, node_id: str) -> dict[str, Any]:
        if node_id in self.sources:
            source = self.sources[node_id]
            claims = [
                c for c in self.claims.values()
                if any(edge["source"] == node_id for edge in c.get("support", []))
            ]
            claim_ids = {c["id"] for c in claims}
            decisions = [
                d for d in self.decisions.values()
                if claim_ids.intersection(d.get("based_on", []))
            ]
            return {"type": "source", "source": source, "claims": claims, "decisions": decisions}

        if node_id in self.claims:
            claim = self.claims[node_id]
            sources = [
                self.sources[edge["source"]]
                for edge in claim.get("support", [])
                if edge["source"] in self.sources
            ]
            decisions = [
                d for d in self.decisions.values()
                if node_id in d.get("based_on", [])
            ]
            return {"type": "claim", "claim": claim, "sources": sources, "decisions": decisions}

        if node_id in self.decisions:
            decision = self.decisions[node_id]
            claims = [
                self.claims[c]
                for c in decision.get("based_on", [])
                if c in self.claims
            ]
            source_ids: list[str] = []
            for claim in claims:
                for edge in claim.get("support", []):
                    if edge["source"] not in source_ids:
                        source_ids.append(edge["source"])
            sources = [self.sources[s] for s in source_ids if s in self.sources]
            return {
                "type": "decision",
                "decision": decision,
                "permission": self.permission(node_id),
                "evidence_proven": self.evidence_proven(node_id),
                "claims": claims,
                "sources": sources,
            }

        raise KeyError(f"Unknown provenance node: {node_id}")
