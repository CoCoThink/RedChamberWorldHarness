from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .graph import ProvenanceGraph
from .io import load_data


@dataclass
class LiteralRegistry:
    constraints: dict[str, dict[str, Any]]

    @classmethod
    def from_repo(cls, root: Path) -> "LiteralRegistry":
        result: dict[str, dict[str, Any]] = {}
        path = root / "data" / "literals"
        if path.exists():
            for file in sorted(path.glob("*.yaml")):
                doc = load_data(file) or {}
                for item in doc.get("literal_constraints", []):
                    item_id = item["id"]
                    if item_id in result:
                        raise ValueError(f"Duplicate literal constraint id: {item_id}")
                    result[item_id] = item
        return cls(result)

    def validate_integrity(self, graph: ProvenanceGraph) -> list[str]:
        errors: list[str] = []
        exact_targets = {"NOVEL_EXACT", "NAME_EXACT"}

        for literal_id, literal in self.constraints.items():
            targets = set(literal.get("targets", []))
            claim_refs = literal.get("claim_refs", [])

            for claim_id in claim_refs:
                if claim_id not in graph.claims:
                    errors.append(f"{literal_id}: unknown claim {claim_id}")
                    continue
                claim = graph.claims[claim_id]
                if claim.get("status") != "SUPPORTED":
                    errors.append(f"{literal_id}: claim {claim_id} is not SUPPORTED")

            advertised_targets: set[str] = set()
            for claim_id in claim_refs:
                if claim_id in graph.claims:
                    advertised_targets.update(graph.claims[claim_id].get("literal_targets", []))
            if not targets.issubset(advertised_targets):
                missing = sorted(targets - advertised_targets)
                errors.append(
                    f"{literal_id}: targets {missing} are not supported by claim literal_targets"
                )

            for decision_id in literal.get("decision_refs", []):
                if decision_id not in graph.decisions:
                    errors.append(f"{literal_id}: unknown decision {decision_id}")

            for impl_id in literal.get("implementation_refs", []):
                if impl_id not in graph.implementations:
                    errors.append(f"{literal_id}: unknown implementation {impl_id}")

            required = literal.get("required_in_active_prose", False)
            if targets.intersection(exact_targets):
                if not required:
                    errors.append(
                        f"{literal_id}: NOVEL_EXACT/NAME_EXACT must be required in active prose"
                    )
                if not literal.get("implementation_refs"):
                    errors.append(
                        f"{literal_id}: exact literal requires an active implementation locator"
                    )

            if targets == {"SOURCE_EXACT"} and required:
                errors.append(
                    f"{literal_id}: SOURCE_EXACT alone must not require prose insertion"
                )

            if targets == {"SEM"} and required:
                errors.append(
                    f"{literal_id}: SEM alone must not require exact prose insertion"
                )

            if "BOUNDARY" in targets:
                boundary = literal.get("boundary")
                if not boundary:
                    errors.append(f"{literal_id}: BOUNDARY target requires boundary metadata")
                else:
                    claim_id = boundary.get("claim_ref")
                    if claim_id not in graph.claims:
                        errors.append(f"{literal_id}: boundary claim {claim_id} is unknown")
                    elif graph.claims[claim_id].get("status") != "SUPPORTED":
                        errors.append(
                            f"{literal_id}: boundary claim {claim_id} is not SUPPORTED"
                        )

        return errors

    def describe(self, literal_id: str, graph: ProvenanceGraph) -> dict[str, Any]:
        if literal_id not in self.constraints:
            raise KeyError(f"Unknown literal constraint: {literal_id}")
        literal = self.constraints[literal_id]
        claims = [graph.claims[c] for c in literal.get("claim_refs", []) if c in graph.claims]
        decisions = [
            graph.decisions[d] for d in literal.get("decision_refs", []) if d in graph.decisions
        ]
        implementations = [
            graph.implementations[i]
            for i in literal.get("implementation_refs", [])
            if i in graph.implementations
        ]
        source_ids: list[str] = []
        for claim in claims:
            for edge in claim.get("support", []):
                if edge["source"] not in source_ids:
                    source_ids.append(edge["source"])
        sources = [graph.sources[s] for s in source_ids if s in graph.sources]
        return {
            "literal": literal,
            "claims": claims,
            "decisions": decisions,
            "implementations": implementations,
            "sources": sources,
        }


def format_literal(payload: dict[str, Any]) -> str:
    literal = payload["literal"]
    out = [
        "LITERAL CONSTRAINT",
        f"id: {literal['id']}",
        f"text: {literal['text']}",
        f"targets: {literal['targets']}",
        f"scope: {literal['scope']}",
        f"required_in_active_prose: {literal['required_in_active_prose']}",
    ]
    if literal.get("boundary"):
        out.append(f"boundary: {literal['boundary']['description']}")

    out.extend(["", "CLAIMS"])
    for claim in payload["claims"]:
        out.append(f"- {claim['id']} [{claim['status']}] {claim['statement']}")

    out.extend(["", "SOURCES"])
    for source in payload["sources"]:
        out.append(f"- {source['id']} [{source.get('tier')}] {source['title']}")

    out.extend(["", "DECISIONS"])
    for decision in payload["decisions"]:
        out.append(
            f"- {decision['id']} [{decision['status']}/{decision['constraint']}] "
            f"{decision['statement']}"
        )

    out.extend(["", "IMPLEMENTATIONS"])
    if payload["implementations"]:
        for impl in payload["implementations"]:
            out.append(
                f"- {impl['id']} [{impl['status']}] ch{impl['chapter']} "
                f"{impl['locator']}"
            )
    else:
        out.append("- none (source-only constraint)")

    return "\n".join(out)
