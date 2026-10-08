from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .graph import ProvenanceGraph
from .io import load_data


@dataclass
class HistoricalMechanismRegistry:
    mechanisms: dict[str, dict[str, Any]]

    @classmethod
    def from_repo(cls, root: Path) -> "HistoricalMechanismRegistry":
        result: dict[str, dict[str, Any]] = {}
        path = root / "data" / "mechanisms"
        if path.exists():
            for file in sorted(path.glob("*.yaml")):
                doc = load_data(file) or {}
                for item in doc.get("historical_mechanisms", []):
                    item_id = item["id"]
                    if item_id in result:
                        raise ValueError(f"Duplicate historical mechanism id: {item_id}")
                    result[item_id] = item
        return cls(result)

    @staticmethod
    def _source_types_for_claims(
        graph: ProvenanceGraph, claim_refs: list[str]
    ) -> set[str]:
        result: set[str] = set()
        for claim_id in claim_refs:
            claim = graph.claims.get(claim_id)
            if not claim:
                continue
            for edge in claim.get("support", []):
                source = graph.sources.get(edge["source"])
                if source:
                    result.add(source["type"])
        return result

    def validate_integrity(self, graph: ProvenanceGraph) -> list[str]:
        errors: list[str] = []
        if not self.mechanisms:
            errors.append("historical mechanism registry must be nonempty")

        for mechanism_id, mechanism in self.mechanisms.items():
            if mechanism.get("effect") != "FEASIBILITY_ONLY":
                errors.append(f"{mechanism_id}: effect must be FEASIBILITY_ONLY")

            claim_refs = mechanism.get("claim_refs", [])
            for claim_id in claim_refs:
                claim = graph.claims.get(claim_id)
                if claim is None:
                    errors.append(f"{mechanism_id}: unknown claim {claim_id}")
                    continue
                if claim.get("status") != "SUPPORTED":
                    errors.append(f"{mechanism_id}: claim {claim_id} is not SUPPORTED")
                if claim.get("authority_scope") != "HISTORICAL_FEASIBILITY":
                    errors.append(
                        f"{mechanism_id}: claim {claim_id} must be HISTORICAL_FEASIBILITY"
                    )

            for impl_id in mechanism.get("implementation_refs", []):
                if impl_id not in graph.implementations:
                    errors.append(f"{mechanism_id}: unknown implementation {impl_id}")

            source_types = self._source_types_for_claims(graph, claim_refs)
            basis = mechanism.get("evidence_basis")
            verdict = mechanism.get("verdict")

            if basis == "PRIMARY" and "HISTORICAL_PRIMARY" not in source_types:
                errors.append(f"{mechanism_id}: PRIMARY basis lacks HISTORICAL_PRIMARY source")

            if basis == "SECONDARY_SOFT":
                if "SECONDARY_RESEARCH" not in source_types:
                    errors.append(
                        f"{mechanism_id}: SECONDARY_SOFT basis lacks SECONDARY_RESEARCH source"
                    )
                if "HISTORICAL_PRIMARY" in source_types:
                    errors.append(
                        f"{mechanism_id}: SECONDARY_SOFT must not masquerade as primary-backed"
                    )

            if verdict == "PASS-SOFT" and basis != "SECONDARY_SOFT":
                errors.append(
                    f"{mechanism_id}: PASS-SOFT must use SECONDARY_SOFT evidence basis"
                )

        return errors

    def describe(self, mechanism_id: str, graph: ProvenanceGraph) -> dict[str, Any]:
        if mechanism_id not in self.mechanisms:
            raise KeyError(f"Unknown historical mechanism: {mechanism_id}")

        mechanism = self.mechanisms[mechanism_id]
        claims = [
            graph.claims[c] for c in mechanism.get("claim_refs", []) if c in graph.claims
        ]
        source_ids: list[str] = []
        for claim in claims:
            for edge in claim.get("support", []):
                if edge["source"] not in source_ids:
                    source_ids.append(edge["source"])
        sources = [graph.sources[s] for s in source_ids if s in graph.sources]
        implementations = [
            graph.implementations[i]
            for i in mechanism.get("implementation_refs", [])
            if i in graph.implementations
        ]
        return {
            "mechanism": mechanism,
            "claims": claims,
            "sources": sources,
            "implementations": implementations,
        }


def format_mechanism(payload: dict[str, Any]) -> str:
    mechanism = payload["mechanism"]
    out = [
        "HISTORICAL MECHANISM",
        f"id: {mechanism['id']}",
        f"title: {mechanism['title']}",
        f"verdict: {mechanism['verdict']}",
        f"effect: {mechanism['effect']}",
        f"evidence_basis: {mechanism['evidence_basis']}",
        "",
        "ALLOWS (feasible, not required plot)",
    ]
    for item in mechanism["allows"]:
        out.append(f"- {item}")

    out.extend(["", "REJECTS AS HISTORICAL CLAIM"])
    for item in mechanism.get("rejects", []):
        out.append(f"- {item}")

    out.extend(["", "OPEN"])
    for item in mechanism["open"]:
        out.append(f"- {item}")

    out.extend(["", "CANNOT PROVE"])
    for item in mechanism["cannot_prove"]:
        out.append(f"- {item}")

    out.extend(["", "CLAIMS"])
    for claim in payload["claims"]:
        out.append(f"- {claim['id']} [{claim['status']}] {claim['statement']}")

    out.extend(["", "SOURCES"])
    for source in payload["sources"]:
        out.append(f"- {source['id']} ({source['type']}) {source['title']}")

    out.extend(["", "CURRENT IMPLEMENTATIONS"])
    if payload["implementations"]:
        for impl in payload["implementations"]:
            out.append(
                f"- {impl['id']} [{impl['status']}] ch{impl['chapter']} {impl['summary']}"
            )
    else:
        out.append("- none")

    return "\n".join(out)
