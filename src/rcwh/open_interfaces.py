from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .graph import ProvenanceGraph
from .history import HistoricalMechanismRegistry
from .io import load_data
from .literals import LiteralRegistry


@dataclass
class OpenInterfaceRegistry:
    interfaces: dict[str, dict[str, Any]]

    @classmethod
    def from_repo(cls, root: Path) -> "OpenInterfaceRegistry":
        result: dict[str, dict[str, Any]] = {}
        path = root / "data" / "open_interfaces"
        if path.exists():
            for file in sorted(path.glob("*.yaml")):
                doc = load_data(file) or {}
                for item in doc.get("open_interfaces", []):
                    item_id = item["id"]
                    if item_id in result:
                        raise ValueError(f"Duplicate OPEN interface id: {item_id}")
                    result[item_id] = item
        return cls(result)

    def validate_integrity(
        self,
        graph: ProvenanceGraph,
        literals: LiteralRegistry,
        mechanisms: HistoricalMechanismRegistry,
    ) -> list[str]:
        errors: list[str] = []
        expected = {f"OL-{i:03d}" for i in range(1, 29)}
        present = set(self.interfaces)
        if present and present != expected:
            errors.append(
                "OPEN registry must contain OL-001..OL-028 exactly; "
                f"missing={sorted(expected-present)} extra={sorted(present-expected)}"
            )

        for interface_id, interface in self.interfaces.items():
            if interface.get("state") != "OPEN_LOCKED":
                errors.append(f"{interface_id}: state must remain OPEN_LOCKED")

            for decision_id in interface.get("hard_anchor_decision_refs", []):
                decision = graph.decisions.get(decision_id)
                if decision is None:
                    errors.append(f"{interface_id}: unknown hard anchor decision {decision_id}")
                elif decision.get("status") != "LOCKED":
                    errors.append(
                        f"{interface_id}: hard anchor {decision_id} is not LOCKED"
                    )

            for decision_id in interface.get("open_decision_refs", []):
                decision = graph.decisions.get(decision_id)
                if decision is None:
                    errors.append(f"{interface_id}: unknown open decision {decision_id}")
                elif decision.get("status") != "OPEN" or decision.get("constraint") != "OPEN":
                    errors.append(
                        f"{interface_id}: open decision {decision_id} must remain OPEN/OPEN"
                    )

            for decision_id in interface.get("current_decision_refs", []):
                decision = graph.decisions.get(decision_id)
                if decision is None:
                    errors.append(f"{interface_id}: unknown current decision {decision_id}")
                elif decision.get("status") != "CURRENT" or decision.get("constraint") != "MAY":
                    errors.append(
                        f"{interface_id}: current decision {decision_id} must remain CURRENT/MAY"
                    )

            for literal_id in interface.get("literal_refs", []):
                if literal_id not in literals.constraints:
                    errors.append(f"{interface_id}: unknown literal {literal_id}")

            for mechanism_id in interface.get("mechanism_refs", []):
                if mechanism_id not in mechanisms.mechanisms:
                    errors.append(f"{interface_id}: unknown mechanism {mechanism_id}")

            for impl_id in interface.get("implementation_refs", []):
                if impl_id not in graph.implementations:
                    errors.append(f"{interface_id}: unknown implementation {impl_id}")

            current_status = interface["current_model"]["status"]
            if current_status.startswith("LOCK"):
                errors.append(
                    f"{interface_id}: current model may not masquerade as locked evidence"
                )

            if not interface.get("forbidden_hardening"):
                errors.append(f"{interface_id}: missing forbidden_hardening")
            if not interface.get("reopen_triggers"):
                errors.append(f"{interface_id}: missing reopen_triggers")

        return errors

    def describe(
        self,
        interface_id: str,
        graph: ProvenanceGraph,
        literals: LiteralRegistry,
        mechanisms: HistoricalMechanismRegistry,
    ) -> dict[str, Any]:
        if interface_id not in self.interfaces:
            raise KeyError(f"Unknown OPEN interface: {interface_id}")
        item = self.interfaces[interface_id]
        return {
            "interface": item,
            "hard_anchor_decisions": [
                graph.decisions[x]
                for x in item.get("hard_anchor_decision_refs", [])
                if x in graph.decisions
            ],
            "open_decisions": [
                graph.decisions[x]
                for x in item.get("open_decision_refs", [])
                if x in graph.decisions
            ],
            "current_decisions": [
                graph.decisions[x]
                for x in item.get("current_decision_refs", [])
                if x in graph.decisions
            ],
            "literals": [
                literals.constraints[x]
                for x in item.get("literal_refs", [])
                if x in literals.constraints
            ],
            "mechanisms": [
                mechanisms.mechanisms[x]
                for x in item.get("mechanism_refs", [])
                if x in mechanisms.mechanisms
            ],
            "implementations": [
                graph.implementations[x]
                for x in item.get("implementation_refs", [])
                if x in graph.implementations
            ],
        }


def format_open_interface(payload: dict[str, Any]) -> str:
    item = payload["interface"]
    out = [
        "OPEN INTERFACE",
        f"id: {item['id']}",
        f"title: {item['title']}",
        f"state: {item['state']}",
        f"current_model: {item['current_model']['status']} — {item['current_model']['summary']}",
        "",
        "UNCERTAINTY",
    ]
    out.extend(f"- {x}" for x in item["uncertainty"])
    out.extend(["", "FORBIDDEN HARDENING"])
    out.extend(f"- {x}" for x in item["forbidden_hardening"])
    out.extend(["", "REOPEN TRIGGERS"])
    out.extend(f"- {x}" for x in item["reopen_triggers"])

    for label, key in [
        ("HARD ANCHORS", "hard_anchor_decisions"),
        ("OPEN DECISIONS", "open_decisions"),
        ("CURRENT DECISIONS", "current_decisions"),
    ]:
        out.extend(["", label])
        values = payload[key]
        if values:
            for value in values:
                out.append(
                    f"- {value['id']} [{value['status']}/{value['constraint']}] "
                    f"{value['statement']}"
                )
        else:
            out.append("- none")

    out.extend(["", "HISTORICAL MECHANISMS"])
    if payload["mechanisms"]:
        for value in payload["mechanisms"]:
            out.append(f"- {value['id']} [{value['verdict']}] {value['title']}")
    else:
        out.append("- none")

    out.extend(["", "CURRENT IMPLEMENTATIONS"])
    if payload["implementations"]:
        for value in payload["implementations"]:
            out.append(f"- {value['id']} ch{value['chapter']} {value['summary']}")
    else:
        out.append("- none")

    return "\n".join(out)
