from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any
from pathlib import Path


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
    semantic_reading: dict | None = None,
    entry_state: dict | None = None,
    candidate_authors: list[dict] | None = None,
    root: Path | None = None,
) -> list[EvaluationResult]:
    results: list[EvaluationResult] = []

    missing = []
    for beat in contract.get("required_beats", []):
        terms = beat.get("any_text", [])
        if terms and not _matches_any(text, terms):
            missing.append(f"Missing required beat {beat['id']}: expected one of {terms}")
    results.append(EvaluationResult("lint:required_beats", "WARN" if missing else "PASS", missing, {"report_kind": "LINT", "semantic_coverage": False}))

    forbidden = []
    for beat in contract.get("forbidden_beats", []):
        terms = beat.get("any_text", [])
        hits = [term for term in terms if term in text]
        if hits:
            forbidden.append(f"Forbidden beat {beat['id']} matched: {hits}")
    results.append(EvaluationResult("lint:forbidden_beats", "WARN" if forbidden else "PASS", forbidden, {"report_kind": "LINT", "semantic_coverage": False}))

    exposition_terms = ["终于明白", "这才懂得人生", "看破红尘", "所谓人生", "人生不过"]
    exposition_hits = [term for term in exposition_terms if term in text]
    results.append(
        EvaluationResult(
            "lint:exposition",
            "WARN" if exposition_hits else "PASS",
            [f"Explicit interpretation phrase: {x}" for x in exposition_hits],
        )
    )

    if knowledge_runtime is not None and contract.get("knowledge_guards"):
        payload = knowledge_runtime.text_guard(contract["id"], contract, text)
        results.append(
            EvaluationResult(
                "lint:knowledge_omniscience",
                "WARN" if payload["findings"] else "PASS",
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
            public_status = "FAIL" if item.get("reason") == "UNKNOWN_ADAPTER" else "WARN" if item["missing_required_groups"] or item["forbidden_hits"] else "PASS"
            human_findings = []
            if item["missing_required_groups"]:
                human_findings.append(
                    f"Missing lexical signal groups: {item['missing_required_groups']}"
                )
            if item["forbidden_hits"]:
                human_findings.append(
                    f"Historical overclaim terms: {item['forbidden_hits']}"
                )
            if item["status"] == "PASS_WITH_OPEN":
                human_findings.append(
                    "Lexical hints present; historical feasibility remains unverified and OPEN."
                )
            results.append(
                EvaluationResult(
                    f"lint:historical_adapter:{item['adapter']}",
                    public_status,
                    human_findings,
                    item,
                )
            )

    from .evaluation.semantics import make_request, check_reading, registered_reading
    from .io import load_data
    schema_root = root or getattr(knowledge_runtime, "root", None) or Path(__file__).resolve().parents[2]
    if entry_state is None:
        from .evaluation.state import SceneStateAdapter
        entry_state = SceneStateAdapter(schema_root, contract).snapshot()
    request = make_request(contract, text, entry_state, candidate_authors)
    if semantic_reading is None:
        semantic_reading = registered_reading(schema_root, request)
    semantic = check_reading(request, semantic_reading, load_data(schema_root / "schemas/semantic_reading.schema.json"), knowledge_runtime, schema_root)
    results.append(EvaluationResult("scene_semantics", semantic["status"], semantic["findings"], semantic))
    return results


def overall_status(results: list[EvaluationResult]) -> str:
    if any(r.status == "FAIL" for r in results):
        return "FAIL"
    if any(r.status == "PENDING" for r in results):
        return "PENDING"
    if any(r.status == "WARN" for r in results):
        return "WARN"
    return "PASS"
