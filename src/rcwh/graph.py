from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from .io import load_data


@dataclass
class ProvenanceGraph:
    sources: dict[str, dict[str, Any]]
    claims: dict[str, dict[str, Any]]
    decisions: dict[str, dict[str, Any]]
    implementations: dict[str, dict[str, Any]]

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
            implementations=load_dir("implementations", "implementations"),
        )

    @staticmethod
    def _source_fingerprint(source: dict[str, Any]) -> str:
        witness = source.get("witness", {})
        locator = json.dumps(source.get("locator", {}), ensure_ascii=False, sort_keys=True)
        return "|".join([
            str(witness.get("siglum") or witness.get("label")),
            locator,
            source.get("text_sha256", ""),
        ])

    def decision_fully_source_backed(self, decision_id: str) -> bool:
        decision = self.decisions[decision_id]
        based_on = decision.get("based_on", [])
        if not based_on:
            return False
        return all(
            claim_id in self.claims
            and self.claims[claim_id].get("status") == "SUPPORTED"
            and bool(self.claims[claim_id].get("support"))
            for claim_id in based_on
        )

    def validate_integrity(self) -> list[str]:
        errors: list[str] = []

        seen_fingerprints: dict[str, str] = {}
        for source_id, source in self.sources.items():
            fingerprint = self._source_fingerprint(source)
            if fingerprint in seen_fingerprints:
                errors.append(
                    f"{source_id}: duplicate source witness/locator/text of "
                    f"{seen_fingerprints[fingerprint]}"
                )
            else:
                seen_fingerprints[fingerprint] = source_id

        for claim_id, claim in self.claims.items():
            support = claim.get("support", [])
            if claim.get("status") == "SUPPORTED" and not support:
                errors.append(f"{claim_id}: SUPPORTED claim has no source support")
            for edge in support:
                source_id = edge["source"]
                if source_id not in self.sources:
                    errors.append(f"{claim_id}: unknown source {source_id}")

        compatibility = {
            "LOCKED": {"MUST", "MUST_NOT"},
            "CURRENT": {"MAY"},
            "OPEN": {"OPEN"},
            "REJECTED": {"NONE"},
        }

        for decision_id, decision in self.decisions.items():
            based_on = decision.get("based_on", [])
            for claim_id in based_on:
                if claim_id not in self.claims:
                    errors.append(f"{decision_id}: unknown claim {claim_id}")

            status = decision.get("status")
            constraint = decision.get("constraint")
            if constraint not in compatibility.get(status, set()):
                errors.append(
                    f"{decision_id}: incompatible status/constraint {status}/{constraint}"
                )

            if status == "LOCKED":
                if decision.get("reversible") is not False:
                    errors.append(f"{decision_id}: LOCKED decision must be irreversible")
                unsupported = [
                    c for c in based_on
                    if c not in self.claims
                    or self.claims[c].get("status") != "SUPPORTED"
                    or not self.claims[c].get("support")
                ]
                if unsupported:
                    errors.append(
                        f"{decision_id}: LOCKED decision has non-supported basis {unsupported}"
                    )

            for impl_id in decision.get("implementation_refs", []):
                if impl_id not in self.implementations:
                    errors.append(f"{decision_id}: unknown implementation {impl_id}")

        for impl_id, implementation in self.implementations.items():
            for decision_id in implementation.get("decision_refs", []):
                if decision_id not in self.decisions:
                    errors.append(f"{impl_id}: unknown decision {decision_id}")
                    continue
                if impl_id not in self.decisions[decision_id].get("implementation_refs", []):
                    # LOCKED decisions may describe a required function implemented here
                    # without needing a prose-specific ref in their own record.
                    if self.decisions[decision_id].get("status") != "LOCKED":
                        errors.append(
                            f"{impl_id}: decision {decision_id} does not point back to implementation"
                        )

        return errors

    def permission(self, decision_id: str) -> str:
        return self.decisions[decision_id]["constraint"]

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
            decision_ids = {d["id"] for d in decisions}
            implementations = [
                i for i in self.implementations.values()
                if decision_ids.intersection(i.get("decision_refs", []))
            ]
            return {
                "type": "source",
                "source": source,
                "claims": claims,
                "decisions": decisions,
                "implementations": implementations,
            }

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
            decision_ids = {d["id"] for d in decisions}
            implementations = [
                i for i in self.implementations.values()
                if decision_ids.intersection(i.get("decision_refs", []))
            ]
            return {
                "type": "claim",
                "claim": claim,
                "sources": sources,
                "decisions": decisions,
                "implementations": implementations,
            }

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
            implementations = [
                self.implementations[i]
                for i in decision.get("implementation_refs", [])
                if i in self.implementations
            ]
            return {
                "type": "decision",
                "decision": decision,
                "permission": self.permission(node_id),
                "fully_source_backed": self.decision_fully_source_backed(node_id),
                "claims": claims,
                "sources": sources,
                "implementations": implementations,
            }

        if node_id in self.implementations:
            implementation = self.implementations[node_id]
            decisions = [
                self.decisions[d]
                for d in implementation.get("decision_refs", [])
                if d in self.decisions
            ]
            claim_ids: list[str] = []
            for decision in decisions:
                for claim_id in decision.get("based_on", []):
                    if claim_id not in claim_ids:
                        claim_ids.append(claim_id)
            claims = [self.claims[c] for c in claim_ids if c in self.claims]
            source_ids: list[str] = []
            for claim in claims:
                for edge in claim.get("support", []):
                    if edge["source"] not in source_ids:
                        source_ids.append(edge["source"])
            sources = [self.sources[s] for s in source_ids if s in self.sources]
            return {
                "type": "implementation",
                "implementation": implementation,
                "decisions": decisions,
                "claims": claims,
                "sources": sources,
            }

        raise KeyError(f"Unknown provenance node: {node_id}")
