from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass
class EvaluationResult:
    evaluator: str
    status: str
    findings: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _matches_any(text: str, terms: list[str]) -> bool:
    return any(term in text for term in terms)


def evaluate_scene_text(contract: dict[str, Any], text: str) -> list[EvaluationResult]:
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

    return results


def overall_status(results: list[EvaluationResult]) -> str:
    if any(r.status == "FAIL" for r in results):
        return "FAIL"
    if any(r.status == "WARN" for r in results):
        return "WARN"
    return "PASS"
