from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass
class EvaluationResult:
    evaluator: str
    status: str
    findings: list[str]
    details: Any | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _matches_any(text: str, terms: list[str]) -> bool:
    return any(term in text for term in terms)


def evaluate_scene_text(
    contract: dict[str, Any],
    text: str,
    knowledge_runtime: Any | None = None,
    mechanism_adapter_runtime: Any | None = None,
    historical_mechanisms: Any | None = None,
) -> list[EvaluationResult]:
    results: list[EvaluationResult] = []

    missing = []
    for beat in contract.get("required_beats", []):
        terms = beat.get("any_text", [])
        if terms and not _matches_any(text, terms):
            missing.append(f"Missing required beat {beat['id']}: expected one of {terms}")
    results.append(EvaluationResult("required_beats", "FAIL" if missing else "PASS", missing))

    forbidden = []
    for beat in contract.get("forbidden_beats", []):
        terms = beat.get("any_text", [])
        hits = [term for term in terms if term in text]
        if hits:
            forbidden.append(f"Forbidden beat {beat['id']} matched: {hits}")
    results.append(EvaluationResult("forbidden_beats", "FAIL" if forbidden else "PASS", forbidden))

    exposition_terms = ["终于明白", "这才懂得人生", "看破红尘", "所谓人生", "人生不过"]
    exposition_hits = [term for term in exposition_terms if term in text]
    results.append(
        EvaluationResult(
            "exposition",
            "WARN" if exposition_hits else "PASS",
            [f"Explicit interpretation phrase: {x}" for x in exposition_hits],
        )
    )

    if knowledge_runtime is not None and contract.get("knowledge_guards"):
        payload = knowledge_runtime.text_guard(contract["id"], contract, text)
        results.append(
            EvaluationResult(
                "knowledge_omniscience",
                payload["status"],
                payload["findings"],
                payload,
            )
        )

    if mechanism_adapter_runtime is not None and contract.get("historical_adapters"):
        payload = mechanism_adapter_runtime.scene_status(
            contract,
            text,
            historical_mechanisms,
        )
        for item in payload["findings"]:
            public_status = "FAIL" if item["status"] == "FAIL" else "PASS"
            human_findings = []
            if item["missing_required_groups"]:
                human_findings.append(
                    f"Missing feasibility signal groups: {item['missing_required_groups']}"
                )
            if item["forbidden_hits"]:
                human_findings.append(
                    f"Historical overclaim terms: {item['forbidden_hits']}"
                )
            if item["status"] == "PASS_WITH_OPEN":
                human_findings.append(
                    "Feasibility profile passes only with historical questions preserved OPEN."
                )
            results.append(
                EvaluationResult(
                    f"historical_adapter:{item['adapter']}",
                    public_status,
                    human_findings,
                    item,
                )
            )

    return results


def overall_status(results: list[EvaluationResult]) -> str:
    if any(r.status == "FAIL" for r in results):
        return "FAIL"
    if any(r.status == "WARN" for r in results):
        return "WARN"
    return "PASS"
