from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .io import load_data


REQUIRED_ISSUE4 = {
    "medical",
    "household_economy",
    "mourning_marriage",
    "detention",
    "pawnshop",
    "transport_letters",
    "monastic_economy",
}


@dataclass
class HistoricalAdapterRuntime:
    root: Path
    data: dict[str, Any]

    @classmethod
    def from_repo(cls, root: Path) -> "HistoricalAdapterRuntime":
        return cls(
            root=root,
            data=load_data(root / "data" / "mechanism_adapters" / "v04.json") or {},
        )

    @property
    def adapters(self) -> dict[str, dict[str, Any]]:
        return {x["id"]: x for x in self.data.get("adapters", [])}

    def summary(self) -> dict[str, Any]:
        backed = [x["id"] for x in self.adapters.values() if x["mechanism_refs"]]
        open_research = [
            x["id"] for x in self.adapters.values()
            if x["research_status"] == "OPEN_RESEARCH"
        ]
        return {
            "id": self.data.get("id"),
            "status": self.data.get("status"),
            "effect": self.data.get("effect"),
            "adapters": len(self.adapters),
            "required_issue4": sorted(REQUIRED_ISSUE4),
            "h_backed": sorted(backed),
            "open_research": sorted(open_research),
            "chapter86_first_implementation": self.data.get("completion", {}).get(
                "chapter86_first_implementation", []
            ),
            "structured_scene_findings": self.data.get("completion", {}).get(
                "structured_scene_findings"
            ),
        }

    def describe(self, adapter_id: str, mechanisms: Any | None = None) -> dict[str, Any]:
        adapter = self.adapters.get(adapter_id)
        if adapter is None:
            raise KeyError(f"Unknown historical adapter: {adapter_id}")
        payload = dict(adapter)
        open_questions = list(adapter.get("open_questions", []))
        cannot_prove = list(adapter.get("cannot_prove", []))
        if mechanisms is not None:
            for mid in adapter.get("mechanism_refs", []):
                mechanism = mechanisms.mechanisms[mid]
                for item in mechanism.get("open", []):
                    if item not in open_questions:
                        open_questions.append(item)
                for item in mechanism.get("cannot_prove", []):
                    if item not in cannot_prove:
                        cannot_prove.append(item)
        payload["effective_open_questions"] = open_questions
        payload["effective_cannot_prove"] = cannot_prove
        payload["plot_authority"] = "NONE"
        return payload

    def evaluate_scene(
        self,
        contract: dict[str, Any],
        text: str,
        mechanisms: Any | None = None,
    ) -> list[dict[str, Any]]:
        requirements = contract.get("historical_adapter_requirements", {})
        findings: list[dict[str, Any]] = []
        for adapter_id in contract.get("historical_adapters", []):
            if adapter_id not in self.adapters:
                findings.append({
                    "adapter": adapter_id,
                    "status": "FAIL",
                    "reason": "UNKNOWN_ADAPTER",
                    "plot_authority": "NONE",
                    "required_groups": [],
                    "forbidden_hits": [],
                    "open_questions": [],
                })
                continue
            adapter = self.describe(adapter_id, mechanisms)
            req = requirements.get(adapter_id, {})
            required_groups = []
            missing = []
            for index, terms in enumerate(req.get("required_any", []), start=1):
                hits = [term for term in terms if term in text]
                required_groups.append({
                    "group": index,
                    "terms": terms,
                    "hits": hits,
                    "pass": bool(hits),
                })
                if not hits:
                    missing.append(index)

            forbidden_terms = list(dict.fromkeys(
                list(adapter.get("global_reject_terms", []))
                + list(req.get("forbidden_any", []))
            ))
            forbidden_hits = [term for term in forbidden_terms if term in text]

            if forbidden_hits:
                status = "FAIL"
                reason = "HISTORICAL_OVERCLAIM"
            elif missing:
                status = "FAIL"
                reason = "MISSING_FEASIBILITY_SIGNAL"
            elif adapter["research_status"] == "OPEN_RESEARCH":
                status = "PASS_WITH_OPEN"
                reason = "OPEN_RESEARCH_PROFILE_ONLY"
            else:
                status = "PASS"
                reason = "FEASIBILITY_ONLY"

            findings.append({
                "adapter": adapter_id,
                "status": status,
                "reason": reason,
                "support_class": adapter["support_class"],
                "research_status": adapter["research_status"],
                "plot_authority": "NONE",
                "may_create_events": False,
                "mechanism_refs": adapter.get("mechanism_refs", []),
                "required_groups": required_groups,
                "missing_required_groups": missing,
                "forbidden_hits": forbidden_hits,
                "open_questions": adapter["effective_open_questions"],
                "cannot_prove": adapter["effective_cannot_prove"],
            })
        return findings

    def scene_status(
        self,
        contract: dict[str, Any],
        text: str,
        mechanisms: Any | None = None,
    ) -> dict[str, Any]:
        findings = self.evaluate_scene(contract, text, mechanisms)
        return {
            "scene_id": contract.get("id"),
            "status": "FAIL" if any(x["status"] == "FAIL" for x in findings) else "PASS",
            "findings": findings,
            "plot_authority": "NONE",
        }

    def validate_integrity(self, mechanisms: Any, registry: Any) -> list[str]:
        errors: list[str] = []
        if self.data.get("issue") != 4:
            errors.append("historical adapters must be bound to issue #4")
        if self.data.get("effect") != "FEASIBILITY_ONLY":
            errors.append("adapter runtime effect must remain FEASIBILITY_ONLY")

        present = set(self.adapters)
        missing = REQUIRED_ISSUE4 - present
        if missing:
            errors.append(f"missing issue #4 adapters: {sorted(missing)}")

        completion = self.data.get("completion", {})
        if set(completion.get("chapter86_first_implementation", [])) != {
            "medical", "household_economy"
        }:
            errors.append("chapter86 first implementation must be medical + household_economy")
        if completion.get("structured_scene_findings") is not True:
            errors.append("issue #4 requires structured scene findings")
        if completion.get("preserves_open") is not True:
            errors.append("issue #4 must preserve OPEN historical questions")
        if completion.get("plot_invention") is not False:
            errors.append("historical adapters may not invent plot")

        for aid, adapter in self.adapters.items():
            if adapter.get("effect") != "FEASIBILITY_ONLY":
                errors.append(f"{aid}: effect drift")
            if adapter.get("plot_authority") != "NONE":
                errors.append(f"{aid}: plot authority must be NONE")
            if adapter.get("may_create_events") is not False:
                errors.append(f"{aid}: adapter may not create events")
            for mid in adapter.get("mechanism_refs", []):
                if mid not in mechanisms.mechanisms:
                    errors.append(f"{aid}: unknown mechanism {mid}")
            for ref in adapter.get("source_refs", []):
                if ref.startswith("doc:") and ref not in registry.documents:
                    errors.append(f"{aid}: unknown source document {ref}")

            if adapter.get("research_status") == "OPEN_RESEARCH":
                if adapter.get("mechanism_refs"):
                    errors.append(f"{aid}: OPEN_RESEARCH adapter must not pretend H-backed authority")
                if not adapter.get("open_questions"):
                    errors.append(f"{aid}: OPEN_RESEARCH adapter must retain open questions")

            described = self.describe(aid, mechanisms)
            for mid in adapter.get("mechanism_refs", []):
                for item in mechanisms.mechanisms[mid].get("open", []):
                    if item not in described["effective_open_questions"]:
                        errors.append(f"{aid}: lost OPEN question from {mid}: {item}")
                for item in mechanisms.mechanisms[mid].get("cannot_prove", []):
                    if item not in described["effective_cannot_prove"]:
                        errors.append(f"{aid}: lost cannot_prove boundary from {mid}: {item}")

        return errors


def format_adapter(kind: str, payload: Any) -> str:
    if kind == "summary":
        return "\n".join([
            "HISTORICAL ADAPTERS v0.4",
            f"status: {payload['status']}",
            f"effect: {payload['effect']}",
            f"adapters: {payload['adapters']}",
            f"issue4-required: {', '.join(payload['required_issue4'])}",
            f"h-backed: {', '.join(payload['h_backed'])}",
            f"open-research: {', '.join(payload['open_research']) or 'none'}",
            f"chapter86-first: {', '.join(payload['chapter86_first_implementation'])}",
        ])
    if kind == "describe":
        return "\n".join([
            f"HISTORICAL ADAPTER {payload['id']} / {payload['title']}",
            f"effect: {payload['effect']}",
            f"research_status: {payload['research_status']}",
            f"plot_authority: {payload['plot_authority']}",
            f"mechanisms: {', '.join(payload['mechanism_refs']) or 'none'}",
            f"open_questions: {len(payload['effective_open_questions'])}",
            f"cannot_prove: {len(payload['effective_cannot_prove'])}",
        ])
    if kind == "scene":
        lines = [
            f"HISTORICAL ADAPTER SCENE {payload['scene_id']}",
            f"status: {payload['status']}",
            "plot_authority: NONE",
        ]
        for item in payload["findings"]:
            lines.append(
                f"- {item['adapter']}: {item['status']} / {item['reason']} "
                f"(open={len(item['open_questions'])})"
            )
        return "\n".join(lines)
    return str(payload)
